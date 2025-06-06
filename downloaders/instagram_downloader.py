"""
Instagram downloader for posts and stories.
"""

import os
import logging
import requests
import json
import time
from typing import Dict, Any, Callable, Optional, List

from .base_downloader import BaseDownloader
from utils.auth_manager import AuthManager
from utils.error_handler import ErrorHandler, ErrorCategory, ErrorSeverity

class InstagramDownloader(BaseDownloader):
    """Instagram content downloader."""
    
    def __init__(self, config_manager):
        super().__init__(config_manager)
        self.platform = "instagram"
        self.session = None
        self.logged_in = False
        
        # Initialize authentication and error handling
        self.auth_manager = AuthManager(config_manager)
        self.error_handler = ErrorHandler(config_manager)
        
        # Session management
        self.session_timeout = 3600  # 1 hour
        self.max_retries = 3
        self.request_delay = 2.0
        
        # Load existing session if available
        self._restore_session()
        
    def download(self, url: str, options: Dict[str, Any], 
                progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        """Download Instagram content."""
        try:
            self.log_download_start(self.platform, url)
            
            # Determine if it's a username or post URL
            if self._is_post_url(url):
                result = self._download_single_post(url, options, progress_callback)
            else:
                result = self._download_user_content(url, options, progress_callback)
                
            if result['success']:
                self.log_download_complete(self.platform, url, result.get('files_downloaded', 0))
            else:
                self.log_download_error(self.platform, url, result.get('error', 'Unknown error'))
                
            return result
            
        except Exception as e:
            error_msg = f"Instagram download failed: {str(e)}"
            self.log_download_error(self.platform, url, error_msg)
            return {'success': False, 'error': error_msg}

    def login(self, username: str, password: str, save_credentials: bool = True) -> Dict[str, Any]:
        """Login to Instagram with robust authentication."""
        try:
            # Validate credentials format
            if not self._validate_credentials_format(username, password):
                return {
                    'success': False,
                    'error': 'Invalid credentials format',
                    'requires_2fa': False
                }
            
            # Check for existing session
            existing_session = self.auth_manager.get_session(self.platform)
            if existing_session:
                self.session = existing_session.get('session_object')
                self.logged_in = True
                logging.info("Using existing Instagram session")
                return {'success': True, 'message': 'Using existing session'}
            
            # Create new session
            self.session = requests.Session()
            
            # Set up headers
            self.session.headers.update({
                'User-Agent': self.config.get('instagram', {}).get('user_agent', 
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            })
            
            # Attempt login
            login_result = self._perform_login(username, password)
            
            if login_result['success']:
                self.logged_in = True
                
                # Save session
                session_data = {
                    'session_object': self.session,
                    'username': username,
                    'login_time': time.time()
                }
                
                self.auth_manager.create_session(
                    self.platform, 
                    session_data, 
                    expires_in=self.session_timeout
                )
                
                # Save credentials if requested
                if save_credentials:
                    self.auth_manager.store_credentials(
                        self.platform, username, password
                    )
                
                logging.info(f"Instagram login successful for {username}")
                return login_result
            else:
                return login_result
                
        except Exception as e:
            error_info = self.error_handler.handle_error(
                e, 
                context={'username': username, 'action': 'login'},
                category=ErrorCategory.AUTHENTICATION,
                severity=ErrorSeverity.HIGH
            )
            
            return {
                'success': False,
                'error': f"Login failed: {str(e)}",
                'error_details': error_info
            }
            
    def logout(self):
        """Logout from Instagram."""
        try:
            self.logged_in = False
            
            if self.session:
                self.session.close()
                self.session = None
            
            # Clear stored session
            self.auth_manager.logout(self.platform)
            
            logging.info("Instagram logout successful")
            
        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={'action': 'logout'},
                category=ErrorCategory.AUTHENTICATION,
                severity=ErrorSeverity.MEDIUM
            )
            
    def _validate_credentials_format(self, username: str, password: str) -> bool:
        """Validate credentials format."""
        try:
            if not username or not password:
                return False
                
            if len(username) < 1 or len(password) < 6:
                return False
                
            # Instagram username validation
            if not username.replace('_', '').replace('.', '').isalnum():
                return False
                
            return True
            
        except Exception:
            return False
            
    def _perform_login(self, username: str, password: str) -> Dict[str, Any]:
        """Perform actual Instagram login."""
        try:
            # Get login page first
            login_url = "https://www.instagram.com/accounts/login/"
            response = self.session.get(login_url)
            
            if response.status_code != 200:
                return {
                    'success': False,
                    'error': 'Could not access Instagram login page'
                }
            
            # Extract CSRF token
            csrf_token = self._extract_csrf_token(response.text)
            if not csrf_token:
                return {
                    'success': False,
                    'error': 'Could not extract CSRF token'
                }
            
            # Prepare login data
            login_data = {
                'username': username,
                'password': password,
                'csrfmiddlewaretoken': csrf_token,
                'optIntoOneTap': 'false'
            }
            
            # Add CSRF token to headers
            self.session.headers.update({
                'X-CSRFToken': csrf_token,
                'Referer': login_url
            })
            
            # Submit login
            login_response = self.session.post(
                "https://www.instagram.com/accounts/login/ajax/",
                data=login_data
            )
            
            if login_response.status_code == 200:
                response_data = login_response.json()
                
                if response_data.get('authenticated'):
                    return {'success': True, 'message': 'Login successful'}
                elif response_data.get('two_factor_required'):
                    return {
                        'success': False,
                        'requires_2fa': True,
                        'error': '2FA required',
                        'two_factor_identifier': response_data.get('two_factor_info', {}).get('two_factor_identifier')
                    }
                else:
                    return {
                        'success': False,
                        'error': response_data.get('message', 'Login failed')
                    }
            else:
                return {
                    'success': False,
                    'error': f'Login request failed with status {login_response.status_code}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Login process failed: {str(e)}'
            }
            
    def _extract_csrf_token(self, html: str) -> Optional[str]:
        """Extract CSRF token from HTML."""
        try:
            import re
            
            # Try multiple patterns
            patterns = [
                r'"csrf_token":"([^"]+)"',
                r'csrfmiddlewaretoken["\s]*:["\s]*([^"]+)',
                r'name="csrfmiddlewaretoken" value="([^"]+)"'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, html)
                if match:
                    return match.group(1)
                    
            return None
            
        except Exception:
            return None
            
    def _restore_session(self):
        """Restore existing session if available."""
        try:
            session_data = self.auth_manager.get_session(self.platform)
            
            if session_data:
                self.session = session_data.get('session_object')
                self.logged_in = True
                logging.info("Instagram session restored")
                
        except Exception as e:
            logging.warning(f"Could not restore Instagram session: {e}")
            
    def handle_two_factor(self, code: str, identifier: str) -> Dict[str, Any]:
        """Handle two-factor authentication."""
        try:
            if not self.session:
                return {'success': False, 'error': 'No active session for 2FA'}
                
            two_factor_data = {
                'verificationCode': code,
                'identifier': identifier,
                'csrfmiddlewaretoken': self._get_current_csrf_token()
            }
            
            response = self.session.post(
                "https://www.instagram.com/accounts/login/ajax/two_factor/",
                data=two_factor_data
            )
            
            if response.status_code == 200:
                response_data = response.json()
                
                if response_data.get('authenticated'):
                    self.logged_in = True
                    return {'success': True, 'message': '2FA verification successful'}
                else:
                    return {
                        'success': False,
                        'error': response_data.get('message', '2FA verification failed')
                    }
            else:
                return {
                    'success': False,
                    'error': f'2FA request failed with status {response.status_code}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'2FA handling failed: {str(e)}'
            }
            
    def _get_current_csrf_token(self) -> Optional[str]:
        """Get current CSRF token from session."""
        try:
            if self.session and 'csrftoken' in self.session.cookies:
                return self.session.cookies['csrftoken']
            return None
        except Exception:
            return None


            if self._is_post_url(url):
                result = self._download_single_post(url, options, progress_callback)
            else:
                result = self._download_user_content(url, options, progress_callback)
                
            if result['success']:
                self.log_download_complete(self.platform, url, result.get('files_downloaded', 0))
            else:
                self.log_download_error(self.platform, url, result.get('error', 'Unknown error'))
                
            return result
            
        except Exception as e:
            error_msg = f"Instagram download failed: {str(e)}"
            self.log_download_error(self.platform, url, error_msg)
            return {'success': False, 'error': error_msg}
            
    def _is_post_url(self, url: str) -> bool:
        """Check if the URL is an Instagram post URL."""
        return 'instagram.com' in url and ('/p/' in url or '/reel/' in url)
        
    def _download_single_post(self, url: str, options: Dict[str, Any], 
                            progress_callback: Optional[Callable[[int], None]]) -> Dict[str, Any]:
        """Download a single Instagram post."""
        try:
            # Get post info
            post_info = self._get_post_info(url)
            if not post_info:
                return {'success': False, 'error': 'Failed to get post information'}
                
            download_path = self.get_download_path(self.platform)
            
            # Download media from post
            result = self._download_post_media(post_info, download_path, progress_callback)
            return result
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    def _download_user_content(self, username: str, options: Dict[str, Any], 
                             progress_callback: Optional[Callable[[int], None]]) -> Dict[str, Any]:
        """Download content from an Instagram user with bulk optimization."""
        try:
            # Clean username
            username = username.replace('@', '').strip()
            max_posts = options.get('limit', 0)  # 0 = unlimited
            
            # Get user's posts with pagination for unlimited downloads
            posts = self._get_user_posts_bulk(username, max_posts)
            if not posts:
                return {'success': False, 'error': 'No posts found or failed to fetch user content'}
                
            download_path = self.get_download_path(self.platform, username)
            total_posts = len(posts)
            downloaded_count = 0
            
            # Use batch processing for efficiency
            batch_size = 10
            for batch_start in range(0, total_posts, batch_size):
                batch_end = min(batch_start + batch_size, total_posts)
                batch_posts = posts[batch_start:batch_end]
                
                for i, post_info in enumerate(batch_posts):
                    try:
                        current_index = batch_start + i
                        if progress_callback:
                            progress = int((current_index / total_posts) * 90)  # Reserve 10% for stories
                            progress_callback(progress)
                            
                        result = self._download_post_media(post_info, download_path)
                        
                        if result.get('success', False):
                            downloaded_count += result.get('files_downloaded', 0)
                            
                        # Reduced delay for bulk operations
                        time.sleep(1)
                        
                    except Exception as e:
                        logging.warning(f"Failed to download post {post_info.get('id', 'unknown')}: {e}")
                        continue
                
                # Batch delay to avoid rate limiting
                time.sleep(3)
                    
            # Download stories if requested
            if options.get('include_stories', False):
                try:
                    if progress_callback:
                        progress_callback(95)
                        
                    stories_result = self._download_user_stories(username, download_path)
                    if stories_result.get('success', False):
                        downloaded_count += stories_result.get('files_downloaded', 0)
                        
                except Exception as e:
                    logging.warning(f"Failed to download stories for {username}: {e}")
                    
            # Download highlights if requested
            if options.get('include_highlights', False):
                try:
                    if progress_callback:
                        progress_callback(97)
                        
                    highlights_result = self._download_user_highlights(username, download_path)
                    if highlights_result.get('success', False):
                        downloaded_count += highlights_result.get('files_downloaded', 0)
                        
                except Exception as e:
                    logging.warning(f"Failed to download highlights for {username}: {e}")
                    
            if progress_callback:
                progress_callback(100)
                
            return {
                'success': True,
                'files_downloaded': downloaded_count,
                'total_posts': total_posts
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    def _get_user_posts_bulk(self, username: str, max_posts: int = 0) -> List[Dict[str, Any]]:
        """Get all posts from Instagram user with pagination for unlimited downloads."""
        try:
            posts = []
            next_cursor = None
            total_retrieved = 0
            
            while True:
                # Break if we've reached the limit
                if max_posts > 0 and total_retrieved >= max_posts:
                    break
                
                # Get batch of posts
                batch_limit = 50  # Instagram API limit
                if max_posts > 0:
                    batch_limit = min(50, max_posts - total_retrieved)
                    if batch_limit <= 0:
                        break
                
                batch_posts = self._fetch_user_posts_batch(username, batch_limit, next_cursor)
                
                if not batch_posts:
                    logging.info(f"No more posts available for @{username}")
                    break
                
                posts.extend(batch_posts)
                total_retrieved += len(batch_posts)
                
                logging.info(f"Retrieved {total_retrieved} posts from @{username}")
                
                # Get next cursor for pagination
                next_cursor = self._extract_next_cursor(batch_posts)
                if not next_cursor:
                    logging.info(f"Reached end of posts for @{username}")
                    break
                
                # Rate limiting between requests
                time.sleep(2)
                
            logging.info(f"Total retrieved: {len(posts)} posts from @{username}")
            return posts
            
        except Exception as e:
            logging.error(f"Error getting bulk user posts: {e}")
            return []
            
    def _fetch_user_posts_batch(self, username: str, limit: int, cursor: str = None) -> List[Dict[str, Any]]:
        """Fetch a batch of posts from user profile with pagination."""
        try:
            # This would require Instagram API implementation
            logging.warning("Instagram bulk posts fetching requires API integration")
            return []
        except Exception as e:
            logging.error(f"Error fetching post batch: {e}")
            return []
            
    def _extract_next_cursor(self, posts: List[Dict[str, Any]]) -> Optional[str]:
        """Extract pagination cursor from posts batch."""
        try:
            # Implementation would depend on Instagram API response structure
            return None
        except Exception as e:
            logging.error(f"Error extracting next cursor: {e}")
            return None
            
    def _get_post_info(self, url: str) -> Dict[str, Any]:
        """Get information about an Instagram post."""
        try:
            # This is a simplified implementation
            # In a real application, you would use Instagram's API or a proper scraper
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # Add ?__a=1 to get JSON response (may not work with current Instagram)
            json_url = url + '?__a=1' if '?' not in url else url + '&__a=1'
            
            response = requests.get(json_url, headers=headers)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    # Parse the JSON structure (simplified)
                    return self._parse_post_json(data)
                except json.JSONDecodeError:
                    # Fallback to HTML parsing
                    return self._parse_post_html(response.text)
            else:
                # Try HTML parsing
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                return self._parse_post_html(response.text)
                
        except Exception as e:
            logging.error(f"Error getting post info: {e}")
            return {}
            
    def _get_user_posts(self, username: str, limit: int) -> List[Dict[str, Any]]:
        """Get posts from an Instagram user."""
        try:
            # This is a simplified implementation
            # In a real application, you would use Instagram's API
            
            posts = []
            # Mock implementation - in reality you'd scrape or use API
            
            # For demonstration, we'll return empty list with error message
            logging.warning("User posts fetching not fully implemented - requires proper Instagram API integration")
            return []
            
        except Exception as e:
            logging.error(f"Error getting user posts: {e}")
            return []
            
    def _download_user_stories(self, username: str, download_path: str) -> Dict[str, Any]:
        """Download user's Instagram stories."""
        try:
            # Stories are ephemeral and require special handling
            # This would require Instagram API access
            
            logging.warning("Stories download not fully implemented - requires Instagram API access")
            return {'success': True, 'files_downloaded': 0}
            
        except Exception as e:
            logging.error(f"Error downloading stories: {e}")
            return {'success': False, 'error': str(e)}
            
    def _download_user_highlights(self, username: str, download_path: str) -> Dict[str, Any]:
        """Download user's Instagram highlights."""
        try:
            highlights_path = os.path.join(download_path, "highlights")
            os.makedirs(highlights_path, exist_ok=True)
            
            # Get highlights data
            highlights = self._get_user_highlights(username)
            if not highlights:
                return {'success': True, 'files_downloaded': 0, 'message': 'No highlights found'}
                
            downloaded_count = 0
            
            for highlight in highlights:
                try:
                    highlight_id = highlight.get('id', 'unknown')
                    highlight_title = self.sanitize_filename(highlight.get('title', f'highlight_{highlight_id}'))
                    highlight_path = os.path.join(highlights_path, highlight_title)
                    os.makedirs(highlight_path, exist_ok=True)
                    
                    # Download highlight items
                    items = highlight.get('items', [])
                    for i, item in enumerate(items):
                        media_url = item.get('video_url') or item.get('image_url')
                        if media_url:
                            extension = 'mp4' if item.get('video_url') else 'jpg'
                            filename = f"{highlight_title}_{i+1:03d}.{extension}"
                            output_path = os.path.join(highlight_path, filename)
                            
                            if self._download_file(media_url, output_path):
                                downloaded_count += 1
                                
                        time.sleep(1)
                        
                except Exception as e:
                    logging.warning(f"Failed to download highlight {highlight.get('id', 'unknown')}: {e}")
                    continue
                    
            return {
                'success': True,
                'files_downloaded': downloaded_count,
                'total_highlights': len(highlights)
            }
            
        except Exception as e:
            logging.error(f"Error downloading highlights: {e}")
            return {'success': False, 'error': str(e)}
            
    def _get_user_highlights(self, username: str) -> List[Dict[str, Any]]:
        """Get user's highlights data."""
        try:
            # This would require Instagram API implementation for highlights
            logging.warning("Highlights fetching requires Instagram API integration")
            return []
        except Exception as e:
            logging.error(f"Error getting highlights: {e}")
            return []
            
    def _download_post_media(self, post_info: Dict[str, Any], download_path: str, 
                           progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        """Download media from a post."""
        try:
            post_id = post_info.get('id', 'unknown')
            media_items = post_info.get('media', [])
            
            if not media_items:
                return {'success': False, 'error': 'No media found in post'}
                
            downloaded_count = 0
            total_items = len(media_items)
            
            for i, media_item in enumerate(media_items):
                try:
                    media_url = media_item.get('url')
                    media_type = media_item.get('type', 'unknown')
                    
                    if not media_url:
                        continue
                        
                    # Generate filename
                    extension = self._get_extension_from_url(media_url)
                    filename = f"{post_id}_{i+1:03d}.{extension}"
                    
                    output_path = os.path.join(download_path, filename)
                    
                    if self.file_exists(output_path):
                        downloaded_count += 1
                        continue
                        
                    # Download file
                    if self._download_file(media_url, output_path):
                        downloaded_count += 1
                        
                    if progress_callback:
                        progress = int(((i + 1) / total_items) * 100)
                        progress_callback(progress)
                        
                    time.sleep(1)  # Rate limiting
                    
                except Exception as e:
                    logging.warning(f"Failed to download media item {i}: {e}")
                    continue
                    
            return {
                'success': True,
                'files_downloaded': downloaded_count,
                'total_media': total_items
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    def _parse_post_json(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Instagram post JSON data."""
        try:
            # This is a simplified parser
            # The actual Instagram JSON structure is complex and changes frequently
            
            post_info = {
                'id': 'unknown',
                'media': []
            }
            
            # Extract media URLs (simplified)
            # Real implementation would handle the complex nested structure
            
            return post_info
            
        except Exception as e:
            logging.error(f"Error parsing post JSON: {e}")
            return {}
            
    def _parse_post_html(self, html: str) -> Dict[str, Any]:
        """Parse Instagram post HTML for media URLs."""
        try:
            # This is a very simplified HTML parser
            # In reality, you'd use BeautifulSoup or similar
            
            post_info = {
                'id': 'unknown',
                'media': []
            }
            
            # Extract media URLs from HTML (simplified)
            # This would require proper HTML parsing
            
            return post_info
            
        except Exception as e:
            logging.error(f"Error parsing post HTML: {e}")
            return {}
            
    def _download_file(self, url: str, output_path: str) -> bool:
        """Download a file from URL."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, stream=True)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        
            return True
            
        except Exception as e:
            logging.error(f"Error downloading file {url}: {e}")
            if os.path.exists(output_path):
                os.remove(output_path)
            return False
            
    def _get_extension_from_url(self, url: str) -> str:
        """Get file extension from URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            path = parsed.path
            
            if '.' in path:
                return path.split('.')[-1].lower()
            else:
                return 'jpg'  # Default for Instagram
                
        except:
            return 'jpg'
