"""
Model Sources Manager for Vybe
Integrates multiple model sources (Huggingface, Ollama, direct URLs) with 4K+ context filtering
"""

import requests
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from urllib.parse import urlparse
import asyncio
import aiohttp

# Import caching decorator
from ..utils.cache_manager import cache

logger = logging.getLogger(__name__)

class ModelSourcesManager:
    """Manages multiple sources for downloading and discovering 4K+ context models"""
    
    def __init__(self, models_dir: Path):
        self.models_dir = models_dir
        self.models_dir.mkdir(exist_ok=True)
        
        # Model sources configuration
        self.sources = {
            'huggingface': {
                'api_base': 'https://huggingface.co',
                'api_url': 'https://huggingface.co/api/models',
                'download_template': 'https://huggingface.co/{repo}/resolve/main/{filename}',
                'search_filters': {
                    'pipeline_tag': 'text-generation',
                    'library': 'gguf',
                    'sort': 'downloads',
                    'direction': -1
                }
            },
            'ollama': {
                'api_base': 'https://registry.ollama.ai',
                'api_url': 'https://registry.ollama.ai/v2/library',
                'search_filters': {}
            },
            'direct': {
                'api_base': None,
                'curated_models': []  # Will be populated with curated URLs
            }
        }
        
        # Curated backend orchestrator models optimized for concurrent operation
        self.curated_models = [
            # Tier 1: 8GB GPU Backend Models (2-3GB VRAM usage)
            {
                'name': 'dolphin-2.6-phi-2-2.7b',
                'repo': 'cognitivecomputations/dolphin-2.6-phi-2-gguf',
                'filename': 'dolphin-2.6-phi-2.Q4_K_M.gguf',
                'size_mb': 1600,
                'context': 32768,
                'uncensored': True,
                'vram_usage': 2.5,
                'tier': 1,
                'description': 'Dolphin Phi-2 2.7B - Efficient uncensored backend for 8GB GPUs',
                'backend_optimized': True
            },
            # Tier 2: 10GB GPU Backend Models (3-4GB VRAM usage)
            {
                'name': 'dolphin-2.8-mistral-7b-v02',
                'repo': 'cognitivecomputations/dolphin-2.8-mistral-7b-v02-gguf',
                'filename': 'dolphin-2.8-mistral-7b-v02.Q4_K_M.gguf',
                'size_mb': 4100,
                'context': 32768,
                'uncensored': True,
                'vram_usage': 3.5,
                'tier': 2,
                'description': 'Dolphin Mistral 7B v02 - Uncensored backend for 10GB GPUs',
                'backend_optimized': True
            },
            # Tier 3: 16GB GPU Backend Models (4-5GB VRAM usage)
            {
                'name': 'hermes-2-pro-llama-3-8b',
                'repo': 'NousResearch/Hermes-2-Pro-Llama-3-8B-GGUF',
                'filename': 'Hermes-2-Pro-Llama-3-8B.Q4_K_M.gguf',
                'size_mb': 4800,
                'context': 32768,
                'uncensored': True,
                'vram_usage': 4.5,
                'tier': 3,
                'description': 'Hermes 2 Pro Llama3 8B - Professional uncensored backend for 16GB GPUs',
                'backend_optimized': True
            },
            # Tier 4: 24GB+ GPU Backend Models (8GB VRAM usage)
            {
                'name': 'dolphin-2.9-llama3-70b',
                'repo': 'cognitivecomputations/dolphin-2.9-llama3-70b-gguf',
                'filename': 'dolphin-2.9-llama3-70b.Q2_K.gguf',
                'size_mb': 28000,
                'context': 32768,
                'uncensored': True,
                'vram_usage': 8.0,
                'tier': 4,
                'description': 'Dolphin Llama3 70B - Flagship uncensored backend for high-end GPUs',
                'backend_optimized': True
            },
            
            # Additional frontend-optimized models for concurrent use
            {
                'name': 'hermes-2-theta-llama-3-8b',
                'repo': 'NousResearch/Hermes-2-Theta-Llama-3-8B-GGUF',
                'filename': 'Hermes-2-Theta-Llama-3-8B.Q4_K_M.gguf',
                'size_mb': 4800,
                'context': 32768,
                'uncensored': True,
                'vram_usage': 4.5,
                'description': 'Hermes 2 Theta Llama3 8B - Alternative uncensored frontend model',
                'backend_optimized': False
            },
            {
                'name': 'mixtral-8x7b-instruct-v0.1',
                'repo': 'mistralai/Mixtral-8x7B-Instruct-v0.1-GGUF',
                'filename': 'mixtral-8x7b-instruct-v0.1.Q4_K_M.gguf',
                'size_mb': 26000,
                'context': 32768,
                'uncensored': False,
                'vram_usage': 12.0,
                'description': 'Mixtral 8x7B Instruct - High-performance MoE model for capable systems',
                'backend_optimized': False
            },
            {
                'name': 'qwen2-7b-instruct',
                'repo': 'Qwen/Qwen2-7B-Instruct-GGUF',
                'filename': 'qwen2-7b-instruct-q4_k_m.gguf',
                'size_mb': 4200,
                'context': 32768,
                'uncensored': False,
                'vram_usage': 4.0,
                'description': 'Qwen2 7B Instruct - Excellent reasoning with 32K context',
                'backend_optimized': False
            }
        ]
    
    @cache.cached(timeout=3600, cache_name="model_data")  # Cache for 1 hour
    def get_available_models(self, min_context: int = 16384, uncensored_only: bool = False, prefer_smallest: bool = False) -> List[Dict[str, Any]]:
        """Get list of available models that meet context and censorship requirements.
        If prefer_smallest is True, sort to choose smallest model meeting min context
        (uncensored first, then lowest context that meets min, then size).
        Otherwise, prefer larger context.
        """
        filtered_models = []
        
        for model in self.curated_models:
            # Filter by context requirement
            if model['context'] < min_context:
                continue
            
            # Filter by censorship requirement
            if uncensored_only and not model['uncensored']:
                continue
                
            # Add download information
            model['download_url'] = self.sources['huggingface']['download_template'].format(
                repo=model['repo'],
                filename=model['filename']
            )
            
            # Check if already downloaded
            local_path = self.models_dir / model['filename']
            model['downloaded'] = local_path.exists()
            model['local_path'] = str(local_path) if model['downloaded'] else None
            
            filtered_models.append(model)
        
        # Enforce global hard minimum context
        try:
            from ..config import Config
            hard_min = int(getattr(Config, 'REQUIRED_MIN_CONTEXT_TOKENS', min_context))
        except Exception:
            hard_min = min_context
        filtered_models = [m for m in filtered_models if m['context'] >= hard_min]

        if prefer_smallest:
            # Prefer uncensored, then just-enough context (ascending), then smaller size
            filtered_models.sort(key=lambda x: (
                0 if x.get('uncensored', False) else 1,
                x['context'],
                x['size_mb']
            ))
        else:
            # Prefer uncensored, then higher context, then smaller size
            filtered_models.sort(key=lambda x: (
                0 if x.get('uncensored', False) else 1,
                -x['context'],
                x['size_mb']
            ))
        
        return filtered_models
    
    def get_recommended_model(self, hardware_tier: str = 'tier_2_10gb', uncensored_preferred: bool = True, 
                             backend_optimized: bool = True) -> Optional[Dict[str, Any]]:
        """Get recommended model based on hardware tier and preferences
        
        Args:
            hardware_tier: GPU VRAM-based tier (tier_1_8gb, tier_2_10gb, tier_3_16gb, tier_4_24gb_plus)
            uncensored_preferred: Whether to prefer uncensored models
            backend_optimized: Whether to get backend-optimized models for orchestration
        """
        available_models = self.get_available_models(min_context=16384, uncensored_only=False)
        
        # Filter by backend optimization if requested
        if backend_optimized:
            available_models = [m for m in available_models if m.get('backend_optimized', False)]
        
        # Filter by tier if model has tier information
        tier_map = {
            'tier_1_8gb': 1,
            'tier_2_10gb': 2, 
            'tier_3_16gb': 3,
            'tier_4_24gb_plus': 4
        }
        
        target_tier = tier_map.get(hardware_tier, 2)  # Default to tier 2
        tier_models = [m for m in available_models if m.get('tier', 2) == target_tier]
        
        if not tier_models:
            # Fallback to any available model if no tier-specific models found
            tier_models = available_models
        
        if not tier_models:
            return None
        
        # Sort by preference: uncensored first (if preferred), then by VRAM efficiency
        def sort_key(model):
            uncensored_score = 0 if (uncensored_preferred and model.get('uncensored', False)) else 1
            vram_score = model.get('vram_usage', 10.0)  # Lower VRAM usage is better
            return (uncensored_score, vram_score)
        
        tier_models.sort(key=sort_key)
        return tier_models[0] if tier_models else None
    
    def download_model(self, model: Dict[str, Any], progress_callback: Optional[Callable[[str, float], None]] = None) -> bool:
        """Download a model with progress tracking"""
        try:
            download_url = model['download_url']
            filename = model['filename']
            local_path = self.models_dir / filename
            
            if local_path.exists():
                logger.info(f"Model {filename} already exists")
                return True
            
            logger.info(f"Downloading {filename} from {download_url}")
            
            # Download with progress tracking
            response = requests.get(download_url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if progress_callback and total_size > 0:
                            progress = (downloaded / total_size) * 100
                            progress_callback(f"Downloading {filename}", progress)
            
            logger.info(f"Successfully downloaded {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download model {model['name']}: {e}")
            # Clean up partial download
            if local_path.exists():
                local_path.unlink()
            return False
    
    async def search_huggingface_models(self, query: str = "", min_context: int = 4096) -> List[Dict[str, Any]]:
        """Search for models on Huggingface with context filtering"""
        try:
            params = {
                'search': query,
                'filter': 'text-generation',
                'sort': 'downloads',
                'direction': -1,
                'limit': 50
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.sources['huggingface']['api_url'], params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        filtered_models = []
                        for model_info in data:
                            # Basic filtering - would need more sophisticated context detection
                            if any(keyword in model_info['modelId'].lower() for keyword in ['gguf', 'chat', 'instruct']):
                                filtered_models.append({
                                    'name': model_info['modelId'],
                                    'downloads': model_info.get('downloads', 0),
                                    'likes': model_info.get('likes', 0),
                                    'repo': model_info['modelId'],
                                    'source': 'huggingface'
                                })
                        
                        return filtered_models
                        
        except Exception as e:
            logger.error(f"Failed to search Huggingface: {e}")
            
        return []
    
    @cache.cached(timeout=1800, cache_name="model_data")  # Cache for 30 minutes (more dynamic)
    def get_ollama_models(self) -> List[Dict[str, Any]]:
        """Get available models from Ollama registry"""
        try:
            # Ollama has different API - this is a simplified version
            # In reality, would need to integrate with actual Ollama API
            ollama_models = [
                {
                    'name': 'dolphin-llama3:8b',
                    'repo': 'dolphin-llama3',
                    'tag': '8b',
                    'context': 32768,
                    'uncensored': True,
                    'source': 'ollama'
                },
                {
                    'name': 'phi3:mini',
                    'repo': 'phi3',
                    'tag': 'mini',
                    'context': 4096,
                    'uncensored': False,
                    'source': 'ollama'
                }
            ]
            
            return ollama_models
            
        except Exception as e:
            logger.error(f"Failed to get Ollama models: {e}")
            return []
    
    def validate_model_context(self, model_path: Path) -> Optional[int]:
        """Validate that a model has sufficient context (placeholder implementation)"""
        # This would need to inspect the GGUF file metadata to determine actual context
        # For now, return None to indicate unknown context
        return None
    
    def get_model_priority_order(self) -> List[str]:
        """Get the priority order for model selection"""
        return [
            'dolphin', 'hermes', 'uncensored', 'mixtral', 'llama3', 'qwen', 'mistral', 'phi3'
        ]

def get_model_sources_manager() -> ModelSourcesManager:
    """Get singleton instance of ModelSourcesManager"""
    if not hasattr(get_model_sources_manager, '_instance'):
        from ..config import Config
        models_dirs = Config.get_models_directories()
        primary_models_dir = models_dirs[0] if models_dirs else Path('models')
        get_model_sources_manager._instance = ModelSourcesManager(primary_models_dir)
    
    return get_model_sources_manager._instance
