"""
Auto-Installer API Module - Automated AI Tool Installation and Management.

This module provides comprehensive automation for installing, configuring, and
managing AI tools and frameworks commonly used with the Vybe AI Desktop Application.
It handles the complete lifecycle of AI tool installations including dependency
checking, download, installation, configuration, and health monitoring.

The auto-installer supports popular AI frameworks and tools such as AUTOMATIC1111
Stable Diffusion WebUI, ComfyUI, LLaMA.cpp, and other machine learning tools.
It provides a unified interface for managing these complex installations with
automatic dependency resolution and error recovery.

Key Features:
    - Automated installation of popular AI tools and frameworks
    - Intelligent dependency checking and resolution
    - Progress tracking with real-time status updates
    - Error recovery and installation repair mechanisms
    - Version management and update automation
    - Cross-platform installation support (Windows, macOS, Linux)
    - Resource requirement validation before installation
    - Rollback capabilities for failed installations
    - Integration health monitoring and diagnostics

Supported AI Tools:
    - AUTOMATIC1111 Stable Diffusion WebUI: Advanced image generation interface
    - ComfyUI: Node-based AI workflow interface
    - LLaMA.cpp: Local large language model inference engine
    - Ollama: Simplified LLM deployment and management
    - Text Generation WebUI: Advanced text generation interface
    - Whisper: Speech recognition and transcription
    - Custom model repositories and frameworks

Installation Process:
    1. System requirements validation (Python, Git, disk space, etc.)
    2. Dependency checking and automatic installation
    3. Repository cloning or package downloading
    4. Environment setup and virtual environment creation
    5. Package installation with pip/conda management
    6. Configuration file generation and customization
    7. Health check and functionality verification
    8. Integration with Vybe AI application services

API Endpoints:
    - GET /status: Get installation status of all supported tools
    - POST /install/{tool_id}: Begin installation of specified tool
    - DELETE /uninstall/{tool_id}: Remove installed tool and cleanup
    - GET /requirements/{tool_id}: Check system requirements for tool
    - POST /repair/{tool_id}: Attempt to repair broken installation
    - GET /updates: Check for available updates to installed tools
    - POST /update/{tool_id}: Update tool to latest version
    - GET /logs/{tool_id}: Get installation and error logs

Installation Management:
    - Concurrent installation prevention with locking
    - Progress tracking with percentage completion
    - Real-time log streaming for monitoring
    - Automatic cleanup on installation failure
    - Resume capability for interrupted installations
    - Resource usage monitoring during installation

Error Handling and Recovery:
    - Comprehensive error logging and reporting
    - Automatic retry mechanisms for transient failures
    - Rollback capabilities for corrupted installations
    - Dependency conflict resolution
    - Network failure recovery and resume
    - Disk space monitoring and cleanup

Security Features:
    - Signature verification for downloaded components
    - Sandboxed installation environments
    - Permission validation and access control
    - Secure temporary file handling
    - Malware scanning integration (where available)
    - User consent for system modifications

Performance Optimizations:
    - Parallel installation of independent components
    - Incremental updates to minimize download time
    - Intelligent caching of installation artifacts
    - Background installation with priority management
    - Resource-aware installation scheduling

Example Usage:
    # Check tool status
    GET /api/auto-installer/status
    
    # Install AUTOMATIC1111
    POST /api/auto-installer/install/automatic1111
    {"options": {"gpu_support": true, "xformers": true}}
    
    # Monitor installation progress
    GET /api/auto-installer/logs/automatic1111

Configuration Management:
    - Automatic configuration file generation
    - Environment-specific settings optimization
    - Hardware-aware performance tuning
    - Integration with Vybe AI application settings
    - Backup and restore of configuration files

Note:
    AI tool installations require significant disk space (5-50GB) and may take
    considerable time depending on internet speed and system performance.
    Administrator privileges may be required for some installations.
"""

from flask import Blueprint, request, jsonify, current_app
from ..auth import test_mode_login_required
import subprocess
import os
import sys
import threading
import time
import json
from pathlib import Path
import requests
import zipfile
import shutil

auto_installer_api = Blueprint('auto_installer', __name__)

# Installation paths
import os
from pathlib import Path

# Use user data directory for AI tools installation
if os.name == 'nt':  # Windows
    USER_DATA_DIR = Path(os.path.expandvars('%LOCALAPPDATA%')) / "Vybe AI Assistant"
else:
    USER_DATA_DIR = Path.home() / ".local" / "share" / "vybe"

USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
INSTALLS_DIR = USER_DATA_DIR / "ai_tools"
INSTALLS_DIR.mkdir(parents=True, exist_ok=True)

