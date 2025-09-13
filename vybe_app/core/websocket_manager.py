"""
WebSocket Manager for Vybe Application
Provides WebSocket connection management, health monitoring, and automatic reconnection
"""

import time
import threading
import asyncio
import uuid
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import json
import weakref
from collections import deque

from flask_socketio import SocketIO, emit, disconnect
from flask import request, session

from ..logger import log_info, log_warning, log_error


class ConnectionState(Enum):
    """WebSocket connection states"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


@dataclass
class ConnectionInfo:
    """Connection information"""
    sid: str
    user_id: Optional[str]
    ip_address: str
    user_agent: str
    connected_at: datetime
    last_activity: datetime
    state: ConnectionState
    message_count: int = 0
    error_count: int = 0
    pool_id: Optional[str] = None  # Connection pool identifier
    session_data: Optional[Dict[str, Any]] = None  # Session data for the connection
    
    def __post_init__(self):
        """Initialize session_data if not provided"""
        if self.session_data is None:
            self.session_data = {}


class ConnectionPool:
    """Connection pool for managing WebSocket connections efficiently"""
    
    def __init__(self, max_connections: int = 100, max_idle_time: int = 300):
        self.max_connections = max_connections
        self.max_idle_time = max_idle_time
        self.active_connections: Dict[str, ConnectionInfo] = {}
        self.idle_connections: deque = deque()
        self.connection_stats = {
            'created': 0,
            'reused': 0,
            'closed': 0,
            'timeout': 0
        }
        self._lock = threading.RLock()
    
    def get_connection(self, sid: str, user_id: Optional[str] = None) -> Optional[ConnectionInfo]:
        """Get connection from pool or create new one"""
        with self._lock:
            # Check if connection already exists
            if sid in self.active_connections:
                conn = self.active_connections[sid]
                conn.last_activity = datetime.utcnow()
                return conn
            
            # Try to reuse idle connection
            if self.idle_connections:
                conn = self.idle_connections.popleft()
                if self._is_connection_valid(conn):
                    conn.sid = sid
                    conn.user_id = user_id
                    conn.last_activity = datetime.utcnow()
                    conn.state = ConnectionState.CONNECTED
                    
                    # Clear any old session data to prevent session hijacking
                    if hasattr(conn, 'session_data'):
                        conn.session_data = {}
                    
                    self.active_connections[sid] = conn
                    self.connection_stats['reused'] += 1
                    log_info(f"Reused connection {sid} with cleared session data")
                    return conn
            
            # Create new connection if pool not full
            if len(self.active_connections) < self.max_connections:
                conn = ConnectionInfo(
                    sid=sid,
                    user_id=user_id,
                    ip_address=request.environ.get('REMOTE_ADDR', 'unknown'),
                    user_agent=request.headers.get('User-Agent', 'unknown'),
                    connected_at=datetime.utcnow(),
                    last_activity=datetime.utcnow(),
                    state=ConnectionState.CONNECTED
                )
                self.active_connections[sid] = conn
                self.connection_stats['created'] += 1
                return conn
            
            return None
    
    def release_connection(self, sid: str, keep_alive: bool = False):
        """Release connection back to pool or close it"""
        with self._lock:
            if sid in self.active_connections:
                conn = self.active_connections.pop(sid)
                
                if keep_alive and len(self.idle_connections) < self.max_connections // 2:
                    # Keep connection in idle pool
                    conn.state = ConnectionState.DISCONNECTED
                    self.idle_connections.append(conn)
                else:
                    # Close connection
                    self.connection_stats['closed'] += 1
    
    def cleanup_idle_connections(self):
        """Clean up idle connections that have timed out"""
        with self._lock:
            current_time = datetime.utcnow()
            while self.idle_connections:
                conn = self.idle_connections[0]
                if (current_time - conn.last_activity).total_seconds() > self.max_idle_time:
                    self.idle_connections.popleft()
                    self.connection_stats['timeout'] += 1
                else:
                    break
    
    def _is_connection_valid(self, conn: ConnectionInfo) -> bool:
        """Check if connection is still valid"""
        return (datetime.utcnow() - conn.last_activity).total_seconds() < self.max_idle_time
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        with self._lock:
            return {
                'active_connections': len(self.active_connections),
                'idle_connections': len(self.idle_connections),
                'max_connections': self.max_connections,
                'stats': self.connection_stats.copy()
            }


class WebSocketManager:
    """Manages WebSocket connections with health monitoring and automatic reconnection"""
    
    def __init__(self, socketio: SocketIO):
        self.socketio = socketio
        self.connections: Dict[str, ConnectionInfo] = {}
        self.event_handlers: Dict[str, List[Callable]] = {}
        self.health_check_interval = 30  # seconds
        self.connection_timeout = 300  # seconds
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 5  # seconds
        
        # Connection pooling
        self.connection_pool = ConnectionPool(max_connections=200, max_idle_time=600)
        
        # Statistics
        self.stats = {
            'total_connections': 0,
            'active_connections': 0,
            'total_messages': 0,
            'total_errors': 0,
            'reconnections': 0,
            'pool_hits': 0,
            'pool_misses': 0
        }
        
        # Start health monitoring
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._health_monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        # Start connection pool cleanup
        self.pool_cleanup_thread = threading.Thread(target=self._pool_cleanup_loop, daemon=True)
        self.pool_cleanup_thread.start()
        
        # Register default event handlers
        self._register_default_handlers()
        
        log_info("WebSocket manager initialized with connection pooling")
    
    def _register_default_handlers(self):
        """Register default WebSocket event handlers"""
        @self.socketio.on('connect')
        def handle_connect(auth):
            self._handle_connect()
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            self._handle_disconnect()
        
        @self.socketio.on('error')
        def handle_error(data):
            self._handle_error(data)
        
        @self.socketio.on('ping')
        def handle_ping():
            self._handle_ping()
    
    def _get_current_sid(self):
        """Get current session ID from Flask-SocketIO context"""
        # For Flask-SocketIO, we need to track this differently
        # This is a temporary solution until we implement proper session tracking
        import uuid
        return str(uuid.uuid4())
    
    def _handle_connect(self):
        """Handle new WebSocket connection"""
        # In Flask-SocketIO, we can get the session ID from the socketio context
        import uuid
        sid = str(uuid.uuid4())  # Generate a unique session ID
        user_id = getattr(request, 'user_id', None)
        
        # Get connection from pool or create new one
        connection_info = self.connection_pool.get_connection(sid, user_id)
        
        if connection_info:
            self.connections[sid] = connection_info
            self.stats['total_connections'] += 1
            self.stats['active_connections'] += 1
            
            if connection_info.pool_id:
                self.stats['pool_hits'] += 1
            else:
                self.stats['pool_misses'] += 1
            
            log_info(f"WebSocket connected: {sid} (user: {user_id})")
        else:
            log_warning(f"Failed to establish WebSocket connection: {sid} (pool full)")
            disconnect()
    
    def _handle_disconnect(self):
        """Handle WebSocket disconnection"""
        sid = self._get_current_sid()
        
        if sid in self.connections:
            connection_info = self.connections[sid]
            self.stats['active_connections'] -= 1
            
            # Release connection back to pool
            self.connection_pool.release_connection(sid, keep_alive=True)
            
            log_info(f"WebSocket disconnected: {sid}")
    
    def _handle_error(self, data):
        """Handle WebSocket error"""
        sid = self._get_current_sid()
        
        if sid in self.connections:
            connection_info = self.connections[sid]
            connection_info.error_count += 1
            connection_info.state = ConnectionState.ERROR
            self.stats['total_errors'] += 1
            
            log_error(f"WebSocket error: {sid} - {data}")
    
    def _handle_ping(self):
        """Handle ping message"""
        sid = self._get_current_sid()
        
        if sid in self.connections:
            connection_info = self.connections[sid]
            connection_info.last_activity = datetime.utcnow()
            connection_info.message_count += 1
            self.stats['total_messages'] += 1
            
            # Send pong response
            emit('pong', {'timestamp': time.time()})
    
    def _health_monitor_loop(self):
        """Health monitoring loop with configurable intervals"""
        while self.monitoring:
            try:
                self._check_connection_health()
                # Use configurable health check interval instead of hardcoded sleep
                import threading
                event = threading.Event()
                event.wait(timeout=self.health_check_interval)
                if not self.monitoring:
                    break
            except Exception as e:
                log_error(f"Health monitor error: {e}")
                # Shorter sleep on error, but still configurable
                import threading
                event = threading.Event()
                event.wait(timeout=5)
    
    def _pool_cleanup_loop(self):
        """Connection pool cleanup loop with configurable intervals"""
        cleanup_interval = 60  # seconds
        error_interval = 30   # seconds
        
        while self.monitoring:
            try:
                self.connection_pool.cleanup_idle_connections()
                # Clean up every minute with event-based waiting
                import threading
                event = threading.Event()
                event.wait(timeout=cleanup_interval)
                if not self.monitoring:
                    break
            except Exception as e:
                log_error(f"Pool cleanup error: {e}")
                # Wait shorter time on error
                import threading
                event = threading.Event()
                event.wait(timeout=error_interval)
    
    def _check_connection_health(self):
        """Check health of all connections"""
        current_time = datetime.utcnow()
        disconnected_sids = []
        
        for sid, connection_info in self.connections.items():
            # Check for timeout
            if (current_time - connection_info.last_activity).total_seconds() > self.connection_timeout:
                disconnected_sids.append(sid)
                connection_info.state = ConnectionState.DISCONNECTED
                log_warning(f"Connection timeout: {sid}")
            
            # Check for too many errors
            elif connection_info.error_count > 10:
                disconnected_sids.append(sid)
                connection_info.state = ConnectionState.ERROR
                log_warning(f"Connection error limit exceeded: {sid}")
        
        # Disconnect unhealthy connections
        for sid in disconnected_sids:
            self._force_disconnect(sid)
    
    def _force_disconnect(self, sid: str):
        """Force disconnect a connection"""
        if sid in self.connections:
            connection_info = self.connections.pop(sid)
            self.stats['active_connections'] -= 1
            
            # Release connection back to pool
            self.connection_pool.release_connection(sid, keep_alive=False)
            
            try:
                disconnect(sid)
            except Exception as e:
                log_error(f"Error disconnecting {sid}: {e}")
    
    def send_message(self, sid: str, event: str, data: Any):
        """Send message to specific connection"""
        if sid in self.connections:
            connection_info = self.connections[sid]
            connection_info.last_activity = datetime.utcnow()
            connection_info.message_count += 1
            self.stats['total_messages'] += 1
            
            try:
                emit(event, data, room=sid)
                return True
            except Exception as e:
                log_error(f"Error sending message to {sid}: {e}")
                connection_info.error_count += 1
                return False
        return False
    
    def broadcast_message(self, event: str, data: Any, exclude_sid: Optional[str] = None):
        """Broadcast message to all connections"""
        success_count = 0
        total_count = len(self.connections)
        
        for sid in list(self.connections.keys()):
            if sid != exclude_sid:
                if self.send_message(sid, event, data):
                    success_count += 1
        
        log_info(f"Broadcast sent: {success_count}/{total_count} connections")
        return success_count
    
    def get_connection_info(self, sid: str) -> Optional[ConnectionInfo]:
        """Get connection information"""
        return self.connections.get(sid)
    
    def get_all_connections(self) -> Dict[str, ConnectionInfo]:
        """Get all active connections"""
        return self.connections.copy()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get WebSocket manager statistics"""
        pool_stats = self.connection_pool.get_stats()
        
        return {
            **self.stats,
            'connection_pool': pool_stats,
            'monitoring': self.monitoring
        }
    
    def shutdown(self):
        """Shutdown WebSocket manager"""
        self.monitoring = False
        
        # Disconnect all connections
        for sid in list(self.connections.keys()):
            self._force_disconnect(sid)
        
        log_info("WebSocket manager shutdown complete")


# Global WebSocket manager instance
_websocket_manager: Optional[WebSocketManager] = None


def get_websocket_manager() -> WebSocketManager:
    """Get global WebSocket manager instance"""
    global _websocket_manager
    if _websocket_manager is None:
        raise RuntimeError("WebSocket manager not initialized")
    return _websocket_manager


def init_websocket_manager(socketio: SocketIO) -> WebSocketManager:
    """Initialize global WebSocket manager"""
    global _websocket_manager
    if _websocket_manager is None:
        _websocket_manager = WebSocketManager(socketio)
    return _websocket_manager
