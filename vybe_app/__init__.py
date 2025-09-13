"""
Vybe AI Desktop Application - Flask Application Factory and Configuration.

This module serves as the main application factory for the Vybe AI Desktop Application,
a comprehensive AI-powered desktop assistant with multi-modal capabilities including
text generation, image synthesis, audio processing, and smart home integration.

The module provides:
- Flask application factory pattern implementation
- Lazy loading of heavy AI model controllers
- Database initialization and migration management
- WebSocket and real-time communication setup
- Security middleware and authentication configuration
- Background job scheduling and system monitoring
- Plugin architecture and extension management

Key Components:
- Application factory (create_app): Main Flask app configuration
- Controller lazy loading: Memory-efficient AI model management  
- Database setup: SQLAlchemy models and migrations
- WebSocket handlers: Real-time communication via SocketIO
- Background services: Job scheduling and system monitoring
- Security features: CORS, authentication, and middleware

Architecture:
The application follows a modular architecture with clear separation of concerns:
- Core services (job management, system monitoring)
- AI controllers (text, image, audio generation)
- API endpoints (REST and WebSocket)
- Database models and utilities
- Security and authentication layers

Example:
    Basic usage to create and run the application:
    
    >>> from vybe_app import create_app, socketio
    >>> app = create_app()
    >>> socketio.run(app, host='127.0.0.1', port=5000)

Note:
    This module is designed for desktop deployment and includes specific
    optimizations for local AI model execution and resource management.
"""

# Disable eventlet for now as it's causing server exit issues
# import eventlet
# eventlet.monkey_patch()  # Must be called before any other imports

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_socketio import SocketIO
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit
import os
import threading
import socket
import time
from datetime import datetime
from pathlib import Path

# Import configuration and logging
from .config import Config
from .logger import logger

# Ensure user data directories exist before importing controllers
Config.ensure_user_data_dirs()

# Helper function to avoid repetitive sys.path manipulation
def _ensure_run_module_import():
    """
    Ensure the parent directory is in sys.path for run module imports.
    
    This helper function handles the import path configuration needed to access
    the run module's cleanup registration functionality. It safely adds the parent
    directory to sys.path if it's not already present.
    
    Returns:
        callable or None: The register_cleanup_function from run module if successful,
                         None if the import fails.
    
    Note:
        This function is used to establish proper cleanup chains between the
        application factory and the main run script.
    """
    try:
        import sys
        import os
        parent_dir = os.path.dirname(os.path.dirname(__file__))
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        from run import register_cleanup_function
        return register_cleanup_function
    except ImportError:
        return None

# Import lightweight core modules only
from .core import job_manager, system_monitor
from .core.setup_manager import setup_workspace_directories
from .core.agent_manager import get_agent_manager
from .core.manager_model import get_manager_model, initialize_manager_model
from .core.hardware_manager import get_hardware_manager, initialize_hardware_manager
from .core.installation_monitor import installation_monitor

# Lazy loading functions for heavy controllers
def get_stable_diffusion_controller():
    """
    Lazy load stable diffusion controller for image generation.
    
    This function implements lazy loading to avoid loading heavy AI models
    during application startup. The Stable Diffusion controller is only
    instantiated when first requested, improving startup performance.
    
    Returns:
        object or None: The stable diffusion controller instance if successful,
                       None if loading fails.
    
    Note:
        The controller instance is cached after first creation and cleanup
        is automatically registered with the application shutdown handlers.
    """
    try:
        if not hasattr(get_stable_diffusion_controller, '_instance'):
            from .core.stable_diffusion_controller import stable_diffusion_controller
            get_stable_diffusion_controller._instance = stable_diffusion_controller
            # Register cleanup
            register_cleanup_function = _ensure_run_module_import()
            if register_cleanup_function:
                register_cleanup_function(
                    lambda: _cleanup_controller_instance(get_stable_diffusion_controller, 'Stable Diffusion controller'),
                    "Stable Diffusion controller cleanup"
                )
        return get_stable_diffusion_controller._instance
    except Exception as e:
        logger.warning(f"Failed to load Stable Diffusion controller: {e}")
        return None

