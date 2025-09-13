"""
LLM Backend Manager for Vybe
Manages llama-cpp-python backend lifecycle and model management
Integrated backend management system replacing external dependencies
"""
import threading
import time
import requests
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from collections import deque
import statistics
import logging

logger = logging.getLogger(__name__)

class LLMBackendManager:
    """Manages integrated llama-cpp-python backend lifecycle"""
    
    def __init__(self, 
                 backend_url: str = "http://localhost:11435",
                 timeout: int = 30):
        """
        Initialize the LLM backend manager
        
        Args:
            backend_url: URL of the llama-cpp-python backend
            timeout: Default timeout for backend operations (used as fallback)
        """
        self.backend_url = backend_url
        self.default_timeout = timeout
        self.backend_controller = None
        # Create persistent session for connection reuse
        self._session = requests.Session()
        # Note: timeout is set per request, not on session
        
        # Adaptive timeout management
        self._response_times = deque(maxlen=50)  # Store last 50 response times
        self._min_timeout = 5    # Minimum timeout in seconds
        self._max_timeout = 120  # Maximum timeout in seconds
        self._timeout_lock = threading.Lock()
    
    def __del__(self):
        """Cleanup session on object destruction"""
        try:
            if hasattr(self, '_session') and self._session:
                self._session.close()
        except Exception:
            pass  # Ignore cleanup errors

    def _record_response_time(self, response_time: float):
        """Record response time for adaptive timeout calculation"""
        with self._timeout_lock:
            self._response_times.append(response_time)
    
    def _get_adaptive_timeout(self) -> float:
        """Calculate adaptive timeout based on historical response times"""
        with self._timeout_lock:
            if not self._response_times:
                return self.default_timeout
            
            # Calculate statistics from recent response times
            times = list(self._response_times)
            mean_time = statistics.mean(times)
            
            # Calculate standard deviation for variability
            if len(times) > 1:
                stdev = statistics.stdev(times)
                # Set timeout to mean + 2 standard deviations (95% confidence)
                adaptive_timeout = mean_time + (2 * stdev)
            else:
                # If only one sample, add 50% buffer
                adaptive_timeout = mean_time * 1.5
            
            # Ensure timeout is within reasonable bounds
            adaptive_timeout = max(self._min_timeout, min(self._max_timeout, adaptive_timeout))
            
            logger.debug(f"Adaptive timeout calculated: {adaptive_timeout:.2f}s (based on {len(times)} samples)")
            return adaptive_timeout
    
    def _sanitize_error_response(self, error_message: str) -> str:
        """
        Sanitize error responses to avoid exposing backend infrastructure details
        """
        # Generic error messages to avoid exposing infrastructure details
        generic_errors = {
            'connection': "AI service is currently unavailable",
            'timeout': "AI service response timeout",
            'model': "AI model is not available", 
            'server': "AI service encountered an error",
            'network': "Network connectivity issue with AI service",
            'authentication': "AI service authentication failed",
            'resource': "AI service is temporarily overloaded"
        }
        
        error_lower = error_message.lower()
        
        # Check for common error patterns and return generic messages
        if any(term in error_lower for term in ['connection', 'connect', 'unreachable', 'refused']):
            return generic_errors['connection']
        elif any(term in error_lower for term in ['timeout', 'timed out', 'deadline']):
            return generic_errors['timeout']
        elif any(term in error_lower for term in ['model', 'load', 'cuda', 'gpu', 'memory']):
            return generic_errors['model']
        elif any(term in error_lower for term in ['500', 'internal', 'server error']):
            return generic_errors['server']
        elif any(term in error_lower for term in ['network', 'dns', 'resolve']):
            return generic_errors['network']
        elif any(term in error_lower for term in ['auth', 'unauthorized', '401', '403']):
            return generic_errors['authentication']
        elif any(term in error_lower for term in ['overload', 'busy', 'rate limit', '429']):
            return generic_errors['resource']
        else:
            # Default generic error
            return "AI service is currently unavailable"

    def is_backend_running(self) -> bool:
        """Check if LLM backend is running using adaptive timeout"""
        start_time = time.time()
        adaptive_timeout = self._get_adaptive_timeout()
        
        try:
            response = self._session.get(f"{self.backend_url}/v1/models", timeout=adaptive_timeout)
            response_time = time.time() - start_time
            self._record_response_time(response_time)
            
            if response.status_code == 200:
                models = response.json()
                model_count = len(models.get('data', []))
                logger.info(f"✅ LLM backend is running and responsive with {model_count} models (response: {response_time:.2f}s)")
                return True
            else:
                logger.info(f"❌ LLM backend returned status {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            logger.info(f"❌ LLM backend not accessible: {self._sanitize_error_response(str(e))}")
            return False
        except Exception as e:
            logger.warning(f"❌ Error checking LLM backend status: {self._sanitize_error_response(str(e))}")
            return False

    def route_chat(self, messages: list, temperature: float = 0.7, max_tokens: int = 1024) -> Dict[str, Any]:
        """
        Simple local router: always prefer local backend if available.
        Placeholder for future policy that could choose external APIs by intent.

        External provider hooks (commented):
        - OpenAI: POST https://api.openai.com/v1/chat/completions
        - Anthropic: POST https://api.anthropic.com/v1/messages
        - Together/Fireworks/etc.
        """
        # Load routing prefs
        try:
            from vybe_app.models import AppConfiguration
            routing_config = AppConfiguration.query.filter_by(key='llm_routing_mode').first()
            routing_mode = routing_config.get_value() if routing_config else 'prefer_local'
            
            provider_config = AppConfiguration.query.filter_by(key='llm_routing_default_provider').first()
            default_provider = provider_config.get_value() if provider_config else 'local'
        except Exception:
            routing_mode = 'prefer_local'
            default_provider = 'local'

        # Prefer local llama.cpp if policy allows
        if routing_mode != 'cloud_only' and self.is_backend_running():
            try:
                start_time = time.time()
                adaptive_timeout = self._get_adaptive_timeout()
                
                resp = requests.post(
                    f"{self.backend_url}/v1/chat/completions",
                    json={
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "stream": False
                    },
                    timeout=adaptive_timeout
                )
                
                response_time = time.time() - start_time
                self._record_response_time(response_time)
                
                if resp.status_code == 200:
                    data = resp.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    if not content:
                        content = data.get("choices", [{}])[0].get("text", "")
                    return {"provider": "local", "content": content}
            except Exception as e:
                sanitized_error = self._sanitize_error_response(str(e))
                logger.error(f"Router local call failed: {sanitized_error}")

        # Cloud routing intentionally disabled for this build.
        # The following provider calls are intentionally commented out and will remain inactive:
        # - OpenAI (chat/completions)
        # - Anthropic (messages)

        return {"provider": "none", "content": self._sanitize_error_response("AI backend not available. Please ensure the local model is running or configure an API key in Settings.")}

    def find_models(self) -> List[str]:
        """Find available GGUF model files in the models directory"""
        models_dir = Path(os.getcwd()) / "models"
        if not models_dir.exists():
            models_dir.mkdir(exist_ok=True)
            logger.warning(f"Models directory created at {models_dir}. Please place GGUF model files here.")
            return []
            
        # Look for GGUF files
        gguf_files = list(models_dir.glob("*.gguf"))
        
        if not gguf_files:
            logger.warning("No GGUF model files found in models directory")
            logger.info("Consider running: python download_default_model.py")
            return []
        
        model_paths = [str(f) for f in gguf_files]
        logger.info(f"Found {len(model_paths)} GGUF model files")
        return model_paths

    def start_backend(self) -> bool:
        """Start LLM backend with proper initialization"""
        try:
            if self.is_backend_running():
                logger.info("LLM backend is already running")
                return True
            
            # Import and start the backend controller
            from vybe_app.core.backend_llm_controller import BackendLLMController
            
            self.backend_controller = BackendLLMController()
            success = self.backend_controller.start_server()
            
            if success:
                logger.info("LLM backend started successfully")
                return True
            else:
                logger.error("Failed to start LLM backend")
                return False
                
        except Exception as e:
            logger.error(f"Error starting LLM backend: {e}")
            return False

    def ensure_backend_running(self) -> bool:
        """Ensure LLM backend is running, start it if necessary"""
        try:
            if self.is_backend_running():
                return True
                
            # Check if models are available
            models = self.find_models()
            if not models:
                logger.warning("No models found - backend cannot start without models")
                logger.info("Download models using: python download_default_model.py")
                return False
            
            # Try to start backend
            if not self.is_backend_running():
                logger.warning("LLM backend is not running, attempting to start...")
                return self.start_backend()
            
            return True
            
        except Exception as e:
            logger.error(f"Error ensuring backend running: {e}")
            return False

    def stop_backend(self) -> bool:
        """Stop LLM backend if we started it"""
        if self.backend_controller:
            try:
                self.backend_controller.stop_server()
                logger.info("LLM backend stopped")
                return True
            except Exception as e:
                logger.error(f"Error stopping LLM backend: {e}")
                return False
        return True

    def get_backend_status(self) -> Dict[str, Any]:
        """Get LLM backend service status"""
        if self.is_backend_running():
            try:
                adaptive_timeout = self._get_adaptive_timeout()
                response = requests.get(f"{self.backend_url}/v1/models", timeout=adaptive_timeout)
                if response.status_code == 200:
                    models = response.json()
                    return {
                        'running': True,
                        'models_available': len(models.get('data', [])) > 0,
                        'models_count': len(models.get('data', [])),
                        'url': self.backend_url,
                        'status': 'ready'
                    }
            except Exception as e:
                sanitized_error = self._sanitize_error_response(str(e))
                logger.error(f"Error getting LLM backend status: {sanitized_error}")
        
        return {
            'running': False,
            'models_available': False,
            'models_count': 0,
            'url': self.backend_url,
            'status': 'stopped'
        }

    def download_default_model(self) -> bool:
        """Download default model if none are available"""
        try:
            models = self.find_models()
            if models:
                logger.info(f"Models already available: {len(models)} found")
                return True
            
            # Try to run the download script
            import subprocess
            download_script = Path(os.getcwd()) / "download_default_model.py"
            
            if download_script.exists():
                logger.info("Running default model download script...")
                result = subprocess.run(
                    ["python", str(download_script)],
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )
                
                if result.returncode == 0:
                    logger.info("Default model downloaded successfully")
                    return True
                else:
                    logger.error(f"Model download failed: {result.stderr}")
                    return False
            else:
                logger.error("Download script not found")
                return False
                
        except Exception as e:
            logger.error(f"Error downloading default model: {e}")
            return False

    def health_check(self) -> bool:
        """Perform a comprehensive health check"""
        try:
            # Check if backend is responsive
            if not self.is_backend_running():
                logger.warning("Health check failed: Backend not running")
                return False
            
            # Check if models are available
            status = self.get_backend_status()
            if not status['models_available']:
                logger.warning("Health check failed: No models available")
                return False
            
            logger.info("✅ LLM backend health check passed")
            return True
            
        except Exception as e:
            sanitized_error = self._sanitize_error_response(str(e))
            logger.error(f"Health check error: {sanitized_error}")
            return False


# Thread-safe singleton instance
_llm_backend_manager: Optional['LLMBackendManager'] = None
_llm_backend_manager_lock = threading.Lock()


def get_llm_backend_manager() -> 'LLMBackendManager':
    """Get thread-safe singleton LLM backend manager instance"""
    global _llm_backend_manager
    if _llm_backend_manager is None:
        with _llm_backend_manager_lock:
            # Double-check locking pattern
            if _llm_backend_manager is None:
                _llm_backend_manager = LLMBackendManager()
    return _llm_backend_manager


# Backward compatibility
llm_backend_manager = get_llm_backend_manager()
