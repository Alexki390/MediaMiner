
"""
Authentication manager for social media platforms.
Handles secure login, session management, and credential storage.
"""

import os
import json
import logging
import hashlib
import base64
import time
from typing import Dict, Any, Optional, Tuple
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import requests
import pickle

class AuthManager:
    """Manages authentication for various social media platforms."""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.config = config_manager.get_config()
        self.auth_dir = os.path.expanduser("~/.social_media_downloader/auth")
        os.makedirs(self.auth_dir, exist_ok=True)
        
        self.sessions = {}
        self.credentials_file = os.path.join(self.auth_dir, "credentials.enc")
        self.sessions_file = os.path.join(self.auth_dir, "sessions.enc")
        
        # Initialize encryption
        self._init_encryption()
        
        # Load existing credentials and sessions
        self._load_credentials()
        self._load_sessions()
        
    def _init_encryption(self):
        """Initialize encryption for credential storage."""
        try:
            key_file = os.path.join(self.auth_dir, "key.key")
            
            if os.path.exists(key_file):
                with open(key_file, "rb") as f:
                    self.key = f.read()
            else:
                # Generate new key
                password = os.urandom(32)  # Random password
                salt = os.urandom(16)
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                )
                key = base64.urlsafe_b64encode(kdf.derive(password))
                
                with open(key_file, "wb") as f:
                    f.write(key)
                    
                with open(os.path.join(self.auth_dir, "salt.key"), "wb") as f:
                    f.write(salt)
                    
                self.key = key
                
            self.cipher = Fernet(self.key)
            
        except Exception as e:
            logging.error(f"Failed to initialize encryption: {e}")
            self.cipher = None
            
    def _load_credentials(self):
        """Load encrypted credentials from file."""
        try:
            if os.path.exists(self.credentials_file) and self.cipher:
                with open(self.credentials_file, "rb") as f:
                    encrypted_data = f.read()
                    
                decrypted_data = self.cipher.decrypt(encrypted_data)
                self.credentials = json.loads(decrypted_data.decode())
            else:
                self.credentials = {}
                
        except Exception as e:
            logging.error(f"Failed to load credentials: {e}")
            self.credentials = {}
            
    def _save_credentials(self):
        """Save encrypted credentials to file."""
        try:
            if self.cipher:
                data = json.dumps(self.credentials).encode()
                encrypted_data = self.cipher.encrypt(data)
                
                with open(self.credentials_file, "wb") as f:
                    f.write(encrypted_data)
                    
        except Exception as e:
            logging.error(f"Failed to save credentials: {e}")
            
    def _load_sessions(self):
        """Load encrypted sessions from file."""
        try:
            if os.path.exists(self.sessions_file) and self.cipher:
                with open(self.sessions_file, "rb") as f:
                    encrypted_data = f.read()
                    
                decrypted_data = self.cipher.decrypt(encrypted_data)
                self.sessions = pickle.loads(decrypted_data)
                
                # Clean expired sessions
                self._clean_expired_sessions()
            else:
                self.sessions = {}
                
        except Exception as e:
            logging.error(f"Failed to load sessions: {e}")
            self.sessions = {}
            
    def _save_sessions(self):
        """Save encrypted sessions to file."""
        try:
            if self.cipher:
                data = pickle.dumps(self.sessions)
                encrypted_data = self.cipher.encrypt(data)
                
                with open(self.sessions_file, "wb") as f:
                    f.write(encrypted_data)
                    
        except Exception as e:
            logging.error(f"Failed to save sessions: {e}")
            
    def _clean_expired_sessions(self):
        """Remove expired sessions."""
        current_time = time.time()
        expired_platforms = []
        
        for platform, session_data in self.sessions.items():
            if session_data.get('expires_at', 0) < current_time:
                expired_platforms.append(platform)
                
        for platform in expired_platforms:
            del self.sessions[platform]
            logging.info(f"Removed expired session for {platform}")
            
    def store_credentials(self, platform: str, username: str, password: str, 
                         additional_data: Optional[Dict[str, Any]] = None):
        """Store encrypted credentials for a platform."""
        try:
            self.credentials[platform] = {
                'username': username,
                'password': password,
                'additional_data': additional_data or {},
                'stored_at': time.time()
            }
            
            self._save_credentials()
            logging.info(f"Credentials stored for {platform}")
            
        except Exception as e:
            logging.error(f"Failed to store credentials for {platform}: {e}")
            raise
            
    def get_credentials(self, platform: str) -> Optional[Dict[str, Any]]:
        """Get stored credentials for a platform."""
        return self.credentials.get(platform)
        
    def remove_credentials(self, platform: str):
        """Remove stored credentials for a platform."""
        if platform in self.credentials:
            del self.credentials[platform]
            self._save_credentials()
            logging.info(f"Credentials removed for {platform}")
            
    def create_session(self, platform: str, session_data: Dict[str, Any], 
                      expires_in: int = 3600):
        """Create and store a session."""
        try:
            expires_at = time.time() + expires_in
            
            self.sessions[platform] = {
                'session_data': session_data,
                'created_at': time.time(),
                'expires_at': expires_at,
                'last_used': time.time()
            }
            
            self._save_sessions()
            logging.info(f"Session created for {platform}")
            
        except Exception as e:
            logging.error(f"Failed to create session for {platform}: {e}")
            raise
            
    def get_session(self, platform: str) -> Optional[Dict[str, Any]]:
        """Get active session for a platform."""
        session = self.sessions.get(platform)
        
        if session and session.get('expires_at', 0) > time.time():
            # Update last used time
            session['last_used'] = time.time()
            self._save_sessions()
            return session.get('session_data')
            
        elif session:
            # Session expired
            del self.sessions[platform]
            self._save_sessions()
            
        return None
        
    def refresh_session(self, platform: str, new_session_data: Dict[str, Any], 
                       expires_in: int = 3600):
        """Refresh an existing session."""
        if platform in self.sessions:
            self.sessions[platform].update({
                'session_data': new_session_data,
                'expires_at': time.time() + expires_in,
                'last_used': time.time()
            })
            self._save_sessions()
            logging.info(f"Session refreshed for {platform}")
            
    def is_authenticated(self, platform: str) -> bool:
        """Check if authenticated for a platform."""
        return self.get_session(platform) is not None
        
    def logout(self, platform: str):
        """Logout from a platform."""
        if platform in self.sessions:
            del self.sessions[platform]
            self._save_sessions()
            logging.info(f"Logged out from {platform}")
            
    def logout_all(self):
        """Logout from all platforms."""
        self.sessions.clear()
        self._save_sessions()
        logging.info("Logged out from all platforms")
        
    def get_session_info(self, platform: str) -> Optional[Dict[str, Any]]:
        """Get session information (without sensitive data)."""
        session = self.sessions.get(platform)
        
        if session:
            return {
                'platform': platform,
                'created_at': session.get('created_at'),
                'expires_at': session.get('expires_at'),
                'last_used': session.get('last_used'),
                'is_expired': session.get('expires_at', 0) < time.time()
            }
            
        return None
        
    def list_stored_platforms(self) -> list:
        """List platforms with stored credentials."""
        return list(self.credentials.keys())
        
    def list_active_sessions(self) -> list:
        """List platforms with active sessions."""
        active_sessions = []
        
        for platform in self.sessions:
            if self.is_authenticated(platform):
                active_sessions.append(platform)
                
        return active_sessions
        
    def validate_credentials(self, platform: str, username: str, password: str) -> bool:
        """Validate credentials by attempting login."""
        try:
            # This would be implemented per platform
            # For now, just basic validation
            
            if not username or not password:
                return False
                
            if platform == "instagram":
                return self._validate_instagram_credentials(username, password)
            elif platform == "tiktok":
                return self._validate_tiktok_credentials(username, password)
            elif platform == "twitter":
                return self._validate_twitter_credentials(username, password)
            else:
                # Generic validation - just check format
                return len(username) > 0 and len(password) > 0
                
        except Exception as e:
            logging.error(f"Credential validation failed for {platform}: {e}")
            return False
            
    def _validate_instagram_credentials(self, username: str, password: str) -> bool:
        """Validate Instagram credentials."""
        try:
            # Implement Instagram-specific validation
            # This is a placeholder - real implementation would use Instagram API
            return len(username) > 0 and len(password) > 6
            
        except Exception as e:
            logging.error(f"Instagram credential validation failed: {e}")
            return False
            
    def _validate_tiktok_credentials(self, username: str, password: str) -> bool:
        """Validate TikTok credentials."""
        try:
            # Implement TikTok-specific validation
            return len(username) > 0 and len(password) > 6
            
        except Exception as e:
            logging.error(f"TikTok credential validation failed: {e}")
            return False
            
    def _validate_twitter_credentials(self, username: str, password: str) -> bool:
        """Validate Twitter credentials."""
        try:
            # Implement Twitter-specific validation
            return len(username) > 0 and len(password) > 6
            
        except Exception as e:
            logging.error(f"Twitter credential validation failed: {e}")
            return False
            
    def handle_two_factor(self, platform: str, code: str) -> bool:
        """Handle two-factor authentication."""
        try:
            # This would be implemented per platform
            # For now, just validate the code format
            
            if not code or len(code) < 4:
                return False
                
            # Platform-specific 2FA handling would go here
            return True
            
        except Exception as e:
            logging.error(f"2FA handling failed for {platform}: {e}")
            return False
            
    def get_auth_status(self) -> Dict[str, Any]:
        """Get comprehensive authentication status."""
        return {
            'stored_credentials': self.list_stored_platforms(),
            'active_sessions': self.list_active_sessions(),
            'total_stored': len(self.credentials),
            'total_active': len(self.list_active_sessions()),
            'session_info': {
                platform: self.get_session_info(platform) 
                for platform in self.sessions
            }
        }
