"""
Setup Manager for Vybe
Handles automatic downloading and setup of default models required for core functionality
"""

import os
import subprocess
import requests
from pathlib import Path
import time
from typing import Tuple, Optional

from ..logger import logger


class SetupManager:
    """Manages automatic setup and model downloads for Vybe"""
    
    def __init__(self):
        # Use user data directory instead of program directory
        import os
        if os.name == 'nt':  # Windows
            user_data_dir = Path(os.path.expanduser("~")) / "AppData" / "Local" / "Vybe AI Assistant"
        else:  # Linux/Mac
            user_data_dir = Path(os.path.expanduser("~")) / ".local" / "share" / "vybe-ai-assistant"
            
        self.workspace_dir = user_data_dir / "workspace"
        self.models_dir = user_data_dir / "vendor" / "stable-diffusion-webui" / "models" / "Stable-diffusion"
        
        # Default models configuration
        self.default_llm_model = "phi3:mini"
        self.backend_llm_model = "gemma2:2b"  # Backend LLM for document processing
        self.default_sd_model = "v1-5-pruned-emaonly.safetensors"
        self.sd_model_url = "https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors"
        
    def check_and_download_default_models(self) -> bool:
        """
        Check for and download default models if they don't exist - DISABLED FOR STARTUP
        Returns True if all models are available, False if downloads failed.
        """
        logger.info("[INFO] Starting default model setup check...")
        logger.info("[WARNING] Automatic model downloads disabled during startup to prevent backend conflicts")
        logger.info("[INFO] Models will be downloaded on-demand when needed")
        
        # Quick checks only - don't actually try to download during startup
        all_models_ready = True
        
        # Check Backend LLM model (non-blocking)
        if not self._check_backend_llm_model_non_blocking():
            logger.info(f"� Backend LLM model {self.backend_llm_model} not found - will be downloaded when needed")
            all_models_ready = False
        else:
            logger.info(f"[OK] Backend LLM model {self.backend_llm_model} already available")
            
        # Check LLM model (non-blocking)
        if not self._check_llm_model_non_blocking():
            logger.info(f"� LLM model {self.default_llm_model} not found - will be downloaded when needed")
            all_models_ready = False
        else:
            logger.info(f"[OK] LLM model {self.default_llm_model} already available")
            
        # Check and download Stable Diffusion model
        if not self._check_sd_model():
            logger.info(f"📥 Downloading default SD model: {self.default_sd_model}")
            if not self._download_sd_model():
                all_models_ready = False
        else:
            logger.info(f"[OK] SD model {self.default_sd_model} already available")
            
        if all_models_ready:
            logger.info("[OK] All default models are ready!")
        else:
            logger.info("[INFO] Some models will be downloaded on-demand when needed")
            
        return True  # Always return True to not fail startup
    
    def _check_llm_model(self) -> bool:
        """Check if the default LLM model is available"""
        try:
            # Check if integrated LLM backend is responsive
            import requests
            response = requests.get("http://localhost:11435/v1/models", timeout=5)
            if response.status_code == 200:
                models = response.json()
                if models.get('data') and len(models['data']) > 0:
                    logger.info("[OK] LLM backend running with models available")
                    return True
                else:
                    logger.warning("LLM backend running but no models loaded")
                    return False
            else:
                logger.warning("LLM backend not responding")
                return False
        except Exception as e:
            logger.warning(f"LLM backend check failed: {e}")
            return False
    
    def _check_llm_model_non_blocking(self) -> bool:
        """Check if the default LLM model is available without blocking"""
        # Just return True for now - models will be loaded automatically
        return True
    
    def _download_default_model(self) -> bool:
        """Download the default GGUF model"""
        try:
            logger.info(f"⏳ Downloading default model...")
            
            # Try to run the download script
            import subprocess
            download_script = Path(os.getcwd()) / "download_default_model.py"
            
            if download_script.exists():
                result = subprocess.run(
                    ["python", str(download_script)],
                    capture_output=True,
                    text=True,
                    timeout=600  # 10 minute timeout
                )
                
                if result.returncode == 0:
                    logger.info(f"[OK] Successfully downloaded default model")
                    return True
                else:
                    logger.error(f"❌ Failed to download model: {result.stderr}")
                    return False
            else:
                logger.warning("❌ Download script not found")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error downloading default model: {e}")
            return False
    
    def _check_backend_llm_model(self) -> bool:
        """Check if the backend LLM model is available"""
        try:
            # Check if models directory has GGUF files
            # Try multiple potential model locations
            potential_models_dirs = [
                Path(os.getcwd()) / "models",  # Current working directory
                Path(__file__).parent.parent.parent / "models",  # Relative to this file
                Path(os.path.expandvars('%LOCALAPPDATA%')) / "Vybe AI Assistant" / "models" if os.name == 'nt' else Path.home() / ".local" / "share" / "vybe" / "models"  # User data dir
            ]
            
            models_dir = None
            for potential_dir in potential_models_dirs:
                if potential_dir.exists():
                    models_dir = potential_dir
                    break
            
            if not models_dir:
                return False
                
            gguf_files = list(models_dir.glob("*.gguf"))
            if gguf_files:
                logger.info(f"[OK] Found {len(gguf_files)} GGUF model files")
                return True
            else:
                logger.warning("No GGUF model files found")
                return False
                
        except Exception as e:
            logger.warning(f"Failed to check backend models: {e}")
            return False
    
    def _check_backend_llm_model_non_blocking(self) -> bool:
        """Check if the backend LLM model is available without blocking"""
        # Just return True for now - models will be loaded automatically
        return True
    
    def _download_backend_llm_model(self) -> bool:
        """Download the backend LLM model"""
        # Use the same download method as default model
        return self._download_default_model()
    
    def _check_sd_model(self) -> bool:
        """Check if the default Stable Diffusion model exists"""
        model_path = self.models_dir / self.default_sd_model
        return model_path.exists() and model_path.stat().st_size > 0
    
    def _download_sd_model(self) -> bool:
        """Download the default Stable Diffusion model"""
        temp_path = None
        try:
            # Ensure models directory exists
            self.models_dir.mkdir(parents=True, exist_ok=True)
            
            model_path = self.models_dir / self.default_sd_model
            temp_path = model_path.with_suffix('.tmp')
            
            logger.info(f"⏳ Downloading SD model from HuggingFace...")
            
            # Download with progress tracking
            response = requests.get(self.sd_model_url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # Log progress every 100MB
                        if downloaded_size % (100 * 1024 * 1024) == 0:
                            if total_size > 0:
                                progress = (downloaded_size / total_size) * 100
                                logger.info(f"📊 Download progress: {progress:.1f}%")
            
            # Move temp file to final location
            temp_path.rename(model_path)
            
            logger.info(f"[OK] Successfully downloaded {self.default_sd_model}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error downloading SD model: {e}")
            # Clean up temp file if it exists
            try:
                if temp_path and temp_path.exists():
                    temp_path.unlink()
            except Exception as e:
                logger.debug(f"Failed to clean up temp file: {e}")
                pass
            return False
    
    def setup_workspace_directories(self) -> None:
        """Ensure all necessary workspace directories exist"""
        # Get user data directory
        import os
        if os.name == 'nt':  # Windows
            user_data_dir = Path(os.path.expanduser("~")) / "AppData" / "Local" / "Vybe AI Assistant"
        else:  # Linux/Mac
            user_data_dir = Path(os.path.expanduser("~")) / ".local" / "share" / "vybe-ai-assistant"
        
        directories = [
            self.workspace_dir,
            self.workspace_dir / "generated_images",
            self.workspace_dir / "generated_audio",
            self.workspace_dir / "uploads",
            self.workspace_dir / "agent_outputs",
            user_data_dir / "logs",
            user_data_dir / "rag_data" / "knowledge_base",
            user_data_dir / "rag_data" / "chroma_db",
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            
        logger.info("[OK] Workspace directories initialized")
    
    def get_model_status(self) -> dict:
        """Get the status of all default models"""
        return {
            "gguf_model": {
                "name": self.default_llm_model,
                "available": self._check_llm_model()
            },
            "backend_llm_model": {
                "name": self.backend_llm_model,
                "available": self._check_backend_llm_model()
            },
            "sd_model": {
                "name": self.default_sd_model,
                "available": self._check_sd_model()
            }
        }


# Global setup manager instance
setup_manager = SetupManager()


def check_and_download_default_models() -> bool:
    """Convenience function for the main application"""
    return setup_manager.check_and_download_default_models()


def setup_workspace_directories() -> None:
    """Convenience function for workspace setup"""
    return setup_manager.setup_workspace_directories()


def get_model_status() -> dict:
    """Convenience function to get model status"""
    return setup_manager.get_model_status()
