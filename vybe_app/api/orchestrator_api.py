"""
Orchestrator API module - handles orchestrator model selection and management.
"""

from flask import Blueprint, request, jsonify, Response
from ..auth import test_mode_login_required, current_user
import json
from datetime import datetime
from typing import Dict, List, Any, Union

from ..logger import log_error, log_api_request, handle_api_errors, log_execution_time
from ..core.manager_model import get_manager_model
from ..models import db, AppSetting

# Create orchestrator sub-blueprint
orchestrator_bp = Blueprint('orchestrator', __name__, url_prefix='/orchestrator')


@orchestrator_bp.route('/status', methods=['GET'])
@test_mode_login_required
@handle_api_errors
def get_orchestrator_status():  # Remove slow log_execution_time decorator
    """Get current orchestrator status and configuration"""
    log_api_request(request.endpoint, request.method)
    
    try:
        manager = get_manager_model()
        status = manager.get_status()
        
        return jsonify({
            'success': True,
            'status': status,
            'selected_model': manager.orchestrator_model,
            'pc_profile': manager.pc_profile,
            'user_profile_summary': {
                'total_interactions': manager.user_profile.get('total_interactions', 0),
                'skill_level': manager._assess_skill_level(),
                'hardware_tier': manager.pc_profile.get('hardware_tier', 'unknown')
            }
        })
        
    except Exception as e:
        log_error(f"Error getting orchestrator status: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@orchestrator_bp.route('/models', methods=['GET'])
@test_mode_login_required
@handle_api_errors
@log_execution_time
def get_available_orchestrator_models():
    """Get list of available orchestrator models"""
    log_api_request(request.endpoint, request.method)
    
    try:
        manager = get_manager_model()
        models = manager.get_available_orchestrator_models()
        
        # Add installation status for each model
        installed_models = [m['name'] for m in manager.model_manager.get_available_models()]
        
        for model in models:
            model['installed'] = model['name'] in installed_models
            model['recommended_for_user'] = model['tier'] == manager.pc_profile.get('hardware_tier', 'budget')
        
        return jsonify({
            'success': True,
            'models': models,
            'current_selection': manager.orchestrator_model['name'],
            'hardware_tier': manager.pc_profile.get('hardware_tier', 'unknown'),
            'recommended_models': manager._get_recommended_models_for_tier(manager.pc_profile.get('hardware_tier', 'budget'))
        })
        
    except Exception as e:
        log_error(f"Error getting orchestrator models: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@orchestrator_bp.route('/select', methods=['POST'])
@test_mode_login_required
@handle_api_errors
@log_execution_time
def select_orchestrator_model():
    """Select a new orchestrator model"""
    log_api_request(request.endpoint, request.method)
    
    try:
        data = request.get_json()
        if not data or 'model_name' not in data:
            return jsonify({'success': False, 'error': 'Model name is required'}), 400
        
        model_name = data['model_name']
        
        # Get manager and validate model
        manager = get_manager_model()
        available_models = manager.get_available_orchestrator_models()
        
        selected_model = None
        for model in available_models:
            if model['name'] == model_name:
                selected_model = model
                break
        
        if not selected_model:
            return jsonify({'success': False, 'error': 'Invalid model name'}), 400
        
        # Check if model is installed
        installed_models = [m['name'] for m in manager.model_manager.get_available_models()]
        if model_name not in installed_models:
            return jsonify({
                'success': False, 
                'error': 'Model not installed',
                'requires_installation': True,
                'model_info': selected_model
            }), 400
        
        # Update configuration
        try:
            setting = AppSetting.query.filter_by(key='manager_model_selected_orchestrator').first()
            if not setting:
                setting = AppSetting()
                setting.key = 'manager_model_selected_orchestrator'
                setting.value = json.dumps(model_name)
                db.session.add(setting)
            else:
                setting.value = json.dumps(model_name)
            db.session.commit()
            
            # Update manager instance
            manager.config['selected_orchestrator'] = model_name
            manager._orchestrator_model = None  # Force reload of orchestrator model
            _ = manager.orchestrator_model  # Trigger reload
            
            return jsonify({
                'success': True,
                'message': f'Orchestrator model changed to {selected_model["display_name"]}',
                'selected_model': selected_model,
                'restart_recommended': True
            })
            
        except Exception as e:
            db.session.rollback()
            raise e
            
    except Exception as e:
        log_error(f"Error selecting orchestrator model: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@orchestrator_bp.route('/recommendations', methods=['GET'])
@test_mode_login_required
@handle_api_errors
@log_execution_time
def get_personalized_recommendations():
    """Get personalized recommendations from orchestrator"""
    log_api_request(request.endpoint, request.method)
    
    try:
        manager = get_manager_model()
        recommendations = manager.get_personalized_recommendations()
        
        return jsonify({
            'success': True,
            'recommendations': recommendations,
            'user_profile': {
                'skill_level': manager._assess_skill_level(),
                'total_interactions': manager.user_profile.get('total_interactions', 0),
                'most_used_tasks': list(manager.user_profile.get('usage_patterns', {}).keys())[:5]
            },
            'hardware_profile': {
                'tier': manager.pc_profile.get('hardware_tier', 'unknown'),
                'ram_gb': manager.pc_profile.get('total_ram_gb', 0),
                'gpu': manager.pc_profile.get('gpu_available', 'none'),
                'concurrent_models': manager.pc_profile.get('max_concurrent_models', 1)
            }
        })
        
    except Exception as e:
        log_error(f"Error getting recommendations: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@orchestrator_bp.route('/model_info', methods=['POST'])
@test_mode_login_required
@handle_api_errors
@log_execution_time
def get_agentic_model_info():
    """Get agentic model information based on user query"""
    log_api_request(request.endpoint, request.method)
    
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'success': False, 'error': 'Query is required'}), 400
        
        query = data['query']
        manager = get_manager_model()
        
        # Use orchestrator to provide intelligent model information
        result = manager.manage_model_information_agentic(query)
        
        return jsonify(result)
        
    except Exception as e:
        log_error(f"Error getting agentic model info: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@orchestrator_bp.route('/interaction', methods=['POST'])
@test_mode_login_required
@handle_api_errors
@log_execution_time
def log_user_interaction():
    """Log user interaction for personalization"""
    log_api_request(request.endpoint, request.method)
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Interaction data is required'}), 400
        
        manager = get_manager_model()
        
        # Update user RAG with interaction data
        interaction_data = {
            'timestamp': datetime.now().isoformat(),
            'intent': data.get('intent'),
            'task_type': data.get('task_type'),
            'model_used': data.get('model_used'),
            'satisfaction': data.get('satisfaction', 'neutral'),
            'duration': data.get('duration', 0),
            'user_input': data.get('user_input', ''),
            'success': data.get('success', True)
        }
        
        manager.update_user_rag(interaction_data)
        
        return jsonify({
            'success': True,
            'message': 'Interaction logged for personalization',
            'updated_skill_level': manager._assess_skill_level()
        })
        
    except Exception as e:
        log_error(f"Error logging interaction: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@orchestrator_bp.route('/requirements_check', methods=['POST'])
@test_mode_login_required
@handle_api_errors
@log_execution_time
def check_requirements():
    """Trigger requirements check and auto-installation"""
    log_api_request(request.endpoint, request.method)
    
    try:
        manager = get_manager_model()
        
        # Force requirements check
        manager._check_and_install_requirements()
        
        # Get status of all components
        requirements_status = {
            'image_generation': _check_image_generation_status(),
            'video_generation': _check_video_generation_status(),
            'audio_processing': _check_audio_processing_status(),
            'llm_models': _check_llm_models_status()
        }
        
        return jsonify({
            'success': True,
            'message': 'Requirements check completed',
            'status': requirements_status,
            'auto_install_enabled': manager.config.get('auto_install_requirements', True)
        })
        
    except Exception as e:
        log_error(f"Error checking requirements: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@orchestrator_bp.route('/config', methods=['GET', 'POST'])
@test_mode_login_required
@handle_api_errors
@log_execution_time
def manage_orchestrator_config() -> Union[Response, tuple[Response, int]]:
    """Get or update orchestrator configuration"""
    log_api_request(request.endpoint, request.method)
    
    try:
        manager = get_manager_model()
        
        if request.method == 'GET':
            return jsonify({
                'success': True,
                'config': manager.config,
                'user_profile': manager.user_profile,
                'pc_profile': manager.pc_profile
            })
        
        elif request.method == 'POST':
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'Configuration data is required'}), 400
            
            # Update configuration
            updated_keys = []
            for key, value in data.items():
                if key in manager.config:
                    old_value = manager.config[key]
                    manager.config[key] = value
                    updated_keys.append(key)
                    
                    # Save to database
                    setting = AppSetting.query.filter_by(key=f'manager_model_{key}').first()
                    if not setting:
                        setting = AppSetting()
                        setting.key = f'manager_model_{key}'
                        setting.value = json.dumps(value)
                        db.session.add(setting)
                    else:
                        setting.value = json.dumps(value)
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'Updated configuration: {", ".join(updated_keys)}',
                'updated_config': {k: manager.config[k] for k in updated_keys}
            })
        
        else:
            return jsonify({'success': False, 'error': 'Method not allowed'}), 405
            
    except Exception as e:
        log_error(f"Error managing orchestrator config: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@orchestrator_bp.route('/integration_test', methods=['POST'])
@test_mode_login_required
@handle_api_errors
@log_execution_time
def run_integration_tests():
    """Run comprehensive integration tests to validate all features"""
    log_api_request(request.endpoint, request.method)
    
    try:
        from ..utils.integration_tests import run_integration_tests_sync
        
        # Run comprehensive tests
        results = run_integration_tests_sync()
        
        return jsonify({
            'success': results.get('success', False),
            'test_results': results.get('test_results', {}),
            'errors': results.get('errors', []),
            'warnings': results.get('warnings', []),
            'summary': results.get('summary', {}),
            'timestamp': datetime.now().isoformat(),
            'recommendations': _generate_integration_recommendations(results)
        })
        
    except Exception as e:
        log_error(f"Error running integration tests: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


def _generate_integration_recommendations(test_results: Dict[str, Any]) -> List[str]:
    """Generate recommendations based on integration test results"""
    recommendations = []
    
    summary = test_results.get('summary', {})
    errors = test_results.get('errors', [])
    warnings = test_results.get('warnings', [])
    
    # Success rate recommendations
    success_rate = summary.get('success_rate', 0)
    if success_rate < 70:
        recommendations.append("🚨 Critical: Many features are not working properly. Check installation and configuration.")
    elif success_rate < 90:
        recommendations.append("⚠️ Some features need attention. Review warnings and partial test results.")
    else:
        recommendations.append("✅ System is performing well! All critical features are working.")
    
    # Specific feature recommendations
    if any('image generation' in str(error).lower() for error in errors):
        recommendations.append("🎨 Install Stable Diffusion WebUI for image generation capabilities.")
    
    if any('video generation' in str(error).lower() for error in errors):
        recommendations.append("🎬 Install ComfyUI for video generation capabilities.")
    
    if any('audio' in str(error).lower() or 'tts' in str(error).lower() for error in errors):
        recommendations.append("🔊 Install audio dependencies for speech synthesis and transcription.")
    
    if any('model' in str(error).lower() for error in errors):
        recommendations.append("🤖 Download AI models through the Models Manager for full functionality.")
    
    # Performance recommendations
    if summary.get('failed_tests', 0) > 0:
        recommendations.append("🔧 Check the system logs for detailed error information and troubleshooting steps.")
    
    if len(warnings) > 3:
        recommendations.append("📋 Review warnings in the Orchestrator Settings for optimization opportunities.")
    
    return recommendations[:5]  # Limit to top 5 recommendations


def _check_image_generation_status() -> Dict[str, Any]:
    """Check image generation status"""
    try:
        from ..core.stable_diffusion_controller import StableDiffusionController
        sd_controller = StableDiffusionController()
        return {
            'installed': sd_controller.check_and_install(),
            'running': sd_controller.is_running(),
            'service': 'Stable Diffusion WebUI'
        }
    except Exception as e:
        return {
            'installed': False,
            'running': False,
            'error': str(e),
            'service': 'Stable Diffusion WebUI'
        }


def _check_video_generation_status() -> Dict[str, Any]:
    """Check video generation status"""
    try:
        from ..core.video_generator import VideoGeneratorController
        video_controller = VideoGeneratorController()
        status = video_controller.get_status()
        return {
            'installed': status.get('installed', False),
            'running': status.get('running', False),
            'service': 'ComfyUI Video Generator'
        }
    except Exception as e:
        return {
            'installed': False,
            'running': False,
            'error': str(e),
            'service': 'ComfyUI Video Generator'
        }


def _check_audio_processing_status() -> Dict[str, Any]:
    """Check audio processing status"""
    try:
        import edge_tts
        import speech_recognition
        return {
            'installed': True,
            'running': True,
            'service': 'Audio Processing (TTS + STT)'
        }
    except ImportError as e:
        return {
            'installed': False,
            'running': False,
            'error': str(e),
            'service': 'Audio Processing (TTS + STT)'
        }


def _check_llm_models_status() -> Dict[str, Any]:
    """Check LLM models status"""
    try:
        from ..utils.llm_model_manager import LLMModelManager
        model_manager = LLMModelManager()
        models = model_manager.get_available_models()
        return {
            'installed': len(models) > 0,
            'running': True,
            'count': len(models),
            'service': 'LLM Models'
        }
    except Exception as e:
        return {
            'installed': False,
            'running': False,
            'error': str(e),
            'service': 'LLM Models'
        }
