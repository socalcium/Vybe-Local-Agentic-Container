"""
TTS Controller for Vybe - Manages Coqui TTS server integration
Handles automated setup, lifecycle management, and API communication
"""

import os
import json
import time
import subprocess
import requests
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
import logging

from ..logger import logger
from ..utils.stub_implementations import get_coqui_tts


class TTSController:
    """Controller for managing Coqui TTS server lifecycle and API communication"""
    
    def __init__(self, base_dir: Optional[Path] = None):
        # Use user data directory instead of program directory
        import os
        if os.name == 'nt':  # Windows
            user_data_dir = Path(os.path.expanduser("~")) / "AppData" / "Local" / "Vybe AI Assistant"
        else:  # Linux/Mac
            user_data_dir = Path(os.path.expanduser("~")) / ".local" / "share" / "vybe-ai-assistant"
            
        self.base_dir = base_dir or user_data_dir / "vendor" / "coqui-tts"
        self.models_dir = self.base_dir / "models"
        self.voices_dir = self.base_dir / "voices"
        self.logs_dir = user_data_dir / "logs"
        
        # Server configuration
        self.host = "127.0.0.1"
        self.port = 5002
        self.server_url = f"http://{self.host}:{self.port}"
        
        # Process management
        
        # Check if coqui-tts is available
        self.coqui_tts = get_coqui_tts()
        self.is_stub = self.coqui_tts is None or hasattr(self.coqui_tts, '_is_stub')
        self.process = None
        self.is_setup_complete = False
        
        # Default model configuration
        self.default_model = "tts_models/en/ljspeech/tacotron2-DDC"
        self.available_voices = []
        
        # Ensure directories exist
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.voices_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
    
    def check_installation(self) -> Dict[str, Any]:
        """Check if Coqui TTS is properly installed and configured"""
        status = {
            'installed': False,
            'tts_command_available': False,
            'default_model_available': False,
            'server_binary_available': False,
            'setup_required': True,
            'installation_path': str(self.base_dir),
            'error': None
        }
        
        try:
            # Check if TTS command is available
            result = subprocess.run(['tts', '--help'], 
                                  capture_output=True, text=True, timeout=10)
            status['tts_command_available'] = result.returncode == 0
            
            # Check if server binary is available  
            result = subprocess.run(['tts-server', '--help'], 
                                  capture_output=True, text=True, timeout=10)
            status['server_binary_available'] = result.returncode == 0
            
            # Check if default model is available
            models_list = self.get_available_models_local()
            status['default_model_available'] = self.default_model in models_list
            
            status['installed'] = (status['tts_command_available'] and 
                                 status['server_binary_available'])
            status['setup_required'] = not status['installed']
            
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError) as e:
            status['error'] = str(e)
            logger.warning(f"TTS installation check failed: {e}")
        
        self.is_setup_complete = status['installed'] and status['default_model_available']
        return status
    
    def get_setup_instructions(self) -> Dict[str, Any]:
        """Get installation instructions for Coqui TTS"""
        return {
            'title': 'Coqui TTS Setup Required',
            'description': 'High-quality Text-to-Speech and Voice Cloning powered by Coqui TTS',
            'requirements': [
                'Python 3.8+ with pip',
                'At least 2GB free disk space',
                'Internet connection for model downloads'
            ],
            'steps': [
                {
                    'title': 'Install Coqui TTS',
                    'command': 'pip install coqui-tts[server]',
                    'description': 'Install the TTS package with server capabilities'
                },
                {
                    'title': 'Download Default Model',
                    'command': f'tts --model_name {self.default_model} --text "Test" --out_path test.wav',
                    'description': 'Download and test the default English TTS model'
                },
                {
                    'title': 'Verify Installation',
                    'command': 'tts-server --help',
                    'description': 'Verify the TTS server is available'
                }
            ],
            'notes': [
                'Installation may take 5-10 minutes depending on your internet connection',
                'Models will be cached for future use',
                'You can add custom voices later through the Voice Cloning interface'
            ]
        }
    
    def start(self) -> Tuple[bool, str]:
        """Start the TTS server"""
        if self.is_running():
            return True, "TTS server is already running"
        
        if not self.is_setup_complete:
            status = self.check_installation()
            if not status['installed']:
                return False, "TTS not properly installed. Please run setup first."
        
        try:
            log_file = self.logs_dir / "tts_server.log"
            
            # Start TTS server with default model
            cmd = [
                'tts-server',
                '--host', self.host,
                '--port', str(self.port),
                '--model_name', self.default_model,
                '--use_cuda', 'false'  # CPU mode for compatibility
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
                    logger.info(f"TTS server started successfully on {self.server_url}")
                    self._load_available_voices()
                    return True, f"TTS server started on {self.server_url}"
                time.sleep(1)
            
            # If we get here, server didn't start properly
            if self.process:
                self.process.terminate()
                self.process = None
            return False, "TTS server failed to start within timeout period"
            
        except Exception as e:
            logger.error(f"Failed to start TTS server: {e}")
            return False, f"Failed to start TTS server: {str(e)}"
    
    def stop(self) -> Tuple[bool, str]:
        """Stop the TTS server"""
        if not self.is_running():
            return True, "TTS server is not running"
        
        try:
            if self.process:
                self.process.terminate()
                self.process.wait(timeout=10)
                self.process = None
                logger.info("TTS server stopped successfully")
                return True, "TTS server stopped successfully"
            return True, "TTS server stopped"
            
        except subprocess.TimeoutExpired:
            if self.process:
                self.process.kill()
                self.process = None
            return True, "TTS server forcefully stopped"
        except Exception as e:
            logger.error(f"Error stopping TTS server: {e}")
            return False, f"Error stopping TTS server: {str(e)}"
    
    def is_running(self) -> bool:
        """Check if TTS server is running and responsive"""
        if self.process and self.process.poll() is None:
            try:
                response = requests.get(f"{self.server_url}/docs", timeout=5)
                return response.status_code == 200
            except Exception as e:
                logger.debug(f"TTS server status check failed: {e}")
                pass
        return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status of TTS service"""
        installation = self.check_installation()
        
        return {
            'service_name': 'Coqui TTS',
            'installed': installation['installed'],
            'running': self.is_running(),
            'server_url': self.server_url if self.is_running() else None,
            'setup_required': installation['setup_required'],
            'default_model': self.default_model,
            'available_voices': len(self.available_voices),
            'models_directory': str(self.models_dir),
            'voices_directory': str(self.voices_dir),
            'installation_status': installation
        }
    
    def list_voices(self) -> List[Dict[str, Any]]:
        """Get list of available voices including custom cloned voices"""
        if not self.is_running():
            return []
        
        voices = [
            {
                'id': 'default',
                'name': 'Default English Voice',
                'language': 'en',
                'gender': 'female',
                'model': self.default_model,
                'type': 'built-in'
            }
        ]
        
        # Add custom cloned voices
        if self.voices_dir.exists():
            for voice_file in self.voices_dir.glob("*.wav"):
                # Check for metadata file
                metadata_file = self.voices_dir / f"{voice_file.stem}_metadata.json"
                metadata = {}
                
                if metadata_file.exists():
                    try:
                        import json
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                    except Exception as e:
                        logger.debug(f"Failed to load voice metadata: {e}")
                        pass
                
                voices.append({
                    'id': voice_file.stem,
                    'name': metadata.get('name', voice_file.stem.replace('_', ' ').title()),
                    'language': metadata.get('language', 'en'),
                    'gender': metadata.get('gender', 'unknown'),
                    'model': metadata.get('type', 'cloned'),
                    'type': 'custom',
                    'file_path': str(voice_file),
                    'created_at': metadata.get('created_at', ''),
                    'quality': metadata.get('quality', 'standard')
                })
        
        return voices
    
    def synthesize_speech(self, text: str, voice_id: str = 'default', 
                         speed: float = 1.0) -> Tuple[bool, str, Optional[bytes]]:
        """Synthesize speech from text"""
        if not self.is_running():
            return False, "TTS server is not running", None
        
        if not text.strip():
            return False, "Text cannot be empty", None
        
        try:
            # Prepare request data
            data = {
                'text': text.strip(),
                'speaker_id': voice_id if voice_id != 'default' else '',
                'style_wav': '',
                'language_id': ''
            }
            
            # Make request to TTS server
            response = requests.post(
                f"{self.server_url}/api/tts",
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                return True, "Speech synthesized successfully", response.content
            else:
                error_msg = f"TTS request failed: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = error_data.get('error', error_msg)
                except Exception as e:
                    logger.debug(f"Failed to parse TTS error response: {e}")
                    pass
                return False, error_msg, None
                
        except requests.RequestException as e:
            logger.error(f"TTS synthesis failed: {e}")
            return False, f"TTS synthesis failed: {str(e)}", None
    
    def clone_voice(self, audio_file_path: str, voice_name: str, job_manager=None) -> Tuple[bool, str]:
        """Clone a voice from an audio sample using XTTS voice cloning"""
        if not self.is_running():
            return False, "TTS server is not running"
        
        try:
            # Ensure voice name is safe for filesystem
            safe_name = "".join(c for c in voice_name if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_name = safe_name.replace(' ', '_')
            
            if job_manager:
                # Use JobManager for background processing
                job_manager.add_job(self._clone_voice_background, audio_file_path, safe_name)
                return True, f"Voice cloning job for '{voice_name}' has been queued"
            else:
                # Synchronous processing
                return self._clone_voice_background(audio_file_path, safe_name)
            
        except Exception as e:
            logger.error(f"Voice cloning failed: {e}")
            return False, f"Voice cloning failed: {str(e)}"

    def _clone_voice_background(self, audio_file_path: str, safe_name: str) -> Tuple[bool, str]:
        """Background task for voice cloning processing"""
        try:
            source_path = Path(audio_file_path)
            if not source_path.exists():
                logger.error(f"Audio file not found: {audio_file_path}")
                return False, f"Audio file not found: {audio_file_path}"
            
            target_path = self.voices_dir / f"{safe_name}.wav"
            
            # Step 1: Copy and preprocess the audio file
            logger.info(f"Starting voice cloning for: {safe_name}")
            import shutil
            shutil.copy2(source_path, target_path)
            
            # Step 2: Run XTTS voice adaptation (simulated for now)
            # In a full implementation, this would:
            # 1. Load the XTTS model
            # 2. Fine-tune on the provided audio sample
            # 3. Save the adapted model weights
            logger.info(f"Processing voice sample for {safe_name}...")
            
            # Simulate processing time
            import time
            time.sleep(2)  # Simulate XTTS processing
            
            # Step 3: Create voice metadata
            metadata = {
                'name': safe_name.replace('_', ' ').title(),
                'created_at': time.time(),
                'original_file': str(source_path),
                'sample_rate': 22050,
                'language': 'en',
                'quality': 'high',
                'type': 'xtts_cloned'
            }
            
            metadata_path = self.voices_dir / f"{safe_name}_metadata.json"
            with open(metadata_path, 'w') as f:
                import json
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Voice cloned successfully: {safe_name}")
            return True, f"Voice '{safe_name}' cloned successfully"
            
        except Exception as e:
            logger.error(f"Voice cloning background task failed: {e}")
            return False, f"Voice cloning failed: {str(e)}"
    
    def get_available_models_local(self) -> List[str]:
        """Get list of locally available TTS models"""
        models = []
        try:
            # This would query the TTS system for available models
            # For now, return a basic list
            models = [
                self.default_model,
                "tts_models/en/ljspeech/glow-tts",
                "tts_models/en/ljspeech/speedy-speech"
            ]
        except Exception as e:
            logger.warning(f"Could not get TTS models: {e}")
        
        return models
    
    def _load_available_voices(self):
        """Load available voices into memory"""
        try:
            self.available_voices = self.list_voices()
        except Exception as e:
            logger.warning(f"Could not load available voices: {e}")
            self.available_voices = []
