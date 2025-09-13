"""
Dynamic Model Selector for Vybe
Replaces hardcoded model lists with intelligent hardware-based recommendations
"""

import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

from .hardware_manager import get_hardware_manager
from ..models import db, AppSetting

logger = logging.getLogger(__name__)


class DynamicModelSelector:
    """
    Intelligent model selector that provides up-to-date model recommendations
    based on hardware capabilities and current model availability
    """
    
    # Model repository sources
    MODEL_SOURCES = {
        'huggingface': {
            'api_url': 'https://huggingface.co/api/models',
            'search_params': {
                'filter': 'gguf',
                'sort': 'downloads',
                'direction': -1,
                'limit': 50
            }
        },
        'ollama': {
            'api_url': 'https://registry.ollama.ai/v2/models',
            'backup_file': 'ollama_models_backup.json'
        }
    }
    
    # Model categories by hardware tier
    TIER_REQUIREMENTS = {
        'high_end': {
            'llm': {
                'min_params': '7B',
                'max_params': '70B',
                'context_sizes': [32768, 64768, 128000],
                'formats': ['Q5_K_M', 'Q6_K', 'Q8_0'],
                'recommended_types': ['chat', 'instruct', 'code']
            },
            'image': {
                'models': ['sdxl', 'stable-diffusion-2.1', 'dreamshaper'],
                'resolutions': ['512x512', '768x768', '1024x1024'],
                'batch_sizes': [4, 8]
            },
            'audio': {
                'whisper': ['large-v3', 'large-v2', 'medium'],
                'tts': ['xtts-v2', 'bark', 'tortoise']
            }
        },
        'mid_range': {
            'llm': {
                'min_params': '3B',
                'max_params': '13B',
                'context_sizes': [16384, 32768],
                'formats': ['Q4_K_M', 'Q5_K_M'],
                'recommended_types': ['chat', 'instruct']
            },
            'image': {
                'models': ['stable-diffusion-1.5', 'dreamshaper-v8'],
                'resolutions': ['512x512', '768x768'],
                'batch_sizes': [1, 2]
            },
            'audio': {
                'whisper': ['medium', 'small'],
                'tts': ['xtts-v2', 'pyttsx3']
            }
        },
        'entry_level': {
            'llm': {
                'min_params': '1B',
                'max_params': '7B',
                'context_sizes': [8192, 16384],
                'formats': ['Q4_0', 'Q4_K_M'],
                'recommended_types': ['chat', 'mini']
            },
            'image': {
                'models': ['sd-turbo'],
                'resolutions': ['512x512'],
                'batch_sizes': [1]
            },
            'audio': {
                'whisper': ['small', 'base'],
                'tts': ['pyttsx3', 'edge-tts']
            }
        },
        'minimal': {
            'llm': {
                'min_params': '0.5B',
                'max_params': '3B',
                'context_sizes': [4096, 8192],
                'formats': ['Q4_0'],
                'recommended_types': ['mini', 'tiny']
            },
            'image': {
                'models': [],  # No image generation on minimal
                'resolutions': [],
                'batch_sizes': []
            },
            'audio': {
                'whisper': ['base', 'tiny'],
                'tts': ['pyttsx3']
            }
        }
    }
    
    def __init__(self):
        """Initialize the Dynamic Model Selector"""
        self.hardware_manager = get_hardware_manager()
        self.cache_duration = timedelta(hours=6)  # Refresh model list every 6 hours
        self._model_cache = {}
        self._last_update = {}
        
    def get_recommended_models(self, category: str = 'all') -> Dict[str, Any]:
        """
        Get model recommendations based on current hardware
        
        Args:
            category: 'llm', 'image', 'audio', or 'all'
            
        Returns:
            Dictionary containing categorized model recommendations
        """
        # Ensure hardware is detected
        if not self.hardware_manager.performance_tier:
            self.hardware_manager.classify_performance_tier()
        
        tier = self.hardware_manager.performance_tier or 'minimal'
        tier_config = self.TIER_REQUIREMENTS.get(tier, self.TIER_REQUIREMENTS['minimal'])
        
        recommendations = {
            'hardware_tier': tier,
            'tier_description': self.hardware_manager.TIER_DEFINITIONS.get(tier, {}).get('description', 'Minimal system'),
            'timestamp': datetime.now().isoformat(),
            'categories': {}
        }
        
        if category in ['llm', 'all']:
            recommendations['categories']['llm'] = self._get_llm_recommendations(tier_config['llm'])
        
        if category in ['image', 'all']:
            recommendations['categories']['image'] = self._get_image_recommendations(tier_config['image'])
            
        if category in ['audio', 'all']:
            recommendations['categories']['audio'] = self._get_audio_recommendations(tier_config['audio'])
        
        return recommendations
    
    def _get_llm_recommendations(self, tier_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get LLM model recommendations for the hardware tier"""
        models = []
        
        # Try to fetch fresh model data
        try:
            fresh_models = self._fetch_llm_models()
            
            for model in fresh_models:
                if self._model_matches_tier(model, tier_config):
                    models.append(self._format_llm_model(model))
                    
                if len(models) >= 10:  # Limit to top 10 recommendations
                    break
                    
        except Exception as e:
            logger.warning(f"Failed to fetch fresh LLM models: {e}")
            models = self._get_fallback_llm_models(tier_config)
        
        return sorted(models, key=lambda x: x.get('downloads', 0), reverse=True)
    
    def _get_image_recommendations(self, tier_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get image model recommendations for the hardware tier"""
        models = []
        
        for model_name in tier_config['models']:
            model_info = self._get_image_model_info(model_name)
            if model_info:
                models.append(model_info)
        
        return models
    
    def _get_audio_recommendations(self, tier_config: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """Get audio model recommendations for the hardware tier"""
        return {
            'whisper': [self._get_whisper_model_info(model) for model in tier_config['whisper']],
            'tts': [self._get_tts_model_info(model) for model in tier_config['tts']]
        }
    
    def _fetch_llm_models(self) -> List[Dict[str, Any]]:
        """Fetch fresh LLM models from HuggingFace"""
        cache_key = 'llm_models'
        
        # Check cache first
        if self._is_cache_valid(cache_key):
            return self._model_cache[cache_key]
        
        try:
            # Fetch from HuggingFace
            params = self.MODEL_SOURCES['huggingface']['search_params'].copy()
            response = requests.get(
                self.MODEL_SOURCES['huggingface']['api_url'],
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            models = response.json()
            
            # Cache the results
            self._model_cache[cache_key] = models
            self._last_update[cache_key] = datetime.now()
            self._save_model_cache()
            
            logger.info(f"Fetched {len(models)} LLM models from HuggingFace")
            return models
            
        except Exception as e:
            logger.warning(f"Failed to fetch models from HuggingFace: {e}")
            return self._load_fallback_models(cache_key)
    
    def _model_matches_tier(self, model: Dict[str, Any], tier_config: Dict[str, Any]) -> bool:
        """Check if a model matches the hardware tier requirements"""
        model_id = model.get('id', '').lower()
        
        # Check parameter count
        param_indicators = ['0.5b', '1b', '1.1b', '2b', '3b', '7b', '8b', '13b', '70b']
        model_params = None
        
        for indicator in param_indicators:
            if indicator in model_id:
                model_params = indicator
                break
        
        if not model_params:
            return False
        
        # Convert to comparable format
        min_params = tier_config['min_params'].lower()
        max_params = tier_config['max_params'].lower()
        
        # Simple parameter comparison (this could be more sophisticated)
        param_order = ['0.5b', '1b', '1.1b', '2b', '3b', '7b', '8b', '13b', '70b']
        
        try:
            model_idx = param_order.index(model_params)
            min_idx = param_order.index(min_params)
            max_idx = param_order.index(max_params)
            
            if not (min_idx <= model_idx <= max_idx):
                return False
        except ValueError:
            return False
        
        # Check if it's a recommended type
        for rec_type in tier_config['recommended_types']:
            if rec_type in model_id:
                return True
        
        return False
    
    def _format_llm_model(self, model: Dict[str, Any]) -> Dict[str, Any]:
        """Format model data for frontend display"""
        return {
            'id': model.get('id', ''),
            'name': model.get('id', '').split('/')[-1],
            'author': model.get('id', '').split('/')[0] if '/' in model.get('id', '') else 'Unknown',
            'downloads': model.get('downloads', 0),
            'updated': model.get('lastModified', ''),
            'description': _extract_model_description(model),
            'size_estimate': _estimate_model_size(model),
            'context_length': _extract_context_length(model),
            'download_url': f"https://huggingface.co/{model.get('id', '')}/resolve/main",
            'type': 'llm'
        }
    
    def _get_image_model_info(self, model_name: str) -> Dict[str, Any]:
        """Get information for an image model"""
        model_database = {
            'stable-diffusion-1.5': {
                'name': 'Stable Diffusion v1.5',
                'type': 'General Purpose',
                'size_gb': 4.2,
                'resolution': '512x512',
                'description': 'The classic Stable Diffusion v1.5 model. Great for general image generation.',
                'sample_images': [
                    'https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/blog/sd_benchmarking/sd_1_5.png'
                ],
                'download_url': 'https://huggingface.co/runwayml/stable-diffusion-v1-5',
                'license': 'CreativeML Open RAIL-M'
            },
            'dreamshaper-v8': {
                'name': 'DreamShaper v8',
                'type': 'Artistic',
                'size_gb': 2.1,
                'resolution': '512x512',
                'description': 'Popular community model known for vibrant colors and artistic style.',
                'sample_images': [
                    'https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/diffusers/astronaut_rides_horse.png'
                ],
                'download_url': 'https://civitai.com/models/4384/dreamshaper',
                'license': 'CreativeML Open RAIL-M'
            },
            'sdxl': {
                'name': 'Stable Diffusion XL',
                'type': 'High Resolution',
                'size_gb': 6.9,
                'resolution': '1024x1024',
                'description': 'Latest SDXL model for high-resolution image generation.',
                'sample_images': [
                    'https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/blog/stable_diffusion_jax/image_2.png'
                ],
                'download_url': 'https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0',
                'license': 'CreativeML Open RAIL++'
            }
        }
        
        return model_database.get(model_name, {
            'name': model_name.replace('-', ' ').title(),
            'type': 'Unknown',
            'size_gb': 0,
            'description': f'{model_name} image generation model',
            'sample_images': [],
            'download_url': '',
            'license': 'Unknown'
        })
    
    def _get_whisper_model_info(self, model_name: str) -> Dict[str, Any]:
        """Get information for a Whisper model"""
        whisper_models = {
            'tiny': {'size_mb': 39, 'description': 'Fastest model for real-time transcription'},
            'base': {'size_mb': 74, 'description': 'Good balance of speed and accuracy'},
            'small': {'size_mb': 244, 'description': 'Higher accuracy with reasonable speed'},
            'medium': {'size_mb': 769, 'description': 'Professional quality transcription'},
            'large-v2': {'size_mb': 1550, 'description': 'Best accuracy for production use'},
            'large-v3': {'size_mb': 1550, 'description': 'Latest model with improved accuracy'}
        }
        
        info = whisper_models.get(model_name, {
            'size_mb': 0,
            'description': f'{model_name} Whisper model'
        })
        
        return {
            'name': f'whisper-{model_name}',
            'size_mb': info['size_mb'],
            'description': info['description'],
            'type': 'speech-to-text',
            'download_url': f'https://huggingface.co/openai/whisper-{model_name}'
        }
    
    def _get_tts_model_info(self, model_name: str) -> Dict[str, Any]:
        """Get information for a TTS model"""
        tts_models = {
            'pyttsx3': {
                'size_mb': 0,
                'description': 'Built-in system text-to-speech',
                'status': 'installed'
            },
            'edge-tts': {
                'size_mb': 0,
                'description': 'Microsoft Edge cloud-based TTS',
                'status': 'available'
            },
            'xtts-v2': {
                'size_mb': 1800,
                'description': 'Advanced voice cloning and multi-language TTS',
                'status': 'downloadable'
            },
            'bark': {
                'size_mb': 5000,
                'description': 'Realistic speech synthesis with emotions',
                'status': 'downloadable'
            }
        }
        
        info = tts_models.get(model_name, {
            'size_mb': 0,
            'description': f'{model_name} TTS model',
            'status': 'unknown'
        })
        
        return {
            'name': model_name,
            'size_mb': info['size_mb'],
            'description': info['description'],
            'type': 'text-to-speech',
            'status': info['status']
        }
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        if cache_key not in self._model_cache or cache_key not in self._last_update:
            return False
        
        return datetime.now() - self._last_update[cache_key] < self.cache_duration
    
    def _save_model_cache(self):
        """Save model cache to database"""
        try:
            cache_data = {
                'models': self._model_cache,
                'last_update': {k: v.isoformat() for k, v in self._last_update.items()}
            }
            
            setting = AppSetting.query.filter_by(key='dynamic_model_cache').first()
            if not setting:
                setting = AppSetting()
                setting.key = 'dynamic_model_cache'
            setting.value = json.dumps(cache_data)
            db.session.add(setting)
            db.session.commit()
        except Exception as e:
            logger.error(f"Failed to save model cache: {e}")
    
    def _load_model_cache(self):
        """Load model cache from database"""
        try:
            setting = AppSetting.query.filter_by(key='dynamic_model_cache').first()
            if setting and setting.value:
                cache_data = json.loads(setting.value)
                self._model_cache = cache_data.get('models', {})
                
                # Restore timestamps
                last_update_str = cache_data.get('last_update', {})
                self._last_update = {
                    k: datetime.fromisoformat(v) for k, v in last_update_str.items()
                }
        except Exception as e:
            logger.warning(f"Failed to load model cache: {e}")
    
    def _get_fallback_llm_models(self, tier_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get fallback LLM models when API calls fail"""
        fallback_models = {
            'high_end': [
                {'id': 'microsoft/DialoGPT-large', 'downloads': 100000},
                {'id': 'NousResearch/Nous-Hermes-2-Mixtral-8x7B-DPO', 'downloads': 80000}
            ],
            'mid_range': [
                {'id': 'microsoft/DialoGPT-medium', 'downloads': 50000},
                {'id': 'NousResearch/Nous-Hermes-2-Mistral-7B-DPO', 'downloads': 60000}
            ],
            'entry_level': [
                {'id': 'microsoft/DialoGPT-small', 'downloads': 30000},
                {'id': 'TinyLlama/TinyLlama-1.1B-Chat-v1.0', 'downloads': 40000}
            ],
            'minimal': [
                {'id': 'TinyLlama/TinyLlama-1.1B-Chat-v1.0', 'downloads': 40000}
            ]
        }
        
        tier = tier_config.get('tier', 'minimal')
        models = fallback_models.get(tier, fallback_models['minimal'])
        return [self._format_llm_model(model) for model in models]
    
    def _load_fallback_models(self, cache_key: str) -> List[Dict[str, Any]]:
        """Load fallback models from cache or return empty list"""
        if cache_key in self._model_cache:
            return self._model_cache[cache_key]
        return []


# Helper functions for extracting model information
def _extract_model_description(model: Dict[str, Any]) -> str:
    """Extract description from model metadata"""
    # This would parse the model card or README for description
    return f"Advanced language model with {model.get('id', 'unknown')} architecture"

def _estimate_model_size(model: Dict[str, Any]) -> str:
    """Estimate model size based on name patterns"""
    model_id = model.get('id', '').lower()
    
    if '0.5b' in model_id:
        return '~0.5 GB'
    elif '1b' in model_id or '1.1b' in model_id:
        return '~1.0 GB'
    elif '2b' in model_id:
        return '~1.5 GB'
    elif '3b' in model_id:
        return '~2.1 GB'
    elif '7b' in model_id or '8b' in model_id:
        return '~4.2 GB'
    elif '13b' in model_id:
        return '~7.8 GB'
    elif '70b' in model_id:
        return '~42 GB'
    
    return 'Unknown'

def _extract_context_length(model: Dict[str, Any]) -> int:
    """Extract context length from model name or metadata"""
    model_id = model.get('id', '').lower()
    
    if '128k' in model_id:
        return 128000
    elif '64k' in model_id:
        return 65536
    elif '32k' in model_id:
        return 32768
    elif '16k' in model_id:
        return 16384
    elif '8k' in model_id:
        return 8192
    
    return 4096  # Default context length


# Global instance
_dynamic_selector: Optional[DynamicModelSelector] = None

def get_dynamic_model_selector() -> DynamicModelSelector:
    """Get or create the global Dynamic Model Selector instance"""
    global _dynamic_selector
    if _dynamic_selector is None:
        _dynamic_selector = DynamicModelSelector()
    return _dynamic_selector
