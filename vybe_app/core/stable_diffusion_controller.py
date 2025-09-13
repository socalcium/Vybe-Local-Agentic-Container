"""
Stable Diffusion Controller for Vybe
Manages the lifecycle of AUTOMATIC1111 Stable Diffusion WebUI instance
Provides automated installation, on-demand loading, and unified management
"""

import os
import sys
import json
import time
import requests
import subprocess
import threading
from pathlib import Path
from typing import Optional, Dict, List, Any, TextIO
from urllib.parse import urljoin
import base64
from io import BytesIO
# PIL import moved to function level to prevent memory leaks

from ..logger import logger
from ..config import Config


class StableDiffusionController:
    """Singleton controller for managing AUTOMATIC1111 Stable Diffusion WebUI"""
    
    _instance = None
    _lock = threading.Lock()
    _init_lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Thread-safe initialization check
        with self._init_lock:
            if hasattr(self, 'initialized'):
                return
            
            self.initialized = True
            self.process: Optional[subprocess.Popen] = None
            self._log_file: Optional[TextIO] = None  # Handle for log file
            self.base_url = "http://127.0.0.1:7860"
            self.api_timeout = 30
            self.startup_timeout = 300  # Increased timeout for slower systems and first-time setup
            
            # Paths - Use user data directory instead of Program Files
            import os
            self.vybe_root = Path(__file__).parent.parent.parent
            
            # Use user's AppData for vendor and workspace directories
            if os.name == 'nt':  # Windows
                self.user_data_dir = Path(os.path.expanduser("~")) / "AppData" / "Local" / "Vybe AI Assistant"
            else:  # Linux/Mac
                self.user_data_dir = Path(os.path.expanduser("~")) / ".local" / "share" / "vybe-ai-assistant"
                
            self.vendor_dir = self.user_data_dir / "vendor"
            self.sd_dir = self.vendor_dir / "stable-diffusion-webui"
            self.workspace_dir = self.user_data_dir / "workspace"
            self.images_dir = self.workspace_dir / "generated_images"
            
            # Ensure directories exist
            self.vendor_dir.mkdir(parents=True, exist_ok=True)
            self.workspace_dir.mkdir(parents=True, exist_ok=True)
            self.images_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"StableDiffusionController initialized - SD dir: {self.sd_dir}")
            logger.info(f"Images will be saved to: {self.images_dir}")
            logger.info(f"SD WebUI logs will be written to: {self.user_data_dir / 'logs' / 'sd_webui.log'}")
    
    def _cleanup_log_file(self, log_file):
        """Helper method to safely close log file handle"""
        if log_file and not log_file.closed:
            try:
                log_file.close()
            except Exception as e:
                logger.debug(f"Error closing log file: {e}")
    
    def _ensure_launch_scripts(self) -> bool:
        """Ensure launch scripts exist and are properly configured"""
        try:
            if os.name == 'nt':  # Windows
                # Check for webui-user.bat first (preferred)
                script_user = self.sd_dir / "webui-user.bat"
                script_main = self.sd_dir / "webui.bat"
                webui_py = self.sd_dir / "webui.py"
                
                # If webui.py exists but no .bat files, create webui-user.bat
                if webui_py.exists() and not script_user.exists() and not script_main.exists():
                    logger.info("Creating webui-user.bat launcher script")
                    script_content = """@echo off
set COMMANDLINE_ARGS=--api --skip-torch-cuda-test --no-half-vae --listen --port 7860 --cors-allow-origins=http://localhost:8000,http://127.0.0.1:8000
call webui.bat
"""
                    try:
                        with open(script_user, 'w', encoding='utf-8') as f:
                            f.write(script_content)
                        logger.info(f"Created launch script: {script_user}")
                        return True
                    except Exception as e:
                        logger.warning(f"Failed to create webui-user.bat: {e}")
                        return False
                        
            return True  # Scripts already exist or not Windows
        except Exception as e:
            logger.error(f"Error ensuring launch scripts: {e}")
            return False

    def check_and_install(self) -> bool:
        """Check for AUTOMATIC1111 installation and install if needed"""
        try:
            # Check Git availability with better error handling
            git_available = self._check_git_availability()
            if not git_available:
                logger.error("Git not found in PATH. Please install Git from https://git-scm.com/")
                logger.error("AUTOMATIC1111 installation requires Git to clone the repository.")
                return False

            if self.sd_dir.exists():
                # Check if essential files exist (not just folder)
                essential_files = [
                    self.sd_dir / "webui.py",
                    self.sd_dir / "launch.py", 
                    self.sd_dir / "modules",
                    self.sd_dir / "repositories"
                ]
                
                # Check if we have main script OR batch file, plus other essentials  
                has_main_script = (self.sd_dir / "webui.py").exists() or (self.sd_dir / "webui.bat").exists()
                has_essential_dirs = (self.sd_dir / "modules").exists() and (self.sd_dir / "repositories").exists()
                
                if has_main_script and has_essential_dirs:
                    logger.info("AUTOMATIC1111 Stable Diffusion WebUI already installed and complete")
                    # Ensure launch scripts are properly configured
                    self._ensure_launch_scripts()
                    return self._check_default_model()
                else:
                    missing_items = []
                    if not has_main_script:
                        missing_items.append("webui.py/webui.bat")
                    if not (self.sd_dir / "modules").exists():
                        missing_items.append("modules/")
                    if not (self.sd_dir / "repositories").exists():
                        missing_items.append("repositories/")
                    logger.warning(f"SD directory exists but missing essential components: {missing_items}")
                    logger.info("SD directory exists without webui.py; attempting to repair via git fetch/reset")
                    repaired = False
                    try:
                        result = subprocess.run(
                            ["git", "-C", str(self.sd_dir), "fetch"],
                            capture_output=True, text=True, timeout=120
                        )
                        if result.returncode == 0:
                            logger.info("Git fetch succeeded; running git reset --hard origin/master")
                            subprocess.run(["git", "-C", str(self.sd_dir), "reset", "--hard", "origin/master"],
                                           capture_output=True, text=True, timeout=120)
                            repaired = (self.sd_dir / "webui.py").exists() or (self.sd_dir / "webui.bat").exists()
                        else:
                            logger.warning("Git fetch failed; will attempt clean reinstall")
                    except Exception as e:
                        logger.warning(f"SD repair attempt failed: {e}")
                    
                    if not repaired:
                        # Delete and reclone cleanly
                        try:
                            import shutil
                            shutil.rmtree(self.sd_dir, ignore_errors=True)
                            logger.info("Removed incomplete SD directory; re-cloning fresh copy")
                        except Exception as e:
                            logger.warning(f"Failed to remove SD directory: {e}")
                    # Proceed to clone below
            
            logger.info("Installing AUTOMATIC1111 Stable Diffusion WebUI...")
            logger.info(f"Cloning to: {self.sd_dir}")
            
            # Clone the repository (with one retry if needed)
            def _clone_repo() -> subprocess.CompletedProcess:
                cmd_local = [
                    "git", "clone",
                    "https://github.com/AUTOMATIC1111/stable-diffusion-webui.git",
                    str(self.sd_dir)
                ]
                logger.info(f"Running command: {' '.join(cmd_local)}")
                return subprocess.run(
                    cmd_local,
                    capture_output=True,
                    text=True,
                    timeout=600,
                    cwd=self.vendor_dir
                )

            result = _clone_repo()
            if result.returncode != 0:
                stderr_lower = (result.stderr or '').lower()
                if 'already exists and is not an empty directory' in stderr_lower:
                    # Verify content; if missing, remove and retry once
                    has_scripts = (self.sd_dir / "webui.py").exists() or (self.sd_dir / "webui.bat").exists()
                    if not has_scripts:
                        logger.warning("SD dir exists but missing launch scripts; removing and retrying clone once")
                        try:
                            import shutil
                            shutil.rmtree(self.sd_dir, ignore_errors=True)
                        except Exception:
                            pass
                        result = _clone_repo()
                
            if result.returncode != 0:
                logger.error(f"Failed to clone SD WebUI. Return code: {result.returncode}")
                logger.error(f"STDOUT: {result.stdout}")
                logger.error(f"STDERR: {result.stderr}")
                return False

            logger.info("Successfully cloned AUTOMATIC1111 Stable Diffusion WebUI")
            logger.info(f"STDOUT: {result.stdout}")
            
            # Verify expected launch scripts exist with short settle loop (handles slow AV scanning)
            settle_ok = False
            for _ in range(20):  # up to ~10s
                if (self.sd_dir / "webui.py").exists() or (self.sd_dir / "webui.bat").exists():
                    settle_ok = True
                    break
                time.sleep(0.5)
            if not settle_ok:
                logger.error("Clone completed but launch scripts not found after settle; repository structure unexpected")
                # Try to create missing launch scripts before failing
                if self._ensure_launch_scripts():
                    logger.info("Created missing launch scripts after clone")
                else:
                    return False
            
            # Ensure launch scripts exist
            self._ensure_launch_scripts()
            
            return self._check_default_model()
            
        except subprocess.TimeoutExpired:
            logger.error("Git clone timed out after 10 minutes")
            return False
        except FileNotFoundError:
            logger.error("Git command not found. Please install Git and ensure it's in your PATH")
            return False
        except Exception as e:
            logger.error(f"Error during SD WebUI installation: {e}", exc_info=True)
            return False
    
    def is_installed(self) -> bool:
        """Check if Stable Diffusion WebUI is installed"""
        try:
            # Check if SD directory exists and has essential files
            if not self.sd_dir.exists():
                return False
            
            # Check for essential files that indicate a complete installation
            essential_files = ["webui.py", "webui.bat"]
            has_essential = any((self.sd_dir / file).exists() for file in essential_files)
            
            return has_essential
        except Exception as e:
            logger.error(f"Error checking SD installation: {e}")
            return False
    
    def _check_git_availability(self) -> bool:
        """Check if Git is available and working"""
        try:
            import shutil
            git_path = shutil.which("git")
            if git_path is None:
                logger.error("Git not found in PATH")
                return False
            
            # Test Git functionality
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                logger.info(f"Git found: {result.stdout.strip()}")
                return True
            else:
                logger.error(f"Git test failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Git version check timed out")
            return False
        except Exception as e:
            logger.error(f"Error checking Git availability: {e}")
            return False
    
    def _check_default_model(self) -> bool:
        """Check for at least one model and download default if none exists"""
        try:
            models_dir = self.sd_dir / "models" / "Stable-diffusion"
            models_dir.mkdir(parents=True, exist_ok=True)
            
            # Check for existing models
            model_files = list(models_dir.glob("*.safetensors")) + list(models_dir.glob("*.ckpt"))
            
            if model_files:
                logger.info(f"Found {len(model_files)} existing model(s):")
                for model_file in model_files:
                    logger.info(f"  - {model_file.name}")
                return True
            
            logger.info("No models found, downloading default model...")
            
            # Download v1-5-pruned-emaonly.safetensors
            model_url = "https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors"
            model_path = models_dir / "v1-5-pruned-emaonly.safetensors"
            
            logger.info(f"Downloading model from: {model_url}")
            logger.info(f"Saving to: {model_path}")
            
            response = requests.get(model_url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            logger.info(f"Model size: {total_size / (1024*1024*1024):.2f} GB")
            
            downloaded_size = 0
            last_log_size = 0
            
            with open(model_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # Log progress every 100MB
                        if downloaded_size - last_log_size > 100 * 1024 * 1024:
                            if total_size > 0:
                                progress = (downloaded_size / total_size) * 100
                                logger.info(f"Download progress: {progress:.1f}% ({downloaded_size / (1024*1024):.1f} MB)")
                            else:
                                logger.info(f"Downloaded: {downloaded_size / (1024*1024):.1f} MB")
                            last_log_size = downloaded_size
            
            logger.info(f"Successfully downloaded default model to {model_path}")
            logger.info(f"Final size: {model_path.stat().st_size / (1024*1024*1024):.2f} GB")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error downloading default model: {e}")
            return False
        except Exception as e:
            logger.error(f"Error checking/downloading default model: {e}", exc_info=True)
            return False
    
    def start(self) -> bool:
        """Start the Stable Diffusion WebUI service with robust subprocess management"""
        try:
            # Respect config to avoid auto-launching external apps unless allowed
            if not Config.AUTO_LAUNCH_EXTERNAL_APPS:
                logger.info("AUTO_LAUNCH_EXTERNAL_APPS is disabled; skipping SD WebUI start")
                return False
            # Check if already running
            if self.is_running():
                logger.info("Stable Diffusion WebUI is already running")
                return True
            
            # Ensure SD WebUI is installed
            if not self.check_and_install():
                logger.error("Failed to install or verify SD WebUI")
                return False
            
            logger.info("Starting Stable Diffusion WebUI...")
            
            # Cross-platform script determination with proper command structure
            if os.name == "nt":  # Windows
                # Prefer the batch script to allow A1111 to manage its environment
                script_user = self.sd_dir / "webui-user.bat"
                script_main = self.sd_dir / "webui.bat"
                webui_py = self.sd_dir / "webui.py"
                if script_user.exists():
                    cmd = ["cmd.exe", "/c", str(script_user)]
                elif script_main.exists():
                    cmd = ["cmd.exe", "/c", str(script_main)]
                elif webui_py.exists():
                    # Last resort: direct Python
                    cmd = [sys.executable, str(webui_py)]
                else:
                    logger.error("No launch script or webui.py found for SD WebUI")
                    return False
            else:  # Unix-like systems (Linux, macOS)
                script_path = self.sd_dir / "webui.sh"
                webui_py = self.sd_dir / "webui.py"
                if script_path.exists():
                    script_path.chmod(0o755)
                    cmd = ["/bin/bash", str(script_path)]
                elif webui_py.exists():
                    cmd = [sys.executable, str(webui_py)]
                else:
                    logger.error("No launch script or webui.py found for SD WebUI")
                    return False
            
            # Verify launch target exists
            try:
                launch_target = cmd[-1]
                if launch_target.endswith(".bat") or launch_target.endswith(".sh") or launch_target.endswith("webui.py"):
                    lt_path = self.sd_dir / (launch_target if os.path.isabs(launch_target) else Path(launch_target).name)
                    if not lt_path.exists():
                        logger.error(f"Launch target not found: {lt_path}")
                        return False
            except Exception:
                pass
            
            # Prepare robust environment variables
            env = os.environ.copy()
            # Enhanced command line arguments for API access and stability
            # Use direct arguments when launching webui.py directly
            if cmd and str(cmd[0]).endswith("python.exe") or (len(cmd) > 1 and str(cmd[1]).endswith("webui.py")):
                # Add arguments directly to command when using webui.py
                cmd.extend([
                    "--api", 
                    "--skip-torch-cuda-test", 
                    "--no-half-vae", 
                    "--listen", 
                    "--port", "7860", 
                    "--enable-insecure-extension-access"
                ])
            else:
                # Use environment variable for batch/shell scripts
                env["COMMANDLINE_ARGS"] = "--api --skip-torch-cuda-test --no-half-vae --listen --port 7860 --enable-insecure-extension-access"
            
            # Ensure logs directory exists
            logs_dir = self.user_data_dir / "logs"
            logs_dir.mkdir(exist_ok=True)
            log_file_path = logs_dir / "sd_webui.log"
            
            logger.info(f"SD WebUI command: {cmd}")
            logger.info(f"SD WebUI working directory: {self.sd_dir}")
            logger.info(f"SD WebUI log file: {log_file_path}")
            logger.info(f"Platform: {os.name} ({sys.platform})")
            
            # Initialize log file with startup information
            try:
                with open(log_file_path, 'w', encoding='utf-8') as log_init:
                    log_init.write(f"=== Stable Diffusion WebUI Startup Log ===\n")
                    log_init.write(f"Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    log_init.write(f"Platform: {os.name} ({sys.platform})\n")
                    log_init.write(f"Command: {cmd}\n")
                    log_init.write(f"Working Directory: {self.sd_dir}\n")
                    log_init.write(f"Environment Args: {env.get('COMMANDLINE_ARGS', 'None')}\n")
                    log_init.write("=" * 50 + "\n\n")
                    log_init.flush()
            except Exception as e:
                logger.error(f"Failed to initialize log file: {e}")
                return False
            
            # Start subprocess with comprehensive output logging
            log_file = None
            try:
                # Open log file for continuous writing with line buffering
                log_file = open(log_file_path, 'a', encoding='utf-8', buffering=1)
                
                # Platform-specific subprocess configuration
                if os.name == "nt":  # Windows
                    # Windows: Hide console window and use proper subprocess flags
                    startup_info = subprocess.STARTUPINFO()
                    startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startup_info.wShowWindow = subprocess.SW_HIDE
                    
                    self.process = subprocess.Popen(
                        cmd,
                        cwd=str(self.sd_dir),
                        env=env,
                        stdout=log_file,
                        stderr=subprocess.STDOUT,
                        stdin=subprocess.DEVNULL,
                        startupinfo=startup_info,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        text=True,
                        bufsize=1
                    )
                else:  # Unix-like systems
                    # Unix-like systems: Standard configuration
                    self.process = subprocess.Popen(
                        cmd,
                        cwd=str(self.sd_dir),
                        env=env,
                        stdout=log_file,
                        stderr=subprocess.STDOUT,
                        stdin=subprocess.DEVNULL,
                        text=True,
                        bufsize=1
                    )
                
                logger.info(f"SD WebUI process started successfully with PID: {self.process.pid}")

                # Attempt to lower process priority to reduce resource contention
                try:
                    import psutil  # type: ignore
                    proc = psutil.Process(self.process.pid)
                    if os.name == "nt":
                        proc.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
                    else:
                        try:
                            proc.nice(10)
                        except Exception:
                            pass
                    logger.info("SD WebUI process priority lowered for system safety")
                except Exception as e:
                    logger.debug(f"Unable to adjust SD WebUI process priority: {e}")
                
                # Store log file handle for proper cleanup
                self._log_file = log_file
                
                # Wait for the service to become fully ready
                if self._wait_for_service_ready():
                    logger.info("Stable Diffusion WebUI started successfully and is ready for requests")
                    return True
                else:
                    logger.error("Stable Diffusion WebUI failed to become ready within timeout")
                    self._log_recent_output()
                    self.stop()
                    return False
                    
            except FileNotFoundError as e:
                logger.error(f"Command not found - ensure required executables are in PATH: {e}")
                self._cleanup_log_file(log_file)
                return False
            except PermissionError as e:
                logger.error(f"Permission denied when starting SD WebUI: {e}")
                self._cleanup_log_file(log_file)
                return False
            except Exception as e:
                logger.error(f"Failed to start SD WebUI process: {e}", exc_info=True)
                self._cleanup_log_file(log_file)
                return False
                
        except Exception as e:
            logger.error(f"Unexpected error starting SD WebUI: {e}", exc_info=True)
            # Ensure log file is cleaned up even in unexpected errors
            if 'log_file' in locals():
                self._cleanup_log_file(log_file)
            return False
    
    def _wait_for_service_ready(self) -> bool:
        """Wait for the SD WebUI service to become fully ready with comprehensive health checks"""
        start_time = time.time()
        logger.info(f"Waiting for SD WebUI to become ready (timeout: {self.startup_timeout}s)")
        
        # Health check endpoints to try in order of reliability
        health_endpoints = [
            ("/sdapi/v1/progress", "progress endpoint"),
            ("/sdapi/v1/models", "models endpoint"),
            ("/sdapi/v1/samplers", "samplers endpoint"),
        ]
        
        last_log_time = start_time
        check_interval = 5  # Check every 5 seconds
        consecutive_successes = 0  # Track consecutive successful checks
        required_successes = 2  # Require 2 consecutive successes for stability
        
        while time.time() - start_time < self.startup_timeout:
            current_time = time.time()
            elapsed = current_time - start_time
            
            # Log progress every 20 seconds
            if current_time - last_log_time >= 20:
                logger.info(f"Still waiting for SD WebUI... ({elapsed:.1f}s elapsed)")
                last_log_time = current_time
                
                # Also log recent output for debugging
                if elapsed > 60:  # After 1 minute, start showing log excerpts
                    self._log_recent_output_excerpt()
            
            # Check if process is still running
            if self.process and self.process.poll() is not None:
                logger.error(f"SD WebUI process terminated unexpectedly with return code: {self.process.returncode}")
                self._log_recent_output()
                return False
            
            # Try health check endpoints
            service_ready = False
            for endpoint, description in health_endpoints:
                try:
                    url = f"{self.base_url}{endpoint}"
                    response = requests.get(url, timeout=10)
                    
                    if response.status_code == 200:
                        # Additional validation for specific endpoints
                        if endpoint == "/sdapi/v1/progress":
                            try:
                                progress_data = response.json()
                                if isinstance(progress_data, dict):
                                    logger.debug(f"Health check passed on {description}")
                                    service_ready = True
                                    break
                            except Exception:
                                # If we can parse the response as JSON, consider it ready
                                logger.debug(f"Health check passed on {description} (JSON parse issue)")
                                service_ready = True
                                break
                        else:
                            logger.debug(f"Health check passed on {description}")
                            service_ready = True
                            break
                    else:
                        logger.debug(f"Health check {description} returned status: {response.status_code}")
                        
                except requests.exceptions.ConnectionError:
                    # Expected during startup - service not yet accepting connections
                    logger.debug(f"Connection refused on {description} - still starting")
                except requests.exceptions.Timeout:
                    logger.debug(f"Timeout on {description} - service may be slow to respond")
                except Exception as e:
                    logger.debug(f"Health check error on {description}: {e}")
            
            if service_ready:
                consecutive_successes += 1
                logger.debug(f"Health check success {consecutive_successes}/{required_successes}")
                
                if consecutive_successes >= required_successes:
                    # Perform final comprehensive check
                    if self._comprehensive_health_check():
                        logger.info(f"SD WebUI is fully ready and stable after {elapsed:.1f} seconds")
                        return True
                    else:
                        logger.warning("Comprehensive health check failed, resetting success counter")
                        consecutive_successes = 0
            else:
                # Reset success counter if health check fails
                consecutive_successes = 0
            
            time.sleep(check_interval)
        
        logger.error(f"SD WebUI failed to become ready within {self.startup_timeout} seconds")
        self._log_recent_output()
        return False
    
    def _comprehensive_health_check(self) -> bool:
        """Perform a comprehensive health check to ensure SD WebUI is fully operational"""
        try:
            # Test multiple endpoints to ensure full functionality
            endpoints_to_test = [
                ("/sdapi/v1/progress", "progress"),
                ("/sdapi/v1/sd-models", "sd-models"),  # Changed from models to sd-models
                ("/sdapi/v1/samplers", "samplers")
            ]
            
            successful_checks = 0
            total_checks = len(endpoints_to_test)
            
            for endpoint, name in endpoints_to_test:
                try:
                    response = requests.get(f"{self.base_url}{endpoint}", timeout=15)
                    if response.status_code == 200:
                        successful_checks += 1
                        
                        # Additional validation for specific endpoints
                        if endpoint == "/sdapi/v1/sd-models":
                            try:
                                models = response.json()
                                if isinstance(models, list):
                                    model_count = len(models)
                                    logger.info(f"Found {model_count} available SD models")
                                    if model_count == 0:
                                        logger.warning("No SD models available - this may cause issues")
                                else:
                                    logger.warning("SD models endpoint returned unexpected format")
                            except Exception as e:
                                logger.warning(f"Failed to parse SD models response: {e}")
                        
                        elif endpoint == "/sdapi/v1/progress":
                            try:
                                progress = response.json()
                                if isinstance(progress, dict):
                                    logger.debug("Progress endpoint validated successfully")
                            except Exception as e:
                                logger.debug(f"Progress endpoint JSON parse issue: {e}")
                                
                        logger.debug(f"Health check passed for {name}")
                    else:
                        logger.warning(f"Health check failed for {name}: status {response.status_code}")
                        
                except requests.exceptions.Timeout:
                    logger.warning(f"Health check timeout for {name}")
                except requests.exceptions.ConnectionError:
                    logger.warning(f"Connection error for {name}")
                except Exception as e:
                    logger.warning(f"Health check error for {name}: {e}")
            
            # Consider it successful if at least 2/3 of checks pass (with progress being mandatory)
            success_threshold = max(1, total_checks - 1)  # Allow one failure
            
            if successful_checks >= success_threshold:
                logger.info(f"Comprehensive health check passed ({successful_checks}/{total_checks} endpoints)")
                return True
            else:
                logger.warning(f"Comprehensive health check failed ({successful_checks}/{total_checks} endpoints)")
                return False
            
        except Exception as e:
            logger.warning(f"Comprehensive health check failed with exception: {e}")
            return False
    
    def _log_recent_output(self):
        """Log recent output from the SD WebUI process for debugging"""
        try:
            logs_dir = self.user_data_dir / "logs"
            log_file_path = logs_dir / "sd_webui.log"
            
            if log_file_path.exists():
                with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    # Get last 20 lines
                    recent_lines = lines[-20:] if len(lines) > 20 else lines
                    
                if recent_lines:
                    logger.error("Recent SD WebUI output:")
                    for line in recent_lines:
                        logger.error(f"SD: {line.rstrip()}")
                else:
                    logger.error("No recent output found in SD WebUI log")
            else:
                logger.error("SD WebUI log file not found")
                
        except Exception as e:
            logger.error(f"Failed to read SD WebUI log: {e}")
    
    def _log_recent_output_excerpt(self):
        """Log a brief excerpt from recent SD WebUI output for progress monitoring"""
        try:
            logs_dir = self.user_data_dir / "logs"
            log_file_path = logs_dir / "sd_webui.log"
            
            if log_file_path.exists():
                with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    # Get last 5 lines for brief monitoring
                    recent_lines = lines[-5:] if len(lines) > 5 else lines
                    
                if recent_lines:
                    logger.info("Recent SD WebUI activity:")
                    for line in recent_lines:
                        # Only log non-empty lines and avoid too much noise
                        if line.strip():
                            logger.info(f"SD: {line.rstrip()}")
                else:
                    logger.info("No recent activity in SD WebUI log")
            else:
                logger.debug("SD WebUI log file not found yet")
                
        except Exception as e:
            logger.debug(f"Failed to read SD WebUI log excerpt: {e}")
    
    def stop(self) -> bool:
        """Stop the Stable Diffusion WebUI service"""
        try:
            if not self.process:
                logger.info("No SD WebUI process to stop")
                return True
            
            logger.info("Stopping Stable Diffusion WebUI...")
            
            # Close log file if open
            if hasattr(self, '_log_file') and self._log_file and not self._log_file.closed:
                try:
                    self._log_file.close()
                except Exception as e:
                    logger.warning(f"Failed to close log file: {e}")
            
            # Try graceful termination first
            self.process.terminate()
            
            try:
                self.process.wait(timeout=15)  # Increased timeout
                logger.info("SD WebUI process terminated gracefully")
            except subprocess.TimeoutExpired:
                logger.warning("Graceful termination timed out, forcing kill")
                self.process.kill()
                try:
                    self.process.wait(timeout=5)
                    logger.info("SD WebUI process killed forcefully")
                except subprocess.TimeoutExpired:
                    logger.error("Failed to kill SD WebUI process")
                    return False
            
            self.process = None
            logger.info("Stable Diffusion WebUI stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping SD WebUI: {e}")
            return False
    
    def is_running(self) -> bool:
        """Check if the Stable Diffusion WebUI service is running and fully responsive"""
        try:
            # First, check if we have a process and it's still alive
            if not self.process or self.process.poll() is not None:
                # Process doesn't exist or has terminated
                if self.process and self.process.poll() is not None:
                    logger.debug(f"SD WebUI process has terminated with code: {self.process.returncode}")
                    self.process = None  # Clear the dead process reference
                return False
            
            # Process exists, now perform comprehensive API health checks
            health_endpoints = [
                ("/sdapi/v1/progress", "progress check", True),  # Most reliable endpoint
                ("/sdapi/v1/sd-models", "models endpoint", False),
                ("/sdapi/v1/samplers", "samplers endpoint", False),
            ]
            
            successful_checks = 0
            critical_check_passed = False
            
            for endpoint, description, is_critical in health_endpoints:
                try:
                    url = f"{self.base_url}{endpoint}"
                    response = requests.get(url, timeout=8)
                    
                    if response.status_code == 200:
                        successful_checks += 1
                        
                        # Mark critical check as passed
                        if is_critical:
                            critical_check_passed = True
                        
                        # Additional validation for specific endpoints
                        if endpoint == "/sdapi/v1/progress":
                            try:
                                progress_data = response.json()
                                # Should be a dict with expected progress structure
                                if isinstance(progress_data, dict):
                                    logger.debug(f"SD WebUI API health check passed: {description}")
                                    # If progress endpoint works properly, we can be confident
                                    if 'progress' in progress_data or 'eta_relative' in progress_data:
                                        return True
                                else:
                                    logger.debug(f"Progress endpoint returned unexpected format")
                            except Exception:
                                # If we can't parse JSON but got 200, still consider it responsive
                                logger.debug(f"SD WebUI progress endpoint responsive but unparseable JSON")
                                return True
                                
                        elif endpoint == "/sdapi/v1/sd-models":
                            try:
                                models_data = response.json()
                                if isinstance(models_data, list):
                                    logger.debug(f"Models endpoint responsive with {len(models_data)} models")
                                else:
                                    logger.debug("Models endpoint returned unexpected format")
                            except Exception:
                                logger.debug("Models endpoint responsive but unparseable JSON")
                        
                        logger.debug(f"Health check passed for {description}")
                    else:
                        logger.debug(f"Health check {description} returned status: {response.status_code}")
                        
                except requests.exceptions.ConnectionError:
                    logger.debug(f"Connection error on {description} - service may not be ready")
                except requests.exceptions.Timeout:
                    logger.debug(f"Timeout on {description} - service may be overloaded")
                except Exception as e:
                    logger.debug(f"Health check error on {description}: {e}")
            
            # Service is considered running if:
            # 1. Critical check passed, OR
            # 2. At least 1 out of 3 health checks passed (for redundancy)
            if critical_check_passed:
                logger.debug("Critical health check (progress) passed - service is running")
                return True
            elif successful_checks > 0:
                logger.debug(f"Health checks passed ({successful_checks}/3) - service is running")
                return True
            else:
                logger.debug("All health checks failed - service not responsive")
                return False
            
        except Exception as e:
            logger.error(f"Error checking if SD WebUI is running: {e}")
            return False
    
    def cleanup(self):
        """Clean up resources and stop the service"""
        try:
            logger.info("Cleaning up StableDiffusionController...")
            
            # Stop the service if running
            if self.process:
                self.stop()
            
            # Close log file if open
            if hasattr(self, '_log_file') and self._log_file and not self._log_file.closed:
                try:
                    self._log_file.close()
                    logger.info("Closed SD WebUI log file")
                except Exception as e:
                    logger.warning(f"Failed to close log file during cleanup: {e}")
            
            logger.info("StableDiffusionController cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        try:
            self.cleanup()
        except Exception:
            # Avoid exceptions in destructor
            pass
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed status information"""
        status = {
            "installed": self.sd_dir.exists() and (self.sd_dir / "webui.py").exists(),
            "running": self.is_running(),
            "models_available": [],
            "base_url": self.base_url,
            "models_dir": str(self.sd_dir / "models" / "Stable-diffusion") if self.sd_dir.exists() else "Not available"
        }
        
        if status["running"]:
            try:
                # Get available models
                response = requests.get(f"{self.base_url}/sdapi/v1/sd-models", timeout=self.api_timeout)
                if response.status_code == 200:
                    models_data = response.json()
                    status["models_available"] = [model["title"] for model in models_data]
            except Exception as e:
                logger.error(f"Error getting models: {e}")
        
        return status
    
    def get_models(self) -> List[Dict[str, str]]:
        """Get list of available models"""
        try:
            if not self.is_running():
                return []
            
            response = requests.get(f"{self.base_url}/sdapi/v1/sd-models", timeout=self.api_timeout)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error getting models: {e}")
            return []
    
    def get_samplers(self) -> List[Dict[str, str]]:
        """Get list of available samplers"""
        try:
            if not self.is_running():
                return []
            
            response = requests.get(f"{self.base_url}/sdapi/v1/samplers", timeout=self.api_timeout)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error getting samplers: {e}")
            return []
    
    def generate_image(self, 
                      prompt: str,
                      negative_prompt: str = "",
                      steps: int = 20,
                      cfg_scale: float = 7.0,
                      width: int = 512,
                      height: int = 512,
                      sampler_name: str = "Euler a",
                      seed: int = -1,
                      **kwargs) -> Optional[str]:
        """Generate an image and save it to workspace"""
        try:
            if not self.is_running():
                raise Exception("Stable Diffusion WebUI is not running")
            
            # Prepare the request payload
            payload = {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "steps": steps,
                "cfg_scale": cfg_scale,
                "width": width,
                "height": height,
                "sampler_name": sampler_name,
                "seed": seed,
                **kwargs
            }
            
            logger.info(f"Generating image with prompt: {prompt[:50]}...")
            
            # Make the API request
            response = requests.post(
                f"{self.base_url}/sdapi/v1/txt2img",
                json=payload,
                timeout=300  # 5 minutes timeout for generation
            )
            response.raise_for_status()
            
            result = response.json()
            
            if not result.get("images"):
                raise Exception("No images generated")
            
            # Decode and save the first image with proper memory management
            image_data = result["images"][0]
            image_bytes = base64.b64decode(image_data)
            
            # Use PIL with context manager to prevent memory leaks
            from PIL import Image
            from io import BytesIO
            
            with BytesIO(image_bytes) as buffer:
                with Image.open(buffer) as image:
                    # Generate filename with timestamp
                    timestamp = int(time.time())
                    filename = f"sd_generated_{timestamp}.png"
                    image_path = self.images_dir / filename
                    
                    # Save the image (copy to avoid reference to closed buffer)
                    image_copy = image.copy()
                    image_copy.save(image_path, "PNG")
            
            # Save metadata
            metadata = {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "steps": steps,
                "cfg_scale": cfg_scale,
                "width": width,
                "height": height,
                "sampler_name": sampler_name,
                "seed": result.get("info", {}).get("seed", seed),
                "generated_at": timestamp
            }
            
            metadata_path = self.images_dir / f"sd_generated_{timestamp}.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Image generated and saved: {image_path}")
            return str(image_path)
            
        except Exception as e:
            logger.error(f"Error generating image: {e}")
            raise
    
    def get_generated_images(self) -> List[Dict[str, Any]]:
        """Get list of generated images with metadata"""
        try:
            images = []
            
            for image_file in self.images_dir.glob("sd_generated_*.png"):
                metadata_file = image_file.with_suffix(".json")
                
                image_info = {
                    "filename": image_file.name,
                    "path": str(image_file),
                    "size": image_file.stat().st_size,
                    "created": image_file.stat().st_mtime
                }
                
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r') as f:
                            image_info["metadata"] = json.load(f)
                    except Exception:
                        pass
                
                images.append(image_info)
            
            # Sort by creation time, newest first
            images.sort(key=lambda x: x["created"], reverse=True)
            return images
            
        except Exception as e:
            logger.error(f"Error getting generated images: {e}")
            return []


# Create global instance
stable_diffusion_controller = StableDiffusionController()
