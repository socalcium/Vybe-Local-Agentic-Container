"""
Desktop Notification System for Vybe
Integrates with Tauri desktop app and web notifications
"""

import json
import asyncio
from typing import Optional, Callable, List
from datetime import datetime

from ..logger import logger


class NotificationManager:
    """Manages desktop and web notifications"""
    
    def __init__(self):
        self.callbacks: List[Callable] = []
        self.notification_history: List[dict] = []
    
    def add_callback(self, callback: Callable):
        """Add a notification callback function"""
        self.callbacks.append(callback)
        logger.info(f"Added notification callback: {callback.__name__}")
    
    def send_notification(self, title: str, message: str, notification_type: str = "info", 
                         agent_id: Optional[str] = None, action_url: Optional[str] = None):
        """
        Send a notification via all registered callbacks
        
        Args:
            title: Notification title
            message: Notification message
            notification_type: Type (info, success, warning, error)
            agent_id: Optional agent ID for context
            action_url: Optional URL to open when clicked
        """
        notification_data = {
            'id': f"notif_{int(datetime.now().timestamp())}",
            'title': title,
            'message': message,
            'type': notification_type,
            'timestamp': datetime.now().isoformat(),
            'agent_id': agent_id,
            'action_url': action_url
        }
        
        # Store in history
        self.notification_history.append(notification_data)
        
        # Keep only last 100 notifications
        if len(self.notification_history) > 100:
            self.notification_history = self.notification_history[-100:]
        
        # Send via all callbacks
        for callback in self.callbacks:
            try:
                callback(notification_data)
            except Exception as e:
                logger.error(f"Notification callback failed: {e}")
        
        logger.info(f"Sent notification: {title} - {message}")
    
    def get_notification_history(self, limit: int = 50) -> List[dict]:
        """Get recent notification history"""
        return self.notification_history[-limit:]
    
    def clear_history(self):
        """Clear notification history"""
        self.notification_history = []


# Global notification manager
notification_manager = NotificationManager()


def get_notification_manager() -> NotificationManager:
    """Get the global notification manager instance"""
    return notification_manager


def send_desktop_notification(title: str, message: str, notification_type: str = "info",
                             agent_id: Optional[str] = None, action_url: Optional[str] = None):
    """Convenience function to send a desktop notification"""
    notification_manager.send_notification(title, message, notification_type, agent_id, action_url)


def send_agent_completion_notification(agent_id: str, objective: str, success: bool = True):
    """Send notification when an agent completes its task"""
    if success:
        title = "✅ Agent Task Completed"
        message = f"Agent has successfully completed: {objective[:50]}{'...' if len(objective) > 50 else ''}"
        notification_type = "success"
    else:
        title = "❌ Agent Task Failed"
        message = f"Agent failed to complete: {objective[:50]}{'...' if len(objective) > 50 else ''}"
        notification_type = "error"
    
    send_desktop_notification(
        title=title,
        message=message,
        notification_type=notification_type,
        agent_id=agent_id,
        action_url=f"/agents/{agent_id}"
    )


def send_rag_completion_notification(filename: str, collection_name: str):
    """Send notification when RAG ingestion completes"""
    send_desktop_notification(
        title="📚 RAG Ingestion Complete",
        message=f"Successfully processed '{filename}' into '{collection_name}' collection",
        notification_type="success",
        action_url="/rag"
    )


def send_finetuning_notification(model_name: str, status: str, agent_id: Optional[str] = None):
    """Send notification about fine-tuning progress"""
    if status == "started":
        title = "🔧 Fine-tuning Started"
        message = f"Model fine-tuning began for: {model_name}"
        notification_type = "info"
    elif status == "completed":
        title = "🎯 Fine-tuning Complete"
        message = f"Model fine-tuning completed successfully: {model_name}"
        notification_type = "success"
    elif status == "failed":
        title = "🚨 Fine-tuning Failed"
        message = f"Model fine-tuning failed for: {model_name}"
        notification_type = "error"
    else:
        title = "🔧 Fine-tuning Update"
        message = f"Fine-tuning status: {status} for {model_name}"
        notification_type = "info"
    
    send_desktop_notification(
        title=title,
        message=message,
        notification_type=notification_type,
        agent_id=agent_id,
        action_url="/finetuning"
    )


def send_connector_sync_notification(connector_name: str, items_synced: int, success: bool = True):
    """Send notification when external connector sync completes"""
    if success:
        title = "🔗 Sync Complete"
        message = f"{connector_name}: Successfully synced {items_synced} items"
        notification_type = "success"
    else:
        title = "🔗 Sync Failed"
        message = f"{connector_name}: Sync failed or partially completed"
        notification_type = "warning"
    
    send_desktop_notification(
        title=title,
        message=message,
        notification_type=notification_type,
        action_url="/connectors"
    )


# WebSocket notification handler for real-time notifications
def setup_websocket_notifications(socketio):
    """Setup WebSocket handlers for real-time notifications"""
    
    def websocket_notification_callback(notification_data):
        """Callback to send notifications via WebSocket"""
        try:
            socketio.emit('notification', notification_data)
        except Exception as e:
            logger.error(f"Failed to send WebSocket notification: {e}")
    
    # Register the WebSocket callback
    notification_manager.add_callback(websocket_notification_callback)


# Tauri notification handler for desktop app
def setup_tauri_notifications():
    """Setup Tauri desktop notification handler"""
    
    def tauri_notification_callback(notification_data):
        """Callback to send notifications via Tauri (when running in desktop app)"""
        try:
            # This would integrate with Tauri's notification API
            # The actual implementation would depend on the Tauri frontend
            logger.info(f"Tauri notification: {notification_data['title']} - {notification_data['message']}")
            
            # In a real implementation, this would call Tauri's invoke API
            # For now, we'll use a placeholder that can be extended
            pass
            
        except Exception as e:
            logger.error(f"Failed to send Tauri notification: {e}")
    
    # Register the Tauri callback
    notification_manager.add_callback(tauri_notification_callback)


# Browser notification handler for web app
def setup_browser_notifications():
    """Setup browser notification handler for web app"""
    
    def browser_notification_callback(notification_data):
        """Callback to trigger browser notifications"""
        try:
            # This would trigger browser notifications via JavaScript
            # Implementation would be handled on the frontend
            logger.info(f"Browser notification: {notification_data['title']} - {notification_data['message']}")
            
        except Exception as e:
            logger.error(f"Failed to send browser notification: {e}")
    
    # Register the browser callback
    notification_manager.add_callback(browser_notification_callback)
