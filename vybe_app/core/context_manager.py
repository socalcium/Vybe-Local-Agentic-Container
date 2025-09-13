"""
Context Window Management System for Vybe AI

Handles intelligent context window management, token counting, and automatic 
context reset with summary/storage when approaching limits.
"""

import json
import logging
import threading
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import hashlib
from pathlib import Path

logger = logging.getLogger(__name__)


class ContextManager:
    """Manages context windows intelligently across different models"""
    
    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or Path.home() / ".local" / "share" / "vybe-ai-assistant" / "context_storage"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Context limits by model type (16K+ minimum for robust AI assistant)
        self.model_limits = {
            'phi3': 120000,        # Near full 128K - excellent for complex tasks
            'llama3': 30000,       # Conservative for 32K models  
            'llama3.1': 120000,    # Near full 128K
            'llama3.2': 120000,    # Near full 128K
            'mixtral': 30000,      # Conservative for 32K models
            'dolphin': 30000,      # Conservative for 32K models - PREFERRED UNCENSORED
            'openhermes': 30000,   # Conservative for 32K models - PREFERRED UNCENSORED
            'hermes': 30000,       # Conservative for 32K models
            'wizard': 30000,       # Upgraded to 32K models only
            'mistral': 30000,      # Conservative for 32K models
            'qwen': 30000,         # Conservative for 32K models
            'default': 30000       # 16K+ minimum for robust AI assistant functionality
        }
        
        # Context usage thresholds
        self.warning_threshold = 0.75  # Warn at 75%
        self.reset_threshold = 0.85    # Auto-reset at 85%
        
        logger.info("ContextManager initialized with intelligent context window management")
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation: 1 token ≈ 4 characters)"""
        return len(text) // 4
    
    def get_model_limit(self, model_name: str) -> int:
        """Get context window limit for a specific model"""
        model_key = model_name.lower().split(':')[0]  # Remove version tags
        
        for key, limit in self.model_limits.items():
            if key in model_key:
                return limit
        
        return self.model_limits['default']
    
    def analyze_context_usage(self, conversation_history: List[Dict], model_name: str) -> Dict[str, Any]:
        """Analyze current context usage and provide recommendations"""
        
        # Calculate total tokens in conversation
        total_text = ""
        for msg in conversation_history:
            if isinstance(msg, dict):
                total_text += str(msg.get('content', '')) + " "
            else:
                total_text += str(msg) + " "
        
        current_tokens = self.estimate_tokens(total_text)
        max_tokens = self.get_model_limit(model_name)
        usage_ratio = current_tokens / max_tokens
        
        # Determine status and recommendations
        status = "optimal"
        recommendations = []
        
        if usage_ratio >= self.reset_threshold:
            status = "critical"
            recommendations.append("Immediate context reset required")
            recommendations.append("Creating conversation summary")
        elif usage_ratio >= self.warning_threshold:
            status = "warning"
            recommendations.append("Consider summarizing older messages")
            recommendations.append("Context approaching limit")
        elif usage_ratio >= 0.5:
            status = "moderate"
            recommendations.append("Context usage is moderate")
        
        return {
            'current_tokens': current_tokens,
            'max_tokens': max_tokens,
            'usage_ratio': usage_ratio,
            'usage_percentage': round(usage_ratio * 100, 1),
            'status': status,
            'recommendations': recommendations,
            'tokens_remaining': max_tokens - current_tokens,
            'estimated_messages_remaining': (max_tokens - current_tokens) // 200  # Rough estimate
        }
    
    def create_conversation_summary(self, conversation_history: List[Dict]) -> str:
        """Create an intelligent summary of conversation history"""
        
        if not conversation_history:
            return "Empty conversation"
        
        # Extract key information
        topics = set()
        user_queries = []
        assistant_responses = []
        important_info = []
        
        for msg in conversation_history:
            if isinstance(msg, dict):
                role = msg.get('role', '')
                content = msg.get('content', '')
                
                if role == 'user':
                    user_queries.append(content)
                    # Extract potential topics (simple keyword extraction)
                    words = content.lower().split()
                    for word in words:
                        if len(word) > 4 and word.isalpha():
                            topics.add(word)
                
                elif role == 'assistant':
                    assistant_responses.append(content)
                    
                    # Mark important information
                    if any(keyword in content.lower() for keyword in ['important', 'note', 'remember', 'key']):
                        important_info.append(content[:200] + "..." if len(content) > 200 else content)
        
        # Create structured summary
        summary_parts = []
        
        if topics:
            summary_parts.append(f"Topics discussed: {', '.join(list(topics)[:10])}")
        
        if user_queries:
            recent_queries = user_queries[-3:] if len(user_queries) > 3 else user_queries
            summary_parts.append(f"Recent user queries: {'; '.join(recent_queries)}")
        
        if important_info:
            summary_parts.append(f"Important information: {'; '.join(important_info)}")
        
        summary_parts.append(f"Conversation length: {len(conversation_history)} messages")
        summary_parts.append(f"Summary created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return " | ".join(summary_parts)
    
    def store_conversation_context(self, conversation_id: str, summary: str, full_context: List[Dict]) -> str:
        """Store conversation context for potential retrieval"""
        
        # Create storage file path
        context_hash = hashlib.md5(f"{conversation_id}_{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        storage_file = self.storage_dir / f"context_{context_hash}.json"
        
        # Store context data
        context_data = {
            'conversation_id': conversation_id,
            'stored_at': datetime.now().isoformat(),
            'summary': summary,
            'message_count': len(full_context),
            'estimated_tokens': self.estimate_tokens(str(full_context)),
            'full_context': full_context[-50:] if len(full_context) > 50 else full_context  # Keep last 50 messages
        }
        
        try:
            with open(storage_file, 'w', encoding='utf-8') as f:
                json.dump(context_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Stored conversation context: {storage_file.name}")
            return context_hash
            
        except Exception as e:
            logger.error(f"Failed to store conversation context: {e}")
            return ""
    
    def retrieve_context_summary(self, context_hash: str) -> Optional[str]:
        """Retrieve a stored conversation summary"""
        
        storage_file = self.storage_dir / f"context_{context_hash}.json"
        
        try:
            if storage_file.exists():
                with open(storage_file, 'r', encoding='utf-8') as f:
                    context_data = json.load(f)
                return context_data.get('summary', '')
        except Exception as e:
            logger.error(f"Failed to retrieve context summary: {e}")
        
        return None
    
    def smart_context_reset(self, conversation_history: List[Dict], model_name: str, conversation_id: str = "default") -> Tuple[List[Dict], str]:
        """Perform intelligent context reset with summary preservation"""
        
        if not conversation_history:
            return [], ""
        
        # Create summary of full conversation
        full_summary = self.create_conversation_summary(conversation_history)
        
        # Store full context for potential retrieval
        context_hash = self.store_conversation_context(conversation_id, full_summary, conversation_history)
        
        # Keep only the most recent messages + summary
        summary_message = {
            'role': 'system',
            'content': f"[Previous conversation summary: {full_summary}]",
            'timestamp': datetime.now().isoformat(),
            'type': 'context_summary',
            'context_hash': context_hash
        }
        
        # Keep last few messages for continuity
        recent_messages = conversation_history[-5:] if len(conversation_history) > 5 else conversation_history
        new_context = [summary_message] + recent_messages
        
        logger.info(f"Smart context reset completed - Reduced from {len(conversation_history)} to {len(new_context)} messages")
        
        return new_context, full_summary
    
    def get_context_status_display(self, analysis: Dict[str, Any]) -> str:
        """Get a user-friendly context status display"""
        
        status = analysis['status']
        percentage = analysis['usage_percentage']
        remaining = analysis['tokens_remaining']
        
        status_icons = {
            'optimal': '🟢',
            'moderate': '🟡', 
            'warning': '🟠',
            'critical': '🔴'
        }
        
        icon = status_icons.get(status, '⚪')
        
        return f"{icon} Context: {percentage}% used ({remaining:,} tokens remaining)"
    
    def cleanup_old_contexts(self, days_old: int = 30):
        """Clean up context storage files older than specified days"""
        
        try:
            cutoff_time = datetime.now().timestamp() - (days_old * 24 * 60 * 60)
            cleaned_count = 0
            
            for context_file in self.storage_dir.glob("context_*.json"):
                if context_file.stat().st_mtime < cutoff_time:
                    context_file.unlink()
                    cleaned_count += 1
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} old context files")
                
        except Exception as e:
            logger.error(f"Error during context cleanup: {e}")


# Thread-safe singleton context manager instance
_context_manager: Optional[ContextManager] = None
_context_manager_lock = threading.Lock()

def get_context_manager() -> ContextManager:
    """Get thread-safe singleton context manager instance"""
    global _context_manager
    if _context_manager is None:
        with _context_manager_lock:
            # Double-check locking pattern
            if _context_manager is None:
                _context_manager = ContextManager()
    return _context_manager
