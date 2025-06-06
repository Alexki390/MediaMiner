"""
Erome.com downloader for adult content with album support.
"""

import os
import logging
import requests
import time
import re
import json
from typing import Dict, Any, Callable, Optional, List
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import cloudscraper

from .base_downloader import BaseDownloader
from utils.protection_bypass import ProtectionBypass
from utils.error_handler import ErrorHandler

class EromeDownloader(BaseDownloader):
    """Erome.com content downloader with full album support."""

    def __init__(self, config_manager):
        super().__init__(config_manager)
        self.platform = "erome"
        self.protection_bypass = ProtectionBypass()
        self.error_handler = ErrorHandler()
        try:
            self.scraper = cloudscraper.create_scraper()
        except:
            self.scraper = requests.Session()
            self.scraper.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })

        # Rate limiting
        self.rate_limit = 5  # requests per minute
        self.delay = 12      # seconds between requests

    def download(self, url: str, options: Dict[str, Any], 
                progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        """Download content from Erome."""
        try:
            self.log_download_start(self.platform, url)

            # Determine content type
            if '/a/' in url:
                result = self._download_album(url, options, progress_callback)
            elif '/u/' in url:
                result = self._download_user_profile(url, options, progress_callback)
            else:
                result = self._download_single_post(url, options, progress_callback)

            if result['success']:
                self.log_download_complete(self.platform, url, result.get('files_downloaded', 0))
            else:
                self.log_download_error(self.platform, url, result.get('error', 'Unknown error'))

            return result

        except Exception as e:
            error_msg = f"Erome download failed: {str(e)}"
            self.log_download_error(self.platform, url, error_msg)
            return self.error_handler.handle_error(e, "erome_download", {"url": url})

    def _download_album(self, url: str, options: Dict[str, Any], 
                       progress_callback: Optional[Callable[[int], None]]) -> Dict[str, Any]:
        """Download complete Erome album."""
        try:
            response = self.scraper.get(url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract album info
            album_title = soup.find('h1', class_='title')
            title = album_title.get_text(strip=True) if album_title else 'erome_album'

            # Extract media URLs
            media_items = []

            # Videos
            video_sources = soup.find_all('source', {'type': 'video/mp4'})
            for source in video_sources:
                src = source.get('src')
                if src:
                    media_items.append({
                        'url': urljoin(url, src),
                        'type': 'video',
                        'extension': 'mp4'
                    })

            # Images
            img_tags = soup.find_all('img', class_='img-front')
            for img in img_tags:
                src = img.get('data-src') or img.get('src')
                if src and not src.endswith('.gif'):
                    media_items.append({
                        'url': urljoin(url, src),
                        'type': 'image',
                        'extension': 'jpg'
                    })

            if not media_items:
                return {'success': False, 'error': 'No media found in album'}

            # Download all media
            download_path = self.get_download_path('erome', self.sanitize_filename(title))
            downloaded_count = 0

            for i, item in enumerate(media_items):
                try:
                    filename = f"{title}_{i+1:03d}.{item['extension']}"
                    output_path = os.path.join(download_path, self.sanitize_filename(filename))

                    if not self.file_exists(output_path):
                        if self._download_media_file(item['url'], output_path):
                            downloaded_count += 1
                    else:
                        downloaded_count += 1

                    if progress_callback:
                        progress = int(((i + 1) / len(media_items)) * 100)
                        progress_callback(progress)

                    # Rate limiting
                    time.sleep(self.delay)

                except Exception as e:
                    logging.warning(f"Failed to download media {i+1}: {e}")
                    continue

            return {
                'success': True,
                'files_downloaded': downloaded_count,
                'total_media': len(media_items),
                'album_title': title
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _download_user_profile(self, url: str, options: Dict[str, Any], 
                              progress_callback: Optional[Callable[[int], None]]) -> Dict[str, Any]:
        """Download all albums from a user profile."""
        try:
            max_pages = options.get('max_pages', 10)
            page = 1
            total_albums = 0
            total_files = 0

            while page <= max_pages:
                page_url = f"{url}?page={page}"

                try:
                    response = self.scraper.get(page_url, timeout=30)
                    response.raise_for_status()

                    soup = BeautifulSoup(response.text, 'html.parser')

                    # Find album links
                    album_links = soup.find_all('a', href=re.compile(r'/a/'))

                    if not album_links:
                        break

                    for link in album_links:
                        album_url = urljoin(url, link.get('href'))

                        try:
                            album_result = self._download_album(album_url, options, None)
                            if album_result['success']:
                                total_files += album_result.get('files_downloaded', 0)
                                total_albums += 1

                            # Progress update
                            if progress_callback:
                                progress = min(int((page / max_pages) * 100), 100)
                                progress_callback(progress)

                        except Exception as e:
                            logging.warning(f"Failed to download album {album_url}: {e}")
                            continue

                    page += 1
                    time.sleep(self.delay * 2)  # Longer delay between pages

                except Exception as e:
                    logging.error(f"Error processing page {page}: {e}")
                    break

            return {
                'success': True,
                'albums_downloaded': total_albums,
                'files_downloaded': total_files,
                'pages_processed': page - 1
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _download_single_post(self, url: str, options: Dict[str, Any], 
                             progress_callback: Optional[Callable[[int], None]]) -> Dict[str, Any]:
        """Download single Erome post."""
        return self._download_album(url, options, progress_callback)

    def _download_media_file(self, url: str, output_path: str) -> bool:
        """Download a single media file."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://www.erome.com/'
            }

            response = self.scraper.get(url, headers=headers, stream=True, timeout=60)
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