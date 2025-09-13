"""
Notifications API for Vybe
Handles desktop notifications and notification history
"""

from flask import Blueprint, jsonify, request
from ..auth import test_mode_login_required, current_user
from typing import Dict, Any

from ..core.notifications import get_notification_manager, send_desktop_notification
from ..logger import logger

notifications_bp = Blueprint('notifications', __name__, url_prefix='/notifications')


@notifications_bp.route('/send', methods=['POST'])
@test_mode_login_required
def send_notification():
    """Send a custom notification"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400

        title = data.get('title', '').strip()
        message = data.get('message', '').strip()
        notification_type = data.get('type', 'info')
        action_url = data.get('action_url')

        if not title or not message:
            return jsonify({
                'success': False,
                'error': 'Title and message are required'
            }), 400

        send_desktop_notification(
            title=title,
            message=message,
            notification_type=notification_type,
            action_url=action_url
        )

        return jsonify({
            'success': True,
            'message': 'Notification sent successfully'
        })

    except Exception as e:
        logger.error(f"Error sending notification: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@notifications_bp.route('/history', methods=['GET'])
@test_mode_login_required
def get_notification_history():
    """Get notification history"""
    try:
        limit = request.args.get('limit', 50, type=int)
        
        notification_manager = get_notification_manager()
        history = notification_manager.get_notification_history(limit)

        return jsonify({
            'success': True,
            'notifications': history,
            'count': len(history)
        })

    except Exception as e:
        logger.error(f"Error getting notification history: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@notifications_bp.route('/clear-history', methods=['POST'])
@test_mode_login_required
def clear_notification_history():
    """Clear notification history"""
    try:
        notification_manager = get_notification_manager()
        notification_manager.clear_history()

        return jsonify({
            'success': True,
            'message': 'Notification history cleared'
        })

    except Exception as e:
        logger.error(f"Error clearing notification history: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@notifications_bp.route('/test', methods=['POST'])
@test_mode_login_required
def test_notification():
    """Send a test notification"""
    try:
        send_desktop_notification(
            title="🧪 Test Notification",
            message="This is a test notification from Vybe AI Assistant",
            notification_type="info"
        )

        return jsonify({
            'success': True,
            'message': 'Test notification sent'
        })

    except Exception as e:
        logger.error(f"Error sending test notification: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
