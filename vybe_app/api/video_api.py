"""
Video API endpoints for Vybe application.
Handles video generation using ComfyUI integration.
"""

from flask import Blueprint, jsonify, request, current_app, send_file
from ..auth import test_mode_login_required, current_user
import os
from pathlib import Path
import time
from werkzeug.utils import secure_filename

from ..logger import logger

# Create the video API blueprint
video_bp = Blueprint('video', __name__, url_prefix='/video')


@video_bp.route('/status', methods=['GET'])
@test_mode_login_required
def get_video_status():
    """Get the status of the video generation service"""
    try:
        video_controller = getattr(current_app, 'video_controller', None)
        if not video_controller:
            return jsonify({
                'success': False,
                'error': 'Video controller not available'
            }), 500
        
        status = video_controller.get_status()
        return jsonify({
            'success': True,
            'status': status
        })
        
    except Exception as e:
        logger.error(f"Error getting video status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@video_bp.route('/start', methods=['POST'])
@test_mode_login_required
def start_video_service():
    """Start the ComfyUI video generation service"""
    try:
        video_controller = getattr(current_app, 'video_controller', None)
        if not video_controller:
            return jsonify({
                'success': False,
                'error': 'Video controller not available'
            }), 500
        
        # Auto-repair if install is incomplete (directory exists but incomplete setup)
        try:
            status = video_controller.get_status()
            if status.get('status') == 'stopped' and status.get('installation_incomplete'):
                # Attempt install/repair before starting
                video_controller.check_and_install()
        except Exception:
            pass
        
        success, message = video_controller.start()
        return jsonify({
            'success': success,
            'message': message if success else f'Launch failed: {message}. Try reinstalling from the Video Portal.'
        })
        
    except Exception as e:
        logger.error(f"Error starting video service: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to fetch: {str(e)}'
        }), 500


