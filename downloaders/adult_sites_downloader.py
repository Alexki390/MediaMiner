
"""
Advanced downloader for adult content sites with comprehensive profile downloading.
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
import cloudscraper

from .base_downloader import BaseDownloader
from utils.protection_bypass import ProtectionBypass
from utils.error_handler import ErrorHandler, ErrorCategory, ErrorSeverity

class AdultSitesDownloader(BaseDownloader):
    """Advanced downloader for adult content sites with profile support."""
    
    def __init__(self, config_manager):
        super().__init__(config_manager)
        self.platform = "adult_sites"
        self.protection_bypass = ProtectionBypass()
        self.error_handler = ErrorHandler()
        
        # Site-specific configurations
        self.site_configs = {
            'urlebird.com': {
                'rate_limit': 8,  # requests per minute
                'delay': 7,       # seconds between requests
                'profile_pattern': r'/user/([^/]+)',
                'post_pattern': r'<div class="thumb-wrap">.*?<a href="([^"]+)"',
                'media_pattern': r'<video[^>]*src="([^"]+)"',
                'pagination_pattern': r'<a[^>]*href="([^"]*\?page=\d+)"',
                'max_retries': 5
            },
            'ttthots.com': {
                'rate_limit': 6,
                'delay': 10,
                'profile_pattern': r'/profile/([^/]+)',
                'post_pattern': r'<a[^>]*href="(/post/[^"]+)"',
                'media_pattern': r'<img[^>]*src="([^"]+)".*?<video[^>]*src="([^"]+)"',
                'pagination_pattern': r'<a[^>]*href="([^"]*page=\d+)"',
                'max_retries': 5
            },
            'sotwe.com': {
                'rate_limit': 10,
                'delay': 6,
                'profile_pattern': r'/user/([^/]+)',
                'post_pattern': r'<article[^>]*>.*?<a href="([^"]+)"',
                'media_pattern': r'<img[^>]*src="([^"]+\.jpg[^"]*)".*?<video[^>]*src="([^"]+\.mp4[^"]*)"',
                'pagination_pattern': r'<a[^>]*href="([^"]*page=\d+)"',
                'max_retries': 3
            },
            'fapsly.com': {
                'rate_limit': 5,
                'delay': 12,
                'profile_pattern': r'/model/([^/]+)',
                'post_pattern': r'<div class="video-item">.*?<a href="([^"]+)"',
                'media_pattern': r'<video[^>]*src="([^"]+)"',
                'pagination_pattern': r'<a[^>]*href="([^"]*\?p=\d+)"',
                'max_retries': 5
            },
            'imhentai.xxx': {
                'rate_limit': 10,
                'delay': 6,
                'profile_pattern': r'/gallery/(\d+)',
                'post_pattern': r'<a[^>]*href="(/gallery/\d+/)"',
                'media_pattern': r'<img[^>]*src="([^"]+/galleries/[^"]+)"',
                'pagination_pattern': r'<a[^>]*href="([^"]*page=\d+)"',
                'max_retries': 3
            },
            'hentaiera.com': {
                'rate_limit': 10,
                'delay': 6,
                'profile_pattern': r'/tag/([^/]+)',
                'post_pattern': r'<a[^>]*href="(/\d+[^"]*)"',
                'media_pattern': r'<img[^>]*src="([^"]+)"',
                'pagination_pattern': r'<a[^>]*href="([^"]*page/\d+)"',
                'max_retries': 3
            },
            'nhentai.net': {
                'rate_limit': 8,
                'delay': 7,
                'profile_pattern': r'/g/(\d+)',
                'post_pattern': r'<a[^>]*href="(/g/\d+/)"',
                'media_pattern': r'<img[^>]*data-src="([^"]+)"',
                'pagination_pattern': r'<a[^>]*href="([^"]*page=\d+)"',
                'max_retries': 5
            }
        }
        
    def download(self, url: str, options: Dict[str, Any], 
                progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        """Download content from adult sites with automatic profile detection."""
        try:
            self.log_download_start(self.platform, url)
            
            domain = urlparse(url).netloc.lower().replace('www.', '')
            
            if domain not in self.site_configs:
                return {'success': False, 'error': f'Unsupported site: {domain}'}
            
            site_config = self.site_configs[domain]
            
            # Determine if this is a profile/user URL
            if self._is_profile_url(url, site_config):
                result = self._download_profile_content(url, options, progress_callback, site_config)
            else:
                result = self._download_single_content(url, options, progress_callback, site_config)
            
            if result['success']:
                self.log_download_complete(self.platform, url, result.get('files_downloaded', 0))
            else:
                self.log_download_error(self.platform, url, result.get('error', 'Unknown error'))
                
            return result
            
        except Exception as e:
            error_msg = f"Adult sites download failed: {str(e)}"
            self.log_download_error(self.platform, url, error_msg)
            return {'success': False, 'error': error_msg}
    
    def _is_profile_url(self, url: str, site_config: Dict[str, Any]) -> bool:
        """Check if URL is a profile/user page."""
        try:
            pattern = site_config.get('profile_pattern', '')
            return bool(re.search(pattern, url))
        except:
            return False
    
    def _download_profile_content(self, profile_url: str, options: Dict[str, Any], 
                                 progress_callback: Optional[Callable[[int], None]], 
                                 site_config: Dict[str, Any]) -> Dict[str, Any]:
        """Download all content from a profile/user with unlimited pagination."""
        try:
            domain = urlparse(profile_url).netloc.lower().replace('www.', '')
            username = self._extract_username(profile_url, site_config)
            
            download_path = self.get_download_path(domain, username)
            
            total_files = 0
            total_posts = 0
            page = 1
            max_pages = options.get('max_pages', 0)  # 0 = unlimited
            
            while True:
                try:
                    # Construct paginated URL
                    page_url = self._construct_page_url(profile_url, page, site_config)
                    
                    logging.info(f"Downloading page {page} from {username}")
                    
                    # Get page content with protection bypass
                    page_content = self._get_page_content(page_url, site_config)
                    if not page_content:
                        logging.warning(f"Failed to get content for page {page}")
                        break
                    
                    # Extract post URLs from page
                    post_urls = self._extract_post_urls(page_content, page_url, site_config)
                    if not post_urls:
                        logging.info(f"No posts found on page {page}, ending pagination")
                        break
                    
                    # Download posts from this page
                    for i, post_url in enumerate(post_urls):
                        try:
                            if progress_callback:
                                progress = min(int((total_posts / max(total_posts + len(post_urls), 1)) * 100), 99)
                                progress_callback(progress)
                            
                            result = self._download_post_content(post_url, download_path, site_config)
                            if result.get('success', False):
                                total_files += result.get('files_downloaded', 0)
                            
                            total_posts += 1
                            
                            # Rate limiting between posts
                            time.sleep(site_config['delay'])
                            
                        except Exception as e:
                            logging.warning(f"Failed to download post {post_url}: {e}")
                            continue
                    
                    # Check if we should continue to next page
                    page += 1
                    if max_pages > 0 and page > max_pages:
                        logging.info(f"Reached maximum pages limit: {max_pages}")
                        break
                    
                    # Check if there's a next page
                    if not self._has_next_page(page_content, site_config):
                        logging.info("No more pages available")
                        break
                    
                    # Longer delay between pages to avoid rate limiting
                    time.sleep(site_config['delay'] * 2)
                    
                except Exception as e:
                    logging.error(f"Error processing page {page}: {e}")
                    break
            
            if progress_callback:
                progress_callback(100)
            
            return {
                'success': True,
                'files_downloaded': total_files,
                'posts_processed': total_posts,
                'pages_processed': page - 1,
                'username': username
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _extract_username(self, url: str, site_config: Dict[str, Any]) -> str:
        """Extract username from profile URL."""
        try:
            pattern = site_config.get('profile_pattern', '')
            match = re.search(pattern, url)
            if match:
                return match.group(1)
            else:
                # Fallback to URL-based naming
                return urlparse(url).path.strip('/').replace('/', '_')
        except:
            return "unknown_user"
    
    def _construct_page_url(self, base_url: str, page: int, site_config: Dict[str, Any]) -> str:
        """Construct URL for specific page."""
        try:
            if page == 1:
                return base_url
            
            # Site-specific pagination logic
            domain = urlparse(base_url).netloc.lower()
            
            if 'urlebird.com' in domain:
                return f"{base_url}?page={page}"
            elif 'ttthots.com' in domain:
                return f"{base_url}?page={page}"
            elif 'sotwe.com' in domain:
                return f"{base_url}?page={page}"
            elif 'fapsly.com' in domain:
                return f"{base_url}?p={page}"
            elif 'imhentai.xxx' in domain:
                return f"{base_url}?page={page}"
            elif 'hentaiera.com' in domain:
                return f"{base_url}/page/{page}"
            elif 'nhentai.net' in domain:
                return f"{base_url}?page={page}"
            else:
                return f"{base_url}?page={page}"
                
        except:
            return base_url
    
    def _get_page_content(self, url: str, site_config: Dict[str, Any]) -> str:
        """Get page content with protection bypass."""
        try:
            max_retries = site_config.get('max_retries', 3)
            
            for attempt in range(max_retries):
                try:
                    # Use cloudscraper for Cloudflare protection
                    scraper = cloudscraper.create_scraper(
                        browser={
                            'browser': 'chrome',
                            'platform': 'windows',
                            'mobile': False
                        }
                    )
                    
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'DNT': '1',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'none',
                        'Cache-Control': 'max-age=0'
                    }
                    
                    response = scraper.get(url, headers=headers, timeout=30)
                    response.raise_for_status()
                    
                    return response.text
                    
                except Exception as e:
                    logging.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(5 * (attempt + 1))  # Exponential backoff
                    continue
            
            return None
            
        except Exception as e:
            logging.error(f"Failed to get page content: {e}")
            return None
    
    def _extract_post_urls(self, html_content: str, base_url: str, site_config: Dict[str, Any]) -> List[str]:
        """Extract post URLs from page content."""
        try:
            post_urls = []
            pattern = site_config.get('post_pattern', '')
            
            if not pattern:
                return []
            
            matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)
            
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]  # Take first group if multiple groups
                
                # Convert relative URLs to absolute
                if match.startswith('//'):
                    post_url = 'https:' + match
                elif match.startswith('/'):
                    post_url = urljoin(base_url, match)
                elif not match.startswith('http'):
                    post_url = urljoin(base_url, match)
                else:
                    post_url = match
                
                if post_url not in post_urls:
                    post_urls.append(post_url)
            
            return post_urls
            
        except Exception as e:
            logging.error(f"Error extracting post URLs: {e}")
            return []
    
    def _download_post_content(self, post_url: str, download_path: str, site_config: Dict[str, Any]) -> Dict[str, Any]:
        """Download content from a single post."""
        try:
            post_content = self._get_page_content(post_url, site_config)
            if not post_content:
                return {'success': False, 'error': 'Failed to get post content'}
            
            # Extract media URLs
            media_urls = self._extract_media_urls(post_content, post_url, site_config)
            if not media_urls:
                return {'success': False, 'error': 'No media found in post'}
            
            files_downloaded = 0
            post_id = self._extract_post_id(post_url)
            
            for i, media_url in enumerate(media_urls):
                try:
                    # Generate filename
                    extension = self._get_file_extension(media_url)
                    filename = f"{post_id}_{i+1:03d}.{extension}"
                    filepath = os.path.join(download_path, filename)
                    
                    if self.file_exists(filepath):
                        files_downloaded += 1
                        continue
                    
                    # Download file
                    if self._download_media_file(media_url, filepath, site_config):
                        files_downloaded += 1
                    
                    # Rate limiting between files
                    time.sleep(1)
                    
                except Exception as e:
                    logging.warning(f"Failed to download media {media_url}: {e}")
                    continue
            
            return {
                'success': True,
                'files_downloaded': files_downloaded
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _extract_media_urls(self, html_content: str, base_url: str, site_config: Dict[str, Any]) -> List[str]:
        """Extract media URLs from post content."""
        try:
            media_urls = []
            pattern = site_config.get('media_pattern', '')
            
            if not pattern:
                # Fallback to generic patterns
                patterns = [
                    r'<img[^>]*src=["\']([^"\']+)["\']',
                    r'<video[^>]*src=["\']([^"\']+)["\']',
                    r'data-src=["\']([^"\']+)["\']'
                ]
            else:
                patterns = [pattern]
            
            for pattern in patterns:
                matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)
                
                for match in matches:
                    if isinstance(match, tuple):
                        # Multiple groups, take all non-empty ones
                        for group in match:
                            if group:
                                media_urls.append(self._normalize_media_url(group, base_url))
                    else:
                        media_urls.append(self._normalize_media_url(match, base_url))
            
            # Remove duplicates while preserving order
            seen = set()
            unique_urls = []
            for url in media_urls:
                if url not in seen and self._is_valid_media_url(url):
                    seen.add(url)
                    unique_urls.append(url)
            
            return unique_urls
            
        except Exception as e:
            logging.error(f"Error extracting media URLs: {e}")
            return []
    
    def _normalize_media_url(self, url: str, base_url: str) -> str:
        """Normalize media URL to absolute form."""
        try:
            if url.startswith('//'):
                return 'https:' + url
            elif url.startswith('/'):
                return urljoin(base_url, url)
            elif not url.startswith('http'):
                return urljoin(base_url, url)
            else:
                return url
        except:
            return url
    
    def _is_valid_media_url(self, url: str) -> bool:
        """Check if URL points to valid media."""
        try:
            # Check for common media extensions
            media_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4', '.webm', '.mov']
            return any(ext in url.lower() for ext in media_extensions)
        except:
            return True  # Default to True if we can't determine
    
    def _download_media_file(self, url: str, filepath: str, site_config: Dict[str, Any]) -> bool:
        """Download a media file."""
        try:
            scraper = cloudscraper.create_scraper()
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': urlparse(url).scheme + '://' + urlparse(url).netloc + '/'
            }
            
            response = scraper.get(url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            return True
            
        except Exception as e:
            logging.error(f"Error downloading file {url}: {e}")
            if os.path.exists(filepath):
                os.remove(filepath)
            return False
    
    def _extract_post_id(self, url: str) -> str:
        """Extract post ID from URL."""
        try:
            # Try various patterns to extract ID
            patterns = [
                r'/post/(\d+)',
                r'/(\d+)/?$',
                r'id=(\d+)',
                r'/([^/]+)/?$'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    return match.group(1)
            
            # Fallback to URL hash
            return str(abs(hash(url)) % 1000000)
            
        except:
            return "unknown"
    
    def _get_file_extension(self, url: str) -> str:
        """Get file extension from URL."""
        try:
            parsed = urlparse(url)
            path = parsed.path
            
            if '.' in path:
                return path.split('.')[-1].lower()
            else:
                return 'jpg'  # Default
                
        except:
            return 'jpg'
    
    def _has_next_page(self, html_content: str, site_config: Dict[str, Any]) -> bool:
        """Check if there's a next page."""
        try:
            pagination_pattern = site_config.get('pagination_pattern', '')
            if not pagination_pattern:
                return False
            
            # Look for pagination links
            matches = re.findall(pagination_pattern, html_content, re.IGNORECASE)
            return len(matches) > 0
            
        except:
            return False
    
    def _download_single_content(self, url: str, options: Dict[str, Any], 
                                progress_callback: Optional[Callable[[int], None]], 
                                site_config: Dict[str, Any]) -> Dict[str, Any]:
        """Download content from a single URL."""
        try:
            domain = urlparse(url).netloc.lower().replace('www.', '')
            download_path = self.get_download_path(domain)
            
            return self._download_post_content(url, download_path, site_config)
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
