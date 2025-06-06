"""
Base downloader class with common functionality.
"""

import os
import logging
import hashlib
from abc import ABC, abstractmethod
from typing import Dict, Any, Callable, Optional
from utils.file_manager import FileManager

class BaseDownloader(ABC):
    """Abstract base class for all downloaders."""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.config = config_manager.get_config()
        self.file_manager = FileManager(config_manager)
        
    @abstractmethod
    def download(self, url: str, options: Dict[str, Any], 
                progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        """
        Download content from the given URL with specified options.
        
        Args:
            url: URL or identifier to download from
            options: Download options specific to each platform
            progress_callback: Optional callback for progress updates (0-100)
            
        Returns:
            Dict with 'success' boolean and optional 'error' message
        """
        pass
        
    def get_download_path(self, platform: str, subfolder: str = "") -> str:
        """Get the download path for a platform."""
        base_path = self.config['download_directory']
        
        if self.config['organize_by_platform']:
            path = os.path.join(base_path, platform.lower())
            if subfolder:
                path = os.path.join(path, subfolder)
        else:
            path = base_path
            
        os.makedirs(path, exist_ok=True)
        return path
        
    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe filesystem storage."""
        if not self.config['sanitize_filenames']:
            return filename
            
        # Remove or replace unsafe characters
        unsafe_chars = '<>:"/\\|?*'
        for char in unsafe_chars:
            filename = filename.replace(char, '_')
            
        # Remove excessive whitespace and dots
        filename = ' '.join(filename.split())
        filename = filename.strip('. ')
        
        # Limit length
        if len(filename) > 200:
            name, ext = os.path.splitext(filename)
            filename = name[:200-len(ext)] + ext
            
        return filename
        
    def file_exists(self, filepath: str) -> bool:
        """Check if file exists and handle skip_existing_files setting."""
        if not os.path.exists(filepath):
            return False
            
        if self.config['skip_existing_files']:
            logging.info(f"Skipping existing file: {filepath}")
            return True
            
        return False
        
    def get_file_hash(self, filepath: str) -> str:
        """Get MD5 hash of a file for duplicate detection."""
        try:
            hash_md5 = hashlib.md5()
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logging.error(f"Error calculating file hash: {e}")
            return ""
            
    def log_download_start(self, platform: str, url: str):
        """Log the start of a download."""
        logging.info(f"Starting {platform} download: {url}")
        
    def log_download_complete(self, platform: str, url: str, files_downloaded: int):
        """Log the completion of a download."""
        logging.info(f"Completed {platform} download: {url} ({files_downloaded} files)")
        
    def log_download_error(self, platform: str, url: str, error: str):
        """Log a download error."""
        logging.error(f"{platform} download failed for {url}: {error}")
        
    def handle_retry(self, func, *args, **kwargs):
        """Handle retry logic for failed operations."""
        max_retries = self.config['retry_attempts']
        
        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries:
                    raise e
                logging.warning(f"Attempt {attempt + 1} failed, retrying: {str(e)}")
                
    def create_progress_callback(self, base_callback: Optional[Callable[[int], None]], 
                               total_items: int, current_item: int) -> Optional[Callable[[int], None]]:
        """Create a progress callback that accounts for multiple items."""
        if not base_callback:
            return None
            
        def progress_callback(item_progress: int):
            # Calculate overall progress
            overall_progress = ((current_item * 100) + item_progress) // total_items
            base_callback(min(overall_progress, 100))
            
        return progress_callback
