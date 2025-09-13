"""
Main Entry Point and Application Launcher for Vybe AI Desktop Application.

This module serves as the primary entry point for the Vybe AI Desktop Application,
handling application initialization, first-time setup, resource management, and
graceful shutdown procedures. It provides a comprehensive startup sequence that
ensures all system components are properly initialized and configured.

Key Responsibilities:
- Cross-platform compatibility setup (Windows console encoding)
- Application lifecycle management (startup, running, shutdown)
- First-time setup orchestration with model downloads
- Signal handling and graceful shutdown coordination
- Hardware detection and optimal configuration selection
- Background service management (LLM backend, workers)
- Error handling and fallback port selection
- Resource cleanup and memory management

Features:
- Automatic first-time setup with progress indicators
- Hardware-optimized AI model selection and download
- Graceful shutdown with registered cleanup functions
- Cross-platform signal handling (SIGINT, SIGTERM, SIGBREAK)
- Automatic port fallback on conflicts
- Console encoding fixes for Windows platforms
- Background LLM backend initialization
- Comprehensive error handling and recovery

Architecture:
The application follows a staged initialization process:
1. Platform compatibility setup
2. Signal handlers and cleanup registration  
3. First-time setup detection and execution
4. Hardware detection and configuration
5. AI model download and verification
6. Flask application creation and configuration
7. Background service startup
8. Main server loop with error recovery

Example:
    Run the application directly:
    
    $ python run.py
    
    Or with environment variables:
    
    $ FLASK_DEBUG=true HOST=0.0.0.0 PORT=5001 python run.py

Note:
    The application automatically detects first-time launches and guides users
    through the setup process, downloading appropriate AI models based on
    detected hardware capabilities.
"""

# C:\AI\LocalAI-CLI\vybe\run.py
import sys
import os
import atexit
import signal
import threading
import time
from pathlib import Path

# Fix Windows console encoding issues
if sys.platform == 'win32':
    try:
        # Try to set the console codepage to UTF-8
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleOutputCP(65001)  # UTF-8 codepage
    except Exception as e:
        # Silently fail if console codepage setting fails
        pass
    
    # Set environment variable for UTF-8 encoding
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    # Disable colored console output to avoid Click/Colorama write errors on some Windows shells
    os.environ.setdefault('NO_COLOR', '1')
    os.environ.setdefault('CLICOLOR', '0')
    os.environ.setdefault('CLICOLOR_FORCE', '0')
    os.environ.setdefault('TERM', 'dumb')

from vybe_app import create_app, socketio
from vybe_app.config import Config
import requests
import subprocess

# Global cleanup registry
_cleanup_functions = []
_cleanup_lock = threading.Lock()
_cleanup_executed = False

def register_cleanup_function(func, description="Cleanup function"):
    """
    Register a function to be called during application shutdown.
    
    This function allows components to register cleanup handlers that will be
    executed when the application is shutting down. Cleanup functions are
    executed in LIFO (Last In, First Out) order to ensure proper dependency
    order during shutdown.
    
    Args:
        func (callable): The cleanup function to register. Should accept no
                        arguments and handle its own exceptions.
        description (str): Human-readable description of the cleanup function
                          for logging purposes. Defaults to "Cleanup function".
    
    Thread Safety:
        This function is thread-safe and can be called from any thread during
        application initialization.
    
    Example:
        >>> def cleanup_my_resource():
        ...     my_resource.close()
        >>> register_cleanup_function(cleanup_my_resource, "My resource cleanup")
    
    Note:
        Cleanup functions should be idempotent and handle exceptions gracefully
        to prevent interfering with other cleanup operations.
    """
    global _cleanup_functions
    with _cleanup_lock:
        _cleanup_functions.append((func, description))
    print(f"[CLEANUP] Registered: {description}")

