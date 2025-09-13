"""
Collaboration API endpoints for Vybe
Provides multi-user collaboration and session management
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
import json

from ..core.collaboration_manager import CollaborationManager, CollaborationType, UserRole, SessionStatus
from ..logger import log_info, log_error

collaboration_bp = Blueprint('collaboration', __name__, url_prefix='/api/collaboration')

# Initialize collaboration manager
collaboration_manager = CollaborationManager()


@collaboration_bp.route('/sessions', methods=['GET'])
@login_required
def get_sessions():
    """Get all collaboration sessions for the current user"""
    try:
        sessions = collaboration_manager.get_user_sessions(current_user.id)
        return jsonify({
            'success': True,
            'sessions': sessions
        })
    except Exception as e:
        log_error(f"Error getting collaboration sessions: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve sessions'
        }), 500


@collaboration_bp.route('/sessions', methods=['POST'])
@login_required
def create_session():
    """Create a new collaboration session"""
    try:
        data = request.get_json()
        
        session_name = data.get('name', 'Untitled Session')
        session_type_str = data.get('type', 'chat')
        description = data.get('description', '')
        max_participants = data.get('max_participants', 10)
        is_public = data.get('is_public', False)
        
        # Convert string type to CollaborationType enum
        try:
            session_type = CollaborationType(session_type_str.lower())
        except ValueError:
            return jsonify({
                'success': False,
                'error': f'Invalid session type: {session_type_str}'
            }), 400
        
        session = collaboration_manager.create_session(
            name=session_name,
            description=description,
            session_type=session_type,
            owner_id=current_user.id,
            max_participants=max_participants,
            is_public=is_public
        )
        
        return jsonify({
            'success': True,
            'session': session
        })
    except Exception as e:
        log_error(f"Error creating collaboration session: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to create session'
        }), 500


@collaboration_bp.route('/sessions/<session_id>', methods=['GET'])
@login_required
def get_session(session_id):
    """Get a specific collaboration session"""
    try:
        session = collaboration_manager.get_session(session_id)
        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
            
        return jsonify({
            'success': True,
            'session': session
        })
    except Exception as e:
        log_error(f"Error getting collaboration session: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve session'
        }), 500


@collaboration_bp.route('/sessions/<session_id>/join', methods=['POST'])
@login_required
def join_session(session_id):
    """Join a collaboration session"""
    try:
        data = request.get_json()
        role_str = data.get('role', 'participant')
        
        # Convert string role to UserRole enum
        try:
            role = UserRole(role_str.lower())
        except ValueError:
            return jsonify({
                'success': False,
                'error': f'Invalid role: {role_str}'
            }), 400
        
        success = collaboration_manager.add_participant(
            session_id=session_id,
            user_id=current_user.id,
            role=role
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Successfully joined session'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to join session'
            }), 400
    except Exception as e:
        log_error(f"Error joining collaboration session: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to join session'
        }), 500


@collaboration_bp.route('/sessions/<session_id>/leave', methods=['POST'])
@login_required
def leave_session(session_id):
    """Leave a collaboration session"""
    try:
        success = collaboration_manager.remove_participant(
            session_id=session_id,
            user_id=current_user.id
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Successfully left session'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to leave session'
            }), 400
    except Exception as e:
        log_error(f"Error leaving collaboration session: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to leave session'
        }), 500


@collaboration_bp.route('/sessions/<session_id>/messages', methods=['GET'])
@login_required
def get_messages(session_id):
    """Get messages for a collaboration session"""
    try:
        messages = collaboration_manager.get_session_messages(session_id)
        return jsonify({
            'success': True,
            'messages': messages
        })
    except Exception as e:
        log_error(f"Error getting collaboration messages: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve messages'
        }), 500


@collaboration_bp.route('/sessions/<session_id>/messages', methods=['POST'])
@login_required
def send_message(session_id):
    """Send a message to a collaboration session"""
    try:
        data = request.get_json()
        content = data.get('content', '')
        message_type = data.get('type', 'text')
        
        if not content.strip():
            return jsonify({
                'success': False,
                'error': 'Message content cannot be empty'
            }), 400
        
        message = collaboration_manager.send_message(
            session_id=session_id,
            sender_id=current_user.id,
            content=content,
            message_type=message_type
        )
        
        return jsonify({
            'success': True,
            'message': message
        })
    except Exception as e:
        log_error(f"Error sending collaboration message: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to send message'
        }), 500


@collaboration_bp.route('/sessions/<session_id>/messages/<message_id>', methods=['PUT'])
@login_required
def edit_message(session_id, message_id):
    """Edit a message in a collaboration session"""
    try:
        data = request.get_json()
        new_content = data.get('content', '')
        
        if not new_content.strip():
            return jsonify({
                'success': False,
                'error': 'Message content cannot be empty'
            }), 400
        
        success = collaboration_manager.edit_message(
            session_id=session_id,
            message_id=message_id,
            user_id=current_user.id,
            new_content=new_content
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Message updated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to update message'
            }), 400
    except Exception as e:
        log_error(f"Error editing collaboration message: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to update message'
        }), 500


@collaboration_bp.route('/sessions/<session_id>/messages/<message_id>', methods=['DELETE'])
@login_required
def delete_message(session_id, message_id):
    """Delete a message from a collaboration session"""
    try:
        success = collaboration_manager.delete_message(
            session_id=session_id,
            message_id=message_id,
            user_id=current_user.id
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Message deleted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to delete message'
            }), 400
    except Exception as e:
        log_error(f"Error deleting collaboration message: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to delete message'
        }), 500


@collaboration_bp.route('/sessions/<session_id>/status', methods=['PUT'])
@login_required
def update_session_status(session_id):
    """Update session status"""
    try:
        data = request.get_json()
        status_str = data.get('status', 'active')
        
        # Convert string status to SessionStatus enum
        try:
            status = SessionStatus(status_str.upper())
        except ValueError:
            return jsonify({
                'success': False,
                'error': f'Invalid status: {status_str}'
            }), 400
        
        success = collaboration_manager.update_session_status(
            session_id=session_id,
            status=status,
            user_id=current_user.id
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Session status updated'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to update session status'
            }), 400
    except Exception as e:
        log_error(f"Error updating session status: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to update session status'
        }), 500


@collaboration_bp.route('/sessions/<session_id>/statistics', methods=['GET'])
@login_required
def get_session_statistics(session_id):
    """Get statistics for a collaboration session"""
    try:
        stats = collaboration_manager.get_session_statistics(session_id)
        return jsonify({
            'success': True,
            'statistics': stats
        })
    except Exception as e:
        log_error(f"Error getting session statistics: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve statistics'
        }), 500


@collaboration_bp.route('/search', methods=['GET'])
@login_required
def search_sessions():
    """Search for collaboration sessions"""
    try:
        query = request.args.get('q', '')
        session_type = request.args.get('type', '')
        is_public = request.args.get('public', 'true').lower() == 'true'
        
        sessions = collaboration_manager.search_sessions(
            query=query,
            user_id=current_user.id
        )
        
        return jsonify({
            'success': True,
            'sessions': sessions
        })
    except Exception as e:
        log_error(f"Error searching sessions: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to search sessions'
        }), 500
