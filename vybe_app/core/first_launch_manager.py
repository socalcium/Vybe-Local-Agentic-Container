"""
First Launch Manager for Vybe
Handles initial setup, model downloads, and readiness checks
"""
import os
import time
import requests
import logging
from pathlib import Path
from typing import Optional, Callable
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class FirstLaunchManager:
    """Manages the first launch experience including model downloads"""
    
    def __init__(self):
        self.app_root = Path(__file__).parent.parent.parent
        self.models_dir = self.app_root / "models"
        self.models_dir.mkdir(exist_ok=True)
        
        # Hardware-aware model selection - will be determined dynamically
        self.selected_model = None
        self.hardware_profile = None
        
        # Default model to download if none exists: must meet hard min context (>=32k)
        self.default_model = {
            'name': 'qwen2-7b-instruct-q4_k_m.gguf',
            'url': 'https://huggingface.co/Qwen/Qwen2-7B-Instruct-GGUF/resolve/main/qwen2-7b-instruct-q4_k_m.gguf',
            'size': 4_400_000_000  # ~4.4GB
        }
        
        # Progress callback for UI updates
        self.progress_callback: Optional[Callable] = None
        self.progress_log = []  # list of dicts: {message, percentage, ts}
        self.is_downloading: bool = False
    
    def set_progress_callback(self, callback: Callable[[str, float], None]):
        """Set callback for progress updates (message, percentage)"""
        self.progress_callback = callback
    
    def _notify_progress(self, message: str, percentage: float = 0.0):
        """Send progress update to UI"""
        if self.progress_callback:
            self.progress_callback(message, percentage)
        logger.info(f"First Launch: {message} ({percentage:.1f}%)")
        try:
            from datetime import datetime
            self.progress_log.append({'message': message, 'percentage': float(percentage), 'ts': datetime.now().isoformat()})
            # Keep only the last 200 entries to bound memory
            if len(self.progress_log) > 200:
                self.progress_log = self.progress_log[-200:]
        except Exception:
            pass

    def get_progress(self):
        """Return current download/setup progress and state"""
        last = self.progress_log[-1] if self.progress_log else None
        pct = last.get('percentage', 0.0) if last else 0.0
        return {
            'in_progress': self.is_downloading,
            'last_message': last.get('message') if last else None,
            'percentage': pct,
            'updates': self.progress_log,
        }
    
    def check_models_available(self) -> bool:
        """Check if any GGUF models are available"""
        gguf_files = list(self.models_dir.glob("*.gguf"))
        return len(gguf_files) > 0
    
    def analyze_hardware_and_select_model(self) -> bool:
        """Analyze hardware and select the best model for this system"""
        try:
            from .hardware_manager import HardwareManager
            from .model_sources_manager import get_model_sources_manager
            
            self._notify_progress("Analyzing system hardware...", 10.0)
            
            # Get hardware profile
            hw_manager = HardwareManager()
            hardware_info = hw_manager.detect_hardware()
            
            # Extract relevant info for model selection
            self.hardware_profile = {
                'total_ram_gb': hardware_info['memory']['total_gb'],
                'cpu_cores': hardware_info['cpu']['count'],
                'gpu_name': hardware_info['gpu'].get('name', '').lower(),
                'vram_gb': hardware_info['gpu'].get('memory_gb', 0)
            }
            
            self._notify_progress("Selecting optimal model for your hardware...", 20.0)
            
            # Get model sources manager
            sources_manager = get_model_sources_manager()
            
            # Determine hardware tier
            gpu_name = self.hardware_profile.get('gpu_name', '').lower()
            ram_gb = self.hardware_profile.get('total_ram_gb', 16)
            vram_gb = self.hardware_profile.get('vram_gb', 0)
            
            # Select model based on hardware tier
            if vram_gb >= 20 and ram_gb >= 64:  # RTX 4080/4090 class
                tier = 'enthusiast'
                model_name = 'mixtral-uncensored-8x7b'
            elif vram_gb >= 12 and ram_gb >= 32:  # RTX 3080/4070 class  
                tier = 'high_end'
                model_name = 'llama3-uncensored-8b-128k'
            elif vram_gb >= 8 and ram_gb >= 16:  # GTX 1080/RTX 3070 class
                tier = 'performance'
                model_name = 'hermes-2-pro-llama3-8b'
            elif vram_gb >= 6 and ram_gb >= 16:  # GTX 1060 6GB/RTX 2060 class
                tier = 'mainstream'
                model_name = 'dolphin-mistral-7b'
            else:  # Entry level
                tier = 'entry'
                model_name = 'qwen2-7b-instruct'
            
            # Get the selected model info with hard minimum context
            try:
                from ..config import Config
                hard_min_ctx = int(getattr(Config, 'REQUIRED_MIN_CONTEXT_TOKENS', 32768))
            except Exception:
                hard_min_ctx = 32768
            available_models = sources_manager.get_available_models(min_context=hard_min_ctx)
            selected_model_info = None
            
            for model in available_models:
                if model_name in model['name']:
                    selected_model_info = model
                    break
            
            if not selected_model_info:
                # Fallback to first available model
                selected_model_info = available_models[0] if available_models else None
            
            if selected_model_info:
                self.selected_model = {
                    'name': selected_model_info['filename'],
                    'url': selected_model_info['download_url'],
                    'size': selected_model_info['size_mb'] * 1024 * 1024,
                    'context': selected_model_info['context'],
                    'description': selected_model_info['description'],
                    'tier': tier
                }
                
                logger.info(f"Selected model: {selected_model_info['name']} for {tier} hardware")
                return True
            else:
                logger.error("No suitable models found")
                return False
                
        except Exception as e:
            logger.error(f"Failed to analyze hardware and select model: {e}")
            return False
    
    def download_selected_model(self) -> bool:
        """Download the hardware-selected model with detailed progress"""
        if not self.selected_model:
            logger.error("No model selected for download")
            return False
        
        try:
            model_name = self.selected_model['name']
            download_url = self.selected_model['url']
            model_size = self.selected_model['size']
            local_path = self.models_dir / model_name
            
            if local_path.exists():
                self._notify_progress(f"Model {model_name} already exists", 100.0)
                return True
            
            self.is_downloading = True
            self._notify_progress(f"Downloading {model_name} ({model_size / 1024 / 1024:.1f} MB)...", 30.0)
            logger.info(f"Downloading {model_name} from {download_url}")
            
            # Download with progress tracking
            response = requests.get(download_url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', model_size))
            downloaded = 0
            
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Update progress (30% to 90% for download)
                        if total_size > 0:
                            download_progress = (downloaded / total_size) * 60  # 60% of total progress
                            total_progress = 30 + download_progress
                            self._notify_progress(
                                f"Downloading {model_name}: {downloaded / 1024 / 1024:.1f} MB / {total_size / 1024 / 1024:.1f} MB",
                                total_progress
                            )
            
            self._notify_progress(f"Successfully downloaded {model_name}", 95.0)
            logger.info(f"Successfully downloaded {model_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download model: {e}")
            # Clean up partial download
            if local_path.exists():
                local_path.unlink()
            return False
        finally:
            self.is_downloading = False
    
    def get_available_models(self) -> list:
        """Get list of available model files"""
        models = []
        for gguf_file in self.models_dir.glob("*.gguf"):
            models.append({
                'name': gguf_file.stem,
                'path': str(gguf_file),
                'size': gguf_file.stat().st_size
            })
        return models
    


    def download_model(self, model_info: Optional[dict] = None) -> bool:
        """Download a model with progress tracking"""
        if model_info is None:
            model_info = self.default_model
        
        model_path = self.models_dir / model_info['name']
        
        # Skip if model already exists
        if model_path.exists():
            self._notify_progress(f"Model {model_info['name']} already available", 100.0)
            return True
        
        self.is_downloading = True
        self._notify_progress("Starting model download...", 0.0)
        
        try:
            response = requests.get(model_info['url'], stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', model_info['size']))
            downloaded = 0
            
            with open(model_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Update progress every MB
                        if downloaded % (1024 * 1024) == 0:
                            percentage = (downloaded / total_size) * 100
                            mb_downloaded = downloaded / (1024 * 1024)
                            mb_total = total_size / (1024 * 1024)
                            self._notify_progress(
                                f"Downloading {model_info['name']}: {mb_downloaded:.1f}/{mb_total:.1f}MB", 
                                percentage
                            )
            
            self._notify_progress(f"Model {model_info['name']} downloaded successfully!", 100.0)
            return True
            
        except Exception as e:
            logger.error(f"Failed to download model: {e}")
            self._notify_progress(f"Download failed: {str(e)}", 0.0)
            
            # Clean up partial download
            if model_path.exists():
                model_path.unlink()
            
            return False
        finally:
            self.is_downloading = False
    
    def check_llama_cpp_available(self) -> bool:
        """Check if llama-cpp-python is available"""
        try:
            import llama_cpp
            return True
        except ImportError:
            return False
    
    def install_essential_features(self) -> bool:
        """Install essential features like audio dependencies"""
        try:
            import subprocess
            import sys
            
            self._notify_progress("Installing essential audio features...", 45.0)
            
            # Install TTS dependencies if not available - Use pyttsx3 (more reliable)
            try:
                import pyttsx3
            except ImportError:
                self._notify_progress("Installing Text-to-Speech engine...", 46.0)
                subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyttsx3'], 
                             capture_output=True, check=True)
            
            # Install audio processing dependencies
            try:
                import speech_recognition
            except ImportError:
                self._notify_progress("Installing speech recognition...", 48.0)
                subprocess.run([sys.executable, '-m', 'pip', 'install', 'SpeechRecognition'], 
                             capture_output=True, check=True)
                
            self._notify_progress("Essential features installed!", 50.0)
            return True
            
        except Exception as e:
            logger.error(f"Failed to install essential features: {e}")
            self._notify_progress("Warning: Some features may be limited", 50.0)
            return False
    
    def run_first_launch_sequence(self) -> bool:
        """Run the complete first launch sequence"""
        self._notify_progress("Checking system readiness...", 10.0)
        
        # Check if llama-cpp-python is available
        if not self.check_llama_cpp_available():
            self._notify_progress("Installing AI backend (this may take a few minutes)...", 20.0)
            # The package should already be installed by now
            time.sleep(2)  # Give some time for any background installation
        
        self._notify_progress("Checking for AI models (32k+ context required)...", 30.0)
        
        # Check if models are available
        if not self.check_models_available():
            self._notify_progress("No suitable AI models found. Downloading Qwen2 7B (32k ctx)...", 40.0)
            
            if not self.download_model():
                self._notify_progress("Model download failed. Please check internet connection.", 0.0)
                return False
        else:
            self._notify_progress("AI models found!", 40.0)
        
        # Install essential features
        self.install_essential_features()
        
        # Initialize auto-installer for AI tools
        self._notify_progress("Setting up AI tools auto-installer...", 60.0)
        try:
            from ..api.auto_installer_api import install_manager
            install_manager.refresh_status()
            self._notify_progress("AI tools installer ready!", 65.0)
        except Exception as e:
            logger.error(f"Auto-installer setup failed: {e}")
            self._notify_progress("Warning: Auto-installer may be limited", 65.0)
        
        self._notify_progress("Initializing AI backend...", 80.0)
        time.sleep(1)  # Give backend time to initialize
        
        self._notify_progress("System ready!", 90.0)
        time.sleep(1)
        
        self._notify_progress("Welcome to Vybe AI!", 100.0)
        time.sleep(1)  # Show welcome message
        
        return True
    
    def create_first_launch_flag(self):
        """Create flag file to indicate first launch is complete"""
        flag_file = self.app_root / "instance" / "first_launch_complete.flag"
        flag_file.parent.mkdir(exist_ok=True)
        flag_file.write_text(f"First launch completed at {time.ctime()}")
    
    def is_first_launch_complete(self) -> bool:
        """Check if first launch has been completed"""
        flag_file = self.app_root / "instance" / "first_launch_complete.flag"
        return flag_file.exists()

# Global instance
first_launch_manager = FirstLaunchManager()
