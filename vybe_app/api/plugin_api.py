"""
Plugin API
Provides endpoints for managing the plugin system
"""

from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Any
import json

from ..core.plugin_manager import plugin_manager, PluginType, PluginStatus
from ..logger import log_info, log_error, log_api_request
from ..auth import test_mode_login_required, current_user

# Create plugin API blueprint
plugin_bp = Blueprint('plugin', __name__, url_prefix='/plugin')


@plugin_bp.route('/api/plugins/status', methods=['GET'])
@test_mode_login_required
def get_plugins_status():
    """Get status of all plugins"""
    try:
        plugins_status = plugin_manager.get_all_plugins_status()
        
        log_api_request('plugins_status', 'GET')
        return jsonify({
            'success': True,
            'plugins': plugins_status,
            'total_plugins': len(plugins_status),
            'active_plugins': len([p for p in plugins_status if p.get('status') == 'active']),
            'disabled_plugins': len([p for p in plugins_status if p.get('status') == 'disabled'])
        })
        
    except Exception as e:
        log_error(f"Error getting plugins status: {e}")
        return jsonify({'error': 'Failed to get plugins status'}), 500


@plugin_bp.route('/api/plugins/discover', methods=['POST'])
@test_mode_login_required
def discover_plugins():
    """Discover new plugins in the plugins directory"""
    try:
        discovered = plugin_manager.discover_plugins()
        
        log_api_request('plugins_discover', {'discovered_count': len(discovered)})
        return jsonify({
            'success': True,
            'discovered_plugins': discovered,
            'message': f'Discovered {len(discovered)} plugins'
        })
        
    except Exception as e:
        log_error(f"Error discovering plugins: {e}")
        return jsonify({'error': 'Failed to discover plugins'}), 500


@plugin_bp.route('/api/plugins/<plugin_id>/load', methods=['POST'])
@test_mode_login_required
def load_plugin(plugin_id):
    """Load a specific plugin"""
    try:
        success = plugin_manager.load_plugin(plugin_id)
        
        if success:
            log_api_request('plugin_load', {'plugin_id': plugin_id})
            return jsonify({
                'success': True,
                'message': f'Plugin {plugin_id} loaded successfully'
            })
        else:
            return jsonify({'error': f'Failed to load plugin {plugin_id}'}), 400
            
    except Exception as e:
        log_error(f"Error loading plugin {plugin_id}: {e}")
        return jsonify({'error': f'Failed to load plugin {plugin_id}'}), 500


@plugin_bp.route('/api/plugins/<plugin_id>/activate', methods=['POST'])
@test_mode_login_required
def activate_plugin(plugin_id):
    """Activate a plugin"""
    try:
        success = plugin_manager.activate_plugin(plugin_id)
        
        if success:
            log_api_request('plugin_activate', {'plugin_id': plugin_id})
            return jsonify({
                'success': True,
                'message': f'Plugin {plugin_id} activated successfully'
            })
        else:
            return jsonify({'error': f'Failed to activate plugin {plugin_id}'}), 400
            
    except Exception as e:
        log_error(f"Error activating plugin {plugin_id}: {e}")
        return jsonify({'error': f'Failed to activate plugin {plugin_id}'}), 500


@plugin_bp.route('/api/plugins/<plugin_id>/deactivate', methods=['POST'])
@test_mode_login_required
def deactivate_plugin(plugin_id):
    """Deactivate a plugin"""
    try:
        success = plugin_manager.deactivate_plugin(plugin_id)
        
        if success:
            log_api_request('plugin_deactivate', {'plugin_id': plugin_id})
            return jsonify({
                'success': True,
                'message': f'Plugin {plugin_id} deactivated successfully'
            })
        else:
            return jsonify({'error': f'Failed to deactivate plugin {plugin_id}'}), 400
            
    except Exception as e:
        log_error(f"Error deactivating plugin {plugin_id}: {e}")
        return jsonify({'error': f'Failed to deactivate plugin {plugin_id}'}), 500


