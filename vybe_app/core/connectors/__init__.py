"""
External Data Connectors Package
Provides connectivity to external data sources for knowledge base integration
"""

from .base_connector import BaseConnector, ConnectionStatus, ConnectorError
from .github_connector import GitHubConnector
from .gdrive_connector import GoogleDriveConnector
from .notion_connector import NotionConnector

# Registry of available connectors
AVAILABLE_CONNECTORS = {
    'github': GitHubConnector,
    'gdrive': GoogleDriveConnector,
    'notion': NotionConnector
}

__all__ = [
    'BaseConnector',
    'ConnectionStatus',
    'ConnectorError',
    'GitHubConnector',
    'GoogleDriveConnector',
    'NotionConnector',
    'AVAILABLE_CONNECTORS'
]
