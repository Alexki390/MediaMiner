
"""
Comprehensive error handling and recovery system.
"""

import logging
import traceback
import time
import os
import json
from typing import Dict, Any, Optional, Callable, List
from enum import Enum
from functools import wraps

class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """Error categories."""
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    FILE_SYSTEM = "file_system"
    PARSING = "parsing"
    PLATFORM_SPECIFIC = "platform_specific"
    CONFIGURATION = "configuration"
    SYSTEM = "system"
    USER_INPUT = "user_input"

class ErrorHandler:
    """Comprehensive error handling and recovery system."""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.config = config_manager.get_config()
        
        # Error tracking
        self.error_log = []
        self.error_stats = {}
        self.recovery_attempts = {}
        
        # Error log file
        self.error_log_file = os.path.expanduser(
            "~/.social_media_downloader/logs/error_analysis.json"
        )
        
        # Load previous error data
        self._load_error_history()
        
    def _load_error_history(self):
        """Load previous error history for analysis."""
        try:
            if os.path.exists(self.error_log_file):
                with open(self.error_log_file, 'r') as f:
                    data = json.load(f)
                    self.error_stats = data.get('stats', {})
                    self.error_log = data.get('recent_errors', [])[-100:]  # Keep last 100
        except Exception as e:
            logging.warning(f"Could not load error history: {e}")
            
    def _save_error_history(self):
        """Save error history to file."""
        try:
            os.makedirs(os.path.dirname(self.error_log_file), exist_ok=True)
            
            data = {
                'stats': self.error_stats,
                'recent_errors': self.error_log[-100:],  # Keep last 100
                'last_updated': time.time()
            }
            
            with open(self.error_log_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logging.error(f"Could not save error history: {e}")
            
    def handle_error(self, error: Exception, context: Dict[str, Any] = None, 
                    category: ErrorCategory = ErrorCategory.SYSTEM,
                    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                    recovery_action: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Handle an error with comprehensive logging and recovery.
        
        Args:
            error: The exception that occurred
            context: Additional context about the error
            category: Error category
            severity: Error severity
            recovery_action: Optional recovery function
            
        Returns:
            Dict with error info and recovery status
        """
        try:
            error_info = {
                'timestamp': time.time(),
                'error_type': type(error).__name__,
                'error_message': str(error),
                'category': category.value,
                'severity': severity.value,
                'context': context or {},
                'traceback': traceback.format_exc(),
                'recovery_attempted': False,
                'recovery_successful': False
            }
            
            # Log the error
            self._log_error(error_info)
            
            # Update statistics
            self._update_error_stats(error_info)
            
            # Attempt recovery if provided
            if recovery_action:
                try:
                    error_info['recovery_attempted'] = True
                    recovery_result = recovery_action()
                    error_info['recovery_successful'] = bool(recovery_result)
                    error_info['recovery_result'] = recovery_result
                    
                except Exception as recovery_error:
                    error_info['recovery_error'] = str(recovery_error)
                    logging.error(f"Recovery action failed: {recovery_error}")
                    
            # Save error history
            self._save_error_history()
            
            return error_info
            
        except Exception as handler_error:
            logging.critical(f"Error handler itself failed: {handler_error}")
            return {
                'error': 'Error handler failed',
                'original_error': str(error),
                'handler_error': str(handler_error)
            }
            
    def _log_error(self, error_info: Dict[str, Any]):
        """Log error with appropriate level."""
        severity = error_info['severity']
        message = f"[{error_info['category'].upper()}] {error_info['error_type']}: {error_info['error_message']}"
        
        if severity == ErrorSeverity.CRITICAL.value:
            logging.critical(message)
        elif severity == ErrorSeverity.HIGH.value:
            logging.error(message)
        elif severity == ErrorSeverity.MEDIUM.value:
            logging.warning(message)
        else:
            logging.info(message)
            
        # Add to error log
        self.error_log.append(error_info)
        
    def _update_error_stats(self, error_info: Dict[str, Any]):
        """Update error statistics."""
        error_type = error_info['error_type']
        category = error_info['category']
        severity = error_info['severity']
        
        # Initialize stats if needed
        if error_type not in self.error_stats:
            self.error_stats[error_type] = {
                'count': 0,
                'categories': {},
                'severities': {},
                'first_seen': error_info['timestamp'],
                'last_seen': error_info['timestamp']
            }
            
        # Update counts
        stats = self.error_stats[error_type]
        stats['count'] += 1
        stats['last_seen'] = error_info['timestamp']
        
        # Update category stats
        if category not in stats['categories']:
            stats['categories'][category] = 0
        stats['categories'][category] += 1
        
        # Update severity stats
        if severity not in stats['severities']:
            stats['severities'][severity] = 0
        stats['severities'][severity] += 1
        
    def with_error_handling(self, category: ErrorCategory = ErrorCategory.SYSTEM,
                           severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                           recovery_action: Optional[Callable] = None,
                           reraise: bool = False):
        """
        Decorator for automatic error handling.
        
        Args:
            category: Error category
            severity: Error severity
            recovery_action: Optional recovery function
            reraise: Whether to reraise the exception after handling
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    context = {
                        'function': func.__name__,
                        'args': str(args)[:200],  # Limit length
                        'kwargs': str(kwargs)[:200]
                    }
                    
                    error_info = self.handle_error(
                        e, context, category, severity, recovery_action
                    )
                    
                    if reraise:
                        raise e
                        
                    return {'error': error_info, 'success': False}
                    
            return wrapper
        return decorator
        
    def create_recovery_action(self, action_type: str, **kwargs) -> Callable:
        """Create common recovery actions."""
        
        if action_type == "retry":
            max_attempts = kwargs.get('max_attempts', 3)
            delay = kwargs.get('delay', 1)
            func = kwargs.get('func')
            
            def retry_action():
                for attempt in range(max_attempts):
                    try:
                        if func:
                            return func()
                        return True
                    except Exception as e:
                        if attempt == max_attempts - 1:
                            raise e
                        time.sleep(delay * (attempt + 1))
                return False
                
            return retry_action
            
        elif action_type == "fallback":
            fallback_func = kwargs.get('fallback_func')
            
            def fallback_action():
                if fallback_func:
                    return fallback_func()
                return False
                
            return fallback_action
            
        elif action_type == "reset":
            reset_func = kwargs.get('reset_func')
            
            def reset_action():
                if reset_func:
                    return reset_func()
                return False
                
            return reset_action
            
        return lambda: False
        
    def get_error_stats(self) -> Dict[str, Any]:
        """Get comprehensive error statistics."""
        total_errors = sum(stats['count'] for stats in self.error_stats.values())
        
        most_common = sorted(
            self.error_stats.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )[:10]
        
        category_stats = {}
        severity_stats = {}
        
        for error_type, stats in self.error_stats.items():
            for category, count in stats['categories'].items():
                category_stats[category] = category_stats.get(category, 0) + count
                
            for severity, count in stats['severities'].items():
                severity_stats[severity] = severity_stats.get(severity, 0) + count
                
        return {
            'total_errors': total_errors,
            'unique_error_types': len(self.error_stats),
            'most_common_errors': most_common,
            'category_breakdown': category_stats,
            'severity_breakdown': severity_stats,
            'recent_error_count': len(self.error_log),
            'error_rate_trend': self._calculate_error_trend()
        }
        
    def _calculate_error_trend(self) -> Dict[str, Any]:
        """Calculate error rate trends."""
        try:
            recent_errors = [e for e in self.error_log if e['timestamp'] > time.time() - 3600]  # Last hour
            older_errors = [e for e in self.error_log if e['timestamp'] <= time.time() - 3600]
            
            return {
                'last_hour': len(recent_errors),
                'previous_period': len(older_errors),
                'trend': 'increasing' if len(recent_errors) > len(older_errors) else 'decreasing'
            }
        except:
            return {'trend': 'unknown'}
            
    def clear_error_history(self):
        """Clear error history."""
        self.error_log.clear()
        self.error_stats.clear()
        self._save_error_history()
        logging.info("Error history cleared")
        
    def export_error_report(self, filepath: str):
        """Export detailed error report."""
        try:
            report = {
                'generated_at': time.time(),
                'statistics': self.get_error_stats(),
                'detailed_errors': self.error_log,
                'error_patterns': self._analyze_error_patterns()
            }
            
            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2)
                
            logging.info(f"Error report exported to {filepath}")
            
        except Exception as e:
            logging.error(f"Failed to export error report: {e}")
            
    def _analyze_error_patterns(self) -> Dict[str, Any]:
        """Analyze error patterns for insights."""
        patterns = {
            'recurring_errors': {},
            'error_clusters': {},
            'time_patterns': {}
        }
        
        try:
            # Find recurring error sequences
            for i, error in enumerate(self.error_log[:-1]):
                next_error = self.error_log[i + 1]
                
                sequence = f"{error['error_type']} -> {next_error['error_type']}"
                patterns['recurring_errors'][sequence] = patterns['recurring_errors'].get(sequence, 0) + 1
                
            # Time-based patterns
            hourly_errors = {}
            for error in self.error_log:
                hour = int((error['timestamp'] % 86400) // 3600)  # Hour of day
                hourly_errors[hour] = hourly_errors.get(hour, 0) + 1
                
            patterns['time_patterns']['hourly_distribution'] = hourly_errors
            
        except Exception as e:
            logging.warning(f"Error pattern analysis failed: {e}")
            
        return patterns

# Common error recovery functions
def network_retry_recovery(func, max_attempts=3):
    """Recovery action for network errors."""
    def recovery():
        for attempt in range(max_attempts):
            try:
                time.sleep(2 ** attempt)  # Exponential backoff
                return func()
            except Exception:
                if attempt == max_attempts - 1:
                    raise
        return False
    return recovery

def file_permission_recovery(filepath):
    """Recovery action for file permission errors."""
    def recovery():
        try:
            # Try to fix permissions
            os.chmod(filepath, 0o666)
            return True
        except:
            return False
    return recovery

def authentication_retry_recovery(auth_func, credentials):
    """Recovery action for authentication errors."""
    def recovery():
        try:
            # Clear cached auth and retry
            return auth_func(**credentials)
        except:
            return False
    return recovery
