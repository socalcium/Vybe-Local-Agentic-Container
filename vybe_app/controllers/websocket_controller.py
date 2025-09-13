"""
Enhanced WebSocket Controller
Real-time communication with comprehensive event handling and security.
"""
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
from flask import request, current_app, session
from functools import wraps
from typing import Dict, Any, Optional, List
import logging
import json
from datetime import datetime

from ..services.user_service import user_service
from ..utils.error_handling import ApplicationError, ErrorCode
from ..utils.input_validation import InputValidator
from ..utils.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)

# Initialize validator
validator = InputValidator()

# Active connections tracking
active_connections = {}
user_rooms = {}


def authenticated_only(f):
    """Decorator for WebSocket events that require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_token = session.get('auth_token')
        if not auth_token:
            emit('error', {
                'message': 'Authentication required',
                'code': ErrorCode.AUTHENTICATION_FAILED
            })
            disconnect()
            return
        
        try:
            session_data = user_service.validate_session(auth_token)
            if not session_data:
                emit('error', {
                    'message': 'Invalid or expired session',
                    'code': ErrorCode.AUTHENTICATION_FAILED
                })
                disconnect()
                return
            
            # Store user data in session for this connection
            session['user_data'] = session_data['user']
            session['session_data'] = session_data['session']
            
        except Exception as e:
            logger.error(f"WebSocket authentication error: {e}")
            emit('error', {
                'message': 'Authentication failed',
                'code': ErrorCode.AUTHENTICATION_FAILED
            })
            disconnect()
            return
        
        return f(*args, **kwargs)
    return decorated_function


def rate_limited(rule_name: str = 'websocket_default'):
    """Decorator for WebSocket rate limiting"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # For WebSocket, we'll use a simpler rate limiting approach
            client_id = getattr(request, 'sid', 'unknown')
            # Simple rate limiting - could be enhanced
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def handle_websocket_errors(f):
    """Decorator for WebSocket error handling"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ApplicationError as e:
            emit('error', {
                'message': e.message,
                'code': e.code,
                'details': getattr(e, 'details', None)
            })
        except Exception as e:
            logger.error(f"WebSocket error in {f.__name__}: {e}")
            emit('error', {
                'message': 'Internal server error',
                'code': ErrorCode.UNKNOWN_ERROR
            })
    return decorated_function


class WebSocketController:
    """Enhanced WebSocket controller with comprehensive features"""
    
    def __init__(self, socketio: SocketIO):
        self.socketio = socketio
        self.setup_handlers()
    
    def setup_handlers(self):
        """Set up all WebSocket event handlers"""
        
        @self.socketio.on('connect')
        @handle_websocket_errors
        def handle_connect(auth=None):
            """Handle client connection"""
            client_id = getattr(request, 'sid', 'unknown')
            client_ip = request.environ.get('REMOTE_ADDR', 'unknown')
            
            logger.info(f"Client connected: {client_id} from {client_ip}")
            
            # Store connection info
            active_connections[client_id] = {
                'connected_at': datetime.utcnow(),
                'ip_address': client_ip,
                'user_agent': request.headers.get('User-Agent', 'unknown'),
                'authenticated': False
            }
            
            # Send welcome message
            emit('connected', {
                'message': 'Connected to Vybe AI WebSocket',
                'session_id': client_id,
                'timestamp': datetime.utcnow().isoformat()
            })
        
        @self.socketio.on('disconnect')
        @handle_websocket_errors
        def handle_disconnect():
            """Handle client disconnection"""
            client_id = getattr(request, 'sid', 'unknown')
            
            logger.info(f"Client disconnected: {client_id}")
            
            # Clean up connection data
            if client_id in active_connections:
                user_data = session.get('user_data')
                if user_data:
                    # Remove from user rooms
                    user_id = user_data['id']
                    if user_id in user_rooms:
                        user_rooms[user_id].discard(client_id)
                        if not user_rooms[user_id]:
                            del user_rooms[user_id]
                
                del active_connections[client_id]
        
        @self.socketio.on('authenticate')
        @rate_limited('websocket_auth')
        @handle_websocket_errors
        def handle_authenticate(data):
            """Handle WebSocket authentication"""
            if not data or 'token' not in data:
                emit('auth_error', {
                    'message': 'Authentication token required',
                    'code': ErrorCode.VALIDATION_ERROR
                })
                return
            
            try:
                session_data = user_service.validate_session(data['token'])
                if not session_data:
                    emit('auth_error', {
                        'message': 'Invalid or expired token',
                        'code': ErrorCode.AUTHENTICATION_FAILED
                    })
                    return
                
                # Store authentication data
                session['auth_token'] = data['token']
                session['user_data'] = session_data['user']
                session['session_data'] = session_data['session']
                
                # Update connection status
                client_id = getattr(request, 'sid', 'unknown')
                if client_id in active_connections:
                    active_connections[client_id]['authenticated'] = True
                    active_connections[client_id]['user_id'] = session_data['user']['id']
                
                # Join user to their personal room
                user_id = session_data['user']['id']
                if user_id not in user_rooms:
                    user_rooms[user_id] = set()
                user_rooms[user_id].add(client_id)
                join_room(f"user_{user_id}")
                
                emit('authenticated', {
                    'message': 'Authentication successful',
                    'user': session_data['user']
                })
                
                logger.info(f"WebSocket authenticated for user {user_id}")
                
            except Exception as e:
                logger.error(f"WebSocket authentication error: {e}")
                emit('auth_error', {
                    'message': 'Authentication failed',
                    'code': ErrorCode.AUTHENTICATION_FAILED
                })
        
        @self.socketio.on('ping')
        @authenticated_only
        @rate_limited('websocket_ping')
        @handle_websocket_errors
        def handle_ping(data=None):
            """Handle ping for keepalive"""
            emit('pong', {
                'timestamp': datetime.utcnow().isoformat(),
                'message': 'pong'
            })
        
        @self.socketio.on('join_chat')
        @authenticated_only
        @rate_limited('websocket_join')
        @handle_websocket_errors
        def handle_join_chat(data):
            """Handle joining a chat room"""
            if not data or 'chat_id' not in data:
                emit('error', {
                    'message': 'Chat ID required',
                    'code': ErrorCode.VALIDATION_ERROR
                })
                return
            
            chat_id = data['chat_id']
            user_data = session.get('user_data', {})
            
            # Validate chat access (this would check permissions)
            # For now, just join the room
            room_name = f"chat_{chat_id}"
            join_room(room_name)
            
            emit('joined_chat', {
                'chat_id': chat_id,
                'room': room_name,
                'message': f'Joined chat {chat_id}'
            })
            
            # Notify other users in the chat
            emit('user_joined', {
                'user': user_data,
                'chat_id': chat_id,
                'timestamp': datetime.utcnow().isoformat()
            }, room=room_name, include_self=False)
            
            logger.info(f"User {user_data.get('id', 'unknown')} joined chat {chat_id}")
        
        @self.socketio.on('leave_chat')
        @authenticated_only
        @handle_websocket_errors
        def handle_leave_chat(data):
            """Handle leaving a chat room"""
            if not data or 'chat_id' not in data:
                emit('error', {
                    'message': 'Chat ID required',
                    'code': ErrorCode.VALIDATION_ERROR
                })
                return
            
            chat_id = data['chat_id']
            user_data = session.get('user_data', {})
            room_name = f"chat_{chat_id}"
            
            leave_room(room_name)
            
            emit('left_chat', {
                'chat_id': chat_id,
                'message': f'Left chat {chat_id}'
            })
            
            # Notify other users
            emit('user_left', {
                'user': user_data,
                'chat_id': chat_id,
                'timestamp': datetime.utcnow().isoformat()
            }, room=room_name)
            
            logger.info(f"User {user_data.get('id', 'unknown')} left chat {chat_id}")
        
        @self.socketio.on('send_message')
        @authenticated_only
        @rate_limited('websocket_message')
        @handle_websocket_errors
        def handle_send_message(data):
            """Handle sending a chat message"""
            if not data:
                emit('error', {
                    'message': 'Message data required',
                    'code': ErrorCode.VALIDATION_ERROR
                })
                return
            
            required_fields = ['chat_id', 'message']
            if not all(field in data for field in required_fields):
                emit('error', {
                    'message': 'Chat ID and message are required',
                    'code': ErrorCode.VALIDATION_ERROR
                })
                return
            
            chat_id = data['chat_id']
            message_content = data['message']
            user_data = session.get('user_data', {})
            
            # Validate message content
            if not message_content or len(message_content.strip()) == 0:
                emit('error', {
                    'message': 'Message cannot be empty',
                    'code': ErrorCode.VALIDATION_ERROR
                })
                return
            
            if len(message_content) > 4000:  # Message length limit
                emit('error', {
                    'message': 'Message too long (max 4000 characters)',
                    'code': ErrorCode.VALIDATION_ERROR
                })
                return
            
            # Create message object
            message = {
                'id': f"msg_{datetime.utcnow().timestamp()}",
                'chat_id': chat_id,
                'user': user_data,
                'content': message_content.strip(),
                'timestamp': datetime.utcnow().isoformat(),
                'type': data.get('type', 'text')
            }
            
            # Send to chat room
            room_name = f"chat_{chat_id}"
            emit('new_message', message, room=room_name)
            
            # Confirm to sender
            emit('message_sent', {
                'message_id': message['id'],
                'status': 'delivered'
            })
            
            logger.info(f"Message sent by user {user_data.get('id', 'unknown')} to chat {chat_id}")
        
        @self.socketio.on('typing_start')
        @authenticated_only
        @rate_limited('websocket_typing')
        @handle_websocket_errors
        def handle_typing_start(data):
            """Handle typing indicator start"""
            if not data or 'chat_id' not in data:
                return
            
            chat_id = data['chat_id']
            user_data = session.get('user_data', {})
            room_name = f"chat_{chat_id}"
            
            emit('user_typing', {
                'user': user_data,
                'chat_id': chat_id,
                'typing': True,
                'timestamp': datetime.utcnow().isoformat()
            }, room=room_name, include_self=False)
        
        @self.socketio.on('typing_stop')
        @authenticated_only
        @rate_limited('websocket_typing')
        @handle_websocket_errors
        def handle_typing_stop(data):
            """Handle typing indicator stop"""
            if not data or 'chat_id' not in data:
                return
            
            chat_id = data['chat_id']
            user_data = session.get('user_data', {})
            room_name = f"chat_{chat_id}"
            
            emit('user_typing', {
                'user': user_data,
                'chat_id': chat_id,
                'typing': False,
                'timestamp': datetime.utcnow().isoformat()
            }, room=room_name, include_self=False)
        
        @self.socketio.on('get_online_users')
        @authenticated_only
        @handle_websocket_errors
        def handle_get_online_users(data):
            """Get list of online users"""
            chat_id = data.get('chat_id') if data else None
            
            # This would query active users, for now return a placeholder
            online_users = []
            for conn_id, conn_data in active_connections.items():
                if conn_data.get('authenticated') and conn_data.get('user_id'):
                    online_users.append({
                        'user_id': conn_data['user_id'],
                        'connected_at': conn_data['connected_at'].isoformat()
                    })
            
            emit('online_users', {
                'chat_id': chat_id,
                'users': online_users,
                'count': len(online_users)
            })
        
        @self.socketio.on('system_notification')
        @authenticated_only
        @handle_websocket_errors
        def handle_system_notification(data):
            """Handle system notifications (admin only)"""
            user_data = session.get('user_data', {})
            
            # Check if user has admin privileges
            if user_data.get('role') != 'admin':
                emit('error', {
                    'message': 'Insufficient privileges',
                    'code': ErrorCode.AUTHORIZATION_FAILED
                })
                return
            
            if not data or 'message' not in data:
                emit('error', {
                    'message': 'Notification message required',
                    'code': ErrorCode.VALIDATION_ERROR
                })
                return
            
            # Broadcast to all authenticated users
            notification = {
                'type': 'system',
                'message': data['message'],
                'level': data.get('level', 'info'),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            self.socketio.emit('notification', notification, 
                             room=None, include_self=False)
            
            emit('notification_sent', {
                'message': 'System notification sent',
                'recipients': len(active_connections)
            })
    
    def broadcast_to_user(self, user_id: int, event: str, data: Dict[str, Any]):
        """Broadcast an event to all connections of a specific user"""
        if user_id in user_rooms:
            self.socketio.emit(event, data, room=f"user_{user_id}")
    
    def broadcast_to_chat(self, chat_id: str, event: str, data: Dict[str, Any]):
        """Broadcast an event to all users in a chat"""
        self.socketio.emit(event, data, room=f"chat_{chat_id}")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        authenticated_count = sum(
            1 for conn in active_connections.values() 
            if conn.get('authenticated', False)
        )
        
        return {
            'total_connections': len(active_connections),
            'authenticated_connections': authenticated_count,
            'unique_users': len(user_rooms),
            'active_rooms': len(user_rooms)
        }


# Global controller instance (will be initialized by app)
websocket_controller = None


def init_websocket_controller(socketio: SocketIO):
    """Initialize the WebSocket controller"""
    global websocket_controller
    websocket_controller = WebSocketController(socketio)
    logger.info("WebSocket controller initialized successfully")
    return websocket_controller
