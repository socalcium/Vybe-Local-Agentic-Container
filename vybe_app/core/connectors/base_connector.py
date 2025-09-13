"""
Base Connector Class
Abstract base class for all external data connectors
"""

import os
import json
import logging
import base64
import hashlib
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.backends import default_backend
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

logger = logging.getLogger(__name__)

class ConnectionStatus(Enum):
    """Status of a connector connection"""
    NOT_CONNECTED = "not_connected"
    CONNECTED = "connected"
    SYNCING = "syncing"
    ERROR = "error"
    EXPIRED = "expired"

class ConnectorError(Exception):
    """Custom exception for connector errors"""
    pass

@dataclass
class ConnectorCredentials:
    """Secure storage for connector credentials"""
    connector_id: str
    credentials: Dict[str, Any] = field(default_factory=dict)
    expires_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    
    def is_expired(self) -> bool:
        """Check if credentials are expired"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "connector_id": self.connector_id,
            "credentials": self.credentials,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat(),
            "last_used": self.last_used.isoformat() if self.last_used else None
        }

@dataclass
class SyncResult:
    """Result of a connector sync operation"""
    success: bool
    items_processed: int = 0
    items_added: int = 0
    items_updated: int = 0
    items_failed: int = 0
    error_message: Optional[str] = None
    duration_seconds: float = 0.0
    sync_timestamp: datetime = field(default_factory=datetime.now)
    collection_name: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "success": self.success,
            "items_processed": self.items_processed,
            "items_added": self.items_added,
            "items_updated": self.items_updated,
            "items_failed": self.items_failed,
            "error_message": self.error_message,
            "duration_seconds": self.duration_seconds,
            "sync_timestamp": self.sync_timestamp.isoformat(),
            "collection_name": self.collection_name
        }

class BaseConnector(ABC):
    """Abstract base class for all external data connectors"""
    
    def __init__(self, connector_id: str, config: Optional[Dict[str, Any]] = None):
        self.connector_id = connector_id
        self.config = config or {}
        self.credentials: Optional[ConnectorCredentials] = None
        self.logger = logging.getLogger(f"connector.{connector_id}")
        self._credentials_file = self._get_credentials_file_path()
        
        # Load existing credentials if available
        self._load_credentials()
    
    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name for the connector"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what this connector does"""
        pass
    
    @property
    @abstractmethod
    def icon(self) -> str:
        """Icon class or URL for the connector"""
        pass
    
    @property
    @abstractmethod
    def required_credentials(self) -> List[str]:
        """List of required credential field names"""
        pass
    
    @property
    @abstractmethod
    def default_collection_name(self) -> str:
        """Default RAG collection name for this connector"""
        pass
    
    @abstractmethod
    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """
        Establish connection with the external service
        
        Args:
            credentials: Dictionary containing required authentication data
            
        Returns:
            bool: True if connection successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def sync(self) -> SyncResult:
        """
        Synchronize data from the external service
        
        Returns:
            SyncResult: Results of the sync operation
        """
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """
        Test if the current connection is valid
        
        Returns:
            bool: True if connection is valid, False otherwise
        """
        pass
    
    def get_status(self) -> ConnectionStatus:
        """Get the current connection status"""
        if not self.credentials:
            return ConnectionStatus.NOT_CONNECTED
        
        if self.credentials.is_expired():
            return ConnectionStatus.EXPIRED
        
        return ConnectionStatus.CONNECTED
    
    def store_credentials(self, credentials: Dict[str, Any], 
                         expires_at: Optional[datetime] = None) -> bool:
        """
        Securely store connector credentials
        
        Args:
            credentials: Dictionary of credential data
            expires_at: Optional expiration datetime
            
        Returns:
            bool: True if stored successfully
        """
        try:
            self.credentials = ConnectorCredentials(
                connector_id=self.connector_id,
                credentials=credentials,
                expires_at=expires_at
            )
            
            return self._save_credentials()
            
        except Exception as e:
            self.logger.error(f"Failed to store credentials: {e}")
            return False
    
    def clear_credentials(self) -> bool:
        """Clear stored credentials"""
        try:
            self.credentials = None
            if self._credentials_file.exists():
                self._credentials_file.unlink()
            return True
        except Exception as e:
            self.logger.error(f"Failed to clear credentials: {e}")
            return False
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get a configuration value"""
        return self.config.get(key, default)
    
    def update_config(self, updates: Dict[str, Any]):
        """Update configuration values"""
        self.config.update(updates)
    
    def _get_credentials_file_path(self) -> Path:
        """Get the path for storing credentials"""
        credentials_dir = Path("instance") / "connectors"
        credentials_dir.mkdir(parents=True, exist_ok=True)
        return credentials_dir / f"{self.connector_id}_credentials.json"
    
    def _get_encryption_key(self) -> bytes:
        """
        Derive encryption key from SECRET_KEY and salt
        
        Returns:
            bytes: Fernet encryption key
        """
        try:
            # Get SECRET_KEY from Flask config or environment
            from flask import current_app
            try:
                secret_key = current_app.config.get('SECRET_KEY')
            except RuntimeError:
                # Fallback if outside app context
                secret_key = os.environ.get('SECRET_KEY', 'default-secret-key-for-development')
            
            if not secret_key:
                secret_key = 'default-secret-key-for-development'
            
            # Use connector_id as salt for key derivation
            salt = self.connector_id.encode('utf-8')[:16].ljust(16, b'0')
            
            # Derive key using PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),  # type: ignore[arg-type]
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )
            key = base64.urlsafe_b64encode(kdf.derive(secret_key.encode('utf-8')))
            return key
            
        except Exception as e:
            logger.error(f"Failed to derive encryption key: {e}")
            # Fallback to a simple key for development
            return base64.urlsafe_b64encode(hashlib.sha256(
                f"{self.connector_id}-fallback-key".encode('utf-8')
            ).digest())
    
    def _encrypt_data(self, data: str) -> str:
        """
        Encrypt data using Fernet encryption
        
        Args:
            data: String data to encrypt
            
        Returns:
            str: Base64 encoded encrypted data
        """
        if not CRYPTO_AVAILABLE:
            logger.warning("Cryptography library not available, storing credentials in plaintext")
            return data
        
        try:
            key = self._get_encryption_key()
            fernet = Fernet(key)
            encrypted_data = fernet.encrypt(data.encode('utf-8'))
            return base64.b64encode(encrypted_data).decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to encrypt data: {e}")
            return data
    
    def _decrypt_data(self, encrypted_data: str) -> str:
        """
        Decrypt data using Fernet encryption
        
        Args:
            encrypted_data: Base64 encoded encrypted data
            
        Returns:
            str: Decrypted data
        """
        if not CRYPTO_AVAILABLE:
            # Data was stored in plaintext
            return encrypted_data
        
        try:
            key = self._get_encryption_key()
            fernet = Fernet(key)
            decoded_data = base64.b64decode(encrypted_data.encode('utf-8'))
            decrypted_data = fernet.decrypt(decoded_data)
            return decrypted_data.decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to decrypt data: {e}")
            # Return as-is if decryption fails (might be plaintext from old version)
            return encrypted_data
    
    def _save_credentials(self) -> bool:
        """Save credentials to encrypted file"""
        try:
            if not self.credentials:
                return False
            
            # Convert credentials to JSON string
            data = self.credentials.to_dict()
            json_data = json.dumps(data, default=str)
            
            # Encrypt the JSON data
            encrypted_data = self._encrypt_data(json_data)
            
            # Save encrypted data to file
            with open(self._credentials_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'encrypted': True,
                    'data': encrypted_data,
                    'version': '1.0'
                }, f)
            
            # Set restrictive permissions (Windows/Unix)
            os.chmod(self._credentials_file, 0o600)
            
            self.logger.info(f"Encrypted credentials saved for {self.connector_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save credentials: {e}")
            return False
    
    def _load_credentials(self) -> bool:
        """Load credentials from encrypted file"""
        try:
            if not self._credentials_file.exists():
                return False
            
            with open(self._credentials_file, 'r', encoding='utf-8') as f:
                file_data = json.load(f)
            
            # Check if data is encrypted (new format) or plain (legacy)
            if isinstance(file_data, dict) and file_data.get('encrypted'):
                # Decrypt the data
                encrypted_data = file_data.get('data', '')
                decrypted_json = self._decrypt_data(encrypted_data)
                data = json.loads(decrypted_json)
            else:
                # Legacy plaintext format
                data = file_data
                self.logger.warning(f"Loading plaintext credentials for {self.connector_id}, consider re-saving to encrypt")
            
            self.credentials = ConnectorCredentials(
                connector_id=data["connector_id"],
                credentials=data["credentials"],
                expires_at=datetime.fromisoformat(data["expires_at"]) if data["expires_at"] else None,
                created_at=datetime.fromisoformat(data["created_at"]),
                last_used=datetime.fromisoformat(data["last_used"]) if data["last_used"] else None
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load credentials: {e}")
            return False
    
    def _update_last_used(self):
        """Update the last used timestamp"""
        if self.credentials:
            self.credentials.last_used = datetime.now()
            self._save_credentials()
    
    async def _ingest_content_to_rag(self, content: str, content_id: str, 
                                   metadata: Optional[Dict[str, Any]] = None,
                                   collection_name: Optional[str] = None) -> bool:
        """
        Ingest content into RAG collection
        
        Args:
            content: Text content to ingest
            content_id: Unique identifier for the content
            metadata: Optional metadata for the content
            collection_name: Optional collection name (uses default if not provided)
            
        Returns:
            bool: True if ingestion successful
        """
        try:
            from ...rag.text_processing import ingest_file_content_to_rag
            
            target_collection = collection_name or self.default_collection_name
            
            # Add connector metadata
            full_metadata = {
                "connector_id": self.connector_id,
                "content_id": content_id,
                "ingested_at": datetime.now().isoformat(),
                **(metadata or {})
            }
            
            success = ingest_file_content_to_rag(
                collection_name=target_collection,
                filename=content_id,
                content=content
            )
            
            if success:
                self.logger.info(f"Ingested content {content_id} to collection {target_collection}")
            else:
                self.logger.error(f"Failed to ingest content {content_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error ingesting content {content_id}: {e}")
            return False
