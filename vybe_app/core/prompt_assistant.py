"""
Transparent Prompt Assistant
============================
Interactive prompt improvement with user control and suggestion bubbles
"""

import json
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class PromptAssistant:
    """Manages transparent prompt improvement suggestions"""
    
    def __init__(self, manager_model: str = "phi3:mini"):
        self.manager_model = manager_model
        self.suggestion_history = []
        self.user_preferences = {
            "auto_suggest": True,
            "suggestion_types": ["clarity", "specificity", "context"],
            "preferred_style": "professional"
        }
    
    async def analyze_prompt(self, user_prompt: str, context: Optional[Dict] = None) -> Dict:
        """Analyze user prompt and generate improvement suggestions"""
        try:
            # Create analysis prompt for the manager model
            analysis_prompt = self._create_analysis_prompt(user_prompt, context)
            
            # Get suggestion from manager model
            # This would call your existing model API
            suggestion_result = await self._call_manager_model(analysis_prompt)
            
            # Parse and structure the suggestion
            suggestion = self._parse_suggestion_result(suggestion_result, user_prompt)
            
            # Store in history
            self.suggestion_history.append({
                "timestamp": datetime.now().isoformat(),
                "original_prompt": user_prompt,
                "suggestion": suggestion,
                "used": False  # Will be updated when user chooses
            })
            
            return suggestion
            
        except Exception as e:
            logger.error(f"Error analyzing prompt: {e}")
            return {
                "has_suggestion": False,
                "error": str(e)
            }
    
    def _create_analysis_prompt(self, user_prompt: str, context: Optional[Dict] = None) -> str:
        """Create the analysis prompt for the manager model"""
        
        analysis_template = f"""
You are a prompt improvement assistant. Analyze the following user prompt and suggest improvements.

Original prompt: "{user_prompt}"

Context: {json.dumps(context or {}, indent=2)}

Provide a JSON response with the following structure:
{{
    "needs_improvement": boolean,
    "improved_prompt": "enhanced version of the prompt",
    "improvements": [
        {{
            "type": "clarity|specificity|context|formatting",
            "description": "what was improved",
            "benefit": "why this helps"
        }}
    ],
    "confidence": 0.8,
    "reasoning": "brief explanation of the improvements"
}}

Focus on:
1. Making the prompt more specific and clear
2. Adding helpful context
3. Improving structure and formatting
4. Ensuring the request is complete

Only suggest improvements if they would meaningfully enhance the prompt. Minor wording changes don't count.
"""
        
        return analysis_template
    
    async def _call_manager_model(self, prompt: str) -> str:
        """Call the manager model for prompt analysis"""
        # This would integrate with your existing model calling infrastructure
        # For now, return a mock response structure
        
        # In real implementation, this would be something like:
        # from vybe_app.core.agent_manager import AgentManager
        # agent_manager = AgentManager()
        # return await agent_manager.call_model(self.manager_model, prompt)
        
        # Mock response for demonstration
        return """
{
    "needs_improvement": true,
    "improved_prompt": "Please provide a detailed explanation of how machine learning algorithms work, including: 1) the basic principles and concepts, 2) common types of algorithms (supervised, unsupervised, reinforcement learning), 3) real-world applications, and 4) key advantages and limitations. Format the response with clear headings and examples.",
    "improvements": [
        {
            "type": "specificity",
            "description": "Added specific topics to cover",
            "benefit": "Ensures comprehensive coverage of the subject"
        },
        {
            "type": "formatting",
            "description": "Requested structured format with headings",
            "benefit": "Makes the response easier to read and follow"
        },
        {
            "type": "context",
            "description": "Asked for examples and applications",
            "benefit": "Provides practical context and understanding"
        }
    ],
    "confidence": 0.85,
    "reasoning": "The original prompt was too vague. The improved version provides clear structure and specific requirements for a comprehensive response."
}
"""
    
    def _parse_suggestion_result(self, result: str, original_prompt: str) -> Dict:
        """Parse the manager model's suggestion result"""
        try:
            # Try to parse JSON response
            suggestion_data = json.loads(result.strip())
            
            # Validate required fields
            if not isinstance(suggestion_data, dict):
                raise ValueError("Invalid response format")
            
            # Structure the response
            return {
                "has_suggestion": suggestion_data.get("needs_improvement", False),
                "original_prompt": original_prompt,
                "improved_prompt": suggestion_data.get("improved_prompt", original_prompt),
                "improvements": suggestion_data.get("improvements", []),
                "confidence": suggestion_data.get("confidence", 0.5),
                "reasoning": suggestion_data.get("reasoning", ""),
                "timestamp": datetime.now().isoformat()
            }
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Error parsing suggestion result: {e}")
            
            # Fallback: try to extract improved prompt with simple heuristics
            return self._fallback_suggestion(original_prompt, result)
    
    def _fallback_suggestion(self, original_prompt: str, raw_result: str) -> Dict:
        """Fallback suggestion when JSON parsing fails"""
        # Simple heuristics to generate a basic suggestion
        has_suggestion = len(original_prompt.split()) < 10  # Very short prompts likely need improvement
        
        if has_suggestion:
            improved_prompt = f"Please provide a detailed response to: {original_prompt}. Include specific examples and explain your reasoning."
            
            return {
                "has_suggestion": True,
                "original_prompt": original_prompt,
                "improved_prompt": improved_prompt,
                "improvements": [
                    {
                        "type": "specificity",
                        "description": "Added request for details and examples",
                        "benefit": "Helps get more comprehensive and useful responses"
                    }
                ],
                "confidence": 0.6,
                "reasoning": "Short prompts often benefit from additional specificity and context",
                "timestamp": datetime.now().isoformat()
            }
        
        return {
            "has_suggestion": False,
            "original_prompt": original_prompt
        }
    
    def record_user_choice(self, suggestion_id: str, used_suggestion: bool, final_prompt: str):
        """Record whether the user used the suggestion"""
        # Find the suggestion in history
        for entry in self.suggestion_history:
            if entry.get("id") == suggestion_id or entry["timestamp"] == suggestion_id:
                entry["used"] = used_suggestion
                entry["final_prompt"] = final_prompt
                entry["choice_timestamp"] = datetime.now().isoformat()
                break
    
    def get_suggestion_stats(self) -> Dict:
        """Get statistics about suggestion usage"""
        total_suggestions = len(self.suggestion_history)
        used_suggestions = sum(1 for entry in self.suggestion_history if entry.get("used", False))
        
        return {
            "total_suggestions": total_suggestions,
            "used_suggestions": used_suggestions,
            "acceptance_rate": used_suggestions / total_suggestions if total_suggestions > 0 else 0,
            "recent_suggestions": self.suggestion_history[-10:]  # Last 10
        }
    
    def update_preferences(self, preferences: Dict):
        """Update user preferences for suggestions"""
        self.user_preferences.update(preferences)
        logger.info(f"Updated prompt assistant preferences: {preferences}")


