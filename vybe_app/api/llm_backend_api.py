"""
LLM Backend API - exposes configuration and recommendations for the local LLM server.
Allows the UI to view/update n_threads and n_ctx with a short "why" explanation based on
hardware manager data. Applies safe limits and restarts the backend if changes require it.
"""

from flask import Blueprint, jsonify, request
from ..auth import test_mode_login_required
from ..logger import log_api_request, log_error

llm_bp = Blueprint('llm', __name__, url_prefix='/llm')


def _build_recommendations():
    """Create hardware-based recommendations and explanations."""
    try:
        from ..core.hardware_manager import get_hardware_manager
        hw = get_hardware_manager()
        # Ensure hardware info present
        if not hw.hardware_info:
            hw.detect_hardware()
            hw.classify_performance_tier()

        cpu_phys = hw.hardware_info.get('cpu', {}).get('count', 1) or 1
        cpu_logical = hw.hardware_info.get('cpu', {}).get('count_logical', cpu_phys) or cpu_phys
        ram_total_gb = hw.hardware_info.get('memory', {}).get('total_gb', 8.0) or 8.0

        # Recommended threads: up to physical cores, but leave one core free
        recommended_threads = max(1, min(cpu_phys, cpu_logical - 1))

        # Recommended context: prefer 16k when RAM permits, else 8k
        # Simple heuristic: >= 12GB RAM -> 16k, else 8k
        recommended_ctx = 16384 if ram_total_gb >= 12 else 8192

        why = (
            f"Threads set to {recommended_threads} based on {cpu_phys} physical cores "
            f"(leaving one logical core free). Context set to {recommended_ctx} tokens based on "
            f"{ram_total_gb:.1f}GB RAM to avoid overflow while keeping quality."
        )

        caps = {
            'max_threads': max(1, cpu_logical),
            'min_threads': 1,
            'max_ctx': 131072,
            'min_ctx': 2048
        }

        return {
            'recommended_threads': recommended_threads,
            'recommended_ctx': recommended_ctx,
            'why': why,
            'caps': caps,
            'hardware': {
                'cpu_physical_cores': cpu_phys,
                'cpu_logical_cores': cpu_logical,
                'ram_total_gb': ram_total_gb,
                'tier': hw.performance_tier
            }
        }
    except Exception as e:
        return {
            'recommended_threads': 2,
            'recommended_ctx': 16384,
            'why': f"Using fallback recommendations due to error: {e}",
            'caps': {'max_threads': 8, 'min_threads': 1, 'max_ctx': 131072, 'min_ctx': 2048},
            'hardware': {}
        }


@llm_bp.route('/config', methods=['GET'])
@test_mode_login_required
def get_llm_config():
    """Get current LLM backend configuration and recommendations."""
    log_api_request(request.endpoint, request.method)
    try:
        from ..core.backend_llm_controller import get_backend_controller
        controller = get_backend_controller()

        rec = _build_recommendations()
        return jsonify({
            'success': True,
            'config': {
                'n_threads': getattr(controller, 'n_threads', None),
                'n_ctx': getattr(controller, 'n_ctx', None),
                'server_url': getattr(controller, 'server_url', None)
            },
            'recommendations': rec
        })
    except Exception as e:
        log_error(f"LLM config error: {e}")
        return jsonify({'success': False, 'error': 'Failed to get LLM config'}), 500


@llm_bp.route('/ready', methods=['GET'])
@test_mode_login_required
def llm_ready():
    """Lightweight readiness endpoint for the desktop loader/UI."""
    try:
        import requests as _rq
        ok = False
        try:
            r = _rq.get('http://127.0.0.1:11435/v1/models', timeout=2)
            ok = (r.status_code == 200)
        except Exception:
            ok = False
        return jsonify({'success': True, 'ready': ok})
    except Exception as e:
        log_error(f"LLM ready check error: {e}")
        return jsonify({'success': False, 'ready': False}), 200