@plugin_bp.route('/api/plugins/<plugin_id>/enable', methods=['POST'])
@test_mode_login_required
def enable_plugin(plugin_id):
    """Enable a disabled plugin"""
    try:
        success = plugin_manager.enable_plugin(plugin_id)
        
        if success:
            log_api_request('plugin_enable', {'plugin_id': plugin_id})
            return jsonify({
                'success': True,
                'message': f'Plugin {plugin_id} enabled successfully'
            })
        else:
            return jsonify({'error': f'Failed to enable plugin {plugin_id}'}), 400
            
    except Exception as e:
        log_error(f"Error enabling plugin {plugin_id}: {e}")
        return jsonify({'error': f'Failed to enable plugin {plugin_id}'}), 500


@plugin_bp.route('/api/plugins/<plugin_id>/disable', methods=['POST'])
@test_mode_login_required
def disable_plugin(plugin_id):
    """Disable a plugin"""
    try:
        success = plugin_manager.disable_plugin(plugin_id)
        
        if success:
            log_api_request('plugin_disable', {'plugin_id': plugin_id})
            return jsonify({
                'success': True,
                'message': f'Plugin {plugin_id} disabled successfully'
            })
        else:
            return jsonify({'error': f'Failed to disable plugin {plugin_id}'}), 400
            
    except Exception as e:
        log_error(f"Error disabling plugin {plugin_id}: {e}")
        return jsonify({'error': f'Failed to disable plugin {plugin_id}'}), 500


@plugin_bp.route('/api/plugins/<plugin_id>/unload', methods=['POST'])
@test_mode_login_required
def unload_plugin(plugin_id):
    """Unload a plugin completely"""
    try:
        success = plugin_manager.unload_plugin(plugin_id)
        
        if success:
            log_api_request('plugin_unload', {'plugin_id': plugin_id})
            return jsonify({
                'success': True,
                'message': f'Plugin {plugin_id} unloaded successfully'
            })
        else:
            return jsonify({'error': f'Failed to unload plugin {plugin_id}'}), 400
            
    except Exception as e:
        log_error(f"Error unloading plugin {plugin_id}: {e}")
        return jsonify({'error': f'Failed to unload plugin {plugin_id}'}), 500


