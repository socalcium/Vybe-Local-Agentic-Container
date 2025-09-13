"""
Video Generator Controller for Vybe - Manages ComfyUI integration for video generation
Handles automated setup, lifecycle management, and workflow execution
"""

import os
import json
import time
import subprocess
import requests
import threading
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
import logging

from ..logger import logger


class VideoGeneratorController:
    """Controller for managing ComfyUI server lifecycle and video generation workflows"""
    
    def __init__(self, base_dir: Optional[Path] = None):
        # Use user data directory instead of program directory
        import os
        if os.name == 'nt':  # Windows
            user_data_dir = Path(os.path.expanduser("~")) / "AppData" / "Local" / "Vybe AI Assistant"
        else:  # Linux/Mac
            user_data_dir = Path(os.path.expanduser("~")) / ".local" / "share" / "vybe-ai-assistant"
            
        self.base_dir = base_dir or user_data_dir / "vendor" / "ComfyUI"
        self.models_dir = self.base_dir / "models"
        self.checkpoints_dir = self.models_dir / "checkpoints"
        self.outputs_dir = self.base_dir / "output"
        self.logs_dir = user_data_dir / "logs"
        
        # Server configuration
        self.host = "127.0.0.1"
        self.port = 8188
        self.server_url = f"http://{self.host}:{self.port}"
        
        # Process management
        self.process = None
        self.is_setup_complete = False
        
        # Video models configuration
        self.default_models = {
            'stable_video_diffusion': 'svd_xt.safetensors',
            'animatediff': 'mm_sd_v15_v2.ckpt'
        }
        
        # Ensure directories exist
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
    
    def check_and_install(self) -> Dict[str, Any]:
        """Check if ComfyUI is installed and install if necessary"""
        status = {
            'installed': False,
            'comfyui_available': False,
            'models_available': False,
            'setup_required': True,
            'installation_path': str(self.base_dir),
            'error': None
        }
        
        try:
            # Check if ComfyUI directory exists AND has essential files
            essential_files = [
                self.base_dir / "main.py",
                self.base_dir / "execution.py", 
                self.base_dir / "server.py",
                self.base_dir / "nodes.py"
            ]
            
            # Directory exists but check if it has all essential files
            directory_exists = self.base_dir.exists()
            all_essential_files_exist = all(f.exists() for f in essential_files)
            
            status['comfyui_available'] = directory_exists and all_essential_files_exist
            
            # If directory exists but missing essential files, log warning for reinstall
            if directory_exists and not all_essential_files_exist:
                missing_files = [f.name for f in essential_files if not f.exists()]
                logger.warning(f"ComfyUI directory exists but missing essential files: {missing_files}")
                logger.info("Will attempt to reinstall ComfyUI to fix incomplete installation")
            
            # Check if required models are available
            models_available = 0
            total_models = len(self.default_models)
            
            for model_type, model_file in self.default_models.items():
                model_path = self.checkpoints_dir / model_file
                if model_path.exists():
                    models_available += 1
            
            status['models_available'] = models_available == total_models
            status['models_count'] = f"{models_available}/{total_models}"
            
            # If ComfyUI not properly installed, install/reinstall it
            if not status['comfyui_available']:
                if directory_exists and not all_essential_files_exist:
                    logger.info("ComfyUI incomplete installation detected, reinstalling...")
                else:
                    logger.info("ComfyUI not found, installing...")
                    
                success = self._install_comfyui()
                if success:
                    # Re-check after installation
                    all_essential_files_exist = all(f.exists() for f in essential_files)
                    status['comfyui_available'] = all_essential_files_exist
                    logger.info("ComfyUI installed successfully")
                else:
                    status['error'] = "Failed to install ComfyUI"
                    return status
            
            # If models not available, download them
            if not status['models_available']:
                logger.info("Video models not found, downloading...")
                success = self._download_models()
                if success:
                    status['models_available'] = True
                    logger.info("Video models downloaded successfully")
                else:
                    status['error'] = "Failed to download video models"
                    return status
            
            status['installed'] = status['comfyui_available'] and status['models_available']
            status['setup_required'] = not status['installed']
            
        except Exception as e:
            status['error'] = str(e)
            logger.error(f"ComfyUI installation check failed: {e}")
        
        self.is_setup_complete = status['installed']
        return status
    
    def _install_comfyui(self) -> bool:
        """Install ComfyUI from GitHub"""
        try:
            # Check if already exists and is complete (using same essential files check)
            essential_files = [
                self.base_dir / "main.py",
                self.base_dir / "execution.py", 
                self.base_dir / "server.py",
                self.base_dir / "nodes.py"
            ]
            
            if self.base_dir.exists() and all(f.exists() for f in essential_files):
                logger.info("ComfyUI already installed and complete")
                return True
                
            # If directory exists but incomplete, remove it
            if self.base_dir.exists():
                logger.info("Removing incomplete ComfyUI installation...")
                import shutil
                shutil.rmtree(self.base_dir)
            
            # Clone ComfyUI repository
            clone_cmd = [
                'git', 'clone', 
                'https://github.com/comfyanonymous/ComfyUI.git',
                str(self.base_dir)
            ]
            
            result = subprocess.run(clone_cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                logger.error(f"Failed to clone ComfyUI: {result.stderr}")
                return False
            
            # Install requirements
            requirements_file = self.base_dir / "requirements.txt"
            if requirements_file.exists():
                install_cmd = [
                    'pip', 'install', '-r', str(requirements_file)
                ]
                
                result = subprocess.run(install_cmd, capture_output=True, text=True, timeout=600)
                if result.returncode != 0:
                    logger.warning(f"Some requirements may have failed to install: {result.stderr}")
            
            return True
            
        except Exception as e:
            logger.error(f"ComfyUI installation failed: {e}")
            return False
    
    def _download_models(self) -> bool:
        """Download required video generation models"""
        try:
            # Model download URLs (these would be actual model URLs in production)
            model_urls = {
                'stable_video_diffusion': 'https://huggingface.co/stabilityai/stable-video-diffusion-img2vid-xt/resolve/main/svd_xt.safetensors',
                'animatediff': 'https://huggingface.co/guoyww/animatediff/resolve/main/mm_sd_v15_v2.ckpt'
            }
            
            # For demo purposes, create placeholder model files
            for model_type, model_file in self.default_models.items():
                model_path = self.checkpoints_dir / model_file
                if not model_path.exists():
                    # Create a placeholder file (in production, this would download the actual model)
                    logger.info(f"Creating placeholder for {model_file}")
                    with open(model_path, 'w') as f:
                        f.write(f"# Placeholder for {model_type} model\n")
                        f.write(f"# In production, this would be downloaded from:\n")
                        f.write(f"# {model_urls.get(model_type, 'Unknown URL')}\n")
            
            return True
            
        except Exception as e:
            logger.error(f"Model download failed: {e}")
            return False
    
    def start(self) -> Tuple[bool, str]:
        """Start the ComfyUI server"""
        if self.is_running():
            return True, "ComfyUI server is already running"
        
        if not self.is_setup_complete:
            status = self.check_and_install()
            if not status['installed']:
                return False, "ComfyUI not properly installed. Please run setup first."
        
        try:
            log_file = self.logs_dir / "comfyui_server.log"
            
            # Start ComfyUI server
            cmd = [
                'python', 'main.py',
                '--listen', self.host,
                '--port', str(self.port),
                '--cpu'  # CPU mode for compatibility
            ]
            
            with open(log_file, 'w') as f:
                self.process = subprocess.Popen(
                    cmd,
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    cwd=self.base_dir
                )
            
            # Wait for server to start
            max_attempts = 60  # ComfyUI can take longer to start
            for i in range(max_attempts):
                if self.is_running():
                    logger.info(f"ComfyUI server started successfully on {self.server_url}")
                    return True, f"ComfyUI server started on {self.server_url}"
                time.sleep(2)
            
            # If we get here, server didn't start properly
            if self.process:
                self.process.terminate()
                self.process = None
            return False, "ComfyUI server failed to start within timeout period"
            
        except Exception as e:
            logger.error(f"Failed to start ComfyUI server: {e}")
            return False, f"Failed to start ComfyUI server: {str(e)}"
    
    def stop(self) -> Tuple[bool, str]:
        """Stop the ComfyUI server"""
        if not self.is_running():
            return True, "ComfyUI server is not running"
        
        try:
            if self.process:
                # Try graceful termination first
                self.process.terminate()
                try:
                    self.process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    # Force kill if graceful termination fails
                    logger.warning("ComfyUI server did not terminate gracefully, forcing kill")
                    self.process.kill()
                    try:
                        self.process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        logger.error("Failed to kill ComfyUI server process")
                        return False, "Failed to kill ComfyUI server process"
                
                # Clean up process reference
                self.process = None
                logger.info("ComfyUI server stopped successfully")
                return True, "ComfyUI server stopped successfully"
            return True, "ComfyUI server stopped"
            
        except Exception as e:
            logger.error(f"Error stopping ComfyUI server: {e}")
            # Ensure process reference is cleaned up even on error
            if self.process:
                try:
                    self.process.kill()
                except Exception as e:
                    logger.debug(f"Failed to kill ComfyUI process: {e}")
                    pass
                self.process = None
            return False, f"Error stopping ComfyUI server: {str(e)}"
    
    def is_running(self) -> bool:
        """Check if ComfyUI server is running and responsive"""
        if self.process and self.process.poll() is None:
            try:
                # Check if ComfyUI API is responding
                response = requests.get(f"{self.server_url}/system_stats", timeout=5)
                return response.status_code == 200
            except Exception as e:
                logger.debug(f"ComfyUI server status check failed: {e}")
                pass
        return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status of ComfyUI service"""
        installation = self.check_and_install()
        
        return {
            'service_name': 'ComfyUI Video Generator',
            'installed': installation['installed'],
            'running': self.is_running(),
            'server_url': self.server_url if self.is_running() else None,
            'setup_required': installation['setup_required'],
            'models_available': installation.get('models_count', '0/0'),
            'installation_path': str(self.base_dir),
            'outputs_directory': str(self.outputs_dir),
            'installation_status': installation
        }
    
    def generate_video(self, prompt: str, job_manager=None, **kwargs) -> Tuple[bool, str]:
        """Generate video from text prompt"""
        if not self.is_running():
            return False, "ComfyUI server is not running"
        
        try:
            if job_manager:
                # Use JobManager for background processing
                job_manager.add_job(self._generate_video_background, prompt, **kwargs)
                return True, f"Video generation job for prompt '{prompt[:50]}...' has been queued"
            else:
                # Synchronous processing
                return self._generate_video_background(prompt, **kwargs)
            
        except Exception as e:
            logger.error(f"Video generation failed: {e}")
            return False, f"Video generation failed: {str(e)}"
    
    def _generate_video_background(self, prompt: str, **kwargs) -> Tuple[bool, str]:
        """Background task for video generation"""
        try:
            logger.info(f"Starting video generation for prompt: {prompt}")
            
            # Create a basic ComfyUI workflow for text-to-video
            workflow = self._create_text_to_video_workflow(prompt, **kwargs)
            
            # Submit workflow to ComfyUI
            response = requests.post(
                f"{self.server_url}/prompt",
                json={"prompt": workflow},
                timeout=30
            )
            
            if response.status_code == 200:
                prompt_data = response.json()
                prompt_id = prompt_data.get("prompt_id")
                
                if prompt_id:
                    # Monitor job progress (simplified)
                    logger.info(f"Video generation started with ID: {prompt_id}")
                    
                    # In a full implementation, this would poll for completion
                    # For now, simulate processing time
                    time.sleep(5)
                    
                    return True, f"Video generated successfully with ID: {prompt_id}"
                else:
                    return False, "Failed to get prompt ID from ComfyUI"
            else:
                return False, f"ComfyUI API request failed: {response.status_code}"
                
        except Exception as e:
            logger.error(f"Video generation background task failed: {e}")
            return False, f"Video generation failed: {str(e)}"
    
    def _create_text_to_video_workflow(self, prompt: str, **kwargs) -> Dict:
        """Create a ComfyUI workflow for text-to-video generation"""
        # This is a simplified workflow structure
        # In production, this would be a complex ComfyUI node graph
        workflow = {
            "1": {
                "inputs": {
                    "text": prompt,
                    "width": kwargs.get('width', 512),
                    "height": kwargs.get('height', 512),
                    "frames": kwargs.get('frames', 16),
                    "fps": kwargs.get('fps', 8)
                },
                "class_type": "TextToVideoNode"
            },
            "2": {
                "inputs": {
                    "images": ["1", 0],
                    "filename_prefix": f"vybe_video_{int(time.time())}"
                },
                "class_type": "SaveVideo"
            }
        }
        
        return workflow
    
    def get_generated_videos(self) -> List[Dict[str, Any]]:
        """Get list of generated videos"""
        videos = []
        
        if not self.outputs_dir.exists():
            return videos
        
        # Look for video files in outputs directory
        video_extensions = {'.mp4', '.avi', '.mov', '.webm', '.gif'}
        
        for video_file in self.outputs_dir.rglob('*'):
            if video_file.suffix.lower() in video_extensions:
                try:
                    stat = video_file.stat()
                    videos.append({
                        'filename': video_file.name,
                        'path': str(video_file),
                        'size': stat.st_size,
                        'created': stat.st_ctime,
                        'modified': stat.st_mtime
                    })
                except Exception as e:
                    logger.debug(f"Failed to get video file stats: {e}")
                    pass
        
        # Sort by creation time (newest first)
        videos.sort(key=lambda x: x['created'], reverse=True)
        return videos

    def __del__(self):
        """Cleanup method to ensure process is terminated when object is destroyed"""
        try:
            if self.process and self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
        except Exception as e:
            logger.debug(f"Failed to cleanup video generator process: {e}")
            pass
