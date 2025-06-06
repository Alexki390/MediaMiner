"""
Pornhub downloader for adult video content.
"""

import os
import logging
import requests
import json
import time
import re
from typing import Dict, Any, Callable, Optional, List
from urllib.parse import urlparse, parse_qs

from .base_downloader import BaseDownloader

class PornhubDownloader(BaseDownloader):
    """Pornhub content downloader."""
    
    def __init__(self, config_manager):
        super().__init__(config_manager)
        self.platform = "pornhub"
        
    def download(self, url: str, options: Dict[str, Any], 
                progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        """Download Pornhub content."""
        try:
            self.log_download_start(self.platform, url)
            
            # Determine if it's a single video or user/channel
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
            error_msg = f"Pornhub download failed: {str(e)}"
            self.log_download_error(self.platform, url, error_msg)
            return {'success': False, 'error': error_msg}
            
    def _is_video_url(self, url: str) -> bool:
        """Check if the URL is a single video URL."""
        return 'pornhub.com/view_video.php' in url or '/video/' in url
        
    def _download_single_video(self, url: str, options: Dict[str, Any], 
                             progress_callback: Optional[Callable[[int], None]]) -> Dict[str, Any]:
        """Download a single Pornhub video."""
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
            
    def _download_user_content(self, username: str, options: Dict[str, Any], 
                             progress_callback: Optional[Callable[[int], None]]) -> Dict[str, Any]:
        """Download content from a Pornhub user or channel with unlimited pagination."""
        try:
            # Clean username/channel
            username = username.replace('@', '').strip()
            if 'pornhub.com/' in username:
                username = username.split('/')[-1]
                
            # Get user's videos with unlimited option
            limit = options.get('limit', 0)  # 0 = unlimited
            videos = self._get_user_videos(username, limit)
            
            # Get user's GIFs
            gifs = self._get_user_gifs(username, limit)
            
            # Combine all content
            all_content = videos + gifs
            
            if not all_content:
                return {'success': False, 'error': 'No content found or failed to fetch user content'}
                
            download_path = self.get_download_path(self.platform, username)
            total_content = len(all_content)
            downloaded_count = 0
            
            for i, content_info in enumerate(all_content):
                try:
                    if progress_callback:
                        progress = int((i / total_content) * 100)
                        progress_callback(progress)
                    
                    # Determine content type and download accordingly
                    if content_info.get('type') == 'gif':
                        result = self._download_gif_media(content_info, download_path)
                    else:
                        result = self._download_video_media(content_info, download_path)
                    
                    if result.get('success', False):
                        downloaded_count += 1
                        
                    # Rate limiting
                    time.sleep(2)
                    
                except Exception as e:
                    logging.warning(f"Failed to download content {content_info.get('id', 'unknown')}: {e}")
                    continue
                    
            if progress_callback:
                progress_callback(100)
                
            return {
                'success': True,
                'files_downloaded': downloaded_count,
                'total_videos': len(videos),
                'total_gifs': len(gifs),
                'total_content': total_content
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    def _get_video_info(self, url: str) -> Dict[str, Any]:
        """Get information about a Pornhub video."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            html_content = response.text
            
            # Extract video ID
            video_id = self._extract_video_id(url)
            
            # Extract title
            title_match = re.search(r'<title>([^<]+)</title>', html_content)
            title = title_match.group(1) if title_match else f'video_{video_id}'
            title = title.replace(' - Pornhub.com', '').strip()
            
            # Extract video URLs from player data
            video_urls = self._extract_video_urls(html_content)
            
            return {
                'id': video_id,
                'title': title,
                'url': url,
                'video_urls': video_urls,
                'duration': self._extract_duration(html_content),
                'views': self._extract_views(html_content)
            }
            
        except Exception as e:
            logging.error(f"Error getting video info: {e}")
            return {}
            
    def _get_user_videos(self, username: str, limit: int = 0) -> List[Dict[str, Any]]:
        """Get videos from a Pornhub user with unlimited pagination."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            videos = []
            page = 1
            
            while True:
                # Break if we've reached the limit
                if limit > 0 and len(videos) >= limit:
                    break
                    
                # Try different URL patterns
                user_urls = [
                    f"https://www.pornhub.com/users/{username}/videos?page={page}",
                    f"https://www.pornhub.com/model/{username}?page={page}",
                    f"https://www.pornhub.com/pornstar/{username}?page={page}"
                ]
                
                found_videos = False
                
                for user_url in user_urls:
                    try:
                        response = requests.get(user_url, headers=headers)
                        if response.status_code == 200:
                            page_videos = self._extract_videos_from_page(response.text)
                            if page_videos:
                                # Add videos but respect limit
                                if limit > 0:
                                    remaining = limit - len(videos)
                                    videos.extend(page_videos[:remaining])
                                else:
                                    videos.extend(page_videos)
                                found_videos = True
                                break
                    except:
                        continue
                
                if not found_videos:
                    logging.info(f"No more videos found for {username} on page {page}")
                    break
                    
                logging.info(f"Retrieved {len(videos)} videos so far for {username}")
                page += 1
                time.sleep(2)  # Rate limiting
                
            logging.info(f"Total retrieved: {len(videos)} videos from {username}")
            return videos
            
        except Exception as e:
            logging.error(f"Error getting user videos: {e}")
            return []
            
    def _extract_video_id(self, url: str) -> str:
        """Extract video ID from Pornhub URL."""
        try:
            if 'viewkey=' in url:
                return url.split('viewkey=')[1].split('&')[0]
            elif '/video/' in url:
                return url.split('/video/')[-1].split('?')[0]
            return str(hash(url))  # Fallback
        except:
            return "unknown"
            
    def _extract_video_urls(self, html_content: str) -> Dict[str, str]:
        """Extract video URLs from HTML content."""
        video_urls = {}
        
        try:
            # Look for video URL patterns in JavaScript
            patterns = [
                r'"videoUrl":"([^"]+)"',
                r'videoUrl":"([^"]+)"',
                r'"quality_(\d+)p":"([^"]+)"'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, html_content)
                for match in matches:
                    if isinstance(match, tuple):
                        quality, url = match
                        video_urls[f"{quality}p"] = url.replace('\\/', '/')
                    else:
                        video_urls['default'] = match.replace('\\/', '/')
                        
        except Exception as e:
            logging.warning(f"Error extracting video URLs: {e}")
            
        return video_urls
        
    def _extract_duration(self, html_content: str) -> str:
        """Extract video duration from HTML."""
        try:
            duration_match = re.search(r'"duration":"([^"]+)"', html_content)
            return duration_match.group(1) if duration_match else "unknown"
        except:
            return "unknown"
            
    def _extract_views(self, html_content: str) -> str:
        """Extract view count from HTML."""
        try:
            views_match = re.search(r'"views":"([^"]+)"', html_content)
            return views_match.group(1) if views_match else "unknown"
        except:
            return "unknown"
            
    def _extract_videos_from_page(self, html_content: str) -> List[Dict[str, Any]]:
        """Extract video information from a page."""
        videos = []
        
        try:
            # Look for video links
            video_links = re.findall(r'href="(/view_video\.php\?viewkey=[^"]+)"', html_content)
            
            for link in video_links:
                full_url = f"https://www.pornhub.com{link}"
                video_id = self._extract_video_id(full_url)
                
                # Try to extract title from the same context
                title_pattern = rf'href="{re.escape(link)}"[^>]*>([^<]+)</a>'
                title_match = re.search(title_pattern, html_content)
                title = title_match.group(1).strip() if title_match else f"video_{video_id}"
                
                videos.append({
                    'id': video_id,
                    'title': title,
                    'url': full_url,
                    'video_urls': {}  # Will be populated when downloading
                })
                
        except Exception as e:
            logging.warning(f"Error extracting videos from page: {e}")
            
        return videos
        
    def _download_video_media(self, video_info: Dict[str, Any], download_path: str, 
                            progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        """Download media from a video."""
        try:
            video_id = video_info['id']
            title = self.sanitize_filename(video_info.get('title', f'video_{video_id}'))
            
            # If video_urls not populated, get them now
            video_urls = video_info.get('video_urls', {})
            if not video_urls and video_info.get('url'):
                updated_info = self._get_video_info(video_info['url'])
                video_urls = updated_info.get('video_urls', {})
            
            if not video_urls:
                return {'success': False, 'error': 'No video URLs found'}
                
            # Select best quality URL
            quality_priority = ['1080p', '720p', '480p', '360p', 'default']
            video_url = None
            
            for quality in quality_priority:
                if quality in video_urls:
                    video_url = video_urls[quality]
                    break
                    
            if not video_url:
                video_url = list(video_urls.values())[0]
                
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
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://www.pornhub.com/'
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

    
    def _get_user_gifs(self, username: str, limit: int = 0) -> List[Dict[str, Any]]:
        """Get GIFs from a Pornhub user with unlimited pagination."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            gifs = []
            page = 1
            
            while True:
                # Break if we've reached the limit
                if limit > 0 and len(gifs) >= limit:
                    break
                    
                # Try different URL patterns for GIFs
                gif_urls = [
                    f"https://www.pornhub.com/users/{username}/gifs?page={page}",
                    f"https://www.pornhub.com/model/{username}/gifs?page={page}",
                    f"https://www.pornhub.com/pornstar/{username}/gifs?page={page}"
                ]
                
                found_gifs = False
                
                for gif_url in gif_urls:
                    try:
                        response = requests.get(gif_url, headers=headers)
                        if response.status_code == 200:
                            page_gifs = self._extract_gifs_from_page(response.text)
                            if page_gifs:
                                # Add GIFs but respect limit
                                if limit > 0:
                                    remaining = limit - len(gifs)
                                    gifs.extend(page_gifs[:remaining])
                                else:
                                    gifs.extend(page_gifs)
                                found_gifs = True
                                break
                    except:
                        continue
                
                if not found_gifs:
                    logging.info(f"No more GIFs found for {username} on page {page}")
                    break
                    
                logging.info(f"Retrieved {len(gifs)} GIFs so far for {username}")
                page += 1
                time.sleep(2)  # Rate limiting
                
            logging.info(f"Total retrieved: {len(gifs)} GIFs from {username}")
            return gifs
            
        except Exception as e:
            logging.error(f"Error getting user GIFs: {e}")
            return []
            
    def _extract_gifs_from_page(self, html_content: str) -> List[Dict[str, Any]]:
        """Extract GIF information from a page."""
        gifs = []
        
        try:
            # Look for GIF links
            gif_patterns = [
                r'href="(/gif/[^"]+)"',
                r'href="(/view_video\.php\?viewkey=[^"]+)"[^>]*class="[^"]*gif[^"]*"'
            ]
            
            for pattern in gif_patterns:
                gif_links = re.findall(pattern, html_content)
                
                for link in gif_links:
                    full_url = f"https://www.pornhub.com{link}"
                    gif_id = self._extract_gif_id(full_url)
                    
                    # Try to extract title from the same context
                    title_pattern = rf'href="{re.escape(link)}"[^>]*>([^<]+)</a>'
                    title_match = re.search(title_pattern, html_content)
                    title = title_match.group(1).strip() if title_match else f"gif_{gif_id}"
                    
                    gifs.append({
                        'id': gif_id,
                        'title': title,
                        'url': full_url,
                        'type': 'gif',
                        'gif_urls': {}  # Will be populated when downloading
                    })
                    
        except Exception as e:
            logging.warning(f"Error extracting GIFs from page: {e}")
            
        return gifs
        
    def _extract_gif_id(self, url: str) -> str:
        """Extract GIF ID from Pornhub GIF URL."""
        try:
            if '/gif/' in url:
                return url.split('/gif/')[-1].split('?')[0]
            elif 'viewkey=' in url:
                return url.split('viewkey=')[1].split('&')[0]
            return str(hash(url))  # Fallback
        except:
            return "unknown"
            
    def _download_gif_media(self, gif_info: Dict[str, Any], download_path: str, 
                          progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        """Download media from a GIF."""
        try:
            gif_id = gif_info['id']
            title = self.sanitize_filename(gif_info.get('title', f'gif_{gif_id}'))
            
            # Get GIF URLs if not populated
            gif_urls = gif_info.get('gif_urls', {})
            if not gif_urls and gif_info.get('url'):
                updated_info = self._get_gif_info(gif_info['url'])
                gif_urls = updated_info.get('gif_urls', {})
            
            if not gif_urls:
                return {'success': False, 'error': 'No GIF URLs found'}
                
            # Try different formats
            formats = ['mp4', 'webm', 'gif']
            downloaded = False
            
            for fmt in formats:
                if fmt in gif_urls:
                    gif_url = gif_urls[fmt]
                    output_path = os.path.join(download_path, f'{title}.{fmt}')
                    
                    if self.file_exists(output_path):
                        return {'success': True, 'output_file': output_path, 'skipped': True}
                        
                    if self._download_file(gif_url, output_path, progress_callback):
                        downloaded = True
                        return {'success': True, 'output_file': output_path}
            
            if not downloaded:
                return {'success': False, 'error': 'Failed to download GIF file'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    def _get_gif_info(self, url: str) -> Dict[str, Any]:
        """Get information about a Pornhub GIF."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            html_content = response.text
            
            # Extract GIF ID
            gif_id = self._extract_gif_id(url)
            
            # Extract title
            title_match = re.search(r'<title>([^<]+)</title>', html_content)
            title = title_match.group(1) if title_match else f'gif_{gif_id}'
            title = title.replace(' - Pornhub.com', '').strip()
            
            # Extract GIF URLs
            gif_urls = self._extract_gif_urls(html_content)
            
            return {
                'id': gif_id,
                'title': title,
                'url': url,
                'gif_urls': gif_urls,
                'type': 'gif'
            }
            
        except Exception as e:
            logging.error(f"Error getting GIF info: {e}")
            return {}
            
    def _extract_gif_urls(self, html_content: str) -> Dict[str, str]:
        """Extract GIF URLs from HTML content."""
        gif_urls = {}
        
        try:
            # Look for GIF URL patterns in JavaScript
            patterns = [
                r'"mp4":"([^"]+)"',
                r'"webm":"([^"]+)"',
                r'"gif":"([^"]+)"',
                r'mp4_url["\']:["\']([^"\']+)["\']',
                r'webm_url["\']:["\']([^"\']+)["\']'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, html_content)
                for match in matches:
                    url = match.replace('\\/', '/')
                    if 'mp4' in pattern.lower():
                        gif_urls['mp4'] = url
                    elif 'webm' in pattern.lower():
                        gif_urls['webm'] = url
                    elif 'gif' in pattern.lower():
                        gif_urls['gif'] = url
                        
        except Exception as e:
            logging.warning(f"Error extracting GIF URLs: {e}")
            
        return gif_urls
