
"""
Advanced content analysis for better download decisions.
"""

import requests
import logging
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
import json
import re

class ContentAnalyzer:
    """Analyzes content before downloading for optimal quality and format selection."""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.config = config_manager.get_config()
        
    def analyze_content_quality(self, url: str) -> Dict[str, Any]:
        """Analyze available quality options for content."""
        try:
            analysis = {
                'url': url,
                'available_qualities': [],
                'recommended_quality': None,
                'file_size_estimates': {},
                'duration': None,
                'has_audio': False,
                'subtitle_languages': [],
                'content_type': 'unknown'
            }
            
            platform = self._detect_platform(url)
            
            if platform == 'youtube':
                analysis.update(self._analyze_youtube_content(url))
            elif platform == 'tiktok':
                analysis.update(self._analyze_tiktok_content(url))
            elif platform == 'instagram':
                analysis.update(self._analyze_instagram_content(url))
            elif platform == 'reddit':
                analysis.update(self._analyze_reddit_content(url))
                
            return analysis
            
        except Exception as e:
            logging.error(f"Content analysis failed: {e}")
            return {'error': str(e)}
            
    def _detect_platform(self, url: str) -> str:
        """Detect platform from URL."""
        url_lower = url.lower()
        
        if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
            return 'youtube'
        elif 'tiktok.com' in url_lower:
            return 'tiktok'
        elif 'instagram.com' in url_lower:
            return 'instagram'
        elif 'reddit.com' in url_lower:
            return 'reddit'
        elif 'twitter.com' in url_lower or 'x.com' in url_lower:
            return 'twitter'
        else:
            return 'unknown'
            
    def _analyze_youtube_content(self, url: str) -> Dict[str, Any]:
        """Analyze YouTube content for quality options."""
        try:
            # This would integrate with yt-dlp to get format info
            return {
                'available_qualities': ['144p', '240p', '360p', '480p', '720p', '1080p', '1440p', '2160p'],
                'recommended_quality': '1080p',
                'has_audio': True,
                'subtitle_languages': ['en', 'es', 'fr', 'de'],
                'content_type': 'video'
            }
        except Exception as e:
            logging.error(f"YouTube analysis failed: {e}")
            return {}
            
    def _analyze_tiktok_content(self, url: str) -> Dict[str, Any]:
        """Analyze TikTok content."""
        try:
            return {
                'available_qualities': ['720p', '1080p'],
                'recommended_quality': '1080p',
                'has_audio': True,
                'is_slideshow': self._check_tiktok_slideshow(url),
                'content_type': 'video'
            }
        except Exception as e:
            logging.error(f"TikTok analysis failed: {e}")
            return {}
            
    def _analyze_instagram_content(self, url: str) -> Dict[str, Any]:
        """Analyze Instagram content."""
        try:
            return {
                'available_qualities': ['480p', '720p', '1080p'],
                'recommended_quality': '1080p',
                'has_audio': True,
                'is_carousel': self._check_instagram_carousel(url),
                'content_type': 'image' if '/p/' in url else 'video'
            }
        except Exception as e:
            logging.error(f"Instagram analysis failed: {e}")
            return {}
            
    def _analyze_reddit_content(self, url: str) -> Dict[str, Any]:
        """Analyze Reddit content."""
        try:
            return {
                'subreddit': self._extract_subreddit(url),
                'post_type': self._detect_reddit_post_type(url),
                'content_type': 'mixed'
            }
        except Exception as e:
            logging.error(f"Reddit analysis failed: {e}")
            return {}
            
    def _check_tiktok_slideshow(self, url: str) -> bool:
        """Check if TikTok URL is a slideshow."""
        # Implementation would check for slideshow indicators
        return False
        
    def _check_instagram_carousel(self, url: str) -> bool:
        """Check if Instagram post is a carousel."""
        # Implementation would check for carousel indicators
        return False
        
    def _extract_subreddit(self, url: str) -> str:
        """Extract subreddit name from Reddit URL."""
        try:
            match = re.search(r'reddit\.com/r/([^/]+)', url)
            return match.group(1) if match else 'unknown'
        except:
            return 'unknown'
            
    def _detect_reddit_post_type(self, url: str) -> str:
        """Detect Reddit post type."""
        if '/comments/' in url:
            return 'post'
        elif '/r/' in url:
            return 'subreddit'
        else:
            return 'unknown'
            
    def get_optimal_download_strategy(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Get optimal download strategy based on content analysis."""
        try:
            strategy = {
                'quality': analysis.get('recommended_quality', 'best'),
                'format': 'mp4',
                'extract_audio': False,
                'download_thumbnails': True,
                'save_metadata': True,
                'concurrent_downloads': 1
            }
            
            content_type = analysis.get('content_type', 'unknown')
            
            if content_type == 'video':
                if analysis.get('has_audio', False):
                    strategy['format'] = 'mp4'
                else:
                    strategy['extract_audio'] = False
                    
            elif content_type == 'image':
                strategy['format'] = 'jpg'
                strategy['extract_audio'] = False
                
            elif content_type == 'mixed':
                strategy['concurrent_downloads'] = 3
                strategy['organize_by_type'] = True
                
            # Adjust for file size
            file_sizes = analysis.get('file_size_estimates', {})
            if file_sizes:
                total_size = sum(file_sizes.values())
                if total_size > 1024 * 1024 * 1024:  # > 1GB
                    strategy['quality'] = '720p'  # Reduce quality for large files
                    
            return strategy
            
        except Exception as e:
            logging.error(f"Strategy optimization failed: {e}")
            return {'quality': 'best', 'format': 'mp4'}
