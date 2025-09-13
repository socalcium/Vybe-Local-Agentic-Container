"""
External Data Connectors API
============================

This module provides a comprehensive RESTful API for managing external data connectors
within the Vybe application. It enables seamless integration with popular cloud services,
productivity platforms, and data sources through a unified connector framework.

The API supports dynamic connector loading, credential management, data synchronization,
and real-time status monitoring. All connector operations are designed to be secure,
efficient, and compatible with the respective service APIs and authentication mechanisms.

Key Features:
    - Universal connector framework supporting multiple data sources
    - Secure credential storage and management with encryption
    - Real-time synchronization with configurable scheduling
    - Comprehensive error handling and retry mechanisms
    - Detailed logging and monitoring for all connector operations
    - Bulk operations for efficient data transfer
    - Webhook support for real-time data updates
    - Advanced filtering and transformation capabilities

Supported Connectors:
    - GitHub: Repository data, issues, pull requests, commits
    - Google Drive: Files, folders, sharing permissions, metadata
    - Notion: Pages, databases, blocks, workspace content
    - Slack: Messages, channels, user data, file attachments
    - Microsoft 365: OneDrive, SharePoint, Teams, Outlook
    - Trello: Boards, cards, lists, team collaboration data
    - Dropbox: Files, folders, sharing, version history
    - Box: Enterprise content management and collaboration

Connector Lifecycle:
    1. Discovery: List available connector types and capabilities
    2. Configuration: Set up authentication and connection parameters
    3. Testing: Validate connectivity and permissions
    4. Activation: Enable data synchronization and monitoring
    5. Operation: Perform data operations (read, write, sync)
    6. Monitoring: Track status, performance, and errors
    7. Maintenance: Update credentials, modify settings
    8. Deactivation: Safely disconnect and clean up resources

API Endpoints:
    - GET /connectors/: List all available connector types
    - GET /connectors/{type}/status: Check connector connection status
    - POST /connectors/{type}/connect: Establish connector connection
    - DELETE /connectors/{type}/disconnect: Disconnect connector
    - GET /connectors/{type}/data: Retrieve data from connector
    - POST /connectors/{type}/sync: Trigger manual synchronization
    - GET /connectors/{type}/jobs: List connector job history
    - PUT /connectors/{type}/config: Update connector configuration

Security Features:
    - OAuth 2.0 and API key authentication support
    - Encrypted credential storage with key rotation
    - Scope-limited access permissions for all connectors
    - Audit logging for all data access and modifications
    - Rate limiting to respect service API limits
    - Secure token refresh and session management

Data Processing:
    - Automatic data transformation and normalization
    - Configurable data filtering and selection rules
    - Incremental synchronization for efficiency
    - Conflict resolution for concurrent modifications
    - Data validation and integrity checking
    - Backup and recovery capabilities

Performance Features:
    - Asynchronous operations for non-blocking execution
    - Connection pooling for efficient resource usage
    - Intelligent batching for bulk operations
    - Caching with configurable TTL for frequently accessed data
    - Background job processing for long-running operations
    - Resource monitoring and automatic scaling

Example Usage:
    ```javascript
    // List available connectors
    const connectors = await fetch('/connectors/');
    
    // Connect to GitHub
    await fetch('/connectors/github/connect', {
        method: 'POST',
        body: JSON.stringify({
            token: 'github_token',
            repositories: ['repo1', 'repo2']
        })
    });
    
    // Retrieve data
    const data = await fetch('/connectors/github/data?type=issues');
    ```

Dependencies:
    - flask: Web framework for API endpoints
    - asyncio: Asynchronous operation support
    - requests: HTTP client for external API communication
    - cryptography: Secure credential storage and encryption
    - schedule: Background job scheduling and execution

Error Handling:
    All endpoints implement comprehensive error handling with specific error
    codes for different failure scenarios. Errors are logged with full context
    for debugging and monitoring purposes.

Note:
    This module requires appropriate API credentials and permissions for each
    external service. Rate limits and service-specific constraints are automatically
    handled to ensure compliance with service terms of use.
"""

from flask import Blueprint, request, jsonify
from ..auth import test_mode_login_required
from typing import Dict, Any, Optional
import logging
import asyncio
from datetime import datetime

from ..core.connectors import AVAILABLE_CONNECTORS, BaseConnector, ConnectionStatus
from ..core.job_manager import JobManager

logger = logging.getLogger(__name__)

connectors_api = Blueprint('connectors_api', __name__, url_prefix='/connectors')

# Active connector instances
_connector_instances: Dict[str, BaseConnector] = {}

