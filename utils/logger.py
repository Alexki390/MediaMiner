"""
Logging configuration and utilities.
"""

import os
import logging
import logging.handlers
from datetime import datetime
from typing import Optional

def setup_logging(log_level: str = "INFO", log_to_file: bool = True, 
                 max_file_size: int = 10 * 1024 * 1024, backup_count: int = 5) -> None:
    """
    Setup application logging with both console and file handlers.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to file
        max_file_size: Maximum log file size in bytes before rotation
        backup_count: Number of backup log files to keep
    """
    try:
        # Create logs directory
        log_dir = os.path.expanduser("~/.social_media_downloader/logs")
        os.makedirs(log_dir, exist_ok=True)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        if log_to_file:
            # File handler with rotation
            log_file = os.path.join(log_dir, 'social_media_downloader.log')
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
            
            # Error log file handler
            error_log_file = os.path.join(log_dir, 'errors.log')
            error_handler = logging.handlers.RotatingFileHandler(
                error_log_file,
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(formatter)
            root_logger.addHandler(error_handler)
            
        # Log startup message
        logging.info("=" * 60)
        logging.info("Social Media Downloader - Logging initialized")
        logging.info(f"Log level: {log_level}")
        logging.info(f"Log directory: {log_dir}")
        logging.info("=" * 60)
        
    except Exception as e:
        print(f"Failed to setup logging: {e}")
        # Fallback to basic logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)

def log_download_start(platform: str, url: str, logger: Optional[logging.Logger] = None):
    """
    Log the start of a download operation.
    
    Args:
        platform: Platform name (youtube, tiktok, etc.)
        url: URL or identifier being downloaded
        logger: Optional logger instance
    """
    if logger is None:
        logger = logging.getLogger(__name__)
        
    logger.info(f"[{platform.upper()}] Starting download: {url}")

def log_download_complete(platform: str, url: str, files_count: int, 
                         logger: Optional[logging.Logger] = None):
    """
    Log the completion of a download operation.
    
    Args:
        platform: Platform name
        url: URL or identifier that was downloaded
        files_count: Number of files downloaded
        logger: Optional logger instance
    """
    if logger is None:
        logger = logging.getLogger(__name__)
        
    logger.info(f"[{platform.upper()}] Download completed: {url} ({files_count} files)")

def log_download_error(platform: str, url: str, error: str, 
                      logger: Optional[logging.Logger] = None):
    """
    Log a download error.
    
    Args:
        platform: Platform name
        url: URL or identifier that failed
        error: Error message
        logger: Optional logger instance
    """
    if logger is None:
        logger = logging.getLogger(__name__)
        
    logger.error(f"[{platform.upper()}] Download failed: {url} - {error}")

def log_progress(platform: str, url: str, progress: int, 
                logger: Optional[logging.Logger] = None):
    """
    Log download progress.
    
    Args:
        platform: Platform name
        url: URL being downloaded
        progress: Progress percentage (0-100)
        logger: Optional logger instance
    """
    if logger is None:
        logger = logging.getLogger(__name__)
        
    if progress % 25 == 0:  # Log every 25% to avoid spam
        logger.info(f"[{platform.upper()}] Progress: {url} - {progress}%")

def log_system_info(logger: Optional[logging.Logger] = None):
    """
    Log system information for debugging.
    
    Args:
        logger: Optional logger instance
    """
    if logger is None:
        logger = logging.getLogger(__name__)
        
    try:
        import platform
        import sys
        
        logger.info("System Information:")
        logger.info(f"  OS: {platform.system()} {platform.release()}")
        logger.info(f"  Python: {sys.version}")
        logger.info(f"  Platform: {platform.platform()}")
        logger.info(f"  Architecture: {platform.architecture()}")
        
    except Exception as e:
        logger.warning(f"Could not log system info: {e}")

def log_configuration(config: dict, logger: Optional[logging.Logger] = None):
    """
    Log current configuration (sensitive data excluded).
    
    Args:
        config: Configuration dictionary
        logger: Optional logger instance
    """
    if logger is None:
        logger = logging.getLogger(__name__)
        
    try:
        logger.info("Current Configuration:")
        
        # Safe keys to log (exclude sensitive information)
        safe_keys = [
            'download_directory', 'max_concurrent_downloads', 'organize_by_platform',
            'skip_existing_files', 'add_date_to_filename', 'sanitize_filenames',
            'default_video_quality', 'audio_format', 'enable_detailed_logging',
            'retry_attempts', 'request_timeout'
        ]
        
        for key in safe_keys:
            if key in config:
                logger.info(f"  {key}: {config[key]}")
                
    except Exception as e:
        logger.warning(f"Could not log configuration: {e}")

def setup_download_logger(download_id: str, platform: str) -> logging.Logger:
    """
    Setup a dedicated logger for a specific download.
    
    Args:
        download_id: Unique download identifier
        platform: Platform name
        
    Returns:
        Logger instance for the download
    """
    try:
        logger_name = f"download.{platform}.{download_id}"
        logger = logging.getLogger(logger_name)
        
        # Don't add handlers if already configured
        if logger.handlers:
            return logger
            
        # Create download-specific log file
        log_dir = os.path.expanduser("~/.social_media_downloader/logs/downloads")
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f"{platform}_{download_id}.log")
        
        # File handler for this download
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.setLevel(logging.DEBUG)
        
        # Prevent propagation to avoid duplicate logs
        logger.propagate = False
        
        return logger
        
    except Exception as e:
        logging.error(f"Failed to setup download logger: {e}")
        return logging.getLogger(__name__)

