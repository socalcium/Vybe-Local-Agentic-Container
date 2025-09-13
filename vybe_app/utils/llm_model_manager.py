"""
LLM Model Manager for Vybe
Direct model control using llama-cpp-python backend
"""

import os
import json
import time
import requests
import threading
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from ..logger import log_info, log_warning, log_error
from ..core.backend_llm_controller import get_backend_controller
from .cache_manager import cache
from urllib.parse import urlparse


class LLMModelManager:
    """Manages LLM models using llama-cpp-python backend"""
    
    def __init__(self, models_dir: Optional[str] = None):
        self.models_dir = Path(models_dir) if models_dir else Path(os.getcwd()) / "models"
        self.models_dir.mkdir(exist_ok=True)
        self.backend_controller = get_backend_controller()
        self._available_models_cache = None
        self._cache_time = 0
        self._cache_duration = 30  # Cache for 30 seconds
        
    def ensure_models_directory(self):
        """Ensure models directory exists"""
        self.models_dir.mkdir(exist_ok=True)
        return True
        
    @cache.cached(timeout=1800, cache_name="model_data")  # Cache for 30 minutes
    def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available GGUF models"""
        current_time = time.time()
        
        # Use cache if recent
        if (self._available_models_cache and 
            current_time - self._cache_time < self._cache_duration):
            return self._available_models_cache
            
        models = []
        
        # Scan for GGUF files
        for gguf_file in self.models_dir.glob("*.gguf"):
            file_size = gguf_file.stat().st_size
            models.append({
                "name": gguf_file.stem,
                "model": gguf_file.name,
                "size": file_size,
                "digest": f"file:{gguf_file}",
                "details": {
                    "format": "gguf",
                    "family": "llama",
                    "families": ["llama"],
                    "parameter_size": "unknown",
                    "quantization_level": self._extract_quantization_level(gguf_file.name)
                },
                "modified_at": gguf_file.stat().st_mtime
            })
        
        # Enforce hard minimum context on recommendations and remove low-context defaults
        if not models:
            models = []
            
        self._available_models_cache = models
        self._cache_time = current_time
        return models
    
    def _extract_quantization_level(self, filename: str) -> str:
        """Extract quantization level from filename"""
        filename_upper = filename.upper()
        quantization_patterns = ["Q4_K_M", "Q4_0", "Q5_K_M", "Q5_0", "Q8_0", "F16", "F32"]
        
        for pattern in quantization_patterns:
            if pattern in filename_upper:
                return pattern
        return "unknown"
    
    def is_model_loaded(self, model_name: str) -> bool:
        """Check if a specific model is currently loaded"""
        return bool(self.backend_controller.is_server_ready() and 
                   self.backend_controller.model_path and 
                   model_name in str(self.backend_controller.model_path))
    
    def load_model(self, model_name: str) -> bool:
        """Load a specific model"""
        log_info(f"Loading model: {model_name}")
        
        # Find the model file
        model_file = None
        for gguf_file in self.models_dir.glob("*.gguf"):
            if model_name in gguf_file.name or model_name == gguf_file.stem:
                model_file = gguf_file
                break
        
        if not model_file:
            log_error(f"Model file not found for: {model_name}")
            return False
        
        # Update the backend controller's model path
        self.backend_controller.model_path = str(model_file)
        
        # Restart the server with the new model
        self.backend_controller.stop_server()
        time.sleep(2)  # Wait for shutdown
        
        success = self.backend_controller.start_server()
        if success:
            log_info(f"Successfully loaded model: {model_name}")
        else:
            log_error(f"Failed to load model: {model_name}")
        
        return success
    
    def unload_model(self) -> bool:
        """Unload the current model"""
        log_info("Unloading current model")
        self.backend_controller.stop_server()
        return True
    
    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive information about a specific model"""
        try:
            models = self.get_available_models()
            for model in models:
                if model["name"] == model_name or model["model"] == model_name:
                    # Enhance with additional metadata
                    enhanced_info = model.copy()
                    
                    # Add file system information
                    model_file = None
                    for gguf_file in self.models_dir.glob("*.gguf"):
                        if model_name in gguf_file.name or model_name == gguf_file.stem:
                            model_file = gguf_file
                            break
                    
                    if model_file:
                        enhanced_info.update({
                            'file_path': str(model_file),
                            'file_size_mb': round(model_file.stat().st_size / (1024 * 1024), 2),
                            'last_modified': model_file.stat().st_mtime,
                            'is_loaded': self.is_model_loaded(model_name),
                            'can_load': True
                        })
                    else:
                        enhanced_info.update({
                            'file_path': None,
                            'file_size_mb': 0,
                            'last_modified': None,
                            'is_loaded': False,
                            'can_load': False
                        })
                    
                    # Add performance estimates
                    file_size_mb = enhanced_info.get('file_size_mb', 0)
                    if file_size_mb > 0:
                        enhanced_info.update({
                            'estimated_load_time': self._estimate_load_time(file_size_mb),
                            'estimated_memory_usage': self._estimate_memory_usage(file_size_mb),
                            'recommended_hardware': self._get_hardware_recommendations(file_size_mb)
                        })
                    
                    return enhanced_info
            
            return None
            
        except Exception as e:
            log_error(f"Error getting model info for {model_name}: {e}")
            return None
    
    def _estimate_load_time(self, file_size_mb: float) -> str:
        """Estimate model load time based on file size"""
        if file_size_mb < 100:
            return "5-10 seconds"
        elif file_size_mb < 500:
            return "10-30 seconds"
        elif file_size_mb < 2000:
            return "30-60 seconds"
        else:
            return "1-3 minutes"
    
    def _estimate_memory_usage(self, file_size_mb: float) -> str:
        """Estimate memory usage based on file size"""
        # Rough estimate: GGUF models typically use 1.5-2x their file size in RAM
        estimated_ram = file_size_mb * 1.8
        if estimated_ram < 1000:
            return f"{estimated_ram:.0f}MB"
        else:
            return f"{estimated_ram/1024:.1f}GB"
    
    def _get_hardware_recommendations(self, file_size_mb: float) -> Dict[str, str]:
        """Get hardware recommendations based on model size"""
        if file_size_mb < 100:
            return {
                'cpu': 'Any modern CPU',
                'ram': '4GB+',
                'gpu': 'Optional',
                'storage': '1GB free space'
            }
        elif file_size_mb < 500:
            return {
                'cpu': '4+ cores recommended',
                'ram': '8GB+',
                'gpu': 'Optional but recommended',
                'storage': '2GB free space'
            }
        elif file_size_mb < 2000:
            return {
                'cpu': '8+ cores recommended',
                'ram': '16GB+',
                'gpu': 'Recommended for performance',
                'storage': '5GB free space'
            }
        else:
            return {
                'cpu': 'High-end CPU recommended',
                'ram': '32GB+',
                'gpu': 'Strongly recommended',
                'storage': '10GB+ free space'
            }
    
    def pull_model(self, model_name: str, download_url: Optional[str] = None) -> bool:
        """Download a model with comprehensive progress tracking and validation"""
        try:
            import requests
            import threading
            import json
            import hashlib
            from pathlib import Path
            from urllib.parse import urlparse
            
            # Create download status file
            status_file = Path(__file__).parent.parent.parent / "instance" / "download_status.json"
            status_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Initialize download status
            download_status = {
                'model_name': model_name,
                'status': 'initializing',
                'progress': 0,
                'downloaded_bytes': 0,
                'total_bytes': 0,
                'start_time': None,
                'estimated_time_remaining': None,
                'download_speed': None,
                'error': None,
                'checksum': None,
                'validation_status': 'pending'
            }
            
            def update_status(status_data):
                try:
                    with open(status_file, 'w', encoding='utf-8') as f:
                        json.dump(status_data, f, indent=2)
                except Exception as e:
                    log_error(f"Failed to update download status: {e}")
            
            # Start download in background thread
            def download_thread():
                try:
                    download_status['start_time'] = time.time()
                    download_status['status'] = 'downloading'
                    update_status(download_status)
                    
                    # Determine download URL
                    final_download_url = download_url
                    if not final_download_url:
                        # Try to find model in Hugging Face model hub
                        base_url = f"https://huggingface.co/{model_name}/resolve/main"
                        
                        # Common GGUF filename patterns
                        filename_patterns = [
                            f"{model_name}.gguf",
                            f"{model_name}-Q4_K_M.gguf",
                            f"{model_name}-Q5_K_M.gguf",
                            f"{model_name}-Q8_0.gguf",
                            "model.gguf",
                            "ggml-model-q4_0.gguf",
                            "ggml-model-q4_1.gguf"
                        ]
                        
                        found_url = None
                        for filename in filename_patterns:
                            test_url = f"{base_url}/{filename}"
                            try:
                                response = requests.head(test_url, timeout=10)
                                if response.status_code == 200:
                                    found_url = test_url
                                    log_info(f"Found model at: {found_url}")
                                    break
                            except Exception as e:
                                log_warning(f"Failed to check {test_url}: {e}")
                                continue
                        
                        if found_url:
                            final_download_url = found_url
                        else:
                            raise ValueError(f"Could not find download URL for model: {model_name}")
                    else:
                        # download_url was provided as parameter, validate it exists
                        if not final_download_url:
                            raise ValueError(f"Could not find download URL for model: {model_name}")
                    
                    # Start download with enhanced headers
                    headers = {
                        'User-Agent': 'Vybe-AI-Desktop/1.0',
                        'Accept': '*/*',
                        'Accept-Encoding': 'gzip, deflate',
                        'Connection': 'keep-alive'
                    }
                    
                    response = requests.get(final_download_url, stream=True, timeout=30, headers=headers)
                    response.raise_for_status()
                    
                    # Get file size and validate
                    total_size = int(response.headers.get('content-length', 0))
                    if total_size == 0:
                        raise ValueError("Could not determine file size")
                    
                    if total_size < 10 * 1024 * 1024:  # Less than 10MB
                        raise ValueError("File too small, likely not a valid model")
                    
                    download_status['total_bytes'] = total_size
                    update_status(download_status)
                    
                    # Determine local filename
                    parsed_url = urlparse(final_download_url)
                    if '/' in parsed_url.path:
                        filename = parsed_url.path.split('/')[-1]
                    else:
                        filename = f"{model_name}.gguf"
                    
                    # Ensure filename has .gguf extension
                    if not filename.endswith('.gguf'):
                        filename = f"{filename}.gguf"
                    
                    local_path = self.models_dir / filename
                    
                    # Create temporary file for download
                    temp_path = local_path.with_suffix('.tmp')
                    
                    # Download with progress tracking and checksum calculation
                    downloaded = 0
                    start_time = time.time()
                    checksum = hashlib.sha256()
                    
                    with open(temp_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                checksum.update(chunk)
                                
                                # Update progress
                                progress = (downloaded / total_size * 100) if total_size > 0 else 0
                                download_status['downloaded_bytes'] = downloaded
                                download_status['progress'] = progress
                                
                                # Calculate download speed and ETA
                                elapsed_time = time.time() - start_time
                                if elapsed_time > 0:
                                    speed = downloaded / elapsed_time
                                    download_status['download_speed'] = f"{speed / (1024*1024):.2f} MB/s"
                                    
                                    if speed > 0:
                                        remaining_bytes = total_size - downloaded
                                        eta_seconds = remaining_bytes / speed
                                        download_status['estimated_time_remaining'] = f"{eta_seconds:.0f}s"
                                
                                update_status(download_status)
                    
                    # Validate downloaded file
                    if temp_path.stat().st_size != total_size:
                        temp_path.unlink()
                        raise ValueError("Downloaded file size doesn't match expected size")
                    
                    # Move temporary file to final location
                    temp_path.rename(local_path)
                    
                    # Update final status
                    download_status['status'] = 'completed'
                    download_status['progress'] = 100
                    download_status['checksum'] = checksum.hexdigest()
                    download_status['validation_status'] = 'validated'
                    download_status['file_path'] = str(local_path)
                    download_status['file_size_mb'] = round(total_size / (1024 * 1024), 2)
                    update_status(download_status)
                    
                    # Invalidate cache
                    self._available_models_cache = None
                    
                    log_info(f"Successfully downloaded model: {model_name} ({download_status['file_size_mb']}MB)")
                    return True
                    
                except Exception as e:
                    log_error(f"Download failed for {model_name}: {e}")
                    download_status['status'] = 'failed'
                    download_status['error'] = str(e)
                    update_status(download_status)
                    
                    # Clean up temporary file if it exists
                    try:
                        if 'temp_path' in locals() and temp_path.exists():
                            temp_path.unlink()
                    except Exception as e:
                        log_error(f"Failed to clean up temp file: {e}")
                        pass
                    
                    return False
            
            # Start download thread
            thread = threading.Thread(target=download_thread, daemon=True)
            thread.start()
            
            return True
            
        except Exception as e:
            log_error(f"Failed to initiate download for {model_name}: {e}")
            return False
    
    def get_download_status(self, model_name: Optional[str] = None) -> Dict[str, Any]:
        """Get current download status for a model or all downloads"""
        try:
            status_file = Path(__file__).parent.parent.parent / "instance" / "download_status.json"
            
            if not status_file.exists():
                return {
                    'success': True,
                    'downloads': [],
                    'message': 'No active downloads'
                }
            
            with open(status_file, 'r', encoding='utf-8') as f:
                status_data = json.load(f)
            
            if model_name and status_data.get('model_name') != model_name:
                return {
                    'success': True,
                    'downloads': [],
                    'message': f'No download found for {model_name}'
                }
            
            return {
                'success': True,
                'downloads': [status_data] if isinstance(status_data, dict) else status_data,
                'message': 'Download status retrieved successfully'
            }
            
        except Exception as e:
            log_error(f"Failed to get download status: {e}")
            return {
                'success': False,
                'error': f'Failed to get download status: {str(e)}'
            }
    
    def cancel_download(self, model_name: str) -> bool:
        """Cancel an active download"""
        try:
            status_file = Path(__file__).parent.parent.parent / "instance" / "download_status.json"
            
            if not status_file.exists():
                return False
            
            with open(status_file, 'r', encoding='utf-8') as f:
                status_data = json.load(f)
            
            if status_data.get('model_name') == model_name and status_data.get('status') == 'downloading':
                status_data['status'] = 'cancelled'
                status_data['error'] = 'Download cancelled by user'
                
                with open(status_file, 'w', encoding='utf-8') as f:
                    json.dump(status_data, f, indent=2)
                
                log_info(f"Download cancelled for {model_name}")
                return True
            
            return False
            
        except Exception as e:
            log_error(f"Failed to cancel download for {model_name}: {e}")
            return False
    
    def delete_model(self, model_name: str) -> bool:
        """Delete a model file"""
        for gguf_file in self.models_dir.glob("*.gguf"):
            if model_name in gguf_file.name or model_name == gguf_file.stem:
                try:
                    gguf_file.unlink()
                    log_info(f"Deleted model: {model_name}")
                    self._available_models_cache = None  # Invalidate cache
                    return True
                except Exception as e:
                    log_error(f"Failed to delete model {model_name}: {e}")
                    return False
        return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the model manager"""
        return {
            "running": self.backend_controller.is_server_ready(),
            "models_directory": str(self.models_dir),
            "available_models": len(self.get_available_models()),
            "current_model": str(self.backend_controller.model_path) if self.backend_controller.model_path else None,
            "server_url": self.backend_controller.server_url,
            "backend": "llama-cpp-python"
        }


# Global instance
llm_model_manager = LLMModelManager()
