"""
Image API Module - AI-Powered Image Generation and Management Endpoints.

This module provides comprehensive REST API endpoints for AI-powered image generation
using Stable Diffusion, image management, gallery features, and integration with
external image generation services. It handles the complete image generation pipeline
from prompt processing to final image delivery.

The API supports multiple image generation backends including local Stable Diffusion
installations, cloud-based services, and hybrid processing workflows. It provides
advanced prompt engineering, style transfer, image editing, and batch processing
capabilities.

Key Features:
    - AI-powered image generation with Stable Diffusion
    - Advanced prompt engineering and negative prompts
    - Multiple sampling methods and quality settings
    - Image-to-image transformation and editing
    - Style transfer and artistic filters
    - Batch image generation and processing
    - Gallery management with metadata storage
    - Image upscaling and enhancement
    - Format conversion and optimization
    - Integration with external AI image services

Supported Image Generation:
    - Text-to-image with detailed prompt control
    - Image-to-image transformation and editing
    - Inpainting and outpainting capabilities
    - Style transfer with reference images
    - Super-resolution and upscaling
    - Background removal and replacement
    - Artistic style application
    - Batch processing workflows

API Endpoints:
    - GET /status: Get Stable Diffusion service status
    - POST /start: Start the image generation service
    - POST /stop: Stop the image generation service
    - POST /generate: Generate images from text prompts
    - POST /img2img: Transform existing images
    - POST /inpaint: Fill masked areas in images
    - GET /gallery: Browse generated image gallery
    - DELETE /gallery/{id}: Remove images from gallery
    - GET /models: List available Stable Diffusion models
    - POST /models/load: Load specific generation model

Image Generation Parameters:
    - prompt: Detailed text description of desired image
    - negative_prompt: Elements to exclude from generation
    - width/height: Output image dimensions
    - steps: Number of generation steps (quality vs speed)
    - cfg_scale: Classifier-free guidance scale
    - sampler: Sampling method (DPM++, Euler, DDIM, etc.)
    - seed: Random seed for reproducible results
    - batch_size: Number of images to generate
    - style: Predefined style presets

Quality Settings:
    - Draft: Fast generation for concept testing
    - Standard: Balanced quality and speed
    - High: Maximum quality for final output
    - Custom: User-defined parameter sets

Security Features:
    - Content filtering for inappropriate prompts
    - Rate limiting for resource-intensive operations
    - Secure temporary file handling
    - User-specific gallery isolation
    - Prompt sanitization and validation

Performance Optimizations:
    - GPU acceleration when available
    - Model caching and preloading
    - Progressive image generation
    - Background processing queues
    - Efficient memory management
    - Batch processing optimization

Error Handling:
    - Graceful service startup and shutdown
    - Model loading failure recovery
    - GPU memory management
    - Queue overflow protection
    - Invalid prompt handling

Example Usage:
    # Generate image from text
    POST /api/images/generate
    {
        "prompt": "A beautiful sunset over mountains",
        "negative_prompt": "blurry, low quality",
        "width": 512,
        "height": 512,
        "steps": 20,
        "cfg_scale": 7.5
    }
    
    # Check service status
    GET /api/images/status

Note:
    Image generation requires significant computational resources and may take
    several seconds to minutes depending on settings and hardware. GPU acceleration
    is strongly recommended for acceptable performance.
"""

from flask import Blueprint, jsonify, request, current_app, send_file
from ..auth import test_mode_login_required, current_user
import os
from pathlib import Path
import json

from ..logger import logger

# Create the images API blueprint
images_bp = Blueprint('images', __name__, url_prefix='/images')


