"""
Redgifs downloader for adult GIF content.
"""

import os
import logging
import requests
import json
import time
from typing import Dict, Any, Callable, Optional, List
from urllib.parse import urlparse

from .base_downloader import BaseDownloader

class RedgifsDownloader(BaseDownloader):
    """Redgifs content downloader."""
    
    def __init__(self, config_manager):
        super().__init__(config_manager)
        self.platform = "redgifs"
        self.api_base = "https://api.redgifs.com/v2"
        
    def download(self, url: str, options: Dict[str, Any], 
                progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        """Download Redgifs content."""
        try:
            self.log_download_start(self.platform, url)
            
            # Determine if it's a single GIF or user profile
            if self._is_gif_url(url):
                result = self._download_single_gif(url, options, progress_callback)
            else:
                result = self._download_user_content(url, options, progress_callback)
                
            if result['success']:
                self.log_download_complete(self.platform, url, result.get('files_downloaded', 0))
            else:
                self.log_download_error(self.platform, url, result.get('error', 'Unknown error'))
                
            return result
            
        except Exception as e:
            error_msg = f"Redgifs download failed: {str(e)}"
            self.log_download_error(self.platform, url, error_msg)
            return {'success': False, 'error': error_msg}
            
    def _is_gif_url(self, url: str) -> bool:
        """Check if the URL is a single GIF URL."""
        return 'redgifs.com/watch/' in url or 'redgifs.com/i/' in url
        
    def _download_single_gif(self, url: str, options: Dict[str, Any], 
                           progress_callback: Optional[Callable[[int], None]]) -> Dict[str, Any]:
        """Download a single Redgifs GIF."""
        try:
            # Extract GIF ID from URL
            gif_id = self._extract_gif_id(url)
            if not gif_id:
                return {'success': False, 'error': 'Could not extract GIF ID from URL'}
                
            # Get GIF info
            gif_info = self._get_gif_info(gif_id)
            if not gif_info:
                return {'success': False, 'error': 'Failed to get GIF information'}
                
            download_path = self.get_download_path(self.platform)
            
            # Download the GIF
            result = self._download_gif_media(gif_info, download_path, progress_callback)
            return result
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    def _download_user_content(self, username: str, options: Dict[str, Any], 
                             progress_callback: Optional[Callable[[int], None]]) -> Dict[str, Any]:
        """Download content from a Redgifs user."""
        try:
            # Clean username
            username = username.replace('@', '').strip()
            if 'redgifs.com/users/' in username:
                username = username.split('/')[-1]
                
            # Get user's GIFs
            gifs = self._get_user_gifs(username, options.get('limit', 50))
            if not gifs:
                return {'success': False, 'error': 'No GIFs found or failed to fetch user content'}
                
            download_path = self.get_download_path(self.platform, username)
            total_gifs = len(gifs)
            downloaded_count = 0
            
            for i, gif_info in enumerate(gifs):
                try:
                    if progress_callback:
                        progress = int((i / total_gifs) * 100)
                        progress_callback(progress)
                        
                    result = self._download_gif_media(gif_info, download_path)
                    
                    if result.get('success', False):
                        downloaded_count += 1
                        
                    # Rate limiting
                    time.sleep(2)
                    
                except Exception as e:
                    logging.warning(f"Failed to download GIF {gif_info.get('id', 'unknown')}: {e}")
                    continue
                    
            if progress_callback:
                progress_callback(100)
                
            return {
                'success': True,
                'files_downloaded': downloaded_count,
                'total_gifs': total_gifs
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    def _extract_gif_id(self, url: str) -> str:
        """Extract GIF ID from Redgifs URL."""
        try:
            if '/watch/' in url:
                return url.split('/watch/')[-1].split('?')[0]
            elif '/i/' in url:
                return url.split('/i/')[-1].split('?')[0]
            return ""
        except:
            return ""
            
    def _get_gif_info(self, gif_id: str) -> Dict[str, Any]:
        """Get information about a Redgifs GIF."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Try to get GIF info from API
            api_url = f"{self.api_base}/gifs/{gif_id}"
            response = requests.get(api_url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if 'gif' in data:
                    gif_data = data['gif']
                    return {
                        'id': gif_data.get('id', gif_id),
                        'title': gif_data.get('tags', gif_id),
                        'urls': gif_data.get('urls', {}),
                        'duration': gif_data.get('duration', 0),
                        'width': gif_data.get('width', 0),
                        'height': gif_data.get('height', 0)
                    }
            
            # Fallback: try direct URL parsing
            return {
                'id': gif_id,
                'title': f'redgifs_{gif_id}',
                'urls': {
                    'hd': f'https://thumbs2.redgifs.com/{gif_id}.mp4',
                    'sd': f'https://thumbs2.redgifs.com/{gif_id}-mobile.mp4'
                }
            }
            
        except Exception as e:
            logging.error(f"Error getting GIF info: {e}")
            return {}
            
    def _get_user_gifs(self, username: str, limit: int = 0) -> List[Dict[str, Any]]:
        """Get all GIFs from a Redgifs user with unlimited pagination."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            gifs = []
            page = 1
            per_page = 80  # API limit
            total_retrieved = 0
            
            while True:
                # Break if we've reached the limit
                if limit > 0 and total_retrieved >= limit:
                    break
                    
                api_url = f"{self.api_base}/users/{username}/gifs"
                params = {
                    'page': page,
                    'count': per_page
                }
                
                response = requests.get(api_url, headers=headers, params=params)
                
                if response.status_code != 200:
                    logging.info(f"No more GIFs available for {username} (page {page})")
                    break
                    
                data = response.json()
                page_gifs = data.get('gifs', [])
                
                if not page_gifs:
                    logging.info(f"Reached end of GIFs for {username}")
                    break
                    
                for gif_data in page_gifs:
                    if limit > 0 and len(gifs) >= limit:
                        break
                        
                    gif_info = {
                        'id': gif_data.get('id'),
                        'title': gif_data.get('tags', gif_data.get('id', 'unknown')),
                        'urls': gif_data.get('urls', {}),
                        'duration': gif_data.get('duration', 0),
                        'width': gif_data.get('width', 0),
                        'height': gif_data.get('height', 0),
                        'thumbnail': gif_data.get('thumbnail', {}),
                        'created_at': gif_data.get('createDate', '')
                    }
                    gifs.append(gif_info)
                    total_retrieved += 1
                    
                logging.info(f"Retrieved {len(page_gifs)} GIFs from page {page} of {username}")
                page += 1
                time.sleep(1)  # Rate limiting
                
            logging.info(f"Total retrieved: {len(gifs)} GIFs from {username}")
            return gifs
            
        except Exception as e:
            logging.error(f"Error getting user GIFs: {e}")
            return []
            
    def _download_gif_media(self, gif_info: Dict[str, Any], download_path: str, 
                          progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        """Download media from a GIF."""
        try:
            gif_id = gif_info['id']
            title = self.sanitize_filename(gif_info.get('title', f'gif_{gif_id}'))
            urls = gif_info.get('urls', {})
            
            # Try HD first, then SD
            video_url = urls.get('hd') or urls.get('sd')
            
            if not video_url:
                return {'success': False, 'error': 'No video URL found'}
                
            # Determine file extension from URL
            extension = 'mp4' if '.mp4' in video_url else 'gif'
            output_path = os.path.join(download_path, f'{title}.{extension}')
            
            if self.file_exists(output_path):
                return {'success': True, 'output_file': output_path, 'skipped': True}
                
            if self._download_file(video_url, output_path, progress_callback):
                return {'success': True, 'output_file': output_path}
            else:
                return {'success': False, 'error': 'Failed to download file'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    def _download_file(self, url: str, output_path: str, 
                      progress_callback: Optional[Callable[[int], None]] = None) -> bool:
        """Download a file from URL."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://www.redgifs.com/'
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