
"""
Anonymous usage analytics for improving the application.
"""

import os
import json
import logging
import hashlib
from typing import Dict, Any
from datetime import datetime, timedelta
import requests
import threading

class AnalyticsManager:
    """Manages anonymous usage analytics."""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.config = config_manager.get_config()
        self.analytics_enabled = self.config.get('analytics_enabled', True)
        self.session_id = self._generate_session_id()
        self.analytics_data = []
        
    def _generate_session_id(self) -> str:
        """Generate anonymous session ID."""
        import uuid
        return str(uuid.uuid4())[:8]
        
    def track_download(self, platform: str, success: bool, file_count: int = 0):
        """Track download event."""
        if not self.analytics_enabled:
            return
            
        event = {
            'event': 'download',
            'platform': platform,
            'success': success,
            'file_count': file_count,
            'timestamp': datetime.now().isoformat(),
            'session_id': self.session_id
        }
        
        self.analytics_data.append(event)
        
    def track_app_start(self):
        """Track application start."""
        if not self.analytics_enabled:
            return
            
        event = {
            'event': 'app_start',
            'timestamp': datetime.now().isoformat(),
            'session_id': self.session_id
        }
        
        self.analytics_data.append(event)
        
    def track_error(self, error_type: str, platform: str = None):
        """Track error occurrence."""
        if not self.analytics_enabled:
            return
            
        event = {
            'event': 'error',
            'error_type': error_type,
            'platform': platform,
            'timestamp': datetime.now().isoformat(),
            'session_id': self.session_id
        }
        
        self.analytics_data.append(event)
        
    def send_analytics(self):
        """Send analytics data asynchronously."""
        if not self.analytics_enabled or not self.analytics_data:
            return
            
        def send_data():
            try:
                # Send to your analytics endpoint
                # requests.post('https://your-analytics-endpoint.com/data', json=self.analytics_data)
                self.analytics_data.clear()
            except Exception as e:
                logging.debug(f"Analytics send failed: {e}")
                
        thread = threading.Thread(target=send_data, daemon=True)
        thread.start()
        
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get local usage statistics."""
        stats = {
            'total_downloads': len([e for e in self.analytics_data if e['event'] == 'download']),
            'successful_downloads': len([e for e in self.analytics_data if e['event'] == 'download' and e['success']]),
            'platforms_used': list(set([e['platform'] for e in self.analytics_data if e.get('platform')])),
            'session_duration': self._calculate_session_duration()
        }
        return stats
        
    def _calculate_session_duration(self) -> float:
        """Calculate current session duration in minutes."""
        if not self.analytics_data:
            return 0
            
        start_time = datetime.fromisoformat(self.analytics_data[0]['timestamp'])
        current_time = datetime.now()
        duration = (current_time - start_time).total_seconds() / 60
        return round(duration, 2)
