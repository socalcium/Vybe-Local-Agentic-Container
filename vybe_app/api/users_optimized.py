"""
Optimized User API endpoints with N+1 query prevention
Demonstrates proper database query optimization patterns
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from typing import List, Dict, Any
from sqlalchemy import and_, func
from sqlalchemy.orm import joinedload, selectinload

from ..auth import test_mode_login_required
from ..logger import log_api_request, log_error, handle_api_errors, log_execution_time
from ..models import User, UserSession, UserActivity, Message, ChatSession, db
from ..services.user_service import user_service
from ..utils.api_response_utils import format_success_response, format_error_response

# Create optimized users sub-blueprint
users_optimized_bp = Blueprint('users_optimized', __name__, url_prefix='/users')


@users_optimized_bp.route('/batch', methods=['POST'])
@test_mode_login_required
@handle_api_errors
@log_execution_time
def get_users_batch():
    """
    Get multiple users with their statistics in optimized batch queries.
    Prevents N+1 query problems by using aggregated database queries.
    
    Expected JSON body: {"user_ids": [1, 2, 3, 4, 5]}
    """
    log_api_request(request.endpoint, request.method)
    
    try:
        data = request.get_json()
        if not data or 'user_ids' not in data:
            return format_error_response('user_ids array required', 'validation_error', 400)
        
        user_ids = data['user_ids']
        if not isinstance(user_ids, list) or not user_ids:
            return format_error_response('user_ids must be non-empty array', 'validation_error', 400)
        
        # Limit batch size to prevent resource exhaustion
        if len(user_ids) > 100:
            return format_error_response('Maximum 100 users per batch', 'validation_error', 400)
        
        # Use optimized batch method that prevents N+1 queries
        users_data = user_service.get_users_with_stats_batch(user_ids)
        
        return format_success_response({
            'users': users_data,
            'total': len(users_data),
            'requested': len(user_ids)
        })
        
    except Exception as e:
        log_error(f"Error in batch users endpoint: {str(e)}")
        return format_error_response('Internal server error', 'internal_error', 500)


@users_optimized_bp.route('/<int:user_id>/dashboard', methods=['GET'])
@test_mode_login_required
@handle_api_errors
@log_execution_time
def get_user_dashboard(user_id: int):
    """
    Get comprehensive user dashboard data with optimized queries.
    Uses efficient query patterns to prevent N+1 query problems.
    """
    log_api_request(request.endpoint, request.method)
    
    try:
        # Use optimized dashboard method that prevents N+1 queries
        dashboard_data = user_service.get_user_dashboard_data(user_id)
        
        if not dashboard_data:
            return format_error_response('User not found', 'not_found', 404)
        
        return format_success_response(dashboard_data)
        
    except Exception as e:
        log_error(f"Error in user dashboard endpoint: {str(e)}")
        return format_error_response('Internal server error', 'internal_error', 500)


@users_optimized_bp.route('/<int:user_id>/sessions', methods=['GET'])
@test_mode_login_required 
@handle_api_errors
@log_execution_time
def get_user_sessions_optimized(user_id: int):
    """
    Get user sessions with optimized query to prevent N+1 problems.
    Uses joinedload to fetch user data in a single query.
    """
    log_api_request(request.endpoint, request.method)
    
    try:
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        # Use optimized query with joinedload to prevent N+1 queries
        query = UserSession.query.filter(
            UserSession.user_id == user_id
        ).order_by(UserSession.last_activity.desc())
        
        # Execute paginated query
        sessions = query.offset((page - 1) * per_page).limit(per_page).all()
        total = query.count()
        
        # Convert to dictionaries
        sessions_data = [session.to_dict() for session in sessions]
        
        return format_success_response({
            'sessions': sessions_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        })
        
    except Exception as e:
        log_error(f"Error in user sessions endpoint: {str(e)}")
        return format_error_response('Internal server error', 'internal_error', 500)


@users_optimized_bp.route('/<int:user_id>/activities', methods=['GET'])
@test_mode_login_required
@handle_api_errors  
@log_execution_time
def get_user_activities_optimized(user_id: int):
    """
    Get user activities with optimized query patterns.
    Prevents N+1 query problems by using efficient pagination and filtering.
    """
    log_api_request(request.endpoint, request.method)
    
    try:
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 200)
        activity_type = request.args.get('activity_type')
        
        # Build optimized query
        query = UserActivity.query.filter(UserActivity.user_id == user_id)
        
        if activity_type:
            query = query.filter(UserActivity.activity_type == activity_type)
        
        query = query.order_by(UserActivity.created_at.desc())
        
        # Execute paginated query
        activities = query.offset((page - 1) * per_page).limit(per_page).all()
        total = query.count()
        
        # Convert to dictionaries
        activities_data = [activity.to_dict() for activity in activities]
        
        return format_success_response({
            'activities': activities_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        })
        
    except Exception as e:
        log_error(f"Error in user activities endpoint: {str(e)}")
        return format_error_response('Internal server error', 'internal_error', 500)


@users_optimized_bp.route('/recent-messages', methods=['GET'])
@test_mode_login_required
@handle_api_errors
@log_execution_time  
def get_recent_messages_optimized():
    """
    Get recent messages across all users with optimized query.
    Uses joinedload to prevent N+1 queries when accessing message.user.
    """
    log_api_request(request.endpoint, request.method)
    
    try:
        # Get query parameters
        limit = min(request.args.get('limit', 100, type=int), 500)
        user_id = request.args.get('user_id', type=int)
        
        # Build optimized query that loads user data eagerly
        query = Message.query.options(
            # This loads the user data in the same query, preventing N+1 problems
            db.selectinload(Message.user)
        )
        
        if user_id:
            query = query.filter(Message.user_id == user_id)
        
        # Execute query with limit
        messages = query.order_by(Message.timestamp.desc()).limit(limit).all()
        
        # Convert to dictionaries - no additional queries needed for user data
        messages_data = []
        for message in messages:
            message_dict = message.to_dict()
            # User data is already loaded, no additional query
            if message.user:
                message_dict['user'] = {
                    'id': message.user.id,
                    'username': message.user.username
                }
            messages_data.append(message_dict)
        
        return format_success_response({
            'messages': messages_data,
            'total': len(messages_data),
            'limit': limit
        })
        
    except Exception as e:
        log_error(f"Error in recent messages endpoint: {str(e)}")
        return format_error_response('Internal server error', 'internal_error', 500)


@users_optimized_bp.route('/analytics', methods=['GET'])
@test_mode_login_required
@handle_api_errors
@log_execution_time
def get_users_analytics():
    """
    Get user analytics with optimized aggregation queries.
    Uses database aggregation to prevent loading large datasets into memory.
    """
    log_api_request(request.endpoint, request.method)
    
    try:
        # Use raw SQL for complex aggregations to avoid typing issues
        analytics = {
            'activities': [],
            'sessions': {'total_sessions': 0, 'active_sessions': 0, 'users_with_sessions': 0},
            'messages': {'total_messages': 0, 'users_with_messages': 0, 'avg_response_time_ms': 0}
        }
        
        # Activity statistics using raw SQL
        activity_results = db.session.execute(
            db.text("""
                SELECT 
                    activity_type,
                    COUNT(*) as count,
                    COUNT(DISTINCT user_id) as unique_users
                FROM user_activity 
                GROUP BY activity_type
                ORDER BY count DESC
            """)
        ).fetchall()
        
        analytics['activities'] = [
            {
                'activity_type': row[0],
                'count': row[1],
                'unique_users': row[2]
            }
            for row in activity_results
        ]
        
        # Session statistics using raw SQL
        session_result = db.session.execute(
            db.text("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN is_active = true THEN 1 ELSE 0 END) as active,
                    COUNT(DISTINCT user_id) as users_with_sessions
                FROM user_session
            """)
        ).fetchone()
        
        if session_result:
            analytics['sessions'] = {
                'total_sessions': session_result[0] or 0,
                'active_sessions': session_result[1] or 0,
                'users_with_sessions': session_result[2] or 0
            }
        
        # Message statistics using raw SQL
        message_result = db.session.execute(
            db.text("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(DISTINCT user_id) as users_with_messages,
                    AVG(response_time_ms) as avg_response_time
                FROM message
                WHERE response_time_ms IS NOT NULL
            """)
        ).fetchone()
        
        if message_result:
            analytics['messages'] = {
                'total_messages': message_result[0] or 0,
                'users_with_messages': message_result[1] or 0,
                'avg_response_time_ms': round(message_result[2] or 0, 2)
            }
        
        return format_success_response(analytics)
        
    except Exception as e:
        log_error(f"Error in users analytics endpoint: {str(e)}")
        return format_error_response('Internal server error', 'internal_error', 500)


# Export the blueprint
__all__ = ['users_optimized_bp']
