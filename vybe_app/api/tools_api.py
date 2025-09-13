"""
Tools API module - handles tool configuration endpoints.
"""

from flask import Blueprint, request, jsonify
from ..auth import test_mode_login_required, current_user
from ..models import db, AppSetting
from ..logger import log_error, log_api_request, log_user_action

# Create tools sub-blueprint
tools_bp = Blueprint('tools', __name__, url_prefix='/tools')

@tools_bp.route('', methods=['GET'])
@test_mode_login_required
def api_tools():
    """Get available tools configuration"""
    log_api_request(request.endpoint, request.method)
    try:
        # For now, return a static list of available tools
        tools = [
            {
                'name': 'web_search',
                'display_name': 'Web Search',
                'description': 'Search the internet for current information',
                'enabled': True
            },
            {
                'name': 'file_management',
                'display_name': 'File Management',
                'description': 'Manage files in workspace directory',
                'enabled': True
            },
            {
                'name': 'rag_query',
                'display_name': 'RAG Knowledge Base',
                'description': 'Query specialized knowledge collections',
                'enabled': True
            }
        ]
        
        # Check database for tool settings
        for tool in tools:
            setting = AppSetting.query.filter_by(key=f'tool_{tool["name"]}_enabled').first()
            if setting:
                tool['enabled'] = setting.value.lower() == 'true'
        
        return jsonify(tools)
        
    except Exception as e:
        log_error(f"Tools API error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@tools_bp.route('/toggle', methods=['POST'])
@test_mode_login_required
def api_toggle_tool():
    """Toggle a tool's enabled status"""
    log_api_request(request.endpoint, request.method)
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data is required'}), 400
            
        tool_name = data.get('tool_name')
        enabled = data.get('enabled', False)
        
        if not tool_name:
            return jsonify({'error': 'Tool name is required'}), 400
        
        # Validate tool name
        valid_tools = ['web_search', 'file_management', 'rag_query', 'image_generation', 'audio_processing']
        if tool_name not in valid_tools:
            return jsonify({'error': f'Invalid tool name. Must be one of: {", ".join(valid_tools)}'}), 400
        
        # Validate enabled parameter
        if not isinstance(enabled, bool):
            try:
                enabled = bool(enabled)
            except (ValueError, TypeError):
                return jsonify({'error': 'Enabled parameter must be a boolean'}), 400
        
        # Save tool setting
        setting_key = f'tool_{tool_name}_enabled'
        setting = AppSetting.query.filter_by(key=setting_key).first()
        if setting:
            setting.value = 'true' if enabled else 'false'
        else:
            setting = AppSetting()
            setting.key = setting_key
            setting.value = 'true' if enabled else 'false'
            db.session.add(setting)
        
        db.session.commit()
        log_user_action(current_user.id, f"{'Enabled' if enabled else 'Disabled'} tool: {tool_name}")
        
        return jsonify({'success': True, 'tool_name': tool_name, 'enabled': enabled})
        
    except Exception as e:
        log_error(f"Toggle tool API error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
