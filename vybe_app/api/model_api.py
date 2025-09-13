"""
Model API for Vybe AI Desktop Application
Handles model downloading, status tracking, and model information retrieval
"""

from flask import Blueprint, jsonify, request
import os
import time
import threading
from pathlib import Path
from typing import Dict, Any, Optional
import logging

from ..logger import log_info, log_warning, log_error
from ..utils.llm_model_manager import LLMModelManager

logger = logging.getLogger(__name__)

model_api = Blueprint('model_api', __name__)

# Thread-safe singleton model manager instance
_model_manager: Optional[LLMModelManager] = None
_model_manager_lock = threading.Lock()


def get_model_manager() -> LLMModelManager:
    """Get thread-safe singleton model manager instance"""
    global _model_manager
    if _model_manager is None:
        with _model_manager_lock:
            # Double-check locking pattern
            if _model_manager is None:
                _model_manager = LLMModelManager()
    return _model_manager

@model_api.route('/download', methods=['POST'])
def download_model():
    """
    Start downloading a model with progress tracking
    """
    try:
        data = request.json
        if not data:
            return jsonify({
                "status": "error",
                "message": "No data provided"
            }), 400
        
        model_name = data.get('model_name')
        download_url = data.get('download_url')
        
        if not model_name:
            return jsonify({
                "status": "error",
                "message": "Model name is required"
            }), 400
        
        # Start download
        model_manager = get_model_manager()
        success = model_manager.pull_model(model_name, download_url)
        
        if success:
            log_info(f"Model download initiated: {model_name}")
            return jsonify({
                "status": "success",
                "message": f"Download started for {model_name}",
                "data": {
                    "model_name": model_name,
                    "download_url": download_url,
                    "status": "initiated"
                }
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": f"Failed to start download for {model_name}"
            }), 500
            
    except Exception as e:
        log_error(f"Error starting model download: {e}")
        return jsonify({
            "status": "error",
            "message": f"Failed to start download: {str(e)}"
        }), 500

@model_api.route('/download/status', methods=['GET'])
def get_download_status():
    """
    Get current download status for a model or all downloads
    """
    try:
        model_name = request.args.get('model_name')
        
        model_manager = get_model_manager()
        status = model_manager.get_download_status(model_name)
        
        return jsonify({
            "status": "success",
            "data": status
        }), 200
        
    except Exception as e:
        log_error(f"Error getting download status: {e}")
        return jsonify({
            "status": "error",
            "message": f"Failed to get download status: {str(e)}"
        }), 500

@model_api.route('/download/cancel', methods=['POST'])
def cancel_download():
    """
    Cancel an active model download
    """
    try:
        data = request.json
        if not data:
            return jsonify({
                "status": "error",
                "message": "No data provided"
            }), 400
        
        model_name = data.get('model_name')
        
        if not model_name:
            return jsonify({
                "status": "error",
                "message": "Model name is required"
            }), 400
        
        # Cancel download
        model_manager = get_model_manager()
        success = model_manager.cancel_download(model_name)
        
        if success:
            log_info(f"Model download cancelled: {model_name}")
            return jsonify({
                "status": "success",
                "message": f"Download cancelled for {model_name}"
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": f"No active download found for {model_name}"
            }), 404
            
    except Exception as e:
        log_error(f"Error cancelling download: {e}")
        return jsonify({
            "status": "error",
            "message": f"Failed to cancel download: {str(e)}"
        }), 500

@model_api.route('/list', methods=['GET'])
def list_models():
    """
    Get list of available models
    """
    try:
        model_manager = get_model_manager()
        models = model_manager.get_available_models()
        
        return jsonify({
            "status": "success",
            "data": {
                "models": models,
                "total_count": len(models)
            }
        }), 200
        
    except Exception as e:
        log_error(f"Error listing models: {e}")
        return jsonify({
            "status": "error",
            "message": f"Failed to list models: {str(e)}"
        }), 500

@model_api.route('/info/<model_name>', methods=['GET'])
def get_model_info(model_name):
    """
    Get detailed information about a specific model
    """
    try:
        model_manager = get_model_manager()
        info = model_manager.get_model_info(model_name)
        
        if info:
            return jsonify({
                "status": "success",
                "data": info
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": f"Model not found: {model_name}"
            }), 404
        
    except Exception as e:
        log_error(f"Error getting model info for {model_name}: {e}")
        return jsonify({
            "status": "error",
            "message": f"Failed to get model info: {str(e)}"
        }), 500

