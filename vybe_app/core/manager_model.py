"""
Manager Model for Vybe - The Orchestrator LLM
This module implements the core "brain" of Vybe - a small, fast, always-on orchestrator
that analyzes user intent, manages resources, and delegates to specialized models.
"""

import json
import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime

from ..core.backend_llm_controller import get_backend_controller
from ..core.system_monitor import SystemMonitor
from ..core.context_optimizer import get_context_optimizer
from ..utils.llm_model_manager import LLMModelManager
from ..models import db, AppSetting

# Import app for Flask application context
try:
    from .. import app
    APP_AVAILABLE = True
except ImportError:
    APP_AVAILABLE = False
    print("Warning: Flask app not available for manager model")

logger = logging.getLogger(__name__)


class ManagerModel:
    """
    The Manager Model is the central orchestrator of the Vybe system.
    It uses a selected LLM to analyze user intent, coordinate responses,
    manage system resources, and personalize user experience.
    """
    
    def __init__(self):
        """Initialize the Manager Model with lazy loading to avoid state dependencies"""
        # Use lazy initialization to prevent cross-module state dependencies
        self._backend_controller = None
        self._model_manager = None
        self._system_monitor = None
        self._context_optimizer = None
        
        # Initialize basic state
        self.conversation_context = []
        self.active_agents = {}
        self.user_preferences = {}
        self.session_data = {}
        
        # Lazy-loaded properties
        self._config = None
        self._user_profile = None
        self._pc_profile = None
        self._orchestrator_model = None
        self._orchestrator_prompt = None
        
        logger.info("Manager Model initialized with lazy loading pattern")
    
    def ensure_initialized(self):
        """Ensure all components are initialized - call this when manager is first used"""
        # Trigger lazy loading of all components
        _ = self.config
        _ = self.user_profile
        _ = self.pc_profile
        _ = self.orchestrator_model
        _ = self.orchestrator_prompt
        
        # Run requirements check
        self._check_and_install_requirements()
        
        logger.info(f"Manager Model fully initialized with orchestrator: {self.orchestrator_model['name']}")
        logger.info(f"PC Profile: {self.pc_profile['hardware_tier']} tier, {self.pc_profile['gpu_available']} GPU")
    
    @property
    def backend_controller(self):
        """Lazy-loaded backend controller"""
        if self._backend_controller is None:
            self._backend_controller = get_backend_controller()
        return self._backend_controller
    
    @property
    def model_manager(self):
        """Lazy-loaded model manager"""
        if self._model_manager is None:
            self._model_manager = LLMModelManager()
        return self._model_manager
    
    @property
    def system_monitor(self):
        """Lazy-loaded system monitor"""
        if self._system_monitor is None:
            self._system_monitor = SystemMonitor()
        return self._system_monitor
    
    @property
    def context_optimizer(self):
        """Lazy-loaded context optimizer"""
        if self._context_optimizer is None:
            self._context_optimizer = get_context_optimizer()
        return self._context_optimizer
    
    @property
    def config(self):
        """Lazy-loaded configuration"""
        if self._config is None:
            self._config = self._load_config()
        return self._config
    
    @property
    def user_profile(self):
        """Lazy-loaded user profile"""
        if self._user_profile is None:
            self._user_profile = self._load_user_profile()
        return self._user_profile
    
    @property
    def pc_profile(self):
        """Lazy-loaded PC profile"""
        if self._pc_profile is None:
            self._pc_profile = self._analyze_pc_capabilities()
        return self._pc_profile
    
    @property
    def orchestrator_model(self):
        """Lazy-loaded orchestrator model"""
        if self._orchestrator_model is None:
            self._orchestrator_model = self._get_orchestrator_model()
        return self._orchestrator_model
    
    @property
    def orchestrator_prompt(self):
        """Lazy-loaded orchestrator prompt"""
        if self._orchestrator_prompt is None:
            self._orchestrator_prompt = self._create_orchestrator_prompt()
        return self._orchestrator_prompt
    
    def _load_config(self) -> Dict[str, Any]:
        """Load Manager Model configuration from database"""
        config = {
            'selected_orchestrator': 'auto',  # Auto-select best available model or download on first use
            'max_context_length': 32768,  # 32K context for advanced AI assistant capabilities
            'orchestrator_temperature': 0.3,
            'delegation_threshold': 0.7,
            'auto_install_requirements': True,
            'personalization_enabled': True,
            'hardware_optimization': True,
            'preferred_models': {},
            'user_rag_enabled': True
        }
        
        # Load from database if available
        try:
            if not APP_AVAILABLE:
                logger.warning("Flask app not available - using default config for manager model")
                return config
                
            with app.app_context():
                settings = AppSetting.query.filter(AppSetting.key.like('manager_model_%')).all()
                for setting in settings:
                    key = setting.key.replace('manager_model_', '')
                    if setting.value:
                        try:
                            config[key] = json.loads(setting.value)
                        except Exception as e:
                            logger.warning(f"Failed to parse JSON config for {key}: {e}")
                            config[key] = setting.value
        except Exception as e:
            logger.warning(f"Could not load Manager Model config from database: {e}")
        
        return config

    def _load_user_profile(self) -> Dict[str, Any]:
        """Load or create user profile for personalization"""
        profile = {
            'usage_patterns': {},
            'preferred_tasks': [],
            'skill_level': 'intermediate',
            'interaction_style': 'balanced',
            'favorite_models': {},
            'custom_workflows': [],
            'session_count': 0,
            'total_interactions': 0,
            'last_active': None
        }
        
        try:
            if not APP_AVAILABLE:
                logger.warning("Flask app not available - using default user profile")
                return profile
                
            with app.app_context():
                setting = AppSetting.query.filter_by(key='user_profile').first()
                if setting and setting.value:
                    stored_profile = json.loads(setting.value)
                    profile.update(stored_profile)
        except Exception as e:
            logger.warning(f"Could not load user profile: {e}")
        
        return profile

    def _analyze_pc_capabilities(self) -> Dict[str, Any]:
        """Analyze PC hardware capabilities for model selection"""
        try:
            import psutil
            import platform
            
            # Get system information
            cpu_count = psutil.cpu_count(logical=True) or 4  # Default to 4 cores if None
            cpu_freq = psutil.cpu_freq()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Estimate GPU availability
            gpu_available = self._detect_gpu()
            
            # Calculate hardware tier
            hardware_tier = self._calculate_hardware_tier(cpu_count, memory.total, gpu_available)
            
            profile = {
                'cpu_cores': cpu_count,
                'cpu_frequency': cpu_freq.max if cpu_freq else 0,
                'total_ram_gb': round(memory.total / (1024**3), 1),
                'available_ram_gb': round(memory.available / (1024**3), 1),
                'disk_space_gb': round(disk.total / (1024**3), 1),
                'disk_free_gb': round(disk.free / (1024**3), 1),
                'platform': platform.system(),
                'platform_version': platform.release(),
                'python_version': platform.python_version(),
                'gpu_available': gpu_available,
                'hardware_tier': hardware_tier,
                'recommended_models': self._get_recommended_models_for_tier(hardware_tier),
                'max_concurrent_models': self._estimate_concurrent_models(memory.total, gpu_available)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing PC capabilities: {e}")
            profile = {
                'hardware_tier': 'unknown',
                'gpu_available': 'unknown',
                'recommended_models': ['phi3:mini', 'tinyllama:1.1b'],
                'max_concurrent_models': 1
            }
        
        return profile

    def _detect_gpu(self) -> str:
        """Detect available GPU with enhanced error handling"""
        try:
            # Try to detect NVIDIA GPU
            import subprocess
            result = subprocess.run(['nvidia-smi'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return 'nvidia'
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.debug(f"NVIDIA GPU detection failed: {e}")
        except Exception as e:
            logger.warning(f"Unexpected error in NVIDIA GPU detection: {e}")
        
        try:
            # Try to detect AMD GPU (basic check)
            import platform
            if platform.system() == 'Windows':
                result = subprocess.run(['wmic', 'path', 'win32_VideoController', 'get', 'name'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0 and ('amd' in result.stdout.lower() or 'radeon' in result.stdout.lower()):
                    return 'amd'
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.debug(f"AMD GPU detection failed: {e}")
        except Exception as e:
            logger.warning(f"Unexpected error in AMD GPU detection: {e}")
        
        return 'none'

    def _calculate_hardware_tier(self, cpu_cores: int, total_ram: int, gpu: str) -> str:
        """Calculate hardware tier based on GPU VRAM and system specs"""
        ram_gb = total_ram / (1024**3)
        
        # Try to get GPU VRAM information for more accurate tiering
        gpu_vram_gb = self._detect_gpu_vram()
        
        # Define tier thresholds based on GPU VRAM capacity for backend + frontend models
        if gpu_vram_gb and gpu_vram_gb >= 24:
            return 'tier_4_24gb_plus'  # RTX 4090, RTX 3090 Ti, Professional GPUs
        elif gpu_vram_gb and gpu_vram_gb >= 16:
            return 'tier_3_16gb'       # RTX 4070 Ti, RTX 3090, RTX 4080
        elif gpu_vram_gb and gpu_vram_gb >= 10:
            return 'tier_2_10gb'       # RTX 3080 10GB, RTX 4060 Ti 16GB
        elif gpu_vram_gb and gpu_vram_gb >= 8:
            return 'tier_1_8gb'        # GTX 1070, RTX 3060 8GB, RTX 4060
        elif gpu in ['nvidia', 'amd'] and ram_gb >= 32 and cpu_cores >= 12:
            return 'high_end_no_vram'  # High-end system but VRAM unknown
        elif gpu in ['nvidia', 'amd'] and ram_gb >= 16 and cpu_cores >= 8:
            return 'mid_range_gpu'     # Gaming PC with GPU but VRAM unknown
        elif ram_gb >= 16 and cpu_cores >= 6:
            return 'mid_range_cpu'     # Modern system, CPU-only inference
        elif ram_gb >= 8 and cpu_cores >= 4:
            return 'budget_cpu'        # Basic modern PC, CPU-only
        else:
            return 'mobile'            # Phone/tablet tier

    def _detect_gpu_vram(self) -> Optional[float]:
        """Detect GPU VRAM in GB for more accurate tier calculation"""
        try:
            # Try to get VRAM info from hardware safety module
            try:
                from .hardware_safety import HardwareSafetyMonitor
                safety_monitor = HardwareSafetyMonitor()
                if safety_monitor.specs and safety_monitor.specs.gpu_memory_gb:
                    return safety_monitor.specs.gpu_memory_gb
            except (ImportError, AttributeError) as e:
                logger.debug(f"Could not import HardwareSafetyManager: {e}")
        except Exception as e:
            logger.debug(f"Could not get VRAM from hardware safety: {e}")
        
        # Fallback: try nvidia-ml-py if available
        try:
            try:
                import pynvml
                pynvml.nvmlInit()
                device_count = pynvml.nvmlDeviceGetCount()
                if device_count > 0:
                    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                    mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    if hasattr(mem_info, 'total') and isinstance(mem_info.total, (int, float)):
                        return float(mem_info.total) / (1024**3)  # Convert to GB
            except ImportError:
                logger.debug("pynvml not available for VRAM detection")
        except Exception as e:
            logger.debug(f"Could not detect VRAM via pynvml: {e}")
        
        return None

    def _get_recommended_models_for_tier(self, tier: str) -> List[str]:
        """Get recommended backend orchestrator models for hardware tier"""
        model_tiers = {
            # VRAM-based tiers for optimal backend + frontend concurrency
            'tier_1_8gb': ['dolphin-2.6-phi-2-2.7b'],  # 2.5GB backend, 5.5GB for 7B Q4 frontend
            'tier_2_10gb': ['dolphin-2.8-mistral-7b-v02'],  # 3.5GB backend, 6.5GB for frontend + SD
            'tier_3_16gb': ['hermes-2-pro-llama-3-8b'],  # 4.5GB backend, 11.5GB for large frontend
            'tier_4_24gb_plus': ['dolphin-2.9-llama3-70b'],  # 8GB backend, 16GB+ for massive frontend
            
            # Fallback tiers for systems without VRAM detection
            'high_end_no_vram': ['hermes-2-pro-llama-3-8b', 'dolphin-2.8-mistral-7b-v02'],
            'mid_range_gpu': ['dolphin-2.8-mistral-7b-v02', 'dolphin-2.6-phi-2-2.7b'],
            'mid_range_cpu': ['phi3:mini'],  # CPU-only inference
            'budget_cpu': ['tinyllama:1.1b'],  # Very basic CPU inference
            'mobile': ['tinyllama:1.1b']
        }
        
        return model_tiers.get(tier, ['dolphin-2.6-phi-2-2.7b'])  # Default to most compatible

    def _estimate_concurrent_models(self, total_ram: int, gpu: str) -> int:
        """Estimate how many models can run concurrently"""
        ram_gb = total_ram / (1024**3)
        
        if gpu in ['nvidia', 'amd'] and ram_gb >= 32:
            return 3  # Can run orchestrator + 2 specialized models
        elif ram_gb >= 16:
            return 2  # Can run orchestrator + 1 specialized model  
        else:
            return 1  # Only orchestrator

    def get_available_orchestrator_models(self) -> List[Dict[str, Any]]:
        """Get list of available backend orchestrator models optimized for concurrent operation
        
        Three tiers designed to run efficiently as backend while leaving VRAM for frontend chat models:
        - Tier 1 (8GB GPU): Backend model + 7B Q4 frontend chat
        - Tier 2 (10GB GPU): Backend model + 7B Q4 frontend chat + light image generation
        - Tier 3 (16GB GPU): Backend model + larger frontend models + full multimodal pipeline
        """
        models = [
            # Tier 1: 8GB GPU (GTX 1070 / RTX 3060 8GB)
            {
                'name': 'dolphin-2.6-phi-2-2.7b',
                'display_name': 'Tier 1: Dolphin Phi-2 2.7B Backend (8GB GPU Compatible)',
                'tier': 1,
                'backend_vram_usage': '2.5GB',
                'remaining_vram': '5.5GB',
                'ram_requirement': '16GB System + 8GB VRAM',
                'gpu_requirement': 'GTX 1070 / RTX 3060 8GB',
                'description': 'Efficient uncensored 2.7B backend orchestrator, leaves 5.5GB VRAM for 7B Q4 frontend chat',
                'uncensored': True,
                'n_ctx': 32768,
                'concurrent_capacity': 'Frontend: 7B Q4 model (4.5GB) + small tasks',
                'capabilities': ['backend_orchestration', 'task_routing', 'uncensored_coordination'],
                'recommended_for': ['8GB_gpu', 'budget_ai_enthusiast'],
                'predownload': True,
                'repo': 'cognitivecomputations/dolphin-2.6-phi-2-gguf',
                'filename': 'dolphin-2.6-phi-2.Q4_K_M.gguf',
                'size_mb': 1600
            },
            # Tier 2: 10GB GPU (RTX 3080 10GB / RTX 4060 Ti 16GB on conservative settings)
            {
                'name': 'dolphin-2.8-mistral-7b-v02',
                'display_name': 'Tier 2: Dolphin Mistral 7B Backend (10GB GPU Optimized)',
                'tier': 2,
                'backend_vram_usage': '3.5GB',
                'remaining_vram': '6.5GB',
                'ram_requirement': '16GB System + 10GB VRAM',
                'gpu_requirement': 'RTX 3080 10GB / RTX 4060 Ti',
                'description': 'Uncensored 7B backend with Q4 quantization, leaves 6.5GB for frontend models + light image gen',
                'uncensored': True,
                'n_ctx': 32768,
                'concurrent_capacity': 'Frontend: 7B Q4 model (4.5GB) + SD 1.5 (2GB) OR 13B Q2 model',
                'capabilities': ['advanced_orchestration', 'uncensored_coordination', 'multi_modal_support'],
                'recommended_for': ['10GB_gpu', 'mainstream_ai_user'],
                'predownload': True,
                'repo': 'cognitivecomputations/dolphin-2.8-mistral-7b-v02-gguf',
                'filename': 'dolphin-2.8-mistral-7b-v02.Q4_K_M.gguf',
                'size_mb': 4100
            },
            # Tier 3: 16GB GPU (RTX 4070 Ti / RTX 3090 / RTX 4080)
            {
                'name': 'hermes-2-pro-llama-3-8b',
                'display_name': 'Tier 3: Hermes 2 Pro Llama3 8B Backend (16GB GPU Performance)',
                'tier': 3,
                'backend_vram_usage': '4.5GB',
                'remaining_vram': '11.5GB',
                'ram_requirement': '32GB System + 16GB VRAM',
                'gpu_requirement': 'RTX 4070 Ti / RTX 3090 / RTX 4080',
                'description': 'Professional uncensored 8B backend, leaves 11.5GB for large frontend models + full multimodal',
                'uncensored': True,
                'n_ctx': 32768,
                'concurrent_capacity': 'Frontend: 13B Q4 model (7GB) + SD XL (3GB) + TTS (1GB) + transcription',
                'capabilities': ['professional_orchestration', 'uncensored_coordination', 'advanced_reasoning', 'full_multimodal'],
                'recommended_for': ['16GB_gpu', 'ai_enthusiast', 'content_creator'],
                'predownload': True,
                'repo': 'NousResearch/Hermes-2-Pro-Llama-3-8B-GGUF',
                'filename': 'Hermes-2-Pro-Llama-3-8B.Q4_K_M.gguf',
                'size_mb': 4800
            },
            # Bonus Tier: 24GB+ GPU (RTX 4090 / RTX 3090 Ti)
            {
                'name': 'dolphin-2.9-llama3-70b',
                'display_name': 'Bonus: Dolphin Llama3 70B Backend (24GB+ GPU)',
                'tier': 4,
                'backend_vram_usage': '8GB',
                'remaining_vram': '16GB+',
                'ram_requirement': '64GB System + 24GB VRAM',
                'gpu_requirement': 'RTX 4090 / RTX 3090 Ti / Professional GPU',
                'description': 'Flagship uncensored 70B backend with extreme Q2 quantization for maximum intelligence',
                'uncensored': True,
                'n_ctx': 32768,
                'concurrent_capacity': 'Frontend: 20B+ models + SD XL + video processing + real-time everything',
                'capabilities': ['maximum_intelligence', 'research_grade', 'uncensored_expertise', 'enterprise_coordination'],
                'recommended_for': ['24GB_gpu', 'ai_researcher', 'professional_workstation'],
                'predownload': False,
                'repo': 'cognitivecomputations/dolphin-2.9-llama3-70b-gguf',
                'filename': 'dolphin-2.9-llama3-70b.Q2_K.gguf',
                'size_mb': 28000
            }
        ]
        
        return models

    def _get_orchestrator_model(self) -> Dict[str, Any]:
        """Get the currently selected orchestrator model"""
        selected_name = self.config.get('selected_orchestrator', 'auto')
        available_models = self.get_available_orchestrator_models()
        
        # If auto-select, choose based on hardware tier with better fallbacks
        if selected_name == 'auto':
            hardware_tier = self.pc_profile.get('hardware_tier', 'entry_level')
            # Select appropriate tier model with verified availability
            if hardware_tier == 'high_end':
                selected_name = 'hermes-2-pro-llama3-8b'
            elif hardware_tier in ['mid_range', 'mainstream']:
                selected_name = 'dolphin-mistral-7b'
            else:
                selected_name = 'qwen2-7b-instruct'
        
        # Check if selected model exists in available models
        for model in available_models:
            if model['name'] == selected_name:
                logger.info(f"Selected orchestrator model: {model['name']} ({model['display_name']})")
                return model
        
        # Model not found - log warning and try fallbacks
        logger.warning(f"Selected orchestrator model {selected_name} not available - trying fallbacks")
        
        # Fallback to first recommended model for this tier
        hardware_tier = self.pc_profile.get('hardware_tier', 'entry_level')
        recommended = self._get_recommended_models_for_tier(hardware_tier)
        logger.info(f"Trying fallback models for {hardware_tier}: {recommended}")
        
        for model in available_models:
            if model['name'] in recommended:
                logger.info(f"Using fallback orchestrator model: {model['name']}")
                return model
        
        # Try any available model from the list (prefer entry-level models)
        for model in sorted(available_models, key=lambda x: x.get('tier', 999)):
            if model.get('predownload', False):  # Prefer predownload models
                logger.info(f"Using available predownload model: {model['name']}")
                return model
        
        # If no predownload models, use the first available
        if available_models:
            model = available_models[0]
            logger.info(f"Using first available model: {model['name']}")
            return model
        
        # Ultimate fallback - return a placeholder model
        logger.warning("No orchestrator models available - using placeholder")
        return {
            'name': 'qwen2-7b-instruct',  # Use the actual default model from first launch manager
            'display_name': 'Qwen2 7B Instruct (Will be downloaded)',
            'description': 'Default 32K context model - will download automatically on first use',
            'tier': 1,
            'n_ctx': 32768,
            'uncensored': False,
            'predownload': True
        }

    def _check_and_install_requirements(self):
        """Auto-check and install all required features"""
        if not self.config.get('auto_install_requirements', True):
            return
        
        logger.info("Checking system requirements...")
        
        try:
            # Check image generation requirements
            self._check_image_generation_requirements()
            
            # Check video generation requirements
            self._check_video_generation_requirements()
            
            # Check audio requirements
            self._check_audio_requirements()
            
            # Check model availability
            self._check_llm_model_availability()
            
        except Exception as e:
            logger.error(f"Error checking requirements: {e}")

    def _check_image_generation_requirements(self):
        """Check and setup image generation requirements"""
        try:
            # Non-blocking: only detect presence; defer install/download to explicit user action
            from ..core.stable_diffusion_controller import StableDiffusionController
            sd_controller = StableDiffusionController()
            has_install = sd_controller.sd_dir.exists() and ((sd_controller.sd_dir / 'webui.py').exists() or (sd_controller.sd_dir / 'webui.bat').exists())
            if not has_install:
                logger.info("Stable Diffusion not installed yet (will install on first user start)")
                return
            logger.info("Stable Diffusion detected")
                
        except Exception as e:
            logger.warning(f"Image generation check failed: {e}")

    def _check_video_generation_requirements(self):
        """Check and setup video generation requirements"""
        try:
            # Non-blocking: only detect presence; defer install/download to explicit user action
            from ..core.video_generator import VideoGeneratorController
            video_controller = VideoGeneratorController()
            main_py = video_controller.base_dir / 'main.py'
            if not main_py.exists():
                logger.info("ComfyUI not installed yet (will install on first user start)")
                return
            logger.info("ComfyUI detected")
                
        except Exception as e:
            logger.warning(f"Video generation check failed: {e}")

    def _check_audio_requirements(self):
        """Check and setup audio requirements"""
        try:
            # Check TTS - Use pyttsx3 (more reliable, offline)
            import pyttsx3
            
            # Check speech recognition
            import speech_recognition as sr
            
            logger.info("Audio requirements satisfied")
            
        except ImportError as e:
            logger.warning(f"Audio requirements missing: {e}")
            # Try to install pyttsx3 as fallback
            try:
                import subprocess
                import sys
                subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyttsx3'], 
                             capture_output=True, check=True, timeout=30)
                logger.info("Successfully installed pyttsx3 TTS engine")
            except Exception as install_error:
                logger.warning(f"Could not auto-install TTS: {install_error}")

    def _check_llm_model_availability(self):
        """Check if orchestrator model is available"""
        try:
            available_models = [m['name'] for m in self.model_manager.get_available_models()]
            selected_model = self.orchestrator_model['name']
            
            if selected_model not in available_models:
                logger.warning(f"Selected orchestrator model {selected_model} not available - using fallback")
                # Strict fallback: require hard-min-context models only
                try:
                    from ..config import Config
                    hard_min_ctx = int(getattr(Config, 'REQUIRED_MIN_CONTEXT_TOKENS', 32768))
                except Exception:
                    hard_min_ctx = 32768
                from .model_sources_manager import get_model_sources_manager
                msm = get_model_sources_manager()
                # Prefer smallest model meeting min context for backend orchestrator to conserve resources
                candidates = msm.get_available_models(min_context=hard_min_ctx, prefer_smallest=True)
                for info in candidates:
                    name = info.get('name') or info.get('filename') or ''
                    self.orchestrator_model['name'] = name
                    logger.info(f"Orchestrator fallback to high-context model: {name}")
                    return
                
        except Exception as e:
            logger.warning(f"Model availability check failed: {e}")

    def manage_model_information_agentic(self, query: str) -> Dict[str, Any]:
        """Agentic model information management with context gathering"""
        try:
            # Use orchestrator to understand what information is needed
            analysis_prompt = f"""
User is asking about models: "{query}"

Based on this query, determine what model information they need:
- Model specifications (context, size, capabilities)
- Model comparisons  
- Hardware requirements
- Installation status
- Performance metrics
- Recommendations based on their hardware tier: {self.pc_profile['hardware_tier']}

Available models: {[m['name'] for m in self.model_manager.get_available_models()]}
PC specs: {self.pc_profile['total_ram_gb']}GB RAM, {self.pc_profile['cpu_cores']} cores, GPU: {self.pc_profile['gpu_available']}

Provide a structured response with the needed information."""

            response = self.backend_controller.generate_response(
                prompt=analysis_prompt,
                system_prompt=self.orchestrator_prompt,
                temperature=0.3,
                max_tokens=1024
            )
            
            return {
                'success': True,
                'response': response,
                'context': {
                    'user_hardware': self.pc_profile,
                    'available_models': self.model_manager.get_available_models(),
                    'personalized': True
                }
            }
            
        except Exception as e:
            logger.error(f"Error in agentic model information: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def update_user_rag(self, interaction_data: Dict[str, Any]):
        """Update user personalization RAG with interaction data"""
        if not self.config.get('user_rag_enabled', True):
            return
        
        try:
            # Extract meaningful data from interaction
            user_data = {
                'timestamp': datetime.now().isoformat(),
                'intent': interaction_data.get('intent'),
                'task_type': interaction_data.get('task_type'),
                'model_used': interaction_data.get('model_used'),
                'satisfaction': interaction_data.get('satisfaction'),
                'duration': interaction_data.get('duration'),
                'hardware_used': {
                    'cpu_usage': self._get_current_cpu_usage(),
                    'ram_usage': self._get_current_ram_usage(),
                    'gpu_usage': self._get_current_gpu_usage()
                }
            }
            
            # Update user profile
            self._update_user_preferences(user_data)
            
            # Save to persistent storage
            self._save_user_profile()
            
        except Exception as e:
            logger.error(f"Error updating user RAG: {e}")

    def _update_user_preferences(self, interaction_data: Dict[str, Any]):
        """Update user preferences based on interaction data"""
        # Track usage patterns
        task_type = interaction_data.get('task_type', 'unknown')
        if task_type not in self.user_profile['usage_patterns']:
            self.user_profile['usage_patterns'][task_type] = 0
        self.user_profile['usage_patterns'][task_type] += 1
        
        # Track model preferences
        model_used = interaction_data.get('model_used')
        if model_used:
            if model_used not in self.user_profile['favorite_models']:
                self.user_profile['favorite_models'][model_used] = 0
            self.user_profile['favorite_models'][model_used] += 1
        
        # Update session counters
        self.user_profile['total_interactions'] += 1
        self.user_profile['last_active'] = datetime.now().isoformat()

    def _save_user_profile(self):
        """Save user profile to database with proper transaction management"""
        try:
            if not APP_AVAILABLE:
                logger.warning("Flask app not available - cannot save user profile to database")
                return
                
            with app.app_context():
                setting = AppSetting.query.filter_by(key='user_profile').first()
                if not setting:
                    setting = AppSetting()
                    setting.key = 'user_profile'
                    db.session.add(setting)
                
                setting.value = json.dumps(self.user_profile)
                db.session.commit()
            
        except Exception as e:
            logger.error(f"Error saving user profile: {e}")
            try:
                db.session.rollback()
            except Exception as rollback_error:
                logger.error(f"Error during rollback: {rollback_error}")

    def _get_current_cpu_usage(self) -> float:
        """Get current CPU usage percentage"""
        try:
            import psutil
            cpu_usage = psutil.cpu_percent(interval=1)
            # Handle case where psutil returns a list (per-cpu) or float (average)
            if isinstance(cpu_usage, list):
                return float(sum(cpu_usage) / len(cpu_usage)) if cpu_usage else 0.0
            return float(cpu_usage)
        except Exception as e:
            logger.warning(f"Failed to get CPU usage: {e}")
            return 0.0

    def _get_current_ram_usage(self) -> float:
        """Get current RAM usage percentage"""
        try:
            import psutil
            return psutil.virtual_memory().percent
        except Exception as e:
            logger.warning(f"Failed to get RAM usage: {e}")
            return 0.0

    def _get_current_gpu_usage(self) -> float:
        """Get current GPU usage percentage"""
        try:
            if self.pc_profile['gpu_available'] == 'nvidia':
                import subprocess
                result = subprocess.run(['nvidia-smi', '--query-gpu=utilization.gpu', '--format=csv,noheader,nounits'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return float(result.stdout.strip())
        except Exception as e:
            logger.warning(f"Failed to get GPU usage: {e}")
            pass
        return 0.0

    def get_personalized_recommendations(self) -> Dict[str, Any]:
        """Get personalized recommendations based on user data"""
        try:
            # Analyze user patterns
            most_used_tasks = sorted(self.user_profile['usage_patterns'].items(), 
                                   key=lambda x: x[1], reverse=True)[:3]
            
            favorite_models = sorted(self.user_profile['favorite_models'].items(),
                                   key=lambda x: x[1], reverse=True)[:3]
            
            # Generate recommendations
            recommendations = {
                'suggested_models': self._get_model_recommendations_for_user(),
                'workflow_optimizations': self._get_workflow_optimizations(),
                'hardware_optimizations': self._get_hardware_optimizations(),
                'most_used_tasks': most_used_tasks,
                'favorite_models': favorite_models,
                'skill_level_assessment': self._assess_skill_level()
            }
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting personalized recommendations: {e}")
            return {}

    def _get_model_recommendations_for_user(self) -> List[str]:
        """Get model recommendations based on user patterns"""
        # Analyze user's most common tasks
        common_tasks = list(self.user_profile['usage_patterns'].keys())
        
        recommendations = []
        
        if 'creative' in str(common_tasks).lower():
            recommendations.extend(['llama3.1:8b', 'mistral:7b'])
        if 'coding' in str(common_tasks).lower() or 'technical' in str(common_tasks).lower():
            recommendations.extend(['qwen2.5-coder:7b', 'deepseek-coder:6.7b'])
        if 'chat' in str(common_tasks).lower():
            recommendations.extend(['phi3:medium', 'llama3.2:3b'])
        
        # Filter by hardware tier
        tier_models = self._get_recommended_models_for_tier(self.pc_profile['hardware_tier'])
        recommendations = [m for m in recommendations if m in tier_models]
        
        return recommendations[:3]

    def _get_workflow_optimizations(self) -> List[str]:
        """Get workflow optimization suggestions"""
        optimizations = []
        
        if self.pc_profile['max_concurrent_models'] > 1:
            optimizations.append("Consider running specialized models concurrently for better performance")
        
        if self.pc_profile['gpu_available'] != 'none':
            optimizations.append("Enable GPU acceleration for faster model inference")
        
        if self.user_profile['total_interactions'] > 50:
            optimizations.append("Create custom workflows for your most common tasks")
        
        return optimizations

    def _get_hardware_optimizations(self) -> List[str]:
        """Get hardware optimization suggestions"""
        optimizations = []
        
        if self.pc_profile['available_ram_gb'] < 8:
            optimizations.append("Consider upgrading RAM for better model performance")
        
        if self.pc_profile['gpu_available'] == 'none':
            optimizations.append("A dedicated GPU would significantly improve generation speeds")
        
        if self.pc_profile['disk_free_gb'] < 20:
            optimizations.append("Free up disk space - models require significant storage")
        
        return optimizations

    def _assess_skill_level(self) -> str:
        """Assess user skill level based on interaction patterns"""
        interactions = self.user_profile['total_interactions']
        task_variety = len(self.user_profile['usage_patterns'])
        
        if interactions > 100 and task_variety > 5:
            return 'expert'
        elif interactions > 50 and task_variety > 3:
            return 'advanced'
        elif interactions > 20:
            return 'intermediate'
        else:
            return 'beginner'
    
    def _create_orchestrator_prompt(self) -> str:
        """Create the master system prompt for the orchestrator"""
        from ..utils.policy_manager import get_policy_manager
        pm = get_policy_manager()
        # Build a minimal policy set based on enabled features to reduce prompt size
        include_files = [
            '001_resource_coordination',
            '003_safety_and_privacy',
        ]
        if self._feature_enabled('rag'):
            include_files.append('002_rag_usage')
        policy_excerpt = pm.get_excerpt_for(include_files, max_chars=1400)
        return f"""You are the Vybe Orchestrator, a highly efficient AI system coordinator.

Your role is to:
1. Analyze user intent and classify requests
2. Determine which specialized models or tools to use
3. Create execution plans for complex tasks
4. Monitor system resources and optimize performance
5. Coordinate multi-step workflows

Request Classification:
- SIMPLE_QUERY: Direct factual questions that can be answered immediately
- CREATIVE_TASK: Requires creative generation (stories, ideas, etc.)
- TECHNICAL_TASK: Programming, analysis, or technical problem-solving
- IMAGE_GENERATION: Requests for visual content creation
- AUDIO_TASK: TTS, transcription, or audio processing
- RAG_QUERY: Requires searching knowledge base
- MULTI_STEP: Complex tasks requiring multiple operations
- SYSTEM_COMMAND: System configuration or status queries

        For each request, provide a structured response:
        {{
          "intent": "classification",
          "confidence": 0.0-1.0,
          "plan": ["step1", "step2"],
          "resources_needed": ["model_type", "tools"],
          "estimated_time": "seconds",
          "delegate_to": "model_name or 'self'"
        }}

Always consider system resources and user preferences when making decisions.

        [Policy Excerpts]
        {policy_excerpt}
"""

    def _feature_enabled(self, name: str) -> bool:
        try:
            if name == 'rag':
                return bool(self.config.get('user_rag_enabled', True))
        except Exception:
            pass
        return False
    
    def analyze_intent(self, user_input: str) -> Dict[str, Any]:
        """
        Analyze user intent and determine how to handle the request
        
        Args:
            user_input: The user's input text
            
        Returns:
            Dictionary containing intent analysis and execution plan
        """
        try:
            # Prepare the analysis prompt
            from ..utils.context_packer import clamp_text
            analysis_prompt = f"""Analyze this user request and provide a structured response:

User Request: "{clamp_text(user_input, 8000)}"

Recent Context: {clamp_text(self._get_recent_context(), 4000)}

System Status:
- Available Models: {[m['name'] for m in self.model_manager.get_available_models()]}
- System Load: {self._get_system_status()}

Provide your analysis in the specified JSON format."""

            # Get orchestrator analysis
            response = self.backend_controller.generate_response(
                prompt=analysis_prompt,
                system_prompt=self.orchestrator_prompt,
                temperature=self.config['orchestrator_temperature'],
                max_tokens=512
            )
            
            # Parse the response
            analysis = self._parse_orchestrator_response(response)
            
            # Add metadata
            analysis['timestamp'] = datetime.now().isoformat()
            analysis['user_input'] = user_input
            
            # Log the decision
            logger.info(f"Orchestrator decision: {analysis.get('intent')} "
                       f"with confidence {analysis.get('confidence', 0):.2f}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing intent: {e}")
            return {
                'intent': 'ERROR',
                'confidence': 0.0,
                'error': str(e),
                'fallback': 'direct_response'
            }
    
    def create_execution_plan(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Create a detailed execution plan based on intent analysis
        
        Args:
            analysis: The intent analysis result
            
        Returns:
            List of execution steps
        """
        intent = analysis.get('intent', 'SIMPLE_QUERY')
        plan = []
        
        if intent == 'MULTI_STEP':
            # Complex multi-step planning
            plan = self._create_multi_step_plan(analysis)
        elif intent == 'IMAGE_GENERATION':
            plan = [{
                'step': 'generate_image',
                'model': 'stable_diffusion',
                'params': self._extract_image_params(analysis)
            }]
        elif intent == 'RAG_QUERY':
            plan = [{
                'step': 'search_knowledge',
                'tool': 'rag_search',
                'query': analysis.get('user_input')
            }, {
                'step': 'generate_response',
                'model': 'chat_model',
                'context': 'rag_results'
            }]
        elif intent in ['CREATIVE_TASK', 'TECHNICAL_TASK']:
            # Delegate to larger model
            plan = [{
                'step': 'delegate_to_model',
                'model': self._select_best_model(intent),
                'params': {'temperature': 0.7 if intent == 'CREATIVE_TASK' else 0.3}
            }]
        else:
            # Simple direct response
            plan = [{
                'step': 'direct_response',
                'model': 'orchestrator',
                'params': {}
            }]
        
        return plan
    
    def execute_plan(self, plan: List[Dict[str, Any]], context: Dict[str, Any]) -> Any:
        """
        Execute a plan step by step
        
        Args:
            plan: The execution plan
            context: Execution context including user input
            
        Returns:
            Final result of plan execution
        """
        results = []
        intermediate_context = context.copy()
        
        for step in plan:
            try:
                logger.info(f"Executing step: {step.get('step')}")
                
                if step['step'] == 'direct_response':
                    result = self._handle_direct_response(intermediate_context)
                elif step['step'] == 'delegate_to_model':
                    result = self._delegate_to_model(step, intermediate_context)
                elif step['step'] == 'generate_image':
                    result = self._trigger_image_generation(step, intermediate_context)
                elif step['step'] == 'search_knowledge':
                    result = self._search_knowledge_base(step, intermediate_context)
                else:
                    result = f"Unknown step type: {step['step']}"
                
                results.append(result)
                intermediate_context[f"step_{len(results)}_result"] = result
                
            except Exception as e:
                logger.error(f"Error executing step {step}: {e}")
                results.append(f"Error in step: {str(e)}")
        
        return self._combine_results(results)
    
    def _parse_orchestrator_response(self, response: str) -> Dict[str, Any]:
        """Parse the orchestrator's JSON response"""
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                # Fallback parsing
                return {
                    'intent': 'SIMPLE_QUERY',
                    'confidence': 0.5,
                    'plan': ['direct_response'],
                    'delegate_to': 'self'
                }
        except Exception as e:
            logger.warning(f"Could not parse orchestrator response: {e}")
            return {
                'intent': 'SIMPLE_QUERY',
                'confidence': 0.3,
                'plan': ['direct_response'],
                'parse_error': str(e)
            }
    
    def _get_system_status(self) -> str:
        """Get current system status for decision making"""
        try:
            usage = self.system_monitor.get_system_usage()
            return f"CPU: {usage['cpu_percent']:.1f}%, RAM: {usage['ram_percent']:.1f}%"
        except Exception as e:
            logger.warning(f"Failed to get system status: {e}")
            return "System status unavailable"
    
    def _get_recent_context(self) -> str:
        """Get recent conversation context"""
        if not self.conversation_context:
            return "No recent context"
        
        # Return last 3 interactions
        recent = self.conversation_context[-3:]
        return "; ".join([f"{c['role']}: {c['message'][:50]}..." for c in recent])
    
    def _create_multi_step_plan(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create a plan for multi-step operations"""
        base_plan = analysis.get('plan', [])
        detailed_plan = []
        
        for step_desc in base_plan:
            # Convert high-level step descriptions to executable steps
            if 'research' in step_desc.lower():
                detailed_plan.append({
                    'step': 'search_knowledge',
                    'tool': 'rag_search',
                    'description': step_desc
                })
            elif 'generate' in step_desc.lower() or 'create' in step_desc.lower():
                detailed_plan.append({
                    'step': 'delegate_to_model',
                    'model': 'creative_model',
                    'description': step_desc
                })
            elif 'analyze' in step_desc.lower():
                detailed_plan.append({
                    'step': 'delegate_to_model',
                    'model': 'analytical_model',
                    'description': step_desc
                })
            else:
                detailed_plan.append({
                    'step': 'process',
                    'description': step_desc
                })
        
        return detailed_plan
    
    def _select_best_model(self, intent: str) -> str:
        """Select the best model for a given intent based on hardware and availability"""
        # This would integrate with hardware tier system
        model_mapping = {
            'CREATIVE_TASK': 'llama-2-7b',
            'TECHNICAL_TASK': 'codellama-7b',
            'SIMPLE_QUERY': 'tinyllama',
            'ANALYSIS': 'mixtral-8x7b'
        }
        
        preferred = model_mapping.get(intent, 'tinyllama')
        
        # Check if model is available
        available_models = [m['name'] for m in self.model_manager.get_available_models()]
        if preferred in available_models:
            return preferred
        
        # Fallback to any available model
        return available_models[0] if available_models else 'tinyllama'
    
    def _handle_direct_response(self, context: Dict[str, Any]) -> str:
        """Handle a direct response from the orchestrator"""
        user_input = context.get('user_input', '')
        return self.backend_controller.generate_response(
            prompt=user_input,
            temperature=0.7,
            max_tokens=512
        )
    
    def _delegate_to_model(self, step: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Delegate generation to a specialized model"""
        model_name = step.get('model', 'default')
        params = step.get('params', {})
        user_input = context.get('user_input', '')
        
        logger.info(f"Delegating to model: {model_name}")
        
        # Here we would load and use the specified model
        # For now, use the backend controller
        return self.backend_controller.generate_response(
            prompt=user_input,
            temperature=params.get('temperature', 0.7),
            max_tokens=params.get('max_tokens', 1024)
        )
    
    def _trigger_image_generation(self, step: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Trigger image generation workflow"""
        # This would integrate with stable_diffusion_controller
        return "Image generation triggered with params: " + str(step.get('params', {}))
    
    def _search_knowledge_base(self, step: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Search the RAG knowledge base"""
        # This would integrate with RAG system
        query = step.get('query', context.get('user_input', ''))
        return f"Searching knowledge base for: {query}"
    
    def _extract_image_params(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Extract image generation parameters from analysis"""
        # Parse user input for image generation params
        return {
            'prompt': analysis.get('user_input', ''),
            'negative_prompt': '',
            'steps': 30,
            'cfg_scale': 7.5,
            'width': 512,
            'height': 512
        }
    
    def _combine_results(self, results: List[Any]) -> Any:
        """Combine multiple step results into final output"""
        if len(results) == 1:
            return results[0]
        
        # Combine multiple results intelligently
        combined = "\n\n".join([str(r) for r in results if r])
        return combined
    
    def update_context(self, role: str, message: str):
        """Update conversation context for better decision making"""
        self.conversation_context.append({
            'role': role,
            'message': message,
            'timestamp': datetime.now().isoformat()
        })
        
        # Keep only last 10 interactions
        if len(self.conversation_context) > 10:
            self.conversation_context = self.conversation_context[-10:]
    
    def get_status(self) -> Dict[str, Any]:
        """Get current Manager Model status"""
        return {
            'is_ready': self.backend_controller.is_server_ready(),
            'config': self.config,
            'active_agents': list(self.active_agents.keys()),
            'context_size': len(self.conversation_context),
            'system_status': self._get_system_status()
        }


# Global instance
_manager_model: Optional[ManagerModel] = None


def get_manager_model() -> ManagerModel:
    """Get or create the global Manager Model instance"""
    global _manager_model
    if _manager_model is None:
        _manager_model = ManagerModel()
    return _manager_model


def initialize_manager_model():
    """Initialize the Manager Model on application startup"""
    manager = get_manager_model()
    logger.info("Manager Model initialized and ready for orchestration")
    return manager