"""
N+1 Query Optimization Module for Vybe AI Desktop
Provides optimized database queries to prevent N+1 query problems.
"""

from typing import List, Optional, Dict, Any
from ..models import User, UserSession, UserActivity, Message, ChatSession, db


class QueryOptimizer:
    """
    Optimized database query methods to prevent N+1 query problems.
    Uses efficient query patterns to minimize database roundtrips.
    """
    
    @staticmethod
    def get_users_with_stats_optimized(user_ids: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        """
        Get users with basic statistics using optimized patterns.
        Prevents N+1 queries by using efficient database operations.
        """
        # Get users efficiently
        users_query = User.query
        if user_ids:
            users_query = users_query.filter(User.id.in_(user_ids))
        users = users_query.all()
        
        if not users:
            return []
        
        user_id_list = [user.id for user in users]
        
        # Get activity counts for all users in single query
        activity_counts = {}
        try:
            activity_results = db.session.execute(
                db.text("""
                    SELECT user_id, COUNT(*) as count 
                    FROM user_activity 
                    WHERE user_id IN :user_ids 
                    GROUP BY user_id
                """),
                {'user_ids': tuple(user_id_list)}
            ).fetchall()
            activity_counts = {row[0]: row[1] for row in activity_results}
        except Exception:
            # Fallback if raw SQL fails
            pass
        
        # Convert to result format
        return [
            {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'is_active': user.is_active,
                'activity_count': activity_counts.get(user.id, 0)
            }
            for user in users
        ]
    
    @staticmethod
    def get_recent_messages_optimized(limit: int = 100, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get recent messages with user information using optimized query patterns.
        Avoids N+1 queries by fetching related data efficiently.
        """
        # Build efficient query
        messages_query = Message.query
        
        if user_id:
            messages_query = messages_query.filter(Message.user_id == user_id)
            
        messages = messages_query.order_by(Message.timestamp.desc()).limit(limit).all()
        
        if not messages:
            return []
        
        # Get all unique user IDs from messages
        user_ids = list(set(msg.user_id for msg in messages if msg.user_id))
        
        # Get all users in single query
        users_dict = {}
        if user_ids:
            users = User.query.filter(User.id.in_(user_ids)).all()
            users_dict = {user.id: user for user in users}
        
        # Combine data without additional queries
        return [
            {
                'id': msg.id,
                'user_message': msg.user_message,
                'ai_response': msg.ai_response,
                'timestamp': msg.timestamp.isoformat() if msg.timestamp else None,
                'user_id': msg.user_id,
                'session_id': msg.session_id,
                'model_used': msg.model_used,
                'response_time_ms': msg.response_time_ms,
                'user': {
                    'username': users_dict[msg.user_id].username if msg.user_id in users_dict else None,
                    'email': users_dict[msg.user_id].email if msg.user_id in users_dict else None
                } if msg.user_id else None
            }
            for msg in messages
        ]
    
    @staticmethod
    def get_user_dashboard_optimized(user_id: int) -> Dict[str, Any]:
        """
        Get user dashboard data using optimized queries.
        Uses multiple efficient queries instead of nested loops.
        """
        # Get user info (1 query)
        user = User.query.get(user_id)
        if not user:
            return {}
        
        # Get session statistics using raw SQL for efficiency
        session_stats = {'total': 0, 'active': 0}
        try:
            result = db.session.execute(
                db.text("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN is_active = true THEN 1 ELSE 0 END) as active
                    FROM user_session 
                    WHERE user_id = :user_id
                """),
                {'user_id': user_id}
            ).fetchone()
            if result:
                session_stats = {'total': result[0] or 0, 'active': result[1] or 0}
        except Exception:
            pass
        
        # Get recent activities (1 query)
        recent_activities = UserActivity.query.filter(
            UserActivity.user_id == user_id
        ).order_by(UserActivity.created_at.desc()).limit(10).all()
        
        # Get message count efficiently
        message_count = Message.query.filter(Message.user_id == user_id).count()
        
        # Total: 4 queries instead of potentially many with N+1 problems
        return {
            'user': user.to_dict(),
            'session_stats': session_stats,
            'recent_activities': [activity.to_dict() for activity in recent_activities],
            'message_count': message_count
        }
    
    @staticmethod
    def get_analytics_optimized() -> Dict[str, Any]:
        """
        Get system analytics using optimized aggregation queries.
        Uses database aggregation to avoid loading large datasets into memory.
        """
        analytics = {
            'users': {'total': 0, 'active': 0},
            'sessions': {'total': 0, 'active': 0},
            'messages': {'total': 0},
            'activities': []
        }
        
        try:
            # User statistics
            user_count = User.query.count()
            active_user_count = User.query.filter(User.is_active == db.true()).count()
            analytics['users'] = {'total': user_count, 'active': active_user_count}
            
            # Session statistics
            session_count = UserSession.query.count()
            active_session_count = UserSession.query.filter(UserSession.is_active == db.true()).count()
            analytics['sessions'] = {'total': session_count, 'active': active_session_count}
            
            # Message statistics
            message_count = Message.query.count()
            analytics['messages'] = {'total': message_count}
            
            # Activity statistics using raw SQL for efficiency
            activity_results = db.session.execute(
                db.text("""
                    SELECT activity_type, COUNT(*) as count, COUNT(DISTINCT user_id) as unique_users
                    FROM user_activity 
                    GROUP BY activity_type
                    ORDER BY count DESC
                """)
            ).fetchall()
            
            analytics['activities'] = [
                {
                    'type': row[0],
                    'count': row[1],
                    'unique_users': row[2]
                }
                for row in activity_results
            ]
            
        except Exception as e:
            print(f"Analytics query error: {e}")
        
        return analytics


# Helper functions for N+1 prevention
def prevent_n_plus_one_in_list_operations():
    """
    Guidelines for preventing N+1 queries in list operations:
    
    1. Use .filter(Model.id.in_(id_list)) instead of loops
    2. Fetch related data in batch queries  
    3. Use database aggregation instead of Python loops
    4. Limit result sets with .limit() and pagination
    5. Use raw SQL for complex aggregations when needed
    """
    pass


def optimize_relationship_access():
    """
    Best practices for relationship access:
    
    1. Use joinedload() for one-to-one relationships
    2. Use selectinload() for one-to-many relationships
    3. Use batch queries for many-to-many relationships
    4. Avoid accessing relationships in loops
    5. Preload related data when possible
    """
    pass


# Create global instance for easy importing
query_optimizer = QueryOptimizer()
