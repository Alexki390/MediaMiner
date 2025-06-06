
"""
Auto-update manager for keeping the application current.
"""

import os
import logging
import requests
import json
from typing import Dict, Any, Optional
from packaging import version
import subprocess
import tempfile
import shutil

class UpdateManager:
    """Manages application updates and version checking."""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.config = config_manager.get_config()
        self.current_version = "1.0.0"
        self.update_url = "https://api.github.com/repos/yourusername/social-media-downloader/releases/latest"
        
    def check_for_updates(self) -> Dict[str, Any]:
        """Check for available updates."""
        try:
            response = requests.get(self.update_url, timeout=10)
            if response.status_code == 200:
                release_info = response.json()
                latest_version = release_info['tag_name'].lstrip('v')
                
                if version.parse(latest_version) > version.parse(self.current_version):
                    return {
                        'update_available': True,
                        'latest_version': latest_version,
                        'current_version': self.current_version,
                        'download_url': release_info['assets'][0]['browser_download_url'] if release_info['assets'] else None,
                        'changelog': release_info['body']
                    }
                else:
                    return {
                        'update_available': False,
                        'latest_version': latest_version,
                        'current_version': self.current_version
                    }
            else:
                return {'error': 'Failed to check for updates'}
                
        except Exception as e:
            logging.error(f"Update check failed: {e}")
            return {'error': str(e)}
            
    def download_and_install_update(self, download_url: str) -> bool:
        """Download and install update."""
        try:
            # Download update
            response = requests.get(download_url, stream=True)
            if response.status_code == 200:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.exe') as temp_file:
                    for chunk in response.iter_content(chunk_size=8192):
                        temp_file.write(chunk)
                    temp_file_path = temp_file.name
                
                # Launch installer and exit current app
                subprocess.Popen([temp_file_path])
                return True
            return False
            
        except Exception as e:
            logging.error(f"Update installation failed: {e}")
            return False
            
    def get_version_info(self) -> Dict[str, str]:
        """Get current version information."""
        return {
            'version': self.current_version,
            'build_date': '2024-01-01',
            'python_version': f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}"
        }
