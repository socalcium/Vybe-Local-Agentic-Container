"""
Agent API endpoints for Vybe application.
Handles autonomous agent creation, management, and monitoring.
"""

import json
from flask import Blueprint, jsonify, request, current_app
from ..auth import test_mode_login_required, current_user
from typing import List, Dict, Any

from ..core.agent_manager import get_agent_manager
from ..logger import logger

# Create the agents API blueprint
agents_bp = Blueprint('agents', __name__, url_prefix='/agents')


@agents_bp.route('/create', methods=['POST'])
@test_mode_login_required
def create_agent():
    """Create a new autonomous agent"""
    try:
        # CSRF validation
        csrf_token = request.headers.get('X-CSRFToken')
        if not csrf_token:
            return jsonify({
                'success': False,
                'error': 'CSRF token required'
            }), 400
        
        data = request.get_json()
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                return jsonify({'error': 'Invalid JSON format'}), 400
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400

        objective = data.get('objective', '').strip()
        system_prompt = data.get('system_prompt', '').strip()
        authorized_tools = data.get('authorized_tools', [])

        if not objective:
            return jsonify({
                'success': False,
                'error': 'Objective is required'
            }), 400

        if not system_prompt:
            return jsonify({
                'success': False,
                'error': 'System prompt is required'
            }), 400

        if not authorized_tools:
            return jsonify({
                'success': False,
                'error': 'At least one authorized tool is required'
            }), 400

        # Sanitize and validate inputs
        import html
        objective = html.escape(objective)
        system_prompt = html.escape(system_prompt)
        
        if len(objective) > 2000:
            return jsonify({
                'success': False,
                'error': 'Objective too long (max 2000 characters)'
            }), 400
            
        if len(system_prompt) > 5000:
            return jsonify({
                'success': False,
                'error': 'System prompt too long (max 5000 characters)'
            }), 400
        
        # Validate authorized_tools is a list
        if not isinstance(authorized_tools, list):
            return jsonify({
                'success': False,
                'error': 'Authorized tools must be a list'
            }), 400

        # Create the agent
        agent_manager = get_agent_manager()
        agent_id = agent_manager.create_agent(
            objective=objective,
            system_prompt=system_prompt,
            authorized_tools=authorized_tools
        )

        return jsonify({
            'success': True,
            'agent_id': agent_id,
            'message': 'Agent created successfully'
        })

    except Exception as e:
        logger.error(f"Error creating agent: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agents_bp.route('/start/<agent_id>', methods=['POST'])
@test_mode_login_required
def start_agent(agent_id):
    """Start an autonomous agent"""
    try:
        # Validate agent ID
        if not agent_id or not isinstance(agent_id, str):
            return jsonify({
                'success': False,
                'error': 'Valid agent ID is required'
            }), 400
        
        # Check for conflicts - prevent multiple starts
        agent_manager = get_agent_manager()
        
        # Check if agent exists
        if not agent_manager.agent_exists(agent_id):
            return jsonify({
                'success': False,
                'error': 'Agent not found'
            }), 404
        
        # Check if agent is already running
        agent_status = agent_manager.get_agent_status(agent_id)
        if agent_status == 'executing':
            return jsonify({
                'success': False,
                'error': 'Agent is already running'
            }), 409  # Conflict status
        
        # Check if agent is in a transitional state
        if agent_status in ['planning', 'verifying']:
            return jsonify({
                'success': False,
                'error': f'Agent is currently {agent_status}'
            }), 409
        
        # Start the agent
        success = agent_manager.start_agent(agent_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Agent started successfully',
                'agent_id': agent_id
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to start agent'
            }), 500

    except Exception as e:
        logger.error(f"Error starting agent {agent_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agents_bp.route('/status/<agent_id>', methods=['GET'])
@test_mode_login_required
def get_agent_status(agent_id: str):
    """Get the status of a specific agent"""
    try:
        agent_manager = get_agent_manager()
        agent = agent_manager.get_agent(agent_id)
        
        if not agent:
            return jsonify({
                'success': False,
                'error': 'Agent not found'
            }), 404

        status = agent.get_status_summary()
        return jsonify({
            'success': True,
            'agent': status
        })

    except Exception as e:
        logger.error(f"Error getting agent status {agent_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agents_bp.route('/logs/<agent_id>', methods=['GET'])
@test_mode_login_required
def get_agent_logs(agent_id: str):
    """Get logs for a specific agent"""
    try:
        limit = request.args.get('limit', 50, type=int)
        
        agent_manager = get_agent_manager()
        logs = agent_manager.get_agent_logs(agent_id, limit)
        
        return jsonify({
            'success': True,
            'logs': logs
        })

    except Exception as e:
        logger.error(f"Error getting agent logs {agent_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agents_bp.route('/list', methods=['GET'])
@test_mode_login_required
def list_agents():
    """Get a list of all agents"""
    try:
        agent_manager = get_agent_manager()
        agents = agent_manager.get_all_agents()
        
        return jsonify({
            'success': True,
            'agents': agents
        })

    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agents_bp.route('/pause/<agent_id>', methods=['POST'])
@test_mode_login_required
def pause_agent(agent_id: str):
    """Pause an agent's execution"""
    try:
        agent_manager = get_agent_manager()
        
        if agent_manager.pause_agent(agent_id):
            return jsonify({
                'success': True,
                'message': f'Agent {agent_id} paused successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Agent not found'
            }), 404

    except Exception as e:
        logger.error(f"Error pausing agent {agent_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agents_bp.route('/resume/<agent_id>', methods=['POST'])
@test_mode_login_required
def resume_agent(agent_id: str):
    """Resume an agent's execution"""
    try:
        agent_manager = get_agent_manager()
        
        if agent_manager.resume_agent(agent_id):
            return jsonify({
                'success': True,
                'message': f'Agent {agent_id} resumed successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Agent not found'
            }), 404

    except Exception as e:
        logger.error(f"Error resuming agent {agent_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agents_bp.route('/stop/<agent_id>', methods=['POST'])
@test_mode_login_required
def stop_agent(agent_id: str):
    """Stop an agent's execution"""
    try:
        agent_manager = get_agent_manager()
        
        if agent_manager.stop_agent(agent_id):
            return jsonify({
                'success': True,
                'message': f'Agent {agent_id} stopped successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Agent not found'
            }), 404

    except Exception as e:
        logger.error(f"Error stopping agent {agent_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agents_bp.route('/available-tools', methods=['GET'])
@test_mode_login_required
def get_available_tools():
    """Get list of available AI tools for agent authorization"""
    try:
        # List of all available AI tools
        available_tools = [
            {
                'id': 'web_search',
                'name': 'Web Search',
                'description': 'Search the internet for information'
            },
            {
                'id': 'ai_generate_image',
                'name': 'Generate Images',
                'description': 'Create AI-generated images using Stable Diffusion'
            },
            {
                'id': 'ai_speak_text',
                'name': 'Text-to-Speech',
                'description': 'Convert text to speech audio'
            },
            {
                'id': 'ai_transcribe_audio',
                'name': 'Audio Transcription',
                'description': 'Transcribe audio files to text'
            },
            {
                'id': 'ai_list_files',
                'name': 'List Files',
                'description': 'List files in the workspace directory'
            },
            {
                'id': 'ai_read_file',
                'name': 'Read File',
                'description': 'Read contents of files in the workspace'
            },
            {
                'id': 'ai_write_file',
                'name': 'Write File',
                'description': 'Create or modify files in the workspace'
            },
            {
                'id': 'ai_delete_file',
                'name': 'Delete File',
                'description': 'Delete files from the workspace'
            },
            {
                'id': 'ai_query_rag',
                'name': 'Query Knowledge Base',
                'description': 'Search the RAG knowledge base for information'
            },
            {
                'id': 'ai_execute_python',
                'name': 'Execute Python Code',
                'description': 'Run Python code in a secure sandboxed environment'
            },
            {
                'id': 'ai_generate_video',
                'name': 'Generate Videos',
                'description': 'Create AI-generated videos using ComfyUI'
            },
            {
                'id': 'ai_store_agent_memory',
                'name': 'Store Memory',
                'description': 'Store information in long-term agent memory'
            },
            {
                'id': 'ai_retrieve_agent_memories',
                'name': 'Retrieve Memories',
                'description': 'Retrieve relevant past experiences from memory'
            },
            {
                'id': 'ai_get_memory_stats',
                'name': 'Memory Statistics',
                'description': 'Get statistics about the agent memory system'
            }
        ]
        
        return jsonify({
            'success': True,
            'tools': available_tools
        })

    except Exception as e:
        logger.error(f"Error getting available tools: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agents_bp.route('/system-prompts', methods=['GET'])
@test_mode_login_required
def get_system_prompts():
    """Get available system prompts for agent configuration"""
    try:
        from ..models import SystemPrompt
        
        prompts = SystemPrompt.query.all()
        prompt_list = []
        
        for prompt in prompts:
            prompt_list.append({
                'id': prompt.id,
                'name': prompt.name,
                'description': prompt.description or 'No description available',
                'content': prompt.content
            })
        
        # Seed defaults if none present
        if not prompt_list:
            defaults = [
                { 'name': 'General Assistant', 'description': 'Helpful, concise assistant', 'content': 'You are a helpful, concise assistant.' },
                { 'name': 'Coder', 'description': 'Code-focused assistant', 'content': 'You are a coding assistant. Provide code and explanations.' },
                { 'name': 'Analyst', 'description': 'Analysis and reasoning', 'content': 'You analyze and reason step-by-step, explaining clearly.' },
                { 'name': 'Summarizer', 'description': 'Summarize text', 'content': 'Summarize the provided content into key points.' },
                { 'name': 'Creative Writer', 'description': 'Story and creative writing', 'content': 'Write engaging, creative prose with clear style.' }
            ]
            try:
                for d in defaults:
                    # Create SystemPrompt using SQLAlchemy model pattern
                    sp = SystemPrompt()
                    sp.name = d['name']
                    sp.description = d['description']
                    sp.content = d['content']
                    sp.category = 'General'
                    sp.is_default = True
                    from ..models import db
                    db.session.add(sp)
                db.session.commit()
                prompts = SystemPrompt.query.all()
                prompt_list = [{
                    'id': p.id,
                    'name': p.name,
                    'description': p.description or 'No description available',
                    'content': p.content
                } for p in prompts]
            except Exception as _:
                # If seeding fails, fall back to an in-memory list
                prompt_list = defaults
        return jsonify({'success': True, 'prompts': prompt_list})

    except Exception as e:
        logger.error(f"Error getting system prompts: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agents_bp.route('/orchestrate/research-write', methods=['POST'])
@test_mode_login_required
def create_research_write_workflow():
    """Create a research and writing workflow with multiple agents"""
    try:
        data = request.get_json()
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                return jsonify({'error': 'Invalid JSON format'}), 400
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400

        topic = data.get('topic', '').strip()
        if not topic:
            return jsonify({
                'success': False,
                'error': 'Topic is required'
            }), 400

        agent_manager = get_agent_manager()
        orchestration_id = agent_manager.create_research_and_write_workflow(topic)
        
        # Start the orchestrated task
        if agent_manager.execute_orchestrated_task(orchestration_id):
            return jsonify({
                'success': True,
                'orchestration_id': orchestration_id,
                'message': f'Research and writing workflow started for: {topic}'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to start orchestrated task'
            }), 500

    except Exception as e:
        logger.error(f"Error creating research-write workflow: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agents_bp.route('/orchestrate/custom', methods=['POST'])
@test_mode_login_required
def create_custom_orchestration():
    """Create a custom multi-agent orchestration"""
    try:
        data = request.get_json()
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                return jsonify({'error': 'Invalid JSON format'}), 400
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400

        main_objective = data.get('main_objective', '').strip()
        sub_tasks = data.get('sub_tasks', [])

        if not main_objective:
            return jsonify({
                'success': False,
                'error': 'Main objective is required'
            }), 400

        if not sub_tasks or len(sub_tasks) < 2:
            return jsonify({
                'success': False,
                'error': 'At least 2 sub-tasks are required for orchestration'
            }), 400

        agent_manager = get_agent_manager()
        orchestration_id = agent_manager.create_orchestrated_task(main_objective, sub_tasks)
        
        # Start the orchestrated task
        if agent_manager.execute_orchestrated_task(orchestration_id):
            return jsonify({
                'success': True,
                'orchestration_id': orchestration_id,
                'message': f'Custom orchestration started: {main_objective}'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to start orchestrated task'
            }), 500

    except Exception as e:
        logger.error(f"Error creating custom orchestration: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agents_bp.route('/orchestrate/<orchestration_id>/status', methods=['GET'])
@test_mode_login_required
def get_orchestration_status(orchestration_id: str):
    """Get status of an orchestrated task"""
    try:
        agent_manager = get_agent_manager()
        status = agent_manager.get_orchestration_status(orchestration_id)
        
        if 'error' in status:
            return jsonify({
                'success': False,
                'error': status['error']
            }), 404
        
        return jsonify({
            'success': True,
            'orchestration': status
        })

    except Exception as e:
        logger.error(f"Error getting orchestration status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