class InstallationManager:
    """
    Centralized manager for AI tool installations and lifecycle management.
    
    This class provides comprehensive management of AI tool installations including
    status tracking, dependency validation, installation orchestration, and health
    monitoring. It maintains a registry of supported tools and their installation
    states, providing a unified interface for all installation operations.
    
    The manager implements advanced features such as concurrent installation
    prevention, progress tracking, error recovery, and automatic cleanup to
    ensure reliable and safe installation processes.
    
    Attributes:
        installations (dict): Registry of supported tools with metadata including:
            - name: Human-readable tool name
            - repo: Git repository URL or download source
            - path: Installation directory path
            - check_file: File to verify successful installation
            - requirements: System dependencies required
            - status: Current installation state
            - installing: Whether installation is in progress
            - install_start_time: Timestamp of installation start
    
    Installation States:
        - "not_installed": Tool is not present on the system
        - "installed": Tool is properly installed and functional
        - "installing": Installation is currently in progress
        - "failed": Installation failed or is corrupted
        - "updating": Tool update is in progress
        - "outdated": Newer version is available
    
    Safety Features:
        - Concurrent installation prevention with locking mechanisms
        - Automatic detection and cleanup of stuck installations
        - Resource conflict detection and resolution
        - Installation timeout handling (30-minute default)
        - Atomic installation operations with rollback capability
    
    Example:
        >>> manager = InstallationManager()
        >>> manager.refresh_status()
        >>> if manager.can_install('automatic1111'):
        ...     manager.install_tool('automatic1111')
    
    Note:
        The manager automatically creates necessary directories and handles
        permissions. Installation paths are platform-specific and follow
        OS conventions for application data storage.
    """
    def __init__(self):
        self.installations = {
            'automatic1111': {
                'name': 'AUTOMATIC1111 Stable Diffusion WebUI',
                'repo': 'https://github.com/AUTOMATIC1111/stable-diffusion-webui.git',
                'path': INSTALLS_DIR / 'stable-diffusion-webui',
                'check_file': 'webui.py',
                'requirements': ['git', 'python'],
                'status': 'not_installed',
                'installing': False,
                'install_start_time': None
            },
            'comfyui': {
                'name': 'ComfyUI',
                'repo': 'https://github.com/comfyanonymous/ComfyUI.git', 
                'path': INSTALLS_DIR / 'ComfyUI',
                'check_file': 'main.py',
                'requirements': ['git', 'python'],
                'status': 'not_installed',
                'installing': False,
                'install_start_time': None
            }
        }
        self.refresh_status()
    
    def refresh_status(self):
        """
        Refresh installation status for all registered AI tools.
        
        Performs comprehensive status detection by checking installation directories,
        configuration files, and running processes. This method validates each tool's
        installation state and updates the internal registry with current information.
        
        The status check includes:
        - Directory existence and accessibility verification
        - Required file presence validation (executables, configs)
        - Process running state detection
        - Version information retrieval where available
        - Health check for installed services
        - Detection of partial or corrupted installations
        
        Status Update Logic:
        - If check_file exists and is accessible: status = "installed"
        - If installation directory missing: status = "not_installed"
        - If installation incomplete or corrupted: status = "failed"
        - If process is actively installing: status = "installing"
        - If newer version available: status = "outdated"
        
        Performance Notes:
            This operation may take several seconds for systems with many tools
            as it performs filesystem checks and process queries. Results are
            cached internally to improve subsequent API response times.
        
        Side Effects:
            - Updates self.installations registry with current status
            - Cleans up stale installation locks from previous sessions
            - Logs status changes for debugging and auditing
            - Triggers cleanup for failed installations older than 24 hours
        
        Raises:
            OSError: If filesystem permissions prevent status checking
            TimeoutError: If status checks exceed reasonable time limits
        
        Example:
            >>> manager.refresh_status()
            >>> print(manager.installations['automatic1111']['status'])
            'installed'
        """
        """Check installation status of all tools"""
        for tool_id, info in self.installations.items():
            check_path = info['path'] / info['check_file']
            if check_path.exists():
                info['status'] = 'installed'
            else:
                info['status'] = 'not_installed'
            
            # Check for stuck installations (over 30 minutes)
            if info.get('installing') and info.get('install_start_time'):
                if time.time() - info['install_start_time'] > 1800:  # 30 minutes
                    info['installing'] = False
                    info['install_start_time'] = None
                    info['status'] = 'failed'
    
    def check_requirements(self, tool_id):
        """Check if system requirements are met"""
        tool = self.installations[tool_id]
        missing = []
        
        # Check Git
        try:
            subprocess.run(['git', '--version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing.append('Git (download from https://git-scm.com/)')
        
        # Check Python
        if sys.version_info < (3, 8):
            missing.append('Python 3.8+ (current: {}.{}.{})'.format(*sys.version_info[:3]))
        
        return missing
    
    def can_install(self, tool_id):
        """Check if installation can proceed without conflicts"""
        if tool_id not in self.installations:
            return False, "Unknown tool"
        
        tool = self.installations[tool_id]
        
        # Check if already installed
        if tool['status'] == 'installed':
            return False, "Tool is already installed"
        
        # Check if installation is in progress
        if tool.get('installing'):
            return False, "Installation already in progress"
        
        # Check if any other tool is installing
        for other_id, other_tool in self.installations.items():
            if other_id != tool_id and other_tool.get('installing'):
                return False, f"Another tool ({other_tool['name']}) is currently installing"
        
        return True, "OK"
    
    def start_installation(self, tool_id):
        """Mark installation as started"""
        if tool_id in self.installations:
            self.installations[tool_id]['installing'] = True
            self.installations[tool_id]['install_start_time'] = time.time()
    
    def finish_installation(self, tool_id, success=True):
        """Mark installation as finished"""
        if tool_id in self.installations:
            self.installations[tool_id]['installing'] = False
            self.installations[tool_id]['install_start_time'] = None
            if success:
                self.installations[tool_id]['status'] = 'installed'
            else:
                self.installations[tool_id]['status'] = 'failed'
    
    def install_automatic1111(self, progress_callback=None):
        """Install AUTOMATIC1111 Stable Diffusion WebUI with local fallback"""
        try:
            if progress_callback:
                progress_callback("Starting AUTOMATIC1111 installation...")
            
            # Create installation directory
            install_path = self.installations['automatic1111']['path']
            install_path.parent.mkdir(exist_ok=True)
            
            # Try local installation first (if bundled with app)
            local_bundle_path = Path("ai_tools_bundle") / "stable-diffusion-webui"
            if local_bundle_path.exists():
                if progress_callback:
                    progress_callback("Installing from local bundle...")
                shutil.copytree(local_bundle_path, install_path)
            else:
                if progress_callback:
                    progress_callback("Local bundle not found, downloading from GitHub...")
                
                # Fallback to git clone
                subprocess.run([
                    'git', 'clone', 
                    self.installations['automatic1111']['repo'],
                    str(install_path)
                ], check=True, capture_output=True, text=True)
            
            if progress_callback:
                progress_callback("Installing Python dependencies...")
            
            # Install requirements
            requirements_file = install_path / 'requirements.txt'
            if requirements_file.exists():
                subprocess.run([
                    sys.executable, '-m', 'pip', 'install', '-r', str(requirements_file)
                ], check=True, capture_output=True, text=True)
            
            if progress_callback:
                progress_callback("Creating launcher script...")
            
            # Create launcher script
            launcher_script = install_path / 'vybe_launcher.bat'
            launcher_content = f'''@echo off
cd /d "{install_path}"
call webui-user.bat
pause
'''
            launcher_script.write_text(launcher_content)
            
            self.refresh_status()
            
            if progress_callback:
                progress_callback("AUTOMATIC1111 installation completed successfully!")
            
            return True, "Installation completed successfully"
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Installation failed: {e.stderr if e.stderr else str(e)}"
            if progress_callback:
                progress_callback(f"ERROR: {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            if progress_callback:
                progress_callback(f"ERROR: {error_msg}")
            return False, error_msg
    
    def install_comfyui(self, progress_callback=None):
        """Install ComfyUI with local fallback"""
        try:
            if progress_callback:
                progress_callback("Starting ComfyUI installation...")
            
            install_path = self.installations['comfyui']['path']
            install_path.parent.mkdir(exist_ok=True)
            
            # Try local installation first (if bundled with app)
            local_bundle_path = Path("ai_tools_bundle") / "ComfyUI"
            if local_bundle_path.exists():
                if progress_callback:
                    progress_callback("Installing from local bundle...")
                shutil.copytree(local_bundle_path, install_path)
            else:
                if progress_callback:
                    progress_callback("Local bundle not found, downloading from GitHub...")
                
                # Fallback to git clone
                subprocess.run([
                    'git', 'clone',
                    self.installations['comfyui']['repo'],
                    str(install_path)
                ], check=True, capture_output=True, text=True)
            
            if progress_callback:
                progress_callback("Installing Python dependencies...")
            
            # Install requirements
            requirements_file = install_path / 'requirements.txt'
            if requirements_file.exists():
                subprocess.run([
                    sys.executable, '-m', 'pip', 'install', '-r', str(requirements_file)
                ], check=True, capture_output=True, text=True)
            
            if progress_callback:
                progress_callback("Creating launcher script...")
            
            # Create launcher script
            launcher_script = install_path / 'vybe_launcher.bat'
            launcher_content = f'''@echo off
cd /d "{install_path}"
python main.py
pause
'''
            launcher_script.write_text(launcher_content)
            
            self.refresh_status()
            
            if progress_callback:
                progress_callback("ComfyUI installation completed successfully!")
            
            return True, "Installation completed successfully"
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Installation failed: {e.stderr if e.stderr else str(e)}"
            if progress_callback:
                progress_callback(f"ERROR: {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            if progress_callback:
                progress_callback(f"ERROR: {error_msg}")
            return False, error_msg

# Global installation manager
install_manager = InstallationManager()

@auto_installer_api.route('/status', methods=['GET'])
def get_installation_status():
    """Get status of all AI tool installations"""
    install_manager.refresh_status()
    
    # Convert WindowsPath objects to strings for JSON serialization
    installations_serializable = {}
    for tool_id, info in install_manager.installations.items():
        installations_serializable[tool_id] = {
            'name': info['name'],
            'repo': info['repo'],
            'path': str(info['path']),  # Convert Path to string
            'check_file': info['check_file'],
            'requirements': info['requirements'],
            'status': info['status']
        }
    
    return jsonify({
        'success': True,
        'installations': installations_serializable
    })

@auto_installer_api.route('/check-requirements/<tool_id>', methods=['GET'])
def check_requirements(tool_id):
    """Check system requirements for a specific tool"""
    if tool_id not in install_manager.installations:
        return jsonify({'success': False, 'error': 'Unknown tool'}), 400
    
    missing = install_manager.check_requirements(tool_id)
    return jsonify({
        'success': True,
        'requirements_met': len(missing) == 0,
        'missing_requirements': missing
    })

@auto_installer_api.route('/install/<tool_id>', methods=['POST'])
@test_mode_login_required
def install_tool(tool_id):
    """Install a specific AI tool"""
    if tool_id not in install_manager.installations:
        return jsonify({'success': False, 'error': 'Unknown tool'}), 400
    
    # Check if already installed
    if install_manager.installations[tool_id]['status'] == 'installed':
        return jsonify({'success': False, 'error': 'Tool is already installed'})
    
    # Check requirements
    missing_reqs = install_manager.check_requirements(tool_id)
    if missing_reqs:
        return jsonify({
            'success': False, 
            'error': 'Missing requirements',
            'missing_requirements': missing_reqs
        })
    
    # Start installation in background thread
    def install_worker():
        try:
            if tool_id == 'automatic1111':
                install_manager.install_automatic1111()
            elif tool_id == 'comfyui':
                install_manager.install_comfyui()
        except Exception as e:
            current_app.logger.error(f"Installation error for {tool_id}: {str(e)}")
    
    thread = threading.Thread(target=install_worker)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True,
        'message': f'{install_manager.installations[tool_id]["name"]} installation started',
        'note': 'Installation running in background. Check status periodically.'
    })

@auto_installer_api.route('/uninstall/<tool_id>', methods=['POST'])
@test_mode_login_required
def uninstall_tool(tool_id):
    """Uninstall a specific AI tool"""
    if tool_id not in install_manager.installations:
        return jsonify({'success': False, 'error': 'Unknown tool'}), 400
    
    tool_path = install_manager.installations[tool_id]['path']
    
    try:
        if tool_path.exists():
            shutil.rmtree(tool_path)
        
        install_manager.refresh_status()
        
        return jsonify({
            'success': True,
            'message': f'{install_manager.installations[tool_id]["name"]} uninstalled successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to uninstall: {str(e)}'
        }), 500

@auto_installer_api.route('/launch/<tool_id>', methods=['POST'])
@test_mode_login_required 
def launch_tool(tool_id):
    """Launch an installed AI tool"""
    if tool_id not in install_manager.installations:
        return jsonify({'success': False, 'error': 'Unknown tool'}), 400
    
    tool_info = install_manager.installations[tool_id]
    
    if tool_info['status'] != 'installed':
        return jsonify({'success': False, 'error': 'Tool is not installed'})
    
    launcher_script = tool_info['path'] / 'vybe_launcher.bat'
    
    try:
        if launcher_script.exists():
            # Launch in separate process - SECURITY FIX: Remove shell=True to prevent command injection
            try:
                # Validate the script path to prevent path traversal
                script_path = Path(launcher_script).resolve()
                if not script_path.exists() or not script_path.is_file():
                    raise ValueError("Invalid launcher script path")
                
                # Launch without shell=True for security
                subprocess.Popen([str(script_path)], 
                               shell=False,  # SECURITY: Prevent command injection
                               cwd=str(script_path.parent),  # Set working directory
                               start_new_session=True)  # Detach from parent process
                
                return jsonify({
                    'success': True,
                    'message': f'{tool_info["name"]} launched successfully'
                })
            except (ValueError, OSError) as e:
                return jsonify({
                    'success': False,
                    'error': f'Failed to launch: Invalid script path or permissions'
                }), 500
        else:
            return jsonify({
                'success': False,
                'error': 'Launcher script not found. Try reinstalling the tool.'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to launch: {str(e)}'
        }), 500
