"""
Twitter downloader for tweets, images, and videos.
"""

import os
import logging
import requests
import json
import time
import re
from typing import Dict, Any, Callable, Optional, List
from urllib.parse import urlparse

from .base_downloader import BaseDownloader

class TwitterDownloader(BaseDownloader):
    """Twitter content downloader."""

    def __init__(self, config_manager):
        super().__init__(config_manager)
        self.platform = "twitter"
        self.bearer_token = None  # Will need to be set via configuration

    def download(self, url: str, options: Dict[str, Any], 
                progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        """Download Twitter content with bulk optimization."""
        try:
            self.log_download_start(self.platform, url)

            # Determine if it's a username or tweet URL
            if self._is_tweet_url(url):
                result = self._download_single_tweet(url, options, progress_callback)
            else:
                result = self._download_user_content_bulk(url, options, progress_callback)

            if result['success']:
                self.log_download_complete(self.platform, url, result.get('files_downloaded', 0))
            else:
                self.log_download_error(self.platform, url, result.get('error', 'Unknown error'))

            return result

        except Exception as e:
            error_msg = f"Twitter download failed: {str(e)}"
            self.log_download_error(self.platform, url, error_msg)
            return {'success': False, 'error': error_msg}

    def _download_user_content_bulk(self, username: str, options: Dict[str, Any], 
                                   progress_callback: Optional[Callable[[int], None]]) -> Dict[str, Any]:
        """Download all content from Twitter user with bulk optimization."""
        try:
            username = username.replace('@', '').strip()
            max_tweets = options.get('limit', 0)  # 0 = unlimited

            # Get user's tweets with pagination
            tweets = self._get_user_tweets_bulk(username, max_tweets)
            if not tweets:
                return {'success': False, 'error': 'No tweets found or failed to fetch user content'}

            download_path = self.get_download_path(self.platform, username)
            total_tweets = len(tweets)
            downloaded_count = 0

            # Process in batches for efficiency
            batch_size = 20
            for batch_start in range(0, total_tweets, batch_size):
                batch_end = min(batch_start + batch_size, total_tweets)
                batch_tweets = tweets[batch_start:batch_end]

                for i, tweet_info in enumerate(batch_tweets):
                    try:
                        current_index = batch_start + i
                        if progress_callback:
                            progress = int((current_index / total_tweets) * 100)
                            progress_callback(progress)

                        result = self._download_tweet_media(tweet_info, download_path)
                        if result.get('success', False):
                            downloaded_count += result.get('files_downloaded', 0)

                        # Minimal delay for bulk operations
                        time.sleep(0.5)

                    except Exception as e:
                        logging.warning(f"Failed to download tweet {tweet_info.get('id', 'unknown')}: {e}")
                        continue

                # Batch delay to respect rate limits
                time.sleep(2)

            if progress_callback:
                progress_callback(100)

            return {
                'success': True,
                'files_downloaded': downloaded_count,
                'total_tweets': total_tweets
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _get_user_tweets_bulk(self, username: str, max_tweets: int = 0) -> List[Dict[str, Any]]:
        """Get all tweets from user with pagination for unlimited downloads."""
        try:
            tweets = []
            next_cursor = None
            total_retrieved = 0

            while True:
                if max_tweets > 0 and total_retrieved >= max_tweets:
                    break

                # Twitter API typically allows 200 tweets per request
                batch_limit = 200
                if max_tweets > 0:
                    batch_limit = min(200, max_tweets - total_retrieved)
                    if batch_limit <= 0:
                        break

                batch_tweets = self._fetch_user_tweets_batch(username, batch_limit, next_cursor)

                if not batch_tweets:
                    logging.info(f"No more tweets available for @{username}")
                    break

                tweets.extend(batch_tweets)
                total_retrieved += len(batch_tweets)

                logging.info(f"Retrieved {total_retrieved} tweets from @{username}")

                # Get next cursor for pagination
                next_cursor = self._extract_tweets_cursor(batch_tweets)
                if not next_cursor:
                    logging.info(f"Reached end of tweets for @{username}")
                    break

                # Rate limiting
                time.sleep(1)

            logging.info(f"Total retrieved: {len(tweets)} tweets from @{username}")
            return tweets

        except Exception as e:
            logging.error(f"Error getting bulk user tweets: {e}")
            return []

    def _fetch_user_tweets_batch(self, username: str, limit: int, cursor: str = None) -> List[Dict[str, Any]]:
        """Fetch a batch of tweets from user with pagination."""
        try:
            # This would require Twitter API v2 implementation
            logging.warning("Twitter bulk tweets fetching requires API integration")
            return []
        except Exception as e:
            logging.error(f"Error fetching tweets batch: {e}")
            return []

    def _extract_tweets_cursor(self, tweets: List[Dict[str, Any]]) -> Optional[str]:
        """Extract pagination cursor from tweets batch."""
        try:
            # Implementation would depend on Twitter API response
            return None
        except Exception as e:
            logging.error(f"Error extracting tweets cursor: {e}")
            return None

    def _is_tweet_url(self, url: str) -> bool:
        """Check if the URL is a single tweet URL."""
        return '/status/' in url and 'twitter.com' in url

    def _download_single_tweet(self, url: str, options: Dict[str, Any], 
                             progress_callback: Optional[Callable[[int], None]]) -> Dict[str, Any]:
        """Download a single tweet."""
        try:
            # Extract tweet ID
            tweet_id = self._extract_tweet_id(url)
            if not tweet_id:
                return {'success': False, 'error': 'Could not extract tweet ID from URL'}

            # Get tweet info
            tweet_info = self._get_tweet_info(tweet_id)
            if not tweet_info:
                return {'success': False, 'error': 'Failed to get tweet information'}

            download_path = self.get_download_path(self.platform)

            # Download media from tweet
            result = self._download_tweet_media(tweet_info, download_path, progress_callback)
            return result

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _download_user_timeline(self, username: str, options: Dict[str, Any], 
                              progress_callback: Optional[Callable[[int], None]]) -> Dict[str, Any]:
        """Download content from a Twitter user's timeline."""
        try:
            # Clean username
            username = username.replace('@', '').strip()
            if 'twitter.com/' in username:
                username = username.split('/')[-1]

            # Get user's tweets
            tweets = self._get_user_tweets(username, options.get('limit', 50))
            if not tweets:
                return {'success': False, 'error': 'No tweets found or failed to fetch user timeline'}

            download_path = self.get_download_path(self.platform, username)
            total_tweets = len(tweets)
            downloaded_count = 0

            for i, tweet_info in enumerate(tweets):
                try:
                    if progress_callback:
                        progress = int((i / total_tweets) * 100)
                        progress_callback(progress)

                    result = self._download_tweet_media(tweet_info, download_path)

                    if result.get('success', False):
                        downloaded_count += result.get('files_downloaded', 0)

                    # Rate limiting
                    time.sleep(1)

                except Exception as e:
                    logging.warning(f"Failed to download media from tweet {tweet_info.get('id', 'unknown')}: {e}")
                    continue

            if progress_callback:
                progress_callback(100)

            return {
                'success': True,
                'files_downloaded': downloaded_count,
                'total_tweets': total_tweets
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _extract_tweet_id(self, url: str) -> str:
        """Extract tweet ID from Twitter URL."""
        try:
            if '/status/' in url:
                return url.split('/status/')[-1].split('?')[0]
            return ""
        except:
            return ""

    def _get_tweet_info(self, tweet_id: str) -> Dict[str, Any]:
        """Get information about a tweet."""
        try:
            # This would require Twitter API access
            # For now, we'll use a fallback approach with web scraping

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }

            # Try to get tweet data
            tweet_url = f"https://twitter.com/i/status/{tweet_id}"

            # This is a simplified approach - real implementation would need proper API access
            tweet_info = {
                'id': tweet_id,
                'text': f'Tweet {tweet_id}',
                'media': [],
                'user': 'unknown'
            }

            # Note: This implementation is basic and would require actual Twitter API integration
            # or advanced web scraping techniques for real functionality

            return tweet_info

        except Exception as e:
            logging.error(f"Error getting tweet info: {e}")
            return {}

    def _get_user_tweets(self, username: str, limit: int) -> List[Dict[str, Any]]:
        """Get tweets from a Twitter user."""
        try:
            # This would require Twitter API access
            # For now, return empty list with warning

            logging.warning("Twitter user timeline fetching requires API access - please configure Twitter API credentials")
            return []

        except Exception as e:
            logging.error(f"Error getting user tweets: {e}")
            return []

    def _download_tweet_media(self, tweet_info: Dict[str, Any], download_path: str, 
                            progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        """Download media from a tweet including videos, images, and GIFs."""
        try:
            tweet_id = tweet_info['id']
            media_items = tweet_info.get('media', [])

            if not media_items:
                return {'success': True, 'files_downloaded': 0, 'message': 'No media found in tweet'}

            downloaded_count = 0
            total_items = len(media_items)

            for i, media_item in enumerate(media_items):
                try:
                    media_url = media_item.get('url')
                    media_type = media_item.get('type', 'unknown')
                    
                    # Handle different media types
                    if media_type == 'video':
                        # For Twitter videos, get the best quality variant
                        video_variants = media_item.get('video_info', {}).get('variants', [])
                        if video_variants:
                            # Sort by bitrate and get highest quality
                            best_variant = max(video_variants, key=lambda x: x.get('bitrate', 0))
                            media_url = best_variant.get('url')
                    elif media_type == 'animated_gif':
                        # Handle Twitter GIFs
                        video_variants = media_item.get('video_info', {}).get('variants', [])
                        if video_variants:
                            media_url = video_variants[0].get('url')

                    if not media_url:
                        continue

                    # Generate filename with proper extension
                    if media_type == 'video' or media_type == 'animated_gif':
                        extension = 'mp4'
                    else:
                        extension = self._get_extension_from_url(media_url) or 'jpg'
                        
                    filename = f"tweet_{tweet_id}_{media_type}_{i+1:03d}.{extension}"
                    output_path = os.path.join(download_path, filename)

                    if self.file_exists(output_path):
                        downloaded_count += 1
                        continue

                    # Download file with enhanced error handling
                    if self._download_file(media_url, output_path, progress_callback):
                        downloaded_count += 1

                    if progress_callback:
                        progress = int(((i + 1) / total_items) * 100)
                        progress_callback(progress)

                    time.sleep(0.5)  # Rate limiting

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

    def _get_extension_from_url(self, url: str) -> str:
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

    def _download_file(self, url: str, output_path: str, 
                      progress_callback: Optional[Callable[[int], None]] = None) -> bool:
        """Download a file from URL."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://twitter.com/'
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

    def set_bearer_token(self, bearer_token: str):
        """Set Twitter API bearer token."""
        self.bearer_token = bearer_token

    def _get_api_headers(self) -> Dict[str, str]:
        """Get headers for Twitter API requests."""
        return {
            'Authorization': f'Bearer {self.bearer_token}',
            'User-Agent': 'Social Media Downloader Bot 1.0'
        } if self.bearer_token else {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }