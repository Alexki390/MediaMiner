"""
Kwai.com downloader for short videos with profile support.
"""

import os
import logging
import requests
import time
import re
import json
from typing import Dict, Any, Callable, Optional, List
from urllib.parse import urlparse, urljoin, quote
from bs4 import BeautifulSoup
try:
    import cloudscraper
except ImportError:
    cloudscraper = None

from .base_downloader import BaseDownloader
from utils.protection_bypass import ProtectionBypass
from utils.error_handler import ErrorHandler

class KwaiDownloader(BaseDownloader):
    """Kwai content downloader with profile support."""

    def __init__(self, config_manager):
        super().__init__(config_manager)
        self.platform = "kwai"
        self.protection_bypass = ProtectionBypass()
        self.error_handler = ErrorHandler()
        if cloudscraper:
            self.scraper = cloudscraper.create_scraper()
        else:
            self.scraper = requests.Session()
            self.scraper.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })

        # Rate limiting
        self.rate_limit = 10  # requests per minute
        self.delay = 6       # seconds between requests

        # API endpoints
        self.api_base = "https://www.kwai.com/rest/"

    def download(self, url: str, options: Dict[str, Any], 
                progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        """Download content from Kwai."""
        try:
            self.log_download_start(self.platform, url)

            # Parse URL to determine content type
            if '/profile/' in url or '/u/' in url:
                result = self._download_user_profile(url, options, progress_callback)
            elif '/short/' in url or '/video/' in url:
                result = self._download_single_video(url, options, progress_callback)
            else:
                # Try to detect user from URL
                result = self._download_user_profile(url, options, progress_callback)

            if result['success']:
                self.log_download_complete(self.platform, url, result.get('files_downloaded', 0))
            else:
                self.log_download_error(self.platform, url, result.get('error', 'Unknown error'))

            return result

        except Exception as e:
            error_msg = f"Kwai download failed: {str(e)}"
            self.log_download_error(self.platform, url, error_msg)
            return self.error_handler.handle_error(e, "kwai_download", {"url": url})

    def _download_user_profile(self, url: str, options: Dict[str, Any], 
                              progress_callback: Optional[Callable[[int], None]]) -> Dict[str, Any]:
        """Download all videos from a Kwai user profile."""
        try:
            max_videos = options.get('limit', 50)

            # Extract user ID from URL
            user_id = self._extract_user_id(url)
            if not user_id:
                return {'success': False, 'error': 'Could not extract user ID from URL'}

            # Get user videos
            videos = self._get_user_videos(user_id, max_videos)
            if not videos:
                return {'success': False, 'error': 'No videos found for user'}

            # Download videos
            download_path = self.get_download_path('kwai', f"user_{user_id}")
            downloaded_count = 0

            for i, video in enumerate(videos):
                try:
                    video_url = video.get('playUrl') or video.get('videoUrl')
                    if not video_url:
                        continue

                    title = video.get('title', f'kwai_video_{i+1}')
                    filename = f"{self.sanitize_filename(title)}.mp4"
                    output_path = os.path.join(download_path, filename)

                    if not self.file_exists(output_path):
                        if self._download_video_file(video_url, output_path):
                            downloaded_count += 1
                    else:
                        downloaded_count += 1

                    if progress_callback:
                        progress = int(((i + 1) / len(videos)) * 100)
                        progress_callback(progress)

                    # Rate limiting
                    time.sleep(self.delay)

                except Exception as e:
                    logging.warning(f"Failed to download video {i+1}: {e}")
                    continue

            return {
                'success': True,
                'files_downloaded': downloaded_count,
                'total_videos': len(videos),
                'user_id': user_id
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _download_single_video(self, url: str, options: Dict[str, Any], 
                              progress_callback: Optional[Callable[[int], None]]) -> Dict[str, Any]:
        """Download single Kwai video."""
        try:
            video_id = self._extract_video_id(url)
            if not video_id:
                return {'success': False, 'error': 'Could not extract video ID from URL'}

            # Get video info
            video_info = self._get_video_info(video_id)
            if not video_info:
                return {'success': False, 'error': 'Could not get video information'}

            video_url = video_info.get('playUrl') or video_info.get('videoUrl')
            if not video_url:
                return {'success': False, 'error': 'Could not extract video URL'}

            title = video_info.get('title', f'kwai_video_{video_id}')
            filename = f"{self.sanitize_filename(title)}.mp4"

            download_path = self.get_download_path('kwai')
            output_path = os.path.join(download_path, filename)

            if self.file_exists(output_path):
                return {'success': True, 'output_file': output_path, 'skipped': True}

            if self._download_video_file(video_url, output_path, progress_callback):
                return {'success': True, 'output_file': output_path}
            else:
                return {'success': False, 'error': 'Failed to download video'}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _extract_user_id(self, url: str) -> Optional[str]:
        """Extract user ID from Kwai URL."""
        patterns = [
            r'/profile/([^/?]+)',
            r'/u/([^/?]+)',
            r'user[_-]id[=:]([^&/?]+)',
            r'userId[=:]([^&/?]+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        return None

    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from Kwai URL."""
        patterns = [
            r'/short/([^/?]+)',
            r'/video/([^/?]+)',
            r'photoId[=:]([^&/?]+)',
            r'video[_-]id[=:]([^&/?]+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        return None

    def _get_user_videos(self, user_id: str, max_videos: int) -> List[Dict]:
        """Get videos from user profile."""
        try:
            videos = []
            cursor = ""

            while len(videos) < max_videos:
                api_url = f"{self.api_base}n/feed/profile"
                params = {
                    'userId': user_id,
                    'count': min(20, max_videos - len(videos)),
                    'cursor': cursor
                }

                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'application/json'
                }

                response = self.scraper.get(api_url, params=params, headers=headers, timeout=30)
                response.raise_for_status()

                data = response.json()

                if not data.get('data') or not data['data'].get('feeds'):
                    break

                feeds = data['data']['feeds']
                for feed in feeds:
                    if len(videos) >= max_videos:
                        break

                    video_info = {
                        'playUrl': feed.get('photo', {}).get('photoUrl'),
                        'title': feed.get('photo', {}).get('caption', ''),
                        'id': feed.get('photo', {}).get('id')
                    }
                    videos.append(video_info)

                # Check for next page
                cursor = data['data'].get('cursor')
                if not cursor or not feeds:
                    break

                time.sleep(self.delay)

            return videos

        except Exception as e:
            logging.error(f"Error getting user videos: {e}")
            return []

    def _get_video_info(self, video_id: str) -> Optional[Dict]:
        """Get single video information."""
        try:
            api_url = f"{self.api_base}n/photo/info"
            params = {'photoId': video_id}

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json'
            }

            response = self.scraper.get(api_url, params=params, headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json()

            if data.get('data') and data['data'].get('photo'):
                photo = data['data']['photo']
                return {
                    'playUrl': photo.get('photoUrl'),
                    'title': photo.get('caption', ''),
                    'id': photo.get('id')
                }

            return None

        except Exception as e:
            logging.error(f"Error getting video info: {e}")
            return None

    def _download_video_file(self, url: str, output_path: str, 
                            progress_callback: Optional[Callable[[int], None]] = None) -> bool:
        """Download video file."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://www.kwai.com/'
            }

            response = self.scraper.get(url, headers=headers, stream=True, timeout=60)
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
            logging.error(f"Error downloading video {url}: {e}")
            if os.path.exists(output_path):
                os.remove(output_path)
            return False