@llm_bp.route('/config', methods=['POST'])
@test_mode_login_required
def set_llm_config():
    """Update LLM backend configuration. Will restart backend if running."""
    log_api_request(request.endpoint, request.method)
    try:
        data = request.get_json() or {}
        n_threads = data.get('n_threads')
        n_ctx = data.get('n_ctx')

        from ..core.backend_llm_controller import get_backend_controller
        controller = get_backend_controller()

        rec = _build_recommendations()
        caps = rec.get('caps', {})
        max_threads = caps.get('max_threads', 8)
        min_threads = caps.get('min_threads', 1)
        max_ctx = caps.get('max_ctx', 131072)
        min_ctx = caps.get('min_ctx', 2048)

        changed = False
        if isinstance(n_threads, int):
            safe_threads = max(min_threads, min(n_threads, max_threads))
            controller.n_threads = safe_threads
            changed = True
        if isinstance(n_ctx, int):
            safe_ctx = max(min_ctx, min(n_ctx, max_ctx))
            controller.n_ctx = safe_ctx
            changed = True

        restarted = False
        if changed:
            try:
                # If server is running, restart to apply new settings
                if controller.is_server_ready():
                    controller.stop_server()
                    restarted = controller.start_server()
                else:
                    # Not running; next start will honor config
                    restarted = False
            except Exception as e:
                log_error(f"Failed to restart LLM backend: {e}")

        return jsonify({
            'success': True,
            'restarted': restarted,
            'config': {
                'n_threads': controller.n_threads,
                'n_ctx': controller.n_ctx
            },
            'recommendations': rec
        })
    except Exception as e:
        log_error(f"LLM config update error: {e}")
        return jsonify({'success': False, 'error': 'Failed to update LLM config'}), 500


@llm_bp.route('/restart', methods=['POST'])
@test_mode_login_required
def restart_llm_backend():
    """Restart the LLM backend with new configuration."""
    log_api_request(request.endpoint, request.method)
    try:
        # Check for conflicts - prevent multiple restarts
        from ..core.backend_llm_controller import get_backend_controller
        controller = get_backend_controller()
        
        # Check if backend is currently restarting
        if hasattr(controller, '_restarting') and controller._restarting:
            return jsonify({
                'success': False,
                'error': 'Backend restart already in progress'
            }), 409  # Conflict status
        
        # Check if backend is starting up
        if hasattr(controller, '_starting') and controller._starting:
            return jsonify({
                'success': False,
                'error': 'Backend is currently starting up'
            }), 409
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data is required'}), 400
        
        # Validate configuration parameters
        try:
            n_threads = int(data.get('n_threads', controller.n_threads))
            n_ctx = int(data.get('n_ctx', controller.n_ctx))
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid numeric parameters'}), 400
        
        # Get hardware recommendations for validation
        rec = _build_recommendations()
        caps = rec.get('caps', {})
        
        # Validate against hardware limits
        if n_threads < caps.get('min_threads', 1) or n_threads > caps.get('max_threads', 8):
            return jsonify({
                'error': f'Thread count must be between {caps.get("min_threads", 1)} and {caps.get("max_threads", 8)}'
            }), 400
        
        if n_ctx < caps.get('min_ctx', 2048) or n_ctx > caps.get('max_ctx', 131072):
            return jsonify({
                'error': f'Context size must be between {caps.get("min_ctx", 2048)} and {caps.get("max_ctx", 131072)}'
            }), 400
        
        # Set restart flag to prevent conflicts
        controller._restarting = True
        
        try:
            # Stop current backend
            if controller.is_running:
                controller.stop_server()
            
            # Update configuration
            controller.n_threads = n_threads
            controller.n_ctx = n_ctx
            
            # Start backend with new configuration
            success = controller.start_server()
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'Backend restarted successfully',
                    'config': {
                        'n_threads': n_threads,
                        'n_ctx': n_ctx
                    }
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to restart backend'
                }), 500
                
        finally:
            # Clear restart flag
            controller._restarting = False
        
    except Exception as e:
        log_error(f"LLM restart error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


