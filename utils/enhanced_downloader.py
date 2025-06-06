
"""
Enhanced downloader utility for handling complex cases like private accounts and age-restricted content.
"""

import os
import logging
import asyncio
import time
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path

class EnhancedDownloader:
    """Enhanced downloader with advanced features for private accounts and restricted content."""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.config = config_manager.get_config()
        
    def detect_content_type(self, url: str) -> Dict[str, Any]:
        """Detect content type and restrictions."""
        try:
            detection_result = {
                'platform': None,
                'content_type': None,
                'is_private': False,
                'is_age_restricted': False,
                'requires_auth': False,
                'supported': True
            }
            
            url_lower = url.lower()
            
            # Platform detection
            if 'tiktok.com' in url_lower:
                detection_result['platform'] = 'tiktok'
                detection_result['content_type'] = 'video' if '/video/' in url_lower else 'user'
            elif 'youtube.com' in url_lower or 'youtu.be' in url_lower:
                detection_result['platform'] = 'youtube'
                detection_result['content_type'] = 'video' if 'watch?v=' in url_lower or 'youtu.be/' in url_lower else 'channel'
            elif 'instagram.com' in url_lower:
                detection_result['platform'] = 'instagram'
                detection_result['content_type'] = 'post' if '/p/' in url_lower else 'user'
            elif 'twitter.com' in url_lower or 'x.com' in url_lower:
                detection_result['platform'] = 'twitter'
                detection_result['content_type'] = 'tweet' if '/status/' in url_lower else 'user'
                
            # Advanced detection (would require actual requests in real implementation)
            if detection_result['platform']:
                detection_result.update(self._check_content_restrictions(url, detection_result))
                
            return detection_result
            
        except Exception as e:
            logging.error(f"Content detection failed: {e}")
            return {'platform': None, 'supported': False, 'error': str(e)}
            
    def _check_content_restrictions(self, url: str, base_info: Dict[str, Any]) -> Dict[str, Any]:
        """Check for content restrictions."""
        restrictions = {
            'is_private': False,
            'is_age_restricted': False,
            'requires_auth': False
        }
        
        platform = base_info['platform']
        
        # Platform-specific restriction checking
        if platform == 'youtube':
            # YouTube age restriction detection would be implemented here
            restrictions['requires_auth'] = True  # Most restricted content needs auth
        elif platform == 'tiktok':
            # TikTok private account detection
            restrictions['requires_auth'] = True  # Private accounts need auth
        elif platform == 'instagram':
            # Instagram private account detection
            restrictions['requires_auth'] = True
            
        return restrictions
        
    def get_recommended_auth_method(self, platform: str, content_type: str) -> Dict[str, Any]:
        """Get recommended authentication method for platform and content type."""
        recommendations = {
            'youtube': {
                'primary': 'browser_cookies',
                'alternative': 'google_oauth',
                'description': 'Use browser cookies for age-restricted content'
            },
            'tiktok': {
                'primary': 'credentials',
                'alternative': 'browser_session',
                'description': 'Login with username/password for private accounts'
            },
            'instagram': {
                'primary': 'credentials',
                'alternative': 'session_cookies',
                'description': 'Login with username/password for private accounts'
            },
            'twitter': {
                'primary': 'bearer_token',
                'alternative': 'credentials',
                'description': 'Use API token or login credentials'
            }
        }
        
        return recommendations.get(platform, {
            'primary': 'credentials',
            'alternative': 'manual',
            'description': 'Manual authentication required'
        })
        
    def prepare_download_environment(self, platform: str, auth_method: str = None) -> bool:
        """Prepare download environment with necessary authentication."""
        try:
            if platform == 'youtube' and auth_method == 'browser_cookies':
                # Setup browser cookie extraction
                return self._setup_youtube_cookies()
            elif platform == 'tiktok' and auth_method == 'browser_session':
                # Setup TikTok browser session
                return self._setup_tiktok_browser()
            elif platform in ['instagram', 'tiktok'] and auth_method == 'credentials':
                # Verify credentials are stored
                return self._verify_stored_credentials(platform)
                
            return True
            
        except Exception as e:
            logging.error(f"Failed to prepare download environment: {e}")
            return False
            
    def _setup_youtube_cookies(self) -> bool:
        """Setup YouTube cookies for age-restricted content."""
        try:
            # This would implement cookie extraction
            logging.info("YouTube cookie setup initialized")
            return True
        except Exception as e:
            logging.error(f"YouTube cookie setup failed: {e}")
            return False
            
    def _setup_tiktok_browser(self) -> bool:
        """Setup TikTok browser session."""
        try:
            # This would implement browser session setup
            logging.info("TikTok browser session setup initialized")
            return True
        except Exception as e:
            logging.error(f"TikTok browser setup failed: {e}")
            return False
            
    def _verify_stored_credentials(self, platform: str) -> bool:
        """Verify that credentials are stored for the platform."""
        try:
            from utils.auth_manager import AuthManager
            auth_manager = AuthManager(self.config_manager)
            
            credentials = auth_manager.get_credentials(platform)
            return credentials is not None and 'username' in credentials and 'password' in credentials
            
        except Exception as e:
            logging.error(f"Credential verification failed: {e}")
            return False
            
    def validate_download_capability(self, url: str) -> Dict[str, Any]:
        """Validate if the URL can be downloaded with current setup."""
        try:
            # Detect content
            content_info = self.detect_content_type(url)
            
            if not content_info.get('supported', False):
                return {
                    'can_download': False,
                    'reason': 'Unsupported platform or content type',
                    'recommendations': []
                }
                
            platform = content_info['platform']
            requires_auth = content_info.get('requires_auth', False)
            
            # Check authentication status
            if requires_auth:
                auth_ready = self.prepare_download_environment(platform)
                if not auth_ready:
                    auth_method = self.get_recommended_auth_method(platform, content_info.get('content_type', ''))
                    return {
                        'can_download': False,
                        'reason': 'Authentication required',
                        'recommendations': [
                            f"Setup {auth_method['primary']} authentication",
                            auth_method['description']
                        ],
                        'content_info': content_info
                    }
                    
            return {
                'can_download': True,
                'content_info': content_info,
                'auth_status': 'ready' if requires_auth else 'not_required'
            }
            
        except Exception as e:
            return {
                'can_download': False,
                'reason': f'Validation failed: {str(e)}',
                'recommendations': ['Check URL format and try again']
            }

    def batch_process_urls(self, urls: List[str], options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process multiple URLs in batch with optimized performance."""
        try:
            results = {
                'successful': [],
                'failed': [],
                'total_files': 0,
                'processing_time': 0
            }
            
            start_time = time.time()
            
            for url in urls:
                try:
                    # Validate each URL
                    validation = self.validate_download_capability(url)
                    
                    if validation['can_download']:
                        results['successful'].append({
                            'url': url,
                            'platform': validation['content_info']['platform'],
                            'status': 'ready'
                        })
                    else:
                        results['failed'].append({
                            'url': url,
                            'reason': validation['reason'],
                            'recommendations': validation.get('recommendations', [])
                        })
                        
                except Exception as e:
                    results['failed'].append({
                        'url': url,
                        'reason': f'Validation error: {str(e)}',
                        'recommendations': ['Check URL format']
                    })
                    
            results['processing_time'] = time.time() - start_time
            
            return results
            
        except Exception as e:
            logging.error(f"Batch processing failed: {e}")
            return {'error': str(e)}
            
    def smart_retry_mechanism(self, download_func, max_retries: int = 5) -> Dict[str, Any]:
        """Intelligent retry mechanism with exponential backoff."""
        for attempt in range(max_retries):
            try:
                result = download_func()
                if result.get('success', False):
                    return result
                    
                # Exponential backoff
                wait_time = 2 ** attempt
                logging.warning(f"Retry attempt {attempt + 1}/{max_retries} in {wait_time}s")
                time.sleep(wait_time)
                
            except Exception as e:
                if attempt == max_retries - 1:
                    return {'success': False, 'error': f'Max retries reached: {str(e)}'}
                    
                wait_time = 2 ** attempt
                logging.warning(f"Error on attempt {attempt + 1}: {e}. Retrying in {wait_time}s")
                time.sleep(wait_time)
                
        return {'success': False, 'error': 'Max retries exceeded'}
