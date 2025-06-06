"""
File management utilities.
"""

import os
import shutil
import hashlib
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

class FileManager:
    """Manages file operations and organization."""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.config = config_manager.get_config()
        
    def organize_files(self, download_path: str, platform: str) -> Dict[str, Any]:
        """Organize downloaded files according to configuration."""
        try:
            if not self.config.get('organize_by_platform', True):
                return {'success': True, 'message': 'Organization disabled'}
                
            organized_count = 0
            
            # Create platform-specific directory structure
            platform_dir = os.path.join(download_path, platform.lower())
            os.makedirs(platform_dir, exist_ok=True)
            
            # Get all files in download directory
            for filename in os.listdir(download_path):
                filepath = os.path.join(download_path, filename)
                
                if os.path.isfile(filepath) and filename != '.test_write':
                    # Move file to platform directory
                    new_filepath = os.path.join(platform_dir, filename)
                    
                    try:
                        shutil.move(filepath, new_filepath)
                        organized_count += 1
                    except Exception as e:
                        logging.warning(f"Could not move file {filename}: {e}")
                        
            return {
                'success': True,
                'organized_count': organized_count,
                'message': f'Organized {organized_count} files'
            }
            
        except Exception as e:
            logging.error(f"Error organizing files: {e}")
            return {'success': False, 'error': str(e)}
            
    def clean_filename(self, filename: str) -> str:
        """Clean and sanitize filename."""
        if not self.config.get('sanitize_filenames', True):
            return filename
            
        # Remove or replace unsafe characters
        unsafe_chars = '<>:"/\\|?*'
        for char in unsafe_chars:
            filename = filename.replace(char, '_')
            
        # Remove control characters
        filename = ''.join(char for char in filename if ord(char) >= 32)
        
        # Remove excessive whitespace and dots
        filename = ' '.join(filename.split())
        filename = filename.strip('. ')
        
        # Limit length
        if len(filename) > 200:
            name, ext = os.path.splitext(filename)
            filename = name[:200-len(ext)] + ext
            
        return filename
        
    def add_date_to_filename(self, filename: str) -> str:
        """Add current date to filename if configured."""
        if not self.config.get('add_date_to_filename', False):
            return filename
            
        name, ext = os.path.splitext(filename)
        date_str = datetime.now().strftime('%Y%m%d')
        
        return f"{name}_{date_str}{ext}"
        
    def get_unique_filename(self, filepath: str) -> str:
        """Get unique filename by adding number suffix if file exists."""
        if not os.path.exists(filepath):
            return filepath
            
        directory = os.path.dirname(filepath)
        name, ext = os.path.splitext(os.path.basename(filepath))
        
        counter = 1
        while True:
            new_filename = f"{name}_{counter}{ext}"
            new_filepath = os.path.join(directory, new_filename)
            
            if not os.path.exists(new_filepath):
                return new_filepath
                
            counter += 1
            
    def calculate_file_hash(self, filepath: str, algorithm: str = 'md5') -> str:
        """Calculate hash of a file."""
        try:
            if algorithm.lower() == 'md5':
                hash_obj = hashlib.md5()
            elif algorithm.lower() == 'sha1':
                hash_obj = hashlib.sha1()
            elif algorithm.lower() == 'sha256':
                hash_obj = hashlib.sha256()
            else:
                raise ValueError(f"Unsupported hash algorithm: {algorithm}")
                
            with open(filepath, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_obj.update(chunk)
                    
            return hash_obj.hexdigest()
            
        except Exception as e:
            logging.error(f"Error calculating file hash: {e}")
            return ""
            
    def find_duplicates(self, directory: str) -> Dict[str, List[str]]:
        """Find duplicate files in directory based on file hash."""
        try:
            file_hashes = {}
            duplicates = {}
            
            for root, dirs, files in os.walk(directory):
                for filename in files:
                    filepath = os.path.join(root, filename)
                    
                    if os.path.isfile(filepath):
                        file_hash = self.calculate_file_hash(filepath)
                        
                        if file_hash:
                            if file_hash in file_hashes:
                                # Duplicate found
                                if file_hash not in duplicates:
                                    duplicates[file_hash] = [file_hashes[file_hash]]
                                duplicates[file_hash].append(filepath)
                            else:
                                file_hashes[file_hash] = filepath
                                
            return duplicates
            
        except Exception as e:
            logging.error(f"Error finding duplicates: {e}")
            return {}
            
    def remove_duplicates(self, directory: str, keep_newest: bool = True) -> Dict[str, Any]:
        """Remove duplicate files from directory."""
        try:
            duplicates = self.find_duplicates(directory)
            removed_count = 0
            
            for file_hash, file_list in duplicates.items():
                if len(file_list) <= 1:
                    continue
                    
                # Sort by modification time
                file_list.sort(key=lambda x: os.path.getmtime(x), reverse=keep_newest)
                
                # Remove all but the first file (newest if keep_newest=True)
                for filepath in file_list[1:]:
                    try:
                        os.remove(filepath)
                        removed_count += 1
                        logging.info(f"Removed duplicate file: {filepath}")
                    except Exception as e:
                        logging.warning(f"Could not remove duplicate {filepath}: {e}")
                        
            return {
                'success': True,
                'removed_count': removed_count,
                'duplicates_found': len(duplicates)
            }
            
        except Exception as e:
            logging.error(f"Error removing duplicates: {e}")
            return {'success': False, 'error': str(e)}
            
    def get_directory_size(self, directory: str) -> int:
        """Get total size of directory in bytes."""
        try:
            total_size = 0
            
            for root, dirs, files in os.walk(directory):
                for filename in files:
                    filepath = os.path.join(root, filename)
                    if os.path.isfile(filepath):
                        total_size += os.path.getsize(filepath)
                        
            return total_size
            
        except Exception as e:
            logging.error(f"Error calculating directory size: {e}")
            return 0
            
    def get_file_info(self, filepath: str) -> Dict[str, Any]:
        """Get detailed information about a file."""
        try:
            if not os.path.exists(filepath):
                return {'error': 'File not found'}
                
            stat = os.stat(filepath)
            
            return {
                'path': filepath,
                'size': stat.st_size,
                'created': datetime.fromtimestamp(stat.st_ctime),
                'modified': datetime.fromtimestamp(stat.st_mtime),
                'hash_md5': self.calculate_file_hash(filepath, 'md5'),
                'extension': os.path.splitext(filepath)[1].lower()
            }
            
        except Exception as e:
            logging.error(f"Error getting file info: {e}")
            return {'error': str(e)}
            
    def cleanup_empty_directories(self, directory: str) -> int:
        """Remove empty directories recursively."""
        try:
            removed_count = 0
            
            for root, dirs, files in os.walk(directory, topdown=False):
                for dirname in dirs:
                    dirpath = os.path.join(root, dirname)
                    
                    try:
                        # Try to remove if empty
                        os.rmdir(dirpath)
                        removed_count += 1
                        logging.info(f"Removed empty directory: {dirpath}")
                    except OSError:
                        # Directory not empty, skip
                        pass
                        
            return removed_count
            
        except Exception as e:
            logging.error(f"Error cleaning up empty directories: {e}")
            return 0
            
    def create_backup(self, source_path: str, backup_dir: str) -> bool:
        """Create backup of a file or directory."""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            source_name = os.path.basename(source_path)
            backup_name = f"{source_name}_backup_{timestamp}"
            backup_path = os.path.join(backup_dir, backup_name)
            
            os.makedirs(backup_dir, exist_ok=True)
            
            if os.path.isfile(source_path):
                shutil.copy2(source_path, backup_path)
            elif os.path.isdir(source_path):
                shutil.copytree(source_path, backup_path)
            else:
                return False
                
            logging.info(f"Created backup: {backup_path}")
            return True
            
        except Exception as e:
            logging.error(f"Error creating backup: {e}")
            return False
