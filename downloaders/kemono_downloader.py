"""
Kemono.su downloader for Patreon and other platform content.
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
from utils.protection_bypass import get_protection_bypass

class KemonoDownloader(BaseDownloader):
    """Kemono.su content downloader."""

    def __init__(self, config_manager):
        super().__init__(config_manager)
        self.platform = "kemono"
        self.protection_bypass = get_protection_bypass(config_manager)
        self.base_url = "https://kemono.su"

    def download(self, url: str, options: Dict[str, Any], 
                progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        """Download Kemono.su content."""
        try:
            self.log_download_start(self.platform, url)

            # Parse the URL to determine the type
            if '/user/' in url:
                result = self._download_user_content(url, options, progress_callback)
            elif '/post/' in url:
                result = self._download_single_post(url, options, progress_callback)
            else:
                result = {'success': False, 'error': 'Unsupported URL format'}

            if result['success']:
                self.log_download_complete(self.platform, url, result.get('files_downloaded', 0))
            else:
                self.log_download_error(self.platform, url, result.get('error', 'Unknown error'))

            return result

        except Exception as e:
            error_msg = f"Kemono download failed: {str(e)}"
            self.log_download_error(self.platform, url, error_msg)
            return {'success': False, 'error': error_msg}

    def _download_user_content(self, url: str, options: Dict[str, Any], 
                             progress_callback: Optional[Callable[[int], None]]) -> Dict[str, Any]:
        """Download all content from a Kemono.su user."""
        try:
            # Extract service and user ID from URL
            service, user_id = self._parse_user_url(url)
            if not service or not user_id:
                return {'success': False, 'error': 'Could not parse user URL'}

            # Get all posts for user
            posts = self._get_user_posts(service, user_id, options.get('limit', 0))
            if not posts:
                return {'success': False, 'error': 'No posts found for user'}

            download_path = self.get_download_path(self.platform, f"{service}_{user_id}")
            total_posts = len(posts)
            downloaded_count = 0
            total_files = 0

            for i, post in enumerate(posts):
                try:
                    if progress_callback:
                        progress = int((i / total_posts) * 100)
                        progress_callback(progress)

                    result = self._download_post_media(post, download_path)

                    if result.get('success', False):
                        downloaded_count += 1
                        total_files += result.get('files_downloaded', 0)

                    # Rate limiting
                    time.sleep(2)

                except Exception as e:
                    logging.warning(f"Failed to download post {post.get('id', 'unknown')}: {e}")
                    continue

            if progress_callback:
                progress_callback(100)

            return {
                'success': True,
                'files_downloaded': total_files,
                'posts_downloaded': downloaded_count,
                'total_posts': total_posts
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _download_single_post(self, url: str, options: Dict[str, Any], 
                            progress_callback: Optional[Callable[[int], None]]) -> Dict[str, Any]:
        """Download a single post from Kemono.su."""
        try:
            post_data = self._get_post_data(url)
            if not post_data:
                return {'success': False, 'error': 'Failed to get post data'}

            download_path = self.get_download_path(self.platform)
            result = self._download_post_media(post_data, download_path, progress_callback)
            return result

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _parse_user_url(self, url: str) -> tuple:
        """Parse user URL to extract service and user ID."""
        try:
            # URL format: https://kemono.su/patreon/user/12345
            # or https://kemono.su/fanbox/user/12345
            parts = url.split('/')
            if len(parts) >= 5 and parts[4] == 'user':
                return parts[3], parts[5]
            return None, None
        except:
            return None, None

    def _get_user_posts(self, service: str, user_id: str, limit: int = 0) -> List[Dict[str, Any]]:
        """Get all posts from a user with unlimited pagination and robust error handling."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json, text/html, */*',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': f'{self.base_url}/{service}/user/{user_id}',
                'Cache-Control': 'no-cache'
            }

            posts = []
            offset = 0
            consecutive_failures = 0
            max_consecutive_failures = 5

            while True:
                # Break if we've reached the limit
                if limit > 0 and len(posts) >= limit:
                    break

                # Break if too many consecutive failures
                if consecutive_failures >= max_consecutive_failures:
                    logging.warning(f"Too many consecutive failures, stopping at offset {offset}")
                    break

                try:
                    # Try API first
                    api_url = f"{self.base_url}/api/v1/{service}/user/{user_id}"
                    params = {'o': offset}

                    response = requests.get(api_url, headers=headers, params=params, timeout=30)

                    if response.status_code == 429:  # Rate limited
                        logging.warning("Rate limited, waiting 30 seconds...")
                        time.sleep(30)
                        consecutive_failures += 1
                        continue

                    if response.status_code == 404:
                        logging.info(f"User {user_id} not found or no more content")
                        break

                    if response.status_code != 200:
                        logging.warning(f"API request failed with status {response.status_code}, trying HTML scraping...")
                        # Fallback to HTML scraping
                        user_page_url = f"{self.base_url}/{service}/user/{user_id}?o={offset}"
                        html_response = requests.get(user_page_url, headers=headers, timeout=30)
                        if html_response.status_code == 200:
                            html_posts = self._scrape_posts_from_html(html_response.text, service, user_id)
                            if html_posts:
                                posts.extend(html_posts)
                                offset += len(html_posts)
                                consecutive_failures = 0
                            else:
                                consecutive_failures += 1
                        else:
                            consecutive_failures += 1
                        time.sleep(3)
                        continue

                    try:
                        data = response.json()
                    except json.JSONDecodeError:
                        logging.warning("Invalid JSON response, trying HTML scraping...")
                        user_page_url = f"{self.base_url}/{service}/user/{user_id}?o={offset}"
                        html_response = requests.get(user_page_url, headers=headers, timeout=30)
                        if html_response.status_code == 200:
                            html_posts = self._scrape_posts_from_html(html_response.text, service, user_id)
                            if html_posts:
                                posts.extend(html_posts)
                                offset += len(html_posts)
                                consecutive_failures = 0
                            else:
                                consecutive_failures += 1
                        else:
                            consecutive_failures += 1
                        time.sleep(3)
                        continue

                    if not isinstance(data, list):
                        logging.warning(f"Unexpected data format: {type(data)}")
                        consecutive_failures += 1
                        time.sleep(3)
                        continue

                    if not data:
                        logging.info(f"Reached end of posts for {user_id} at offset {offset}")
                        break

                    # Filter out duplicates
                    new_posts = []
                    existing_ids = {post.get('id') for post in posts}

                    for post in data:
                        if limit > 0 and len(posts) + len(new_posts) >= limit:
                            break
                        if post.get('id') not in existing_ids:
                            new_posts.append(post)

                    posts.extend(new_posts)
                    consecutive_failures = 0

                    logging.info(f"Retrieved {len(new_posts)} new posts from offset {offset} for {user_id} (total: {len(posts)})")

                    offset += len(data)
                    time.sleep(2)  # Kemono requires more conservative rate limiting

                except requests.RequestException as e:
                    logging.warning(f"Network error at offset {offset}: {e}")
                    consecutive_failures += 1
                    time.sleep(5)
                    continue

                except Exception as e:
                    logging.error(f"Unexpected error at offset {offset}: {e}")
                    consecutive_failures += 1
                    time.sleep(3)
                    continue

            logging.info(f"Total retrieved: {len(posts)} posts from {user_id}")
            return posts

        except Exception as e:
            logging.error(f"Critical error getting user posts: {e}")
            return []

    def _scrape_posts_from_html(self, html_content: str, service: str, user_id: str) -> List[Dict[str, Any]]:
        """Scrape posts from HTML when API is not available."""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            posts = []

            # Find post containers
            post_elements = soup.find_all('article', class_='post-card')

            for post_elem in post_elements:
                try:
                    # Extract post link
                    post_link = post_elem.find('a')
                    if not post_link:
                        continue

                    post_url = post_link.get('href')
                    if not post_url.startswith('http'):
                        post_url = urljoin(self.base_url, post_url)

                    post_id = self._extract_post_id_from_url(post_url)

                    # Extract title
                    title_elem = post_elem.find('header')
                    title = title_elem.get_text(strip=True) if title_elem else f'post_{post_id}'

                    posts.append({
                        'id': post_id,
                        'title': title,
                        'url': post_url,
                        'service': service,
                        'user': user_id
                    })

                except Exception as e:
                    logging.warning(f"Error parsing post element: {e}")
                    continue

            return posts

        except Exception as e:
            logging.error(f"Error scraping posts from HTML: {e}")
            return []

    def _get_post_data(self, url: str) -> Dict[str, Any]:
        """Get data for a single post."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(url, headers=headers)
            response.raise_for_status()

            # Try API first
            post_id = self._extract_post_id_from_url(url)
            service, user_id = self._extract_service_user_from_url(url)

            if service and user_id and post_id:
                api_url = f"{self.base_url}/api/v1/{service}/user/{user_id}/post/{post_id}"
                api_response = requests.get(api_url, headers=headers)

                if api_response.status_code == 200:
                    try:
                        return api_response.json()
                    except:
                        pass

            # Fallback to HTML scraping
            soup = BeautifulSoup(response.text, 'html.parser')

            title_elem = soup.find('h1', class_='post__title') or soup.find('title')
            title = title_elem.get_text(strip=True) if title_elem else f'post_{post_id}'

            # Find attachments
            attachments = []
            file_links = soup.find_all('a', class_='post__attachment-link')

            for link in file_links:
                file_url = link.get('href')
                if file_url and not file_url.startswith('http'):
                    file_url = urljoin(self.base_url, file_url)

                filename = link.get_text(strip=True) or os.path.basename(file_url)

                attachments.append({
                    'name': filename,
                    'path': file_url
                })

            # Find embedded files
            file_elements = soup.find_all('div', class_='post__files')
            for file_div in file_elements:
                download_links = file_div.find_all('a', {'download': True})
                for link in download_links:
                    file_url = link.get('href')
                    if file_url and not file_url.startswith('http'):
                        file_url = urljoin(self.base_url, file_url)

                    filename = link.get('download') or os.path.basename(file_url)

                    attachments.append({
                        'name': filename,
                        'path': file_url
                    })

            return {
                'id': post_id,
                'title': title,
                'attachments': attachments,
                'file': {}
            }

        except Exception as e:
            logging.error(f"Error getting post data: {e}")
            return {}

    def _extract_post_id_from_url(self, url: str) -> str:
        """Extract post ID from URL."""
        try:
            parts = url.split('/')
            return parts[-1] if parts else str(hash(url))
        except:
            return "unknown"

    def _extract_service_user_from_url(self, url: str) -> tuple:
        """Extract service and user ID from post URL."""
        try:
            # URL format: https://kemono.su/patreon/user/12345/post/67890
            parts = url.split('/')
            if len(parts) >= 6 and parts[4] == 'user' and parts[6] == 'post':
                return parts[3], parts[5]
            return None, None
        except:
            return None, None

    def _download_post_media(self, post: Dict[str, Any], download_path: str, 
                           progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        """Download all media from a post."""
        try:
            post_id = post.get('id', 'unknown')
            title = self.sanitize_filename(post.get('title', f'post_{post_id}'))

            # Create post-specific directory
            post_dir = os.path.join(download_path, f"{post_id}_{title}")
            os.makedirs(post_dir, exist_ok=True)

            files_downloaded = 0

            # Get detailed post data if needed
            if 'url' in post and not post.get('attachments'):
                detailed_post = self._get_post_data(post['url'])
                post.update(detailed_post)

            # Download attachments
            attachments = post.get('attachments', [])
            total_files = len(attachments)

            # Add main file if exists
            if post.get('file', {}).get('path'):
                attachments.append(post['file'])
                total_files += 1

            for i, attachment in enumerate(attachments):
                try:
                    if progress_callback and total_files > 0:
                        progress = int((i / total_files) * 100)
                        progress_callback(progress)

                    file_url = attachment.get('path')
                    if not file_url:
                        continue

                    if not file_url.startswith('http'):
                        file_url = urljoin(self.base_url, file_url)

                    filename = attachment.get('name') or os.path.basename(file_url)
                    filename = self.sanitize_filename(filename)

                    output_path = os.path.join(post_dir, filename)

                    if self.file_exists(output_path):
                        continue

                    if self._download_file(file_url, output_path):
                        files_downloaded += 1

                except Exception as e:
                    logging.warning(f"Failed to download attachment: {e}")
                    continue

            if progress_callback:
                progress_callback(100)

            return {
                'success': True,
                'files_downloaded': files_downloaded,
                'output_directory': post_dir
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _download_file(self, url: str, output_path: str) -> bool:
        """Download a file from URL."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': self.base_url
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