class TransparentPromptHandler:
    """Handles the transparent prompt flow in chat interface"""
    
    def __init__(self):
        self.assistant = PromptAssistant()
        self.pending_suggestions = {}  # Store suggestions waiting for user decision
    
    async def process_user_message(self, user_message: str, session_id: str, context: Optional[Dict] = None) -> Dict:
        """Process user message and generate suggestion if needed"""
        
        # Check if user wants suggestions
        if not self.assistant.user_preferences.get("auto_suggest", True):
            return {
                "type": "direct_response",
                "message": user_message
            }
        
        # Analyze the prompt
        suggestion = await self.assistant.analyze_prompt(user_message, context)
        
        if not suggestion.get("has_suggestion", False):
            # No improvement needed, proceed with original
            return {
                "type": "direct_response",
                "message": user_message
            }
        
        # Store suggestion for this session
        suggestion_id = f"{session_id}_{datetime.now().timestamp()}"
        self.pending_suggestions[suggestion_id] = suggestion
        
        # Return suggestion bubble data
        return {
            "type": "suggestion_bubble",
            "suggestion_id": suggestion_id,
            "original_message": user_message,
            "suggested_message": suggestion["improved_prompt"],
            "improvements": suggestion["improvements"],
            "confidence": suggestion["confidence"],
            "reasoning": suggestion["reasoning"]
        }
    
    def handle_user_choice(self, suggestion_id: str, choice: str) -> Optional[str]:
        """Handle user's choice on suggestion (use/keep_original)"""
        
        if suggestion_id not in self.pending_suggestions:
            return None
        
        suggestion = self.pending_suggestions[suggestion_id]
        
        if choice == "use_suggestion":
            final_prompt = suggestion["improved_prompt"]
            self.assistant.record_user_choice(suggestion_id, True, final_prompt)
        else:  # keep_original
            final_prompt = suggestion["original_prompt"]
            self.assistant.record_user_choice(suggestion_id, False, final_prompt)
        
        # Clean up
        del self.pending_suggestions[suggestion_id]
        
        return final_prompt
    
    def get_stats(self) -> Dict:
        """Get suggestion statistics"""
        return self.assistant.get_suggestion_stats()


# Global instance
transparent_prompt_handler = TransparentPromptHandler()
