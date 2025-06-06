
"""
XVideos downloader for adult video content.
"""

import os
import logging
import requests
import json
import time
import re
from typing import Dict, Any, Callable, Optional, List
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup

from .base_downloader import BaseDownloader

class XVideosDownloader(BaseDownloader):
    """XVideos content downloader."""
    
    def __init__(self, config_manager):
        super().__init__(config_manager)
        self.platform = "xvideos"
        self.base_url = "https://www.xvideos.com"
        
    def download(self, url: str, options: Dict[str, Any], 
                progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        """Download XVideos content."""
        try:
            self.log_download_start(self.platform, url)
            
            # Determine if it's a single video or user/channel profile
            if self._is_video_url(url):
                result = self._download_single_video(url, options, progress_callback)
            else:
                result = self._download_channel_content(url, options, progress_callback)
                
            if result['success']:
                self.log_download_complete(self.platform, url, result.get('files_downloaded', 0))
            else:
                self.log_download_error(self.platform, url, result.get('error', 'Unknown error'))
                
            return result
            
        except Exception as e:
            error_msg = f"XVideos download failed: {str(e)}"
            self.log_download_error(self.platform, url, error_msg)
            return {'success': False, 'error': error_msg}
            
    def _is_video_url(self, url: str) -> bool:
        """Check if the URL is a single video URL."""
        return '/video' in url and 'xvideos.com' in url
        
    def _download_single_video(self, url: str, options: Dict[str, Any], 
                             progress_callback: Optional[Callable[[int], None]]) -> Dict[str, Any]:
        """Download a single XVideos video."""
        try:
            # Get video info
            video_info = self._get_video_info(url)
            if not video_info:
                return {'success': False, 'error': 'Failed to get video information'}
                
            download_path = self.get_download_path(self.platform)
            
            # Download the video
            result = self._download_video_media(video_info, download_path, progress_callback)
            return result
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    def _download_channel_content(self, url: str, options: Dict[str, Any], 
                                progress_callback: Optional[Callable[[int], None]]) -> Dict[str, Any]:
        """Download all content from an XVideos channel/user."""
        try:
            # Extract channel/user name
            channel_name = self._extract_channel_name(url)
            if not channel_name:
                return {'success': False, 'error': 'Could not extract channel name from URL'}
                
            max_videos = options.get('limit', 0)  # 0 = unlimited
            
            # Get channel's videos with pagination
            videos = self._get_channel_videos_bulk(channel_name, max_videos)
            if not videos:
                return {'success': False, 'error': 'No videos found or failed to fetch channel content'}
                
            download_path = self.get_download_path(self.platform, channel_name)
            total_videos = len(videos)
            downloaded_count = 0
            
            # Process in batches for efficiency
            batch_size = 10
            for batch_start in range(0, total_videos, batch_size):
                batch_end = min(batch_start + batch_size, total_videos)
                batch_videos = videos[batch_start:batch_end]
                
                for i, video_info in enumerate(batch_videos):
                    try:
                        current_index = batch_start + i
                        if progress_callback:
                            progress = int((current_index / total_videos) * 100)
                            progress_callback(progress)
                            
                        result = self._download_video_media(video_info, download_path)
                        
                        if result.get('success', False):
                            downloaded_count += 1
                            
                        # Rate limiting for adult content sites
                        time.sleep(3)
                        
                    except Exception as e:
                        logging.warning(f"Failed to download video {video_info.get('id', 'unknown')}: {e}")
                        continue
                
                # Batch delay to avoid rate limiting
                time.sleep(5)
                    
            if progress_callback:
                progress_callback(100)
                
            return {
                'success': True,
                'files_downloaded': downloaded_count,
                'total_videos': total_videos
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    def _extract_channel_name(self, url: str) -> str:
        """Extract channel/user name from XVideos URL."""
        try:
            if '/channels/' in url:
                return url.split('/channels/')[-1].split('/')[0]
            elif '/profiles/' in url:
                return url.split('/profiles/')[-1].split('/')[0]
            elif '/pornstar/' in url:
                return url.split('/pornstar/')[-1].split('/')[0]
            return ""
        except:
            return ""
            
    def _get_video_info(self, url: str) -> Dict[str, Any]:
        """Get information about an XVideos video."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': self.base_url
            }
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract video information
            video_id = self._extract_video_id(url)
            title = self._extract_title(soup)
            video_url = self._extract_video_url(soup, response.text)
            
            if not video_url:
                return {}
                
            return {
                'id': video_id,
                'title': title,
                'url': video_url,
                'source_url': url,
                'platform': self.platform
            }
            
        except Exception as e:
            logging.error(f"Error getting video info: {e}")
            return {}
            
    def _get_channel_videos_bulk(self, channel_name: str, max_videos: int = 0) -> List[Dict[str, Any]]:
        """Get all videos from channel with pagination."""
        try:
            videos = []
            page = 0
            total_retrieved = 0
            
            while True:
                if max_videos > 0 and total_retrieved >= max_videos:
                    break
                    
                # Construct channel videos URL
                channel_url = f"{self.base_url}/channels/{channel_name}/videos/{page}"
                
                batch_videos = self._fetch_channel_videos_batch(channel_url)
                
                if not batch_videos:
                    logging.info(f"No more videos available for {channel_name}")
                    break
                    
                videos.extend(batch_videos)
                total_retrieved += len(batch_videos)
                
                logging.info(f"Retrieved {total_retrieved} videos from {channel_name}")
                
                page += 1
                time.sleep(2)  # Rate limiting
                
            logging.info(f"Total retrieved: {len(videos)} videos from {channel_name}")
            return videos[:max_videos] if max_videos > 0 else videos
            
        except Exception as e:
            logging.error(f"Error getting bulk channel videos: {e}")
            return []
            
    def _fetch_channel_videos_batch(self, url: str) -> List[Dict[str, Any]]:
        """Fetch a batch of videos from channel page."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': self.base_url
            }
            
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                return []
                
            soup = BeautifulSoup(response.text, 'html.parser')
            videos = []
            
            # Find video elements (this selector may need adjustment)
            video_elements = soup.find_all('div', class_='thumb-block')
            
            for element in video_elements:
                try:
                    video_link = element.find('a')
                    if video_link:
                        video_url = urljoin(self.base_url, video_link.get('href', ''))
                        title = video_link.get('title', 'Unknown Title')
                        video_id = self._extract_video_id(video_url)
                        
                        videos.append({
                            'id': video_id,
                            'title': title,
                            'source_url': video_url,
                            'platform': self.platform
                        })
                        
                except Exception as e:
                    logging.warning(f"Error parsing video element: {e}")
                    continue
                    
            return videos
            
        except Exception as e:
            logging.error(f"Error fetching video batch: {e}")
            return []
            
    def _extract_video_id(self, url: str) -> str:
        """Extract video ID from XVideos URL."""
        try:
            if '/video' in url:
                # Extract from URL pattern like /video12345/title
                match = re.search(r'/video(\d+)/', url)
                if match:
                    return match.group(1)
            return "unknown"
        except:
            return "unknown"
            
    def _extract_title(self, soup) -> str:
        """Extract video title from page."""
        try:
            title_element = soup.find('meta', property='og:title')
            if title_element:
                return title_element.get('content', 'Unknown Title')
                
            title_element = soup.find('title')
            if title_element:
                return title_element.text.strip()
                
            return 'Unknown Title'
        except:
            return 'Unknown Title'
            
    def _extract_video_url(self, soup, page_content: str) -> str:
        """Extract actual video URL from page."""
        try:
            # Look for video URL patterns in JavaScript
            patterns = [
                r'html5player\.setVideoUrlLow\([\'"]([^\'"]+)[\'"]',
                r'html5player\.setVideoUrlHigh\([\'"]([^\'"]+)[\'"]',
                r'html5player\.setVideoHLS\([\'"]([^\'"]+)[\'"]',
                r'setVideoUrl\([\'"]([^\'"]+)[\'"]'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, page_content)
                if match:
                    return match.group(1).replace('\\', '')
                    
            return ""
            
        except Exception as e:
            logging.error(f"Error extracting video URL: {e}")
            return ""
            
    def _download_video_media(self, video_info: Dict[str, Any], download_path: str, 
                            progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        """Download video media."""
        try:
            video_id = video_info.get('id', 'unknown')
            title = self.sanitize_filename(video_info.get('title', f'video_{video_id}'))
            
            # Get actual video URL if not already extracted
            video_url = video_info.get('url')
            if not video_url:
                video_url = self._extract_video_url_from_source(video_info.get('source_url', ''))
                
            if not video_url:
                return {'success': False, 'error': 'No video URL found'}
                
            # Generate filename
            filename = f"{title}.mp4"
            output_path = os.path.join(download_path, filename)
            
            if self.file_exists(output_path):
                return {'success': True, 'output_file': output_path, 'skipped': True}
                
            if self._download_file(video_url, output_path, progress_callback):
                return {'success': True, 'output_file': output_path}
            else:
                return {'success': False, 'error': 'Failed to download file'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    def _extract_video_url_from_source(self, source_url: str) -> str:
        """Extract video URL from source page."""
        try:
            video_info = self._get_video_info(source_url)
            return video_info.get('url', '')
        except:
            return ""
            
    def _download_file(self, url: str, output_path: str, 
                      progress_callback: Optional[Callable[[int], None]] = None) -> bool:
        """Download a file from URL."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': self.base_url
            }
            
            response = requests.get(url, headers=headers, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        if progress_callback and total_size > 0:
                            progress = int((downloaded_size / total_size) * 100)
                            progress_callback(progress)
                            
            return True
            
        except Exception as e:
            logging.error(f"Error downloading file {url}: {e}")
            if os.path.exists(output_path):
                os.remove(output_path)
            return False
