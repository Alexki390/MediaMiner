"""
TikTok downloader with slideshow processing.
"""

import os
import logging
import requests
import json
import time
import asyncio
from typing import Dict, Any, Callable, Optional, List
from urllib.parse import urlparse
from pathlib import Path

from .base_downloader import BaseDownloader
from utils.media_processor import MediaProcessor
from utils.auth_manager import AuthManager
from utils.error_handler import ErrorHandler

try:
    from tiktokapipy.async_api import AsyncTikTokAPI
    from tiktokapipy.models.video import Video
    from tiktokapipy.models.user import User
    TIKTOK_API_AVAILABLE = True
except ImportError:
    TIKTOK_API_AVAILABLE = False
    
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    import undetected_chromedriver as uc
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

class TikTokDownloader(BaseDownloader):
    """TikTok content downloader with slideshow support."""
    
    def __init__(self, config_manager):
        super().__init__(config_manager)
        self.platform = "tiktok"
        self.media_processor = MediaProcessor(config_manager)
        self.auth_manager = AuthManager(config_manager)
        self.error_handler = ErrorHandler(config_manager)
        
        # Enhanced session management
        self.session = requests.Session()
        self.browser_driver = None
        self.api_client = None
        
        # Configuration for private accounts
        self.use_browser = True
        self.use_api = TIKTOK_API_AVAILABLE
        self.max_retries = 3
        self.request_delay = 2.0
        
        # Initialize session
        self._setup_session()
        
    def download(self, url: str, options: Dict[str, Any], 
                progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        """Download TikTok content."""
        try:
            self.log_download_start(self.platform, url)
            
            # Determine if it's a username or video URL
            if self._is_video_url(url):
                result = self._download_single_video(url, options, progress_callback)
            else:
                result = self._download_user_content(url, options, progress_callback)
                
            if result['success']:
                self.log_download_complete(self.platform, url, result.get('files_downloaded', 0))
            else:
                self.log_download_error(self.platform, url, result.get('error', 'Unknown error'))
                
            return result
            
        except Exception as e:
            error_msg = f"TikTok download failed: {str(e)}"
            self.log_download_error(self.platform, url, error_msg)
            return {'success': False, 'error': error_msg}
            
    def download_user_content(self, username: str, options: Dict[str, Any], 
                             progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        """Download all content from a TikTok user."""
        try:
            self.log_download_start(self.platform, f"@{username}")
            
            # Clean username
            username = username.replace('@', '').strip()
            max_videos = options.get('limit', 0)  # 0 = unlimited
            
            # Get user's videos with pagination
            videos = self._get_user_videos(username, max_videos)
            if not videos:
                return {'success': False, 'error': 'No videos found or failed to fetch user content'}
            
            download_path = self.get_download_path(self.platform, username)
            total_videos = len(videos)
            downloaded_count = 0
            
            for i, video_url in enumerate(videos):
                try:
                    if progress_callback:
                        progress = int((i / total_videos) * 100)
                        progress_callback(progress)
                    
                    result = self.download(video_url, options)
                    if result.get('success', False):
                        downloaded_count += result.get('files_downloaded', 0)
                    
                    # Rate limiting
                    time.sleep(3)
                    
                except Exception as e:
                    logging.warning(f"Failed to download video {video_url}: {e}")
                    continue
            
            if progress_callback:
                progress_callback(100)
                
            self.log_download_complete(self.platform, f"@{username}", downloaded_count)
            return {
                'success': True,
                'files_downloaded': downloaded_count,
                'total_videos': total_videos
            }
            
        except Exception as e:
            error_msg = f"TikTok user download failed: {str(e)}"
            self.log_download_error(self.platform, f"@{username}", error_msg)
            return {'success': False, 'error': error_msg}
            
    def _get_user_videos(self, username: str, max_videos: int = 0) -> List[str]:
        """Get all video URLs from a TikTok user."""
        try:
            videos = []
            cursor = 0
            count = 50  # TikTok API limit per request
            
            while True:
                if max_videos > 0 and len(videos) >= max_videos:
                    break
                
                # This would use TikTok API or scraping
                # For now, placeholder implementation
                batch_videos = self._fetch_user_videos_batch(username, cursor, count)
                
                if not batch_videos:
                    break
                
                videos.extend(batch_videos)
                cursor += count
                
                # Rate limiting
                time.sleep(2)
                
                # If we got fewer videos than requested, we've reached the end
                if len(batch_videos) < count:
                    break
            
            if max_videos > 0:
                videos = videos[:max_videos]
                
            return videos
            
        except Exception as e:
            logging.error(f"Error getting user videos: {e}")
            return []
            
    def _fetch_user_videos_batch(self, username: str, cursor: int, count: int) -> List[str]:
        """Fetch a batch of videos from user profile."""
        try:
            # Placeholder - would implement actual TikTok API/scraping
            logging.warning("User videos fetching requires TikTok API integration")
            return []
        except Exception as e:
            logging.error(f"Error fetching video batch: {e}")
            return []
            
    def _is_video_url(self, url: str) -> bool:
        """Check if the URL is a TikTok video URL."""
        return 'tiktok.com' in url and ('/video/' in url or '/v/' in url or '@' in url)
        
    def _download_single_video(self, url: str, options: Dict[str, Any], 
                             progress_callback: Optional[Callable[[int], None]]) -> Dict[str, Any]:
        """Download a single TikTok video."""
        try:
            # Get video info
            video_info = self._get_video_info(url)
            if not video_info:
                return {'success': False, 'error': 'Failed to get video information'}
                
            download_path = self.get_download_path(self.platform)
            
            if video_info.get('is_slideshow', False) and options.get('process_slideshows', True):
                # Handle slideshow
                result = self._download_slideshow(video_info, download_path, progress_callback)
            else:
                # Handle regular video
                result = self._download_regular_video(video_info, download_path, progress_callback)
                
            return result
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    def _download_user_content(self, username: str, options: Dict[str, Any], 
                             progress_callback: Optional[Callable[[int], None]]) -> Dict[str, Any]:
        """Download content from a TikTok user."""
        try:
            # Clean username
            username = username.replace('@', '').strip()
            
            # Get user's videos
            videos = self._get_user_videos(username, options.get('limit', 50))
            if not videos:
                return {'success': False, 'error': 'No videos found or failed to fetch user content'}
                
            download_path = self.get_download_path(self.platform, username)
            total_videos = len(videos)
            downloaded_count = 0
            
            for i, video_info in enumerate(videos):
                try:
                    if progress_callback:
                        progress = int((i / total_videos) * 100)
                        progress_callback(progress)
                        
                    if video_info.get('is_slideshow', False) and options.get('process_slideshows', True):
                        result = self._download_slideshow(video_info, download_path)
                    else:
                        result = self._download_regular_video(video_info, download_path)
                        
                    if result.get('success', False):
                        downloaded_count += 1
                        
                    # Small delay to avoid rate limiting
                    time.sleep(1)
                    
                except Exception as e:
                    logging.warning(f"Failed to download video {video_info.get('id', 'unknown')}: {e}")
                    continue
                    
            if progress_callback:
                progress_callback(100)
                
            return {
                'success': True,
                'files_downloaded': downloaded_count,
                'total_videos': total_videos
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    def _setup_session(self):
        """Setup enhanced session for TikTok with proper headers."""
        try:
            # Enhanced headers to mimic real browser
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0'
            })
            
            # Load existing cookies if available
            self._load_session_cookies()
            
        except Exception as e:
            logging.error(f"Failed to setup TikTok session: {e}")
            
    def _load_session_cookies(self):
        """Load saved session cookies."""
        try:
            session_data = self.auth_manager.get_session('tiktok')
            if session_data and 'cookies' in session_data:
                for cookie in session_data['cookies']:
                    self.session.cookies.set(**cookie)
                logging.info("Loaded TikTok session cookies")
        except Exception as e:
            logging.warning(f"Failed to load TikTok cookies: {e}")
            
    def login_with_credentials(self, username: str, password: str) -> bool:
        """Login to TikTok with credentials for private account access."""
        try:
            if not SELENIUM_AVAILABLE:
                logging.error("Selenium not available for TikTok login")
                return False
                
            # Setup Chrome driver for login
            chrome_options = Options()
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Use undetected Chrome driver
            self.browser_driver = uc.Chrome(options=chrome_options)
            self.browser_driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Navigate to login page
            self.browser_driver.get('https://www.tiktok.com/login')
            time.sleep(3)
            
            # Find and fill login form
            try:
                # Click on "Use phone / email / username"
                login_link = WebDriverWait(self.browser_driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'Use phone / email / username')]"))
                )
                login_link.click()
                time.sleep(2)
                
                # Fill username
                username_field = WebDriverWait(self.browser_driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "username"))
                )
                username_field.clear()
                username_field.send_keys(username)
                
                # Fill password
                password_field = self.browser_driver.find_element(By.NAME, "password")
                password_field.clear()
                password_field.send_keys(password)
                
                # Click login button
                login_button = self.browser_driver.find_element(By.XPATH, "//button[@type='submit']")
                login_button.click()
                
                # Wait for login to complete
                time.sleep(5)
                
                # Check if login was successful
                if "tiktok.com/foryou" in self.browser_driver.current_url or "tiktok.com/following" in self.browser_driver.current_url:
                    # Save session cookies
                    cookies = self.browser_driver.get_cookies()
                    session_data = {
                        'cookies': cookies,
                        'user_agent': self.session.headers['User-Agent']
                    }
                    
                    self.auth_manager.create_session('tiktok', session_data, expires_in=7200)  # 2 hours
                    
                    # Update requests session with cookies
                    for cookie in cookies:
                        self.session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])
                        
                    logging.info(f"Successfully logged into TikTok as {username}")
                    return True
                else:
                    logging.error("TikTok login failed - not redirected to main page")
                    return False
                    
            except Exception as e:
                logging.error(f"Error during TikTok login process: {e}")
                return False
                
        except Exception as e:
            logging.error(f"TikTok login failed: {e}")
            return False
        finally:
            if self.browser_driver:
                self.browser_driver.quit()
                self.browser_driver = None
                
    def _get_user_videos_enhanced(self, username: str, limit: int) -> List[Dict[str, Any]]:
        """Enhanced method to get user videos including private accounts."""
        try:
            videos = []
            
            # Method 1: Try API if available
            if self.use_api and TIKTOK_API_AVAILABLE:
                try:
                    videos = asyncio.run(self._get_videos_via_api(username, limit))
                    if videos:
                        return videos
                except Exception as e:
                    logging.warning(f"API method failed: {e}")
            
            # Method 2: Try browser scraping
            if self.use_browser and SELENIUM_AVAILABLE:
                try:
                    videos = self._get_videos_via_browser(username, limit)
                    if videos:
                        return videos
                except Exception as e:
                    logging.warning(f"Browser method failed: {e}")
            
            # Method 3: Try requests with session
            try:
                videos = self._get_videos_via_requests(username, limit)
                if videos:
                    return videos
            except Exception as e:
                logging.warning(f"Requests method failed: {e}")
                
            return videos
            
        except Exception as e:
            logging.error(f"Error getting user videos: {e}")
            return []
            
    async def _get_videos_via_api(self, username: str, limit: int) -> List[Dict[str, Any]]:
        """Get videos using TikTok API."""
        try:
            async with AsyncTikTokAPI() as api:
                user = await api.user(username)
                videos = []
                
                async for video in user.videos(count=limit):
                    video_info = {
                        'id': video.id,
                        'url': f"https://www.tiktok.com/@{username}/video/{video.id}",
                        'title': video.desc or f"TikTok_{video.id}",
                        'author': username,
                        'duration': getattr(video, 'duration', 0),
                        'is_slideshow': hasattr(video, 'image_post') and video.image_post,
                        'video_url': getattr(video, 'video', {}).get('download_addr') if hasattr(video, 'video') else None,
                        'images': [],
                        'audio_url': getattr(video, 'music', {}).get('play_url') if hasattr(video, 'music') else None,
                        'stats': {
                            'likes': getattr(video.stats, 'digg_count', 0) if hasattr(video, 'stats') else 0,
                            'comments': getattr(video.stats, 'comment_count', 0) if hasattr(video, 'stats') else 0,
                            'shares': getattr(video.stats, 'share_count', 0) if hasattr(video, 'stats') else 0,
                            'plays': getattr(video.stats, 'play_count', 0) if hasattr(video, 'stats') else 0
                        }
                    }
                    
                    # Handle slideshow images
                    if video_info['is_slideshow'] and hasattr(video, 'image_post') and video.image_post:
                        for image in video.image_post.images:
                            video_info['images'].append(image.image_url.url_list[0])
                    
                    videos.append(video_info)
                    
                return videos
                
        except Exception as e:
            logging.error(f"API video fetching failed: {e}")
            return []

    def _get_video_info(self, url: str) -> Dict[str, Any]:
        """Get information about a TikTok video."""
        try:
            # This is a simplified implementation
            # In a real application, you would use a proper TikTok API or scraper
            
            # For now, we'll use a basic approach with requests
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            # Extract basic info from HTML (simplified)
            html_content = response.text
            
            # This is a mock implementation - in reality you'd parse the HTML/JSON properly
            video_info = {
                'id': self._extract_video_id(url),
                'url': url,
                'title': self._extract_title_from_html(html_content),
                'is_slideshow': self._is_slideshow_from_html(html_content),
                'video_url': self._extract_video_url_from_html(html_content),
                'images': self._extract_slideshow_images(html_content) if self._is_slideshow_from_html(html_content) else [],
                'audio_url': self._extract_audio_url_from_html(html_content)
            }
            
            return video_info
            
        except Exception as e:
            logging.error(f"Error getting video info: {e}")
            return {}
            
    def _get_user_videos(self, username: str, limit: int) -> List[Dict[str, Any]]:
        """Get videos from a TikTok user."""
        try:
            # This is a simplified implementation
            # In a real application, you would use a proper TikTok API
            
            videos = []
            # Mock implementation - in reality you'd scrape or use API
            
            # For demonstration, we'll return empty list with error message
            logging.warning("User video fetching not fully implemented - requires proper TikTok API integration")
            return []
            
        except Exception as e:
            logging.error(f"Error getting user videos: {e}")
            return []
            
    def _download_slideshow(self, video_info: Dict[str, Any], download_path: str, 
                          progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        """Download and process a TikTok slideshow."""
        try:
            video_id = video_info['id']
            title = self.sanitize_filename(video_info.get('title', f'slideshow_{video_id}'))
            
            # Create temporary directory for slideshow assets
            temp_dir = os.path.join(download_path, f'temp_{video_id}')
            os.makedirs(temp_dir, exist_ok=True)
            
            try:
                # Download images
                image_paths = []
                images = video_info.get('images', [])
                
                if not images:
                    return {'success': False, 'error': 'No images found in slideshow'}
                    
                for i, image_url in enumerate(images):
                    image_filename = f'slide_{i+1:03d}.jpg'
                    image_path = os.path.join(temp_dir, image_filename)
                    
                    if self._download_file(image_url, image_path):
                        image_paths.append(image_path)
                        
                    if progress_callback:
                        progress = int((i / len(images)) * 50)  # 50% for images
                        progress_callback(progress)
                        
                # Download audio
                audio_url = video_info.get('audio_url')
                audio_path = None
                
                if audio_url:
                    audio_path = os.path.join(temp_dir, 'audio.mp3')
                    self._download_file(audio_url, audio_path)
                    
                if progress_callback:
                    progress_callback(75)  # 75% after audio download
                    
                # Create video from slideshow
                output_path = os.path.join(download_path, f'{title}.mp4')
                
                if self.media_processor.create_slideshow_video(image_paths, audio_path, output_path):
                    if progress_callback:
                        progress_callback(100)
                        
                    return {'success': True, 'output_file': output_path}
                else:
                    return {'success': False, 'error': 'Failed to create slideshow video'}
                    
            finally:
                # Clean up temporary files
                self._cleanup_temp_dir(temp_dir)
                
        except Exception as e:
            return {'success': False, 'error': f'Slideshow processing failed: {str(e)}'}
            
    def _download_regular_video(self, video_info: Dict[str, Any], download_path: str, 
                              progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        """Download a regular TikTok video."""
        try:
            video_id = video_info['id']
            title = self.sanitize_filename(video_info.get('title', f'video_{video_id}'))
            video_url = video_info.get('video_url')
            
            if not video_url:
                return {'success': False, 'error': 'No video URL found'}
                
            output_path = os.path.join(download_path, f'{title}.mp4')
            
            if self.file_exists(output_path):
                return {'success': True, 'output_file': output_path, 'skipped': True}
                
            if self._download_file(video_url, output_path, progress_callback):
                return {'success': True, 'output_file': output_path}
            else:
                return {'success': False, 'error': 'Failed to download video file'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    def _download_file(self, url: str, output_path: str, 
                      progress_callback: Optional[Callable[[int], None]] = None) -> bool:
        """Download a file from URL."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
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
            
    def _extract_video_id(self, url: str) -> str:
        """Extract video ID from TikTok URL."""
        # Simplified extraction
        if '/video/' in url:
            return url.split('/video/')[-1].split('?')[0]
        return str(hash(url))  # Fallback
        
    def _extract_title_from_html(self, html: str) -> str:
        """Extract video title from HTML."""
        # Simplified extraction - in reality you'd parse JSON-LD or meta tags
        try:
            if '<title>' in html:
                start = html.find('<title>') + 7
                end = html.find('</title>', start)
                return html[start:end].strip()
        except:
            pass
        return "TikTok Video"
        
    def _is_slideshow_from_html(self, html: str) -> bool:
        """Determine if video is a slideshow from HTML content."""
        # Simplified detection
        return 'slideshow' in html.lower() or 'carousel' in html.lower()
        
    def _extract_video_url_from_html(self, html: str) -> str:
        """Extract video URL from HTML."""
        # This would require proper HTML parsing in a real implementation
        # For now, return empty string
        return ""
        
    def _extract_slideshow_images(self, html: str) -> List[str]:
        """Extract slideshow image URLs from HTML."""
        # This would require proper HTML parsing in a real implementation
        return []
        
    def _extract_audio_url_from_html(self, html: str) -> str:
        """Extract audio URL from HTML."""
        # This would require proper HTML parsing in a real implementation
        return ""
        
    def _cleanup_temp_dir(self, temp_dir: str):
        """Clean up temporary directory."""
        try:
            import shutil
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        except Exception as e:
            logging.warning(f"Failed to clean up temp directory {temp_dir}: {e}")
