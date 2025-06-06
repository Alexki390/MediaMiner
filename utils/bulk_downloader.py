"""
Specialized bulk downloader for massive download operations.
"""

import logging
import time
import threading
from typing import Dict, Any, List, Callable, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue, Empty

class BulkDownloader:
    """Handles massive bulk download operations with optimization."""

    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.config = config_manager.get_config()
        self.download_queue = Queue()
        self.active_downloads = {}
        self.statistics = {
            'total_requested': 0,
            'total_completed': 0,
            'total_failed': 0,
            'bytes_downloaded': 0
        }

    def bulk_download_subreddit(self, subreddit: str, options: Dict[str, Any], 
                               progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        """Download entire subreddit with unlimited posts."""
        try:
            from downloaders.reddit_downloader import RedditDownloader

            # Override limit to 0 for unlimited
            bulk_options = options.copy()
            bulk_options['limit'] = 0  # Unlimited posts

            downloader = RedditDownloader(self.config_manager)
            result = downloader.download(subreddit, bulk_options, progress_callback)

            self.statistics['total_requested'] += 1
            if result.get('success', False):
                self.statistics['total_completed'] += 1
                self.statistics['bytes_downloaded'] += result.get('files_downloaded', 0) * 1024 * 1024  # Estimate
            else:
                self.statistics['total_failed'] += 1

            return result

        except Exception as e:
            logging.error(f"Bulk subreddit download failed: {e}")
            self.statistics['total_failed'] += 1
            return {'success': False, 'error': str(e)}

    def bulk_download_youtube_channel(self, channel_url: str, options: Dict[str, Any], 
                                     progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        """Download entire YouTube channel."""
        try:
            from downloaders.youtube_downloader import YouTubeDownloader

            # Set options for entire channel
            bulk_options = options.copy()
            bulk_options['entire_channel'] = True
            bulk_options['playlist_items'] = None  # Download all

            downloader = YouTubeDownloader(self.config_manager)
            result = downloader.download(channel_url, bulk_options, progress_callback)

            self.statistics['total_requested'] += 1
            if result.get('success', False):
                self.statistics['total_completed'] += 1
            else:
                self.statistics['total_failed'] += 1

            return result

        except Exception as e:
            logging.error(f"Bulk YouTube channel download failed: {e}")
            self.statistics['total_failed'] += 1
            return {'success': False, 'error': str(e)}

    def bulk_download_tiktok_user(self, username: str, options: Dict[str, Any], 
                                 progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        """Download all content from TikTok user."""
        try:
            from downloaders.tiktok_downloader import TikTokDownloader

            # Override limit for unlimited
            bulk_options = options.copy()
            bulk_options['limit'] = 0  # Unlimited videos

            downloader = TikTokDownloader(self.config_manager)
            result = downloader.download_user_content(username, bulk_options, progress_callback)

            self.statistics['total_requested'] += 1
            if result.get('success', False):
                self.statistics['total_completed'] += 1
            else:
                self.statistics['total_failed'] += 1

            return result

        except Exception as e:
            logging.error(f"Bulk TikTok user download failed: {e}")
            self.statistics['total_failed'] += 1
            return {'success': False, 'error': str(e)}

    def bulk_download_instagram_user(self, username: str, options: Dict[str, Any], 
                                    progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        """Download all content from Instagram user."""
        try:
            from downloaders.instagram_downloader import InstagramDownloader

            # Override limit for unlimited
            bulk_options = options.copy()
            bulk_options['limit'] = 0  # Unlimited posts
            bulk_options['include_stories'] = options.get('include_stories', False)

            downloader = InstagramDownloader(self.config_manager)
            result = downloader._download_user_content(username, bulk_options, progress_callback)

            self.statistics['total_requested'] += 1
            if result.get('success', False):
                self.statistics['total_completed'] += 1
            else:
                self.statistics['total_failed'] += 1

            return result

        except Exception as e:
            logging.error(f"Bulk Instagram user download failed: {e}")
            self.statistics['total_failed'] += 1
            return {'success': False, 'error': str(e)}

    def crawl_and_download_platform(self, platform: str, crawl_options: Dict[str, Any], 
                                   progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        """Advanced crawling and bulk download for a specific platform."""
        try:
            crawl_type = crawl_options.get('type', 'user')  # user, hashtag, search, trending
            query = crawl_options.get('query', '')
            max_items = crawl_options.get('limit', 0)  # 0 = unlimited

            if crawl_type == 'user':
                return self._crawl_user_content(platform, query, crawl_options, progress_callback)
            elif crawl_type == 'hashtag':
                return self._crawl_hashtag_content(platform, query, crawl_options, progress_callback)
            elif crawl_type == 'search':
                return self._crawl_search_results(platform, query, crawl_options, progress_callback)
            elif crawl_type == 'trending':

                return self._crawl_trending_content(platform, crawl_options, progress_callback)
            else:
                return {'success': False, 'error': f'Unsupported crawl type: {crawl_type}'}

        except Exception as e:
            logging.error(f"Platform crawling failed: {e}")
            return {'success': False, 'error': str(e)}

    def _crawl_user_content(self, platform: str, username: str, options: Dict[str, Any], 
                           progress_callback: Optional[Callable[[int], None]]) -> Dict[str, Any]:
        """Crawl all content from a user across the platform."""
        try:
            if platform == 'youtube':
                return self.bulk_download_youtube_channel(f"https://youtube.com/@{username}", options, progress_callback)
            elif platform == 'tiktok':
                return self.bulk_download_tiktok_user(username, options, progress_callback)
            elif platform == 'instagram':
                return self.bulk_download_instagram_user(username, options, progress_callback)
            elif platform == 'reddit':
                return self.bulk_download_subreddit(username, options, progress_callback)
            elif platform == 'pornhub':
                return self.bulk_download_pornhub_user(username, options, progress_callback)
            elif platform == 'coomer':
                return self.bulk_download_coomer_user(username, options, progress_callback)
            elif platform == 'kemono':
                return self.bulk_download_kemono_user(username, options, progress_callback)
            else:
                return {'success': False, 'error': f'User crawling not supported for {platform}'}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _crawl_hashtag_content(self, platform: str, hashtag: str, options: Dict[str, Any], 
                              progress_callback: Optional[Callable[[int], None]]) -> Dict[str, Any]:
        """Crawl content by hashtag."""
        try:
            # This would require hashtag-specific API implementations
            logging.warning(f"Hashtag crawling for {platform} requires specialized API integration")
            return {'success': False, 'error': 'Hashtag crawling not yet implemented'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _crawl_search_results(self, platform: str, query: str, options: Dict[str, Any], 
                             progress_callback: Optional[Callable[[int], None]]) -> Dict[str, Any]:
        """Crawl search results from platform."""
        try:
            # This would require search API implementations
            logging.warning(f"Search crawling for {platform} requires specialized API integration")
            return {'success': False, 'error': 'Search crawling not yet implemented'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _crawl_trending_content(self, platform: str, options: Dict[str, Any], 
                               progress_callback: Optional[Callable[[int], None]]) -> Dict[str, Any]:
        """Crawl trending content from platform."""
        try:
            # This would require trending/discover API implementations
            logging.warning(f"Trending crawling for {platform} requires specialized API integration")
            return {'success': False, 'error': 'Trending crawling not yet implemented'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def bulk_download_multiple_urls(self, urls: List[str], platform: str, options: Dict[str, Any], 
                                   progress_callback: Optional[Callable[[int], None]] = None,
                                   max_workers: int = 5) -> Dict[str, Any]:
        """Download multiple URLs concurrently."""
        try:
            total_urls = len(urls)
            completed = 0
            failed = 0
            results = []

            # Import appropriate downloader
            downloader_map = {
                'youtube': 'downloaders.youtube_downloader.YouTubeDownloader',
                'tiktok': 'downloaders.tiktok_downloader.TikTokDownloader',
                'instagram': 'downloaders.instagram_downloader.InstagramDownloader',
                'reddit': 'downloaders.reddit_downloader.RedditDownloader',
                'twitter': 'downloaders.twitter_downloader.TwitterDownloader',
                'redgifs': 'downloaders.redgifs_downloader.RedgifsDownloader',
                'xvideos': 'downloaders.xvideos_downloader.XVideosDownloader',
                'pornhub': 'downloaders.pornhub_downloader.PornhubDownloader',
                'coomer': 'downloaders.coomer_downloader.CoomerDownloader',
                'kemono': 'downloaders.kemono_downloader.KemonoDownloader'
            }

            if platform not in downloader_map:
                return {'success': False, 'error': f'Unsupported platform: {platform}'}

            # Dynamic import
            module_path, class_name = downloader_map[platform].rsplit('.', 1)
            module = __import__(module_path, fromlist=[class_name])
            downloader_class = getattr(module, class_name)

            def download_single_url(url):
                try:
                    downloader = downloader_class(self.config_manager)
                    return downloader.download(url, options)
                except Exception as e:
                    logging.error(f"Failed to download {url}: {e}")
                    return {'success': False, 'error': str(e)}

            # Use ThreadPoolExecutor for concurrent downloads
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_url = {executor.submit(download_single_url, url): url for url in urls}

                for future in as_completed(future_to_url):
                    url = future_to_url[future]
                    try:
                        result = future.result()
                        results.append({'url': url, 'result': result})

                        if result.get('success', False):
                            completed += 1
                        else:
                            failed += 1

                        if progress_callback:
                            progress = int(((completed + failed) / total_urls) * 100)
                            progress_callback(progress)

                    except Exception as e:
                        logging.error(f"Exception for {url}: {e}")
                        failed += 1
                        results.append({'url': url, 'result': {'success': False, 'error': str(e)}})

            self.statistics['total_requested'] += total_urls
            self.statistics['total_completed'] += completed
            self.statistics['total_failed'] += failed

            return {
                'success': True,
                'total_urls': total_urls,
                'completed': completed,
                'failed': failed,
                'results': results
            }

        except Exception as e:
            logging.error(f"Bulk multiple URLs download failed: {e}")
            return {'success': False, 'error': str(e)}

    def batch_process_mixed_urls(self, urls: List[str], options: Dict[str, Any] = None,
                                progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        """Process a batch of mixed platform URLs with automatic platform detection."""
        try:
            if not options:
                options = {}
            
            total_urls = len(urls)
            results = {
                'processed': 0,
                'successful': 0,
                'failed': 0,
                'platform_breakdown': {},
                'errors': []
            }
            
            for i, url in enumerate(urls):
                try:
                    # Detect platform
                    platform = self._detect_platform_from_url(url)
                    
                    if platform not in results['platform_breakdown']:
                        results['platform_breakdown'][platform] = {'processed': 0, 'successful': 0, 'failed': 0}
                    
                    results['platform_breakdown'][platform]['processed'] += 1
                    
                    # Get appropriate downloader
                    if platform == 'erome':
                        result = self.bulk_download_erome_profile(url, options, None)
                    elif platform == 'kwai':
                        result = self.bulk_download_kwai_profile(url, options, None)
                    elif platform == 'pornhub':
                        result = self.bulk_download_pornhub_user(url, options, None)
                    else:
                        # Use multiple URLs method for other platforms
                        result = self.bulk_download_multiple_urls([url], platform, options, None, 1)
                    
                    if result.get('success', False):
                        results['successful'] += 1
                        results['platform_breakdown'][platform]['successful'] += 1
                    else:
                        results['failed'] += 1
                        results['platform_breakdown'][platform]['failed'] += 1
                        results['errors'].append({
                            'url': url,
                            'platform': platform,
                            'error': result.get('error', 'Unknown error')
                        })
                    
                    results['processed'] += 1
                    
                    # Progress callback
                    if progress_callback:
                        progress = int(((i + 1) / total_urls) * 100)
                        progress_callback(progress)
                    
                    # Rate limiting
                    time.sleep(options.get('delay', 5))
                    
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append({
                        'url': url,
                        'platform': 'unknown',
                        'error': str(e)
                    })
                    logging.error(f"Error processing URL {url}: {e}")
            
            return {
                'success': True,
                'total_urls': total_urls,
                **results
            }
            
        except Exception as e:
            logging.error(f"Batch processing failed: {e}")
            return {'success': False, 'error': str(e)}

    def _detect_platform_from_url(self, url: str) -> str:
        """Detect platform from URL for batch processing."""
        url_lower = url.lower()
        
        if 'erome.com' in url_lower:
            return 'erome'
        elif 'kwai.com' in url_lower:
            return 'kwai'
        elif 'pornhub.com' in url_lower:
            return 'pornhub'
        elif 'coomer.su' in url_lower:
            return 'coomer'
        elif 'kemono.su' in url_lower:
            return 'kemono'
        elif 'youtube.com' in url_lower or 'youtu.be' in url_lower:
            return 'youtube'
        elif 'tiktok.com' in url_lower:
            return 'tiktok'
        elif 'instagram.com' in url_lower:
            return 'instagram'
        elif 'reddit.com' in url_lower:
            return 'reddit'
        elif 'redgifs.com' in url_lower:
            return 'redgifs'
        elif 'twitter.com' in url_lower or 'x.com' in url_lower:
            return 'twitter'
        else:
            return 'generic'

    def bulk_download_pornhub_user(self, username: str, options: Dict[str, Any], 
                                  progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        """Download all content from Pornhub user including videos and GIFs."""
        try:
            from downloaders.pornhub_downloader import PornhubDownloader

            # Override limit for unlimited
            bulk_options = options.copy()
            bulk_options['limit'] = 0  # Unlimited content
            bulk_options['include_gifs'] = True

            downloader = PornhubDownloader(self.config_manager)
            result = downloader._download_user_content(username, bulk_options, progress_callback)

            self.statistics['total_requested'] += 1
            if result.get('success', False):
                self.statistics['total_completed'] += 1
            else:
                self.statistics['total_failed'] += 1

            return result

        except Exception as e:
            logging.error(f"Bulk Pornhub user download failed: {e}")
            self.statistics['total_failed'] += 1
            return {'success': False, 'error': str(e)}

    def bulk_download_coomer_user(self, username: str, options: Dict[str, Any], 
                                 progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        """Download all content from Coomer.su user."""
        try:
            from downloaders.coomer_downloader import CoomerDownloader

            # Override limit for unlimited
            bulk_options = options.copy()
            bulk_options['limit'] = 0  # Unlimited posts

            # Construct proper URL if just username provided
            if not username.startswith('http'):
                service = options.get('service', 'onlyfans')  # Default to OnlyFans
                username = f"https://coomer.su/{service}/user/{username}"

            downloader = CoomerDownloader(self.config_manager)
            result = downloader._download_user_content(username, bulk_options, progress_callback)

            self.statistics['total_requested'] += 1
            if result.get('success', False):
                self.statistics['total_completed'] += 1
            else:
                self.statistics['total_failed'] += 1

            return result

        except Exception as e:
            logging.error(f"Bulk Coomer user download failed: {e}")
            self.statistics['total_failed'] += 1
            return {'success': False, 'error': str(e)}

    def bulk_download_kemono_user(self, username: str, options: Dict[str, Any], 
                                 progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        """Download all content from Kemono.su user."""
        try:
            from downloaders.kemono_downloader import KemonoDownloader

            # Override limit for unlimited
            bulk_options = options.copy()
            bulk_options['limit'] = 0  # Unlimited posts

            # Construct proper URL if just username provided
            if not username.startswith('http'):
                service = options.get('service', 'patreon')  # Default to Patreon
                username = f"https://kemono.su/{service}/user/{username}"

            downloader = KemonoDownloader(self.config_manager)
            result = downloader._download_user_content(username, bulk_options, progress_callback)

            self.statistics['total_requested'] += 1
            if result.get('success', False):
                self.statistics['total_completed'] += 1
            else:
                self.statistics['total_failed'] += 1

            return result

        except Exception as e:
            logging.error(f"Bulk Kemono user download failed: {e}")
            self.statistics['total_failed'] += 1
            return {'success': False, 'error': str(e)}

    def bulk_download_adult_site_profile(self, profile_url: str, options: Dict[str, Any], 
                                        progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        """Download all content from adult site profile (urlebird, ttthots, sotwe, fapsly, etc.)."""
        try:
            from downloaders.adult_sites_downloader import AdultSitesDownloader

            # Override limit for unlimited posts
            bulk_options = options.copy()
            bulk_options['max_pages'] = 0  # Unlimited pages

            downloader = AdultSitesDownloader(self.config_manager)
            result = downloader.download(profile_url, bulk_options, progress_callback)

            self.statistics['total_requested'] += 1
            if result.get('success', False):
                self.statistics['total_completed'] += 1
            else:
                self.statistics['total_failed'] += 1

            return result

        except Exception as e:
            logging.error(f"Bulk adult site profile download failed: {e}")
            self.statistics['total_failed'] += 1
            return {'success': False, 'error': str(e)}

    def bulk_download_erome_profile(self, profile_url: str, options: Dict[str, Any], 
                                   progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        """Download all albums from Erome profile."""
        try:
            from downloaders.erome_downloader import EromeDownloader

            # Override for unlimited pages
            bulk_options = options.copy()
            bulk_options['max_pages'] = 0  # Unlimited pages

            downloader = EromeDownloader(self.config_manager)
            result = downloader.download(profile_url, bulk_options, progress_callback)

            self.statistics['total_requested'] += 1
            if result.get('success', False):
                self.statistics['total_completed'] += 1
            else:
                self.statistics['total_failed'] += 1

            return result

        except Exception as e:
            logging.error(f"Bulk Erome profile download failed: {e}")
            self.statistics['total_failed'] += 1
            return {'success': False, 'error': str(e)}

    def bulk_download_kwai_profile(self, profile_url: str, options: Dict[str, Any], 
                                  progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        """Download all videos from Kwai profile."""
        try:
            from downloaders.kwai_downloader import KwaiDownloader

            # Override for unlimited videos
            bulk_options = options.copy()
            bulk_options['limit'] = 0  # Unlimited videos

            downloader = KwaiDownloader(self.config_manager)
            result = downloader.download(profile_url, bulk_options, progress_callback)

            self.statistics['total_requested'] += 1
            if result.get('success', False):
                self.statistics['total_completed'] += 1
            else:
                self.statistics['total_failed'] += 1

            return result

        except Exception as e:
            logging.error(f"Bulk Kwai profile download failed: {e}")
            self.statistics['total_failed'] += 1
            return {'success': False, 'error': str(e)}

    def bulk_download_hentai_gallery(self, gallery_url: str, options: Dict[str, Any], 
                                    progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        """Download complete hentai galleries from nhentai, imhentai, hentaiera."""
        try:
            from downloaders.adult_sites_downloader import AdultSitesDownloader

            # Set options for complete gallery download
            bulk_options = options.copy()
            bulk_options['download_all_pages'] = True

            downloader = AdultSitesDownloader(self.config_manager)
            result = downloader.download(gallery_url, bulk_options, progress_callback)

            self.statistics['total_requested'] += 1
            if result.get('success', False):
                self.statistics['total_completed'] += 1
            else:
                self.statistics['total_failed'] += 1

            return result

        except Exception as e:
            logging.error(f"Bulk hentai gallery download failed: {e}")
            self.statistics['total_failed'] += 1
            return {'success': False, 'error': str(e)}

    def get_statistics(self) -> Dict[str, Any]:
        """Get bulk download statistics."""
        return self.statistics.copy()

    def reset_statistics(self):
        """Reset download statistics."""
        self.statistics = {
            'total_requested': 0,
            'total_completed': 0,
            'total_failed': 0,
            'bytes_downloaded': 0
        }