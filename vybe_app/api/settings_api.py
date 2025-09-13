"""
Settings API module - handles settings and configuration endpoints.
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from ..auth import test_mode_login_required
from ..models import db, AppSetting, SystemPrompt, AppConfiguration
from ..logger import log_error, log_api_request, log_user_action
from ..utils.api_response_utils import (
    format_success_response, format_error_response, format_validation_error,
    handle_api_exception, standardize_model_response
)
from ..utils.input_validation import InputValidator, ValidationError
from ..utils.cache_manager import cached

# Create settings sub-blueprint
settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

# Cached helper functions for semi-static data
@cached(timeout=3600)  # Cache for 1 hour
def get_cached_system_prompts():
    """Get all system prompts with 1-hour cache"""
    prompts = SystemPrompt.query.all()
    prompts_data = []
    for prompt in prompts:
        prompts_data.append(standardize_model_response({
            'id': prompt.id,
            'name': prompt.name,
            'description': prompt.description,
            'category': prompt.category,
            'content': prompt.content,
            'created_at': prompt.created_at.isoformat() if prompt.created_at else None
        }))
    return format_success_response({'prompts': prompts_data})

@cached(timeout=1800)  # Cache for 30 minutes
def get_cached_app_settings():
    """Get all app settings with 30-minute cache"""
    settings_dict = {}
    all_settings = AppSetting.query.all()
    for setting in all_settings:
        settings_dict[setting.key] = setting.value
    return settings_dict

@cached(timeout=2400)  # Cache for 40 minutes
def get_cached_app_configuration():
    """Get app configuration with 40-minute cache"""
    from ..config import Config
    config = Config.get_config_dict()
    return config

@settings_bp.route('/theme_mode', methods=['GET', 'POST'])
@test_mode_login_required
def api_theme_mode():
    """Get or set theme mode"""
    log_api_request(request.endpoint, request.method)
    try:
        if request.method == 'GET':
            # Get theme mode from app settings
            setting = AppSetting.query.filter_by(key='theme_mode').first()
            theme_mode = setting.value if setting else 'light'
            return format_success_response({'theme_mode': theme_mode})
        
        elif request.method == 'POST':
            data = request.get_json()
            if not data:
                return format_validation_error('data', 'Request data is required')
            
            # Use comprehensive validation
            try:
                theme_mode = InputValidator.validate_theme_mode(data.get('theme_mode', 'light'))
            except ValidationError as e:
                return format_validation_error(e.field or '', e.message, e.args[0] if e.args else e.message)
            
            # Save theme mode to database
            setting = AppSetting.query.filter_by(key='theme_mode').first()
            if setting:
                setting.value = theme_mode
            else:
                setting = AppSetting()
                setting.key = 'theme_mode'
                setting.value = theme_mode
                db.session.add(setting)
            
            db.session.commit()
            log_user_action(current_user.id, f"Changed theme mode to {theme_mode}")
            return format_success_response({'theme_mode': theme_mode})
        
        # Fallback return for any unhandled cases
        return format_error_response('Invalid request method', 'method_not_allowed', 405)
            
    except (ValueError, TypeError) as e:
        log_error(f"Theme mode API validation error: {str(e)}")
        return format_validation_error('theme_mode', str(e))
    except Exception as e:
        return handle_api_exception(e, {'endpoint': 'theme_mode', 'method': request.method})

@settings_bp.route('/system_prompts', methods=['GET', 'POST'])
@test_mode_login_required
def api_system_prompts():
    """Get all system prompts or create a new one"""
    log_api_request(request.endpoint, request.method)
    try:
        if request.method == 'GET':
            return get_cached_system_prompts()
        
        elif request.method == 'POST':
            data = request.get_json()
            if not data:
                return format_validation_error('data', 'Request data is required')
            
            # Use comprehensive validation
            try:
                validated_data = InputValidator.validate_system_prompt(data)
            except ValidationError as e:
                return format_validation_error(e.field or 'data', e.message)
            
            new_prompt = SystemPrompt()
            new_prompt.name = validated_data['name']
            new_prompt.description = validated_data['description']
            new_prompt.category = validated_data['category']
            new_prompt.content = validated_data['content']
            
            db.session.add(new_prompt)
            db.session.commit()
            log_user_action(current_user.id, f"Created system prompt: {new_prompt.name}")
            
            return format_success_response(
                standardize_model_response({
                    'id': new_prompt.id,
                    'name': new_prompt.name,
                    'description': new_prompt.description,
                    'category': new_prompt.category,
                    'content': new_prompt.content
                }),
                status_code=201
            )
        
        return format_error_response('Invalid request method', 'method_not_allowed', 405)
        
    except (ValueError, TypeError) as e:
        log_error(f"System prompts API validation error: {str(e)}")
        return format_validation_error('prompt_data', str(e))
    except Exception as e:
        return handle_api_exception(e, {'endpoint': 'system_prompts', 'method': request.method})

@settings_bp.route('/system_prompts/<int:prompt_id>', methods=['GET', 'PUT', 'DELETE'])
@test_mode_login_required
def api_system_prompt_detail(prompt_id):
    """Get, update, or delete a specific system prompt"""
    log_api_request(request.endpoint, request.method)
    try:
        prompt = SystemPrompt.query.get_or_404(prompt_id)
        
        if request.method == 'GET':
            return format_success_response({
                'id': prompt.id,
                'name': prompt.name,
                'description': prompt.description,
                'category': prompt.category,
                'content': prompt.content,
                'created_at': prompt.created_at.isoformat() if prompt.created_at else None
            })
        
        elif request.method == 'PUT':
            data = request.get_json()
            prompt.name = data.get('name', prompt.name)
            prompt.description = data.get('description', prompt.description)
            prompt.category = data.get('category', prompt.category)
            prompt.content = data.get('content', prompt.content)
            
            db.session.commit()
            log_user_action(current_user.id, f"Updated system prompt: {prompt.name}")
            
            return format_success_response({
                'id': prompt.id,
                'name': prompt.name,
                'description': prompt.description,
                'category': prompt.category,
                'content': prompt.content
            })
        
        elif request.method == 'DELETE':
            db.session.delete(prompt)
            db.session.commit()
            log_user_action(current_user.id, f"Deleted system prompt: {prompt.name}")
            return format_success_response({'success': True})
        
        return format_error_response('Invalid request method', 'method_not_allowed', 405)
        
    except Exception as e:
        log_error(f"System prompt detail API error: {str(e)}")
        return handle_api_exception(e, {'endpoint': 'system_prompt_detail', 'method': request.method})

@settings_bp.route('/system_prompts/<int:prompt_id>/use', methods=['POST'])
@test_mode_login_required
def api_use_system_prompt(prompt_id):
    """Set a system prompt as the active one"""
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
        
        return format_success_response({'success': True, 'active_prompt_id': prompt_id})
        
    except Exception as e:
        log_error(f"Use system prompt API error: {str(e)}")
        return handle_api_exception(e, {'endpoint': 'use_system_prompt', 'method': request.method})


@settings_bp.route('/startup_prefs', methods=['GET', 'POST'])
@test_mode_login_required
def api_startup_prefs():
    """Get or set startup preferences for auto-launching services at app start."""
    log_api_request(request.endpoint, request.method)
    try:
        pref_keys = {
            'auto_launch_llm_on_start': False,
            'auto_launch_sd_on_start': False,
            'auto_launch_comfy_on_start': False
        }
        if request.method == 'GET':
            prefs = {}
            for key, default in pref_keys.items():
                setting = AppSetting.query.filter_by(key=key).first()
                prefs[key] = (setting.value.lower() == 'true') if setting else default
            return format_success_response({'success': True, 'prefs': prefs})
        elif request.method == 'POST':
            data = request.get_json() or {}
            updated = {}
            for key in pref_keys.keys():
                if key in data:
                    val = bool(data[key])
                    setting = AppSetting.query.filter_by(key=key).first()
                    if not setting:
                        setting = AppSetting()
                        setting.key = key
                        db.session.add(setting)
                    setting.value = 'true' if val else 'false'
                    updated[key] = val
            db.session.commit()
            log_user_action(current_user.id, f"Updated startup prefs: {updated}")
            return format_success_response({'success': True, 'updated': updated})
        return format_error_response('Invalid request method', 'method_not_allowed', 405)
    except Exception as e:
        log_error(f"Startup prefs API error: {str(e)}")
        return handle_api_exception(e, {'endpoint': 'startup_prefs', 'method': request.method})


@settings_bp.route('/audio_prefs', methods=['GET', 'POST'])
@test_mode_login_required
def api_audio_prefs():
    """Get or set audio preferences (e.g., enable Edge TTS)."""
    log_api_request(request.endpoint, request.method)
    try:
        key = 'enable_edge_tts'
        if request.method == 'GET':
            setting = AppSetting.query.filter_by(key=key).first()
            enabled = (setting.value.lower() == 'true') if setting and isinstance(setting.value, str) else False
            return format_success_response({'success': True, 'prefs': {'enable_edge_tts': enabled}})
        elif request.method == 'POST':
            data = request.get_json() or {}
            enabled = bool(data.get('enable_edge_tts', False))
            setting = AppSetting.query.filter_by(key=key).first()
            if not setting:
                setting = AppSetting()
                setting.key = key
                db.session.add(setting)
            setting.value = 'true' if enabled else 'false'
            db.session.commit()
            log_user_action(current_user.id, f"Updated audio prefs: enable_edge_tts={enabled}")
            return format_success_response({'success': True, 'updated': {'enable_edge_tts': enabled}})
        return format_error_response('Invalid request method', 'method_not_allowed', 405)
    except Exception as e:
        log_error(f"Audio prefs API error: {str(e)}")
        return handle_api_exception(e, {'endpoint': 'audio_prefs', 'method': request.method})


@settings_bp.route('/ha_config', methods=['GET', 'POST'])
@test_mode_login_required
def api_ha_config():
    """Get or set Home Assistant configuration"""
    log_api_request(request.endpoint, request.method)
    try:
        if request.method == 'GET':
            # Get Home Assistant config from app settings
            api_url_setting = AppSetting.query.filter_by(key='ha_api_url').first()
            token_setting = AppSetting.query.filter_by(key='ha_api_token').first()
            
            return format_success_response({
                'api_url': api_url_setting.value if api_url_setting else '',
                'has_token': bool(token_setting and token_setting.value)
            })
        
        elif request.method == 'POST':
            data = request.get_json()
            if not data:
                return format_validation_error('data', 'Request data is required')
            
            api_url = data.get('api_url', '').strip()
            api_token = data.get('api_token', '').strip()
            
            if not api_url:
                return format_validation_error('api_url', 'API URL is required')
            
            # Save API URL
            url_setting = AppSetting.query.filter_by(key='ha_api_url').first()
            if url_setting:
                url_setting.value = api_url
            else:
                url_setting = AppSetting()
                url_setting.key = 'ha_api_url'
                url_setting.value = api_url
                db.session.add(url_setting)
            
            # Save API token if provided
            if api_token:
                token_setting = AppSetting.query.filter_by(key='ha_api_token').first()
                if token_setting:
                    token_setting.value = api_token
                else:
                    token_setting = AppSetting()
                    token_setting.key = 'ha_api_token'
                    token_setting.value = api_token
                    db.session.add(token_setting)
            
            db.session.commit()
            log_user_action(current_user.id, "Updated Home Assistant configuration")
            return format_success_response({'success': True})
        
        return format_error_response('Invalid request method', 'method_not_allowed', 405)
            
    except Exception as e:
        log_error(f"Home Assistant config API error: {str(e)}")
        return handle_api_exception(e, {'endpoint': 'ha_config', 'method': request.method})


@settings_bp.route('/test_ha_connection', methods=['POST'])
@test_mode_login_required
def api_test_ha_connection():
    """Test Home Assistant connection"""
    log_api_request(request.endpoint, request.method)
    try:
        from ..core.home_assistant_controller import HomeAssistantController
        
        ha_controller = HomeAssistantController()
        
        # Test connection by getting entities
        entities = ha_controller.get_entities()
        
        if entities is not None:
            return format_success_response({
                'success': True,
                'entity_count': len(entities)
            })
        else:
            return format_error_response(
                'Failed to connect to Home Assistant. Check URL and token.',
                'ha_connection_failed',
                500
            )
            
    except Exception as e:
        log_error(f"Test Home Assistant connection error: {str(e)}")
        return handle_api_exception(e, {'endpoint': 'test_ha_connection', 'method': request.method})


@settings_bp.route('/backend_llm_status', methods=['GET'])
@test_mode_login_required
def api_backend_llm_status():
    """Check backend LLM model status"""
    log_api_request(request.endpoint, request.method)
    try:
        from ..core.setup_manager import setup_manager
        
        model_status = setup_manager.get_model_status()
        backend_model = model_status.get('backend_llm_model', {})
        
        return format_success_response({
            'success': True,
            'available': backend_model.get('available', False),
            'model_name': backend_model.get('name', 'gemma2:2b')
        })
            
    except Exception as e:
        log_error(f"Backend LLM status API error: {str(e)}")
        return handle_api_exception(e, {'endpoint': 'backend_llm_status', 'method': request.method})


@settings_bp.route('/download_backend_llm', methods=['POST'])
@test_mode_login_required
def api_download_backend_llm():
    """Download backend LLM model"""
    log_api_request(request.endpoint, request.method)
    try:
        from ..core.setup_manager import setup_manager
        
        # Download the backend LLM model
        success = setup_manager._download_backend_llm_model()
        
        if success:
            log_user_action(current_user.id, "Downloaded backend LLM model")
            return format_success_response({'success': True})
        else:
            return format_error_response(
                'Failed to download model. Check logs for details.',
                'model_download_failed',
                500
            )
            
    except Exception as e:
        log_error(f"Download backend LLM API error: {str(e)}")
        return handle_api_exception(e, {'endpoint': 'download_backend_llm', 'method': request.method})


@settings_bp.route('/rag_config', methods=['GET', 'POST'])
@test_mode_login_required
def api_rag_config():
    """Get or set RAG configuration"""
    log_api_request(request.endpoint, request.method)
    try:
        if request.method == 'GET':
            # Get RAG auto-processing setting
            setting = AppSetting.query.filter_by(key='rag_auto_processing').first()
            auto_processing = setting.value == 'true' if setting else True  # Default to True
            
            return format_success_response({'auto_processing': auto_processing})
        
        elif request.method == 'POST':
            data = request.get_json()
            if not data:
                return format_validation_error('data', 'Request data is required')
            
            auto_processing = data.get('auto_processing', True)
            
            # Save RAG auto-processing setting
            setting = AppSetting.query.filter_by(key='rag_auto_processing').first()
            if setting:
                setting.value = 'true' if auto_processing else 'false'
            else:
                setting = AppSetting()
                setting.key = 'rag_auto_processing'
                setting.value = 'true' if auto_processing else 'false'
                db.session.add(setting)
            
            db.session.commit()
            log_user_action(current_user.id, f"Set RAG auto-processing to {auto_processing}")
            return format_success_response({'success': True})
        
        return format_error_response('Invalid request method', 'method_not_allowed', 405)
            
    except Exception as e:
        log_error(f"RAG config API error: {str(e)}")
        return handle_api_exception(e, {'endpoint': 'rag_config', 'method': request.method})


# === External AI Provider Settings (OpenAI / Anthropic) ===
@settings_bp.route('/api_providers', methods=['GET', 'POST'])
@test_mode_login_required
def api_providers():
    """Get or set external AI provider configuration. Keys are stored as sensitive values."""
    log_api_request(request.endpoint, request.method)
    try:
        if request.method == 'GET':
            # Return only presence flags, never the raw keys
            openai_cfg = AppConfiguration.query.filter_by(key='openai_api_key').first()
            anthropic_cfg = AppConfiguration.query.filter_by(key='anthropic_api_key').first()
            # Get configuration values from database
            default_provider_config = AppConfiguration.query.filter_by(key='llm_routing_default_provider').first()
            default_provider = default_provider_config.get_value() if default_provider_config else 'local'
            
            routing_mode_config = AppConfiguration.query.filter_by(key='llm_routing_mode').first()
            routing_mode = routing_mode_config.get_value() if routing_mode_config else 'prefer_local'
            return format_success_response({
                'success': True,
                'providers': {
                    'openai': { 'configured': bool(openai_cfg and openai_cfg.value) },
                    'anthropic': { 'configured': bool(anthropic_cfg and anthropic_cfg.value) }
                },
                'default_provider': default_provider,
                'routing_mode': routing_mode
            })

        # POST: Save provided keys and preferences
        data = request.get_json() or {}
        updated = {}

        if 'openai_api_key' in data:
            val = (data.get('openai_api_key') or '').strip()
            config = AppConfiguration.query.filter_by(key='openai_api_key').first()
            if not config:
                config = AppConfiguration()
                config.key = 'openai_api_key'
                config.data_type = 'string'
                config.description = 'OpenAI API key'
                db.session.add(config)
            config.set_value(val)
            updated['openai'] = bool(val)

        if 'anthropic_api_key' in data:
            val = (data.get('anthropic_api_key') or '').strip()
            config = AppConfiguration.query.filter_by(key='anthropic_api_key').first()
            if not config:
                config = AppConfiguration()
                config.key = 'anthropic_api_key'
                config.data_type = 'string'
                config.description = 'Anthropic API key'
                db.session.add(config)
            config.set_value(val)
            updated['anthropic'] = bool(val)

        if 'default_provider' in data:
            config = AppConfiguration.query.filter_by(key='llm_routing_default_provider').first()
            if not config:
                config = AppConfiguration()
                config.key = 'llm_routing_default_provider'
                config.data_type = 'string'
                config.description = 'Default provider for LLM routing'
                db.session.add(config)
            config.set_value(data.get('default_provider') or 'local')

        if 'routing_mode' in data:
            config = AppConfiguration.query.filter_by(key='llm_routing_mode').first()
            if not config:
                config = AppConfiguration()
                config.key = 'llm_routing_mode'
                config.data_type = 'string'
                config.description = 'Routing mode policy'
                db.session.add(config)
            config.set_value(data.get('routing_mode') or 'prefer_local')

        log_user_action(getattr(current_user, 'id', None), f"Updated API providers: {list(updated.keys())}")
        return format_success_response({ 'success': True, 'updated': updated })

    except Exception as e:
        log_error(f"API providers settings error: {str(e)}")
        return handle_api_exception(e, {'endpoint': 'api_providers', 'method': request.method})
