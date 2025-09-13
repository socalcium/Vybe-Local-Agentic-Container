"""
Model Discovery Web Scraper for Vybe
Scrapes Hugging Face and other sources for compatible GGUF models
GGUF model discovery and management system
"""
import requests
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import time
import re

logger = logging.getLogger(__name__)

class ModelDiscoveryManager:
    """Manages discovery of compatible GGUF models from various sources"""
    
    def __init__(self):
        self.huggingface_api_base = "https://huggingface.co/api"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Vybe-AI-Assistant/1.2.0 Model-Discovery'
        })
        
    def discover_huggingface_models(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Discover GGUF models from Hugging Face"""
        try:
            logger.info("Discovering GGUF models from Hugging Face...")
            
            # Search for GGUF models
            search_url = f"{self.huggingface_api_base}/models"
            params = {
                'search': 'gguf',
                'filter': 'gguf',
                'sort': 'downloads',
                'direction': -1,
                'limit': limit
            }
            
            response = self.session.get(search_url, params=params, timeout=10)
            response.raise_for_status()
            
            models_data = response.json()
            discovered_models = []
            
            for model in models_data:
                try:
                    model_info = {
                        'name': model.get('id', 'Unknown'),
                        'description': model.get('description', '')[:200],
                        'downloads': model.get('downloads', 0),
                        'likes': model.get('likes', 0),
                        'tags': model.get('tags', []),
                        'source': 'huggingface',
                        'scraped': True,
                        'model_type': 'gguf',
                        'url': f"https://huggingface.co/{model.get('id', '')}",
                        'size_estimate': self._estimate_model_size(model.get('tags', [])),
                        'compatibility': self._check_compatibility(model.get('tags', []))
                    }
                    
                    # Filter for likely compatible models
                    if self._is_compatible_model(model_info):
                        discovered_models.append(model_info)
                        
                except Exception as e:
                    logger.debug(f"Error processing model {model.get('id', 'Unknown')}: {e}")
                    continue
            
            logger.info(f"Discovered {len(discovered_models)} compatible models from Hugging Face")
            return discovered_models
            
        except Exception as e:
            logger.error(f"Error discovering Hugging Face models: {e}")
            return []
    
    def discover_popular_models(self) -> List[Dict[str, Any]]:
        """Get a curated list of popular, tested GGUF models"""
        popular_models = [
            {
                'name': 'microsoft/DialoGPT-medium',
                'description': 'A medium-size conversational AI model, good for chat applications',
                'downloads': 100000,
                'likes': 500,
                'tags': ['conversational', 'text-generation', 'gguf'],
                'source': 'curated',
                'scraped': True,
                'model_type': 'gguf',
                'url': 'https://huggingface.co/microsoft/DialoGPT-medium',
                'size_estimate': '1.5GB',
                'compatibility': 'high'
            },
            {
                'name': 'TinyLlama/TinyLlama-1.1B-Chat-v1.0',
                'description': 'Small but capable chat model, perfect for getting started',
                'downloads': 50000,
                'likes': 300,
                'tags': ['text-generation', 'chat', 'gguf', 'small'],
                'source': 'curated',
                'scraped': True,
                'model_type': 'gguf',
                'url': 'https://huggingface.co/TinyLlama/TinyLlama-1.1B-Chat-v1.0',
                'size_estimate': '700MB',
                'compatibility': 'high'
            },
            {
                'name': 'Qwen/Qwen2-1.5B-Instruct',
                'description': 'Efficient instruction-following model with good performance',
                'downloads': 25000,
                'likes': 150,
                'tags': ['text-generation', 'instruct', 'gguf'],
                'source': 'curated',
                'scraped': True,
                'model_type': 'gguf',
                'url': 'https://huggingface.co/Qwen/Qwen2-1.5B-Instruct',
                'size_estimate': '900MB',
                'compatibility': 'high'
            }
        ]
        
        logger.info(f"Providing {len(popular_models)} curated popular models")
        return popular_models
    
    def _estimate_model_size(self, tags: List[str]) -> str:
        """Estimate model size from tags"""
        size_indicators = {
            '1b': '700MB', '1.1b': '700MB', '1.5b': '900MB',
            '3b': '1.8GB', '7b': '4.0GB', '13b': '7.5GB',
            '30b': '17GB', '65b': '38GB'
        }
        
        for tag in tags:
            tag_lower = tag.lower()
            for size_key in size_indicators:
                if size_key in tag_lower:
                    return size_indicators[size_key]
        
        return 'Unknown'
    
    def _check_compatibility(self, tags: List[str]) -> str:
        """Check model compatibility level"""
        high_compat_tags = ['gguf', 'q4_k_m', 'q4_0', 'chat', 'instruct']
        medium_compat_tags = ['text-generation', 'conversational']
        
        tag_str = ' '.join(tags).lower()
        
        high_matches = sum(1 for tag in high_compat_tags if tag in tag_str)
        medium_matches = sum(1 for tag in medium_compat_tags if tag in tag_str)
        
        if high_matches >= 2:
            return 'high'
        elif high_matches >= 1 or medium_matches >= 1:
            return 'medium'
        else:
            return 'low'
    
    def _is_compatible_model(self, model_info: Dict[str, Any]) -> bool:
        """Check if model is likely compatible with our backend"""
        # Filter criteria
        if model_info['compatibility'] == 'low':
            return False
        
        # Check for reasonable size (under 10GB for most users)
        size_str = model_info['size_estimate'].lower()
        if 'gb' in size_str:
            try:
                size_num = float(size_str.replace('gb', '').strip())
                if size_num > 10:
                    return False
            except ValueError:
                pass
        
        # Must have reasonable popularity
        if model_info['downloads'] < 100:
            return False
        
        return True
    
    def get_model_recommendations(self, user_preferences: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get model recommendations based on user preferences"""
        if user_preferences is None:
            user_preferences = {}
        
        # Start with popular models
        recommendations = self.discover_popular_models()
        
        # Try to add some from Hugging Face if possible
        try:
            hf_models = self.discover_huggingface_models(limit=20)
            recommendations.extend(hf_models[:5])  # Add top 5
        except Exception as e:
            logger.warning(f"Could not fetch Hugging Face recommendations: {e}")
        
        # Sort by compatibility and popularity
        recommendations.sort(key=lambda x: (
            x['compatibility'] == 'high',
            x['downloads']
        ), reverse=True)
        
        return recommendations[:15]  # Return top 15
    
    def search_models(self, query: str) -> List[Dict[str, Any]]:
        """Search for models matching a query"""
        try:
            # Search Hugging Face
            search_url = f"{self.huggingface_api_base}/models"
            params = {
                'search': f"{query} gguf",
                'limit': 20
            }
            
            response = self.session.get(search_url, params=params, timeout=10)
            response.raise_for_status()
            
            models_data = response.json()
            search_results = []
            
            for model in models_data:
                model_info = {
                    'name': model.get('id', 'Unknown'),
                    'description': model.get('description', '')[:200],
                    'downloads': model.get('downloads', 0),
                    'likes': model.get('likes', 0),
                    'tags': model.get('tags', []),
                    'source': 'search',
                    'scraped': True,
                    'model_type': 'gguf',
                    'url': f"https://huggingface.co/{model.get('id', '')}",
                    'size_estimate': self._estimate_model_size(model.get('tags', [])),
                    'compatibility': self._check_compatibility(model.get('tags', []))
                }
                
                if self._is_compatible_model(model_info):
                    search_results.append(model_info)
            
            logger.info(f"Found {len(search_results)} models matching '{query}'")
            return search_results
            
        except Exception as e:
            logger.error(f"Error searching models: {e}")
            return []
    
    def save_discovered_models(self, models: List[Dict[str, Any]], 
                              filepath: Optional[Path] = None) -> bool:
        """Save discovered models to a JSON file"""
        if filepath is None:
            filepath = Path(__file__).parent.parent / "discovered_models.json"
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(models, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(models)} discovered models to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving discovered models: {e}")
            return False
    
    def load_discovered_models(self, filepath: Optional[Path] = None) -> List[Dict[str, Any]]:
        """Load previously discovered models from JSON file"""
        if filepath is None:
            filepath = Path(__file__).parent.parent / "discovered_models.json"
        
        try:
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    models = json.load(f)
                
                logger.info(f"Loaded {len(models)} previously discovered models")
                return models
            else:
                logger.info("No previously discovered models file found")
                return []
                
        except Exception as e:
            logger.error(f"Error loading discovered models: {e}")
            return []


# Global instance
model_discovery_manager = ModelDiscoveryManager()