def execute_global_cleanup():
    """
    Execute all registered cleanup functions in LIFO order.
    
    This function executes all cleanup functions that have been registered
    via register_cleanup_function(). Functions are executed in reverse order
    of registration (LIFO) to ensure proper dependency cleanup sequence.
    
    The function is idempotent - it can be called multiple times but will
    only execute the cleanup once. Individual cleanup function errors are
    caught and logged but do not prevent other cleanup functions from running.
    
    Thread Safety:
        This function is thread-safe and uses locking to ensure cleanup
        functions are only executed once even if called from multiple threads.
    
    Error Handling:
        Each cleanup function is executed in a try-catch block. Errors are
        logged but do not stop the execution of remaining cleanup functions.
    
    Note:
        This function is automatically called by signal handlers and atexit
        handlers to ensure cleanup occurs during normal and abnormal termination.
    """
    global _cleanup_executed
    with _cleanup_lock:
        if _cleanup_executed:
            return
        _cleanup_executed = True
        
        print("[CLEANUP] Executing global cleanup...")
        for func, description in reversed(_cleanup_functions):  # LIFO order
            try:
                print(f"[CLEANUP] Executing: {description}")
                func()
            except Exception as e:
                print(f"[CLEANUP] Error in {description}: {e}")
        print("[CLEANUP] Global cleanup completed")

def signal_handler(signum, frame):
    """
    Handle termination signals for graceful shutdown.
    
    This function is registered as a signal handler for SIGINT, SIGTERM, and
    SIGBREAK (Windows) signals. It initiates the graceful shutdown process
    by executing all registered cleanup functions before terminating the
    application.
    
    Args:
        signum (int): The signal number that triggered the handler.
        frame: The current stack frame (unused but required by signal handler
               interface).
    
    Behavior:
        1. Logs the received signal number
        2. Executes all registered cleanup functions via execute_global_cleanup()
        3. Exits the application with status code 0
    
    Signals Handled:
        - SIGINT (Ctrl+C): Keyboard interrupt
        - SIGTERM: Termination request
        - SIGBREAK (Windows): Console close or Ctrl+Break
    
    Note:
        This handler ensures that resources are properly cleaned up even when
        the application is terminated unexpectedly by external signals.
    """
    print(f"\n[SIGNAL] Received signal {signum}, initiating cleanup...")
    execute_global_cleanup()
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
if hasattr(signal, 'SIGBREAK'):  # Windows
    signal.signal(signal.SIGBREAK, signal_handler)

# Register atexit handler
atexit.register(execute_global_cleanup)