def _cleanup_controller_instance(controller_func, name):
    """
    Clean up a controller instance during application shutdown.
    
    This function handles the proper cleanup of AI model controllers when
    the application is shutting down. It attempts to call cleanup methods
    in order of preference and logs the cleanup status.
    
    Args:
        controller_func (callable): The function that holds the controller instance.
        name (str): Human-readable name of the controller for logging.
    
    Note:
        Cleanup methods are attempted in order: cleanup(), shutdown(), then
        simple instance deletion. All exceptions are caught and logged to
        prevent shutdown failures.
    """
    if hasattr(controller_func, '_instance'):
        try:
            instance = controller_func._instance
            if hasattr(instance, 'cleanup'):
                instance.cleanup()
            elif hasattr(instance, 'shutdown'):
                instance.shutdown()
            delattr(controller_func, '_instance')
            logger.info(f"[CLEANUP] {name} cleaned up")
        except Exception as e:
            logger.warning(f"[CLEANUP] Error cleaning {name}: {e}")

def get_tts_controller():
    """
    Lazy load PyTTSx3 TTS controller for text-to-speech functionality.
    
    This function provides lazy loading for the text-to-speech controller,
    using PyTTSx3 as the backend for better reliability compared to edge_tts.
    The controller is cached after first instantiation.
    
    Returns:
        object: The TTS controller instance.
    
    Note:
        PyTTSx3 was chosen over edge_tts for improved stability and offline
        capabilities. Cleanup is automatically registered for shutdown.
    """
    if not hasattr(get_tts_controller, '_instance'):
        from .core.pyttsx3_tts_controller import get_pyttsx3_controller
        get_tts_controller._instance = get_pyttsx3_controller()
        # Register cleanup
        register_cleanup_function = _ensure_run_module_import()
        if register_cleanup_function:
            register_cleanup_function(
                lambda: _cleanup_controller_instance(get_tts_controller, 'TTS controller'),
                "TTS controller cleanup"
            )
    return get_tts_controller._instance

def get_transcription_controller():
    """
    Lazy load transcription controller for audio-to-text conversion.
    
    This function provides lazy loading for the audio transcription controller,
    which handles converting spoken audio to text. The controller supports
    multiple audio formats and transcription backends.
    
    Returns:
        TranscriptionController: The transcription controller instance.
    
    Note:
        The controller is cached after first creation and cleanup handlers
        are automatically registered for proper resource management.
    """
    if not hasattr(get_transcription_controller, '_instance'):
        from .core.transcription_controller import TranscriptionController
        get_transcription_controller._instance = TranscriptionController()
        # Register cleanup
        register_cleanup_function = _ensure_run_module_import()
        if register_cleanup_function:
            register_cleanup_function(
                lambda: _cleanup_controller_instance(get_transcription_controller, 'Transcription controller'),
                "Transcription controller cleanup"
            )
    return get_transcription_controller._instance

def get_video_generator_controller():
    """
    Lazy load video generator controller for video creation and processing.
    
    This function provides lazy loading for the video generation controller,
    which handles video creation using AI models like ComfyUI. The controller
    supports various video generation workflows and formats.
    
    Returns:
        VideoGeneratorController: The video generator controller instance.
    
    Note:
        Video generation is computationally intensive, so lazy loading helps
        with application startup performance. Cleanup is automatically handled.
    """
    if not hasattr(get_video_generator_controller, '_instance'):
        from .core.video_generator import VideoGeneratorController
        get_video_generator_controller._instance = VideoGeneratorController()
        # Register cleanup
        register_cleanup_function = _ensure_run_module_import()
        if register_cleanup_function:
            register_cleanup_function(
                lambda: _cleanup_controller_instance(get_video_generator_controller, 'Video generator controller'),
                "Video generator controller cleanup"
            )
    return get_video_generator_controller._instance

