"""
Code Interpreter API
RESTful API for secure Python code execution
"""

from flask import Blueprint, request, jsonify, session
from typing import Dict, Any, Optional
import logging
import uuid
import threading
from datetime import datetime

from ..core.code_interpreter import (
    SecureCodeInterpreter, 
    SecuritySettings, 
    CodeExecutionResult,
    get_code_interpreter,
    cleanup_interpreter
)
from ..core.job_manager import JobManager

logger = logging.getLogger(__name__)

code_api = Blueprint('code_api', __name__, url_prefix='/api/code')

# Thread-safe session management
active_sessions: Dict[str, Dict[str, Any]] = {}
active_sessions_lock = threading.Lock()

@code_api.route('/session', methods=['POST'])
def create_session():
    """Create a new code interpreter session"""
    try:
        data = request.get_json() or {}
        
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        # Parse security settings
        security_config = data.get('security', {})
        security_settings = SecuritySettings(
            allow_file_io=security_config.get('allow_file_io', True),
            allow_network=security_config.get('allow_network', False),
            allow_subprocess=security_config.get('allow_subprocess', False),
            max_execution_time=security_config.get('max_execution_time', 30.0),
            max_memory_mb=security_config.get('max_memory_mb', 512),
            workspace_dir=security_config.get('workspace_dir')
        )
        
        # Create interpreter
        interpreter = get_code_interpreter(session_id, security_settings)
        
        # Store session info (thread-safe)
        session_info = {
            "created_at": datetime.now().isoformat(),
            "last_used": datetime.now().isoformat(),
            "executions_count": 0,
            "security_settings": {
                "allow_file_io": security_settings.allow_file_io,
                "allow_network": security_settings.allow_network,
                "allow_subprocess": security_settings.allow_subprocess,
                "max_execution_time": security_settings.max_execution_time,
                "max_memory_mb": security_settings.max_memory_mb
            }
        }
        
        with active_sessions_lock:
            active_sessions[session_id] = session_info
        
        logger.info(f"Created code interpreter session: {session_id}")
        
        return jsonify({
            "success": True,
            "session_id": session_id,
            "workspace_dir": interpreter.workspace_dir,
            "security_settings": session_info["security_settings"]
        })
        
    except Exception as e:
        logger.error(f"Failed to create code session: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@code_api.route('/session/<session_id>', methods=['DELETE'])
def delete_session(session_id: str):
    """Delete a code interpreter session"""
    try:
        session_exists = False
        with active_sessions_lock:
            if session_id in active_sessions:
                session_exists = True
                del active_sessions[session_id]
        
        if session_exists:
            cleanup_interpreter(session_id)
            logger.info(f"Deleted code interpreter session: {session_id}")
            
        return jsonify({
            "success": True,
            "message": "Session deleted successfully"
        })
        
    except Exception as e:
        logger.error(f"Failed to delete session {session_id}: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@code_api.route('/session/<session_id>/info', methods=['GET'])
def get_session_info(session_id: str):
    """Get information about a code interpreter session"""
    try:
        with active_sessions_lock:
            if session_id not in active_sessions:
                return jsonify({
                    "success": False,
                    "error": "Session not found"
                }), 404
            
            session_info = active_sessions[session_id].copy()
        
        interpreter = get_code_interpreter(session_id)
        
        return jsonify({
            "success": True,
            "session_id": session_id,
            "session_info": session_info,
            "workspace_dir": interpreter.workspace_dir,
            "workspace_files": interpreter.get_workspace_files()
        })
        
    except Exception as e:
        logger.error(f"Failed to get session info for {session_id}: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@code_api.route('/execute', methods=['POST'])
def execute_code():
    """Execute Python code"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No JSON data provided"
            }), 400
        
        code = data.get('code')
        if not code:
            return jsonify({
                "success": False,
                "error": "No code provided"
            }), 400
        
        session_id = data.get('session_id')
        
        # Check session exists (thread-safe)
        with active_sessions_lock:
            if not session_id or session_id not in active_sessions:
                return jsonify({
                    "success": False,
                    "error": "Invalid or missing session_id"
                }), 400
        
        context = data.get('context', {})
        
        # Get interpreter
        interpreter = get_code_interpreter(session_id)
        
        # Execute code
        result = interpreter.execute_code(code, context)
        
        # Update session stats (thread-safe)
        with active_sessions_lock:
            active_sessions[session_id]["last_used"] = datetime.now().isoformat()
            active_sessions[session_id]["executions_count"] += 1
        
        logger.info(f"Code executed in session {session_id}: success={result.success}")
        
        return jsonify({
            "success": True,
            "execution_result": result.to_dict(),
            "session_id": session_id
        })
        
    except Exception as e:
        logger.error(f"Code execution failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@code_api.route('/execute_async', methods=['POST'])
def execute_code_async():
    """Execute Python code asynchronously using JobManager"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No JSON data provided"
            }), 400
        
        code = data.get('code')
        if not code:
            return jsonify({
                "success": False,
                "error": "No code provided"
            }), 400
        
        session_id = data.get('session_id')
        
        # Check session exists (thread-safe)
        with active_sessions_lock:
            if not session_id or session_id not in active_sessions:
                return jsonify({
                    "success": False,
                    "error": "Invalid or missing session_id"
                }), 400
        
        context = data.get('context', {})
        
        # Create background job
        job_manager = JobManager()
        
        def execute_code_job():
            interpreter = get_code_interpreter(session_id)
            result = interpreter.execute_code(code, context)
            
            # Update session stats (thread-safe)
            with active_sessions_lock:
                active_sessions[session_id]["last_used"] = datetime.now().isoformat()
                active_sessions[session_id]["executions_count"] += 1
            
            return result.to_dict()
        
        job_id = job_manager.add_job(
            execute_code_job
        )
        
        logger.info(f"Submitted async code execution job {job_id} for session {session_id}")
        
        return jsonify({
            "success": True,
            "job_id": job_id,
            "message": "Code execution started",
            "session_id": session_id
        })
        
    except Exception as e:
        logger.error(f"Async code execution failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@code_api.route('/session/<session_id>/stop', methods=['POST'])
def stop_execution(session_id: str):
    """Stop running code execution in a session"""
    try:
        with active_sessions_lock:
            if session_id not in active_sessions:
                return jsonify({
                    "success": False,
                    "error": "Session not found"
                }), 404
        
        interpreter = get_code_interpreter(session_id)
        interpreter.stop_execution()
        
        logger.info(f"Stopped code execution in session {session_id}")
        
        return jsonify({
            "success": True,
            "message": "Execution stopped"
        })
        
    except Exception as e:
        logger.error(f"Failed to stop execution in session {session_id}: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@code_api.route('/session/<session_id>/files', methods=['GET'])
def list_workspace_files(session_id: str):
    """List files in the session workspace"""
    try:
        with active_sessions_lock:
            if session_id not in active_sessions:
                return jsonify({
                    "success": False,
                    "error": "Session not found"
            }), 404
        
        interpreter = get_code_interpreter(session_id)
        files = interpreter.get_workspace_files()
        
        return jsonify({
            "success": True,
            "files": files
        })
        
    except Exception as e:
        logger.error(f"Failed to list files for session {session_id}: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@code_api.route('/session/<session_id>/files/<path:file_path>', methods=['GET'])
def get_file_content(session_id: str, file_path: str):
    """Get content of a file in the session workspace"""
    try:
        with active_sessions_lock:
            if session_id not in active_sessions:
                return jsonify({
                    "success": False,
                "error": "Session not found"
            }), 404
        
        interpreter = get_code_interpreter(session_id)
        content = interpreter.get_file_content(file_path)
        
        if content is None:
            return jsonify({
                "success": False,
                "error": "File not found or cannot be read"
            }), 404
        
        return jsonify({
            "success": True,
            "file_path": file_path,
            "content": content
        })
        
    except Exception as e:
        logger.error(f"Failed to get file content for {file_path} in session {session_id}: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@code_api.route('/sessions', methods=['GET'])
def list_sessions():
    """List all active code interpreter sessions"""
    try:
        with active_sessions_lock:
            sessions_copy = {
                session_id: {
                    **session_info,
                    "session_id": session_id
                }
                for session_id, session_info in active_sessions.items()
            }
        
        return jsonify({
            "success": True,
            "sessions": sessions_copy
        })
        
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@code_api.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    with active_sessions_lock:
        active_sessions_count = len(active_sessions)
    
    return jsonify({
        "success": True,
        "message": "Code interpreter API is healthy",
        "active_sessions": active_sessions_count,
        "timestamp": datetime.now().isoformat()
    })

# Error handlers
@code_api.errorhandler(400)
def bad_request(error):
    return jsonify({
        "success": False,
        "error": "Bad request",
        "details": str(error)
    }), 400

@code_api.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False,
        "error": "Not found",
        "details": str(error)
    }), 404

@code_api.errorhandler(500)
def internal_error(error):
    return jsonify({
        "success": False,
        "error": "Internal server error",
        "details": str(error)
    }), 500