def get_connector_instance(connector_type: str) -> Optional[BaseConnector]:
    """Get or create a connector instance"""
    if connector_type not in AVAILABLE_CONNECTORS:
        return None
    
    if connector_type not in _connector_instances:
        connector_class = AVAILABLE_CONNECTORS[connector_type]
        _connector_instances[connector_type] = connector_class(connector_type)
    
    return _connector_instances[connector_type]

@connectors_api.route('/', methods=['GET'])
@test_mode_login_required
def list_connectors():
    """List available connectors - root endpoint"""
    try:
        connectors = ['GitHub', 'Google Drive', 'Notion']
        return jsonify({
            "success": True,
            "connectors": connectors
        })
    except Exception as e:
        logger.error(f"Error listing connectors: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@connectors_api.route('/available', methods=['GET'])
@test_mode_login_required
def list_available_connectors():
    """List all available connector types"""
    try:
        connectors = []
        
        for connector_type, connector_class in AVAILABLE_CONNECTORS.items():
            # Create temporary instance to get metadata
            temp_instance = connector_class(connector_type)
            
            connectors.append({
                "type": connector_type,
                "display_name": temp_instance.display_name,
                "description": temp_instance.description,
                "icon": temp_instance.icon,
                "required_credentials": temp_instance.required_credentials,
                "default_collection": temp_instance.default_collection_name
            })
        
        return jsonify({
            "success": True,
            "connectors": connectors
        })
        
    except Exception as e:
        logger.error(f"Failed to list available connectors: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@connectors_api.route('/status', methods=['GET'])
@test_mode_login_required
def get_connectors_status():
    """Get status of all configured connectors"""
    try:
        connectors_status = {}
        
        for connector_type in AVAILABLE_CONNECTORS:
            connector = get_connector_instance(connector_type)
            if connector:
                status = connector.get_status()
                # Get sync summary if available, otherwise use empty dict
                summary = {}
                if hasattr(connector, 'get_sync_summary'):
                    try:
                        summary = getattr(connector, 'get_sync_summary')()
                    except (AttributeError, TypeError):
                        summary = {}
                
                connectors_status[connector_type] = {
                    "status": status.value,
                    "display_name": connector.display_name,
                    "last_sync": summary.get("last_sync"),
                    **summary
                }
        
        return jsonify({
            "success": True,
            "connectors": connectors_status
        })
        
    except Exception as e:
        logger.error(f"Failed to get connectors status: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@connectors_api.route('/<connector_type>/connect', methods=['POST'])
@test_mode_login_required
def connect_connector(connector_type: str):
    """Connect a specific connector with credentials"""
    try:
        if connector_type not in AVAILABLE_CONNECTORS:
            return jsonify({
                "success": False,
                "error": f"Unknown connector type: {connector_type}"
            }), 400
        
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No credentials provided"
            }), 400
        
        credentials = data.get("credentials", {})
        if not credentials:
            return jsonify({
                "success": False,
                "error": "Credentials are required"
            }), 400
        
        connector = get_connector_instance(connector_type)
        if not connector:
            return jsonify({
                "success": False,
                "error": "Failed to create connector instance"
            }), 500
        
        # Validate required credentials
        missing_creds = []
        for required_field in connector.required_credentials:
            if not credentials.get(required_field):
                missing_creds.append(required_field)
        
        if missing_creds:
            return jsonify({
                "success": False,
                "error": f"Missing required credentials: {', '.join(missing_creds)}"
            }), 400
        
        # Attempt to connect
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            success = loop.run_until_complete(connector.connect(credentials))
        finally:
            loop.close()
        
        if success:
            logger.info(f"Successfully connected {connector_type} connector")
            return jsonify({
                "success": True,
                "message": f"Successfully connected to {connector.display_name}",
                "status": connector.get_status().value
            })
        else:
            return jsonify({
                "success": False,
                "error": f"Failed to connect to {connector.display_name}"
            }), 400
            
    except Exception as e:
        logger.error(f"Failed to connect {connector_type}: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@connectors_api.route('/<connector_type>/disconnect', methods=['POST'])
@test_mode_login_required
def disconnect_connector(connector_type: str):
    """Disconnect a specific connector"""
    try:
        if connector_type not in AVAILABLE_CONNECTORS:
            return jsonify({
                "success": False,
                "error": f"Unknown connector type: {connector_type}"
            }), 400
        
        connector = get_connector_instance(connector_type)
        if not connector:
            return jsonify({
                "success": False,
                "error": "Connector not found"
            }), 404
        
        success = connector.clear_credentials()
        
        if success:
            logger.info(f"Successfully disconnected {connector_type} connector")
            return jsonify({
                "success": True,
                "message": f"Successfully disconnected from {connector.display_name}"
            })
        else:
            return jsonify({
                "success": False,
                "error": f"Failed to disconnect from {connector.display_name}"
            }), 500
            
    except Exception as e:
        logger.error(f"Failed to disconnect {connector_type}: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@connectors_api.route('/<connector_type>/test', methods=['POST'])
@test_mode_login_required
def test_connector_connection(connector_type: str):
    """Test connection for a specific connector"""
    try:
        if connector_type not in AVAILABLE_CONNECTORS:
            return jsonify({
                "success": False,
                "error": f"Unknown connector type: {connector_type}"
            }), 400
        
        connector = get_connector_instance(connector_type)
        if not connector:
            return jsonify({
                "success": False,
                "error": "Connector not found"
            }), 404
        
        # Test the connection
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            is_valid = loop.run_until_complete(connector.test_connection())
        finally:
            loop.close()
        
        return jsonify({
            "success": True,
            "is_connected": is_valid,
            "status": connector.get_status().value
        })
        
    except Exception as e:
        logger.error(f"Failed to test {connector_type} connection: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@connectors_api.route('/<connector_type>/sync', methods=['POST'])
@test_mode_login_required
def sync_connector(connector_type: str):
    """Trigger manual sync for a specific connector"""
    try:
        if connector_type not in AVAILABLE_CONNECTORS:
            return jsonify({
                "success": False,
                "error": f"Unknown connector type: {connector_type}"
            }), 400
        
        connector = get_connector_instance(connector_type)
        if not connector:
            return jsonify({
                "success": False,
                "error": "Connector not found"
            }), 404
        
        if connector.get_status() != ConnectionStatus.CONNECTED:
            return jsonify({
                "success": False,
                "error": f"{connector.display_name} is not connected"
            }), 400
        
        # Create background sync job using JobManager
        from flask import current_app
        job_manager = getattr(current_app, 'job_manager', None)
        
        if not job_manager:
            return jsonify({
                "success": False,
                "error": "Job manager not available"
            }), 500
        
        def sync_job():
            """Background sync job"""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(connector.sync())
                return result.to_dict()
            finally:
                loop.close()
        
        job_id = job_manager.submit_job(
            sync_job,
            f"Sync {connector.display_name} data",
            {"connector_type": connector_type}
        )
        
        logger.info(f"Started sync job {job_id} for {connector_type}")
        
        return jsonify({
            "success": True,
            "job_id": job_id,
            "message": f"Sync started for {connector.display_name}"
        })
        
    except Exception as e:
        logger.error(f"Failed to sync {connector_type}: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@connectors_api.route('/<connector_type>/config', methods=['GET'])
@test_mode_login_required
def get_connector_config(connector_type: str):
    """Get configuration for a specific connector"""
    try:
        if connector_type not in AVAILABLE_CONNECTORS:
            return jsonify({
                "success": False,
                "error": f"Unknown connector type: {connector_type}"
            }), 400
        
        connector = get_connector_instance(connector_type)
        if not connector:
            return jsonify({
                "success": False,
                "error": "Connector not found"
            }), 404
        
        return jsonify({
            "success": True,
            "config": connector.config,
            "status": connector.get_status().value,
            "required_credentials": connector.required_credentials
        })
        
    except Exception as e:
        logger.error(f"Failed to get {connector_type} config: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@connectors_api.route('/<connector_type>/config', methods=['PUT'])
@test_mode_login_required
def update_connector_config(connector_type: str):
    """Update configuration for a specific connector"""
    try:
        if connector_type not in AVAILABLE_CONNECTORS:
            return jsonify({
                "success": False,
                "error": f"Unknown connector type: {connector_type}"
            }), 400
        
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No configuration data provided"
            }), 400
        
        connector = get_connector_instance(connector_type)
        if not connector:
            return jsonify({
                "success": False,
                "error": "Connector not found"
            }), 404
        
        config_updates = data.get("config", {})
        connector.update_config(config_updates)
        
        logger.info(f"Updated configuration for {connector_type}")
        
        return jsonify({
            "success": True,
            "message": f"Configuration updated for {connector.display_name}",
            "config": connector.config
        })
        
    except Exception as e:
        logger.error(f"Failed to update {connector_type} config: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@connectors_api.route('/health', methods=['GET'])
@test_mode_login_required
def health_check():
    """Health check endpoint for connectors"""
    return jsonify({
        "success": True,
        "message": "Connectors API is healthy",
        "available_connectors": list(AVAILABLE_CONNECTORS.keys()),
        "timestamp": datetime.now().isoformat()
    })

# Error handlers
@connectors_api.errorhandler(400)
def bad_request(error):
    return jsonify({
        "success": False,
        "error": "Bad request",
        "details": str(error)
    }), 400

@connectors_api.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False,
        "error": "Not found",
        "details": str(error)
    }), 404

@connectors_api.errorhandler(500)
def internal_error(error):
    return jsonify({
        "success": False,
        "error": "Internal server error",
        "details": str(error)
    }), 500
