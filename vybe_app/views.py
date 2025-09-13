from flask import Blueprint, render_template, redirect, url_for, send_from_directory, current_app, abort, g, jsonify, request
import time
from datetime import datetime
from flask_login import login_required
from pathlib import Path
from .config import Config
from .auth import test_mode_login_required
import os
import logging

logger = logging.getLogger(__name__)

# Mock User class for test mode
class MockUser:
    """Mock user object for test mode to prevent template errors"""
    def __init__(self):
        self.id = 1
        self.username = "test_user"
        self.email = "test@example.com"
        self.is_active = True
        self.is_authenticated = True
        self.is_anonymous = False
    
    def get_id(self):
        return str(self.id)

views_bp = Blueprint('views', __name__)

@views_bp.route('/health')
def health_check():
    """Health check endpoint for desktop app with enhanced diagnostics"""
    try:
        startup_time = current_app.config.get('startup_time', 'unknown')
        
        # Basic health indicators
        health_data = {
            'status': 'healthy',
            'server': 'running',
            'timestamp': startup_time
        }
        
        # Add optional enhanced diagnostics in test mode
        if Config.VYBE_TEST_MODE:
            try:
                health_data.update({
                    'test_mode': True,
                    'database_accessible': True,  # We'll test this below
                    'templates_available': True   # We'll test this below
                })
                
                # Test database connectivity
                try:
                    from .models import db, User
                    # Simple test - count users table (which should always exist)
                    User.query.count()
                except Exception as db_error:
                    health_data['database_accessible'] = False
                    health_data['database_error'] = str(db_error)
                
                # Test template availability
                try:
                    template_folder = current_app.template_folder
                    if not template_folder or not Path(template_folder).exists():
                        health_data['templates_available'] = False
                except Exception as template_error:
                    health_data['templates_available'] = False
                    health_data['template_error'] = str(template_error)
                    
            except Exception as diag_error:
                health_data['diagnostics_error'] = str(diag_error)
        
        return health_data, 200
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            'status': 'error',
            'server': 'running',
            'error': str(e),
            'timestamp': time.time()
        }, 500



@views_bp.route('/')
@test_mode_login_required
def index():
    """Smart landing: always prefer chat to avoid splash stalls."""
    try:
        from .config import Config
        # Always go to chat to avoid splash screen hanging issues
        return redirect(url_for('views.chat'))
    except Exception as e:
        # If chat fails, try to render index directly instead of redirecting
        logger.warning(f"Chat redirect failed: {e}, rendering index directly", extra={
            'error_type': type(e).__name__,
            'error_details': str(e),
            'endpoint': 'index',
            'action': 'chat_redirect'
        })
        try:
            return render_template('index.html')
        except Exception as render_error:
            logger.error(f"Failed to render index: {render_error}", extra={
                'error_type': type(render_error).__name__,
                'error_details': str(render_error),
                'endpoint': 'index',
                'action': 'render_fallback',
                'original_error': str(e)
            })
            # Ultimate fallback - simple error page
            return f"""
            <html>
            <head><title>Vybe - Error</title></head>
            <body>
                <h1>Vybe AI Assistant</h1>
                <p>Application is starting up. Please wait a moment and refresh the page.</p>
                <p>If this persists, check the server logs for errors.</p>
                <script>setTimeout(() => window.location.reload(), 5000);</script>
            </body>
            </html>
            """, 503

@views_bp.route('/chat')
@test_mode_login_required
def chat():
    return render_template('index.html')  # Main chat content

# Health check moved to API blueprint to avoid conflicts

@views_bp.route('/splash')
@test_mode_login_required
def splash():
    # Always redirect to chat immediately - no splash screen
    return redirect(url_for('views.chat'))

@views_bp.route('/search')
@test_mode_login_required  
def search():
    return render_template('web_search_standalone.html')

@views_bp.route('/smart_home')
@test_mode_login_required
def smart_home():
    # Check if home assistant integration exists
    try:
        return render_template('home_assistant/dashboard.html')
    except Exception as e:
        logger.debug(f"Home Assistant template not available: {e}")
        # Fallback to settings if HA not configured
        return render_template('settings.html')

@views_bp.route('/settings')
@test_mode_login_required
def settings():
    return render_template('settings.html')

@views_bp.route('/orchestrator')
@test_mode_login_required
def orchestrator_settings():
    return render_template('orchestrator_settings.html')

@views_bp.route('/system-health')
@test_mode_login_required
def system_health():
    return render_template('system_health.html')

