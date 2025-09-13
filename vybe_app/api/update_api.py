"""
Update Management API for Vybe AI
Provides endpoints for checking updates, configuring settings, and performing one-click updates
"""

from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required
import logging

from ..core.update_notifier import update_notifier
from ..utils.input_validation import InputValidator
from ..logger import log_info, log_warning, log_error

logger = logging.getLogger(__name__)

update_api = Blueprint('update_api', __name__)
input_validator = InputValidator()


@update_api.route('/check-updates', methods=['GET'])
@login_required
def api_check_updates():
    """Check for available updates"""
    try:
        force = request.args.get('force', 'false').lower() == 'true'
        
        update_info = update_notifier.check_for_updates(force=force)
        
        if update_info:
            return jsonify({
                'success': True,
                'update_available': True,
                'update_info': update_info
            })
        else:
            return jsonify({
                'success': True,
                'update_available': False,
                'message': 'No updates available'
            })
            
    except Exception as e:
        log_error(f"Error checking for updates: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to check for updates'
        }), 500


@update_api.route('/update-settings', methods=['GET', 'POST'])
@login_required
def api_update_settings():
    """Get or update notification settings"""
    try:
        if request.method == 'GET':
            return jsonify({
                'success': True,
                'settings': update_notifier.update_settings
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
                'check_frequency_hours': int,
                'notification_frequency_hours': int,
                'auto_check_enabled': bool,
                'one_click_update_enabled': bool,
                'backup_before_update': bool,
                'notify_on_beta': bool
            }
            
            validated_settings = {}
            for key, value in data.items():
                if key in valid_settings:
                    try:
                        if valid_settings[key] == bool:
                            validated_settings[key] = bool(value)
                        elif valid_settings[key] == int:
                            validated_settings[key] = int(value)
                        else:
                            validated_settings[key] = value
                    except (ValueError, TypeError):
                        return jsonify({
                            'success': False,
                            'error': f'Invalid value for {key}'
                        }), 400
            
            # Update settings
            update_notifier.update_settings_config(**validated_settings)
            
            return jsonify({
                'success': True,
                'message': 'Settings updated successfully',
                'settings': update_notifier.update_settings
            })
            
    except Exception as e:
        log_error(f"Error managing update settings: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to manage update settings'
        }), 500


@update_api.route('/perform-update', methods=['POST'])
@login_required
def api_perform_update():
    """Perform one-click update"""
    try:
        data = request.get_json()
        if not data or 'update_info' not in data:
            return jsonify({
                'success': False,
                'error': 'Update information required'
            }), 400
        
        update_info = data['update_info']
        
        # Validate update info
        required_fields = ['version', 'assets']
        for field in required_fields:
            if field not in update_info:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Perform update
        result = update_notifier.perform_one_click_update(update_info)
        
        if result['success']:
            log_info(f"One-click update successful: {result['message']}")
            return jsonify({
                'success': True,
                'message': result['message'],
                'backup_path': result.get('backup_path')
            })
        else:
            log_warning(f"One-click update failed: {result['error']}")
            return jsonify({
                'success': False,
                'error': result['error']
            }), 400
            
    except Exception as e:
        log_error(f"Error performing update: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to perform update'
        }), 500


@update_api.route('/update-status', methods=['GET'])
@login_required
def api_update_status():
    """Get current update status and statistics"""
    try:
        check_data = update_notifier._load_check_data()
        notification_data = update_notifier._load_notification_data()
        
        status = {
            'current_version': update_notifier.current_version,
            'last_check': check_data.get('last_check'),
            'last_version_checked': check_data.get('last_version'),
            'install_date': check_data.get('install_date'),
            'settings': update_notifier.update_settings,
            'notified_versions': notification_data.get('notified_versions', []),
            'last_notification': notification_data.get('last_daily_check')
        }
        
        return jsonify({
            'success': True,
            'status': status
        })
        
    except Exception as e:
        log_error(f"Error getting update status: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get update status'
        }), 500


@update_api.route('/dismiss-notification', methods=['POST'])
@login_required
def api_dismiss_notification():
    """Dismiss update notification for current version"""
    try:
        data = request.get_json()
        version = data.get('version') if data else None
        
        if not version:
            return jsonify({
                'success': False,
                'error': 'Version required'
            }), 400
        
        # Add to notified versions to prevent re-notification
        notification_data = update_notifier._load_notification_data()
        if version not in notification_data.get('notified_versions', []):
            notification_data['notified_versions'].append(version)
            update_notifier._save_notification_data(notification_data)
        
        return jsonify({
            'success': True,
            'message': f'Notification dismissed for version {version}'
        })
        
    except Exception as e:
        log_error(f"Error dismissing notification: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to dismiss notification'
        }), 500


@update_api.route('/restart-background-checker', methods=['POST'])
@login_required
def api_restart_background_checker():
    """Restart the background update checker"""
    try:
        # Start background checker
        update_notifier.start_background_checker()
        
        return jsonify({
            'success': True,
            'message': 'Background update checker restarted'
        })
        
    except Exception as e:
        log_error(f"Error restarting background checker: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to restart background checker'
        }), 500
