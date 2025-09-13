"""
Context Optimizer for Vybe
Implements smart context management with table of contents and on-demand instruction loading
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class ContextOptimizer:
    """
    Intelligent context manager that provides instructions on-demand rather than
    loading everything upfront. Uses a table of contents approach for efficiency.
    """
    
    def __init__(self):
        """Initialize the Context Optimizer"""
        self.instructions_dir = Path(__file__).parent.parent / 'instructions'
        self.policies_dir = Path(__file__).parent.parent / 'policies'
        self.cache = {}
        self.table_of_contents = self._build_table_of_contents()
        
        # Ensure directories exist
        self.instructions_dir.mkdir(exist_ok=True)
        self.policies_dir.mkdir(exist_ok=True)
        
        # Initialize instruction files if they don't exist
        self._initialize_instruction_files()
    
    def _build_table_of_contents(self) -> Dict[str, Any]:
        """Build a table of contents for all available instructions"""
        toc = {
            'categories': {
                'general': {
                    'description': 'General purpose instructions and guidelines',
                    'files': ['basic_chat.md', 'user_interaction.md', 'safety_guidelines.md'],
                    'priority': 1
                },
                'coding': {
                    'description': 'Code generation and programming assistance',
                    'files': ['code_generation.md', 'debugging_help.md', 'best_practices.md'],
                    'priority': 2
                },
                'image_generation': {
                    'description': 'Image creation and Stable Diffusion guidance',
                    'files': ['sd_prompting.md', 'image_optimization.md', 'art_styles.md'],
                    'priority': 3
                },
                'audio_processing': {
                    'description': 'Audio transcription and TTS instructions',
                    'files': ['whisper_usage.md', 'tts_configuration.md', 'audio_quality.md'],
                    'priority': 3
                },
                'system_management': {
                    'description': 'System operations and resource management',
                    'files': ['resource_monitoring.md', 'model_switching.md', 'optimization.md'],
                    'priority': 4
                },
                'troubleshooting': {
                    'description': 'Error handling and problem resolution',
                    'files': ['error_diagnosis.md', 'recovery_procedures.md', 'performance_issues.md'],
                    'priority': 5
                }
            },
            'core_instructions': {
                'description': 'Always-loaded essential instructions',
                'files': ['core_personality.md', 'response_format.md'],
                'max_tokens': 500  # Keep core instructions small
            },
            'metadata': {
                'version': '1.0',
                'last_updated': datetime.now().isoformat(),
                'total_categories': 6
            }
        }
        return toc
    
    def get_relevant_context(self, user_intent: str, available_tokens: int = 2000) -> Dict[str, Any]:
        """
        Get relevant context based on user intent and available token budget
        
        Args:
            user_intent: Detected user intention/category
            available_tokens: Token budget for context
            
        Returns:
            Dictionary containing relevant instructions and metadata
        """
        context = {
            'core_instructions': self._get_core_instructions(),
            'specific_instructions': [],
            'token_usage': 0,
            'categories_loaded': [],
            'instructions_summary': '',
            'optimization_metadata': {
                'intent_detected': user_intent,
                'token_budget': available_tokens,
                'optimization_strategy': 'adaptive_loading'
            }
        }
        
        # Calculate token usage for core instructions
        core_tokens = self._estimate_tokens(context['core_instructions'])
        context['token_usage'] += core_tokens
        remaining_tokens = available_tokens - core_tokens
        
        # Load specific instructions based on intent with priority ordering
        intent_categories = self._map_intent_to_categories(user_intent)
        
        for category in intent_categories:
            if remaining_tokens <= 100:  # Reserve 100 tokens for safety
                break
                
            category_instructions = self._load_category_instructions(category, remaining_tokens)
            if category_instructions:
                context['specific_instructions'].extend(category_instructions)
                context['categories_loaded'].append(category)
                
                # Update token usage
                category_tokens = self._estimate_tokens('\n'.join(category_instructions))
                context['token_usage'] += category_tokens
                remaining_tokens -= category_tokens
        
        # Generate summary of loaded instructions
        context['instructions_summary'] = self._generate_instructions_summary(context)
        
        # Add optimization metadata
        context['optimization_metadata'].update({
            'tokens_used': context['token_usage'],
            'tokens_remaining': remaining_tokens,
            'categories_loaded': context['categories_loaded'],
            'efficiency_ratio': context['token_usage'] / available_tokens if available_tokens > 0 else 0
        })
        
        return context
    
    def _get_core_instructions(self) -> str:
        """Get always-loaded core instructions"""
        core_file = self.instructions_dir / 'core_personality.md'
        
        if core_file.exists():
            return core_file.read_text(encoding='utf-8')
        
        # Default core instructions if file doesn't exist
        return """You are Vybe, an intelligent AI assistant focused on being helpful, accurate, and efficient.

Core Guidelines:
- Provide clear, concise responses
- Ask for clarification when needed
- Prioritize user safety and privacy
- Adapt your communication style to the user's expertise level
- Use available tools and capabilities efficiently

