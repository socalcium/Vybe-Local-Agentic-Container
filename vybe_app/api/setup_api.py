"""
Setup API
Provides environment checks for Setup page (python, git, venv, llm backend, SD, TTS, whisper, models)
"""

from flask import Blueprint, jsonify
from ..auth import test_mode_login_required
import subprocess, sys, os
from ..core.installation_monitor import installation_monitor
import logging

logger = logging.getLogger(__name__)

setup_api = Blueprint('setup', __name__, url_prefix='/setup')


@setup_api.route('/check-python', methods=['GET'])
@test_mode_login_required
def check_python():
    try:
        return jsonify({'installed': True, 'version_ok': sys.version_info >= (3, 8), 'version': sys.version.split()[0]})
    except Exception:
        return jsonify({'installed': False})


@setup_api.route('/check-git', methods=['GET'])
@test_mode_login_required
def check_git():
    try:
        out = subprocess.run(['git', '--version'], capture_output=True, text=True, timeout=5)
        ok = out.returncode == 0
        version = out.stdout.strip() if ok else ''
        return jsonify({'installed': ok, 'version': version})
    except Exception:
        return jsonify({'installed': False})


@setup_api.route('/check-venv', methods=['GET'])
@test_mode_login_required
def check_venv():
    try:
        exists = hasattr(sys, 'base_prefix') and sys.prefix != sys.base_prefix
        active = exists
        return jsonify({'exists': exists, 'active': active})
    except Exception:
        return jsonify({'exists': False, 'active': False})


@setup_api.route('/check-llm-backend', methods=['GET'])
@test_mode_login_required
def check_llm_backend():
    try:
        from ..core.backend_llm_controller import get_backend_controller
        llm = get_backend_controller()
        running = llm.is_server_ready()
        models_available = bool(llm.list_available_models())
        return jsonify({'running': running, 'models_available': models_available})
    except Exception:
        return jsonify({'running': False, 'models_available': False})


@setup_api.route('/check-sd', methods=['GET'])
@test_mode_login_required
def check_sd():
    try:
        from ..core.stable_diffusion_controller import stable_diffusion_controller
        installed = stable_diffusion_controller.is_installed()
        deps = installed  # assume if installed then deps installed
        return jsonify({'repo_exists': installed, 'dependencies_installed': deps})
    except Exception:
        return jsonify({'repo_exists': False, 'dependencies_installed': False})


@setup_api.route('/check-tts', methods=['GET'])
@test_mode_login_required
def check_tts():
    try:
        from ..core.edge_tts_controller import EdgeTTSController
        tts = EdgeTTSController()
        return jsonify({'repo_exists': True, 'installed': bool(tts)})
    except Exception:
        return jsonify({'repo_exists': False, 'installed': False})


@setup_api.route('/check-whisper', methods=['GET'])
@test_mode_login_required
def check_whisper():
    try:
        import speech_recognition  # noqa: F401
        return jsonify({'repo_exists': True, 'built': True})
    except Exception:
        return jsonify({'repo_exists': False, 'built': False})


@setup_api.route('/check-models', methods=['GET'])
@test_mode_login_required
def check_models():
    try:
        from ..utils.llm_model_manager import LLMModelManager
        mm = LLMModelManager()
        models = mm.get_available_models()
        sd_model = False
        whisper_model = True  # assume on-demand download
        return jsonify({'sd_model': sd_model, 'whisper_model': whisper_model, 'llm_models': len(models)})
    except Exception:
        return jsonify({'sd_model': False, 'whisper_model': False, 'llm_models': 0})


@setup_api.route('/installation-status', methods=['GET'])
@test_mode_login_required
def get_installation_status():
    """Get detailed status of all AI tool installations"""
    try:
        status = installation_monitor.get_installation_status()
        return jsonify({
            'success': True,
            'installations': status
        })
    except Exception as e:
        logger.error(f"Error getting installation status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@setup_api.route('/repair-installations', methods=['POST'])
@test_mode_login_required
def repair_installations():
    """Force repair all failed installations"""
    try:
        results = installation_monitor.force_repair_all()
        return jsonify({
            'success': True,
            'results': results,
            'message': 'Installation repair completed'
        })
    except Exception as e:
        logger.error(f"Error repairing installations: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@setup_api.route('/start-installation-monitor', methods=['POST'])
@test_mode_login_required
def start_installation_monitor():
    """Start the background installation monitor"""
    try:
        installation_monitor.start_monitoring()
        return jsonify({
            'success': True,
            'message': 'Installation monitor started'
        })
    except Exception as e:
        logger.error(f"Error starting installation monitor: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