def cleanup_old_logs(days_to_keep: int = 30):
    """
    Clean up old log files.
    
    Args:
        days_to_keep: Number of days of logs to keep
    """
    try:
        import time
        
        log_dir = os.path.expanduser("~/.social_media_downloader/logs")
        if not os.path.exists(log_dir):
            return
            
        current_time = time.time()
        cutoff_time = current_time - (days_to_keep * 24 * 60 * 60)
        
        removed_count = 0
        
        for root, dirs, files in os.walk(log_dir):
            for filename in files:
                if filename.endswith('.log'):
                    filepath = os.path.join(root, filename)
                    
                    try:
                        file_time = os.path.getmtime(filepath)
                        if file_time < cutoff_time:
                            os.remove(filepath)
                            removed_count += 1
                    except OSError:
                        pass  # Skip files that can't be accessed
                        
        if removed_count > 0:
            logging.info(f"Cleaned up {removed_count} old log files")
            
    except Exception as e:
        logging.warning(f"Error cleaning up old logs: {e}")

def get_log_stats() -> dict:
    """
    Get statistics about log files.
    
    Returns:
        Dictionary with log statistics
    """
    try:
        log_dir = os.path.expanduser("~/.social_media_downloader/logs")
        if not os.path.exists(log_dir):
            return {'error': 'Log directory not found'}
            
        stats = {
            'total_files': 0,
            'total_size': 0,
            'oldest_log': None,
            'newest_log': None
        }
        
        oldest_time = None
        newest_time = None
        
        for root, dirs, files in os.walk(log_dir):
            for filename in files:
                if filename.endswith('.log'):
                    filepath = os.path.join(root, filename)
                    
                    try:
                        file_stat = os.stat(filepath)
                        stats['total_files'] += 1
                        stats['total_size'] += file_stat.st_size
                        
                        file_time = file_stat.st_mtime
                        
                        if oldest_time is None or file_time < oldest_time:
                            oldest_time = file_time
                            stats['oldest_log'] = datetime.fromtimestamp(file_time)
                            
                        if newest_time is None or file_time > newest_time:
                            newest_time = file_time
                            stats['newest_log'] = datetime.fromtimestamp(file_time)
                            
                    except OSError:
                        pass
                        
        return stats
        
    except Exception as e:
        return {'error': str(e)}

# Configure module logger
_module_logger = logging.getLogger(__name__)
