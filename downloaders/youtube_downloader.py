"""
YouTube downloader using yt-dlp.
"""

import os
import logging
import time
from typing import Dict, Any, Callable, Optional, List
import subprocess
import json
import tempfile

from .base_downloader import BaseDownloader
from utils.auth_manager import AuthManager
from utils.error_handler import ErrorHandler
from utils.cookie_manager import CookieManager

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    GOOGLE_AUTH_AVAILABLE = True
except ImportError:
    GOOGLE_AUTH_AVAILABLE = False

try:
    import browser_cookie3
    BROWSER_COOKIES_AVAILABLE = True
except ImportError:
    BROWSER_COOKIES_AVAILABLE = False

class YouTubeDownloader(BaseDownloader):
    """YouTube content downloader."""

    def __init__(self, config_manager):
        super().__init__(config_manager)
        self.platform = "youtube"
        self.auth_manager = AuthManager(config_manager)
        self.error_handler = ErrorHandler(config_manager)
        self.cookie_manager = CookieManager(config_manager)

        # Authentication setup
        self.cookies_file = None
        self.oauth_credentials = None
        self.authenticated = False

        # Setup authentication
        self._setup_authentication()

    def download_bulk(self, urls: list[str], options: Dict[str, Any], 
                     progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        """Download multiple YouTube videos in bulk."""
        try:
            total_urls = len(urls)
            successful_downloads = 0
            failed_downloads = 0

            for i, url in enumerate(urls):
                try:
                    if progress_callback:
                        progress = int((i / total_urls) * 100)
                        progress_callback(progress)

                    result = self.download(url, options)
                    if result.get('success', False):
                        successful_downloads += 1
                    else:
                        failed_downloads += 1

                    # Rate limiting
                    time.sleep(2)

                except Exception as e:
                    logging.warning(f"Failed to download {url}: {e}")
                    failed_downloads += 1
                    continue

            if progress_callback:
                progress_callback(100)

            return {
                'success': True,
                'total_downloads': successful_downloads,
                'failed_downloads': failed_downloads,
                'total_processed': total_urls
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def download(self, url: str, options: Dict[str, Any], 
                progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        """Download YouTube content."""
        try:
            self.log_download_start(self.platform, url)

            # Prepare download path
            download_path = self.get_download_path(self.platform)

            # Build yt-dlp command
            cmd = self._build_ytdlp_command(url, options, download_path)

            # Execute download
            result = self._execute_download(cmd, progress_callback)

            if result['success']:
                self.log_download_complete(self.platform, url, result.get('files_downloaded', 0))
            else:
                self.log_download_error(self.platform, url, result.get('error', 'Unknown error'))

            return result

        except Exception as e:
            error_msg = f"YouTube download failed: {str(e)}"
            self.log_download_error(self.platform, url, error_msg)
            return {'success': False, 'error': error_msg}

    def _setup_authentication(self):
        """Setup YouTube authentication for age-restricted content."""
        try:
            # Try to get cookies file (prefer manual)
            cookies_file = self.cookie_manager.get_cookies_file('youtube', prefer_manual=True)
            if cookies_file and self.cookie_manager.validate_cookies_file(cookies_file):
                self.cookies_file = cookies_file
                self.authenticated = True
                logging.info(f"Loaded YouTube cookies from {cookies_file}")
            else:
                # Try to load existing session
                session_data = self.auth_manager.get_session('youtube')
                if session_data and 'cookies_file' in session_data:
                    self.cookies_file = session_data['cookies_file']
                    if os.path.exists(self.cookies_file):
                        self.authenticated = True
                        logging.info("Loaded YouTube authentication from session")

        except Exception as e:
            logging.warning(f"Failed to load YouTube session: {e}")

    def login_with_browser_cookies(self, browser: str = 'chrome') -> bool:
        """Login using browser cookies for age-restricted content."""
        try:
            if not BROWSER_COOKIES_AVAILABLE:
                logging.error("browser_cookie3 not available")
                return False

            # Extract cookies from browser
            if browser.lower() == 'chrome':
                cookies = browser_cookie3.chrome(domain_name='youtube.com')
            elif browser.lower() == 'firefox':
                cookies = browser_cookie3.firefox(domain_name='youtube.com')
            elif browser.lower() == 'edge':
                cookies = browser_cookie3.edge(domain_name='youtube.com')
            else:
                logging.error(f"Unsupported browser: {browser}")
                return False

            # Create cookies file for yt-dlp
            cookies_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
            cookies_file.write("# Netscape HTTP Cookie File\n")

            for cookie in cookies:
                if 'youtube.com' in cookie.domain:
                    # Format: domain, flag, path, secure, expiration, name, value
                    cookies_file.write(f"{cookie.domain}\tTRUE\t{cookie.path}\t{str(cookie.secure).upper()}\t{int(cookie.expires) if cookie.expires else 0}\t{cookie.name}\t{cookie.value}\n")

            cookies_file.close()
            self.cookies_file = cookies_file.name

            # Save session
            session_data = {
                'cookies_file': self.cookies_file,
                'browser': browser
            }
            self.auth_manager.create_session('youtube', session_data, expires_in=86400)  # 24 hours

            self.authenticated = True
            logging.info(f"Successfully extracted YouTube cookies from {browser}")
            return True

        except Exception as e:
            logging.error(f"Failed to extract browser cookies: {e}")
            return False

    def login_with_google_oauth(self, client_secrets_file: str = None) -> bool:
        """Login using Google OAuth for full API access."""
        try:
            if not GOOGLE_AUTH_AVAILABLE:
                logging.error("Google Auth libraries not available")
                return False

            if not client_secrets_file or not os.path.exists(client_secrets_file):
                logging.error("Google OAuth client secrets file not found")
                return False

            SCOPES = ['https://www.googleapis.com/auth/youtube.readonly']

            creds = None
            # Load existing credentials
            token_file = os.path.join(self.auth_manager.auth_dir, 'youtube_token.json')

            if os.path.exists(token_file):
                creds = Credentials.from_authorized_user_file(token_file, SCOPES)

            # If there are no (valid) credentials available, let the user log in
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, SCOPES)
                    creds = flow.run_local_server(port=0)

                # Save the credentials for the next run
                with open(token_file, 'w') as token:
                    token.write(creds.to_json())

            self.oauth_credentials = creds
            self.authenticated = True
            logging.info("Successfully authenticated with Google OAuth")
            return True

        except Exception as e:
            logging.error(f"Google OAuth authentication failed: {e}")
            return False

    def set_manual_cookies(self, cookies_text: str, format_type: str = 'netscape') -> bool:
        """Set manual cookies for YouTube authentication."""
        try:
            success = self.cookie_manager.store_manual_cookies('youtube', cookies_text, format_type)
            if success:
                # Update current cookies file
                cookies_file = self.cookie_manager.get_cookies_file('youtube', prefer_manual=True)
                if cookies_file:
                    self.cookies_file = cookies_file
                    self.authenticated = True
                    logging.info("Manual YouTube cookies set successfully")
                    return True
            return False

        except Exception as e:
            logging.error(f"Failed to set manual cookies: {e}")
            return False

    def get_cookie_template(self) -> str:
        """Get a template for manual cookie input."""
        return self.cookie_manager.export_cookies_template('youtube')

    def get_available_cookies(self) -> Dict[str, List[str]]:
        """Get list of available cookie files."""
        return self.cookie_manager.list_available_cookies().get('youtube', [])

    def check_age_restricted(self, url: str) -> bool:
        """Check if a video is age-restricted."""
        try:
            cmd = ['yt-dlp', '--dump-json', '--no-download', url]

            if self.cookies_file and os.path.exists(self.cookies_file):
                cmd.extend(['--cookies', self.cookies_file])

            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()

            if process.returncode == 0:
                video_info = json.loads(stdout)
                return video_info.get('age_limit', 0) > 0
            else:
                # If we can't get info, assume it might be age-restricted
                return 'age' in stderr.lower() or 'restricted' in stderr.lower()

        except Exception as e:
            logging.warning(f"Could not check age restriction: {e}")
            return False

    def _build_ytdlp_command(self, url: str, options: Dict[str, Any], download_path: str) -> list:
        """Build yt-dlp command based on options."""
        cmd = ['yt-dlp']

        # Output template
        if options.get('entire_channel', False):
            output_template = os.path.join(download_path, '%(uploader)s', '%(title)s.%(ext)s')
        else:
            output_template = os.path.join(download_path, '%(title)s.%(ext)s')

        cmd.extend(['-o', output_template])

        # Quality selection
        quality = options.get('quality', self.config['default_video_quality'])
        if options.get('audio_only', False):
            cmd.extend(['-f', 'bestaudio/best'])
            cmd.extend(['--extract-audio'])
            audio_format = options.get('audio_format', self.config['audio_format'])
            if audio_format != 'best':
                cmd.extend(['--audio-format', audio_format])
        else:
            if quality == 'best':
                cmd.extend(['-f', 'best'])
            elif quality == 'worst':
                cmd.extend(['-f', 'worst'])
            else:
                # Specific quality
                quality_num = quality.replace('p', '')
                cmd.extend(['-f', f'best[height<={quality_num}]'])

        # Additional options
        cmd.extend(['--write-info-json'])  # Save metadata
        cmd.extend(['--write-thumbnail'])  # Save thumbnails
        cmd.extend(['--no-overwrites'])    # Don't overwrite files

        if self.config['skip_existing_files']:
            cmd.extend(['--download-archive', os.path.join(download_path, 'archive.txt')])

        # Playlist handling
        if options.get('entire_channel', False):
            cmd.extend(['--yes-playlist'])
        else:
            cmd.extend(['--no-playlist'])

        # Add authentication if available
        if self.cookies_file and os.path.exists(self.cookies_file):
            cmd.extend(['--cookies', self.cookies_file])
            logging.info("Using cookies for YouTube authentication")

        # Handle age-restricted content
        if options.get('age_restricted', False) or self.check_age_restricted(url):
            if not self.authenticated:
                logging.warning("Age-restricted content detected but no authentication available")
                # Try to use browser cookies automatically
                if self.login_with_browser_cookies():
                    cmd.extend(['--cookies', self.cookies_file])
            cmd.extend(['--age-limit', '99'])

        # Enhanced error handling for restricted content
        cmd.extend(['--ignore-errors'])
        cmd.extend(['--no-abort-on-error'])

        # Add URL
        cmd.append(url)

        return cmd

    def _execute_download(self, cmd: list, progress_callback: Optional[Callable[[int], None]]) -> Dict[str, Any]:
        """Execute the yt-dlp command."""
        try:
            # Add progress hook if callback provided
            if progress_callback:
                cmd.extend(['--progress-hook', self._create_progress_hook(progress_callback)])

            # Execute command
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                universal_newlines=True
            )

            stdout, stderr = process.communicate()

            if process.returncode == 0:
                # Count downloaded files from output
                files_downloaded = self._count_downloaded_files(stdout)
                return {
                    'success': True,
                    'files_downloaded': files_downloaded,
                    'output': stdout
                }
            else:
                return {
                    'success': False,
                    'error': f"yt-dlp failed with return code {process.returncode}: {stderr}",
                    'output': stdout
                }

        except FileNotFoundError:
            return {
                'success': False,
                'error': "yt-dlp not found. Please install yt-dlp: pip install yt-dlp"
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Command execution failed: {str(e)}"
            }

    def _create_progress_hook(self, progress_callback: Callable[[int], None]) -> str:
        """Create a temporary progress hook script."""
        # For simplicity, we'll parse stdout for progress
        # In a real implementation, you might want to use yt-dlp's built-in progress hook
        return ""

    def _count_downloaded_files(self, output: str) -> int:
        """Count the number of files downloaded from yt-dlp output."""
        count = 0
        lines = output.split('\n')

        for line in lines:
            if '[download]' in line and 'Destination:' in line:
                count += 1
            elif '[download]' in line and '100%' in line:
                count += 1

        return max(count, 1)  # At least 1 if download was successful

    def get_video_info(self, url: str) -> Dict[str, Any]:
        """Get video information without downloading."""
        try:
            cmd = ['yt-dlp', '--dump-json', '--no-playlist', url]

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = process.communicate()

            if process.returncode == 0:
                return json.loads(stdout)
            else:
                logging.error(f"Failed to get video info: {stderr}")
                return {}

        except Exception as e:
            logging.error(f"Error getting video info: {e}")
            return {}