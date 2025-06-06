"""
Generic downloader for other websites and platforms.
"""

import os
import logging
import requests
import time
from typing import Dict, Any, Callable, Optional, List
from urllib.parse import urlparse, urljoin
import re

from .base_downloader import BaseDownloader

class GenericDownloader(BaseDownloader):
    """Generic content downloader for various websites."""
    
    def __init__(self, config_manager):
        super().__init__(config_manager)
        self.platform = "generic"
        
        # Supported domains and their specific handlers
        self.domain_handlers = {
            'xvideos.com': self._handle_xvideos,
            'xnxx.com': self._handle_xnxx,
            'youporn.com': self._handle_youporn,
            'tube8.com': self._handle_tube8,
            'spankbang.com': self._handle_spankbang,
            'xhamster.com': self._handle_xhamster,
            'beeg.com': self._handle_beeg,
            'thisvid.com': self._handle_thisvid,
            'motherless.com': self._handle_motherless,
            'eporner.com': self._handle_eporner,
            'faphouse.com': self._handle_faphouse,
            'onlyfans.com': self._handle_onlyfans
        }
        
    def download(self, url: str, options: Dict[str, Any], 
                progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        """Download content from generic websites."""
        try:
            self.log_download_start(self.platform, url)
            
            # Parse domain
            domain = urlparse(url).netloc.lower()
            domain = domain.replace('www.', '')
            
            # Check if we have a specific handler for this domain
            handler = None
            for supported_domain, handler_func in self.domain_handlers.items():
                if supported_domain in domain:
                    handler = handler_func
                    break
                    
            if handler:
                result = handler(url, options, progress_callback)
            else:
                result = self._handle_generic_site(url, options, progress_callback)
                
            if result['success']:
                self.log_download_complete(self.platform, url, result.get('files_downloaded', 0))
            else:
                self.log_download_error(self.platform, url, result.get('error', 'Unknown error'))
                
            return result
            
        except Exception as e:
            error_msg = f"Generic download failed: {str(e)}"
            self.log_download_error(self.platform, url, error_msg)
            return {'success': False, 'error': error_msg}
            
    def _handle_xvideos(self, url: str, options: Dict[str, Any], 
                       progress_callback: Optional[Callable[[int], None]]) -> Dict[str, Any]:
        """Handle Xvideos downloads."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            html_content = response.text
            
            # Extract video info
            title_match = re.search(r'<title>([^<]+)</title>', html_content)
            title = title_match.group(1).strip() if title_match else 'xvideos_video'
            title = title.replace(' - XVIDEOS.COM', '').strip()
            
            # Extract video URL
            video_url_patterns = [
                r'html5player\.setVideoUrlHigh\(\'([^\']+)\'\)',
                r'html5player\.setVideoUrlLow\(\'([^\']+)\'\)',
                r'setVideoTitle\(\'[^\']*\',\'[^\']*\',\'([^\']+)\'\)'
            ]
            
            video_url = None
            for pattern in video_url_patterns:
                match = re.search(pattern, html_content)
                if match:
                    video_url = match.group(1)
                    break
                    
            if not video_url:
                return {'success': False, 'error': 'Could not extract video URL'}
                
            download_path = self.get_download_path('xvideos')
            filename = self.sanitize_filename(f'{title}.mp4')
            output_path = os.path.join(download_path, filename)
            
            if self.file_exists(output_path):
                return {'success': True, 'output_file': output_path, 'skipped': True}
                
            if self._download_file(video_url, output_path, progress_callback):
                return {'success': True, 'output_file': output_path}
            else:
                return {'success': False, 'error': 'Failed to download video'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    def _handle_xnxx(self, url: str, options: Dict[str, Any], 
                    progress_callback: Optional[Callable[[int], None]]) -> Dict[str, Any]:
        """Handle XNXX downloads."""
        return self._handle_generic_adult_site(url, options, progress_callback, 'xnxx')
        
    def _handle_youporn(self, url: str, options: Dict[str, Any], 
                       progress_callback: Optional[Callable[[int], None]]) -> Dict[str, Any]:
        """Handle YouPorn downloads."""
        return self._handle_generic_adult_site(url, options, progress_callback, 'youporn')
        
    def _handle_tube8(self, url: str, options: Dict[str, Any], 
                     progress_callback: Optional[Callable[[int], None]]) -> Dict[str, Any]:
        """Handle Tube8 downloads."""
        return self._handle_generic_adult_site(url, options, progress_callback, 'tube8')
        
    def _handle_spankbang(self, url: str, options: Dict[str, Any], 
                         progress_callback: Optional[Callable[[int], None]]) -> Dict[str, Any]:
        """Handle SpankBang downloads."""
        return self._handle_generic_adult_site(url, options, progress_callback, 'spankbang')
        
    def _handle_xhamster(self, url: str, options: Dict[str, Any], 
                        progress_callback: Optional[Callable[[int], None]]) -> Dict[str, Any]:
        """Handle xHamster downloads."""
        return self._handle_generic_adult_site(url, options, progress_callback, 'xhamster')
        
    def _handle_beeg(self, url: str, options: Dict[str, Any], 
                    progress_callback: Optional[Callable[[int], None]]) -> Dict[str, Any]:
        """Handle Beeg downloads."""
        return self._handle_generic_adult_site(url, options, progress_callback, 'beeg')
        
    def _handle_thisvid(self, url: str, options: Dict[str, Any], 
                       progress_callback: Optional[Callable[[int], None]]) -> Dict[str, Any]:
        """Handle ThisVid downloads."""
        return self._handle_generic_adult_site(url, options, progress_callback, 'thisvid')
        
    def _handle_motherless(self, url: str, options: Dict[str, Any], 
                          progress_callback: Optional[Callable[[int], None]]) -> Dict[str, Any]:
        """Handle Motherless downloads."""
        return self._handle_generic_adult_site(url, options, progress_callback, 'motherless')
        
    def _handle_eporner(self, url: str, options: Dict[str, Any], 
                       progress_callback: Optional[Callable[[int], None]]) -> Dict[str, Any]:
        """Handle EPorner downloads."""
        return self._handle_generic_adult_site(url, options, progress_callback, 'eporner')
        
    def _handle_faphouse(self, url: str, options: Dict[str, Any], 
                        progress_callback: Optional[Callable[[int], None]]) -> Dict[str, Any]:
        """Handle FapHouse downloads."""
        return self._handle_generic_adult_site(url, options, progress_callback, 'faphouse')
        
    def _handle_onlyfans(self, url: str, options: Dict[str, Any], 
                        progress_callback: Optional[Callable[[int], None]]) -> Dict[str, Any]:
        """Handle OnlyFans downloads."""
        return {'success': False, 'error': 'OnlyFans requires authentication and API access. Please provide your OnlyFans session cookies or API credentials.'}
        
    def _handle_generic_adult_site(self, url: str, options: Dict[str, Any], 
                                  progress_callback: Optional[Callable[[int], None]], 
                                  site_name: str) -> Dict[str, Any]:
        """Generic handler for adult video sites."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            html_content = response.text
            
            # Extract title
            title_patterns = [
                r'<title>([^<]+)</title>',
                r'<h1[^>]*>([^<]+)</h1>',
                r'"title":"([^"]+)"'
            ]
            
            title = f'{site_name}_video'
            for pattern in title_patterns:
                match = re.search(pattern, html_content)
                if match:
                    title = match.group(1).strip()
                    # Clean up common suffixes
                    for suffix in [f' - {site_name.upper()}', ' - Free Porn Videos', ' Porn Video']:
                        title = title.replace(suffix, '')
                    break
                    
            # Extract video URLs using common patterns
            video_url_patterns = [
                r'"videoUrl":"([^"]+)"',
                r'"video_url":"([^"]+)"',
                r'"file":"([^"]+\.mp4[^"]*)"',
                r'video_url["\s]*[:=]["\s]*([^"\']+)',
                r'src["\s]*:["\s]*([^"\']+\.mp4[^"\']*)',
                r'file["\s]*:["\s]*([^"\']+\.mp4[^"\']*)'
            ]
            
            video_url = None
            for pattern in video_url_patterns:
                matches = re.findall(pattern, html_content)
                for match in matches:
                    if '.mp4' in match and 'http' in match:
                        video_url = match.replace('\\/', '/')
                        break
                if video_url:
                    break
                    
            if not video_url:
                return {'success': False, 'error': f'Could not extract video URL from {site_name}'}
                
            download_path = self.get_download_path(site_name)
            filename = self.sanitize_filename(f'{title}.mp4')
            output_path = os.path.join(download_path, filename)
            
            if self.file_exists(output_path):
                return {'success': True, 'output_file': output_path, 'skipped': True}
                
            if self._download_file(video_url, output_path, progress_callback):
                return {'success': True, 'output_file': output_path}
            else:
                return {'success': False, 'error': 'Failed to download video'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    def _handle_generic_site(self, url: str, options: Dict[str, Any], 
                           progress_callback: Optional[Callable[[int], None]]) -> Dict[str, Any]:
        """Handle generic websites."""
        try:
            domain = urlparse(url).netloc.replace('www.', '')
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            # Look for direct media links
            content_type = response.headers.get('content-type', '').lower()
            
            if any(media_type in content_type for media_type in ['video/', 'image/', 'audio/']):
                # Direct media file
                filename = os.path.basename(urlparse(url).path) or 'media_file'
                download_path = self.get_download_path(domain)
                output_path = os.path.join(download_path, filename)
                
                if self.file_exists(output_path):
                    return {'success': True, 'output_file': output_path, 'skipped': True}
                    
                if self._download_file(url, output_path, progress_callback):
                    return {'success': True, 'output_file': output_path}
                else:
                    return {'success': False, 'error': 'Failed to download media file'}
            else:
                # HTML page - look for media links
                html_content = response.text
                media_urls = self._extract_media_urls(html_content, url)
                
                if not media_urls:
                    return {'success': False, 'error': 'No media files found on the page'}
                    
                download_path = self.get_download_path(domain)
                downloaded_count = 0
                
                for i, media_url in enumerate(media_urls):
                    try:
                        filename = f'media_{i+1:03d}.{self._get_extension_from_url(media_url)}'
                        output_path = os.path.join(download_path, filename)
                        
                        if not self.file_exists(output_path):
                            if self._download_file(media_url, output_path):
                                downloaded_count += 1
                        else:
                            downloaded_count += 1
                            
                        if progress_callback:
                            progress = int(((i + 1) / len(media_urls)) * 100)
                            progress_callback(progress)
                            
                        time.sleep(1)  # Rate limiting
                        
                    except Exception as e:
                        logging.warning(f"Failed to download media {i+1}: {e}")
                        continue
                        
                return {
                    'success': True,
                    'files_downloaded': downloaded_count,
                    'total_media': len(media_urls)
                }
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    def _extract_media_urls(self, html_content: str, base_url: str) -> List[str]:
        """Extract media URLs from HTML content."""
        media_urls = []
        
        # Patterns for media files
        patterns = [
            r'src=["\']([^"\']+\.(?:mp4|avi|mov|wmv|flv|webm|mkv|m4v))["\']',
            r'src=["\']([^"\']+\.(?:jpg|jpeg|png|gif|bmp|webp))["\']',
            r'href=["\']([^"\']+\.(?:mp4|avi|mov|wmv|flv|webm|mkv|m4v))["\']',
            r'url\(["\']?([^"\']+\.(?:jpg|jpeg|png|gif|bmp|webp))["\']?\)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                # Convert relative URLs to absolute
                if match.startswith('//'):
                    media_url = 'https:' + match
                elif match.startswith('/'):
                    media_url = urljoin(base_url, match)
                elif not match.startswith('http'):
                    media_url = urljoin(base_url, match)
                else:
                    media_url = match
                    
                if media_url not in media_urls:
                    media_urls.append(media_url)
                    
        return media_urls
        
    def _get_extension_from_url(self, url: str) -> str:
        """Get file extension from URL."""
        try:
            parsed = urlparse(url)
            path = parsed.path
            
            if '.' in path:
                return path.split('.')[-1].lower()
            else:
                return 'mp4'  # Default
                
        except:
            return 'mp4'
            
    def _download_file(self, url: str, output_path: str, 
                      progress_callback: Optional[Callable[[int], None]] = None) -> bool:
        """Download a file from URL."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': urlparse(url).scheme + '://' + urlparse(url).netloc + '/'
            }
            
            response = requests.get(url, headers=headers, stream=True, timeout=30)
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