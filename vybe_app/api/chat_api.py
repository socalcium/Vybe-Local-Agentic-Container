"""
Chat API module - handles chat-related endpoints using WebSockets.
Refactored to use modular structure for better maintainability.
"""

# Import from the new modular structure
from .chat import chat_bp, register_chat_socketio_handlers, DEFAULT_SYSTEM_PROMPT

# Re-export for backward compatibility
__all__ = ['chat_bp', 'register_chat_socketio_handlers', 'DEFAULT_SYSTEM_PROMPT']
