"""
System Tray Management API for Vybe AI
Provides endpoints for controlling system tray functionality and settings
"""

from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required
import logging

from ..core.system_tray_manager import get_system_tray_manager
from ..utils.input_validation import InputValidator
from ..logger import log_info, log_warning, log_error

logger = logging.getLogger(__name__)

system_tray_api = Blueprint('system_tray_api', __name__)
input_validator = InputValidator()


@system_tray_api.route('/status', methods=['GET'])
@login_required
def api_system_tray_status():
    """Get system tray status"""
    try:
        tray_manager = get_system_tray_manager()
        status = tray_manager.get_status()
        
        return jsonify({
            'success': True,
            'status': status
        })
        
    except Exception as e:
        log_error(f"Error getting system tray status: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get system tray status'
        }), 500


@system_tray_api.route('/settings', methods=['GET', 'POST'])
@login_required
def api_system_tray_settings():
    """Get or update system tray settings"""
    try:
        tray_manager = get_system_tray_manager()
        
        if request.method == 'GET':
            return jsonify({
                'success': True,
                'settings': tray_manager.settings
            })
        
        elif request.method == 'POST':
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'No data provided'
                }), 400
            
            # Validate settings
            valid_settings = {
                'start_minimized': bool,
                'minimize_to_tray': bool,
                'show_notifications': bool,
                'auto_start': bool,
                'close_to_tray': bool,
                'tray_icon_theme': str
            }
            
            validated_settings = {}
            for key, value in data.items():
                if key in valid_settings:
                    try:
                        if valid_settings[key] == bool:
                            validated_settings[key] = bool(value)
                        else:
                            validated_settings[key] = str(value)
                    except (ValueError, TypeError):
                        return jsonify({
                            'success': False,
                            'error': f'Invalid value for {key}'
                        }), 400
            
            # Update settings
            tray_manager.update_settings(**validated_settings)
            
            return jsonify({
                'success': True,
                'message': 'System tray settings updated successfully',
                'settings': tray_manager.settings
            })
            
    except Exception as e:
        log_error(f"Error managing system tray settings: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to manage system tray settings'
        }), 500


@system_tray_api.route('/minimize', methods=['POST'])
@login_required
def api_minimize_to_tray():
    """Minimize application to system tray"""
    try:
        tray_manager = get_system_tray_manager()
        
        if not tray_manager.is_available():
            return jsonify({
                'success': False,
                'error': 'System tray not available'
            }), 400
        
        tray_manager.minimize_to_tray()
        
        return jsonify({
            'success': True,
            'message': 'Application minimized to system tray'
        })
        
    except Exception as e:
        log_error(f"Error minimizing to tray: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to minimize to tray'
        }), 500


@system_tray_api.route('/restore', methods=['POST'])
@login_required
def api_restore_from_tray():
    """Restore application from system tray"""
    try:
        tray_manager = get_system_tray_manager()
        
        if not tray_manager.is_available():
            return jsonify({
                'success': False,
                'error': 'System tray not available'
            }), 400
        
        tray_manager.restore_from_tray()
        
        return jsonify({
            'success': True,
            'message': 'Application restored from system tray'
        })
        
    except Exception as e:
        log_error(f"Error restoring from tray: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to restore from tray'
        }), 500


@system_tray_api.route('/notification', methods=['POST'])
@login_required
def api_show_notification():
    """Show system tray notification"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        title = data.get('title', 'Vybe AI')
        message = data.get('message', '')
        duration = data.get('duration', 5)
        
        if not message:
            return jsonify({
                'success': False,
                'error': 'Message is required'
            }), 400
        
        # Validate inputs
        if len(title) > 100:
            return jsonify({
                'success': False,
                'error': 'Title too long (max 100 characters)'
            }), 400
        
        if len(message) > 500:
            return jsonify({
                'success': False,
                'error': 'Message too long (max 500 characters)'
            }), 400
        
        if not isinstance(duration, int) or duration < 1 or duration > 30:
            return jsonify({
                'success': False,
                'error': 'Duration must be between 1 and 30 seconds'
            }), 400
        
        tray_manager = get_system_tray_manager()
        
        if not tray_manager.is_available():
            return jsonify({
                'success': False,
                'error': 'System tray not available'
            }), 400
        
        tray_manager.show_notification(title, message, duration)
        
        return jsonify({
            'success': True,
            'message': 'Notification sent to system tray'
        })
        
    except Exception as e:
        log_error(f"Error showing notification: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to show notification'
        }), 500


@system_tray_api.route('/start', methods=['POST'])
@login_required
def api_start_system_tray():
    """Start system tray manager"""
    try:
        tray_manager = get_system_tray_manager()
        
        if not tray_manager.is_available():
            return jsonify({
                'success': False,
                'error': 'System tray not available (pystray not installed)'
            }), 400
        
        if tray_manager.is_running:
            return jsonify({
                'success': True,
                'message': 'System tray already running'
            })
        
        success = tray_manager.start()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'System tray started successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to start system tray'
            }), 500
        
    except Exception as e:
        log_error(f"Error starting system tray: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to start system tray'
        }), 500


@system_tray_api.route('/stop', methods=['POST'])
@login_required
def api_stop_system_tray():
    """Stop system tray manager"""
    try:
        tray_manager = get_system_tray_manager()
        
        if not tray_manager.is_running:
            return jsonify({
                'success': True,
                'message': 'System tray not running'
            })
        
        tray_manager.stop()
        
        return jsonify({
            'success': True,
            'message': 'System tray stopped successfully'
        })
        
    except Exception as e:
        log_error(f"Error stopping system tray: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to stop system tray'
        }), 500


@system_tray_api.route('/register-callback', methods=['POST'])
@login_required
def api_register_callback():
    """Register callback for system tray events"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        event = data.get('event')
        callback_url = data.get('callback_url')
        
        if not event or not callback_url:
            return jsonify({
                'success': False,
                'error': 'Event and callback_url are required'
            }), 400
        
        # Validate event types
        valid_events = ['minimize', 'restore', 'settings', 'quit']
        if event not in valid_events:
            return jsonify({
                'success': False,
                'error': f'Invalid event. Must be one of: {", ".join(valid_events)}'
            }), 400
        
        # Validate callback URL
        if not callback_url.startswith(('http://', 'https://', '/')):
            return jsonify({
                'success': False,
                'error': 'Invalid callback URL'
            }), 400
        
        tray_manager = get_system_tray_manager()
        
        # Create callback function
        def callback_wrapper():
            try:
                import requests
                if callback_url.startswith('/'):
                    # Internal callback
                    with current_app.test_client() as client:
                        response = client.post(callback_url)
                        return response.status_code == 200
                else:
                    # External callback
                    response = requests.post(callback_url, timeout=5)
                    return response.status_code == 200
            except Exception as e:
                log_error(f"Callback execution failed: {e}")
                return False
        
        tray_manager.register_callback(event, callback_wrapper)
        
        return jsonify({
            'success': True,
            'message': f'Callback registered for event: {event}'
        })
        
    except Exception as e:
        log_error(f"Error registering callback: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to register callback'
        }), 500


@system_tray_api.route('/check-availability', methods=['GET'])
@login_required
def api_check_availability():
    """Check if system tray is available"""
    try:
        tray_manager = get_system_tray_manager()
        
        return jsonify({
            'success': True,
            'available': tray_manager.is_available(),
            'running': tray_manager.is_running,
            'minimized': tray_manager.is_minimized
        })
        
    except Exception as e:
        log_error(f"Error checking system tray availability: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to check availability'
        }), 500
