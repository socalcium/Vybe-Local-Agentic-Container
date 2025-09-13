"""
Backend LLM Controller for Vybe
Manages llama-cpp-python server for direct LLM inference without external dependencies
"""
import threading
import time
import requests
import os
import signal
import atexit
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class BackendLLMController:
    # Class-level cache for model discovery
    _model_cache = None
    _cache_timestamp = 0
    _cache_ttl = 300  # 5 minutes cache TTL
    _cache_lock = threading.Lock()  # Thread safety for shared cache
    
    def __init__(self, 
                 model_path: Optional[str] = None, 
                 server_host: str = "127.0.0.1", 
                 server_port: int = 11435,  # Different from Flask (8000) and default LLaMA server (11434)
                 n_ctx: Optional[int] = None,
                 n_threads: Optional[int] = None,
                 max_memory_gb: Optional[float] = None):
        """
        Initialize the llama-cpp-python backend controller
        
        Args:
            model_path: Path to GGUF model file. If None, will try to find one in models directory
            server_host: Host to bind the llama-cpp server to
            server_port: Port to bind the llama-cpp server to
            n_ctx: Context size for the model
            n_threads: Number of threads to use
        """
        self.model_path = model_path
        self.server_host = server_host
        self.server_port = server_port
        self.server_url = f"http://{server_host}:{server_port}"
        # Create instance-level lock for this controller's operations
        self.cache_lock = self._cache_lock  # Use the class-level lock
        
        # Enforce hard minimum context; allow overrides upward
        try:
            from ..config import Config
            hard_min_ctx = int(getattr(Config, 'REQUIRED_MIN_CONTEXT_TOKENS', 32768))
        except Exception:
            hard_min_ctx = 32768
        try:
            requested_ctx = int(os.getenv('VYBE_LLM_CTX', str(n_ctx if n_ctx is not None else hard_min_ctx)))
        except Exception:
            requested_ctx = hard_min_ctx
        self.n_ctx = max(requested_ctx, hard_min_ctx)
        try:
            self.n_threads = int(os.getenv('VYBE_LLM_THREADS', str(n_threads if n_threads is not None else 4)))
        except Exception:
            self.n_threads = 4
        try:
            self.max_memory_gb = float(os.getenv('VYBE_LLM_MAX_MEM_GB', str(max_memory_gb if max_memory_gb is not None else 6.0)))
        except Exception:
            self.max_memory_gb = 6.0
        self.server_process = None
        self.server_thread = None
        self.is_running = False
        self._restarting = False
        self._starting = False
        self._shutdown_event = threading.Event()  # Clean shutdown mechanism
        self._cleanup_lock = threading.Lock()  # Thread-safe cleanup
        
        # Try to find a model if none provided
        if not self.model_path:
            self.model_path = self._find_model()
        
        # Register cleanup handlers
        atexit.register(self._cleanup_on_exit)
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown")
        self.stop_server()
        self._cleanup_resources()

    def _cleanup_on_exit(self):
        """Cleanup function registered with atexit"""
        logger.info("Application exiting, cleaning up LLM backend resources")
        self.stop_server()
        self._cleanup_resources()

    def _cleanup_resources(self):
        """Clean up all resources and prevent memory leaks"""
        with self._cleanup_lock:
            try:
                # Stop any running threads
                if self.server_thread and self.server_thread.is_alive():
                    self._shutdown_event.set()
                    self.server_thread.join(timeout=5.0)
                    if self.server_thread.is_alive():
                        logger.warning("Server thread did not terminate gracefully")
                
                # Terminate server process if still running
                if self.server_process and self.server_process.poll() is None:
                    try:
                        self.server_process.terminate()
                        self.server_process.wait(timeout=5.0)
                    except Exception as e:
                        logger.warning(f"Error terminating server process: {e}")
                        try:
                            self.server_process.kill()
                        except Exception:
                            pass
                
                # Clear references
                self.server_process = None
                self.server_thread = None
                self.is_running = False
                
                # Force garbage collection
                import gc
                gc.collect()
                
                logger.info("LLM backend resources cleaned up successfully")
                
            except Exception as e:
                logger.error(f"Error during resource cleanup: {e}")

    def _find_model(self) -> Optional[str]:
        """Find a GGUF model file in the models directories with enhanced error handling and fallback"""
        import time
        
        # Check cache first (thread-safe)
        current_time = time.time()
        with self.cache_lock:
            if (self._model_cache is not None and 
                (current_time - self._cache_timestamp) < self._cache_ttl):
                logger.debug("Using cached model discovery result")
                return self._model_cache
        
        from ..config import Config
        
        # Get all possible models directories (bundled + user)
        try:
            models_dirs = Config.get_models_directories()
        except Exception as e:
            logger.error(f"Failed to get models directories: {e}")
            # Fallback to default models directory
            models_dirs = [Path("models")]
        
        for models_dir in models_dirs:
            if not models_dir.exists():
                logger.debug(f"Models directory does not exist: {models_dir}")
                continue
                
            # Look for GGUF files, prioritizing known good models
            try:
                gguf_files = list(models_dir.glob("*.gguf"))
            except Exception as e:
                logger.warning(f"Error scanning models directory {models_dir}: {e}")
                continue
            
            if not gguf_files:
                logger.debug(f"No GGUF files found in {models_dir}")
                continue
            
            # Use ModelSourcesManager for smart model selection enforcing hard min context
            try:
                from .model_sources_manager import get_model_sources_manager
                sources_manager = get_model_sources_manager()
                
                # Get available models that meet hard minimum context requirement
                try:
                    from ..config import Config
                    hard_min_ctx = int(getattr(Config, 'REQUIRED_MIN_CONTEXT_TOKENS', 32768))
                except Exception:
                    hard_min_ctx = 32768
                
                # For backend, prefer smallest model meeting the min context so front-end/chat can run larger models concurrently
                try:
                    available_models = sources_manager.get_available_models(min_context=hard_min_ctx, prefer_smallest=True)
                    
                    # Find the best locally available model
                    for model_info in available_models:
                        if model_info.get('downloaded') and model_info.get('local_path'):
                            local_path = Path(model_info['local_path'])
                            if local_path.exists():
                                model_path = str(local_path)
                                context_size = model_info.get('context', 'unknown')
                                logger.info(f"Found {context_size}+ context model: {model_path}")
                                # Cache the result (thread-safe)
                                with self.cache_lock:
                                    BackendLLMController._model_cache = model_path
                                    BackendLLMController._cache_timestamp = current_time
                                return model_path
                except Exception as e:
                    logger.warning(f"Failed to get available models from ModelSourcesManager: {e}")
                
            except Exception as e:
                logger.warning(f"Failed to use ModelSourcesManager: {e}")
            
            # Fallback: score files to prefer uncensored + large context
            def _score(p: Path) -> int:
                name = p.name.lower()
                score = 0
                if 'uncensored' in name or 'uncensor' in name or 'no-safety' in name:
                    score += 200
                if 'dolphin' in name or 'hermes' in name or 'openhermes' in name or 'nous' in name:
                    score += 120
                if 'llama3' in name or 'qwen' in name or 'mixtral' in name:
                    score += 80
                if '128k' in name:
                    score += 160
                elif '64k' in name:
                    score += 120
                elif '32k' in name:
                    score += 100
                elif '16k' in name:
                    score += 80
                if 'instruct' in name:
                    score += 20
                if 'q5' in name:
                    score += 15
                if 'q4' in name:
                    score += 10
                if 'q8' in name:
                    score += 5
                return score

            if gguf_files:
                best = sorted(gguf_files, key=_score, reverse=True)[0]
                model_path = str(best)
                logger.info(f"Selected preferred model: {model_path}")
                # Cache the result (thread-safe)
                with self.cache_lock:
                    BackendLLMController._model_cache = model_path
                    BackendLLMController._cache_timestamp = current_time
                return model_path
            
            # No models meeting hard minimum context were found
            logger.error("No local GGUF models meet the required minimum context. Please download a 32k+ context model.")
            return None
        
        logger.warning("No GGUF model files found in any models directory")
        logger.info("Consider running: python download_default_model.py")
        # Cache the negative result too (thread-safe)
        with self.cache_lock:
            BackendLLMController._model_cache = None
            BackendLLMController._cache_timestamp = current_time
        return None

    def find_model_path(self, model_name: Optional[str] = None) -> Optional[str]:
        """
        Find model path by name or return the current model path
        This method is used by the models API
        """
        if model_name:
            # Look for specific model by name
            models_dir = Path(os.getcwd()) / "models"
            if models_dir.exists():
                for gguf_file in models_dir.glob("*.gguf"):
                    if model_name.lower() in gguf_file.name.lower():
                        return str(gguf_file)
            return None
        else:
            # Return current model path or find any available model
            return self.model_path or self._find_model()

    def list_available_models(self) -> list:
        """List all available GGUF model files from all models directories"""
        from ..config import Config
        
        models = []
        models_dirs = Config.get_models_directories()
        
        for models_dir in models_dirs:
            if not models_dir.exists():
                continue
                
            for gguf_file in models_dir.glob("*.gguf"):
                logger.info(f"Found GGUF model: {gguf_file.name}")
                models.append({
                    'name': gguf_file.stem,
                    'path': str(gguf_file),
                    'size': gguf_file.stat().st_size if gguf_file.exists() else 0,
                    'directory': str(models_dir)
                })
        
        if not models:
            logger.warning("No GGUF models found in any models directory")
        
        return models

    def _check_port_available(self) -> bool:
        """Check if the port is available"""
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)  # Quick timeout
                result = sock.connect_ex((self.server_host, self.server_port))
                if result == 0:
                    # Port is in use - check if it's our own server by testing the endpoint
                    try:
                        import requests
                        response = requests.get(f"http://{self.server_host}:{self.server_port}/v1/models", timeout=2)
                        if response.status_code == 200:
                            logger.info(f"LLM server already running on port {self.server_port}")
                            self.is_running = True
                            return True  # Server is running and ready!
                    except requests.exceptions.RequestException as e:
                        logger.debug(f"Port {self.server_port} in use but not responding to API: {e}")
                    except Exception as e:
                        logger.debug(f"Error checking port {self.server_port} API: {e}")
                    
                    logger.error(f"Port {self.server_port} is in use by another process! Will try next available port.")
                    # Try next few ports to avoid startup failure
                    for candidate in range(self.server_port + 1, self.server_port + 6):
                        try:
                            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s2:
                                s2.settimeout(1)  # Quick timeout for port check
                                if s2.connect_ex((self.server_host, candidate)) == 0:
                                    # Port is in use, try next
                                    continue
                                else:
                                    # Port is available
                                    self.server_port = candidate
                                    self.server_url = f"http://{self.server_host}:{self.server_port}"
                                    logger.info(f"Selected fallback port {self.server_port} for LLM server")
                                    return True
                        except Exception as e:
                            logger.debug(f"Error checking fallback port {candidate}: {e}")
                            continue
                    logger.error("No available ports found in range")
                    return False
                return True
        except Exception as e:
            logger.warning(f"Port check failed: {e}")
            return True  # Assume available on error

    def start_server(self) -> bool:
        """Start the llama-cpp-python server in a background thread with enhanced error handling"""
        if self.is_running:
            logger.info("LLM server is already running")
            return True
        
        # CRITICAL: Check if port is already in use to prevent multiple instances
        try:
            port_available = self._check_port_available()
            if not port_available and not self.is_running:
                logger.error(f"Cannot start LLM server - port {self.server_port} in use by another process")
                return False
            elif self.is_running:
                logger.info("LLM server already running and ready")
                return True
        except Exception as e:
            logger.error(f"Port availability check failed: {e}")
            return False
            
        # Validate model path with enhanced error handling
        if not self.model_path:
            logger.error("No model path specified")
            # Try to find a model
            self.model_path = self._find_model()
            if not self.model_path:
                logger.error("No model found and no model path specified")
                return False
        
        if not os.path.exists(self.model_path):
            logger.error(f"Model file not found: {self.model_path}")
            # Try to find a different model
            logger.info("Attempting to find alternative model...")
            self.model_path = self._find_model()
            if not self.model_path or not os.path.exists(self.model_path):
                logger.error("No valid model files found")
                return False
            
        logger.info(f"Starting llama-cpp-python server on {self.server_url}")
        logger.info(f"Model: {self.model_path}")
        
        def run_server():
            try:
                # Try to import llama-cpp-python components
                try:
                    import uvicorn
                    from llama_cpp.server.app import create_app
                    from llama_cpp.server.settings import Settings
                except ImportError as e:
                    logger.error(f"llama-cpp-python not installed: {e}")
                    logger.info("Please install with: pip install llama-cpp-python[server]")
                    self.is_running = False
                    return
                
                # Ensure we have a model path
                if not self.model_path:
                    logger.error("No model path specified")
                    self.is_running = False
                    return
                
                # Validate model file before starting server
                if not os.path.exists(self.model_path):
                    logger.error(f"Model file not found during server startup: {self.model_path}")
                    self.is_running = False
                    return
                
                # Check file size to ensure it's a valid model
                try:
                    file_size = os.path.getsize(self.model_path)
                    if file_size < 1024 * 1024:  # Less than 1MB
                        logger.error(f"Model file appears to be too small: {file_size} bytes")
                        self.is_running = False
                        return
                except Exception as e:
                    logger.error(f"Error checking model file size: {e}")
                    self.is_running = False
                    return
                
                # Configure server settings with MEMORY LIMITS
                # Calculate memory allocation (in MB)
                max_memory_mb = int(self.max_memory_gb * 1024)
                
                # Enforce hard minimum context for backend; no mobile downscale
                try:
                    from ..config import Config
                    hard_min_ctx = int(getattr(Config, 'REQUIRED_MIN_CONTEXT_TOKENS', 32768))
                except Exception:
                    hard_min_ctx = 32768
                effective_n_ctx = max(self.n_ctx, hard_min_ctx)

                # Adjust threads/batch based on hardware tier (no context scaling)
                try:
                    from ..core.hardware_manager import get_hardware_manager
                    hw_tier = get_hardware_manager().performance_tier or 'mid_range'
                    if hw_tier == 'high_end':
                        self.n_threads = max(2, min(self.n_threads, 12))
                        n_batch = 512
                    elif hw_tier == 'mid_range':
                        self.n_threads = max(2, min(self.n_threads, 8))
                        n_batch = 384
                    else:
                        self.n_threads = max(2, min(self.n_threads, 4))
                        n_batch = 256
                except Exception:
                    n_batch = 256

                settings = Settings(
                    model=str(self.model_path),  # Required field
                    host=self.server_host,
                    port=self.server_port,
                    n_ctx=effective_n_ctx,
                    n_threads=self.n_threads,
                    verbose=False,
                    # MEMORY SAFETY: Valid parameters only
                    n_gpu_layers=0,       # Force CPU-only to limit memory usage
                    use_mlock=False,      # Don't lock memory (prevents bluescreens)
                    use_mmap=True,        # Use memory mapping for efficiency
                    embedding=False,      # Disable embeddings (saves memory)
                    logits_all=False,     # Don't store all logits (saves memory)
                    n_batch=n_batch,      # Batch size tuned by hardware tier
                    flash_attn=False,     # Disable flash attention for stability
                )
                
                # Create the FastAPI app
                app = create_app(settings=settings)
                
                # Run with uvicorn - configured to avoid Flask conflicts
                config = uvicorn.Config(
                    app=app,
                    host=self.server_host,
                    port=self.server_port,
                    log_level="warning",      # Reduce logging noise
                    access_log=False,         # Disable access logs
                    server_header=False,      # Don't add server header
                    date_header=False,        # Don't add date header
                    use_colors=False,         # Disable colored output
                    loop="asyncio",           # Use asyncio loop
                    lifespan="off",           # Disable lifespan events
                )
                
                server = uvicorn.Server(config)
                # Limit number of concurrent worker threads to cap CPU usage implicitly
                try:
                    import multiprocessing
                    cpu_count = max(1, multiprocessing.cpu_count() - 1)
                except Exception:
                    cpu_count = 1
                # Respect explicit threads setting, but stay within safe bounds
                safe_threads = max(1, min(self.n_threads, cpu_count))
                self.n_threads = safe_threads
                logger.info(f"LLM server starting with n_threads={self.n_threads}, n_ctx={effective_n_ctx}")
                server.run()
                
            except Exception as e:
                logger.error(f"Error starting llama-cpp server: {e}")
                self.is_running = False
        
        # Start server in background thread
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        
        # Wait for server to start
        for i in range(30):  # 30 second timeout
            try:
                response = requests.get(f"{self.server_url}/v1/models", timeout=10)
                if response.status_code == 200:
                    self.is_running = True
                    logger.info("LLM server started successfully")
                    return True
            except requests.exceptions.RequestException:
                time.sleep(1)
        
        logger.error("Failed to start LLM server within timeout")
        return False

    def stop_server(self):
        """Stop the llama-cpp-python server and clean up resources"""
        logger.info("Stopping LLM server and cleaning up resources...")
        
        # Set shutdown event
        self._shutdown_event.set()
        self.is_running = False
        
        # Try to gracefully shutdown the server
        try:
            if self.server_thread and self.server_thread.is_alive():
                # Try to send shutdown request to server
                try:
                    requests.post(f"{self.server_url}/shutdown", timeout=5)
                except Exception as e:
                    logger.debug(f"Server shutdown endpoint not supported: {e}")
                    pass  # Server might not support shutdown endpoint
                
                # Wait for thread to finish
                self.server_thread.join(timeout=10)
                
                if self.server_thread.is_alive():
                    logger.warning("Server thread did not stop gracefully")
                else:
                    logger.info("LLM server stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping LLM server: {e}")
        
        # Force cleanup
        self.server_thread = None
        self.server_process = None
        
        # CRITICAL: Force garbage collection to free model memory
        import gc
        gc.collect()
        
        logger.info("LLM server cleanup completed")

    def is_server_ready(self) -> bool:
        """Check if the server is ready to accept requests"""
        # Try active flag first, but don't rely on it exclusively
        try:
            response = requests.get(f"{self.server_url}/v1/models", timeout=5)
            if response.status_code == 200:
                self.is_running = True
                return True
        except requests.exceptions.RequestException:
            pass
        return False

    def generate_completion(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> str:
        """Generate a text completion using the local LLM server"""
        if not self.is_server_ready():
            logger.error("LLM server is not ready")
            return ""
        
        try:
            response = requests.post(
                f"{self.server_url}/v1/completions",
                json={
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "stream": False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("choices", [{}])[0].get("text", "")
            else:
                logger.error(f"LLM server error: {response.status_code}")
                return ""
                
        except Exception as e:
            logger.error(f"Error generating completion: {e}")
            return ""

    def generate_response(self, prompt: str, system_prompt: Optional[str] = None, max_tokens: int = 1024, temperature: float = 0.7) -> str:
        """
        Generate a response using the local LLM server with an optional system prompt.
        This method is required by the agent_manager for planning operations.
        
        Args:
            prompt: The user prompt to process
            system_prompt: Optional system prompt to provide context
            max_tokens: Maximum tokens in response
            temperature: Temperature for generation
            
        Returns:
            Generated response text
        """
        if not self.is_server_ready():
            logger.error("LLM server is not ready")
            return "Error: LLM backend not available. Please ensure the model is loaded."
        
        try:
            # Construct the full prompt with system context if provided
            if system_prompt:
                full_prompt = f"{system_prompt}\n\nUser: {prompt}\n\nAssistant:"
            else:
                full_prompt = prompt
            
            # Use the chat completions endpoint for better formatting
            response = requests.post(
                f"{self.server_url}/v1/chat/completions",
                json={
                    "messages": [
                        {"role": "system", "content": system_prompt or "You are a helpful AI assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "stream": False
                },
                timeout=60  # Longer timeout for complex responses
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                if not content:
                    # Fallback to completions-style text
                    content = result.get("choices", [{}])[0].get("text", "")
                return content
            else:
                # Fallback to completions endpoint if chat endpoint fails
                logger.warning(f"Chat endpoint failed with {response.status_code}, trying completions endpoint")
                return self.generate_completion(full_prompt, max_tokens, temperature)
                
        except requests.exceptions.Timeout:
            logger.error("LLM server timeout - request took too long")
            return "Error: Request timeout. The model may be processing a complex request."
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            # Fallback to simple completion
            try:
                return self.generate_completion(prompt, max_tokens, temperature)
            except Exception as fallback_error:
                logger.error(f"Fallback completion also failed: {fallback_error}")
                return f"Error generating response: {str(e)}"

    def generate_summary_and_tags(self, content: str) -> Dict[str, Any]:
        """Generate summary and tags for given content"""
        if not self.is_server_ready():
            return {"summary": "LLM server not available", "tags": []}
        
        # Truncate content if too long
        if len(content) > 2000:
            content = content[:2000] + "..."
        
        prompt = f"""Analyze the following document and provide:
1. A concise summary (2-3 sentences)
2. Relevant tags (up to 5 keywords)

Document:
{content}

Response format:
Summary: [your summary here]
Tags: tag1, tag2, tag3, tag4, tag5"""

        response_text = self.generate_completion(prompt, max_tokens=256, temperature=0.3)
        
        # Parse the response
        summary = ""
        tags = []
        
        if response_text:
            lines = response_text.strip().split('\n')
            for line in lines:
                if line.startswith("Summary:"):
                    summary = line.replace("Summary:", "").strip()
                elif line.startswith("Tags:"):
                    tag_text = line.replace("Tags:", "").strip()
                    tags = [tag.strip() for tag in tag_text.split(",") if tag.strip()]
        
        return {
            "summary": summary or "Unable to generate summary",
            "tags": tags[:5]  # Limit to 5 tags
        }

# Global instance
_backend_controller: Optional[BackendLLMController] = None

def get_backend_controller() -> BackendLLMController:
    """Get or create the global backend controller instance"""
    global _backend_controller
    if _backend_controller is None:
        _backend_controller = BackendLLMController()
    return _backend_controller

def start_backend_llm():
    """Start the backend LLM server"""
    controller = get_backend_controller()
    return controller.start_server()

def stop_backend_llm():
    """Stop the backend LLM server"""
    controller = get_backend_controller()
    controller.stop_server()

def emergency_cleanup():
    """Emergency cleanup function to prevent memory leaks on app shutdown"""
    logger.warning("EMERGENCY CLEANUP: Forcing LLM backend shutdown")
    global _backend_controller
    
    if _backend_controller:
        try:
            _backend_controller.stop_server()
        except Exception as e:
            logger.error(f"Error during emergency cleanup: {e}")
    
    # Force aggressive garbage collection
    import gc
    gc.collect()
    gc.collect()  # Run twice for thorough cleanup
    
    logger.info("Emergency cleanup completed")

# Register emergency cleanup for app shutdown
import atexit
atexit.register(emergency_cleanup)

# Create global instance for import
llm_controller = get_backend_controller()
