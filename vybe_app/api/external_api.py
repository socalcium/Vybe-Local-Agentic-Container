"""
External API Connectors for LLM Model Router
Handles OpenAI, Anthropic, and other external LLM providers
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required
from ..auth import test_mode_login_required
import requests
import os
from ..logger import log_error, log_api_request, handle_api_errors, log_execution_time

# Create external API sub-blueprint
external_api_bp = Blueprint('external_api', __name__, url_prefix='/external')

@external_api_bp.route('/providers', methods=['GET'])
@test_mode_login_required
@handle_api_errors
def get_available_providers():
    """Get list of available external API providers"""
    try:
        providers = [
            {
                'name': 'OpenAI',
                'id': 'openai',
                'models': ['gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo'],
                'status': 'available' if os.getenv('OPENAI_API_KEY') else 'needs_key'
            },
            {
                'name': 'Anthropic',
                'id': 'anthropic', 
                'models': ['claude-3-sonnet', 'claude-3-haiku', 'claude-3-opus'],
                'status': 'available' if os.getenv('ANTHROPIC_API_KEY') else 'needs_key'
            },
            {
                'name': 'Google',
                'id': 'google',
                'models': ['gemini-pro', 'gemini-pro-vision'],
                'status': 'available' if os.getenv('GOOGLE_API_KEY') else 'needs_key'
            },
            {
                'name': 'Local LLM',
                'id': 'local',
                'models': ['llama-cpp-python'],
                'status': 'available'
            }
        ]
        
        return jsonify({
            'success': True,
            'providers': providers
        })
        
    except Exception as e:
        log_error(f"Error getting providers: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@external_api_bp.route('/chat/completions', methods=['POST'])
@test_mode_login_required
@handle_api_errors
def external_chat_completion():
    """Route chat completion to appropriate external provider"""
    try:
        data = request.get_json()
        provider = data.get('provider', 'local')
        model = data.get('model', '')
        messages = data.get('messages', [])
        
        if not messages:
            return jsonify({
                'success': False,
                'error': 'Messages are required'
            }), 400
        
        if provider == 'openai':
            return _handle_openai_completion(model, messages, data)
        elif provider == 'anthropic':
            return _handle_anthropic_completion(model, messages, data)
        elif provider == 'google':
            return _handle_google_completion(model, messages, data)
        elif provider == 'local':
            return _handle_local_completion(model, messages, data)
        else:
            return jsonify({
                'success': False,
                'error': f'Unknown provider: {provider}'
            }), 400
            
    except Exception as e:
        log_error(f"Error in external chat completion: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def _handle_openai_completion(model, messages, data):
    """Handle OpenAI API completion"""
    try:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            return jsonify({
                'success': False,
                'error': 'OpenAI API key not configured'
            }), 401
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': model or 'gpt-3.5-turbo',
            'messages': messages,
            'max_tokens': data.get('max_tokens', 1000),
            'temperature': data.get('temperature', 0.7)
        }
        
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            return jsonify({
                'success': True,
                'provider': 'openai',
                'response': result.get('choices', [{}])[0].get('message', {}).get('content', ''),
                'usage': result.get('usage', {}),
                'model': result.get('model', model)
            })
        else:
            return jsonify({
                'success': False,
                'error': f'OpenAI API error: {response.status_code}',
                'details': response.text
            }), response.status_code
            
    except Exception as e:
        log_error(f"OpenAI completion error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def _handle_anthropic_completion(model, messages, data):
    """Handle Anthropic API completion"""
    try:
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            return jsonify({
                'success': False,
                'error': 'Anthropic API key not configured'
            }), 401
        
        headers = {
            'x-api-key': api_key,
            'Content-Type': 'application/json',
            'anthropic-version': '2023-06-01'
        }
        
        # Convert messages to Anthropic format
        system_message = ""
        user_messages = []
        
        for msg in messages:
            if msg.get('role') == 'system':
                system_message = msg.get('content', '')
            else:
                user_messages.append({
                    'role': msg.get('role', 'user'),
                    'content': msg.get('content', '')
                })
        
        payload = {
            'model': model or 'claude-3-sonnet-20240229',
            'messages': user_messages,
            'max_tokens': data.get('max_tokens', 1000),
            'temperature': data.get('temperature', 0.7)
        }
        
        if system_message:
            payload['system'] = system_message
        
        response = requests.post(
            'https://api.anthropic.com/v1/messages',
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result.get('content', [{}])[0].get('text', '')
            return jsonify({
                'success': True,
                'provider': 'anthropic',
                'response': content,
                'usage': result.get('usage', {}),
                'model': result.get('model', model)
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Anthropic API error: {response.status_code}',
                'details': response.text
            }), response.status_code
            
    except Exception as e:
        log_error(f"Anthropic completion error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def _handle_google_completion(model, messages, data):
    """Handle Google Gemini API completion"""
    try:
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            return jsonify({
                'success': False,
                'error': 'Google API key not configured'
            }), 401
        
        # Convert messages to Gemini format
        contents = []
        for msg in messages:
            if msg.get('role') != 'system':  # Gemini doesn't use system messages
                contents.append({
                    'parts': [{'text': msg.get('content', '')}],
                    'role': 'user' if msg.get('role') == 'user' else 'model'
                })
        
        payload = {
            'contents': contents,
            'generationConfig': {
                'maxOutputTokens': data.get('max_tokens', 1000),
                'temperature': data.get('temperature', 0.7)
            }
        }
        
        model_name = model or 'gemini-pro'
        url = f'https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}'
        
        response = requests.post(url, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            content = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
            return jsonify({
                'success': True,
                'provider': 'google',
                'response': content,
                'model': model_name
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Google API error: {response.status_code}',
                'details': response.text
            }), response.status_code
            
    except Exception as e:
        log_error(f"Google completion error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def _handle_local_completion(model, messages, data):
    """Handle local LLM completion"""
    try:
        from ..core.backend_llm_controller import llm_controller
        
        if not llm_controller.is_server_ready():
            return jsonify({
                'success': False,
                'error': 'Local LLM server not ready'
            }), 503
        
        # Convert messages to prompt format for local LLM
        prompt = ""
        system_prompt = None
        
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            
            if role == 'system':
                system_prompt = content
            elif role == 'user':
                prompt += f"User: {content}\n"
            elif role == 'assistant':
                prompt += f"Assistant: {content}\n"
        
        prompt += "Assistant: "
        
        try:
            response = llm_controller.generate_response(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=data.get('max_tokens', 1000),
                temperature=data.get('temperature', 0.7)
            )
            
            return jsonify({
                'success': True,
                'provider': 'local',
                'response': response,
                'model': llm_controller.model_path or 'local-llm'
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Local LLM error: {str(e)}'
            }), 500
            
    except Exception as e:
        log_error(f"Local completion error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@external_api_bp.route('/route', methods=['POST'])
@test_mode_login_required
@handle_api_errors
def intelligent_route():
    """Intelligently route request to best available model"""
    try:
        from ..core.model_router import model_router
        
        data = request.get_json()
        messages = data.get('messages', [])
        request_type = data.get('request_type', 'general')
        
        if not messages:
            return jsonify({
                'success': False,
                'error': 'Messages are required'
            }), 400
        
        # Route request through intelligent router
        result = model_router.route_request(
            messages=messages,
            request_type=request_type,
            max_tokens=data.get('max_tokens', 1000),
            temperature=data.get('temperature', 0.7),
            max_cost=data.get('max_cost'),
            min_speed=data.get('min_speed'),
            min_quality=data.get('min_quality')
        )
        
        return jsonify(result)
        
    except Exception as e:
        log_error(f"Intelligent routing error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@external_api_bp.route('/routing/stats', methods=['GET'])
@test_mode_login_required
@handle_api_errors
def get_routing_stats():
    """Get routing statistics and model performance"""
    try:
        from ..core.model_router import model_router
        stats = model_router.get_routing_stats()
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        log_error(f"Error getting routing stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@external_api_bp.route('/test/<provider>', methods=['POST'])
@test_mode_login_required
@handle_api_errors
def test_provider(provider):
    """Test connection to an external API provider"""
    try:
        test_messages = [
            {"role": "user", "content": "Hello, this is a test message. Please respond briefly."}
        ]
        
        # Make a test request using the same completion logic
        test_data = {
            'provider': provider,
            'model': '',
            'messages': test_messages,
            'max_tokens': 50,
            'temperature': 0.7
        }
        
        # Use internal completion handler
        if provider == 'openai':
            result = _handle_openai_completion('', test_messages, test_data)
        elif provider == 'anthropic':
            result = _handle_anthropic_completion('', test_messages, test_data)
        elif provider == 'google':
            result = _handle_google_completion('', test_messages, test_data)
        elif provider == 'local':
            result = _handle_local_completion('', test_messages, test_data)
        else:
            return jsonify({
                'success': False,
                'error': f'Unknown provider: {provider}'
            }), 400
        
        # Enhanced tuple response handling with comprehensive error checking
        try:
            if isinstance(result, tuple):
                # Handle Flask tuple response (response, status_code)
                response, status_code = result
                if hasattr(response, 'get_json'):
                    try:
                        result_data = response.get_json()
                    except Exception as json_error:
                        log_error(f"Failed to parse JSON from response: {json_error}")
                        result_data = {'success': False, 'error': 'Invalid JSON response'}
                else:
                    # If response doesn't have get_json, try to extract data directly
                    result_data = getattr(response, 'json', {}) if hasattr(response, 'json') else {}
            else:
                # Handle direct response object
                if hasattr(result, 'get_json'):
                    try:
                        result_data = result.get_json()
                    except Exception as json_error:
                        log_error(f"Failed to parse JSON from result: {json_error}")
                        result_data = {'success': False, 'error': 'Invalid JSON response'}
                elif hasattr(result, 'json'):
                    result_data = result.json
                elif isinstance(result, dict):
                    # Result is already a dictionary
                    result_data = result
                else:
                    log_error(f"Unexpected result type: {type(result)}")
                    result_data = {'success': False, 'error': 'Unexpected response format'}
        except Exception as parse_error:
            log_error(f"Error parsing response: {parse_error}")
            result_data = {'success': False, 'error': f'Response parsing error: {str(parse_error)}'}
        
        if result_data and result_data.get('success'):
            return jsonify({
                'success': True,
                'message': f'{provider.title()} API connection successful',
                'test_response': str(result_data.get('response', ''))[:100] + '...'
            })
        else:
            error_msg = 'Unknown error'
            if result_data and isinstance(result_data, dict):
                error_msg = result_data.get('error', 'Unknown error')
            return jsonify({
                'success': False,
                'error': error_msg
            })
    except Exception as e:
        log_error(f"Provider test error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
