"""
Chat API Package - Modular Real-time Chat and AI Conversation System.

This package provides a comprehensive, modular chat system for the Vybe AI Desktop
Application, supporting both REST API endpoints and real-time WebSocket communication.
It handles AI-powered conversations, message processing, session management, and
integration with multiple AI backends.

The chat system is designed with a modular architecture separating concerns:
- REST API endpoints for HTTP-based chat operations
- WebSocket handlers for real-time bidirectional communication
- Message processors for AI response generation and content filtering
- Session managers for conversation state and history
- Tool integration for enhanced AI capabilities

Key Features:
    - Real-time bidirectional chat via WebSocket connections
    - REST API endpoints for traditional HTTP-based interactions
    - Multi-backend AI integration (local and cloud models)
    - Advanced message processing with content filtering
    - Session-based conversation management with persistence
    - Tool calling and function execution capabilities
    - Streaming response support for real-time typing indicators
    - Message history and conversation context management
    - User authentication and authorization integration
    - Rate limiting and abuse prevention

Architecture Components:
    - rest_api: HTTP endpoints for chat operations and management
    - websocket_handlers: Real-time WebSocket event handling
    - message_processor: AI response generation and content processing
    - session_manager: Conversation state and history management
    - tool_integration: Function calling and external tool access

Supported Communication Patterns:
    - Traditional request-response via REST API
    - Real-time streaming chat via WebSocket
    - Batch message processing for bulk operations
    - Background conversation processing
    - Multi-user chat room support (future feature)

AI Integration:
    - Local model support via llama.cpp backend
    - Cloud API integration (OpenAI, Anthropic, etc.)
    - Multi-model routing and fallback mechanisms
    - Custom system prompt management
    - Tool calling and function execution
    - Response caching and optimization

Security Features:
    - Message content filtering and validation
    - User authentication and session management
    - Rate limiting per user and IP address
    - Input sanitization and XSS prevention
    - Secure WebSocket connection handling
    - Conversation privacy and isolation

Example Usage:
    # REST API
    POST /api/chat/send
    {"message": "Hello, how can you help me?"}
    
    # WebSocket
    emit('send_message', {
        'message': 'What is Python?',
        'session_id': 'chat_session_123'
    })

Package Exports:
    - chat_bp: Flask blueprint with REST API endpoints
    - register_chat_socketio_handlers: WebSocket event handler registration
    - DEFAULT_SYSTEM_PROMPT: Default AI system prompt configuration

Note:
    This package requires proper authentication setup and AI backend configuration.
    WebSocket functionality requires SocketIO initialization in the main application.
"""

from .rest_api import chat_bp
from .websocket_handlers import register_chat_socketio_handlers
from .message_processor import DEFAULT_SYSTEM_PROMPT

__all__ = ['chat_bp', 'register_chat_socketio_handlers', 'DEFAULT_SYSTEM_PROMPT']
