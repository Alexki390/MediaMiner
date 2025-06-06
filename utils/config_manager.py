"""
Configuration management for the application.
"""

import os
import json
import logging
from typing import Dict, Any

class ConfigManager:
    """Manages application configuration."""
    
    def __init__(self):
        self.config_dir = os.path.expanduser("~/.social_media_downloader")
        self.config_file = os.path.join(self.config_dir, "config.json")
        self.default_config_file = os.path.join(os.path.dirname(__file__), "..", "config", "default_config.json")
        
        # Ensure config directory exists
        os.makedirs(self.config_dir, exist_ok=True)
        
        # Load configuration
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default."""
        try:
            # Try to load existing config
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    
                # Merge with default config to ensure all keys exist
                default_config = self._get_default_config()
                merged_config = {**default_config, **config}
                
                # Save merged config to update any missing keys
                self._save_config_file(merged_config)
                
                return merged_config
            else:
                # Create default config
                default_config = self._get_default_config()
                self._save_config_file(default_config)
                return default_config
                
        except Exception as e:
            logging.error(f"Error loading configuration: {e}")
            # Return default configuration as fallback
            return self._get_default_config()
            
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        default_download_dir = os.path.join(os.path.expanduser("~"), "Downloads", "SocialMediaDownloader")
        
        return {
            # Download settings
            "download_directory": default_download_dir,
            "max_concurrent_downloads": 3,
            "organize_by_platform": True,
            "skip_existing_files": True,
            
            # File naming
            "add_date_to_filename": False,
            "sanitize_filenames": True,
            
            # Quality settings
            "default_video_quality": "best",
            "audio_format": "mp3",
            
            # Advanced settings
            "enable_detailed_logging": True,
            "retry_attempts": 3,
            "request_timeout": 30,
            
            # Platform-specific settings
            "youtube": {
                "extract_audio": False,
                "write_thumbnail": True,
                "write_info_json": True
            },
            "tiktok": {
                "process_slideshows": True,
                "slideshow_duration_per_image": 3
            },
            "instagram": {
                "include_stories": False,
                "download_comments": False
            },
            "reddit": {
                "min_score": 0,
                "skip_nsfw": False
            }
        }
        
    def _save_config_file(self, config: Dict[str, Any]):
        """Save configuration to file."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error saving configuration: {e}")
            
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration."""
        return self.config.copy()
        
    def save_config(self, config: Dict[str, Any]):
        """Save configuration."""
        try:
            self.config = config
            self._save_config_file(config)
            logging.info("Configuration saved successfully")
        except Exception as e:
            logging.error(f"Error saving configuration: {e}")
            raise
            
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a specific setting."""
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
            
    def set_setting(self, key: str, value: Any):
        """Set a specific setting."""
        keys = key.split('.')
        config = self.config
        
        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
            
        # Set the value
        config[keys[-1]] = value
        
        # Save configuration
        self._save_config_file(self.config)
        
    def reset_to_defaults(self):
        """Reset configuration to defaults."""
        self.config = self._get_default_config()
        self._save_config_file(self.config)
        logging.info("Configuration reset to defaults")
        
    def get_download_directory(self) -> str:
        """Get the configured download directory."""
        download_dir = self.config['download_directory']
        
        # Ensure directory exists
        os.makedirs(download_dir, exist_ok=True)
        
        return download_dir
        
    def validate_config(self) -> bool:
        """Validate current configuration."""
        try:
            # Check if download directory is writable
            download_dir = self.config['download_directory']
            if not os.path.exists(download_dir):
                os.makedirs(download_dir, exist_ok=True)
                
            # Test write permissions
            test_file = os.path.join(download_dir, '.test_write')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            
            # Validate other settings
            if self.config['max_concurrent_downloads'] < 1:
                self.config['max_concurrent_downloads'] = 1
                
            if self.config['retry_attempts'] < 0:
                self.config['retry_attempts'] = 0
                
            return True
            
        except Exception as e:
            logging.error(f"Configuration validation failed: {e}")
            return False
