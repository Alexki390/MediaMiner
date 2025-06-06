"""
Reddit downloader for subreddit content.
"""

import os
import logging
import requests
import json
import time
from typing import Dict, Any, Callable, Optional, List
from urllib.parse import urlparse

from .base_downloader import BaseDownloader

class RedditDownloader(BaseDownloader):
    """Reddit content downloader."""
    
    def __init__(self, config_manager):
        super().__init__(config_manager)
        self.platform = "reddit"
        self.supported_domains = {
            'imgur.com', 'i.imgur.com',
            'redgifs.com', 'gfycat.com',
            'i.redd.it', 'v.redd.it',
            'youtube.com', 'youtu.be'
        }
        
    def download(self, subreddit: str, options: Dict[str, Any], 
                progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        """Download content from a Reddit subreddit."""
        try:
            self.log_download_start(self.platform, f"r/{subreddit}")
            
            # Get subreddit posts
            posts = self._get_subreddit_posts(subreddit, options)
            if not posts:
                return {'success': False, 'error': 'No posts found or failed to fetch subreddit content'}
                
            download_path = self.get_download_path(self.platform, f"r_{subreddit}")
            
            # Download media from posts
            result = self._download_posts_media(posts, download_path, progress_callback)
            
            if result['success']:
                self.log_download_complete(self.platform, f"r/{subreddit}", result.get('files_downloaded', 0))
            else:
                self.log_download_error(self.platform, f"r/{subreddit}", result.get('error', 'Unknown error'))
                
            return result
            
        except Exception as e:
            error_msg = f"Reddit download failed: {str(e)}"
            self.log_download_error(self.platform, f"r/{subreddit}", error_msg)
            return {'success': False, 'error': error_msg}
            
    def _get_subreddit_posts(self, subreddit: str, options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get posts from a subreddit with pagination support for unlimited downloads."""
        try:
            sort_type = options.get('sort', 'hot')
            max_posts = options.get('limit', 0)  # 0 = unlimited
            posts = []
            after = None
            total_retrieved = 0
            
            while True:
                # Get batch of posts (Reddit API limit is 100)
                batch_limit = 100
                if max_posts > 0:
                    batch_limit = min(100, max_posts - total_retrieved)
                    if batch_limit <= 0:
                        break
                
                url = f"https://www.reddit.com/r/{subreddit}/{sort_type}.json"
                params = {
                    'limit': batch_limit,
                    'raw_json': 1
                }
                
                if after:
                    params['after'] = after
                
                headers = {
                    'User-Agent': 'Social Media Downloader Bot 1.0'
                }
                
                response = requests.get(url, params=params, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                batch_posts = data['data']['children']
                
                if not batch_posts:
                    logging.info(f"No more posts available in r/{subreddit}")
                    break
                
                for post_data in batch_posts:
                    post = post_data['data']
                    
                    # Extract relevant information
                    post_info = {
                        'id': post['id'],
                        'title': post['title'],
                        'url': post.get('url', ''),
                        'domain': post.get('domain', ''),
                        'author': post.get('author', 'unknown'),
                        'created_utc': post.get('created_utc', 0),
                        'score': post.get('score', 0),
                        'is_video': post.get('is_video', False),
                        'media': post.get('media', {}),
                        'preview': post.get('preview', {}),
                        'gallery_data': post.get('gallery_data', {}),
                        'media_metadata': post.get('media_metadata', {})
                    }
                    
                    posts.append(post_info)
                
                total_retrieved += len(batch_posts)
                after = data['data']['after']
                
                logging.info(f"Retrieved {total_retrieved} posts from r/{subreddit}")
                
                # Break if no more pages
                if not after:
                    logging.info(f"Reached end of subreddit r/{subreddit}")
                    break
                
                # Rate limiting between requests
                time.sleep(1)
                
            logging.info(f"Total retrieved: {len(posts)} posts from r/{subreddit}")
            return posts
            
        except Exception as e:
            logging.error(f"Error getting subreddit posts: {e}")
            return []
            
    def _download_posts_media(self, posts: List[Dict[str, Any]], download_path: str, 
                            progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        """Download media from Reddit posts."""
        try:
            total_posts = len(posts)
            downloaded_count = 0
            processed_count = 0
            
            for i, post in enumerate(posts):
                try:
                    if progress_callback:
                        progress = int((i / total_posts) * 100)
                        progress_callback(progress)
                        
                    # Download media from post
                    result = self._download_post_media(post, download_path)
                    
                    if result.get('success', False):
                        downloaded_count += result.get('files_downloaded', 0)
                        
                    processed_count += 1
                    
                    # Rate limiting
                    time.sleep(1)
                    
                except Exception as e:
                    logging.warning(f"Failed to process post {post.get('id', 'unknown')}: {e}")
                    continue
                    
            if progress_callback:
                progress_callback(100)
                
            return {
                'success': True,
                'files_downloaded': downloaded_count,
                'posts_processed': processed_count,
                'total_posts': total_posts
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    def _download_post_media(self, post: Dict[str, Any], download_path: str) -> Dict[str, Any]:
        """Download media from a single Reddit post."""
        try:
            post_id = post['id']
            url = post.get('url', '')
            domain = post.get('domain', '')
            
            if not url or not self._is_supported_domain(domain):
                return {'success': True, 'files_downloaded': 0}  # Skip unsupported content
                
            downloaded_files = 0
            
            # Handle different types of media
            if post.get('is_video', False):
                # Reddit video
                downloaded_files += self._download_reddit_video(post, download_path)
            elif 'gallery_data' in post and post['gallery_data']:
                # Reddit gallery
                downloaded_files += self._download_reddit_gallery(post, download_path)
            elif domain in ['i.redd.it']:
                # Direct Reddit image
                downloaded_files += self._download_direct_image(post, download_path)
            elif domain in ['imgur.com', 'i.imgur.com']:
                # Imgur content
                downloaded_files += self._download_imgur_content(post, download_path)
            elif domain in ['redgifs.com', 'gfycat.com']:
                # GIF hosting sites
                downloaded_files += self._download_gif_content(post, download_path)
            else:
                # Try to download as direct link
                downloaded_files += self._download_direct_link(post, download_path)
                
            return {
                'success': True,
                'files_downloaded': downloaded_files
            }
            
        except Exception as e:
            logging.warning(f"Error downloading media from post {post.get('id', 'unknown')}: {e}")
            return {'success': False, 'error': str(e)}
            
    def _is_supported_domain(self, domain: str) -> bool:
        """Check if domain is supported for downloading."""
        return any(supported in domain for supported in self.supported_domains)
        
    def _download_reddit_video(self, post: Dict[str, Any], download_path: str) -> int:
        """Download Reddit hosted video."""
        try:
            post_id = post['id']
            title = self.sanitize_filename(post['title'][:50])
            
            # Reddit videos have audio and video separate
            video_url = post.get('media', {}).get('reddit_video', {}).get('fallback_url', '')
            
            if not video_url:
                return 0
                
            # Download video
            filename = f"{title}_{post_id}.mp4"
            output_path = os.path.join(download_path, filename)
            
            if self.file_exists(output_path):
                return 1
                
            if self._download_file(video_url, output_path):
                return 1
                
        except Exception as e:
            logging.error(f"Error downloading Reddit video: {e}")
            
        return 0
        
    def _download_reddit_gallery(self, post: Dict[str, Any], download_path: str) -> int:
        """Download Reddit gallery images."""
        try:
            post_id = post['id']
            title = self.sanitize_filename(post['title'][:50])
            media_metadata = post.get('media_metadata', {})
            gallery_data = post.get('gallery_data', {})
            
            if not media_metadata:
                return 0
                
            downloaded_count = 0
            
            for i, (media_id, media_info) in enumerate(media_metadata.items()):
                try:
                    # Get the highest quality image
                    resolutions = media_info.get('s', {})
                    if not resolutions:
                        continue
                        
                    # Use the original image URL
                    image_url = resolutions.get('u', '').replace('&amp;', '&')
                    
                    if image_url:
                        extension = self._get_extension_from_url(image_url) or 'jpg'
                        filename = f"{title}_{post_id}_{i+1:03d}.{extension}"
                        output_path = os.path.join(download_path, filename)
                        
                        if not self.file_exists(output_path):
                            if self._download_file(image_url, output_path):
                                downloaded_count += 1
                        else:
                            downloaded_count += 1
                            
                except Exception as e:
                    logging.warning(f"Error downloading gallery image {i}: {e}")
                    continue
                    
            return downloaded_count
            
        except Exception as e:
            logging.error(f"Error downloading Reddit gallery: {e}")
            return 0
            
    def _download_direct_image(self, post: Dict[str, Any], download_path: str) -> int:
        """Download direct image link."""
        try:
            post_id = post['id']
            title = self.sanitize_filename(post['title'][:50])
            url = post['url']
            
            extension = self._get_extension_from_url(url) or 'jpg'
            filename = f"{title}_{post_id}.{extension}"
            output_path = os.path.join(download_path, filename)
            
            if self.file_exists(output_path):
                return 1
                
            if self._download_file(url, output_path):
                return 1
                
        except Exception as e:
            logging.error(f"Error downloading direct image: {e}")
            
        return 0
        
    def _download_imgur_content(self, post: Dict[str, Any], download_path: str) -> int:
        """Download Imgur content."""
        try:
            # Simplified Imgur handling
            # In reality, you'd parse Imgur pages for gallery content
            
            url = post['url']
            if url.endswith(('.jpg', '.jpeg', '.png', '.gif')):
                return self._download_direct_image(post, download_path)
            else:
                # Could be an album or gallery - would need Imgur API
                logging.info(f"Skipping Imgur album/gallery: {url}")
                return 0
                
        except Exception as e:
            logging.error(f"Error downloading Imgur content: {e}")
            return 0
            
    def _download_gif_content(self, post: Dict[str, Any], download_path: str) -> int:
        """Download GIF content from hosting sites."""
        try:
            # Simplified GIF handling
            # RedGifs and Gfycat would need API integration for proper support
            
            logging.info(f"Skipping GIF content (requires API): {post['url']}")
            return 0
            
        except Exception as e:
            logging.error(f"Error downloading GIF content: {e}")
            return 0
            
    def _download_direct_link(self, post: Dict[str, Any], download_path: str) -> int:
        """Try to download content as direct link."""
        try:
            url = post['url']
            
            # Check if it looks like a media file
            if url.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.mp4', '.webm', '.mov')):
                return self._download_direct_image(post, download_path)
            else:
                return 0
                
        except Exception as e:
            logging.error(f"Error downloading direct link: {e}")
            return 0
            
    def _download_file(self, url: str, output_path: str) -> bool:
        """Download a file from URL."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, stream=True, timeout=30)
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
            parsed = urlparse(url)
            path = parsed.path
            
            if '.' in path:
                return path.split('.')[-1].lower()
            else:
                return 'jpg'  # Default
                
        except:
            return 'jpg'