@views_bp.route('/api/performance/stats')
@test_mode_login_required
def performance_stats():
    """API endpoint for database performance statistics"""
    try:
        from .models import get_query_performance_stats, AppSetting, query_monitor
        
        # Get comprehensive performance stats
        db_stats = get_query_performance_stats()
        cache_stats = AppSetting.get_cache_stats()
        
        response_data = {
            'database': db_stats,
            'cache': cache_stats,
            'query_monitor': query_monitor.get_stats(),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error getting performance stats: {str(e)}")
        return jsonify({'error': 'Failed to retrieve performance statistics'}), 500

@views_bp.route('/api/performance/cache/reset', methods=['POST'])
@test_mode_login_required  
def reset_cache_stats():
    """API endpoint to reset cache statistics"""
    try:
        from .models import AppSetting
        
        AppSetting.reset_cache_stats()
        
        return jsonify({
            'message': 'Cache statistics reset successfully',
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error resetting cache stats: {str(e)}")
        return jsonify({'error': 'Failed to reset cache statistics'}), 500

@views_bp.route('/api/performance/migration/status')
@test_mode_login_required
def migration_status():
    """API endpoint for database migration status"""
    try:
        from .utils.migrate_db import DatabaseMigrator
        
        migrator = DatabaseMigrator()
        status = migrator.get_migration_status()
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Error getting migration status: {str(e)}")
        return jsonify({'error': 'Failed to retrieve migration status'}), 500

@views_bp.route('/api/analytics/user/<int:user_id>/sessions')
@test_mode_login_required
def user_session_analytics(user_id):
    """API endpoint for user session analytics"""
    try:
        from .models import UserActivity
        
        days = request.args.get('days', 30, type=int)
        stats = UserActivity.get_user_session_stats(user_id, days=days)
        
        return jsonify({
            'user_id': user_id,
            'period_days': days,
            'session_stats': stats,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting user session analytics: {str(e)}")
        return jsonify({'error': 'Failed to retrieve session analytics'}), 500

@views_bp.route('/api/analytics/features/usage')
@test_mode_login_required
def feature_usage_analytics():
    """API endpoint for feature usage analytics"""
    try:
        from .models import UserActivity
        
        user_id = request.args.get('user_id', type=int)
        days = request.args.get('days', 30, type=int)
        
        stats = UserActivity.get_feature_usage_analytics(user_id=user_id, days=days)
        
        return jsonify({
            'user_id': user_id,
            'period_days': days,
            'feature_usage': stats,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting feature usage analytics: {str(e)}")
        return jsonify({'error': 'Failed to retrieve feature usage analytics'}), 500

@views_bp.route('/api/analytics/user/<int:user_id>/behavior')
@test_mode_login_required
def user_behavior_patterns(user_id):
    """API endpoint for user behavior pattern analysis"""
    try:
        from .models import UserActivity
        
        days = request.args.get('days', 30, type=int)
        patterns = UserActivity.get_user_behavior_patterns(user_id, days=days)
        
        return jsonify({
            'user_id': user_id,
            'period_days': days,
            'behavior_patterns': patterns,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting user behavior patterns: {str(e)}")
        return jsonify({'error': 'Failed to retrieve behavior patterns'}), 500

@views_bp.route('/models_manager')
@views_bp.route('/models')  # Add alias for backward compatibility
@test_mode_login_required  
def models_manager():
    return render_template('models_manager.html')

@views_bp.route('/rag_manager')
@test_mode_login_required
def rag_manager():
    return render_template('rag_manager.html')

@views_bp.route('/web_search_page')
@test_mode_login_required
def web_search_page():
    return render_template('web_search_standalone.html')

@views_bp.route('/web_search_results')
@test_mode_login_required
def web_search_results():
    return render_template('web_search_results.html')

@views_bp.route('/prompt_maker')
@test_mode_login_required
def prompt_maker():
    return render_template('prompt_maker.html')

@views_bp.route('/rpg')
@test_mode_login_required
def rpg():
    return render_template('rpg.html')

@views_bp.route('/devtools')
@test_mode_login_required
def devtools():
    return render_template('devtools.html')

@views_bp.route('/image_studio')
@test_mode_login_required
def image_studio():
    return render_template('image_studio.html')

@views_bp.route('/audio_lab')
@test_mode_login_required
def audio_lab():
    return render_template('audio_lab.html')

@views_bp.route('/video_portal')
@test_mode_login_required
def video_portal():
    return render_template('video_portal.html')

@views_bp.route('/agents')
@test_mode_login_required
def agents():
    return render_template('agents.html')

@views_bp.route('/collaboration')
@test_mode_login_required
def collaboration():
    return render_template('collaboration.html')

@views_bp.route('/workspace/<path:filename>')
@test_mode_login_required
def serve_workspace_file(filename):
    """Serve files from the workspace directory with security checks"""
    try:
        # Security check - prevent directory traversal
        if '..' in filename or filename.startswith('/') or filename.startswith('\\'):
            logger.warning(f"Directory traversal attempt blocked: {filename}")
            abort(403)
        
        workspace_dir = Path(current_app.root_path).parent / "workspace"
        
        # Ensure the workspace directory exists
        if not workspace_dir.exists():
            logger.warning("Workspace directory does not exist")
            abort(404)
        
        # Resolve the requested file path
        requested_file = workspace_dir / filename
        
        # Security check - ensure the resolved path is within workspace directory
        try:
            requested_file.resolve().relative_to(workspace_dir.resolve())
        except ValueError:
            logger.warning(f"Path traversal attempt blocked: {filename}")
            abort(403)
        
        # Check if file exists
        if not requested_file.exists():
            abort(404)
        
        return send_from_directory(workspace_dir, filename)
    except Exception as e:
        logger.error(f"Error serving workspace file {filename}: {e}")
        abort(500)

@views_bp.route('/test_render/')
def test_render_index():
    """
    Developer test mode index - shows available templates.
    ONLY active when VYBE_TEST_MODE is enabled.
    """
    if not Config.VYBE_TEST_MODE:
        abort(404)  # Hide this route in production
    
    try:
        available_templates = []
        template_folder = current_app.template_folder
        if template_folder:
            template_dir = Path(template_folder)
            if template_dir.exists():
                available_templates = sorted([f.name for f in template_dir.glob('*.html')])
        
        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <title>Developer Test Mode - Template Browser</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 2rem; }}
                h1 {{ color: #2563eb; }}
                ul {{ list-style: none; padding: 0; }}
                li {{ margin: 0.5rem 0; }}
                a {{ color: #2563eb; text-decoration: none; padding: 0.5rem; display: block; border: 1px solid #e5e7eb; border-radius: 0.375rem; }}
                a:hover {{ background-color: #f3f4f6; }}
                .warning {{ background-color: #fef3c7; border: 1px solid #f59e0b; padding: 1rem; border-radius: 0.375rem; margin: 1rem 0; }}
            </style>
        </head>
        <body>
            <h1>🔧 Developer Test Mode</h1>
            <div class="warning">
                <strong>⚠️ Test Mode Active:</strong> Authentication is bypassed. This should only be enabled in development.
            </div>
            <h2>Available Templates:</h2>
            <ul>
                {''.join(f'<li><a href="/test_render/{template}">{template}</a></li>' for template in available_templates)}
            </ul>
            <p><strong>Usage:</strong> Click any template above to render it with mock data, bypassing authentication.</p>
        </body>
        </html>
        """
    except Exception as e:
        return f"<h1>Error listing templates:</h1><p>{str(e)}</p>", 500

@views_bp.route('/test_render/<path:template_name>')
def test_render(template_name):
    """
    Developer test mode route - allows direct access to templates without authentication.
    ONLY active when VYBE_TEST_MODE is enabled.
    Provides mock data to prevent template rendering errors.
    """
    if not Config.VYBE_TEST_MODE:
        abort(404)  # Hide this route in production
    
    # Ensure template_name ends with .html
    if not template_name.endswith('.html'):
        template_name += '.html'
    
    # Security check - prevent directory traversal
    if '..' in template_name or template_name.count('/') > 0:
        abort(400)
    
    try:
        # Create mock context data that templates might expect
        mock_context = {
            'current_user': MockUser(),
            'config': Config,
            'request': None,  # Some templates might check for request
            'session': {},    # Mock session data
            'g': g,          # Flask's application context global
        }
        
        return render_template(template_name, **mock_context)
    except Exception as e:
        # Provide detailed error information in test mode
        error_details = {
            'template': template_name,
            'error': str(e),
            'error_type': type(e).__name__,
            'available_templates': []
        }
        
        # Try to list available templates for debugging
        try:
            template_folder = current_app.template_folder
            if template_folder:
                template_dir = Path(template_folder)
                if template_dir.exists():
                    error_details['available_templates'] = [
                        f.name for f in template_dir.glob('*.html')
                    ]
        except Exception as e:
            logger.warning(f"Error listing available templates: {e}")
            pass
        
        return f"""
        <h1>Template Rendering Error (Test Mode)</h1>
        <h2>Details:</h2>
        <ul>
            <li><strong>Template:</strong> {error_details['template']}</li>
            <li><strong>Error Type:</strong> {error_details['error_type']}</li>
            <li><strong>Error Message:</strong> {error_details['error']}</li>
        </ul>
        <h3>Available Templates:</h3>
        <ul>
            {''.join(f'<li><a href="/test_render/{t}">{t}</a></li>' for t in error_details['available_templates'])}
        </ul>
        <p><strong>Note:</strong> This detailed error is only shown in VYBE_TEST_MODE.</p>
        """, 500


@views_bp.route('/setup')
@test_mode_login_required
def setup():
    """First-Time Setup Checklist page"""
    return render_template('setup.html')

@views_bp.route('/websocket-test')
@test_mode_login_required
def websocket_test():
    """WebSocket testing page"""
    return render_template('websocket_test.html')


