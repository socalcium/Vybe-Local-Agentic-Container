"""
Intelligent Model Router for Vybe
Routes requests to the best available LLM based on context, performance, and availability
"""

import os
import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ModelProvider(Enum):
    LOCAL = "local"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"

@dataclass
class ModelCapability:
    provider: ModelProvider
    model_name: str
    max_tokens: int
    cost_per_1k_tokens: float
    speed_score: int  # 1-10, higher is faster
    quality_score: int  # 1-10, higher is better
    specialties: List[str]  # e.g., ["code", "math", "creative"]
    context_window: int
    available: bool = True

class ModelRouter:
    """Intelligent router for LLM requests"""
    
    def __init__(self):
        self.models = self._initialize_models()
        self.usage_stats = {}
        self.performance_cache = {}
        
    def _initialize_models(self) -> Dict[str, ModelCapability]:
        """Initialize available models with their capabilities"""
        models = {}
        
        # Local models
        models["local-llm"] = ModelCapability(
            provider=ModelProvider.LOCAL,
            model_name="local-llm",
            max_tokens=4096,
            cost_per_1k_tokens=0.0,  # Free
            speed_score=7,
            quality_score=6,
            specialties=["general", "privacy"],
            context_window=4096,
            available=self._check_local_availability()
        )
        
        # OpenAI models
        if os.getenv('OPENAI_API_KEY'):
            models["gpt-4"] = ModelCapability(
                provider=ModelProvider.OPENAI,
                model_name="gpt-4",
                max_tokens=8192,
                cost_per_1k_tokens=0.03,
                speed_score=6,
                quality_score=9,
                specialties=["reasoning", "analysis", "general"],
                context_window=8192,
                available=True
            )
            
            models["gpt-3.5-turbo"] = ModelCapability(
                provider=ModelProvider.OPENAI,
                model_name="gpt-3.5-turbo",
                max_tokens=4096,
                cost_per_1k_tokens=0.002,
                speed_score=9,
                quality_score=7,
                specialties=["general", "fast"],
                context_window=4096,
                available=True
            )
        
        # Anthropic models
        if os.getenv('ANTHROPIC_API_KEY'):
            models["claude-3-sonnet"] = ModelCapability(
                provider=ModelProvider.ANTHROPIC,
                model_name="claude-3-sonnet-20240229",
                max_tokens=4096,
                cost_per_1k_tokens=0.015,
                speed_score=7,
                quality_score=9,
                specialties=["reasoning", "analysis", "safety"],
                context_window=200000,
                available=True
            )
            
            models["claude-3-haiku"] = ModelCapability(
                provider=ModelProvider.ANTHROPIC,
                model_name="claude-3-haiku-20240307",
                max_tokens=4096,
                cost_per_1k_tokens=0.00025,
                speed_score=10,
                quality_score=6,
                specialties=["fast", "general"],
                context_window=200000,
                available=True
            )
        
        # Google models
        if os.getenv('GOOGLE_API_KEY'):
            models["gemini-pro"] = ModelCapability(
                provider=ModelProvider.GOOGLE,
                model_name="gemini-pro",
                max_tokens=2048,
                cost_per_1k_tokens=0.001,
                speed_score=8,
                quality_score=7,
                specialties=["general", "multilingual"],
                context_window=30720,
                available=True
            )
        
        return models
    
    def _check_local_availability(self) -> bool:
        """Check if local LLM is available"""
        try:
            from ..core.backend_llm_controller import llm_controller
            return llm_controller.is_server_ready()
        except Exception as e:
            logger.debug(f"Local LLM availability check failed: {e}")
            return False
    
    def get_best_model(self, 
                      request_type: str = "general",
                      max_cost: Optional[float] = None,
                      min_speed: Optional[int] = None,
                      min_quality: Optional[int] = None,
                      required_context: Optional[int] = None) -> Optional[ModelCapability]:
        """
        Select the best model based on requirements
        
        Args:
            request_type: Type of request ("general", "code", "reasoning", "fast", etc.)
            max_cost: Maximum cost per 1k tokens
            min_speed: Minimum speed score (1-10)
            min_quality: Minimum quality score (1-10)
            required_context: Required context window size
        """
        available_models = [m for m in self.models.values() if m.available]
        
        if not available_models:
            logger.warning("No models available")
            return None
        
        # Filter by requirements
        filtered_models = []
        for model in available_models:
            # Check cost constraint
            if max_cost is not None and model.cost_per_1k_tokens > max_cost:
                continue
                
            # Check speed constraint
            if min_speed is not None and model.speed_score < min_speed:
                continue
                
            # Check quality constraint
            if min_quality is not None and model.quality_score < min_quality:
                continue
                
            # Check context window
            if required_context is not None and model.context_window < required_context:
                continue
            
            filtered_models.append(model)
        
        if not filtered_models:
            # Fall back to local model if no others match
            local_models = [m for m in available_models if m.provider == ModelProvider.LOCAL]
            if local_models:
                return local_models[0]
            # Otherwise return the cheapest available model
            return min(available_models, key=lambda x: x.cost_per_1k_tokens)
        
        # Score models based on request type and performance
        scored_models = []
        for model in filtered_models:
            score = 0
            
            # Specialty bonus
            if request_type in model.specialties:
                score += 10
            elif request_type == "general":
                score += 5
                
            # Quality and speed balance
            score += model.quality_score * 2
            score += model.speed_score
            
            # Cost efficiency (prefer cheaper models, but not at quality expense)
            if model.cost_per_1k_tokens == 0:  # Local/free models
                score += 15
            else:
                # Inverse cost scoring (lower cost = higher score)
                score += max(0, 10 - (model.cost_per_1k_tokens * 100))
            
            # Performance history bonus
            if model.model_name in self.performance_cache:
                avg_response_time = self.performance_cache[model.model_name].get('avg_response_time', 5.0)
                if avg_response_time < 2.0:
                    score += 5
                elif avg_response_time < 5.0:
                    score += 2
            
            scored_models.append((score, model))
        
        # Return the highest scoring model
        best_model = max(scored_models, key=lambda x: x[0])[1]
        logger.info(f"Selected model: {best_model.model_name} from {best_model.provider.value}")
        return best_model
    
    def route_request(self, messages: List[Dict], request_type: str = "general", **kwargs) -> Dict[str, Any]:
        """
        Route a chat completion request to the best available model
        
        Args:
            messages: List of chat messages
            request_type: Type of request for model selection
            **kwargs: Additional parameters (max_tokens, temperature, etc.)
        """
        start_time = time.time()
        
        # Analyze request for requirements
        total_tokens = sum(len(msg.get('content', '')) for msg in messages) // 4  # Rough token estimate
        required_context = kwargs.get('max_tokens', 1000) + total_tokens
        
        # Get performance requirements
        max_cost = kwargs.get('max_cost')
        min_speed = kwargs.get('min_speed')
        min_quality = kwargs.get('min_quality')
        
        # Select best model
        best_model = self.get_best_model(
            request_type=request_type,
            max_cost=max_cost,
            min_speed=min_speed, 
            min_quality=min_quality,
            required_context=required_context
        )
        
        if not best_model:
            return {
                'success': False,
                'error': 'No suitable models available'
            }
        
        # Route to appropriate handler
        try:
            if best_model.provider == ModelProvider.LOCAL:
                result = self._route_to_local(best_model, messages, kwargs)
            elif best_model.provider == ModelProvider.OPENAI:
                result = self._route_to_openai(best_model, messages, kwargs)
            elif best_model.provider == ModelProvider.ANTHROPIC:
                result = self._route_to_anthropic(best_model, messages, kwargs)
            elif best_model.provider == ModelProvider.GOOGLE:
                result = self._route_to_google(best_model, messages, kwargs)
            else:
                return {
                    'success': False,
                    'error': f'Unknown provider: {best_model.provider}'
                }
            
            # Record performance metrics
            response_time = time.time() - start_time
            self._record_performance(best_model.model_name, response_time, result.get('success', False))
            
            # Add routing metadata
            result['routing_info'] = {
                'selected_model': best_model.model_name,
                'provider': best_model.provider.value,
                'response_time': response_time,
                'selection_reason': request_type
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error routing to {best_model.provider.value}: {e}")
            
            # Try fallback to local model
            if best_model.provider != ModelProvider.LOCAL:
                local_model = next((m for m in self.models.values() 
                                  if m.provider == ModelProvider.LOCAL and m.available), None)
                if local_model:
                    logger.info("Falling back to local model")
                    return self._route_to_local(local_model, messages, kwargs)
            
            return {
                'success': False,
                'error': f'Request failed: {str(e)}'
            }
    
    def _route_to_local(self, model: ModelCapability, messages: List[Dict], kwargs: Dict) -> Dict[str, Any]:
        """Route request to local LLM"""
        try:
            from ..core.backend_llm_controller import llm_controller
            
            # Convert messages to local format
            prompt = self._messages_to_prompt(messages)
            system_prompt = self._extract_system_prompt(messages)
            
            response = llm_controller.generate_response(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=kwargs.get('max_tokens', 1000),
                temperature=kwargs.get('temperature', 0.7)
            )
            
            return {
                'success': True,
                'response': response,
                'model': model.model_name,
                'provider': 'local'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Local LLM error: {str(e)}'
            }
    
    def _route_to_openai(self, model: ModelCapability, messages: List[Dict], kwargs: Dict) -> Dict[str, Any]:
        """Route request to OpenAI"""
        return {'success': False, 'error': 'OpenAI integration not available in this version'}
    
    def _route_to_anthropic(self, model: ModelCapability, messages: List[Dict], kwargs: Dict) -> Dict[str, Any]:
        """Route request to Anthropic"""
        return {'success': False, 'error': 'Anthropic integration not available in this version'}
    
    def _route_to_google(self, model: ModelCapability, messages: List[Dict], kwargs: Dict) -> Dict[str, Any]:
        """Route request to Google"""
        return {'success': False, 'error': 'Google integration not available in this version'}
    
    def _messages_to_prompt(self, messages: List[Dict]) -> str:
        """Convert chat messages to a single prompt string"""
        prompt = ""
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            
            if role == 'user':
                prompt += f"User: {content}\n"
            elif role == 'assistant':
                prompt += f"Assistant: {content}\n"
            # Skip system messages here - they're handled separately
        
        prompt += "Assistant: "
        return prompt
    
    def _extract_system_prompt(self, messages: List[Dict]) -> Optional[str]:
        """Extract system prompt from messages"""
        for msg in messages:
            if msg.get('role') == 'system':
                return msg.get('content')
        return None
    
    def _record_performance(self, model_name: str, response_time: float, success: bool):
        """Record performance metrics for model selection"""
        if model_name not in self.performance_cache:
            self.performance_cache[model_name] = {
                'total_requests': 0,
                'successful_requests': 0,
                'total_response_time': 0.0,
                'avg_response_time': 0.0
            }
        
        cache = self.performance_cache[model_name]
        cache['total_requests'] += 1
        cache['total_response_time'] += response_time
        
        if success:
            cache['successful_requests'] += 1
        
        cache['avg_response_time'] = cache['total_response_time'] / cache['total_requests']
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """Get routing statistics and model performance"""
        return {
            'available_models': {name: {
                'provider': model.provider.value,
                'available': model.available,
                'specialties': model.specialties,
                'cost_per_1k': model.cost_per_1k_tokens
            } for name, model in self.models.items()},
            'performance_stats': self.performance_cache,
            'total_models': len(self.models),
            'available_count': sum(1 for m in self.models.values() if m.available)
        }

# Global router instance
model_router = ModelRouter()