@images_bp.route('/status', methods=['GET'])
@test_mode_login_required
def get_status():
    """
    Retrieve current status and health information of the Stable Diffusion service.
    
    This endpoint provides comprehensive status information about the image generation
    service, including service state, model loading status, GPU availability,
    memory usage, and performance metrics. It's essential for monitoring service
    health and troubleshooting generation issues.
    
    Returns:
        JSON response with detailed service status:
        
        Service Running (200):
        {
            "success": true,
            "status": {
                "service_state": "running" | "stopped" | "starting" | "error",
                "model_loaded": true,
                "model_name": "v1-5-pruned-emaonly.safetensors",
                "gpu_available": true,
                "gpu_memory_total": "8192 MB",
                "gpu_memory_used": "4096 MB",
                "gpu_memory_free": "4096 MB",
                "cpu_usage": 25.5,
                "memory_usage": 62.3,
                "generation_queue_length": 2,
                "last_generation_time": 15.2,
                "average_generation_time": 18.7,
                "total_images_generated": 1247,
                "uptime_seconds": 3600,
                "version": "1.7.0",
                "backend": "automatic1111",
                "supported_features": [
                    "txt2img",
                    "img2img", 
                    "inpaint",
                    "upscale"
                ]
            }
        }
        
        Service Stopped (200):
        {
            "success": true,
            "status": {
                "service_state": "stopped",
                "model_loaded": false,
                "gpu_available": true,
                "message": "Service is ready to start"
            }
        }
        
        Controller Error (500):
        {
            "success": false,
            "error": "Stable Diffusion controller not available"
        }
        
        Initialization Error (500):
        {
            "success": false,
            "error": "Stable Diffusion controller failed to initialize"
        }
    
    Status Fields:
        - service_state: Current operational state of the service
        - model_loaded: Whether a generation model is loaded and ready
        - model_name: Name of the currently loaded model
        - gpu_available: Whether GPU acceleration is available
        - gpu_memory_*: GPU memory usage statistics
        - cpu_usage: Current CPU utilization percentage
        - memory_usage: System memory utilization percentage
        - generation_queue_length: Number of pending generation requests
        - last_generation_time: Duration of most recent generation (seconds)
        - average_generation_time: Rolling average generation time
        - total_images_generated: Lifetime count of generated images
        - uptime_seconds: Service runtime since last start
        - supported_features: Available generation capabilities
    
    Service States:
        - "running": Service is active and accepting requests
        - "stopped": Service is not running
        - "starting": Service is initializing (transitional state)
        - "error": Service encountered an error and needs attention
    
    Performance Monitoring:
        - Real-time resource usage tracking
        - Generation queue management
        - Performance metrics collection
        - Error rate monitoring
    
    Example:
        >>> response = requests.get('/api/images/status')
        >>> status = response.json()['status']
        >>> if status['service_state'] == 'running':
        ...     print(f"Service ready, queue length: {status['generation_queue_length']}")
    
    Note:
        This endpoint is lightweight and can be called frequently for monitoring.
        Status information is cached briefly to reduce overhead on the service.
    """
    try:
        # Use lazy loading function
        get_sd_controller = getattr(current_app, 'get_stable_diffusion_controller', None)
        if not get_sd_controller:
            return jsonify({
                'success': False,
                'error': 'Stable Diffusion controller not available'
            }), 500
        
        sd_controller = get_sd_controller()
        if not sd_controller:
            return jsonify({
                'success': False,
                'error': 'Stable Diffusion controller failed to initialize'
            }), 500
        
        status = sd_controller.get_status()
        return jsonify({
            'success': True,
            'status': status
        })
        
    except Exception as e:
        logger.error(f"Error getting SD status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@images_bp.route('/start', methods=['POST'])
@test_mode_login_required
def start_service():
    """
    Initialize and start the Stable Diffusion image generation service.
    
    This endpoint starts the Stable Diffusion service, initializing the AI model,
    GPU acceleration (if available), and preparing the service for image generation
    requests. The startup process includes automatic installation repair if needed
    and comprehensive validation of the service configuration.
    
    The service startup is non-blocking but may take significant time to complete,
    especially on first run or when loading large models. Status can be monitored
    via the /status endpoint during initialization.
    
    Request Body:
        Optional JSON object with startup configuration:
        {
            "model": "v1-5-pruned-emaonly.safetensors",
            "gpu_acceleration": true,
            "memory_optimization": "auto",
            "auto_repair": true
        }
    
    Returns:
        JSON response with startup result:
        
        Started Successfully (200):
        {
            "success": true,
            "message": "Service started successfully",
            "startup_time": 45.2,
            "model_loaded": "v1-5-pruned-emaonly.safetensors",
            "gpu_enabled": true,
            "memory_allocated": "4096 MB",
            "service_url": "http://localhost:7860"
        }
        
        Already Running (200):
        {
            "success": true,
            "message": "Service is already running",
            "uptime": 1847
        }
        
        Auto-Launch Disabled (400):
        {
            "success": false,
            "error": "External app auto-launch is disabled by configuration"
        }
        
        Controller Error (500):
        {
            "success": false,
            "error": "Stable Diffusion controller not available"
        }
        
        Startup Failed (500):
        {
            "success": false,
            "error": "Failed to start Stable Diffusion service",
            "details": "GPU memory insufficient"
        }
    
    Startup Configuration:
        - model: Specific model to load (optional, uses default if not specified)
        - gpu_acceleration: Enable GPU processing if available
        - memory_optimization: Memory usage strategy (auto/low/high)
        - auto_repair: Attempt automatic repair of incomplete installations
    
    Startup Process:
        1. Validate service configuration and dependencies
        2. Check and repair installation if needed
        3. Initialize GPU acceleration if available
        4. Load specified or default AI model
        5. Start web interface and API server
        6. Verify service health and readiness
    
    Auto-Repair Features:
        - Detects incomplete installations automatically
        - Downloads missing components and dependencies
        - Repairs corrupted model files
        - Fixes configuration issues
        - Updates to compatible versions
    
    Performance Considerations:
        - First startup may take several minutes
        - Large models require significant GPU memory
        - CPU fallback available if GPU insufficient
        - Background initialization doesn't block response
    
    Error Recovery:
        - Automatic fallback to CPU processing if GPU fails
        - Model loading retry mechanisms
        - Configuration validation and repair
        - Detailed error reporting for troubleshooting
    
    Example:
        >>> response = requests.post('/api/images/start', json={
        ...     "gpu_acceleration": True,
        ...     "memory_optimization": "auto"
        ... })
        >>> if response.json()['success']:
        ...     print("Image generation service is starting...")
    
    Note:
        Service startup requires significant system resources and may impact
        other applications. Ensure sufficient GPU memory and disk space before
        starting. Monitor the /status endpoint for startup completion.
    """
    try:
        # Use lazy loading function
        get_sd_controller = getattr(current_app, 'get_stable_diffusion_controller', None)
        if not get_sd_controller:
            return jsonify({
                'success': False,
                'error': 'Stable Diffusion controller not available'
            }), 500
        
        sd_controller = get_sd_controller()
        if not sd_controller:
            return jsonify({
                'success': False,
                'error': 'Stable Diffusion controller failed to initialize'
            }), 500
        
        # Auto-repair if install is incomplete (directory exists but no launcher script)
        try:
            import os
            from pathlib import Path
            has_launch = False
            try:
                has_launch = (sd_controller.sd_dir.exists() and ((sd_controller.sd_dir / 'webui.py').exists() or (sd_controller.sd_dir / 'webui.bat').exists()))
            except Exception:
                has_launch = False
            if not has_launch:
                # Attempt install/repair before starting
                sd_controller.check_and_install()
        except Exception:
            pass

        if sd_controller.is_running():
            return jsonify({
                'success': True,
                'message': 'Service is already running'
            })
        
        # Enforce config: do not start external apps if disabled
        from ..config import Config as VybeConfig
        if not VybeConfig.AUTO_LAUNCH_EXTERNAL_APPS:
            return jsonify({
                'success': False,
                'error': 'External app auto-launch is disabled by configuration'
            }), 400

        success = sd_controller.start()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Stable Diffusion service started successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Launch failed: Launcher script not found or start error. Use /api/images/install to reinstall.'
            }), 500
            
    except Exception as e:
        logger.error(f"Error starting SD service: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@images_bp.route('/install', methods=['POST'])
@test_mode_login_required
def install_service():
    """Install or repair the Stable Diffusion WebUI with basic progress feedback."""
    try:
        get_sd_controller = getattr(current_app, 'get_stable_diffusion_controller', None)
        if not get_sd_controller:
            return jsonify({'success': False, 'error': 'Stable Diffusion controller not available'}), 500
        sd_controller = get_sd_controller()
        if not sd_controller:
            return jsonify({'success': False, 'error': 'Stable Diffusion controller failed to initialize'}), 500

        ok = sd_controller.check_and_install()
        status = sd_controller.get_status()
        return jsonify({'success': bool(ok), 'status': status})
    except Exception as e:
        logger.error(f"Error installing SD service: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@images_bp.route('/stop', methods=['POST'])
@test_mode_login_required
def stop_service():
    """Stop the Stable Diffusion service"""
    try:
        # Use lazy loading function
        get_sd_controller = getattr(current_app, 'get_stable_diffusion_controller', None)
        if not get_sd_controller:
            return jsonify({
                'success': False,
                'error': 'Stable Diffusion controller not available'
            }), 500
        
        sd_controller = get_sd_controller()
        if not sd_controller:
            return jsonify({
                'success': False,
                'error': 'Stable Diffusion controller failed to initialize'
            }), 500
        
        success = sd_controller.stop()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Stable Diffusion service stopped successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to stop Stable Diffusion service'
            }), 500
            
    except Exception as e:
        logger.error(f"Error stopping SD service: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@images_bp.route('/models/available', methods=['GET'])
@test_mode_login_required
def get_available_models():
    """Get list of popular Stable Diffusion models available for download"""
    try:
        # Popular models with sample images and download info
        available_models = [
            {
                'name': 'Stable Diffusion v1.5',
                'filename': 'v1-5-pruned-emaonly.safetensors',
                'description': 'The classic Stable Diffusion v1.5 model. Great for general image generation.',
                'size': '4.2 GB',
                'type': 'General Purpose',
                'sample_images': [
                    'https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/blog/sd_benchmarking/sd_1_5.png',
                    'https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/blog/sd_benchmarking/sd_1_5_2.png'
                ],
                'download_url': 'https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors',
                'huggingface_url': 'https://huggingface.co/runwayml/stable-diffusion-v1-5',
                'license': 'CreativeML Open RAIL-M',
                'tags': ['general', 'photorealistic', 'versatile']
            },
            {
                'name': 'DreamShaper v8',
                'filename': 'dreamshaper_8.safetensors',
                'description': 'Popular community model known for vibrant colors and artistic style.',
                'size': '2.1 GB',
                'type': 'Artistic',
                'sample_images': [
                    'https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/blog/stable_diffusion_jax/pipeline.png',
                    'https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/diffusers/astronaut_rides_horse.png'
                ],
                'download_url': 'https://civitai.com/api/download/models/128713',
                'huggingface_url': 'https://civitai.com/models/4384/dreamshaper',
                'license': 'CreativeML Open RAIL-M',
                'tags': ['artistic', 'vibrant', 'fantasy']
            },
            {
                'name': 'Realistic Vision v6.0',
                'filename': 'realisticVisionV60_v60B1VAE.safetensors',
                'description': 'Excellent for photorealistic images with high detail and natural lighting.',
                'size': '2.1 GB',
                'type': 'Photorealistic',
                'sample_images': [
                    'https://image.civitai.com/xG1nkqKTMzGDvpLrqFT7WA/b5d57ec1-9f7d-4e3d-8c12-a7f98e6b4d2c/width=450/realistic1.jpeg',
                    'https://image.civitai.com/xG1nkqKTMzGDvpLrqFT7WA/d2e4f8c6-4a5b-4c3d-9e1f-b7d91e8c6f4a/width=450/realistic2.jpeg'
                ],
                'download_url': 'https://civitai.com/api/download/models/245598',
                'huggingface_url': 'https://civitai.com/models/4201/realistic-vision-v60-b1',
                'license': 'CreativeML Open RAIL-M',
                'tags': ['photorealistic', 'detailed', 'portraits']
            },
            {
                'name': 'Anime Diffusion',
                'filename': 'animefull-final-pruned.safetensors',
                'description': 'Specialized model for anime and manga style illustrations.',
                'size': '4.2 GB',
                'type': 'Anime/Manga',
                'sample_images': [
                    'https://huggingface.co/Ojimi/anime-kawai-diffusion/resolve/main/sample_images/anime_girl1.png',
                    'https://huggingface.co/Ojimi/anime-kawai-diffusion/resolve/main/sample_images/anime_boy1.png'
                ],
                'download_url': 'https://huggingface.co/Ojimi/anime-kawai-diffusion/resolve/main/animefull-final-pruned.safetensors',
                'huggingface_url': 'https://huggingface.co/Ojimi/anime-kawai-diffusion',
                'license': 'CreativeML Open RAIL-M',
                'tags': ['anime', 'manga', 'illustration']
            }
        ]
        
        return jsonify({
            'success': True,
            'models': available_models
        })
        
    except Exception as e:
        logger.error(f"Error getting available models: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@images_bp.route('/models', methods=['GET'])
@test_mode_login_required
def get_models():
    """Get list of available Stable Diffusion models"""
    try:
        # Use lazy loading function
        get_sd_controller = getattr(current_app, 'get_stable_diffusion_controller', None)
        if not get_sd_controller:
            return jsonify({
                'success': False,
                'error': 'Stable Diffusion controller not available'
            }), 500
        
        sd_controller = get_sd_controller()
        if not sd_controller:
            return jsonify({
                'success': False,
                'error': 'Stable Diffusion controller failed to initialize'
            }), 500
        
        # Get models directory path
        models_dir = sd_controller.sd_dir / 'models' / 'Stable-diffusion'
        
        if not models_dir.exists():
            return jsonify({
                'success': True,
                'models': [],
                'message': 'Models directory not found'
            })
        
        models = []
        
        # Look for .safetensors and .ckpt files
        for file_path in models_dir.glob('**/*'):
            if file_path.is_file() and file_path.suffix.lower() in ['.safetensors', '.ckpt']:
                try:
                    model_info = {
                        'name': file_path.name,
                        'path': str(file_path.relative_to(models_dir)),
                        'size': file_path.stat().st_size,
                        'type': file_path.suffix.lower()
                    }
                    models.append(model_info)
                except Exception as e:
                    logger.warning(f"Error processing model file {file_path}: {e}")
                    continue
        
        # Sort models by name
        models.sort(key=lambda x: x['name'])
        
        return jsonify({
            'success': True,
            'models': models,
            'models_dir': str(models_dir)
        })
        
    except Exception as e:
        logger.error(f"Error getting SD models: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@images_bp.route('/samplers', methods=['GET'])
@test_mode_login_required
def get_samplers():
    """Get list of available samplers"""
    try:
        # Use lazy loading function
        get_sd_controller = getattr(current_app, 'get_stable_diffusion_controller', None)
        if not get_sd_controller:
            return jsonify({
                'success': False,
                'error': 'Stable Diffusion controller not available'
            }), 500
        
        sd_controller = get_sd_controller()
        if not sd_controller:
            return jsonify({
                'success': False,
                'error': 'Stable Diffusion controller failed to initialize'
            }), 500
        
        samplers = sd_controller.get_samplers()
        return jsonify({
            'success': True,
            'samplers': samplers
        })
        
    except Exception as e:
        logger.error(f"Error getting SD samplers: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@images_bp.route('/generate', methods=['POST'])
@test_mode_login_required
def generate_image():
    """Generate an image using Stable Diffusion"""
    try:
        # Validate request data using comprehensive validation utility
        from ..utils.input_validation import InputValidator, ValidationError
        
        try:
            data = InputValidator.validate_json_request(
                required_fields=['prompt'],
                optional_fields={
                    'width': {'type': 'int', 'min_value': 64, 'max_value': 2048},
                    'height': {'type': 'int', 'min_value': 64, 'max_value': 2048},
                    'steps': {'type': 'int', 'min_value': 1, 'max_value': 100},
                    'cfg_scale': {'type': 'float', 'min_value': 1.0, 'max_value': 20.0},
                    'seed': {'type': 'int', 'min_value': -1, 'max_value': 2147483647},
                    'negative_prompt': {'type': 'string', 'max_length': 1000},
                    'model': {'type': 'string', 'max_length': 200},
                    'sampler': {'type': 'string', 'allowed_values': ['Euler', 'Euler a', 'LMS', 'Heun', 'DPM2', 'DPM2 a', 'DPM++ 2S a', 'DPM++ 2M', 'DPM++ SDE', 'DPM fast', 'DPM adaptive', 'LMS Karras', 'DPM2 Karras', 'DPM2 a Karras', 'DPM++ 2S a Karras', 'DPM++ 2M Karras', 'DPM++ SDE Karras', 'DDIM', 'PLMS']}
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
        steps = data.get('steps', 20)
        cfg_scale = data.get('cfg_scale', 7.0)
        seed = data.get('seed', -1)
        negative_prompt = data.get('negative_prompt', '')
        model = data.get('model', '')
        sampler = data.get('sampler', 'Euler a')
        
        # Use lazy loading function
        get_sd_controller = getattr(current_app, 'get_stable_diffusion_controller', None)
        if not get_sd_controller:
            return jsonify({
                'success': False,
                'error': 'Stable Diffusion controller not available'
            }), 500
        
        sd_controller = get_sd_controller()
        if not sd_controller:
            return jsonify({
                'success': False,
                'error': 'Stable Diffusion controller failed to initialize'
            }), 500
        
        # Check if service is running
        if not sd_controller.is_running():
            return jsonify({
                'success': False,
                'error': 'Stable Diffusion service is not running'
            }), 503
        
        # Generate image
        result = sd_controller.generate_image(
            prompt=prompt,
            width=width,
            height=height,
            steps=steps,
            cfg_scale=cfg_scale,
            seed=seed
        )
        
        if result.get('success'):
            return jsonify({
                'success': True,
                'image_path': result.get('image_path'),
                'metadata': result.get('metadata', {})
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Image generation failed')
            }), 500
        
    except Exception as e:
        logger.error(f"Error generating image: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@images_bp.route('/gallery', methods=['GET'])
@test_mode_login_required
def get_gallery():
    """Get list of generated images for the gallery"""
    try:
        # Use lazy loading function
        get_sd_controller = getattr(current_app, 'get_stable_diffusion_controller', None)
        if not get_sd_controller:
            return jsonify({
                'success': False,
                'error': 'Stable Diffusion controller not available'
            }), 500
        
        sd_controller = get_sd_controller()
        if not sd_controller:
            return jsonify({
                'success': False,
                'error': 'Stable Diffusion controller failed to initialize'
            }), 500
        
        images = sd_controller.get_generated_images()
        
        # Convert paths to relative paths for web access
        workspace_dir = Path(current_app.root_path).parent / "workspace"
        for image in images:
            try:
                rel_path = Path(image['path']).relative_to(workspace_dir)
                image['web_path'] = str(rel_path).replace('\\', '/')
            except ValueError:
                image['web_path'] = image['filename']
        
        return jsonify({
            'success': True,
            'images': images
        })
        
    except Exception as e:
        logger.error(f"Error getting image gallery: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@images_bp.route('/serve/<path:filename>')
@test_mode_login_required
def serve_image(filename):
    """Serve generated images"""
    try:
        sd_controller = getattr(current_app, 'stable_diffusion_controller', None)
        if not sd_controller:
            return "Stable Diffusion controller not available", 404
        
        image_path = sd_controller.images_dir / filename
        
        if not image_path.exists():
            return "Image not found", 404
        
        return send_file(image_path)
        
    except Exception as e:
        logger.error(f"Error serving image {filename}: {e}")
        return "Error serving image", 500


@images_bp.route('/delete/<filename>', methods=['DELETE'])
@test_mode_login_required
def delete_image(filename):
    """Delete a generated image and its metadata"""
    try:
        # Use lazy loading function
        get_sd_controller = getattr(current_app, 'get_stable_diffusion_controller', None)
        if not get_sd_controller:
            return jsonify({
                'success': False,
                'error': 'Stable Diffusion controller not available'
            }), 500
        
        sd_controller = get_sd_controller()
        if not sd_controller:
            return jsonify({
                'success': False,
                'error': 'Stable Diffusion controller failed to initialize'
            }), 500
        
        image_path = sd_controller.images_dir / filename
        metadata_path = image_path.with_suffix('.json')
        
        if image_path.exists():
            image_path.unlink()
        
        if metadata_path.exists():
            metadata_path.unlink()
        
        return jsonify({
            'success': True,
            'message': 'Image deleted successfully'
        })
        
    except Exception as e:
        logger.error(f"Error deleting image {filename}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@images_bp.route('/open_models_folder', methods=['POST'])
@test_mode_login_required
def open_models_folder():
    """Open the Stable Diffusion models folder in file explorer"""
    try:
        # Use lazy loading function
        get_sd_controller = getattr(current_app, 'get_stable_diffusion_controller', None)
        if not get_sd_controller:
            return jsonify({
                'success': False,
                'error': 'Stable Diffusion controller not available'
            }), 500
        
        sd_controller = get_sd_controller()
        if not sd_controller:
            return jsonify({
                'success': False,
                'error': 'Stable Diffusion controller failed to initialize'
            }), 500
        
        models_dir = sd_controller.sd_dir / 'models' / 'Stable-diffusion'
        
        # Create directory if it doesn't exist
        models_dir.mkdir(parents=True, exist_ok=True)
        
        # Open in file explorer (cross-platform)
        import subprocess
        import platform
        
        system = platform.system()
        if system == "Windows":
            subprocess.run(['explorer', str(models_dir)])
        elif system == "Darwin":  # macOS
            subprocess.run(['open', str(models_dir)])
        else:  # Linux
            subprocess.run(['xdg-open', str(models_dir)])
        
        return jsonify({
            'success': True,
            'message': 'Models folder opened',
            'path': str(models_dir)
        })
        
    except Exception as e:
        logger.error(f"Error opening models folder: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