@plugin_bp.route('/api/plugins/install', methods=['POST'])
@test_mode_login_required
def install_plugin():
    """Install a plugin from uploaded file"""
    try:
        from ..utils.input_validation import InputValidator, ValidationError
        
        if 'plugin_file' not in request.files:
            return jsonify({'error': 'No plugin file provided'}), 400
            
        file = request.files['plugin_file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Enhanced security validation using InputValidator
        try:
            # Validate file upload with comprehensive security checks
            file_info = InputValidator.validate_file_upload(
                'plugin_file',
                allowed_types=['archive', 'document'],  # Allow zip, tar, etc.
                max_size=50 * 1024 * 1024,  # 50MB limit for plugins
                required=True
            )
            
            if not file_info:
                return jsonify({'error': 'Invalid plugin file'}), 400
            
            # Additional security checks
            filename = file_info['filename']
            file_size = file_info['size']
            
            # Check for malicious file extensions
            if any(filename.lower().endswith(ext) for ext in ['.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js']):
                log_error(f"Blocked potentially malicious plugin file: {filename}")
                return jsonify({'error': 'Invalid plugin file type'}), 400
            
            # Check for path traversal attempts
            if '..' in filename or '/' in filename or '\\' in filename:
                log_error(f"Blocked path traversal attempt in plugin: {filename}")
                return jsonify({'error': 'Invalid filename'}), 400
            
            # Save uploaded file to temporary location with secure filename
            if not file.filename:
                return jsonify({'error': 'No filename provided'}), 400
            filename = secure_filename(file.filename)
            if not filename:
                return jsonify({'error': 'Invalid filename'}), 400
            temp_dir = tempfile.mkdtemp()
            temp_path = os.path.join(temp_dir, filename)
            file.save(temp_path)
            
        except ValidationError as e:
            log_error(f"Plugin file validation failed: {str(e)}")
            return jsonify({'error': f'Invalid plugin file: {str(e)}'}), 400
        except Exception as e:
            log_error(f"Plugin file processing error: {str(e)}")
            return jsonify({'error': 'Failed to process plugin file'}), 400
        
        # Install plugin
        success = plugin_manager.install_plugin(temp_path)
        
        # Cleanup temporary file
        os.remove(temp_path)
        os.rmdir(temp_dir)
        
        if success:
            log_api_request('plugin_install', {'filename': filename})
            return jsonify({
                'success': True,
                'message': f'Plugin installed successfully from {filename}'
            })
        else:
            return jsonify({'error': 'Failed to install plugin'}), 400
            
    except Exception as e:
        log_error(f"Error installing plugin: {e}")
        return jsonify({'error': 'Failed to install plugin'}), 500


@plugin_bp.route('/api/plugins/<plugin_id>/uninstall', methods=['POST'])
@test_mode_login_required
def uninstall_plugin(plugin_id):
    """Uninstall a plugin completely"""
    try:
        success = plugin_manager.uninstall_plugin(plugin_id)
        
        if success:
            log_api_request('plugin_uninstall', {'plugin_id': plugin_id})
            return jsonify({
                'success': True,
                'message': f'Plugin {plugin_id} uninstalled successfully'
            })
        else:
            return jsonify({'error': f'Failed to uninstall plugin {plugin_id}'}), 400
            
    except Exception as e:
        log_error(f"Error uninstalling plugin {plugin_id}: {e}")
        return jsonify({'error': f'Failed to uninstall plugin {plugin_id}'}), 500


@plugin_bp.route('/api/plugins/<plugin_id>/update', methods=['POST'])
@test_mode_login_required
def update_plugin(plugin_id):
    """Update a plugin from uploaded file"""
    try:
        from ..utils.input_validation import InputValidator, ValidationError
        
        if 'plugin_file' not in request.files:
            return jsonify({'error': 'No plugin file provided'}), 400
            
        file = request.files['plugin_file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Enhanced security validation using InputValidator
        try:
            # Validate file upload with comprehensive security checks
            file_info = InputValidator.validate_file_upload(
                'plugin_file',
                allowed_types=['archive', 'document'],  # Allow zip, tar, etc.
                max_size=50 * 1024 * 1024,  # 50MB limit for plugins
                required=True
            )
            
            if not file_info:
                return jsonify({'error': 'Invalid plugin file'}), 400
            
            # Additional security checks
            filename = file_info['filename']
            file_size = file_info['size']
            
            # Check for malicious file extensions
            if any(filename.lower().endswith(ext) for ext in ['.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js']):
                log_error(f"Blocked potentially malicious plugin file: {filename}")
                return jsonify({'error': 'Invalid plugin file type'}), 400
            
            # Check for path traversal attempts
            if '..' in filename or '/' in filename or '\\' in filename:
                log_error(f"Blocked path traversal attempt in plugin: {filename}")
                return jsonify({'error': 'Invalid filename'}), 400
            
            # Save uploaded file to temporary location with secure filename
            if not file.filename:
                return jsonify({'error': 'No filename provided'}), 400
            filename = secure_filename(file.filename)
            if not filename:
                return jsonify({'error': 'Invalid filename'}), 400
            temp_dir = tempfile.mkdtemp()
            temp_path = os.path.join(temp_dir, filename)
            file.save(temp_path)
            
        except ValidationError as e:
            log_error(f"Plugin file validation failed: {str(e)}")
            return jsonify({'error': f'Invalid plugin file: {str(e)}'}), 400
        except Exception as e:
            log_error(f"Plugin file processing error: {str(e)}")
            return jsonify({'error': 'Failed to process plugin file'}), 400
        
        # Update plugin
        success = plugin_manager.update_plugin(plugin_id, temp_path)
        
        # Cleanup temporary file
        os.remove(temp_path)
        os.rmdir(temp_dir)
        
        if success:
            log_api_request('plugin_update', {'plugin_id': plugin_id, 'filename': filename})
            return jsonify({
                'success': True,
                'message': f'Plugin {plugin_id} updated successfully'
            })
        else:
            return jsonify({'error': f'Failed to update plugin {plugin_id}'}), 400
            
    except Exception as e:
        log_error(f"Error updating plugin {plugin_id}: {e}")
        return jsonify({'error': f'Failed to update plugin {plugin_id}'}), 500


@plugin_bp.route('/api/plugins/tools', methods=['GET'])
@test_mode_login_required
def get_plugin_tools():
    """Get all available tools from plugins"""
    try:
        tools = plugin_manager.get_available_tools()
        
        log_api_request('plugin_tools', 'GET')
        return jsonify({
            'success': True,
            'tools': tools,
            'total_tools': len(tools)
        })
        
    except Exception as e:
        log_error(f"Error getting plugin tools: {e}")
        return jsonify({'error': 'Failed to get plugin tools'}), 500


@plugin_bp.route('/api/plugins/ui-components', methods=['GET'])
@test_mode_login_required
def get_plugin_ui_components():
    """Get all UI components from plugins"""
    try:
        components = plugin_manager.get_ui_components()
        
        log_api_request('plugin_ui_components', 'GET')
        return jsonify({
            'success': True,
            'components': components,
            'total_components': len(components)
        })
        
    except Exception as e:
        log_error(f"Error getting plugin UI components: {e}")
        return jsonify({'error': 'Failed to get plugin UI components'}), 500


@plugin_bp.route('/api/plugins/api-routes', methods=['GET'])
@test_mode_login_required
def get_plugin_api_routes():
    """Get all API routes from plugins"""
    try:
        routes = plugin_manager.get_api_routes()
        
        log_api_request('plugin_api_routes', 'GET')
        return jsonify({
            'success': True,
            'routes': routes,
            'total_routes': len(routes)
        })
        
    except Exception as e:
        log_error(f"Error getting plugin API routes: {e}")
        return jsonify({'error': 'Failed to get plugin API routes'}), 500


@plugin_bp.route('/api/plugins/marketplace', methods=['GET'])
@test_mode_login_required
def get_plugin_marketplace():
    """Get available plugins from marketplace (placeholder)"""
    try:
        # This would typically fetch from a remote marketplace
        # For now, return a placeholder response
        marketplace_plugins = [
            {
                'id': 'example-tool-plugin',
                'name': 'Example Tool Plugin',
                'description': 'A sample tool plugin for demonstration',
                'author': 'Vybe Team',
                'version': '1.0.0',
                'type': 'tool',
                'download_url': 'https://example.com/plugins/example-tool-plugin.zip',
                'rating': 4.5,
                'downloads': 1234,
                'tags': ['tool', 'example', 'demo']
            },
            {
                'id': 'ui-extension-demo',
                'name': 'UI Extension Demo',
                'description': 'Demonstrates UI extension capabilities',
                'author': 'Vybe Team',
                'version': '1.0.0',
                'type': 'ui_extension',
                'download_url': 'https://example.com/plugins/ui-extension-demo.zip',
                'rating': 4.2,
                'downloads': 567,
                'tags': ['ui', 'extension', 'demo']
            }
        ]
        
        log_api_request('plugin_marketplace', 'GET')
        return jsonify({
            'success': True,
            'plugins': marketplace_plugins,
            'total_plugins': len(marketplace_plugins)
        })
        
    except Exception as e:
        log_error(f"Error getting plugin marketplace: {e}")
        return jsonify({'error': 'Failed to get plugin marketplace'}), 500


@plugin_bp.route('/api/plugins/<plugin_id>/info', methods=['GET'])
@test_mode_login_required
def get_plugin_info(plugin_id):
    """Get detailed information about a specific plugin"""
    try:
        plugin_status = plugin_manager.get_plugin_status(plugin_id)
        
        if not plugin_status:
            return jsonify({'error': f'Plugin {plugin_id} not found'}), 404
            
        log_api_request('plugin_info', {'plugin_id': plugin_id})
        return jsonify({
            'success': True,
            'plugin': plugin_status
        })
        
    except Exception as e:
        log_error(f"Error getting plugin info for {plugin_id}: {e}")
        return jsonify({'error': f'Failed to get plugin info for {plugin_id}'}), 500


@plugin_bp.route('/api/plugins/settings', methods=['GET'])
@test_mode_login_required
def get_plugin_settings():
    """Get global plugin system settings"""
    try:
        settings = {
            'plugins_directory': str(plugin_manager.plugins_dir),
            'auto_discovery': True,
            'auto_load_enabled': False,
            'plugin_validation': True,
            'sandbox_mode': True,
            'max_plugins': 100,
            'allowed_plugin_types': [pt.value for pt in PluginType],
            'plugin_permissions': {
                'file_access': False,
                'network_access': False,
                'system_access': False
            }
        }
        
        log_api_request('plugin_settings', 'GET')
        return jsonify({
            'success': True,
            'settings': settings
        })
        
    except Exception as e:
        log_error(f"Error getting plugin settings: {e}")
        return jsonify({'error': 'Failed to get plugin settings'}), 500


@plugin_bp.route('/api/plugins/settings', methods=['POST'])
@test_mode_login_required
def update_plugin_settings():
    """Update global plugin system settings"""
    try:
        data = request.get_json()
        
        # In a real implementation, you would save these settings
        # For now, we'll just return success
        
        log_api_request('plugin_settings_update', data)
        return jsonify({
            'success': True,
            'message': 'Plugin settings updated successfully'
        })
        
    except Exception as e:
        log_error(f"Error updating plugin settings: {e}")
        return jsonify({'error': 'Failed to update plugin settings'}), 500


@plugin_bp.route('/api/plugins/validate', methods=['POST'])
@test_mode_login_required
def validate_plugin():
    """Validate a plugin file before installation"""
    try:
        if 'plugin_file' not in request.files:
            return jsonify({'error': 'No plugin file provided'}), 400
            
        file = request.files['plugin_file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
            
        # Save uploaded file to temporary location
        if not file.filename:
            return jsonify({'error': 'No filename provided'}), 400
        filename = secure_filename(file.filename)
        if not filename:
            return jsonify({'error': 'Invalid filename'}), 400
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, filename)
        file.save(temp_path)
        
        # Validate plugin structure
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'plugin_info': {}
        }
        
        try:
            # Check if it's a zip file
            if filename.endswith('.zip'):
                import zipfile
                with zipfile.ZipFile(temp_path, 'r') as zip_ref:
                    # Check for manifest.json
                    if 'manifest.json' not in zip_ref.namelist():
                        validation_result['valid'] = False
                        validation_result['errors'].append('Missing manifest.json file')
                    else:
                        # Read and validate manifest
                        manifest_data = json.loads(zip_ref.read('manifest.json'))
                        validation_result['plugin_info'] = {
                            'name': manifest_data.get('name', 'Unknown'),
                            'version': manifest_data.get('version', '1.0.0'),
                            'author': manifest_data.get('author', 'Unknown'),
                            'type': manifest_data.get('type', 'custom')
                        }
                        
                        # Check required fields
                        required_fields = ['name', 'version', 'author', 'type']
                        for field in required_fields:
                            if field not in manifest_data:
                                validation_result['valid'] = False
                                validation_result['errors'].append(f'Missing required field: {field}')
                                
            else:
                validation_result['valid'] = False
                validation_result['errors'].append('Plugin must be a ZIP file')
                
        except Exception as e:
            validation_result['valid'] = False
            validation_result['errors'].append(f'Validation error: {str(e)}')
            
        # Cleanup temporary file
        os.remove(temp_path)
        os.rmdir(temp_dir)
        
        log_api_request('plugin_validate', {'filename': filename, 'valid': validation_result['valid']})
        return jsonify({
            'success': True,
            'validation': validation_result
        })
        
    except Exception as e:
        log_error(f"Error validating plugin: {e}")
        return jsonify({'error': 'Failed to validate plugin'}), 500
