"""
Transcription Controller for Vybe - Manages whisper.cpp server integration
Handles automated setup, lifecycle management, and API communication
"""

import os
import json
import time
import subprocess
import requests
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging
import shutil

from ..logger import logger


class TranscriptionController:
    """Controller for managing whisper.cpp server lifecycle and API communication"""
    
    def __init__(self, base_dir: Optional[Path] = None):
        # Use user data directory instead of program directory
        import os
        if os.name == 'nt':  # Windows
            user_data_dir = Path(os.path.expanduser("~")) / "AppData" / "Local" / "Vybe AI Assistant"
        else:  # Linux/Mac
            user_data_dir = Path(os.path.expanduser("~")) / ".local" / "share" / "vybe-ai-assistant"
            
        self.base_dir = base_dir or user_data_dir / "vendor" / "whisper-cpp"
        self.models_dir = self.base_dir / "models"
        self.logs_dir = user_data_dir / "logs"
        
        # Server configuration
        self.host = "127.0.0.1"
        self.port = 8080
        self.server_url = f"http://{self.host}:{self.port}"
        
        # Process management
        self.process = None
        self.is_setup_complete = False
        
        # Default model configuration
        self.default_model = "ggml-base.en.bin"
        self.model_url = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin"
        
        # Build configuration
        self.server_executable = self.base_dir / "server"
        if os.name == 'nt':  # Windows
            self.server_executable = self.base_dir / "server.exe"
        
        # Ensure directories exist
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
    
    def check_installation(self) -> Dict[str, Any]:
        """Check if whisper.cpp is properly installed and configured"""
        status = {
            'installed': False,
            'repo_cloned': False,
            'server_built': False,
            'default_model_available': False,
            'setup_required': True,
            'installation_path': str(self.base_dir),
            'error': None
        }
        
        try:
            # Check if repo is cloned
            makefile_path = self.base_dir / "Makefile"
            status['repo_cloned'] = makefile_path.exists()
            
            # Check if server is built
            status['server_built'] = self.server_executable.exists() and self.server_executable.is_file()
            
            # Check if default model exists
            model_path = self.models_dir / self.default_model
            status['default_model_available'] = model_path.exists() and model_path.stat().st_size > 1000000
            
            status['installed'] = (status['repo_cloned'] and 
                                 status['server_built'] and 
                                 status['default_model_available'])
            status['setup_required'] = not status['installed']
            
        except Exception as e:
            status['error'] = str(e)
            logger.warning(f"Whisper.cpp installation check failed: {e}")
        
        self.is_setup_complete = status['installed']
        return status
    
    def get_setup_instructions(self) -> Dict[str, Any]:
        """Get installation instructions for whisper.cpp"""
        if os.name == 'nt':  # Windows
            build_command = "make"  # Assumes make is available via MSYS2/WSL
            additional_notes = [
                "Windows users may need to install build tools (Visual Studio Build Tools or WSL)",
                "Alternative: Download pre-built binaries from the whisper.cpp releases page"
            ]
        else:  # Unix-like systems
            build_command = "make"
            additional_notes = [
                "Ensure you have gcc/clang and make installed",
                "On macOS: xcode-select --install",
                "On Ubuntu/Debian: sudo apt install build-essential"
            ]
        
        return {
            'title': 'Whisper.cpp Setup Required',
            'description': 'High-quality Speech-to-Text transcription powered by OpenAI Whisper',
            'requirements': [
                'Git for cloning the repository',
                'C/C++ compiler (gcc, clang, or MSVC)',
                'Make build system',
                'At least 1GB free disk space'
            ],
            'steps': [
                {
                    'title': 'Clone Repository',
                    'command': f'git clone https://github.com/ggerganov/whisper.cpp.git {self.base_dir}',
                    'description': 'Clone the whisper.cpp repository'
                },
                {
                    'title': 'Build Server',
                    'command': f'cd {self.base_dir} && {build_command}',
                    'description': 'Compile the whisper.cpp server executable'
                },
                {
                    'title': 'Download Model',
                    'command': f'curl -L {self.model_url} -o {self.models_dir / self.default_model}',
                    'description': 'Download the base English transcription model (~150MB)'
                }
            ],
            'notes': [
                'Build process may take 2-5 minutes',
                'Model download requires ~150MB bandwidth',
                'Larger models provide better accuracy but require more resources'
            ] + additional_notes
        }
    
    def auto_setup(self) -> Tuple[bool, str]:
        """Attempt automated setup of whisper.cpp"""
        try:
            status = self.check_installation()
            
            # Step 1: Clone repository if needed
            if not status['repo_cloned']:
                logger.info("Cloning whisper.cpp repository...")
                result = subprocess.run([
                    'git', 'clone', 
                    'https://github.com/ggerganov/whisper.cpp.git',
                    str(self.base_dir)
                ], capture_output=True, text=True, timeout=300)
                
                if result.returncode != 0:
                    return False, f"Failed to clone repository: {result.stderr}"
            
            # Step 2: Build server if needed
            if not status['server_built']:
                logger.info("Building whisper.cpp server...")
                result = subprocess.run(['make'], 
                                      cwd=self.base_dir,
                                      capture_output=True, text=True, timeout=300)
                
                if result.returncode != 0:
                    return False, f"Failed to build server: {result.stderr}"
            
            # Step 3: Download model if needed
            if not status['default_model_available']:
                logger.info("Downloading default transcription model...")
                model_path = self.models_dir / self.default_model
                
                # Use requests to download with progress
                response = requests.get(self.model_url, stream=True, timeout=30)
                response.raise_for_status()
                
                with open(model_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                # Verify download
                if not model_path.exists() or model_path.stat().st_size < 1000000:
                    return False, "Model download failed or incomplete"
            
            logger.info("Whisper.cpp setup completed successfully")
            self.is_setup_complete = True
            return True, "Whisper.cpp setup completed successfully"
            
        except subprocess.TimeoutExpired:
            return False, "Setup timed out. Please try manual installation."
        except Exception as e:
            logger.error(f"Auto setup failed: {e}")
            return False, f"Auto setup failed: {str(e)}"
    
    def start(self) -> Tuple[bool, str]:
        """Start the whisper.cpp server"""
        if self.is_running():
            return True, "Transcription server is already running"
        
        if not self.is_setup_complete:
            status = self.check_installation()
            if not status['installed']:
                return False, "Whisper.cpp not properly installed. Please run setup first."
        
        try:
            log_file = self.logs_dir / "transcription_server.log"
            model_path = self.models_dir / self.default_model
            
            # Start whisper.cpp server
            cmd = [
                str(self.server_executable),
                '--host', self.host,
                '--port', str(self.port),
                '--model', str(model_path),
                '--threads', '4'
            ]
            
            with open(log_file, 'w') as f:
                self.process = subprocess.Popen(
                    cmd,
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    cwd=self.base_dir
                )
            
            # Wait for server to start
            max_attempts = 30
            for i in range(max_attempts):
                if self.is_running():
                    logger.info(f"Transcription server started successfully on {self.server_url}")
                    return True, f"Transcription server started on {self.server_url}"
                time.sleep(1)
            
            # If we get here, server didn't start properly
            if self.process:
                self.process.terminate()
                self.process = None
            return False, "Transcription server failed to start within timeout period"
            
        except Exception as e:
            logger.error(f"Failed to start transcription server: {e}")
            return False, f"Failed to start transcription server: {str(e)}"
    
    def stop(self) -> Tuple[bool, str]:
        """Stop the transcription server"""
        if not self.is_running():
            return True, "Transcription server is not running"
        
        try:
            if self.process:
                self.process.terminate()
                self.process.wait(timeout=10)
                self.process = None
                logger.info("Transcription server stopped successfully")
                return True, "Transcription server stopped successfully"
            return True, "Transcription server stopped"
            
        except subprocess.TimeoutExpired:
            if self.process:
                self.process.kill()
                self.process = None
            return True, "Transcription server forcefully stopped"
        except Exception as e:
            logger.error(f"Error stopping transcription server: {e}")
            return False, f"Error stopping transcription server: {str(e)}"
    
    def is_running(self) -> bool:
        """Check if transcription server is running and responsive"""
        if self.process and self.process.poll() is None:
            try:
                response = requests.get(f"{self.server_url}/", timeout=5)
                # Whisper.cpp server returns a simple response
                return response.status_code in [200, 404]  # 404 is normal for root path
            except Exception as e:
                logger.debug(f"Transcription server status check failed: {e}")
                pass
        return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status of transcription service"""
        installation = self.check_installation()
        
        return {
            'service_name': 'Whisper.cpp Transcription',
            'installed': installation['installed'],
            'running': self.is_running(),
            'server_url': self.server_url if self.is_running() else None,
            'setup_required': installation['setup_required'],
            'default_model': self.default_model,
            'models_directory': str(self.models_dir),
            'server_executable': str(self.server_executable),
            'installation_status': installation
        }
    
    def transcribe_audio(self, audio_file_path: str, language: str = 'en') -> Tuple[bool, str, Optional[str]]:
        """Transcribe audio file to text"""
        if not self.is_running():
            return False, "Transcription server is not running", None
        
        file_path = Path(audio_file_path)
        if not file_path.exists():
            return False, f"Audio file not found: {audio_file_path}", None
        
        try:
            # Prepare file for upload
            with open(file_path, 'rb') as f:
                files = {'file': (file_path.name, f, 'audio/wav')}
                data = {'language': language}
                
                # Make request to transcription server
                response = requests.post(
                    f"{self.server_url}/inference",
                    files=files,
                    data=data,
                    timeout=60  # Longer timeout for transcription
                )
            
            if response.status_code == 200:
                result = response.json()
                text = result.get('text', '').strip()
                
                if text:
                    return True, "Transcription completed successfully", text
                else:
                    return False, "No text was transcribed from the audio", None
            else:
                error_msg = f"Transcription request failed: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = error_data.get('error', error_msg)
                except Exception as e:
                    logger.debug(f"Failed to parse transcription error response: {e}")
                    pass
                return False, error_msg, None
                
        except requests.RequestException as e:
            logger.error(f"Transcription failed: {e}")
            return False, f"Transcription failed: {str(e)}", None
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available transcription models"""
        models = []
        
        # Check for downloaded models
        if self.models_dir.exists():
            for model_file in self.models_dir.glob("ggml-*.bin"):
                model_info = {
                    'filename': model_file.name,
                    'path': str(model_file),
                    'size': model_file.stat().st_size,
                    'type': 'whisper'
                }
                
                # Determine model details from filename
                if 'tiny' in model_file.name:
                    model_info.update({'name': 'Tiny', 'params': '39M', 'speed': 'Very Fast'})
                elif 'base' in model_file.name:
                    model_info.update({'name': 'Base', 'params': '74M', 'speed': 'Fast'})
                elif 'small' in model_file.name:
                    model_info.update({'name': 'Small', 'params': '244M', 'speed': 'Medium'})
                elif 'medium' in model_file.name:
                    model_info.update({'name': 'Medium', 'params': '769M', 'speed': 'Slow'})
                elif 'large' in model_file.name:
                    model_info.update({'name': 'Large', 'params': '1550M', 'speed': 'Very Slow'})
                else:
                    model_info.update({'name': 'Unknown', 'params': 'Unknown', 'speed': 'Unknown'})
                
                models.append(model_info)
        
        return models
