"""
Fine-Tuning API for Vybe
Handles AI model fine-tuning with various libraries
"""

from flask import Blueprint, jsonify, request, current_app
from ..auth import test_mode_login_required, current_user
from typing import Dict, Any, Optional
import os
import json
from datetime import datetime

from ..logger import logger
from ..core.job_manager import JobManager

finetuning_bp = Blueprint('finetuning', __name__, url_prefix='/finetuning')


@finetuning_bp.route('/supported-methods', methods=['GET'])
@test_mode_login_required
def get_supported_methods():
    """Get list of supported fine-tuning methods and libraries"""
    try:
        methods = [
            {
                'id': 'unsloth',
                'name': 'Unsloth',
                'description': 'Fast and memory-efficient fine-tuning for Llama, Mistral, and other models',
                'supported_models': ['llama-2', 'llama-3', 'mistral', 'codellama', 'phi-3'],
                'requirements': ['unsloth', 'torch', 'transformers'],
                'gpu_required': True
            },
            {
                'id': 'axolotl',
                'name': 'Axolotl',
                'description': 'Comprehensive fine-tuning framework with extensive configuration options',
                'supported_models': ['llama', 'mistral', 'qwen', 'phi', 'gemma'],
                'requirements': ['axolotl', 'accelerate', 'deepspeed'],
                'gpu_required': True
            },
            {
                'id': 'lora',
                'name': 'LoRA (Low-Rank Adaptation)',
                'description': 'Parameter-efficient fine-tuning using low-rank adapters',
                'supported_models': ['most_huggingface_models'],
                'requirements': ['peft', 'transformers', 'torch'],
                'gpu_required': False
            }
        ]
        
        return jsonify({
            'success': True,
            'methods': methods
        })
        
    except Exception as e:
        logger.error(f"Error getting supported fine-tuning methods: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@finetuning_bp.route('/check-requirements', methods=['POST'])
@test_mode_login_required
def check_requirements():
    """Check if requirements for a fine-tuning method are met"""
    try:
        data = request.get_json()
        method = data.get('method')
        
        if not method:
            return jsonify({
                'success': False,
                'error': 'Method is required'
            }), 400
        
        # Check system requirements
        # Check if PyTorch is available using our stub system
        from ..utils.stub_implementations import get_torch
        torch = get_torch()
        torch_available = torch is not None and not hasattr(torch, '_is_stub')
            
        if not torch_available:
            return jsonify({
                'success': False,
                'error': 'PyTorch not available - please install torch to use fine-tuning'
            }), 503
        import pkg_resources
        
        requirements_check = {
            'gpu_available': torch.cuda.is_available() if torch else False,
            'gpu_count': torch.cuda.device_count() if torch and torch.cuda.is_available() else 0,
            'cuda_version': torch.version.cuda if torch and torch.cuda.is_available() else None,
            'torch_version': torch.__version__ if torch else 'Not installed',
            'installed_packages': {}
        }
        
        # Check specific package requirements based on method
        required_packages = {
            'unsloth': ['unsloth', 'transformers', 'torch', 'accelerate'],
            'axolotl': ['axolotl', 'transformers', 'torch', 'accelerate', 'deepspeed'],
            'lora': ['peft', 'transformers', 'torch', 'accelerate']
        }
        
        packages_to_check = required_packages.get(method, [])
        
        for package in packages_to_check:
            try:
                version = pkg_resources.get_distribution(package).version
                requirements_check['installed_packages'][package] = version
            except pkg_resources.DistributionNotFound:
                requirements_check['installed_packages'][package] = None
        
        # Determine if ready for fine-tuning
        missing_packages = [pkg for pkg, version in requirements_check['installed_packages'].items() if version is None]
        requirements_check['ready'] = len(missing_packages) == 0
        requirements_check['missing_packages'] = missing_packages
        
        return jsonify({
            'success': True,
            'requirements': requirements_check
        })
        
    except Exception as e:
        logger.error(f"Error checking fine-tuning requirements: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@finetuning_bp.route('/prepare-dataset', methods=['POST'])
@test_mode_login_required
def prepare_dataset():
    """Validate and prepare a dataset for fine-tuning"""
    try:
        data = request.get_json()
        dataset_text = data.get('dataset_text', '').strip()
        dataset_format = data.get('format', 'prompt_completion')  # or 'alpaca', 'chatml'
        
        if not dataset_text:
            return jsonify({
                'success': False,
                'error': 'Dataset text is required'
            }), 400
        
        # Parse and validate dataset based on format
        parsed_data = []
        
        if dataset_format == 'prompt_completion':
            # Expected format: "prompt: text\ncompletion: text\n\n"
            entries = dataset_text.split('\n\n')
            for i, entry in enumerate(entries):
                if not entry.strip():
                    continue
                    
                lines = entry.strip().split('\n')
                prompt_line = None
                completion_line = None
                
                for line in lines:
                    if line.startswith('prompt:'):
                        prompt_line = line[7:].strip()
                    elif line.startswith('completion:'):
                        completion_line = line[11:].strip()
                
                if prompt_line and completion_line:
                    parsed_data.append({
                        'prompt': prompt_line,
                        'completion': completion_line
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': f'Invalid format in entry {i+1}. Expected "prompt:" and "completion:" lines.'
                    }), 400
        
        elif dataset_format == 'alpaca':
            # Expected format: JSON with instruction, input, output
            try:
                json_data = json.loads(dataset_text)
                if isinstance(json_data, list):
                    for item in json_data:
                        if 'instruction' in item and 'output' in item:
                            prompt = item['instruction']
                            if 'input' in item and item['input']:
                                prompt += f"\n\nInput: {item['input']}"
                            parsed_data.append({
                                'prompt': prompt,
                                'completion': item['output']
                            })
                else:
                    return jsonify({
                        'success': False,
                        'error': 'Alpaca format should be a JSON array'
                    }), 400
            except json.JSONDecodeError as e:
                return jsonify({
                    'success': False,
                    'error': f'Invalid JSON format: {e}'
                }), 400
        
        # Save prepared dataset
        workspace_dir = current_app.config.get('WORKSPACE_DIR', 'workspace')
        datasets_dir = os.path.join(workspace_dir, 'datasets')
        os.makedirs(datasets_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        dataset_filename = f'dataset_{timestamp}.json'
        dataset_path = os.path.join(datasets_dir, dataset_filename)
        
        with open(dataset_path, 'w', encoding='utf-8') as f:
            json.dump(parsed_data, f, indent=2, ensure_ascii=False)
        
        return jsonify({
            'success': True,
            'dataset_info': {
                'filename': dataset_filename,
                'path': dataset_path,
                'entries_count': len(parsed_data),
                'format': dataset_format,
                'sample_entry': parsed_data[0] if parsed_data else None
            }
        })
        
    except Exception as e:
        logger.error(f"Error preparing dataset: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@finetuning_bp.route('/start', methods=['POST'])
@test_mode_login_required
def start_finetuning():
    """Start a fine-tuning job"""
    try:
        data = request.get_json()
        
        # Required parameters
        method = data.get('method')
        base_model = data.get('base_model')
        dataset_filename = data.get('dataset_filename')
        output_name = data.get('output_name', 'custom_model')
        
        # Optional parameters with defaults
        config = {
            'learning_rate': data.get('learning_rate', 2e-5),
            'batch_size': data.get('batch_size', 4),
            'num_epochs': data.get('num_epochs', 3),
            'max_seq_length': data.get('max_seq_length', 2048),
            'lora_rank': data.get('lora_rank', 16),
            'lora_alpha': data.get('lora_alpha', 32)
        }
        
        if not all([method, base_model, dataset_filename]):
            return jsonify({
                'success': False,
                'error': 'Method, base_model, and dataset_filename are required'
            }), 400
        
        # Validate dataset exists
        workspace_dir = current_app.config.get('WORKSPACE_DIR', 'workspace')
        dataset_path = os.path.join(workspace_dir, 'datasets', dataset_filename)
        
        if not os.path.exists(dataset_path):
            return jsonify({
                'success': False,
                'error': f'Dataset file not found: {dataset_filename}'
            }), 404
        
        # Create fine-tuning job
        from ..core.agent_manager import get_agent_manager
        agent_manager = get_agent_manager()
        
        finetuning_objective = f"Fine-tune {base_model} using {method} with dataset {dataset_filename}"
        
        # Create specialized fine-tuning agent
        agent_id = agent_manager.create_agent(
            objective=finetuning_objective,
            system_prompt=f"""You are a specialized AI model fine-tuning agent. Your task is to fine-tune the model {base_model} using the {method} method.

Dataset: {dataset_path}
Output model name: {output_name}
Configuration: {json.dumps(config, indent=2)}

Steps to complete:
1. Load and validate the dataset
2. Set up the fine-tuning environment
3. Initialize the base model and tokenizer
4. Configure the training parameters
5. Start the fine-tuning process
6. Monitor training progress
7. Save the fine-tuned model
8. Generate a training report

Use the available tools to execute this fine-tuning workflow.""",
            authorized_tools=['ai_execute_code', 'ai_write_file', 'ai_read_file', 'ai_list_files']
        )
        
        # Start the fine-tuning agent
        if agent_manager.start_agent(agent_id):
            # Register for completion notification
            agent_manager._send_notification(
                f"🔧 Fine-tuning started: {base_model} → {output_name}",
                agent_id
            )
            
            return jsonify({
                'success': True,
                'agent_id': agent_id,
                'message': 'Fine-tuning job started successfully',
                'config': config
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to start fine-tuning agent'
            }), 500
        
    except Exception as e:
        logger.error(f"Error starting fine-tuning: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@finetuning_bp.route('/jobs', methods=['GET'])
@test_mode_login_required
def list_finetuning_jobs():
    """List all fine-tuning jobs (agents)"""
    try:
        from ..core.agent_manager import get_agent_manager
        agent_manager = get_agent_manager()
        
        # Filter agents that are fine-tuning jobs
        finetuning_jobs = []
        for agent_id, agent in agent_manager.agents.items():
            if 'fine-tune' in agent.objective.lower():
                finetuning_jobs.append({
                    'agent_id': agent_id,
                    'objective': agent.objective,
                    'status': agent.status.value,
                    'created_at': agent.created_at.isoformat(),
                    'started_at': agent.started_at.isoformat() if agent.started_at else None,
                    'completed_at': agent.completed_at.isoformat() if agent.completed_at else None
                })
        
        return jsonify({
            'success': True,
            'jobs': finetuning_jobs
        })
        
    except Exception as e:
        logger.error(f"Error listing fine-tuning jobs: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@finetuning_bp.route('/job/<agent_id>/status', methods=['GET'])
@test_mode_login_required
def get_finetuning_job_status(agent_id: str):
    """Get detailed status of a fine-tuning job"""
    try:
        from ..core.agent_manager import get_agent_manager
        agent_manager = get_agent_manager()
        
        if agent_id not in agent_manager.agents:
            return jsonify({
                'success': False,
                'error': 'Fine-tuning job not found'
            }), 404
        
        agent = agent_manager.agents[agent_id]
        
        # Get recent actions for progress tracking
        recent_actions = agent.memory.get_recent_actions(10)
        
        return jsonify({
            'success': True,
            'job': {
                'agent_id': agent_id,
                'objective': agent.objective,
                'status': agent.status.value,
                'created_at': agent.created_at.isoformat(),
                'started_at': agent.started_at.isoformat() if agent.started_at else None,
                'completed_at': agent.completed_at.isoformat() if agent.completed_at else None,
                'recent_actions': [
                    {
                        'timestamp': action.timestamp,
                        'action_type': action.action_type,
                        'tool_name': action.tool_name,
                        'success': action.success,
                        'result': action.result[:200] + '...' if action.result and len(action.result) > 200 else action.result
                    }
                    for action in recent_actions
                ]
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting fine-tuning job status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