def generate_dynamic_system_prompt():
    """
    Generate a dynamic system prompt that includes current RAG collection information.
    
    This function creates a comprehensive system prompt for the AI assistant that
    includes information about available tools, capabilities, and knowledge collections.
    The prompt is dynamically updated to reflect the current state of RAG collections.
    
    Returns:
        str: A formatted system prompt string that includes:
            - Tool descriptions and capabilities
            - Available RAG collections and their purposes
            - Usage guidelines and restrictions
            - Security and workspace information
    
    Note:
        The prompt is regenerated each time to ensure it reflects the current
        state of the knowledge base and available collections.
    """
    base_prompt = """You are a helpful, knowledgeable, and friendly AI assistant. Provide accurate, clear, and concise responses to help users with their questions and tasks.

You have access to several tools that enhance your capabilities:

🔍 **Web Search**: Search the internet for current information and research
📁 **File Management**: You have a secure workspace directory where you can:
   - List files and directories (ai_list_files_in_directory)
   - Read file contents (ai_read_file) 
   - Write content to files (ai_write_file)
   - Delete files or empty directories (ai_delete_file)

🎨 **Image Generation**: Create stunning AI-generated images using Stable Diffusion:
   - Generate images from text descriptions (ai_generate_image)
   - Specify negative prompts, style settings, dimensions, and sampling parameters
   - Images are automatically saved to your workspace for download or further use

🎤 **Audio & Speech**: Advanced text-to-speech and transcription capabilities:
   - Convert text to speech with natural voices (ai_speak_text)
   - Transcribe audio files to text (ai_transcribe_audio)
   - Support for voice cloning and custom voice synthesis

🏠 **Smart Home Control**: Control Home Assistant devices and automation:
   - Control lights, switches, and other smart devices
   - Format: [TOOL:HOME_ASSISTANT service=domain.service entity_id=entity_name]
   - Examples: [TOOL:HOME_ASSISTANT service=light.turn_on entity_id=light.living_room]
   - Support for brightness, color, temperature settings and more
   - Access all connected smart home devices through your Home Assistant instance

📚 **RAG Knowledge Base**: Query your specialized knowledge collections:
   - Query specific collections: ai_query_rag_collections(query, collection_names=['collection1', 'collection2'])
   - Query all collections: ai_query_rag_collections(query)
   
   Available RAG collections and their contents:
{rag_collections_info}

⚠️ **Important**: All file operations are restricted to your designated workspace directory for security. You cannot access files outside this workspace.

When working with files, always:
- Use relative paths within your workspace
- Be careful with file operations, especially deletions
- Inform the user about what files you're creating or modifying
- Check if files exist before attempting to read them

When using the RAG system:
- Consider what type of information the user is seeking
- Use specific collection names when you know they're relevant to the query
- The tool will tell you which collections were searched and provide source attribution
- Use RAG queries to supplement your knowledge with domain-specific information

Feel free to use these tools to help users with tasks involving file management, research, knowledge retrieval, or any other assistance they need."""

    # Get RAG collection information
    try:
        from .models import RAGCollectionMetadata
        collections = RAGCollectionMetadata.query.all()
        
        if collections:
            rag_info_lines = []
            for collection in collections:
                description = collection.description or "No description available"
                rag_info_lines.append(f"   - '{collection.collection_name}': {description}")
            rag_collections_info = "\n".join(rag_info_lines)
        else:
            rag_collections_info = "   - No RAG collections currently available. Use the RAG Manager to create and upload content to collections."
            
    except Exception:
        # Fallback if database is not yet initialized
        rag_collections_info = "   - Use the ai_query_rag_collections tool to discover and query relevant information\n   - You can specify which collections to search based on the user's query context\n   - If you're unsure which collections to use, omit the collection_names parameter to search all"
    
    return base_prompt.format(rag_collections_info=rag_collections_info)

# Default system prompt - will be updated dynamically
DEFAULT_SYSTEM_PROMPT = generate_dynamic_system_prompt()

# Initialize extensions
login_manager = LoginManager()
scheduler = BackgroundScheduler()
# Use threading async mode for broad compatibility (avoids eventlet requirements)
socketio = SocketIO(async_mode='threading', cors_allowed_origins="*")


def _setup_default_models_job():
    """
    Background job to setup default models with orchestrator management.
    
    This function runs as a background job to set up default AI models using
    the orchestrator for intelligent model management. It determines which
    models need installation and manages the setup process.
    
    Note:
        This function is currently disabled to prevent startup delays but can
        be re-enabled for automatic model installation. The orchestrator handles
        model requirements checking and installation coordination.
    
    Raises:
        Exception: Logs any errors that occur during model setup rather than
                  failing the application startup.
    """
    try:
        logger.info("🤖 Orchestrator managing model setup...")
        
        # Use orchestrator to manage model setup intelligently
        from .core.manager_model import get_manager_model
        manager = get_manager_model()
        
        # Let orchestrator decide if models need setup
        if hasattr(manager, '_check_and_install_requirements'):
            manager._check_and_install_requirements()
        
        logger.info("[OK] Orchestrator model setup completed")
        
    except Exception as e:
        logger.error(f"Error in orchestrator model setup: {e}")


