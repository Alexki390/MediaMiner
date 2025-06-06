
"""
Cookie management system for manual cookie input and management.
"""

import os
import json
import logging
import tempfile
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

class CookieManager:
    """Manages cookies for different platforms with manual input support."""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.cookies_dir = os.path.expanduser("~/.social_media_downloader/cookies")
        os.makedirs(self.cookies_dir, exist_ok=True)
        
    def store_manual_cookies(self, platform: str, cookies_text: str, format_type: str = 'netscape') -> bool:
        """Store manually entered cookies."""
        try:
            cookies_file = os.path.join(self.cookies_dir, f"{platform}_manual.txt")
            
            if format_type.lower() == 'netscape':
                # Netscape format (for yt-dlp)
                with open(cookies_file, 'w', encoding='utf-8') as f:
                    if not cookies_text.startswith('# Netscape HTTP Cookie File'):
                        f.write("# Netscape HTTP Cookie File\n")
                        f.write("# This is a generated file! Do not edit.\n\n")
                    f.write(cookies_text)
                    
            elif format_type.lower() == 'json':
                # JSON format
                cookies_data = json.loads(cookies_text)
                self._convert_json_to_netscape(cookies_data, cookies_file, platform)
                
            elif format_type.lower() == 'header':
                # Cookie header format
                self._convert_header_to_netscape(cookies_text, cookies_file, platform)
                
            logging.info(f"Manual cookies stored for {platform}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to store manual cookies for {platform}: {e}")
            return False
            
    def store_browser_cookies(self, platform: str, browser: str = 'chrome') -> bool:
        """Extract and store cookies from browser."""
        try:
            import browser_cookie3
            
            cookies_file = os.path.join(self.cookies_dir, f"{platform}_{browser}.txt")
            
            # Extract cookies based on platform domain
            domain_map = {
                'youtube': 'youtube.com',
                'tiktok': 'tiktok.com',
                'instagram': 'instagram.com',
                'twitter': 'twitter.com',
                'x': 'x.com'
            }
            
            domain = domain_map.get(platform.lower(), f"{platform}.com")
            
            # Get cookies from browser
            if browser.lower() == 'chrome':
                cookies = browser_cookie3.chrome(domain_name=domain)
            elif browser.lower() == 'firefox':
                cookies = browser_cookie3.firefox(domain_name=domain)
            elif browser.lower() == 'edge':
                cookies = browser_cookie3.edge(domain_name=domain)
            elif browser.lower() == 'brave':
                # Brave uses Chrome's cookie storage
                cookies = browser_cookie3.chrome(domain_name=domain)
            else:
                logging.error(f"Unsupported browser: {browser}")
                return False
                
            # Write to Netscape format
            with open(cookies_file, 'w', encoding='utf-8') as f:
                f.write("# Netscape HTTP Cookie File\n")
                f.write(f"# Extracted from {browser} for {platform}\n")
                f.write(f"# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                for cookie in cookies:
                    if domain in cookie.domain:
                        expires = int(cookie.expires) if cookie.expires else 0
                        secure = str(cookie.secure).upper()
                        f.write(f"{cookie.domain}\tTRUE\t{cookie.path}\t{secure}\t{expires}\t{cookie.name}\t{cookie.value}\n")
                        
            logging.info(f"Browser cookies extracted for {platform} from {browser}")
            return True
            
        except ImportError:
            logging.error("browser_cookie3 not available for browser cookie extraction")
            return False
        except Exception as e:
            logging.error(f"Failed to extract browser cookies: {e}")
            return False
            
    def _convert_json_to_netscape(self, cookies_json: List[Dict], output_file: str, platform: str):
        """Convert JSON cookies to Netscape format."""
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# Netscape HTTP Cookie File\n")
            f.write(f"# Converted from JSON for {platform}\n\n")
            
            for cookie in cookies_json:
                domain = cookie.get('domain', f".{platform}.com")
                path = cookie.get('path', '/')
                secure = 'TRUE' if cookie.get('secure', False) else 'FALSE'
                expires = cookie.get('expirationDate', 0)
                name = cookie.get('name', '')
                value = cookie.get('value', '')
                
                if name and value:
                    f.write(f"{domain}\tTRUE\t{path}\t{secure}\t{int(expires)}\t{name}\t{value}\n")
                    
    def _convert_header_to_netscape(self, cookie_header: str, output_file: str, platform: str):
        """Convert cookie header string to Netscape format."""
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# Netscape HTTP Cookie File\n")
            f.write(f"# Converted from header for {platform}\n\n")
            
            # Parse cookie header
            cookie_pairs = cookie_header.split(';')
            domain = f".{platform}.com"
            
            for pair in cookie_pairs:
                if '=' in pair:
                    name, value = pair.strip().split('=', 1)
                    expires = int((datetime.now() + timedelta(days=365)).timestamp())
                    f.write(f"{domain}\tTRUE\t/\tFALSE\t{expires}\t{name}\t{value}\n")
                    
    def get_cookies_file(self, platform: str, prefer_manual: bool = True) -> Optional[str]:
        """Get the best available cookies file for a platform."""
        try:
            manual_file = os.path.join(self.cookies_dir, f"{platform}_manual.txt")
            browser_files = [
                os.path.join(self.cookies_dir, f"{platform}_chrome.txt"),
                os.path.join(self.cookies_dir, f"{platform}_brave.txt"),
                os.path.join(self.cookies_dir, f"{platform}_firefox.txt"),
                os.path.join(self.cookies_dir, f"{platform}_edge.txt")
            ]
            
            # Prefer manual if requested and exists
            if prefer_manual and os.path.exists(manual_file):
                return manual_file
                
            # Check browser files
            for browser_file in browser_files:
                if os.path.exists(browser_file):
                    return browser_file
                    
            # Fall back to manual if no browser cookies
            if os.path.exists(manual_file):
                return manual_file
                
            return None
            
        except Exception as e:
            logging.error(f"Error getting cookies file: {e}")
            return None
            
    def validate_cookies_file(self, cookies_file: str) -> bool:
        """Validate that a cookies file is properly formatted."""
        try:
            if not os.path.exists(cookies_file):
                return False
                
            with open(cookies_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Check if it's Netscape format
            if not content.startswith('# Netscape HTTP Cookie File'):
                return False
                
            # Check for at least one valid cookie line
            lines = content.split('\n')
            for line in lines:
                if line and not line.startswith('#') and line.count('\t') >= 6:
                    return True
                    
            return False
            
        except Exception as e:
            logging.error(f"Error validating cookies file: {e}")
            return False
            
    def list_available_cookies(self) -> Dict[str, List[str]]:
        """List all available cookie files by platform."""
        try:
            cookies_info = {}
            
            if os.path.exists(self.cookies_dir):
                for filename in os.listdir(self.cookies_dir):
                    if filename.endswith('.txt'):
                        platform = filename.split('_')[0]
                        cookie_type = filename.replace(f"{platform}_", "").replace(".txt", "")
                        
                        if platform not in cookies_info:
                            cookies_info[platform] = []
                            
                        file_path = os.path.join(self.cookies_dir, filename)
                        if self.validate_cookies_file(file_path):
                            # Get file info
                            stat = os.stat(file_path)
                            modified = datetime.fromtimestamp(stat.st_mtime)
                            
                            cookies_info[platform].append({
                                'type': cookie_type,
                                'file': filename,
                                'modified': modified.strftime('%Y-%m-%d %H:%M:%S'),
                                'valid': True
                            })
                        else:
                            cookies_info[platform].append({
                                'type': cookie_type,
                                'file': filename,
                                'valid': False
                            })
                            
            return cookies_info
            
        except Exception as e:
            logging.error(f"Error listing cookies: {e}")
            return {}
            
    def delete_cookies(self, platform: str, cookie_type: str = None) -> bool:
        """Delete cookies for a platform."""
        try:
            if cookie_type:
                # Delete specific type
                filename = f"{platform}_{cookie_type}.txt"
                file_path = os.path.join(self.cookies_dir, filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logging.info(f"Deleted {cookie_type} cookies for {platform}")
                    return True
            else:
                # Delete all cookies for platform
                deleted = False
                for filename in os.listdir(self.cookies_dir):
                    if filename.startswith(f"{platform}_") and filename.endswith('.txt'):
                        file_path = os.path.join(self.cookies_dir, filename)
                        os.remove(file_path)
                        deleted = True
                        
                if deleted:
                    logging.info(f"Deleted all cookies for {platform}")
                    return True
                    
            return False
            
        except Exception as e:
            logging.error(f"Error deleting cookies: {e}")
            return False
            
    def export_cookies_template(self, platform: str) -> str:
        """Generate a template for manual cookie input."""
        template = f"""# Netscape HTTP Cookie File
# Manual template for {platform}
# Format: domain    flag    path    secure    expiration    name    value
# 
# Examples:
# .{platform}.com	TRUE	/	FALSE	1735689600	session_id	your_session_id_here
# .{platform}.com	TRUE	/	TRUE	1735689600	auth_token	your_auth_token_here
# 
# Instructions:
# 1. Replace the example values with your actual cookies
# 2. You can find these in your browser's Developer Tools > Application > Cookies
# 3. Each line represents one cookie
# 4. Use tabs (not spaces) to separate fields
# 5. Remove these instruction lines when done

"""
        return template