You have access to various capabilities including text generation, image creation, audio processing, and system management."""
    
    def _categorize_intent(self, user_intent: str) -> List[Dict[str, Any]]:
        """Categorize user intent to determine relevant instruction categories"""
        intent_lower = user_intent.lower()
        relevant_categories = []
        
        # Check for coding-related intents
        if any(keyword in intent_lower for keyword in ['code', 'program', 'script', 'function', 'debug', 'api']):
            relevant_categories.append({
                'name': 'coding',
                'priority': self.table_of_contents['categories']['coding']['priority'],
                'confidence': 0.9
            })
        
        # Check for image generation intents
        if any(keyword in intent_lower for keyword in ['image', 'picture', 'draw', 'art', 'stable diffusion', 'generate']):
            relevant_categories.append({
                'name': 'image_generation',
                'priority': self.table_of_contents['categories']['image_generation']['priority'],
                'confidence': 0.8
            })
        
        # Check for audio processing intents
        if any(keyword in intent_lower for keyword in ['audio', 'voice', 'speech', 'transcribe', 'whisper', 'tts']):
            relevant_categories.append({
                'name': 'audio_processing',
                'priority': self.table_of_contents['categories']['audio_processing']['priority'],
                'confidence': 0.8
            })
        
        # Check for system management intents
        if any(keyword in intent_lower for keyword in ['system', 'resource', 'model', 'performance', 'optimize']):
            relevant_categories.append({
                'name': 'system_management',
                'priority': self.table_of_contents['categories']['system_management']['priority'],
                'confidence': 0.7
            })
        
        # Check for troubleshooting intents
        if any(keyword in intent_lower for keyword in ['error', 'problem', 'issue', 'fix', 'troubleshoot', 'help']):
            relevant_categories.append({
                'name': 'troubleshooting',
                'priority': self.table_of_contents['categories']['troubleshooting']['priority'],
                'confidence': 0.6
            })
        
        # Always include general category with lower priority
        relevant_categories.append({
            'name': 'general',
            'priority': self.table_of_contents['categories']['general']['priority'],
            'confidence': 0.5
        })
        
        return relevant_categories
    
    def _load_category_instructions(self, category: str, max_tokens: int = 1000) -> Optional[List[str]]:
        """Load instructions for a specific category"""
        if category not in self.table_of_contents['categories']:
            return None
        
        category_info = self.table_of_contents['categories'][category]
        content_parts = []
        total_tokens = 0
        
        # Load files in priority order
        for filename in category_info['files']:
            file_path = self.instructions_dir / filename
            if file_path.exists():
                file_content = file_path.read_text(encoding='utf-8')
                file_tokens = self._estimate_tokens(file_content)
                
                if total_tokens + file_tokens <= max_tokens:
                    content_parts.append(f"## {filename.replace('.md', '').replace('_', ' ').title()}\n{file_content}")
                    total_tokens += file_tokens
                else:
                    # Try to fit partial content
                    remaining_tokens = max_tokens - total_tokens
                    if remaining_tokens > 50:  # Only include if meaningful content can fit
                        truncated_content = ' '.join(file_content.split()[:int(remaining_tokens / 4)])  # Use 4 chars per token
                        content_parts.append(f"## {filename.replace('.md', '').replace('_', ' ').title()}\n{truncated_content}...")
                    break
        
        if not content_parts:
            return None
        
        return content_parts
    
    def _map_intent_to_categories(self, user_intent: str) -> List[str]:
        """
        Map user intent to relevant instruction categories with priority ordering
        
        Args:
            user_intent: Detected user intention
            
        Returns:
            List of category names in priority order
        """
        intent_mapping = {
            'coding': ['coding', 'troubleshooting', 'general'],
            'programming': ['coding', 'troubleshooting', 'general'],
            'debug': ['coding', 'troubleshooting', 'general'],
            'image': ['image_generation', 'general'],
            'art': ['image_generation', 'general'],
            'audio': ['audio_processing', 'general'],
            'voice': ['audio_processing', 'general'],
            'system': ['system_management', 'troubleshooting', 'general'],
            'performance': ['system_management', 'optimization', 'general'],
            'error': ['troubleshooting', 'general'],
            'help': ['general', 'troubleshooting'],
            'chat': ['general'],
            'default': ['general']
        }
        
        # Find best matching intent
        user_intent_lower = user_intent.lower()
        for intent_key, categories in intent_mapping.items():
            if intent_key in user_intent_lower:
                return categories
        
        return intent_mapping['default']
    
    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text (rough approximation)
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Estimated token count
        """
        # Rough approximation: 1 token ≈ 4 characters for English text
        return len(text) // 4
    
    def _generate_instructions_summary(self, context: Dict[str, Any]) -> str:
        """
        Generate a summary of loaded instructions for transparency
        
        Args:
            context: Context dictionary with loaded instructions
            
        Returns:
            Summary string
        """
        summary_parts = []
        
        if context['core_instructions']:
            summary_parts.append("Core instructions loaded")
        
        if context['categories_loaded']:
            categories_str = ', '.join(context['categories_loaded'])
            summary_parts.append(f"Categories: {categories_str}")
        
        summary_parts.append(f"Tokens used: {context['token_usage']}")
        
        return ' | '.join(summary_parts)
    
    def _initialize_instruction_files(self):
        """Initialize instruction files if they don't exist"""
        instruction_templates = {
            'core_personality.md': """# Vybe AI Assistant - Core Personality

You are Vybe, an intelligent and helpful AI assistant with the following characteristics:

## Personality Traits
- Professional yet friendly communication style
- Proactive and solution-oriented approach
- Adaptable to user expertise levels
- Respectful of user privacy and preferences

## Response Guidelines
- Provide clear, accurate information
- Ask clarifying questions when needed
- Suggest practical next steps
- Acknowledge limitations honestly

## Capabilities Overview
- Text generation and conversation
- Code assistance and debugging
- Image generation with Stable Diffusion
- Audio processing (transcription, TTS)
- System resource management
""",
            
            'basic_chat.md': """# Basic Chat Instructions

## Conversation Guidelines
- Maintain context throughout the conversation
- Respond appropriately to user emotions and tone
- Provide helpful and relevant information
- Use examples when explaining complex concepts

## Response Format
- Structure responses with clear headings when appropriate
- Use bullet points for lists
- Include code blocks for technical content
- Provide step-by-step instructions when needed
""",
            
            'code_generation.md': """# Code Generation Guidelines

## Best Practices
- Write clean, readable code with proper comments
- Follow language-specific conventions
- Include error handling where appropriate
- Provide explanation of complex logic

## Languages Supported
- Python, JavaScript, TypeScript, HTML/CSS
- Bash scripting and system automation
- SQL for database operations
- Configuration files (JSON, YAML, etc.)

## Code Quality
- Use meaningful variable names
- Implement proper error handling
- Include input validation
- Follow security best practices
""",
            
            'sd_prompting.md': """# Stable Diffusion Prompting Guide

## Effective Prompt Structure
- Start with main subject/concept
- Add descriptive adjectives
- Specify art style or technique
- Include quality and technical terms

## Quality Enhancers
- "highly detailed", "8k resolution"
- "professional photography", "studio lighting"
- "trending on artstation", "award winning"

## Style Keywords
- Photography: "portrait", "landscape", "macro"
- Art: "oil painting", "watercolor", "digital art"
- 3D: "rendered in blender", "octane render"

## Negative Prompts
- Common issues: "blurry", "low quality", "deformed"
- Unwanted elements: specify what to avoid
""",
            
            'resource_monitoring.md': """# Resource Monitoring Guidelines

## System Health Checks
- Monitor CPU and memory usage
- Track GPU utilization when available
- Watch for disk space limitations
- Monitor network connectivity

## Performance Optimization
- Unload unused models to save memory
- Adjust context length based on available resources
- Use appropriate model sizes for hardware tier
- Implement graceful degradation when resources are limited

## User Communication
- Inform users of resource constraints
- Suggest alternative approaches for resource-intensive tasks
- Provide clear error messages for resource issues
"""
        }
        
        for filename, content in instruction_templates.items():
            file_path = self.instructions_dir / filename
            if not file_path.exists():
                file_path.write_text(content, encoding='utf-8')
                logger.info(f"Created instruction file: {filename}")
    
    def get_instruction_file(self, filename: str) -> Optional[str]:
        """Get content of a specific instruction file"""
        file_path = self.instructions_dir / filename
        if file_path.exists():
            return file_path.read_text(encoding='utf-8')
        return None
    
    def update_instruction_file(self, filename: str, content: str) -> bool:
        """Update or create an instruction file"""
        try:
            file_path = self.instructions_dir / filename
            file_path.write_text(content, encoding='utf-8')
            
            # Clear related cache
            self._clear_cache_for_file(filename)
            
            logger.info(f"Updated instruction file: {filename}")
            return True
        except Exception as e:
            logger.error(f"Failed to update instruction file {filename}: {e}")
            return False
    
    def _clear_cache_for_file(self, filename: str):
        """Clear cache entries related to a specific file"""
        # Find which category this file belongs to
        for category, info in self.table_of_contents['categories'].items():
            if filename in info['files']:
                # Clear all cache entries for this category
                keys_to_remove = [key for key in self.cache.keys() if key.startswith(category)]
                for key in keys_to_remove:
                    del self.cache[key]
                break
    
    def get_table_of_contents(self) -> Dict[str, Any]:
        """Get the current table of contents"""
        return self.table_of_contents
    
    def clear_cache(self):
        """Clear the instruction cache"""
        self.cache.clear()
        logger.info("Context optimizer cache cleared")


# Global instance
_context_optimizer: Optional[ContextOptimizer] = None

def get_context_optimizer() -> ContextOptimizer:
    """Get or create the global Context Optimizer instance"""
    global _context_optimizer
    if _context_optimizer is None:
        _context_optimizer = ContextOptimizer()
    return _context_optimizer
