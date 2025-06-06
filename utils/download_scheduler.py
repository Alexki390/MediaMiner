
"""
Intelligent download scheduler for optimal performance and rate limiting.
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Callable, Optional
from datetime import datetime, timedelta
import threading
from queue import Queue, PriorityQueue

class DownloadScheduler:
    """Manages download scheduling with rate limiting and optimization."""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.config = config_manager.get_config()
        self.download_queue = PriorityQueue()
        self.active_downloads = {}
        self.rate_limiters = {}
        self.statistics = {
            'total_downloads': 0,
            'successful_downloads': 0,
            'failed_downloads': 0,
            'bytes_downloaded': 0,
            'average_speed': 0
        }
        
    def schedule_download(self, url: str, platform: str, options: Dict[str, Any], 
                         priority: int = 5, callback: Optional[Callable] = None) -> str:
        """Schedule a download with priority and rate limiting."""
        try:
            download_id = f"{platform}_{int(time.time())}_{hash(url) % 10000}"
            
            download_task = {
                'id': download_id,
                'url': url,
                'platform': platform,
                'options': options,
                'callback': callback,
                'scheduled_time': datetime.now(),
                'retry_count': 0,
                'status': 'scheduled'
            }
            
            # Add to priority queue (lower number = higher priority)
            self.download_queue.put((priority, download_task))
            
            # Initialize rate limiter for platform if not exists
            if platform not in self.rate_limiters:
                self.rate_limiters[platform] = {
                    'last_request': 0,
                    'request_count': 0,
                    'window_start': time.time(),
                    'max_requests_per_minute': self._get_platform_rate_limit(platform)
                }
            
            logging.info(f"Download scheduled: {download_id} for {platform}")
            return download_id
            
    def _get_platform_rate_limit(self, platform: str) -> int:
        """Get rate limit for specific platform."""
        rate_limits = {
            'youtube': 30,      # 30 requests per minute
            'tiktok': 20,       # 20 requests per minute (more restrictive)
            'instagram': 15,    # 15 requests per minute (very restrictive)
            'reddit': 60,       # 60 requests per minute (more lenient)
            'twitter': 25,      # 25 requests per minute
            'default': 30
        }
        return rate_limits.get(platform, rate_limits['default'])
        
    def _should_rate_limit(self, platform: str) -> bool:
        """Check if request should be rate limited."""
        try:
            if platform not in self.rate_limiters:
                return False
                
            limiter = self.rate_limiters[platform]
            current_time = time.time()
            
            # Reset window if minute has passed
            if current_time - limiter['window_start'] >= 60:
                limiter['request_count'] = 0
                limiter['window_start'] = current_time
                
            # Check if we've exceeded rate limit
            if limiter['request_count'] >= limiter['max_requests_per_minute']:
                return True
                
            return False
            
        except Exception as e:
            logging.error(f"Error checking rate limit: {e}")
            return False
            
    def _update_rate_limiter(self, platform: str):
        """Update rate limiter after successful request."""
        try:
            if platform in self.rate_limiters:
                self.rate_limiters[platform]['request_count'] += 1
                self.rate_limiters[platform]['last_request'] = time.time()
        except Exception as e:
            logging.error(f"Error updating rate limiter: {e}")
            
    def execute_downloads(self, max_concurrent: int = 3) -> Dict[str, Any]:
        """Execute scheduled downloads with rate limiting and optimization."""
        try:
            executed_count = 0
            successful_count = 0
            failed_count = 0
            
            # Process downloads in batches to respect rate limits
            while not self.download_queue.empty():
                # Get next download
                priority, download_task = self.download_queue.get()
                platform = download_task['platform']
                
                # Check rate limiting
                if self._should_rate_limit(platform):
                    # Put back in queue and wait
                    self.download_queue.put((priority, download_task))
                    time.sleep(10)  # Wait 10 seconds before retrying
                    continue
                
                # Execute download
                try:
                    result = self._execute_single_download(download_task)
                    
                    if result.get('success', False):
                        successful_count += 1
                        self._update_rate_limiter(platform)
                    else:
                        failed_count += 1
                        
                    executed_count += 1
                    
                except Exception as e:
                    logging.error(f"Download execution failed: {e}")
                    failed_count += 1
                    
                # Small delay between downloads
                time.sleep(1)
                
            return {
                'success': True,
                'executed': executed_count,
                'successful': successful_count,
                'failed': failed_count
            }
            
        except Exception as e:
            logging.error(f"Batch execution failed: {e}")
            return {'success': False, 'error': str(e)}
            
    def _execute_single_download(self, download_task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single download task."""
        try:
            platform = download_task['platform']
            url = download_task['url']
            options = download_task['options']
            callback = download_task.get('callback')
            
            # Import appropriate downloader
            downloader_map = {
                'youtube': 'downloaders.youtube_downloader.YouTubeDownloader',
                'tiktok': 'downloaders.tiktok_downloader.TikTokDownloader',
                'instagram': 'downloaders.instagram_downloader.InstagramDownloader',
                'reddit': 'downloaders.reddit_downloader.RedditDownloader',
                'twitter': 'downloaders.twitter_downloader.TwitterDownloader'
            }
            
            if platform not in downloader_map:
                return {'success': False, 'error': f'Unsupported platform: {platform}'}
            
            # Dynamic import and execution
            module_path, class_name = downloader_map[platform].rsplit('.', 1)
            module = __import__(module_path, fromlist=[class_name])
            downloader_class = getattr(module, class_name)
            
            downloader = downloader_class(self.config_manager)
            result = downloader.download(url, options)
            
            # Execute callback if provided
            if callback:
                callback(result)
                
            return result
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
        except Exception as e:
            logging.error(f"Failed to schedule download: {e}")
            return None
            
    def start_scheduler(self, max_concurrent: int = 3):
        """Start the download scheduler."""
        try:
            for i in range(max_concurrent):
                worker_thread = threading.Thread(
                    target=self._worker_thread,
                    args=(f"worker_{i}",),
                    daemon=True
                )
                worker_thread.start()
                
            logging.info(f"Download scheduler started with {max_concurrent} workers")
            
        except Exception as e:
            logging.error(f"Failed to start scheduler: {e}")
            
    def _worker_thread(self, worker_name: str):
        """Worker thread for processing downloads."""
        while True:
            try:
                # Get next download task
                priority, download_task = self.download_queue.get()
                
                if download_task is None:  # Shutdown signal
                    break
                    
                # Check rate limiting
                platform = download_task['platform']
                if not self._check_rate_limit(platform):
                    # Re-queue with delay
                    time.sleep(self._get_rate_limit_delay(platform))
                    self.download_queue.put((priority, download_task))
                    continue
                    
                # Execute download
                self._execute_download(download_task, worker_name)
                
                # Mark task as done
                self.download_queue.task_done()
                
            except Exception as e:
                logging.error(f"Worker {worker_name} error: {e}")
                time.sleep(1)
                
    def _execute_download(self, download_task: Dict[str, Any], worker_name: str):
        """Execute a download task."""
        try:
            download_id = download_task['id']
            platform = download_task['platform']
            
            logging.info(f"Worker {worker_name} starting download: {download_id}")
            
            # Update statistics
            self.statistics['total_downloads'] += 1
            
            # Track active download
            self.active_downloads[download_id] = {
                'task': download_task,
                'worker': worker_name,
                'start_time': time.time()
            }
            
            # Here you would call the actual downloader
            # result = downloader.download(download_task['url'], download_task['options'])
            
            # Simulate download for now
            time.sleep(2)  # Simulate download time
            result = {'success': True, 'files_downloaded': 1}
            
            # Update statistics
            if result.get('success', False):
                self.statistics['successful_downloads'] += 1
            else:
                self.statistics['failed_downloads'] += 1
                
            # Execute callback if provided
            if download_task['callback']:
                download_task['callback'](download_id, result)
                
            # Clean up
            del self.active_downloads[download_id]
            
            logging.info(f"Download completed: {download_id}")
            
        except Exception as e:
            logging.error(f"Download execution failed: {e}")
            self.statistics['failed_downloads'] += 1
            
    def _check_rate_limit(self, platform: str) -> bool:
        """Check if platform rate limit allows download."""
        try:
            current_time = time.time()
            
            if platform not in self.rate_limiters:
                self.rate_limiters[platform] = {
                    'last_request': 0,
                    'requests_this_minute': 0,
                    'minute_start': current_time
                }
                
            limiter = self.rate_limiters[platform]
            
            # Reset minute counter if needed
            if current_time - limiter['minute_start'] >= 60:
                limiter['requests_this_minute'] = 0
                limiter['minute_start'] = current_time
                
            # Platform-specific rate limits
            limits = {
                'youtube': {'requests_per_minute': 30, 'min_delay': 1},
                'tiktok': {'requests_per_minute': 20, 'min_delay': 2},
                'instagram': {'requests_per_minute': 15, 'min_delay': 3},
                'reddit': {'requests_per_minute': 60, 'min_delay': 0.5},
                'twitter': {'requests_per_minute': 25, 'min_delay': 1.5}
            }
            
            platform_limits = limits.get(platform, {'requests_per_minute': 30, 'min_delay': 1})
            
            # Check requests per minute
            if limiter['requests_this_minute'] >= platform_limits['requests_per_minute']:
                return False
                
            # Check minimum delay between requests
            if current_time - limiter['last_request'] < platform_limits['min_delay']:
                return False
                
            # Update rate limiter
            limiter['last_request'] = current_time
            limiter['requests_this_minute'] += 1
            
            return True
            
        except Exception as e:
            logging.error(f"Rate limit check failed: {e}")
            return True  # Allow download on error
            
    def _get_rate_limit_delay(self, platform: str) -> float:
        """Get delay time for rate-limited platform."""
        delays = {
            'youtube': 1.0,
            'tiktok': 2.0,
            'instagram': 3.0,
            'reddit': 0.5,
            'twitter': 1.5
        }
        return delays.get(platform, 1.0)
        
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status."""
        return {
            'queued_downloads': self.download_queue.qsize(),
            'active_downloads': len(self.active_downloads),
            'statistics': self.statistics.copy(),
            'rate_limiters': {
                platform: {
                    'requests_this_minute': data['requests_this_minute'],
                    'last_request_ago': time.time() - data['last_request']
                }
                for platform, data in self.rate_limiters.items()
            }
        }
        
    def cancel_download(self, download_id: str) -> bool:
        """Cancel a scheduled or active download."""
        try:
            # Remove from active downloads if present
            if download_id in self.active_downloads:
                del self.active_downloads[download_id]
                logging.info(f"Cancelled active download: {download_id}")
                return True
                
            # Note: Removing from PriorityQueue is complex, 
            # so we'll mark it as cancelled in a real implementation
            logging.info(f"Download cancellation requested: {download_id}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to cancel download: {e}")
            return False
