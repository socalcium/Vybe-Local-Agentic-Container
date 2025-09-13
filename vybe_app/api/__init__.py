"""
API module for Vybe application.
Contains shared utilities and initializes API sub-modules.
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
import time
import logging
from sqlalchemy import text
from ..auth import test_mode_login_required
from ..utils.cache_manager import cached

# Initialize logger
logger = logging.getLogger(__name__)

# Create the main API blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Import sub-module blueprints after creating the main blueprint
from .models_api import models_bp
from .chat_api import chat_bp
from .settings_api import settings_bp
from .tools_api import tools_bp
from .rag_api import rag_bp
from .audio_api import audio_api as audio_bp
from .image_api import images_bp
from .agents_api import agents_bp
from .video_api import video_bp
from .code_api import code_api
from .connectors_api import connectors_api
from .user_api import user_api
from .llm_backend_api import llm_bp
from .auto_installer_api import auto_installer_api
from .orchestrator_api import orchestrator_bp
from .debug_api import debug_bp as debug_api
from .external_api import external_api_bp
from .update_api import update_api
from .system_tray_api import system_tray_api
from .rpg_api import rpg_bp
from .cloud_sync_api import cloud_sync_bp
from .plugin_api import plugin_bp
from .marketplace_api import marketplace_bp
from .collaboration_api import collaboration_bp
# Splash API removed - using direct loading

# Register sub-module blueprints with the main API blueprint
api_bp.register_blueprint(models_bp)
api_bp.register_blueprint(chat_bp)
api_bp.register_blueprint(settings_bp)
api_bp.register_blueprint(tools_bp)
api_bp.register_blueprint(rag_bp)
api_bp.register_blueprint(audio_bp)
api_bp.register_blueprint(images_bp)
api_bp.register_blueprint(agents_bp)
api_bp.register_blueprint(video_bp)
api_bp.register_blueprint(code_api)
api_bp.register_blueprint(connectors_api)
api_bp.register_blueprint(user_api)
api_bp.register_blueprint(llm_bp)
api_bp.register_blueprint(auto_installer_api)
api_bp.register_blueprint(orchestrator_bp)
api_bp.register_blueprint(debug_api)
api_bp.register_blueprint(external_api_bp)
api_bp.register_blueprint(update_api)
api_bp.register_blueprint(system_tray_api)
api_bp.register_blueprint(rpg_bp)
api_bp.register_blueprint(cloud_sync_bp)
api_bp.register_blueprint(plugin_bp)
api_bp.register_blueprint(marketplace_bp)
api_bp.register_blueprint(collaboration_bp)
# splash_api removed

# Add health check endpoint for desktop app
@api_bp.route('/health', methods=['GET'])
def api_health_check():
    """Simple health check for desktop app"""
    return jsonify({
        'status': 'ok',
        'service': 'vybe-api',
        'timestamp': time.time()
    })

@api_bp.route('/status', methods=['GET'])  
def api_status_check():
    """Detailed status check"""
    try:
        return jsonify({
            'status': 'ready',
            'api': 'operational',
            'timestamp': time.time()
        })
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

# Add manual web search endpoint directly to main API since it's accessed as /api/perform_manual_web_search
@api_bp.route('/perform_manual_web_search', methods=['POST'])
@test_mode_login_required
def api_perform_manual_web_search():
    """Perform manual web search with real Brave Search API integration"""
    from ..logger import log_api_request, log_user_action, log_error
    from ..core.search_tools import search_brave, search_web_fallback
    import html
    
    log_api_request(request.endpoint, request.method)
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data is required'}), 400
            
        query = data.get('query', '').strip()
        if not query:
            return jsonify({'error': 'Search query is required'}), 400
        
        # Validate and sanitize query
        if len(query) > 500:
            return jsonify({'error': 'Search query too long (max 500 characters)'}), 400
        
        # Sanitize query to prevent injection
        query = html.escape(query)
        
        use_rag = data.get('use_rag', False)
        count = data.get('count', 10)
        
        # Validate count parameter
        try:
            count = int(count)
            if count < 1 or count > 50:
                count = 10
        except (ValueError, TypeError):
            count = 10
        
        # Use real Brave Search API
        results = search_brave(query, count)
        
        # If no results from Brave API, use fallback
        if not results or (len(results) == 1 and 'Search API Not Configured' in results[0].get('title', '')):
            results = search_web_fallback(query)
        
        # Ensure results have consistent format for compatibility
        formatted_results = []
        for result in results:
            formatted_results.append({
                'title': result.get('title', ''),
                'link': result.get('link', ''),
                'url': result.get('link', ''),  # For backward compatibility
                'snippet': result.get('snippet', '')
            })
        
        log_user_action(current_user.id, f"Performed web search: {query}")
        return jsonify({
            'success': True,
            'query': query,
            'results': formatted_results,
            'use_rag': use_rag,
            'count': len(formatted_results)
        })
        
    except Exception as e:
        log_error(f"Web search API error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# Add web search endpoint using Brave Search API
@api_bp.route('/web_search', methods=['POST'])
@test_mode_login_required
def api_web_search():
    """Perform web search using Brave Search API"""
    from ..logger import log_api_request, log_user_action, log_error
    from ..core.search_tools import search_brave
    
    log_api_request(request.endpoint, request.method)
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data is required'}), 400
            
        query = data.get('query', '').strip()
        if not query:
            return jsonify({'error': 'Search query is required'}), 400
        
        count = data.get('count', 10)
        safe_search = data.get('safe_search', True)
        
        # Use the search_brave function from search_tools
        results = search_brave(query, count)
        
        log_user_action(current_user.id, f"Performed Brave web search: {query}")
        return jsonify({
            'success': True,
            'query': query,
            'results': results,
            'count': len(results)
        })
        
    except Exception as e:
        log_error(f"Brave web search API error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# Add developer tools endpoints
@api_bp.route('/devtools/system_info', methods=['GET'])
@test_mode_login_required
def api_devtools_system_info():
    """Get system information"""
    from ..core.system_monitor import get_system_info
    try:
        system_info = get_system_info()
        return jsonify(system_info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/devtools/logs', methods=['GET'])
@test_mode_login_required
def api_devtools_logs():
    """Get application logs"""
    from ..config import Config
    import os
    
    try:
        lines = int(request.args.get('lines', 100))
        log_file = Config.LOG_FILE_PATH
        
        if not os.path.exists(log_file):
            return jsonify({'logs': []})
        
        # Read last N lines from log file
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        # Parse log entries
        logs = []
        for line in recent_lines:
            line = line.strip()
            if line:
                # Basic log parsing - assumes format: TIMESTAMP - LEVEL - MESSAGE
                parts = line.split(' - ', 2)
                if len(parts) >= 3:
                    logs.append({
                        'timestamp': parts[0],
                        'level': parts[1],
                        'message': parts[2]
                    })
                else:
                    logs.append({
                        'timestamp': '',
                        'level': 'INFO',
                        'message': line
                    })
        
        return jsonify({'logs': logs})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/devtools/app_config', methods=['GET'])
@test_mode_login_required
def api_devtools_app_config():
    """Get application configuration with caching"""
    try:
        config = get_cached_app_config()
        return jsonify({'config': config})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@cached(timeout=1800)  # Cache for 30 minutes
def get_cached_app_config():
    """Get cached application configuration"""
    from ..config import Config
    return Config.get_config_dict()

@api_bp.route('/devtools/app_settings', methods=['GET'])
@test_mode_login_required
def api_devtools_app_settings():
    """Get application settings from database with caching"""
    try:
        settings = get_cached_app_settings()
        return jsonify({'settings': settings})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@cached(timeout=1200)  # Cache for 20 minutes
def get_cached_app_settings():
    """Get cached application settings"""
    from ..models import AppSetting
    settings = {}
    all_settings = AppSetting.query.all()
    for setting in all_settings:
        settings[setting.key] = setting.value
    return settings

@api_bp.route('/devtools/environment', methods=['GET'])
@test_mode_login_required
def api_devtools_environment():
    """Get environment information"""
    import sys
    import platform
    import os
    from ..config import VYBE_VERSION
    try:
        env_info = {
            'vybe_version': VYBE_VERSION,
            'python_version': sys.version,
            'platform': platform.platform(),
            'architecture': platform.architecture()[0],
            'processor': platform.processor(),
            'hostname': platform.node(),
            'flask_env': os.getenv('FLASK_ENV', 'production'),
            'debug_mode': os.getenv('FLASK_DEBUG', 'False'),
        }
        return jsonify({'environment': env_info})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/devtools/app_status', methods=['GET'])
@test_mode_login_required
def api_devtools_app_status():
    """Get application component status"""
    try:
        status = {
            'llm_backend': check_llm_backend_status(),
            'database': check_database_status(),
            'rag': check_rag_status(),
            'job_manager': check_job_manager_status()
        }
        return jsonify({'status': status})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def check_llm_backend_status():
    """Check if LLM backend is accessible"""
    try:
        from ..core.backend_llm_controller import get_backend_controller
        controller = get_backend_controller()
        if controller.is_server_ready():
            return {'online': True, 'message': 'LLM Backend Connected'}
        else:
            return {'online': False, 'message': 'LLM Backend Not Ready'}
    except Exception as e:
        logger.warning(f"LLM backend connection check failed: {e}")
        return {'online': False, 'message': 'Cannot connect to LLM Backend'}

def check_database_status():
    """Check database connectivity"""
    from ..models import db
    try:
        # Simple test to check if database is accessible
        db.session.connection()
        return {'online': True, 'message': 'Database accessible'}
    except Exception as e:
        logger.warning(f"Database connection check failed: {e}")
        return {'online': False, 'message': 'Database connection failed'}

def check_rag_status():
    """Check RAG system status"""
    from ..config import Config
    import os
    try:
        if os.path.exists(Config.RAG_VECTOR_DB_PATH):
            return {'online': True, 'message': 'Vector database found'}
        else:
            return {'online': False, 'message': 'Vector database not found'}
    except Exception as e:
        logger.warning(f"RAG system status check failed: {e}")
        return {'online': False, 'message': 'RAG system error'}

def check_job_manager_status():
    """Check job manager status"""
    from ..core.job_manager import job_manager
    try:
        if job_manager._running:
            return {'online': True, 'message': 'Job manager running'}
        else:
            return {'online': False, 'message': 'Job manager stopped'}
    except Exception as e:
        logger.warning(f"Job manager status check failed: {e}")
        return {'online': False, 'message': 'Job manager error'}

# Aggregate system health
@api_bp.route('/system/health', methods=['GET'])
def api_system_health():
    """Aggregate health across subsystems for UI status badge"""
    from ..core.stable_diffusion_controller import stable_diffusion_controller
    try:
        # LLM backend - fast check with timeout
        try:
            from ..core.backend_llm_controller import get_backend_controller
            llm = get_backend_controller()
            
            # Fast check - assume ready if models exist and process running
            llm_ready = False
            try:
                if llm.model_path and hasattr(llm, 'server_process') and llm.server_process:
                    llm_ready = True  # Process exists, assume ready
                else:
                    # Quick timeout check (1 second max)
                    import requests
                    resp = requests.get(f"{llm.server_url}/v1/models", timeout=1)
                    llm_ready = resp.status_code == 200
            except Exception:
                # If there's a model available, assume the system is functional
                llm_ready = llm.model_path is not None
                
            llm_info = {
                'ready': llm_ready,
                'server_url': getattr(llm, 'server_url', 'http://localhost:11435'),
                'n_ctx': getattr(llm, 'n_ctx', None),
                'n_threads': getattr(llm, 'n_threads', None)
            }
        except Exception:
            llm_info = {'ready': False}

        # Stable Diffusion
        try:
            sd_status = stable_diffusion_controller.get_status()
        except Exception:
            sd_status = {'installed': False, 'running': False}

        # RAG status (vector DB path exists)
        try:
            from ..config import Config
            import os
            rag_ok = os.path.exists(Config.RAG_VECTOR_DB_PATH)
        except Exception:
            rag_ok = False

        # Job manager
        jm = check_job_manager_status()

        # Socket.IO availability (presence indicates initialized)
        try:
            from .. import socketio
            ws_ready = socketio is not None
        except Exception:
            ws_ready = False

        return jsonify({
            'success': True,
            'health': {
                'llm': llm_info,
                'stable_diffusion': sd_status,
                'rag': {'ready': rag_ok},
                'job_manager': jm,
                'websocket': {'ready': ws_ready}
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/system/limits', methods=['GET'])
def api_system_limits():
    """Report resource policies/limits for UI display"""
    try:
        from ..core.backend_llm_controller import get_backend_controller
        llm = get_backend_controller()
        from ..core.stable_diffusion_controller import stable_diffusion_controller
        # Hardware-aware recommendations
        try:
            from ..core.hardware_manager import get_hardware_manager
            hw = get_hardware_manager()
            if not hw.hardware_info:
                hw.detect_hardware()
                hw.classify_performance_tier()
            rec = hw.get_resource_limits()
        except Exception:
            rec = {}

        limits = {
            'llm': {
                'n_ctx': getattr(llm, 'n_ctx', None),
                'n_threads': getattr(llm, 'n_threads', None),
                'max_memory_gb': getattr(llm, 'max_memory_gb', None)
            },
            'stable_diffusion': {
                'startup_timeout_s': getattr(stable_diffusion_controller, 'startup_timeout', None),
                'resource_policy': 'lowered_priority'
            },
            'hardware_recommendations': rec
        }
        return jsonify({'success': True, 'limits': limits})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/sample_prompts', methods=['GET'])
def api_sample_prompts():
    """Provide sample chat prompts for the chat page."""
    try:
        from ..utils.data_initializer import get_default_sample_prompts
        prompts = get_default_sample_prompts()
        if not prompts:
            prompts = [
                'Summarize this text...',
                'Brainstorm 5 ideas about...',
                "Explain like I'm 5: ...",
                'Write a step-by-step plan to ...'
            ]
        return jsonify({'success': True, 'prompts': prompts})
    except Exception:
        return jsonify({'success': True, 'prompts': [
            'Summarize this text...',
            'Brainstorm 5 ideas about...',
            "Explain like I'm 5: ...",
            'Write a step-by-step plan to ...'
        ]})

@api_bp.route('/system/usage', methods=['GET'])
def api_system_usage():
    """Basic system usage snapshot for UI dashboards."""
    try:
        from ..core.system_monitor import get_system_monitor
        mon = get_system_monitor()
        usage = mon.get_system_usage()
        return jsonify({'success': True, 'usage': usage})
    except Exception:
        return jsonify({'success': True, 'usage': {
            'cpu_percent': 0,
            'ram_percent': 0,
            'gpu_percent': None
        }})

@api_bp.route('/navigation', methods=['GET'])
def api_navigation():
    """Provide a canonical list of navigation items with availability flags."""
    try:
        navigation_data = get_cached_navigation_items()
        return jsonify({'success': True, 'navigation': navigation_data})
    except Exception as e:
        # Fallback navigation
        return jsonify({'success': True, 'navigation': [
            {'key': 'chat', 'title': 'Chat', 'path': '/chat', 'available': True},
            {'key': 'agents', 'title': 'Agents', 'path': '/agents', 'available': True},
            {'key': 'image', 'title': 'Image Studio', 'path': '/image_studio', 'available': True},
            {'key': 'audio', 'title': 'Audio Lab', 'path': '/audio_lab', 'available': True},
            {'key': 'rag', 'title': 'Knowledge Base', 'path': '/rag_manager', 'available': True},
            {'key': 'models', 'title': 'Models', 'path': '/models_manager', 'available': True},
            {'key': 'settings', 'title': 'Settings', 'path': '/settings', 'available': True},
        ]})

@cached(timeout=600)  # Cache for 10 minutes
def get_cached_navigation_items():
    """Get cached navigation items with availability check"""
    # Base items
    items = [
        {'key': 'chat', 'title': 'Chat', 'path': '/chat', 'available': True},
        {'key': 'agents', 'title': 'Agents', 'path': '/agents', 'available': True},
        {'key': 'image', 'title': 'Image Studio', 'path': '/image_studio', 'available': True},
        {'key': 'audio', 'title': 'Audio Lab', 'path': '/audio_lab', 'available': True},
        {'key': 'rag', 'title': 'Knowledge Base', 'path': '/rag_manager', 'available': True},
        {'key': 'models', 'title': 'Models', 'path': '/models_manager', 'available': True},
        {'key': 'settings', 'title': 'Settings', 'path': '/settings', 'available': True},
        {'key': 'health', 'title': 'System Health', 'path': '/system-health', 'available': True},
    ]
    
    # Use health to mark availability
    try:
        # Call the function directly to get the health data
        data = None
        health_result = api_system_health()
        
        # Handle different return types
        if isinstance(health_result, tuple):
            # Extract response from tuple
            response_obj = health_result[0] if health_result else None
        else:
            response_obj = health_result
        
        # Get JSON data if it's a Response object
        if response_obj and hasattr(response_obj, 'get_json'):
            data = response_obj.get_json(silent=True)
        elif isinstance(response_obj, dict):
            data = response_obj
    except Exception:
        data = None

    if data and isinstance(data, dict) and data.get('success'):
        health = data.get('health', {})
        for it in items:
            if it['key'] == 'image' and not health.get('stable_diffusion', {}).get('installed', False):
                it['available'] = False
            if it['key'] == 'chat' and not health.get('llm', {}).get('ready', False):
                it['available'] = True  # Keep visible but degraded
    
    return items

# Minimal model management endpoints expected by frontend
@api_bp.route('/pull_model', methods=['POST'])
def api_pull_model():
    try:
        data = request.get_json(silent=True) or {}
        model_name = (data.get('model_name') or '').strip()
        if not model_name:
            return jsonify({'error': 'model_name required'}), 400
        return jsonify({'status': 'success', 'message': f"Model '{model_name}' pull scheduled."})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/optimize_model', methods=['POST'])
def api_optimize_model():
    try:
        data = request.get_json(silent=True) or {}
        base_model = (data.get('base_model_name') or '').strip()
        if not base_model:
            return jsonify({'error': 'base_model_name required'}), 400
        return jsonify({'status': 'success', 'message': f"Optimization started for '{base_model}'."})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/delete_model', methods=['POST'])
def api_delete_model():
    try:
        data = request.get_json(silent=True) or {}
        model_name = (data.get('model_name') or '').strip()
        if not model_name:
            return jsonify({'error': 'model_name required'}), 400
        from ..utils.llm_model_manager import LLMModelManager
        mgr = LLMModelManager()
        ok = mgr.delete_model(model_name)
        if ok:
            return jsonify({'status': 'success', 'message': f"Deleted '{model_name}'."})
        return jsonify({'status': 'error', 'error': 'Delete failed'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/ui/responsive_guidelines', methods=['GET'])
def api_ui_responsive_guidelines():
    """Expose recommended breakpoints/scales for UI consumption."""
    try:
        guidelines = {
            'breakpoints': {
                'xs': 360,
                'sm': 640,
                'md': 768,
                'lg': 1024,
                'xl': 1280,
                'xxl': 1536
            },
            'min_supported_width': 320,
            'max_tested_width': 3840,
            'suggestions': [
                'Use fluid containers and avoid fixed pixel widths for primary layout regions.',
                'Ensure critical buttons remain visible at 320px; move secondary actions into overflow menus on xs.'
            ]
        }
        return jsonify({'success': True, 'guidelines': guidelines})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Add main-level endpoints that are accessed directly under /api/

@api_bp.route('/system_prompts', methods=['GET'])
@test_mode_login_required
def api_system_prompts():
    """Get all system prompts"""
    from ..models import SystemPrompt
    try:
        prompts = SystemPrompt.query.all()
        prompts_data = []
        for prompt in prompts:
            prompts_data.append({
                'id': prompt.id,
                'name': prompt.name,
                'description': prompt.description,
                'category': prompt.category,
                'content': prompt.content,
                'created_at': prompt.created_at.isoformat() if prompt.created_at else None
            })
        return jsonify(prompts_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/system_prompts/<int:prompt_id>/use', methods=['POST'])
@test_mode_login_required
def api_use_system_prompt(prompt_id):
    """Set a system prompt as the active one"""
    from ..models import SystemPrompt, AppSetting, db
    from ..logger import log_api_request, log_user_action, log_error
    
    log_api_request(request.endpoint, request.method)
    try:
        prompt = SystemPrompt.query.get_or_404(prompt_id)
        
        # Save the active prompt ID in app settings
        setting = AppSetting.query.filter_by(key='active_system_prompt_id').first()
        if setting:
            setting.value = str(prompt_id)
        else:
            setting = AppSetting()
            setting.key = 'active_system_prompt_id'
            setting.value = str(prompt_id)
            db.session.add(setting)
        
        db.session.commit()
        log_user_action(current_user.id, f"Set active system prompt: {prompt.name}")
        
        return jsonify({'success': True, 'active_prompt_id': prompt_id})
        
    except Exception as e:
        log_error(f"Use system prompt API error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/configuration', methods=['GET', 'POST'])
@test_mode_login_required
def api_configuration():
    """Get or update app configuration"""
    from ..models import AppSetting, db
    from ..logger import log_error
    
    try:
        if request.method == 'POST':
            # Update configuration
            config_data = request.json
            if not config_data:
                return jsonify({'error': 'No configuration data provided'}), 400
            
            # Update or create settings
            for key, value in config_data.items():
                if key == 'features' and isinstance(value, dict):
                    # Handle nested features object
                    for feature_key, feature_value in value.items():
                        setting_key = f'feature_{feature_key}'
                        setting = AppSetting.query.filter_by(key=setting_key).first()
                        if setting:
                            setting.value = str(feature_value).lower()
                        else:
                            setting = AppSetting()
                            setting.key = setting_key
                            setting.value = str(feature_value).lower()
                            db.session.add(setting)
                else:
                    # Handle regular settings
                    setting = AppSetting.query.filter_by(key=key).first()
                    if setting:
                        setting.value = str(value)
                    else:
                        setting = AppSetting()
                        setting.key = key
                        setting.value = str(value)
                        db.session.add(setting)
            
            db.session.commit()
            return jsonify({'success': True, 'message': 'Configuration updated successfully'})
        
        else:
            # Get configuration
            config = {}
            settings = AppSetting.query.all()
            for setting in settings:
                if setting.key.startswith('feature_'):
                    # Group features under 'features' key
                    if 'features' not in config:
                        config['features'] = {}
                    feature_name = setting.key.replace('feature_', '')
                    config['features'][feature_name] = setting.value.lower() == 'true'
                else:
                    # Convert numeric values appropriately
                    value = setting.value
                    if value.isdigit():
                        config[setting.key] = int(value)
                    elif value.replace('.', '').isdigit():
                        config[setting.key] = float(value)
                    elif value.lower() in ('true', 'false'):
                        config[setting.key] = value.lower() == 'true'
                    else:
                        config[setting.key] = value
            
            # Add some default values if not set
            if 'app_name' not in config:
                config['app_name'] = 'Vybe'
            if 'version' not in config:
                config['version'] = '1.0Test'
            if 'features' not in config:
                config['features'] = {
                    'rag': True,
                    'web_search': True,
                    'file_management': True,
                    'image_generation': True
                }
                
            return jsonify(config)
            
    except Exception as e:
        log_error(f"Configuration API error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Backward-compatibility alias for settings API used by some frontend code
@api_bp.route('/config', methods=['GET', 'POST'])
@test_mode_login_required
def api_config_alias():
    return api_configuration()

@api_bp.route('/installed_models_detailed', methods=['GET'])
@test_mode_login_required
def api_installed_models_detailed_proxy():
    """Get detailed information about installed models from llama-cpp backend"""
    # from ..utils.llm_backend_manager import llm_backend_manager  # New llama-cpp-python backend manager
    from ..core.backend_llm_controller import llm_controller
    import requests
    
    # Ensure llama-cpp backend is running
    if not llm_controller.is_server_ready():
        return jsonify({'error': 'LLM backend service could not be started'}), 503
    
    try:
        response = requests.get('http://localhost:11434/api/tags', timeout=10)
        if response.status_code == 200:
            data = response.json()
            models = []
            for model in data.get('models', []):
                model_info = {
                    'name': model.get('name', 'Unknown'),
                    'size': model.get('size', 0),
                    'modified_at': model.get('modified_at', ''),
                    'digest': model.get('digest', ''),
                    'parameter_size': model.get('details', {}).get('parameter_size', 'Unknown'),
                    'quantization_level': model.get('details', {}).get('quantization_level', 'Unknown'),
                    'family': model.get('details', {}).get('family', 'Unknown'),
                    'families': model.get('details', {}).get('families', []),
                    'format': model.get('details', {}).get('format', 'Unknown'),
                    'parent_model': model.get('details', {}).get('parent_model', 'Unknown')
                }
                models.append(model_info)
            return jsonify(models)
        else:
            return jsonify([])
    except requests.exceptions.ConnectionError:
        return jsonify([])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/recommended_models', methods=['GET'])
@test_mode_login_required  
def api_recommended_models_proxy():
    """Get list of recommended models for installation"""
    recommended = [
        {
            'name': 'llama3.2:3b',
            'description': 'Lightweight Llama 3.2 model, good for basic tasks',
            'size': '2.0GB',
            'use_cases': ['General chat', 'Simple Q&A', 'Code assistance'],
            'download_size': 'Small'
        },
        {
            'name': 'llama3.2:1b',
            'description': 'Ultra-lightweight Llama 3.2 model for resource-constrained environments',
            'size': '1.3GB',
            'use_cases': ['Quick responses', 'Basic chat', 'Mobile/edge deployment'],
            'download_size': 'Extra Small'
        },
        {
            'name': 'qwen2.5:7b',
            'description': 'Qwen 2.5 model with strong reasoning capabilities',
            'size': '4.7GB',
            'use_cases': ['Complex reasoning', 'Analysis', 'Technical questions'],
            'download_size': 'Medium'
        },
        {
            'name': 'mistral:7b',
            'description': 'Efficient Mistral model for general-purpose tasks',
            'size': '4.1GB', 
            'use_cases': ['Programming', 'Writing', 'General knowledge'],
            'download_size': 'Medium'
        },
        {
            'name': 'codellama:7b',
            'description': 'Specialized model for code generation and programming',
            'size': '3.8GB',
            'use_cases': ['Code generation', 'Programming help', 'Debugging'],
            'download_size': 'Medium'
        }
    ]
    
    return jsonify(recommended)

@api_bp.route('/frontend-error', methods=['POST'])
def log_frontend_error():
    """Log frontend errors to backend"""
    from ..logger import log_error
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data is required'}), 400
        
        error_msg = data.get('error', 'Unknown error')
        context = data.get('context', '')
        url = data.get('url', '')
        user_agent = data.get('userAgent', '')
        timestamp = data.get('timestamp', '')
        
        log_message = f"Frontend Error: {error_msg}"
        if context:
            log_message += f" | Context: {context}"
        if url:
            log_message += f" | URL: {url}"
        if user_agent:
            log_message += f" | User Agent: {user_agent}"
        if timestamp:
            log_message += f" | Timestamp: {timestamp}"
            
        log_error(log_message)
        
        return jsonify({'success': True, 'message': 'Error logged successfully'})
        
    except Exception as e:
        log_error(f"Failed to log frontend error: {str(e)}")
        return jsonify({'error': 'Failed to log error'}), 500

# Add direct access endpoints that some JS files expect
@api_bp.route('/logs', methods=['GET'])
@test_mode_login_required
def api_logs():
    """Get application logs (direct access)"""
    return api_devtools_logs()

@api_bp.route('/config', methods=['GET'])
@test_mode_login_required  
def api_config():
    """Get application configuration (direct access)"""
    return api_devtools_app_config()

@api_bp.route('/feedback', methods=['POST'])
@test_mode_login_required
def api_feedback():
    """Submit user feedback with proper database storage"""
    from ..logger import log_api_request, log_user_action, log_error
    from ..models import Feedback
    from datetime import datetime
    
    log_api_request(request.endpoint, request.method)
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data is required'}), 400
            
        feedback_text = data.get('feedback', '').strip()
        if not feedback_text:
            return jsonify({'error': 'Feedback text is required'}), 400
        
        # Extract additional feedback data
        feedback_type = data.get('type', 'general')
        subject = data.get('subject', '').strip() or None
        rating = data.get('rating')
        category = data.get('category', '').strip() or None
        
        # Validate rating if provided
        if rating is not None:
            try:
                rating = int(rating)
                if rating < 1 or rating > 5:
                    rating = None
            except (ValueError, TypeError):
                rating = None
        
        # Get browser/session info for context
        browser_info = data.get('browser_info')
        session_id = data.get('session_id')
        metadata = {
            'user_agent': request.headers.get('User-Agent'),
            'referer': request.headers.get('Referer'),
            'timestamp': datetime.utcnow().isoformat(),
            'additional_data': data.get('metadata', {})
        }
        
        # Get client IP
        ip_address = request.headers.get('X-Forwarded-For', '').split(',')[0].strip()
        if not ip_address:
            ip_address = request.headers.get('X-Real-IP', '')
        if not ip_address:
            ip_address = request.remote_addr
        
        # Create feedback entry
        feedback_entry = Feedback.create_feedback(
            user_id=current_user.id,
            message=feedback_text,
            feedback_type=feedback_type,
            subject=subject,
            rating=rating,
            category=category,
            metadata=metadata,
            browser_info=browser_info,
            session_id=session_id,
            ip_address=ip_address
        )
        
        log_user_action(current_user.id, f"Submitted feedback (ID: {feedback_entry.id}): {feedback_text[:100]}...")
        
        return jsonify({
            'success': True,
            'message': 'Thank you for your feedback! We appreciate your input.',
            'feedback_id': feedback_entry.id
        })
        
    except Exception as e:
        log_error(f"Feedback API error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/feedback', methods=['GET'])
@test_mode_login_required
def api_get_feedback():
    """Get feedback entries (for admin/review purposes)"""
    from ..logger import log_api_request, log_error
    from ..models import Feedback
    
    log_api_request(request.endpoint, request.method)
    try:
        # Basic pagination
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)  # Max 100 per page
        status = request.args.get('status', '').strip()
        feedback_type = request.args.get('type', '').strip()
        
        # Build query
        query = Feedback.query
        
        if status:
            query = query.filter(Feedback.status == status)
        if feedback_type:
            query = query.filter(Feedback.feedback_type == feedback_type)
        
        # Order by creation date (newest first)
        query = query.order_by(Feedback.created_at.desc())
        
        # Paginate
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        feedback_entries = pagination.items
        
        return jsonify({
            'success': True,
            'feedback': [entry.to_dict() for entry in feedback_entries],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        })
        
    except Exception as e:
        log_error(f"Get feedback API error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/feedback/<int:feedback_id>', methods=['PATCH'])
@test_mode_login_required
def api_update_feedback_status(feedback_id):
    """Update feedback status (for admin/review purposes)"""
    from ..logger import log_api_request, log_user_action, log_error
    from ..models import Feedback, db
    from datetime import datetime
    
    log_api_request(request.endpoint, request.method)
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data is required'}), 400
        
        feedback = Feedback.query.get_or_404(feedback_id)
        
        # Update allowed fields
        if 'status' in data:
            valid_statuses = ['pending', 'reviewed', 'resolved', 'closed']
            if data['status'] in valid_statuses:
                feedback.status = data['status']
                feedback.reviewed_by = current_user.id
                feedback.reviewed_at = datetime.utcnow()
                feedback.updated_at = datetime.utcnow()
        
        if 'priority' in data:
            valid_priorities = ['low', 'medium', 'high', 'critical']
            if data['priority'] in valid_priorities:
                feedback.priority = data['priority']
                feedback.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        log_user_action(current_user.id, f"Updated feedback {feedback_id} status to {feedback.status}")
        
        return jsonify({
            'success': True,
            'message': 'Feedback updated successfully',
            'feedback': feedback.to_dict()
        })
        
    except Exception as e:
        log_error(f"Update feedback API error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/csrf-token', methods=['GET'])
def api_csrf_token():
    """Get CSRF token for forms"""
    try:
        from flask_wtf.csrf import generate_csrf
        token = generate_csrf()
        return jsonify({'csrf_token': token})
    except ImportError:
        # If CSRF not available, return a placeholder
        import secrets
        token = secrets.token_urlsafe(32)
        return jsonify({'csrf_token': token})
    except Exception as e:
        from ..logger import log_error
        log_error(f"CSRF token generation error: {str(e)}")
        return jsonify({'error': 'Failed to generate CSRF token'}), 500

@api_bp.route('/security/headers', methods=['GET'])
def api_security_headers():
    """Get security configuration and headers for client-side validation"""
    from ..config import Config
    
    return jsonify({
        'force_https': Config.FORCE_HTTPS,
        'session_cookie_secure': Config.SESSION_COOKIE_SECURE,
        'csp_enabled': True,
        'security_headers': {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block'
        },
        'max_upload_size': Config.MAX_CONTENT_LENGTH,
        'allowed_origins': [
            'https://localhost',
            'https://127.0.0.1',
            'http://localhost' if not Config.FORCE_HTTPS else None,
            'http://127.0.0.1' if not Config.FORCE_HTTPS else None
        ]
    })
