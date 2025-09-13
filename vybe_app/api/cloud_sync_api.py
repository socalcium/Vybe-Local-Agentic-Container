"""
Cloud Sync API
Provides endpoints for managing cloud synchronization with major providers
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
from typing import Dict, List, Any
import json

from ..core.cloud_sync_manager import cloud_sync_manager, SyncItem, SyncConfig, SyncDirection, SyncStatus
from ..logger import log_info, log_error, log_api_request
from ..auth import test_mode_login_required, current_user
from ..config import Config

# Create cloud sync blueprint
cloud_sync_bp = Blueprint('cloud_sync', __name__, url_prefix='/cloud_sync')


@cloud_sync_bp.route('/api/cloud_sync/status', methods=['GET'])
@test_mode_login_required
def get_sync_status():
    """Get sync status for all providers or a specific provider"""
    try:
        provider = request.args.get('provider')
        status = cloud_sync_manager.get_sync_status(provider)
        
        log_api_request('cloud_sync_status', {'provider': provider})
        return jsonify({
            'success': True,
            'status': status
        })
        
    except Exception as e:
        log_error(f"Error getting sync status: {e}")
        return jsonify({'error': 'Failed to get sync status'}), 500


@cloud_sync_bp.route('/api/cloud_sync/providers', methods=['GET'])
@test_mode_login_required
def get_available_providers():
    """Get list of available cloud storage providers"""
    try:
        providers = {
            'gdrive': {
                'name': 'Google Drive',
                'description': 'Sync with Google Drive',
                'icon': 'bi bi-google',
                'available': True,
                'features': ['file_sync', 'folder_sync', 'selective_sync']
            },
            'dropbox': {
                'name': 'Dropbox',
                'description': 'Sync with Dropbox',
                'icon': 'bi bi-dropbox',
                'available': 'dropbox' in cloud_sync_manager.providers,
                'features': ['file_sync', 'folder_sync', 'selective_sync']
            },
            'onedrive': {
                'name': 'OneDrive',
                'description': 'Sync with Microsoft OneDrive',
                'icon': 'bi bi-microsoft',
                'available': 'onedrive' in cloud_sync_manager.providers,
                'features': ['file_sync', 'folder_sync', 'selective_sync']
            }
        }
        
        log_api_request('cloud_sync_providers', 'GET')
        return jsonify({
            'success': True,
            'providers': providers
        })
        
    except Exception as e:
        log_error(f"Error getting providers: {e}")
        return jsonify({'error': 'Failed to get providers'}), 500


@cloud_sync_bp.route('/api/cloud_sync/config/add', methods=['POST'])
@test_mode_login_required
def add_sync_config():
    """Add a new sync configuration"""
    try:
        data = request.get_json()
        
        provider = data.get('provider')
        credentials = data.get('credentials', {})
        sync_items_data = data.get('sync_items', [])
        
        if not provider:
            return jsonify({'error': 'Provider is required'}), 400
        
        # Convert sync items data to SyncItem objects
        sync_items = []
        for item_data in sync_items_data:
            sync_item = SyncItem(
                local_path=item_data.get('local_path'),
                remote_path=item_data.get('remote_path'),
                provider=provider,
                direction=SyncDirection(item_data.get('direction', 'bidirectional')),
                metadata=item_data.get('metadata', {})
            )
            sync_items.append(sync_item)
        
        # Add configuration
        success = cloud_sync_manager.add_sync_config(
            provider=provider,
            credentials=credentials,
            sync_items=sync_items,
            auto_sync=data.get('auto_sync', True),
            sync_interval=data.get('sync_interval', 300),
            max_file_size=data.get('max_file_size', 100 * 1024 * 1024),
            encryption_enabled=data.get('encryption_enabled', True),
            compression_enabled=data.get('compression_enabled', True),
            conflict_resolution=data.get('conflict_resolution', 'newer_wins')
        )
        
        if success:
            log_api_request('cloud_sync_config_add', 'POST')
            return jsonify({
                'success': True,
                'message': f'Sync configuration added for {provider}'
            })
        else:
            return jsonify({'error': 'Failed to add sync configuration'}), 500
        
    except Exception as e:
        log_error(f"Error adding sync config: {e}")
        return jsonify({'error': 'Failed to add sync configuration'}), 500


@cloud_sync_bp.route('/api/cloud_sync/config/remove', methods=['POST'])
@test_mode_login_required
def remove_sync_config():
    """Remove a sync configuration"""
    try:
        data = request.get_json()
        provider = data.get('provider')
        
        if not provider:
            return jsonify({'error': 'Provider is required'}), 400
        
        success = cloud_sync_manager.remove_sync_config(provider)
        
        if success:
            log_api_request('cloud_sync_config_remove', {'provider': provider})
            return jsonify({
                'success': True,
                'message': f'Sync configuration removed for {provider}'
            })
        else:
            return jsonify({'error': 'Failed to remove sync configuration'}), 500
        
    except Exception as e:
        log_error(f"Error removing sync config: {e}")
        return jsonify({'error': 'Failed to remove sync configuration'}), 500


@cloud_sync_bp.route('/api/cloud_sync/sync', methods=['POST'])
@test_mode_login_required
def sync_now():
    """Perform immediate sync"""
    try:
        data = request.get_json()
        provider = data.get('provider')  # Optional, sync all if not specified
        items = data.get('items')  # Optional, sync all items if not specified
        
        results = cloud_sync_manager.sync_now(provider, items)
        
        log_api_request('cloud_sync_now', {'provider': provider, 'items_count': len(items) if items else 'all'})
        return jsonify({
            'success': True,
            'results': results
        })
        
    except Exception as e:
        log_error(f"Error syncing: {e}")
        return jsonify({'error': 'Failed to sync'}), 500


@cloud_sync_bp.route('/api/cloud_sync/history', methods=['GET'])
@test_mode_login_required
def get_sync_history():
    """Get sync history"""
    try:
        limit = request.args.get('limit', 50, type=int)
        history = cloud_sync_manager.get_sync_history(limit)
        
        log_api_request('cloud_sync_history', {'limit': limit})
        return jsonify({
            'success': True,
            'history': history
        })
        
    except Exception as e:
        log_error(f"Error getting sync history: {e}")
        return jsonify({'error': 'Failed to get sync history'}), 500


@cloud_sync_bp.route('/api/cloud_sync/history/clear', methods=['POST'])
@test_mode_login_required
def clear_sync_history():
    """Clear sync history"""
    try:
        cloud_sync_manager.clear_sync_history()
        
        log_api_request('cloud_sync_history_clear', 'POST')
        return jsonify({
            'success': True,
            'message': 'Sync history cleared'
        })
        
    except Exception as e:
        log_error(f"Error clearing sync history: {e}")
        return jsonify({'error': 'Failed to clear sync history'}), 500


@cloud_sync_bp.route('/api/cloud_sync/oauth/url', methods=['POST'])
@test_mode_login_required
def get_oauth_url():
    """Get OAuth URL for provider authentication"""
    try:
        data = request.get_json()
        provider = data.get('provider')
        
        if not provider:
            return jsonify({'error': 'Provider is required'}), 400
        
        # Generate OAuth URLs for different providers
        oauth_urls = {
            'gdrive': {
                'url': 'https://accounts.google.com/o/oauth2/auth',
                'params': {
                    'client_id': 'YOUR_GOOGLE_CLIENT_ID',
                    'redirect_uri': f'http://localhost:{Config.PORT}/cloud_sync/oauth/callback/gdrive',
                    'scope': 'https://www.googleapis.com/auth/drive.file',
                    'response_type': 'code',
                    'access_type': 'offline'
                }
            },
            'dropbox': {
                'url': 'https://www.dropbox.com/oauth2/authorize',
                'params': {
                    'client_id': 'YOUR_DROPBOX_CLIENT_ID',
                    'redirect_uri': f'http://localhost:{Config.PORT}/cloud_sync/oauth/callback/dropbox',
                    'response_type': 'code',
                    'token_access_type': 'offline'
                }
            },
            'onedrive': {
                'url': 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize',
                'params': {
                    'client_id': 'YOUR_ONEDRIVE_CLIENT_ID',
                    'redirect_uri': f'http://localhost:{Config.PORT}/cloud_sync/oauth/callback/onedrive',
                    'scope': 'files.readwrite',
                    'response_type': 'code'
                }
            }
        }
        
        if provider not in oauth_urls:
            return jsonify({'error': f'Provider {provider} not supported'}), 400
        
        oauth_info = oauth_urls[provider]
        
        # Build URL with parameters
        from urllib.parse import urlencode
        full_url = f"{oauth_info['url']}?{urlencode(oauth_info['params'])}"
        
        log_api_request('cloud_sync_oauth_url', 'POST')
        return jsonify({
            'success': True,
            'oauth_url': full_url,
            'provider': provider
        })
        
    except Exception as e:
        log_error(f"Error getting OAuth URL: {e}")
        return jsonify({'error': 'Failed to get OAuth URL'}), 500


@cloud_sync_bp.route('/api/cloud_sync/oauth/callback/<provider>', methods=['GET'])
def oauth_callback(provider):
    """Handle OAuth callback from providers"""
    try:
        code = request.args.get('code')
        error = request.args.get('error')
        
        if error:
            return jsonify({'error': f'OAuth error: {error}'}), 400
        
        if not code:
            return jsonify({'error': 'No authorization code received'}), 400
        
        # In a real implementation, you would exchange the code for tokens
        # For now, we'll return a success message
        log_api_request('cloud_sync_oauth_callback', {'provider': provider})
        return jsonify({
            'success': True,
            'message': f'OAuth callback received for {provider}',
            'provider': provider,
            'code': code
        })
        
    except Exception as e:
        log_error(f"Error in OAuth callback: {e}")
        return jsonify({'error': 'OAuth callback failed'}), 500


@cloud_sync_bp.route('/api/cloud_sync/test_connection', methods=['POST'])
@test_mode_login_required
def test_connection():
    """Test connection to a cloud provider"""
    try:
        data = request.get_json()
        provider = data.get('provider')
        credentials = data.get('credentials', {})
        
        if not provider:
            return jsonify({'error': 'Provider is required'}), 400
        
        # Test connection based on provider
        if provider == 'gdrive':
            import asyncio
            from ..core.connectors.gdrive_connector import GoogleDriveConnector
            connector = GoogleDriveConnector(connector_id=f"gdrive_{provider}")
            success = asyncio.run(connector.connect(credentials))
        elif provider == 'dropbox':
            if 'dropbox' in cloud_sync_manager.providers:
                success = cloud_sync_manager.providers['dropbox'].connect(credentials.get('access_token', ''))
            else:
                success = False
        elif provider == 'onedrive':
            if 'onedrive' in cloud_sync_manager.providers:
                success = cloud_sync_manager.providers['onedrive'].connect(
                    credentials.get('client_id', ''),
                    credentials.get('client_secret', ''),
                    credentials.get('redirect_uri', '')
                )
            else:
                success = False
        else:
            return jsonify({'error': f'Provider {provider} not supported'}), 400
        
        log_api_request('cloud_sync_test_connection', 'POST')
        return jsonify({
            'success': True,
            'connection_successful': success,
            'provider': provider
        })
        
    except Exception as e:
        log_error(f"Error testing connection: {e}")
        return jsonify({'error': 'Failed to test connection'}), 500


@cloud_sync_bp.route('/api/cloud_sync/browse', methods=['POST'])
@test_mode_login_required
def browse_cloud_storage():
    """Browse files in cloud storage"""
    try:
        data = request.get_json()
        provider = data.get('provider')
        path = data.get('path', '/')
        
        if not provider:
            return jsonify({'error': 'Provider is required'}), 400
        
        # Mock file listing for now
        # In a real implementation, this would query the actual cloud storage
        mock_files = [
            {
                'name': 'Documents',
                'path': '/Documents',
                'type': 'folder',
                'size': None,
                'modified': '2024-01-15T10:30:00Z'
            },
            {
                'name': 'example.txt',
                'path': '/example.txt',
                'type': 'file',
                'size': 1024,
                'modified': '2024-01-14T15:45:00Z'
            }
        ]
        
        log_api_request('cloud_sync_browse', 'POST')
        return jsonify({
            'success': True,
            'files': mock_files,
            'path': path,
            'provider': provider
        })
        
    except Exception as e:
        log_error(f"Error browsing cloud storage: {e}")
        return jsonify({'error': 'Failed to browse cloud storage'}), 500


@cloud_sync_bp.route('/api/cloud_sync/settings', methods=['GET'])
@test_mode_login_required
def get_sync_settings():
    """Get global sync settings"""
    try:
        settings = {
            'background_sync_enabled': True,
            'sync_interval_minutes': 5,
            'max_file_size_mb': 100,
            'encryption_enabled': True,
            'compression_enabled': True,
            'conflict_resolution': 'newer_wins',
            'auto_retry_failed_syncs': True,
            'max_retry_attempts': 3,
            'notify_on_sync_completion': True,
            'notify_on_sync_errors': True
        }
        
        log_api_request('cloud_sync_settings', 'GET')
        return jsonify({
            'success': True,
            'settings': settings
        })
        
    except Exception as e:
        log_error(f"Error getting sync settings: {e}")
        return jsonify({'error': 'Failed to get sync settings'}), 500


@cloud_sync_bp.route('/api/cloud_sync/settings', methods=['POST'])
@test_mode_login_required
def update_sync_settings():
    """Update global sync settings"""
    try:
        data = request.get_json()
        
        # In a real implementation, you would save these settings
        # For now, we'll just return success
        
        log_api_request('cloud_sync_settings_update', 'POST')
        return jsonify({
            'success': True,
            'message': 'Sync settings updated'
        })
        
    except Exception as e:
        log_error(f"Error updating sync settings: {e}")
        return jsonify({'error': 'Failed to update sync settings'}), 500