def start_mdns_service(port=None):
    """
    Start mDNS service advertisement for network discovery.
    
    This function would start multicast DNS service advertisement to allow
    network discovery of the Vybe AI application. Currently disabled for
    Windows compatibility and startup stability.
    
    Args:
        port (int, optional): The port number to advertise. Defaults to Config.PORT
                             if not specified.
    
    Note:
        mDNS service is completely disabled to prevent Windows compatibility issues
        and reduce startup complexity. Network discovery is not critical for the
        local desktop application use case.
    """
    # mDNS service completely disabled to prevent Windows compatibility issues
    # and reduce startup complexity. Network discovery not critical for local app.
    logger.info("mDNS service disabled for Windows compatibility and startup stability")
    return


def stop_mdns_service():
    """
    Stop mDNS service advertisement and cleanup resources.
    
    This function would handle stopping the mDNS service and cleaning up
    any associated resources. Currently disabled since mDNS service is
    not active.
    
    Note:
        No cleanup is needed since mDNS service is disabled for stability.
        This function exists for API compatibility and future enablement.
    """
    # No cleanup needed since mDNS is disabled
    logger.debug("mDNS service cleanup skipped (service disabled)")
    return


def create_app():
    """
    Application factory function for creating and configuring the Flask application.
    
    This is the main application factory that creates and configures the complete
    Vybe AI Desktop Application. It handles all aspects of application initialization
    including database setup, security configuration, AI model loading, background
    services, and API endpoint registration.
    
    The factory pattern allows for flexible application configuration and testing
    by creating isolated application instances with different configurations.
    
    Returns:
        Flask: A fully configured Flask application instance with all extensions,
               blueprints, and services initialized and ready to run.
    
    Configuration Steps:
        1. Flask app creation and basic configuration
        2. Database initialization and migrations
        3. Security middleware and CORS setup
        4. AI controller lazy loading setup
        5. Authentication and user management
        6. WebSocket and real-time communication
        7. Background job scheduling
        8. API blueprint registration
        9. Default data initialization
        10. Cleanup handler registration
    
    Features Initialized:
        - SQLAlchemy database with migrations
        - Flask-Login authentication system
        - SocketIO for real-time communication
        - CORS for cross-origin requests
        - Security middleware and monitoring
        - AI model controllers (lazy loaded)
        - Background job scheduler
        - System monitoring and health checks
        - Notification system integration
        - Plugin architecture support
        - Default admin user creation
        - RAG knowledge base system
    
    Note:
        Heavy AI models are lazy-loaded to improve startup performance.
        The application automatically creates default users and data on
        first run if none exist.
    
    Raises:
        Exception: Various exceptions may be raised during initialization,
                  but the factory attempts to continue with degraded
                  functionality rather than failing completely.
    """
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Track startup time for health checks
    app.config['startup_time'] = datetime.now().isoformat()
    
    # Fix database path for proper permissions
    if app.config['SQLALCHEMY_DATABASE_URI'] == 'sqlite:///site.db':
        # Use user data directory for database
        if os.name == 'nt':  # Windows
            user_data_dir = Path(os.path.expandvars('%LOCALAPPDATA%')) / "Vybe AI Assistant"
        else:
            user_data_dir = Path.home() / ".local" / "share" / "vybe"
        
        user_data_dir.mkdir(parents=True, exist_ok=True)
        db_path = user_data_dir / "site.db"
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
        logger.info(f"[DB] Database: {db_path}")
    
    # Enable CORS - permissive in test mode, restrictive otherwise
    try:
        if Config.VYBE_TEST_MODE:
            CORS(app, origins="*", allow_headers="*", methods="*")
            logger.info("[OK] CORS enabled for all origins (TEST MODE)")
        else:
            allowed = [
                "http://localhost", "http://127.0.0.1",
                "https://localhost", "https://127.0.0.1"
            ]
            CORS(app, origins=allowed, allow_headers="*", methods="*")
            logger.info("[OK] CORS restricted to localhost (PRODUCTION MODE)")
    except Exception as e:
        logger.warning(f"[WARNING] CORS setup failed: {e}")
    
    # Initialize security middleware early
    try:
        from .utils.security_middleware import SecurityMiddleware
        security = SecurityMiddleware(app)
        app.security = security  # type: ignore
        logger.info("[OK] Security middleware initialized")
    except ImportError as e:
        logger.warning(f"[WARNING] Security middleware not fully available: {e}")
    
    # Attach core modules to app for easy access
    app.job_manager = job_manager  # type: ignore
    app.system_monitor = system_monitor  # type: ignore
    
    # Use lazy loading for heavy controllers
    app.get_stable_diffusion_controller = get_stable_diffusion_controller  # type: ignore
    app.get_tts_controller = get_tts_controller  # type: ignore
    app.get_transcription_controller = get_transcription_controller  # type: ignore
    app.get_video_controller = get_video_generator_controller  # type: ignore
    
    # Initialize extensions with app FIRST
    from .models import db
    db.init_app(app)  # type: ignore[arg-type]
    
    # Initialize components that need database access within app context
    with app.app_context():
        # Run database migrations first to ensure schema is up to date
        try:
            from .utils.migrate_db import DatabaseMigrator
            migrator = DatabaseMigrator(app)
            # Use transaction safety for migrations
            with db.session.begin():
                migrator.run_all_migrations()
            logger.info("[OK] Database migrations completed")
        except Exception as e:
            logger.warning(f"[WARNING] Database migration failed: {e}")
            # Try to create tables anyway for fresh installations
            try:
                db.create_all()
                logger.info("[OK] Database tables created (fresh installation)")
            except Exception as e2:
                logger.error(f"[ERROR] Database initialization failed: {e2}")
        
        # Create additional database indexes for performance optimization
        try:
            from .models import create_database_indexes
            create_database_indexes()
            logger.info("[OK] Database indexes created/verified")
        except Exception as e:
            logger.warning(f"[WARNING] Database indexes creation failed: {e}")
        
        # Initialize First Launch Manager for splash screen functionality
        from .core.first_launch_manager import first_launch_manager
        app.first_launch_manager = first_launch_manager  # type: ignore
        
        # Initialize Hardware Manager first (determines system capabilities)
        hardware_manager = initialize_hardware_manager()
        app.hardware_manager = hardware_manager  # type: ignore
        
        # Initialize Manager Model (the orchestrator)
        manager_model = initialize_manager_model()
        app.manager_model = manager_model  # type: ignore

        # Honor user startup preferences: optionally auto-start services on app launch
        try:
            from .models import AppSetting
            prefs = {s.key: s.value for s in AppSetting.query.filter(AppSetting.key.in_([
                'auto_launch_llm_on_start', 'auto_launch_sd_on_start', 'auto_launch_comfy_on_start'
            ])).all()}
            def _is_true(v: str) -> bool:
                return str(v).lower() in ('true','1','yes','on')

            # Stable Diffusion (A1111) - Defer installation/start to user action to avoid blocking splash
            if False and _is_true(prefs.get('auto_launch_sd_on_start', 'false')):
                try:
                    import threading
                    def _start_sd():
                        ctrl = app.get_stable_diffusion_controller()  # type: ignore
                        if ctrl:
                            ctrl.start()
                    threading.Thread(target=_start_sd, daemon=True).start()
                    logger.info("[STARTUP] Auto-start: Stable Diffusion queued")
                except Exception as e:
                    logger.warning(f"[STARTUP] Auto-start SD failed: {e}")

            # ComfyUI (Video)
            if _is_true(prefs.get('auto_launch_comfy_on_start', 'false')):
                try:
                    import threading
                    def _start_video():
                        vc = app.get_video_controller()  # type: ignore
                        if vc and hasattr(vc, 'start'):
                            vc.start()
                    threading.Thread(target=_start_video, daemon=True).start()
                    logger.info("[STARTUP] Auto-start: ComfyUI queued")
                except Exception as e:
                    logger.warning(f"[STARTUP] Auto-start ComfyUI failed: {e}")

            # Backend LLM
            if _is_true(prefs.get('auto_launch_llm_on_start', 'false')):
                try:
                    import threading
                    def _start_llm():
                        from .core.backend_llm_controller import get_backend_controller
                        ctrl = get_backend_controller()
                        if getattr(ctrl, 'model_path', None):
                            ctrl.start_server()
                    threading.Thread(target=_start_llm, daemon=True).start()
                    logger.info("[STARTUP] Auto-start: LLM backend queued")
                except Exception as e:
                    logger.warning(f"[STARTUP] Auto-start LLM failed: {e}")
        except Exception as e:
            logger.warning(f"[STARTUP] Reading startup prefs failed: {e}")
    
    # Initialize agent manager with job manager
    agent_manager = get_agent_manager()
    agent_manager.job_manager = job_manager
    app.agent_manager = agent_manager  # type: ignore
    
    # Start the job manager
    job_manager.start()
    logger.info("Job manager started successfully")
    
    # Setup workspace directories
    setup_workspace_directories()
    
    # TEMPORARILY DISABLED: Schedule orchestrator-managed model setup (causing startup hang)
    # job_manager.add_job(_setup_default_models_job)  # Start in background
    logger.info("[WARNING] Model setup job temporarily disabled to fix startup hang")
    
    # Start installation monitor in background
    try:
        installation_monitor.start_monitoring()
        logger.info("[STARTUP] Installation monitor started")
    except Exception as e:
        logger.warning(f"[STARTUP] Failed to start installation monitor: {e}")
    
    login_manager.init_app(app)
    setattr(login_manager, 'login_view', 'auth.login')
    setattr(login_manager, 'login_message', 'Please log in to access this page.')
    setattr(login_manager, 'login_message_category', 'info')
    
    # Initialize SocketIO with consistent async mode and reduced logging
    socketio.init_app(app, async_mode='threading', cors_allowed_origins="*", logger=False, engineio_logger=False)
    
    # Setup SSL context if configured (store in app config instead of direct attribute)
    ssl_context = Config.setup_ssl_context()
    if ssl_context:
        app.config['SSL_CONTEXT'] = ssl_context
    
    @login_manager.user_loader
    def load_user(user_id):
        from .models import User
        return User.query.get(int(user_id))
    
    # Register blueprints - FIXED: Removed duplicate imports and registrations
    from .auth import auth_bp
    from .views import views_bp
    from .api import api_bp
    from .api.chat_api import register_chat_socketio_handlers, chat_bp
    from .api.models_api import models_bp
    from .api.audio_api import audio_api as audio_bp
    from .api.image_api import images_bp
    from .api.finetuning_api import finetuning_bp
    from .api.notifications_api import notifications_bp
    from .api.debug_api import debug_bp
    from .api.auto_installer_api import auto_installer_api
    from .api.orchestrator_api import orchestrator_bp
    from .api.system_api import system_api
    from .api.model_api import model_api
    # splash_api removed - direct loading only
    from .routes.home_assistant import register_home_assistant_blueprints
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(views_bp)  
    app.register_blueprint(api_bp)  # This already includes most sub-blueprints
    app.register_blueprint(chat_bp, url_prefix='/api')  # FIXED: Register chat API
    app.register_blueprint(models_bp, url_prefix='/api')  # FIXED: Register models API
    # audio_bp is already registered via api_bp, no duplicate registration needed
    app.register_blueprint(images_bp, url_prefix='/api')  # FIXED: Register image API
    app.register_blueprint(finetuning_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(debug_bp, url_prefix='/api/debug')
    app.register_blueprint(auto_installer_api, url_prefix='/api/auto-installer')
    app.register_blueprint(orchestrator_bp, url_prefix='/api')
    app.register_blueprint(system_api, url_prefix='/api/system')
    app.register_blueprint(model_api, url_prefix='/api/model')
    # splash_bp removed
    
    # Register Home Assistant blueprints
    register_home_assistant_blueprints(app)
    
    # Add main health check route for desktop app
    @app.route('/health')
    def health_check():
        """Main health check endpoint for desktop app"""
        import time
        from flask import jsonify
        return jsonify({
            'status': 'ok',
            'service': 'vybe-web',
            'timestamp': time.time()
        })
    
    # Register WebSocket event handlers (avoid duplicate registration)
    from .api.chat_api import register_chat_socketio_handlers
    register_chat_socketio_handlers(socketio)

    # Setup notification system (after WebSocket handlers are registered)
    from .core.notifications import setup_websocket_notifications, setup_tauri_notifications, setup_browser_notifications, get_notification_manager
    
    # Initialize notification callbacks
    setup_websocket_notifications(socketio)
    setup_tauri_notifications()
    setup_browser_notifications()
    
    # Connect agent manager to notification system
    agent_manager = get_agent_manager()
    notification_manager = get_notification_manager()
    agent_manager.add_notification_callback(notification_manager.send_notification)

    # Initialize update notifier (temporarily disabled to fix 404 errors)
    try:
        from .core.update_notifier import update_notifier
        # DISABLED: Check for updates on startup (but don't force)
        # update_info = update_notifier.check_for_updates()
        # if update_info:
        #     update_notifier.send_notification(update_info)
        # Start background checker
        # update_notifier.start_background_checker()
        logger.info("[OK] Update notifier initialized (update checks disabled)")
    except Exception as e:
        logger.warning(f"[WARNING] Update notifier failed to initialize: {e}")
    
    # Initialize default data within the existing app context
    # Initialize default data
    from .models import User, SystemPrompt
    from .utils import initialize_default_data, check_initialization_status
    
    # Create default admin user if no users exist
    if User.query.count() == 0:
        admin_user = User()
        admin_user.username = 'admin'
        admin_user.email = 'admin@vybe.local'
        
        # Use environment variable for default password or generate a secure one
        default_password = os.environ.get('VYBE_DEFAULT_ADMIN_PASSWORD')
        if not default_password:
            # Generate a secure random password if none provided
            import secrets
            import string
            alphabet = string.ascii_letters + string.digits + '!@#$%^&*'
            default_password = ''.join(secrets.choice(alphabet) for i in range(16))
            logger.warning("⚠️  SECURITY: Generated random admin password. Set VYBE_DEFAULT_ADMIN_PASSWORD environment variable or check console output.")
            logger.warning(f"⚠️  ADMIN PASSWORD: {default_password}")
        elif default_password == 'admin123':
            logger.error("⚠️  SECURITY RISK: Using weak default password 'admin123'. Set a strong VYBE_DEFAULT_ADMIN_PASSWORD environment variable for production.")
        
        admin_user.set_password(default_password)
        db.session.add(admin_user)
        db.session.commit()
        logger.info(f"Created default admin user (username: admin)")
        if Config.VYBE_TEST_MODE and default_password == 'admin123':
            logger.info("TEST MODE: Default password is 'admin123' - CHANGE THIS IN PRODUCTION!")
    
    # Create default system prompt if none exists
    if SystemPrompt.query.count() == 0:
        default_prompt = SystemPrompt()
        default_prompt.name = "Default Assistant"
        default_prompt.content = generate_dynamic_system_prompt()  # Use dynamic generation
        default_prompt.description = "Default AI assistant prompt with tool capabilities"
        default_prompt.category = "General"
        db.session.add(default_prompt)
        db.session.commit()
        logger.info("Created default system prompt")
    
    # Initialize comprehensive default data for testing and demo
    init_status = check_initialization_status()
    if not init_status['fully_initialized']:
        logger.info("Initializing default data for testing and demo...")
        if initialize_default_data():
            logger.info("[OK] Default data initialization completed - Application ready for testing!")
        else:
            logger.warning("[WARNING] Some default data initialization failed - Check logs for details")
    else:
        logger.info("[OK] Default data already initialized - Application ready!")
    
    # Initialize and start the scheduler with error handling
    try:
        if not scheduler.running:
            scheduler.start()
            # Register cleanup with both atexit and global cleanup system
            atexit.register(lambda: scheduler.shutdown() if scheduler.running else None)
            register_cleanup_function = _ensure_run_module_import()
            if register_cleanup_function:
                register_cleanup_function(
                    lambda: scheduler.shutdown() if scheduler.running else None,
                    "Background scheduler shutdown"
                )
        logger.info("[OK] Background scheduler started")
    except Exception as e:
        logger.warning(f"[WARNING] Background scheduler failed to start: {e}")
    
    # Register cleanup for job manager with error handling
    try:
        atexit.register(job_manager.stop)
        register_cleanup_function = _ensure_run_module_import()
        if register_cleanup_function:
            register_cleanup_function(job_manager.stop, "Job manager shutdown")
        logger.info("[OK] Job manager cleanup registered")
    except Exception as e:
        logger.warning(f"[WARNING] Job manager cleanup registration failed: {e}")
    
    # Start mDNS service advertisement
    # Temporarily disable mDNS service to prevent startup loops
    # start_mdns_service(port=Config.PORT)
    logger.info("mDNS service disabled for stable startup")
    atexit.register(stop_mdns_service)
    
    logger.info("Vybe application initialized successfully")
    return app

# Export socketio for use in run.py
__all__ = ['create_app', 'socketio']

if __name__ == '__main__':
    app = create_app()
    socketio.run(app, debug=True, host=Config.HOST, port=Config.PORT)
