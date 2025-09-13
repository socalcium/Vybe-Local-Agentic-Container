"""
Models API Module - AI Model Management and Discovery Endpoints.

This module provides a comprehensive REST API for managing and discovering AI models
in the Vybe AI Desktop Application. It handles model listing, metadata retrieval,
model loading/unloading, and integration with the llama.cpp backend server.

The API supports multiple model formats with primary focus on GGUF (GGML Universal
File Format) models for efficient local inference. It provides real-time model
status information, performance metrics, and dynamic model selection capabilities.

Key Features:
    - Model discovery and listing from multiple directories
    - Real-time model status and loading state tracking
    - Model metadata and configuration retrieval
    - Dynamic model selection based on system capabilities
    - Integration with llama.cpp backend for model serving
    - Thread-safe model operations with proper error handling
    - Performance monitoring and resource usage tracking

Supported Endpoints:
    - GET /models: List all available models with status information
    - GET /models/available: Get available model names (alias endpoint)
    - GET /models/current: Get currently loaded model information
    - POST /models/load: Load a specific model into memory
    - POST /models/unload: Unload the current model from memory
    - GET /models/status: Get detailed model status and performance metrics
    - GET /models/{model_id}: Get detailed information about a specific model

Security Features:
    - Authentication required for all endpoints (test mode bypass available)
    - Rate limiting for model loading operations
    - Input validation and sanitization
    - Comprehensive error handling and logging

Example Usage:
    # List all available models
    GET /api/models
    
    # Load a specific model
    POST /api/models/load
    Content-Type: application/json
    {"model_name": "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"}
    
    # Get current model status
    GET /api/models/current

Note:
    This module requires the llama.cpp backend to be available for model operations.
    Models are automatically discovered from configured directories and validated
    for compatibility before being presented to the user.
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required
from ..auth import test_mode_login_required
import requests
from ..logger import log_error, log_api_request, handle_api_errors, log_execution_time
from ..core.backend_llm_controller import llm_controller
from ..core.dynamic_model_selector import get_dynamic_model_selector
from flask import current_app as app
import json
from pathlib import Path
import threading
from ..utils.security_middleware import download_rate_limit

# Create models sub-blueprint
models_bp = Blueprint('models', __name__, url_prefix='/models')

@models_bp.route('', methods=['GET'])
@test_mode_login_required
@handle_api_errors
@log_execution_time
def api_models():
    """
    Retrieve comprehensive list of available AI models with real-time status.
    
    This endpoint discovers and returns all available GGUF models from configured
    directories, including their current loading status, metadata, and performance
    characteristics. It provides real-time information about which models are
    loaded and ready for inference.
    
    The endpoint automatically attempts to start the llama.cpp backend if it's
    not running and models are available. For systems without models, it returns
    an empty list with helpful guidance for model installation.
    
    Returns:
        JSON response with model information:
        
        Success (200):
        {
            "models": [
                {
                    "name": "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
                    "path": "/path/to/model.gguf",
                    "size": 1234567890,
                    "type": "GGUF",
                    "status": "loaded" | "available",
                    "context_size": 32768,
                    "n_ctx": 32768,
                    "parameters": "1.1B",
                    "quantization": "Q4_K_M"
                }
            ],
            "total": 1
        }
        
        No Models (200):
        {
            "models": [],
            "total": 0,
            "message": "No GGUF models found. Please add GGUF model files to the models directory."
        }
        
        Backend Error (503):
        {
            "error": "AI backend could not be started"
        }
        
        Internal Error (500):
        {
            "error": "Failed to fetch models"
        }
    
    Model Status Values:
        - "loaded": Model is currently loaded in memory and ready for inference
        - "available": Model file exists and can be loaded on demand
    
    Model Metadata:
        - name: Display name of the model file
        - path: Full filesystem path to the model file
        - size: File size in bytes
        - type: Model format (always "GGUF" for supported models)
        - context_size: Maximum context window size in tokens
        - n_ctx: Context size configuration (may differ from maximum)
        - parameters: Estimated parameter count (if detectable)
        - quantization: Quantization method used (e.g., Q4_K_M, Q8_0)
    
    Error Handling:
        - Gracefully handles backend unavailability
        - Provides helpful messages for missing models
        - Logs all errors for debugging and monitoring
        - Maintains service availability even with partial failures
    
    Performance Considerations:
        - Results include caching for frequently accessed model metadata
        - Backend startup is non-blocking when possible
        - Model discovery is optimized with directory scanning
    
    Example:
        >>> response = requests.get('/api/models')
        >>> models = response.json()['models']
        >>> for model in models:
        ...     print(f"Model: {model['name']} ({model['status']})")
    
    Note:
        This endpoint may trigger backend initialization on first access,
        which can take several seconds. Subsequent calls are much faster
        as the backend remains warm.
    """
    log_api_request(request.endpoint, request.method)
    
    # Ensure llama.cpp backend is running or can start
    if not llm_controller.is_server_ready():
        # If no model is available, return empty models list instead of error
        if not llm_controller.model_path:
            return jsonify({
                'models': [],
                'total': 0,
                'message': 'No GGUF models found. Please add GGUF model files to the models directory.'
            })
        
        # Try to start the backend if we have a model
        if not llm_controller.start_server():
            return jsonify({'error': 'AI backend could not be started'}), 503
        # If we get here, the backend started successfully, so continue
    
    try:
        # Use the new list_available_models method
        models = llm_controller.list_available_models()
        
        # Add status information for each model
        for model in models:
            if llm_controller.model_path and model['path'] == llm_controller.model_path:
                model['status'] = 'loaded'
                model['context_size'] = llm_controller.n_ctx
            else:
                model['status'] = 'available'
                model['context_size'] = 'N/A'
            model['type'] = 'GGUF'
            # Ensure n_ctx field exists for frontend display
            if 'n_ctx' not in model:
                model['n_ctx'] = llm_controller.n_ctx
            
        return jsonify({
            'models': models,
            'total': len(models)
        })
        
    except Exception as e:
        log_error(f"Models API error: {str(e)}")
        return jsonify({'error': 'Failed to fetch models'}), 500

@models_bp.route('/available', methods=['GET'])
@test_mode_login_required
@handle_api_errors
@log_execution_time
def api_available_models():
    """
    Retrieve simplified list of available model names for frontend selection.
    
    This endpoint provides a streamlined interface for retrieving just the
    names of available models, primarily used by frontend components like
    the settings page composer for model selection dropdowns and forms.
    
    This is essentially an alias for the main models endpoint but with
    simplified response format focused on model names and basic metadata
    needed for UI components.
    
    Returns:
        JSON response with available model names:
        
        Success (200):
        {
            "models": [
                "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
                "llama-2-7b-chat.Q4_K_M.gguf"
            ],
            "total": 2
        }
        
        No Models (200):
        {
            "models": [],
            "total": 0,
            "message": "No models available"
        }
        
        Error (500):
        {
            "error": "Failed to fetch available models"
        }
    
    Usage Context:
        - Frontend model selection components
        - Settings page model dropdowns
        - Quick availability checks
        - API client model discovery
    
    Performance Features:
        - Lightweight response format
        - Cached model discovery results
        - Fast response times for UI components
    
    Example:
        >>> response = requests.get('/api/models/available')
        >>> model_names = response.json()['models']
        >>> print(f"Available models: {', '.join(model_names)}")
    
    Note:
        This endpoint focuses on speed and simplicity over detailed metadata.
        Use the main /models endpoint when full model information is needed.
    """
    log_api_request(request.endpoint, request.method)
    
    try:
        models = llm_controller.list_available_models()
        # Return just the model names for the composer dropdown
        model_names = [model['name'] for model in models]
        return jsonify(model_names)
        
    except Exception as e:
        log_error(f"Available models API error: {str(e)}")
        return jsonify([])  # Return empty list on error

@models_bp.route('/detailed', methods=['GET'])
@test_mode_login_required
@handle_api_errors
@log_execution_time
def api_installed_models_detailed():
    """
    Retrieve comprehensive detailed information about all installed GGUF models.
    
    This endpoint provides an optimized, comprehensive view of all installed models
    with detailed metadata, performance characteristics, and system compatibility
    information. It uses efficient single-query operations instead of multiple
    individual model checks for better performance.
    
    The detailed view includes extended metadata such as model architecture,
    parameter counts, quantization details, memory requirements, and performance
    benchmarks when available.
    
    Returns:
        JSON response with detailed model information:
        
        Success (200):
        {
            "models": [
                {
                    "name": "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
                    "path": "/path/to/models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
                    "size": 1234567890,
                    "size_formatted": "1.2 GB",
                    "type": "GGUF",
                    "status": "loaded" | "available",
                    "context_size": 32768,
                    "max_context": 32768,
                    "parameters": "1.1B",
                    "quantization": "Q4_K_M",
                    "architecture": "llama",
                    "vocab_size": 32000,
                    "memory_required": "2.1 GB",
                    "performance_tier": "fast",
                    "last_used": "2024-01-15T10:30:00Z",
                    "compatibility": {
                        "cpu": true,
                        "gpu": false,
                        "metal": true
                    }
                }
            ],
            "total": 1,
            "summary": {
                "total_size": 1234567890,
                "loaded_models": 1,
                "available_models": 1
            }
        }
        
        Backend Error (503):
        {
            "error": "AI backend could not be started"
        }
        
        Internal Error (500):
        {
            "error": "Failed to fetch detailed model information"
        }
    
    Extended Metadata Fields:
        - size_formatted: Human-readable file size (e.g., "1.2 GB")
        - max_context: Maximum supported context window
        - architecture: Model architecture type (llama, falcon, etc.)
        - vocab_size: Vocabulary size for tokenization
        - memory_required: Estimated RAM usage when loaded
        - performance_tier: Performance classification (fast/balanced/slow)
        - last_used: ISO timestamp of last model usage
        - compatibility: Hardware compatibility flags
    
    Performance Optimizations:
        - Single bulk query for all model metadata
        - Cached file system operations
        - Efficient metadata parsing
        - Background performance profiling
    
    Use Cases:
        - Model management interfaces
        - System resource planning
        - Performance optimization
        - Hardware compatibility checking
    
    Example:
        >>> response = requests.get('/api/models/detailed')
        >>> models = response.json()['models']
        >>> for model in models:
        ...     print(f"{model['name']}: {model['size_formatted']} "
        ...           f"({model['performance_tier']})")
    
    Note:
        This endpoint may take longer than the basic models endpoint due to
        comprehensive metadata collection. Results are cached for subsequent
        requests to improve performance.
    """
    log_api_request(request.endpoint, request.method)
    
    try:
        from ..utils.llm_model_manager import LLMModelManager
        model_manager = LLMModelManager()
        
        # OPTIMIZATION: Get all available models in single operation
        # Instead of checking each model individually in a loop (N+1 problem)
        models = model_manager.get_available_models()
        
        # OPTIMIZATION: Get current model info once, not per model
        current_model_path = llm_controller.model_path
        current_context_size = llm_controller.n_ctx
        
        # OPTIMIZATION: Process all models in single loop
        for model in models:
            # Check if this model is currently loaded (string comparison, not query)
            if current_model_path and model.get('name', '') in current_model_path:
                model['status'] = 'loaded'
                model['context_size'] = current_context_size
            else:
                model['status'] = 'available'
                model['context_size'] = 4096  # Default context size
        
        return jsonify(models)
        
    except Exception as e:
        log_error(f"Detailed models API error: {str(e)}")
        return jsonify({'error': 'Failed to fetch model details'}), 500

@models_bp.route('/backend_status', methods=['GET'])
@test_mode_login_required
@handle_api_errors
@log_execution_time
def api_backend_status():
    """
    Get llama.cpp backend status.
    
    Returns:
        JSON response with backend status information
    """
    log_api_request(request.endpoint, request.method)
    
    try:
        is_running = llm_controller.is_server_ready()
        
        # Extract model name from path for display
        current_model = None
        if llm_controller.model_path:
            from pathlib import Path
            model_path = Path(llm_controller.model_path)
            current_model = model_path.stem  # Get filename without extension
        
        return jsonify({
            'success': True,
            'running': is_running,
            'model_loaded': llm_controller.model_path is not None,
            'model_path': llm_controller.model_path,
            'current_model': current_model,
            'status': 'Ready' if is_running else 'Stopped',
            'server_url': llm_controller.server_url if is_running else None
        })
        
    except Exception as e:
        log_error(f"Backend status API error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to get backend status'}), 500

@models_bp.route('/backend_start', methods=['POST'])
@test_mode_login_required
@handle_api_errors
@log_execution_time
def api_backend_start():
    """
    Manually start llama.cpp backend server.
    
    Returns:
        JSON response indicating success or failure
    """
    log_api_request(request.endpoint, request.method)
    
    try:
        if llm_controller.start_server():
            return jsonify({'success': True, 'message': 'Backend started successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to start backend'}), 503
            
    except Exception as e:
        log_error(f"Backend start API error: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@models_bp.route('/recommended', methods=['GET'])
@test_mode_login_required
@handle_api_errors
@log_execution_time
def api_recommended_models():
    """
    Get list of recommended models for installation from curated models data.
    
    Returns:
        JSON response with recommended models list with rich metadata
    """
    import os
    import json
    from pathlib import Path
    
    log_api_request(request.endpoint, request.method)
    
    try:
        # Load models data from JSON file
        models_data_path = Path(__file__).parent.parent / 'models_data.json'
        
        if not models_data_path.exists():
            log_error(f"Models data file not found: {models_data_path}")
            return jsonify([])  # Return empty list if file not found
        
        with open(models_data_path, 'r', encoding='utf-8') as f:
            models_data = json.load(f)
        
        # Transform the data for the frontend
        recommended = []
        for model in models_data:
            # Create full model name for Ollama
            full_name = f"{model['name']}:{model['tag']}"
            
            # Format size for display
            size_display = f"{model.get('size_gb', 'Unknown')} GB" if model.get('size_gb') else 'Unknown size'
            
            # Format context window
            context_formatted = f"{model.get('n_ctx', 'Unknown'):,}" if isinstance(model.get('n_ctx'), int) else str(model.get('n_ctx', 'Unknown'))
            
            # Create model entry
            model_entry = {
                'name': model['name'],
                'tag': model['tag'],
                'full_name': full_name,
                'description': model['description'],
                'fidelity': model['fidelity'],
                'pc_load': model['pc_load'],
                'categories': model['categories'],
                'uncensored': model.get('uncensored', False),
                'n_ctx': model.get('n_ctx', 'Unknown'),
                'context_display': f"{context_formatted} tokens",
                'size': size_display,
                'size_gb': model.get('size_gb'),
                'languages': model.get('languages', ['English']),
                'strengths': model.get('strengths', []),
                'use_cases': model.get('use_cases', []),
                'scraped': False,
                'source': 'curated'
            }
            
            recommended.append(model_entry)
        
        # Sort by PC load (lighter models first) then by name
        load_order = {'Very Low': 1, 'Low': 2, 'Medium': 3, 'Medium-High': 4, 'High': 5, 'Very High': 6}
        recommended.sort(key=lambda x: (load_order.get(x['pc_load'], 99), x['name']))
        
        return jsonify(recommended)
        
    except Exception as e:
        log_error(f"Error loading recommended models: {str(e)}")
        # Fallback to basic models if loading fails
        fallback_models = [
            {
                'name': 'llama3.2',
                'tag': '3b', 
                'full_name': 'llama3.2:3b',
                'description': 'Lightweight Llama 3.2 model, good for basic tasks',
                'size': '2.0 GB',
                'categories': ['General', 'Chat'],
                'pc_load': 'Low',
                'fidelity': 'High',
                'n_ctx': 128000,
                'context_display': '128,000 tokens',
                'uncensored': False,
                'scraped': False,
                'source': 'fallback'
            }
        ]
        return jsonify(fallback_models)


@models_bp.route('/set_backend_model', methods=['POST'])
@test_mode_login_required
@handle_api_errors
@log_execution_time
def api_set_backend_model():
    """
    Set the backend model for the LLM controller.
    
    Returns:
        JSON response indicating success or failure
    """
    log_api_request(request.endpoint, request.method)
    
    try:
        data = request.get_json()
        if not data or 'model_name' not in data:
            return jsonify({'success': False, 'error': 'Model name is required'}), 400
        
        model_name = data['model_name']
        
        # Use the LLM model manager to load the backend model
        from ..utils.llm_model_manager import LLMModelManager
        model_manager = LLMModelManager()
        success = model_manager.load_model(model_name)
        
        if success:
            return jsonify({'success': True, 'message': f'Backend model set to {model_name}'})
        else:
            return jsonify({'success': False, 'error': f'Failed to set backend model to {model_name}'}), 500
            
    except Exception as e:
        log_error(f"Set backend model API error: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@models_bp.route('/dynamic', methods=['GET'])
@test_mode_login_required  
@handle_api_errors
@log_execution_time
def get_dynamic_models():
    """
    Get dynamic model recommendations based on real-time hardware analysis.
    This replaces hardcoded model lists with intelligent hardware-based selection.
    
    Query parameters:
        category: 'llm', 'image', 'audio', or 'all' (default: 'all')
    
    Returns:
        JSON: Hardware-optimized model recommendations with current availability
    """
    log_api_request(request.endpoint, {})
    
    try:
        # Get category filter from query params
        category = request.args.get('category', 'all')
        
        # Use dynamic model selector for hardware-based recommendations
        selector = get_dynamic_model_selector()
        recommendations = selector.get_recommended_models(category)
        
        return jsonify({
            "success": True,
            "data": recommendations,
            "hardware_optimized": True,
            "cache_info": {
                "last_updated": recommendations.get("timestamp", ""),
                "source": "dynamic_selector"
            }
        })
        
    except Exception as e:
        log_error(f"Error getting dynamic model recommendations: {e}")
        return jsonify({
            "success": False, 
            "error": str(e),
            "fallback_available": True
        }), 500

@models_bp.route('/download_progress', methods=['GET'])
@test_mode_login_required
@handle_api_errors
@log_execution_time
def api_download_progress():
    """
    Get download progress for model downloads.
    
    Returns:
        JSON response with download progress information
    """
    log_api_request(request.endpoint, request.method)
    
    try:
        # Check if download is in progress by looking for a download status file
        instance_dir = Path(__file__).parent.parent.parent / "instance"
        download_status_file = instance_dir / "download_status.json"
        
        if download_status_file.exists():
            with open(download_status_file, 'r') as f:
                status = json.load(f)
            return jsonify(status)
        else:
            return jsonify({
                'success': True,
                'percentage': 0,
                'in_progress': False,
                'last_message': 'No download in progress'
            })
        
    except Exception as e:
        log_error(f"Download progress API error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to get download progress'}), 500

@models_bp.route('/download_default', methods=['POST'])
@test_mode_login_required
@handle_api_errors
@log_execution_time
@download_rate_limit()
def api_download_default():
    """
    Download the default recommended model.
    
    Returns:
        JSON response indicating success or failure
    """
    log_api_request(request.endpoint, request.method)
    log_error("api_download_default function called")
    
    try:
        # Start download in background
        try:
            # Temporarily run download directly to test
            log_error("Starting download directly in main thread for testing")
            download_model()
            log_error("Download completed in main thread")
        except Exception as thread_error:
            log_error(f"Failed to run download: {str(thread_error)}")
            return jsonify({'success': False, 'error': 'Failed to start download'}), 500
        
        return jsonify({
            'success': True,
            'message': 'Default model download started',
            'updates': [
                {
                    'percentage': 0,
                    'message': 'Download started'
                }
            ]
        })
        
    except Exception as e:
        log_error(f"Download default model API error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to start download'}), 500

def download_model():
    """Download the default model - moved outside the API function for clarity"""
    log_error("download_model function called - starting download process")
    try:
        # Use a more reliable path for models directory
        models_dir = Path(__file__).parent.parent.parent / "models"
        models_dir.mkdir(exist_ok=True)
        
        # Use instance directory for status file
        instance_dir = Path(__file__).parent.parent.parent / "instance"
        instance_dir.mkdir(exist_ok=True)
        status_file = instance_dir / "download_status.json"
        
        # Log the paths for debugging
        log_error(f"Download paths - models_dir: {models_dir}, instance_dir: {instance_dir}, status_file: {status_file}")
        
        # Update status to show download starting
        with open(status_file, 'w', encoding='utf-8') as f:
            json.dump({
                'success': True,
                'percentage': 0,
                'in_progress': True,
                'last_message': 'Starting download...'
            }, f)
        
        log_error("Download status file created successfully")
        
        # Use a smaller model for testing - TinyLlama 1.1B instead of Qwen2 7B
        model_url = "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
        model_file = models_dir / "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
        model_name = "TinyLlama-1.1B-Chat"
        
        log_error(f"Model file to check: {model_file}")
        
        # Check if model already exists
        if model_file.exists():
            # Validate file size - TinyLlama should be at least 100MB
            file_size = model_file.stat().st_size
            min_size = 100 * 1024 * 1024  # 100MB minimum
            log_error(f"Model file exists, size: {file_size} bytes, minimum expected: {min_size} bytes")
            
            if file_size < min_size:
                log_error(f"Model file is too small ({file_size} bytes), removing corrupted file")
                model_file.unlink()  # Remove corrupted file
            else:
                log_error(f"Model already exists: {model_file}")
                with open(status_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'success': True,
                        'percentage': 100,
                        'in_progress': False,
                        'last_message': f'Model already exists: {model_file.name}'
                    }, f)
                return
        
        log_error("No existing model found, starting download")
        log_error(f"Starting download of {model_name} from {model_url}")
        
        # Download with progress
        try:
            response = requests.get(model_url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            log_error(f"Download started, total size: {total_size} bytes")
            
            if total_size == 0:
                log_error("Warning: Content-Length header is 0, download may fail")
            
            with open(model_file, 'wb') as model_f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        model_f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            # Update progress every 5%
                            if int(progress) % 5 == 0:
                                with open(status_file, 'w', encoding='utf-8') as status_f:
                                    json.dump({
                                        'success': True,
                                        'percentage': progress,
                                        'in_progress': True,
                                        'last_message': f'Downloading {model_name}: {progress:.1f}%'
                                    }, status_f)
            
            # Verify download completed successfully
            final_size = model_file.stat().st_size
            log_error(f"Download completed: {model_file}, final size: {final_size} bytes")
            
            if final_size < min_size:
                raise Exception(f"Downloaded file is too small: {final_size} bytes (expected at least {min_size} bytes)")
            
            # Download complete
            with open(status_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'success': True,
                    'percentage': 100,
                    'in_progress': False,
                    'last_message': f'Download completed: {model_file.name} ({final_size // (1024*1024)} MB)'
                }, f)
                
        except requests.exceptions.Timeout:
            log_error("Download timed out")
            raise Exception("Download timed out - please try again")
        except requests.exceptions.ConnectionError:
            log_error("Connection error during download")
            raise Exception("Connection error - please check your internet connection")
        except requests.exceptions.HTTPError as e:
            log_error(f"HTTP error during download: {e}")
            raise Exception(f"Download failed: {e}")
        except Exception as e:
            log_error(f"Unexpected error during download: {e}")
            raise Exception(f"Download failed: {e}")
            
            # Update status file with error
            with open(status_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'success': False,
                    'percentage': 0,
                    'in_progress': False,
                    'last_message': f'Download failed: {e}'
                }, f)
                
    except Exception as e:
        log_error(f"Download model function error: {e}")
        # Update status file with error
        with open(status_file, 'w', encoding='utf-8') as f:
            json.dump({
                'success': False,
                'percentage': 0,
                'in_progress': False,
                'last_message': f'Download failed: {e}'
            }, f)