@model_api.route('/delete/<model_name>', methods=['DELETE'])
def delete_model(model_name):
    """
    Delete a specific model
    """
    try:
        model_manager = get_model_manager()
        success = model_manager.delete_model(model_name)
        
        if success:
            log_info(f"Model deleted: {model_name}")
            return jsonify({
                "status": "success",
                "message": f"Model {model_name} deleted successfully"
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": f"Model not found or could not be deleted: {model_name}"
            }), 404
            
    except Exception as e:
        log_error(f"Error deleting model {model_name}: {e}")
        return jsonify({
            "status": "error",
            "message": f"Failed to delete model: {str(e)}"
        }), 500

@model_api.route('/status', methods=['GET'])
def get_model_manager_status():
    """
    Get the current status of the model manager
    """
    try:
        model_manager = get_model_manager()
        status = model_manager.get_status()
        
        return jsonify({
            "status": "success",
            "data": status
        }), 200
        
    except Exception as e:
        log_error(f"Error getting model manager status: {e}")
        return jsonify({
            "status": "error",
            "message": f"Failed to get status: {str(e)}"
        }), 500

@model_api.route('/validate/<model_name>', methods=['POST'])
def validate_model(model_name):
    """
    Validate a model file for integrity and compatibility
    """
    try:
        # Get validation options from request
        data = request.json or {}
        validate_file = data.get('validate_file', True)
        validate_format = data.get('validate_format', True)
        check_compatibility = data.get('check_compatibility', True)
        
        # Get model info
        model_manager = get_model_manager()
        info = model_manager.get_model_info(model_name)
        
        if not info:
            return jsonify({
                "status": "error",
                "message": f"Model not found: {model_name}"
            }), 404
        
        validation_results = {
            "model_name": model_name,
            "file_exists": info.get('file_exists', False),
            "file_size_valid": False,
            "format_valid": False,
            "compatibility_check": False,
            "overall_valid": False
        }
        
        # Check file existence and size
        if validate_file and info.get('file_exists'):
            file_size_mb = info.get('file_size_mb', 0)
            validation_results['file_size_valid'] = file_size_mb > 10  # Minimum 10MB
            
        # Check format (GGUF files)
        if validate_format and info.get('file_path'):
            file_path = Path(info['file_path'])
            validation_results['format_valid'] = file_path.suffix.lower() == '.gguf'
        
        # Check compatibility (basic check)
        if check_compatibility:
            # For now, assume all GGUF files are compatible
            validation_results['compatibility_check'] = validation_results['format_valid']
        
        # Overall validation
        validation_results['overall_valid'] = (
            validation_results['file_exists'] and
            validation_results['file_size_valid'] and
            validation_results['format_valid'] and
            validation_results['compatibility_check']
        )
        
        return jsonify({
            "status": "success",
            "data": validation_results
        }), 200
        
    except Exception as e:
        log_error(f"Error validating model {model_name}: {e}")
        return jsonify({
            "status": "error",
            "message": f"Failed to validate model: {str(e)}"
        }), 500

@model_api.route('/search', methods=['GET'])
def search_models():
    """
    Search for models by name or metadata
    """
    try:
        query = request.args.get('q', '').lower()
        model_type = request.args.get('type')
        min_size = request.args.get('min_size')
        max_size = request.args.get('max_size')
        
        model_manager = get_model_manager()
        models = model_manager.get_available_models()
        filtered_models = []
        
        for model in models:
            # Text search
            if query:
                model_name = model.get('name', '').lower()
                model_description = model.get('description', '').lower()
                if query not in model_name and query not in model_description:
                    continue
            
            # Type filter
            if model_type and model.get('type') != model_type:
                continue
            
            # Size filters
            if min_size:
                try:
                    min_size_mb = float(min_size)
                    model_size_mb = model.get('file_size_mb', 0)
                    if model_size_mb < min_size_mb:
                        continue
                except ValueError:
                    pass
            
            if max_size:
                try:
                    max_size_mb = float(max_size)
                    model_size_mb = model.get('file_size_mb', 0)
                    if model_size_mb > max_size_mb:
                        continue
                except ValueError:
                    pass
            
            filtered_models.append(model)
        
        return jsonify({
            "status": "success",
            "data": {
                "models": filtered_models,
                "total_count": len(filtered_models),
                "query": query,
                "filters_applied": {
                    "type": model_type,
                    "min_size": min_size,
                    "max_size": max_size
                }
            }
        }), 200
        
    except Exception as e:
        log_error(f"Error searching models: {e}")
        return jsonify({
            "status": "error",
            "message": f"Failed to search models: {str(e)}"
        }), 500