@video_bp.route('/stop', methods=['POST'])
@test_mode_login_required
def stop_video_service():
    """Stop the ComfyUI video generation service"""
    try:
        video_controller = getattr(current_app, 'video_controller', None)
        if not video_controller:
            return jsonify({
                'success': False,
                'error': 'Video controller not available'
            }), 500
        
        success, message = video_controller.stop()
        return jsonify({
            'success': success,
            'message': message
        })
        
    except Exception as e:
        logger.error(f"Error stopping video service: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@video_bp.route('/generate', methods=['POST'])
@test_mode_login_required
def generate_video():
    """Generate a video using ComfyUI"""
    try:
        # Validate request data
        from ..utils.input_validation import InputValidator, ValidationError
        
        try:
            data = InputValidator.validate_json_request(
                required_fields=['prompt'],
                optional_fields={
                    'width': {'type': 'int', 'min_value': 64, 'max_value': 2048},
                    'height': {'type': 'int', 'min_value': 64, 'max_value': 2048},
                    'frames': {'type': 'int', 'min_value': 1, 'max_value': 100},
                    'fps': {'type': 'int', 'min_value': 1, 'max_value': 60},
                    'model': {'type': 'string', 'allowed_values': ['svd', 'svd_xt', 'svd_xt_turbo']},
                    'seed': {'type': 'int', 'min_value': 0, 'max_value': 2147483647},
                    'guidance_scale': {'type': 'float', 'min_value': 0.1, 'max_value': 20.0},
                    'motion_bucket_id': {'type': 'int', 'min_value': 1, 'max_value': 255},
                    'negative_prompt': {'type': 'string', 'max_length': 1000},
                    'batch_size': {'type': 'int', 'min_value': 1, 'max_value': 4},
                    'quality': {'type': 'string', 'allowed_values': ['standard', 'high', 'ultra']},
                    'style': {'type': 'string', 'allowed_values': ['realistic', 'artistic', 'cinematic']}
                }
            )
        except ValidationError as e:
            return jsonify({
                "status": "error",
                "message": f"Invalid request data: {str(e)}"
            }), 400
        
        # Extract validated parameters
        prompt = data['prompt'].strip()
        width = data.get('width', 512)
        height = data.get('height', 512)
        frames = data.get('frames', 16)
        fps = data.get('fps', 8)
        model = data.get('model', 'svd')
        seed = data.get('seed')
        guidance_scale = data.get('guidance_scale', 7.5)
        motion_bucket_id = data.get('motion_bucket_id', 127)
        negative_prompt = data.get('negative_prompt', '')
        batch_size = data.get('batch_size', 1)
        quality = data.get('quality', 'standard')
        style = data.get('style', 'realistic')
        
        if len(prompt) > 1000:
            return jsonify({
                'success': False,
                'error': 'Prompt too long (max 1000 characters)'
            }), 400
        
        # Validate dimensions
        if width < 256 or width > 2048 or height < 256 or height > 2048:
            return jsonify({
                'success': False,
                'error': 'Invalid dimensions (256-2048 pixels)'
            }), 400
        
        # Validate frames and FPS
        if frames < 1 or frames > 64:
            return jsonify({
                'success': False,
                'error': 'Invalid frame count (1-64)'
            }), 400
        
        if fps < 1 or fps > 30:
            return jsonify({
                'success': False,
                'error': 'Invalid FPS (1-30)'
            }), 400
        
        # Validate advanced parameters
        if seed is not None and (seed < 0 or seed > 2147483647):
            return jsonify({
                'success': False,
                'error': 'Invalid seed value'
            }), 400
        
        if guidance_scale < 1.0 or guidance_scale > 20.0:
            return jsonify({
                'success': False,
                'error': 'Invalid guidance scale (1.0-20.0)'
            }), 400
        
        if motion_bucket_id < 1 or motion_bucket_id > 255:
            return jsonify({
                'success': False,
                'error': 'Invalid motion bucket ID (1-255)'
            }), 400
        
        if len(negative_prompt) > 500:
            return jsonify({
                'success': False,
                'error': 'Negative prompt too long (max 500 characters)'
            }), 400
        
        if batch_size < 1 or batch_size > 4:
            return jsonify({
                'success': False,
                'error': 'Invalid batch size (1-4)'
            }), 400
        
        # Get video controller
        video_controller = getattr(current_app, 'video_controller', None)
        if not video_controller:
            return jsonify({
                'success': False,
                'error': 'Video controller not available'
            }), 500
        
        # Check if service is running
        status = video_controller.get_status()
        if status.get('status') != 'running':
            return jsonify({
                'success': False,
                'error': 'Video service is not running'
            }), 400
        
        # Prepare generation parameters
        generation_params = {
            'prompt': prompt,
            'width': width,
            'height': height,
            'frames': frames,
            'fps': fps,
            'model': model,
            'guidance_scale': guidance_scale,
            'motion_bucket_id': motion_bucket_id,
            'negative_prompt': negative_prompt,
            'batch_size': batch_size,
            'quality': quality,
            'style': style
        }
        
        if seed is not None:
            generation_params['seed'] = seed
        
        # Start video generation
        job_id = video_controller.generate_video(generation_params)
        
        if job_id:
            return jsonify({
                'success': True,
                'message': 'Video generation started successfully',
                'job_id': job_id,
                'parameters': generation_params
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to start video generation'
            }), 500
        
    except Exception as e:
        logger.error(f"Error generating video: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@video_bp.route('/generate-batch', methods=['POST'])
@test_mode_login_required
def generate_batch_videos():
    """Generate multiple videos in batch"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        prompts = data.get('prompts', [])
        base_settings = data.get('base_settings', {})
        
        # Validate prompts
        if not prompts or not isinstance(prompts, list):
            return jsonify({
                'success': False,
                'error': 'Prompts list is required'
            }), 400
        
        if len(prompts) > 10:
            return jsonify({
                'success': False,
                'error': 'Maximum 10 prompts allowed for batch generation'
            }), 400
        
        # Validate each prompt
        for i, prompt in enumerate(prompts):
            if not prompt.strip():
                return jsonify({
                    'success': False,
                    'error': f'Prompt {i + 1} is empty'
                }), 400
            
            if len(prompt) > 1000:
                return jsonify({
                    'success': False,
                    'error': f'Prompt {i + 1} too long (max 1000 characters)'
                }), 400
        
        # Get video controller
        video_controller = getattr(current_app, 'video_controller', None)
        if not video_controller:
            return jsonify({
                'success': False,
                'error': 'Video controller not available'
            }), 500
        
        # Check if service is running
        status = video_controller.get_status()
        if status.get('status') != 'running':
            return jsonify({
                'success': False,
                'error': 'Video service is not running'
            }), 400
        
        # Start batch generation
        job_ids = []
        for prompt in prompts:
            generation_params = {
                'prompt': prompt,
                'width': base_settings.get('width', 512),
                'height': base_settings.get('height', 512),
                'frames': base_settings.get('frames', 16),
                'fps': base_settings.get('fps', 8),
                'model': base_settings.get('model', 'svd'),
                'guidance_scale': base_settings.get('guidance_scale', 7.5),
                'motion_bucket_id': base_settings.get('motion_bucket_id', 127),
                'negative_prompt': base_settings.get('negative_prompt', ''),
                'batch_size': base_settings.get('batch_size', 1),
                'quality': base_settings.get('quality', 'standard'),
                'style': base_settings.get('style', 'realistic')
            }
            
            if 'seed' in base_settings:
                generation_params['seed'] = base_settings['seed']
            
            job_id = video_controller.generate_video(generation_params)
            if job_id:
                job_ids.append(job_id)
        
        if job_ids:
            return jsonify({
                'success': True,
                'message': f'Batch generation started: {len(job_ids)} videos queued',
                'job_ids': job_ids,
                'total_prompts': len(prompts)
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to start batch generation'
            }), 500
        
    except Exception as e:
        logger.error(f"Error generating batch videos: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@video_bp.route('/models', methods=['GET'])
@test_mode_login_required
def get_available_models():
    """Get list of available video generation models"""
    try:
        video_controller = getattr(current_app, 'video_controller', None)
        if not video_controller:
            return jsonify({
                'success': False,
                'error': 'Video controller not available'
            }), 500
        
        models = video_controller.get_available_models()
        return jsonify({
            'success': True,
            'models': models
        })
        
    except Exception as e:
        logger.error(f"Error getting video models: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@video_bp.route('/settings', methods=['GET'])
@test_mode_login_required
def get_video_settings():
    """Get available video generation settings and presets"""
    try:
        settings = {
            'models': [
                {'id': 'svd', 'name': 'Stable Video Diffusion', 'description': 'High-quality video generation'},
                {'id': 'svd_xt', 'name': 'SVD XT', 'description': 'Extended version with more frames'},
                {'id': 'svd_xt_turbo', 'name': 'SVD XT Turbo', 'description': 'Fast generation with good quality'}
            ],
            'qualities': [
                {'id': 'fast', 'name': 'Fast', 'description': 'Quick generation, lower quality'},
                {'id': 'standard', 'name': 'Standard', 'description': 'Balanced speed and quality'},
                {'id': 'high', 'name': 'High', 'description': 'Slower generation, higher quality'}
            ],
            'styles': [
                {'id': 'realistic', 'name': 'Realistic', 'description': 'Photorealistic videos'},
                {'id': 'artistic', 'name': 'Artistic', 'description': 'Creative and stylized videos'},
                {'id': 'cinematic', 'name': 'Cinematic', 'description': 'Movie-like quality videos'}
            ],
            'defaults': {
                'width': 512,
                'height': 512,
                'frames': 16,
                'fps': 8,
                'guidance_scale': 7.5,
                'motion_bucket_id': 127,
                'batch_size': 1
            },
            'limits': {
                'width': {'min': 256, 'max': 2048},
                'height': {'min': 256, 'max': 2048},
                'frames': {'min': 1, 'max': 64},
                'fps': {'min': 1, 'max': 30},
                'guidance_scale': {'min': 1.0, 'max': 20.0},
                'motion_bucket_id': {'min': 1, 'max': 255},
                'batch_size': {'min': 1, 'max': 4},
                'prompt_length': {'max': 1000},
                'negative_prompt_length': {'max': 500},
                'batch_prompts': {'max': 10}
            }
        }
        
        return jsonify({
            'success': True,
            'settings': settings
        })
        
    except Exception as e:
        logger.error(f"Error getting video settings: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@video_bp.route('/gallery', methods=['GET'])
@test_mode_login_required
def get_video_gallery():
    """Get list of generated videos"""
    try:
        video_controller = getattr(current_app, 'video_controller', None)
        if not video_controller:
            return jsonify({
                'success': False,
                'error': 'Video controller not available'
            }), 500
        
        videos = video_controller.get_generated_videos()
        return jsonify({
            'success': True,
            'videos': videos,
            'total_count': len(videos)
        })
        
    except Exception as e:
        logger.error(f"Error getting video gallery: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@video_bp.route('/serve/<filename>')
@test_mode_login_required
def serve_video(filename):
    """Serve generated video files"""
    try:
        video_controller = getattr(current_app, 'video_controller', None)
        if not video_controller:
            return jsonify({'error': 'Video controller not available'}), 500
        
        # Security check - only serve files from the outputs directory
        safe_filename = secure_filename(filename)
        
        outputs_dir = video_controller.outputs_dir
        file_path = outputs_dir / safe_filename
        
        if not file_path.exists() or not file_path.is_file():
            return jsonify({'error': 'File not found'}), 404
        
        # Additional security - ensure file is within the outputs directory
        try:
            file_path.resolve().relative_to(outputs_dir.resolve())
        except ValueError:
            return jsonify({'error': 'Access denied'}), 403
        
        return send_file(file_path, as_attachment=True, download_name=filename)
        
    except Exception as e:
        logger.error(f"Error serving video file: {e}")
        return jsonify({'error': 'Failed to serve file'}), 500


@video_bp.route('/setup', methods=['GET'])
@test_mode_login_required
def get_setup_info():
    """Get video generation setup information"""
    try:
        video_controller = getattr(current_app, 'video_controller', None)
        if not video_controller:
            return jsonify({
                'success': False,
                'error': 'Video controller not available'
            }), 500
        
        setup_info = {
            'title': 'ComfyUI Video Generation Setup',
            'description': 'Advanced text-to-video generation powered by ComfyUI',
            'requirements': [
                'Python 3.8+ with pip',
                'Git for repository cloning',
                'At least 4GB free disk space',
                'Internet connection for model downloads'
            ],
            'steps': [
                {
                    'title': 'Clone ComfyUI Repository',
                    'description': 'Download the ComfyUI codebase from GitHub',
                    'status': 'automatic'
                },
                {
                    'title': 'Install Dependencies',
                    'description': 'Install required Python packages',
                    'status': 'automatic'
                },
                {
                    'title': 'Download Video Models',
                    'description': 'Download Stable Video Diffusion and AnimateDiff models',
                    'status': 'automatic'
                },
                {
                    'title': 'Start ComfyUI Server',
                    'description': 'Launch the ComfyUI backend service',
                    'status': 'manual'
                }
            ],
            'notes': [
                'Initial setup may take 10-20 minutes depending on your internet connection',
                'Video models are large files (2-4GB each)',
                'Generation time varies based on complexity and hardware',
                'CPU mode is used for compatibility, GPU mode available with proper setup'
            ]
        }
        
        return jsonify({
            'success': True,
            'setup_info': setup_info
        })
        
    except Exception as e:
        logger.error(f"Error getting setup info: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@video_bp.route('/install', methods=['POST'])
@test_mode_login_required
def install_video_service():
    """Install and setup the video generation service"""
    try:
        video_controller = getattr(current_app, 'video_controller', None)
        job_manager = getattr(current_app, 'job_manager', None)
        
        if not video_controller:
            return jsonify({
                'success': False,
                'error': 'Video controller not available'
            }), 500
        
        if not job_manager:
            return jsonify({
                'success': False,
                'error': 'Job manager not available'
            }), 500
        
        # Use JobManager for background installation
        job_manager.add_job(video_controller.check_and_install)
        
        return jsonify({
            'success': True,
            'message': 'Video generation installation started in background',
            'job_status': 'queued'
        })
        
    except Exception as e:
        logger.error(f"Error installing video service: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