# --- New First-Time Setup Logic ---
def check_and_run_first_time_setup():
    """
    Comprehensive first-time setup with model download and readiness check.
    
    This function orchestrates the first-time setup process for new Vybe AI
    installations. It detects whether this is a first launch, guides the user
    through the setup process, and ensures all necessary components are
    properly configured.
    
    The setup process includes:
    1. First-time launch detection
    2. User guidance and progress indication
    3. Hardware capability detection
    4. Optimal AI model selection and download
    5. System configuration and validation
    6. Readiness verification
    
    Returns:
        bool: True if setup completed successfully or was already complete,
              False if setup failed or was interrupted.
    
    Features:
        - Progress bar with percentage completion
        - Hardware-optimized model selection
        - Automatic model download with progress tracking
        - Error handling and recovery
        - User-friendly console output
        - Non-blocking background initialization
    
    Error Handling:
        Setup errors are logged and handled gracefully. The function attempts
        to continue with default configurations if specific components fail
        to initialize properly.
    
    Note:
        This function is called early in the application startup sequence and
        may take several minutes to complete on first run due to model downloads.
    """
    from vybe_app.core.first_launch_manager import first_launch_manager
    
    # Check if first launch is complete
    if first_launch_manager.is_first_launch_complete():
        print("[OK] System ready - First-time setup already completed.")
        return True

    print("[SETUP] First launch detected - Setting up Vybe AI Assistant...")
    print("   Analyzing your hardware and selecting the optimal AI model for your system.")
    print("   Please wait while we prepare everything for you...")
    print()
    
    # Set up progress callback for console output
    def progress_callback(message: str, percentage: float):
        # Create a progress bar
        bar_length = 40
        filled_length = int(bar_length * percentage // 100)
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        print(f"\r[PROGRESS] [{bar}] {percentage:6.1f}% - {message}", end='', flush=True)
        if percentage >= 100:
            print()  # New line when complete
    
    first_launch_manager.set_progress_callback(progress_callback)
    
    try:
        # Run the first launch sequence
        success = first_launch_manager.run_first_launch_sequence()
        
        if success:
            # Mark first launch as complete
            first_launch_manager.create_first_launch_flag()
            print("\n[SUCCESS] First-time setup completed successfully!")
            print("   Your Vybe AI Assistant is ready to use.")
            return True
        else:
            print("\n[ERROR] First-time setup failed.")
            print("   Please check your internet connection and try again.")
            return False
            
    except Exception as e:
        print(f"\n[ERROR] First-time setup error: {e}")
        return False

def check_and_download_default_model():
    """
    Check for available AI models and download default model if needed.
    
    Scans the models directory for GGUF format AI models and automatically
    downloads a default TinyLlama model if no models are found. This ensures
    the application has at least one working AI model available for inference.
    
    Returns:
        bool: True if models are available or download succeeded, False if
              download failed but application can continue without models.
    
    Directory Structure:
        - Creates models/ directory if it doesn't exist
        - Scans for *.gguf files (GGML Universal File format)
        - Downloads to models/ directory on success
    
    Download Process:
        1. Check for existing GGUF models in models/ directory
        2. If found, report count and return success
        3. If none found, execute download_default_model.py script
        4. Handle subprocess errors gracefully with user guidance
    
    Error Handling:
        - Subprocess failures logged with guidance for manual download
        - Missing download script handled gracefully
        - Non-fatal errors allow application to continue without models
    
    Note:
        Uses the same Python executable that started the application to
        ensure compatibility with virtual environments and custom Python
        installations.
    """
    models_dir = Path(__file__).parent / "models"
    models_dir.mkdir(exist_ok=True)
    
    # Check if any GGUF models exist
    gguf_files = list(models_dir.glob("*.gguf"))
    if gguf_files:
        print(f"[OK] Found {len(gguf_files)} model(s) in models directory")
        return True
    
    print("[DOWNLOAD] No models found. Downloading default model...")
    try:
        # Run the download script
        python_exe = sys.executable
        download_script = Path(__file__).parent / 'download_default_model.py'
        
        result = subprocess.run([python_exe, str(download_script)], 
                              capture_output=True, text=True, check=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"[WARNING] Failed to download default model: {e}")
        print("You can manually download a GGUF model to the models/ directory")
        return False
    except FileNotFoundError:
        print("[WARNING] Download script not found")
        return False

def check_llm_backend():
    """
    Check availability and status of the integrated LLM backend service.
    
    Performs a health check on the integrated llama-cpp-python backend server
    running on localhost:11435. This backend provides OpenAI-compatible API
    endpoints for local AI model inference without external dependencies.
    
    Returns:
        bool: True if backend is running and responding correctly, False if
              backend is unavailable, starting, or experiencing issues.
    
    Backend Communication:
        - Endpoint: http://localhost:11435/v1/models
        - Protocol: OpenAI-compatible REST API
        - Timeout: 3 seconds for responsiveness
        - Expected: 200 status with models list in response
    
    Status Categories:
        - OK: Backend running with model count reported
        - INFO: Backend starting (connection refused - normal during startup)
        - WARNING: Backend responding but with errors, timeouts, or exceptions
    
    Error Handling:
        - Connection errors indicate backend not yet ready (normal during startup)
        - Timeout errors suggest backend performance issues
        - HTTP errors indicate backend problems but reachable
        - Unexpected exceptions logged for debugging
    
    Note:
        This function is non-blocking and designed for polling during startup.
        Backend may take time to initialize, especially on first run or with
        large models. Connection failures during startup are expected.
    """
    try:
        # Check if our integrated LLM backend is running
        response = requests.get("http://localhost:11435/v1/models", timeout=3)
        if response.status_code == 200:
            models = response.json()
            print(f"[OK] Integrated LLM backend running with {len(models.get('data', []))} models")
            return True
        else:
            print(f"[WARNING] LLM backend returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("[INFO] LLM backend not yet ready (starting in background)")
        return False
    except requests.exceptions.Timeout:
        print("[WARNING] LLM backend check timed out")
        return False
    except requests.exceptions.RequestException as e:
        print(f"[WARNING] LLM backend request error: {e}")
        return False
    except Exception as e:
        print(f"[WARNING] Unexpected error checking LLM backend: {e}")
        import traceback
        traceback.print_exc()
        return False

def start_backend_llm():
    """
    Initialize and start the integrated llama-cpp-python backend server.
    
    Starts the integrated LLM backend server in a separate daemon thread to
    provide local AI model inference without blocking the main Flask application
    startup. The backend provides OpenAI-compatible API endpoints for chat
    completion and model management.
    
    Returns:
        bool: True if backend startup initiated successfully, False if startup
              failed due to missing dependencies or configuration issues.
    
    Architecture:
        - Non-blocking: Runs in separate daemon thread to avoid blocking Flask
        - Lazy loading: Imports backend controller only when needed
        - Graceful degradation: Application continues if backend fails to start
        - Auto-discovery: Automatically finds and loads available models
    
    Threading Model:
        - Main thread: Flask application and web interface
        - Daemon thread: LLM backend server (llama-cpp-python)
        - Communication: HTTP API on localhost:11435
    
    Error Handling:
        - Import errors: Missing llama-cpp-python dependencies
        - File errors: Model files not found or inaccessible
        - Runtime errors: Server startup failures or configuration issues
        - All errors logged with user guidance for resolution
    
    Dependencies:
        - llama-cpp-python[server]: Core LLM inference engine
        - BackendLLMController: Local controller for server lifecycle
        - Models: GGUF format models in models/ directory
    
    Note:
        The backend may take significant time to start, especially on first run
        or with large models. The main application starts immediately while the
        backend initializes in the background. Model downloading occurs on first
        use if no models are available.
    """
    try:
        print("[LLM] Checking for integrated LLM backend...")
        # Import in a try block to avoid startup failures
        from vybe_app.core.backend_llm_controller import BackendLLMController
        
        # Start in a separate thread to avoid blocking Flask startup
        def start_llm_thread():
            try:
                controller = BackendLLMController()
                if controller.model_path:
                    controller.start_server()
                else:
                    print("[WARNING] No models found for LLM backend - will download on first use")
            except ImportError as e:
                print(f"[WARNING] LLM backend dependencies missing: {e}")
            except FileNotFoundError as e:
                print(f"[WARNING] LLM backend model file not found: {e}")
            except Exception as e:
                print(f"[WARNING] LLM backend thread error: {e}")
                import traceback
                traceback.print_exc()
        
        import threading
        llm_thread = threading.Thread(target=start_llm_thread, daemon=True)
        llm_thread.start()
        
        print("[OK] LLM backend startup initiated (running in background)")
        return True
    except ImportError as e:
        print(f"[WARNING] LLM backend not available (missing dependencies): {e}")
        print("    Run: pip install llama-cpp-python[server]")
        return False
    except Exception as e:
        print(f"[WARNING] Unexpected error starting LLM backend: {e}")
        import traceback
        traceback.print_exc()
        return False

# Create the Flask application instance using the application factory pattern
app = create_app()

if __name__ == '__main__':
    """
    Main application entry point and startup sequence.
    
    This block handles the complete application startup process when run.py is
    executed directly. It orchestrates initialization of all system components,
    performs first-time setup if needed, and starts the Flask/SocketIO server.
    
    Startup Sequence:
        1. Cleanup function registration for graceful shutdown
        2. Test mode enablement for easier desktop usage
        3. First-time setup detection and execution
        4. Hardware capability detection and classification
        5. AI model backend initialization (optional)
        6. Flask server configuration and startup
        7. Error handling and port fallback
    
    Environment Variables:
        VYBE_TEST_MODE: Enable test mode (bypasses authentication)
        HOST: Server bind address (default: 127.0.0.1)
        PORT: Server port number (from Config.PORT)
        FLASK_DEBUG: Enable Flask debug mode
        FLASK_SKIP_DOTENV: Skip .env file loading
    
    Features:
        - Automatic first-time setup on cold systems
        - Hardware detection and performance optimization
        - Graceful error handling and recovery
        - Automatic port fallback on conflicts
        - Background LLM backend initialization
        - Comprehensive cleanup registration
    
    Error Handling:
        The startup process includes comprehensive error handling with fallback
        options. Port conflicts trigger automatic fallback to alternative ports.
        Setup failures are logged but don't prevent application startup.
    
    Note:
        The application automatically enables test mode for easier desktop usage
        unless explicitly disabled via environment variables.
    """
    print("[STARTUP] Starting Vybe AI Assistant...")
    
    # Register core cleanup functions
    register_cleanup_function(
        lambda: print("[CLEANUP] Flask application shutdown"),
        "Flask application shutdown"
    )
    
    # Enable test mode by default for easier desktop app usage
    import os
    if not os.getenv('VYBE_TEST_MODE'):
        os.environ['VYBE_TEST_MODE'] = 'true'
        print("[OK] Test mode enabled - authentication bypassed")

    # --- CRITICAL CHANGE ---
    # Perform first-time setup tasks WITHIN the application context
    # This ensures the database and all app components are ready.
    with app.app_context():
        # 1. Optionally run first-time setup (disabled by default to avoid auto-launch confusion)
        from vybe_app.config import Config as VybeConfig
        setup_success = True
        # Auto-run first launch on "cold" systems with no local models and no prior first-launch flag
        try:
            from vybe_app.core.first_launch_manager import first_launch_manager as _flm
            from vybe_app.config import Config as _Cfg
            # Detect presence of any GGUF models across known directories
            any_models = False
            try:
                for _dir in _Cfg.get_models_directories():
                    if list(_dir.glob('*.gguf')):
                        any_models = True
                        break
            except Exception:
                any_models = False
            cold_system = (not any_models) and (not _flm.is_first_launch_complete())
            print(f"[DEBUG] First launch check: any_models={any_models}, first_launch_complete={_flm.is_first_launch_complete()}, cold_system={cold_system}")
        except Exception:
            cold_system = False

        # Only run first launch if explicitly enabled AND it's a cold system
        if VybeConfig.FIRST_LAUNCH_AUTORUN and cold_system:
            setup_success = check_and_run_first_time_setup()
            if not setup_success:
                print("[WARNING] Setup incomplete - some features may not work properly")

        # 2. Initialize Hardware Manager and detect system capabilities
        print("[HW] Detecting system hardware capabilities...")
        try:
            from vybe_app.core.hardware_manager import get_hardware_manager
            hw_manager = get_hardware_manager()
            
            # Register hardware cleanup
            register_cleanup_function(
                lambda: getattr(hw_manager, 'cleanup', lambda: None)(),
                "Hardware manager cleanup"
            )
            
            # Run detection and benchmarking on first launch
            flag_file = Path(__file__).parent / "instance" / "hardware_detected.flag"
            if not flag_file.exists():
                hw_info = hw_manager.detect_hardware()
                tier = hw_manager.classify_performance_tier()
                print(f"[OK] System classified as: {tier}")
                
                # Save flag to avoid re-detection every startup
                flag_file.parent.mkdir(exist_ok=True)
                flag_file.write_text(f"Hardware detected at {time.ctime()}")
                
                # Quick benchmark on first launch (optional)
                print("[BENCHMARK] Running quick system benchmark...")
                hw_manager.benchmark_system()
            else:
                # Load cached hardware info
                tier = hw_manager.performance_tier or hw_manager.classify_performance_tier()
                print(f"[OK] Hardware profile loaded: {tier}")
        except Exception as e:
            print(f"[WARNING] Hardware detection failed: {e}")
            print("   Using default configuration")

        # 3. Start integrated LLM backend server (non-blocking) based on DB startup prefs or env flags
        try:
            from vybe_app.models import AppSetting
            def _get_bool(key: str, default: bool = False) -> bool:
                s = AppSetting.query.filter_by(key=key).first()
                return (s.value.lower() == 'true') if s and isinstance(s.value, str) else default
            db_auto_llm = _get_bool('auto_launch_llm_on_start', False)
        except Exception:
            db_auto_llm = False

        # Register LLM backend cleanup
        try:
            from vybe_app.core.backend_llm_controller import get_backend_controller
            backend_controller = get_backend_controller()
            register_cleanup_function(
                lambda: backend_controller.stop_server() if hasattr(backend_controller, 'stop_server') else None,
                "LLM backend server shutdown"
            )
        except Exception:
            pass

        # Default-on first boot: if no DB pref exists yet, start LLM to avoid splash stall
        # TEMPORARILY DISABLED to prevent crashes with corrupted model files
        # if db_auto_llm or (VybeConfig.AUTO_START_LLM and VybeConfig.AUTO_LAUNCH_EXTERNAL_APPS) or not os.path.exists(os.path.join('instance','site.db')):
        #     # Always use singleton to start backend to unify readiness checks
        #     try:
        #         from vybe_app.core.backend_llm_controller import get_backend_controller
        #         get_backend_controller().start_server()
        #     except Exception:
        #         start_backend_llm()
        print("[INFO] LLM backend startup disabled - will start manually when needed")
    
    # 4. Check LLM backend status (optional - runs in background)
    check_llm_backend()
    
    # Configuration - simplified for reliability
    host = os.getenv('HOST', '127.0.0.1') # Default to localhost for security
    port = Config.PORT
    debug = os.getenv('FLASK_DEBUG', 'False').lower() in ('true', '1', 'yes', 'on')
    
    print(f"[FLASK] Starting Vybe Flask server on http://{host}:{port}")
    print("[INFO] LLM backend will initialize in the background")
    
    # Start Socket.IO server so WS features work
    try:
        print("[FLASK] Starting Socket.IO server...")
        # Additional Windows console compatibility
        os.environ.setdefault('FLASK_SKIP_DOTENV', '1')
        # Register SocketIO cleanup
        register_cleanup_function(
            lambda: socketio.stop() if hasattr(socketio, 'stop') else None,
            "SocketIO server shutdown"
        )
        # Simply run without stderr suppression to avoid hanging
        socketio.run(app, debug=debug, host=host, port=port, allow_unsafe_werkzeug=True, use_reloader=False)
    except Exception as e:
        print(f"[ERROR] Failed to start Vybe server: {e}")
        print(f"[TIP] Check if port {port} is already in use")
        # Attempt automatic port fallback on Windows error/port in use
        try:
            fallback_ports = [port + 1, port + 2, port + 3]
            for fp in fallback_ports:
                try:
                    print(f"[RETRY] Attempting to start on port {fp}...")
                    socketio.run(app, debug=debug, host=host, port=fp, allow_unsafe_werkzeug=True, use_reloader=False)
                    # If the server exits cleanly after running, stop trying others
                    break
                except Exception as ee:
                    print(f"[RETRY] Port {fp} failed: {ee}")
                    continue
            else:
                raise RuntimeError("All fallback ports failed")
            sys.exit(0)
        except Exception:
            pass
        import traceback
        traceback.print_exc()
        sys.exit(1)