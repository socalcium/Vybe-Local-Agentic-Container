"""
Cloud Sync Manager for Vybe
Provides seamless synchronization with major cloud storage providers
"""

import os
import json
import hashlib
import threading
import time
import zipfile
import tempfile
import signal
import atexit
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
import shutil

# Import resource cleanup utilities
from ..utils.resource_cleanup import ResourceCleanupManager, register_thread_cleanup

# Cloud storage SDKs
try:
    import dropbox
    from dropbox.exceptions import ApiError as DropboxApiError
    from dropbox import files as dropbox_files
    DROPBOX_AVAILABLE = True
except ImportError:
    DROPBOX_AVAILABLE = False
    dropbox_files = None

try:
    # OneDrive SDK is deprecated, using Microsoft Graph API instead
    # from onedrivesdk import get_default_client, Client
    # For now, disable OneDrive until proper Graph API implementation
    ONEDRIVE_AVAILABLE = False
except ImportError:
    ONEDRIVE_AVAILABLE = False

from ..logger import log_info, log_error, log_warning
from .connectors.gdrive_connector import GoogleDriveConnector


class SyncStatus(Enum):
    """Sync operation status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CONFLICT = "conflict"


class SyncDirection(Enum):
    """Sync direction"""
    UPLOAD = "upload"
    DOWNLOAD = "download"
    BIDIRECTIONAL = "bidirectional"


@dataclass
class SyncItem:
    """Represents a file or directory to be synced"""
    local_path: str
    remote_path: str
    provider: str
    last_synced: Optional[datetime] = None
    file_hash: Optional[str] = None
    size: Optional[int] = None
    status: SyncStatus = SyncStatus.PENDING
    direction: SyncDirection = SyncDirection.BIDIRECTIONAL
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class SyncConfig:
    """Configuration for a sync operation"""
    provider: str
    credentials: Dict[str, Any]
    sync_items: List[SyncItem]
    auto_sync: bool = True
    sync_interval: int = 300  # 5 minutes
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    encryption_enabled: bool = True
    compression_enabled: bool = True
    conflict_resolution: str = "newer_wins"  # newer_wins, local_wins, remote_wins, manual


class CloudSyncManager:
    """Manages cloud synchronization with multiple providers"""
    
    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = Path(data_dir) if data_dir else Path("cloud_sync_data")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize providers
        self.providers = {}
        self.sync_configs = {}
        self.sync_history = []
        self.sync_lock = threading.Lock()
        
        # Background sync management
        self.sync_thread = None
        self.sync_running = False
        self._shutdown_event = threading.Event()
        self._cleanup_lock = threading.Lock()
        
        # Load existing configurations
        self._load_configs()
        self._initialize_providers()
        
        # Register cleanup handlers
        atexit.register(self._cleanup_on_exit)
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        # Start background sync thread
        self._start_background_sync()
    
    def _load_configs(self):
        """Load sync configurations from database"""
        config_file = self.data_dir / "sync_configs.json"
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    configs_data = json.load(f)
                
                for provider, config_data in configs_data.items():
                    sync_items = [
                        SyncItem(**item_data) for item_data in config_data.get('sync_items', [])
                    ]
                    
                    self.sync_configs[provider] = SyncConfig(
                        provider=provider,
                        credentials=config_data.get('credentials', {}),
                        sync_items=sync_items,
                        auto_sync=config_data.get('auto_sync', True),
                        sync_interval=config_data.get('sync_interval', 300),
                        max_file_size=config_data.get('max_file_size', 100 * 1024 * 1024),
                        encryption_enabled=config_data.get('encryption_enabled', True),
                        compression_enabled=config_data.get('compression_enabled', True),
                        conflict_resolution=config_data.get('conflict_resolution', 'newer_wins')
                    )
                
                log_info(f"Loaded {len(self.sync_configs)} sync configurations")
                
            except Exception as e:
                log_error(f"Error loading sync configs: {e}")
    
    def _save_configs(self):
        """Save sync configurations to database"""
        config_file = self.data_dir / "sync_configs.json"
        try:
            configs_data = {}
            for provider, config in self.sync_configs.items():
                configs_data[provider] = {
                    'credentials': config.credentials,
                    'sync_items': [asdict(item) for item in config.sync_items],
                    'auto_sync': config.auto_sync,
                    'sync_interval': config.sync_interval,
                    'max_file_size': config.max_file_size,
                    'encryption_enabled': config.encryption_enabled,
                    'compression_enabled': config.compression_enabled,
                    'conflict_resolution': config.conflict_resolution
                }
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(configs_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            log_error(f"Error saving sync configs: {e}")
    
    def _initialize_providers(self):
        """Initialize available cloud storage providers"""
        # Google Drive
        if 'gdrive' in self.sync_configs:
            try:
                self.providers['gdrive'] = GoogleDriveConnector(connector_id='gdrive')
                log_info("Google Drive provider initialized")
            except Exception as e:
                log_error(f"Failed to initialize Google Drive: {e}")
        
        # Dropbox
        if DROPBOX_AVAILABLE and 'dropbox' in self.sync_configs:
            try:
                self.providers['dropbox'] = DropboxProvider()
                log_info("Dropbox provider initialized")
            except Exception as e:
                log_error(f"Failed to initialize Dropbox: {e}")
        
        # OneDrive
        if ONEDRIVE_AVAILABLE and 'onedrive' in self.sync_configs:
            try:
                self.providers['onedrive'] = OneDriveProvider()
                log_info("OneDrive provider initialized")
            except Exception as e:
                log_error(f"Failed to initialize OneDrive: {e}")
    
    def add_sync_config(self, provider: str, credentials: Dict[str, Any], 
                       sync_items: List[SyncItem], **kwargs) -> bool:
        """Add a new sync configuration"""
        try:
            config = SyncConfig(
                provider=provider,
                credentials=credentials,
                sync_items=sync_items,
                **kwargs
            )
            
            self.sync_configs[provider] = config
            self._save_configs()
            
            # Initialize provider if not already done
            if provider not in self.providers:
                self._initialize_provider(provider)
            
            log_info(f"Added sync config for {provider}")
            return True
            
        except Exception as e:
            log_error(f"Error adding sync config: {e}")
            return False
    
    def _initialize_provider(self, provider: str):
        """Initialize a specific provider"""
        if provider == 'gdrive':
            self.providers[provider] = GoogleDriveConnector(connector_id=provider)
        elif provider == 'dropbox' and DROPBOX_AVAILABLE:
            self.providers[provider] = DropboxProvider()
        elif provider == 'onedrive' and ONEDRIVE_AVAILABLE:
            self.providers[provider] = OneDriveProvider()
    
    def remove_sync_config(self, provider: str) -> bool:
        """Remove a sync configuration"""
        try:
            if provider in self.sync_configs:
                del self.sync_configs[provider]
                if provider in self.providers:
                    del self.providers[provider]
                self._save_configs()
                log_info(f"Removed sync config for {provider}")
                return True
            return False
        except Exception as e:
            log_error(f"Error removing sync config: {e}")
            return False
    
    def get_sync_status(self, provider: Optional[str] = None) -> Dict[str, Any]:
        """Get sync status for a provider or all providers"""
        if provider:
            if provider not in self.sync_configs:
                return {'error': f'Provider {provider} not configured'}
            
            config = self.sync_configs[provider]
            return {
                'provider': provider,
                'auto_sync': config.auto_sync,
                'sync_interval': config.sync_interval,
                'items_count': len(config.sync_items),
                'last_sync': self._get_last_sync_time(provider),
                'status': self._get_provider_status(provider)
            }
        else:
            return {
                'providers': list(self.sync_configs.keys()),
                'total_configs': len(self.sync_configs),
                'active_providers': len(self.providers),
                'background_sync_running': self.sync_thread and self.sync_thread.is_alive()
            }
    
    def _get_last_sync_time(self, provider: str) -> Optional[datetime]:
        """Get the last sync time for a provider"""
        if provider not in self.sync_configs:
            return None
        
        config = self.sync_configs[provider]
        last_sync = None
        
        for item in config.sync_items:
            if item.last_synced and (not last_sync or item.last_synced > last_sync):
                last_sync = item.last_synced
        
        return last_sync
    
    def _get_provider_status(self, provider: str) -> str:
        """Get the current status of a provider"""
        if provider not in self.providers:
            return "not_initialized"
        
        try:
            # Test connection
            if hasattr(self.providers[provider], 'test_connection'):
                if self.providers[provider].test_connection():
                    return "connected"
                else:
                    return "connection_failed"
            else:
                return "unknown"
        except Exception:
            return "error"
    
    def sync_now(self, provider: Optional[str] = None, items: Optional[List[str]] = None) -> Dict[str, Any]:
        """Perform immediate sync for specified provider and items"""
        try:
            with self.sync_lock:
                if provider:
                    return self._sync_provider(provider, items)
                else:
                    results = {}
                    for prov in self.sync_configs.keys():
                        results[prov] = self._sync_provider(prov, items)
                    return results
        except Exception as e:
            log_error(f"Error in sync_now: {e}")
            return {'error': str(e)}
    
    def _sync_provider(self, provider: str, items: Optional[List[str]] = None) -> Dict[str, Any]:
        """Sync a specific provider"""
        if provider not in self.sync_configs or provider not in self.providers:
            return {'error': f'Provider {provider} not configured or available'}
        
        config = self.sync_configs[provider]
        provider_instance = self.providers[provider]
        
        if provider_instance is None:
            return {'error': f'Provider {provider} not properly initialized'}
        
        results = {
            'provider': provider,
            'started_at': datetime.now().isoformat(),
            'items_processed': 0,
            'items_succeeded': 0,
            'items_failed': 0,
            'errors': []
        }
        
        # Filter items if specified
        sync_items = config.sync_items
        if items:
            sync_items = [item for item in sync_items if item.local_path in items]
        
        for item in sync_items:
            try:
                results['items_processed'] += 1
                
                # Check if file exists locally
                local_path = Path(item.local_path)
                if not local_path.exists():
                    results['errors'].append(f"Local file not found: {item.local_path}")
                    results['items_failed'] += 1
                    continue
                
                # Calculate file hash
                file_hash = self._calculate_file_hash(local_path)
                
                # Check if file has changed
                if item.file_hash == file_hash and item.last_synced:
                    # File hasn't changed, skip sync
                    continue
                
                # Perform sync based on direction
                if item.direction in [SyncDirection.UPLOAD, SyncDirection.BIDIRECTIONAL]:
                    success = self._upload_file(provider_instance, item, local_path, config)
                    if success:
                        item.file_hash = file_hash
                        item.last_synced = datetime.now()
                        results['items_succeeded'] += 1
                    else:
                        results['items_failed'] += 1
                
                if item.direction in [SyncDirection.DOWNLOAD, SyncDirection.BIDIRECTIONAL]:
                    success = self._download_file(provider_instance, item, local_path, config)
                    if success:
                        results['items_succeeded'] += 1
                    else:
                        results['items_failed'] += 1
                
            except Exception as e:
                error_msg = f"Error syncing {item.local_path}: {e}"
                results['errors'].append(error_msg)
                results['items_failed'] += 1
                log_error(error_msg)
        
        # Save updated configurations
        self._save_configs()
        
        results['completed_at'] = datetime.now().isoformat()
        self.sync_history.append(results)
        
        return results
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of a file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def _upload_file(self, provider, item: SyncItem, local_path: Path, config: SyncConfig) -> bool:
        """Upload a file to cloud storage"""
        try:
            # Check file size
            if local_path.stat().st_size > config.max_file_size:
                log_warning(f"File {local_path} exceeds max size limit")
                return False
            
            # Prepare file for upload
            upload_path = local_path
            if config.compression_enabled:
                upload_path = self._compress_file(local_path)
            
            if config.encryption_enabled:
                upload_path = self._encrypt_file(upload_path)
            
            # Upload to provider
            success = provider.upload_file(str(upload_path), item.remote_path)
            
            # Cleanup temporary files
            if upload_path != local_path:
                upload_path.unlink()
            
            return success
            
        except Exception as e:
            log_error(f"Error uploading {local_path}: {e}")
            return False
    
    def _download_file(self, provider, item: SyncItem, local_path: Path, config: SyncConfig) -> bool:
        """Download a file from cloud storage"""
        try:
            # Download from provider
            temp_path = provider.download_file(item.remote_path)
            if not temp_path:
                return False
            
            # Decrypt if needed
            if config.encryption_enabled:
                temp_path = self._decrypt_file(temp_path)
            
            # Decompress if needed
            if config.compression_enabled:
                temp_path = self._decompress_file(temp_path)
            
            # Move to final location
            local_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(temp_path), str(local_path))
            
            return True
            
        except Exception as e:
            log_error(f"Error downloading {local_path}: {e}")
            return False
    
    def _compress_file(self, file_path: Path) -> Path:
        """Compress a file using ZIP"""
        temp_dir = Path(tempfile.gettempdir())
        compressed_path = temp_dir / f"{file_path.stem}_compressed.zip"
        
        with zipfile.ZipFile(compressed_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(file_path, file_path.name)
        
        return compressed_path
    
    def _decompress_file(self, file_path: Path) -> Path:
        """Decompress a ZIP file"""
        temp_dir = Path(tempfile.gettempdir())
        extract_path = temp_dir / f"extracted_{file_path.stem}"
        
        with zipfile.ZipFile(file_path, 'r') as zipf:
            zipf.extractall(extract_path)
        
        # Find the extracted file
        extracted_files = list(extract_path.rglob('*'))
        if extracted_files:
            return extracted_files[0]
        
        return file_path
    
    def _encrypt_file(self, file_path: Path) -> Path:
        """Encrypt a file (placeholder implementation)"""
        # In a real implementation, this would use proper encryption
        # For now, we'll just return the original file
        return file_path
    
    def _decrypt_file(self, file_path: Path) -> Path:
        """Decrypt a file (placeholder implementation)"""
        # In a real implementation, this would use proper decryption
        # For now, we'll just return the original file
        return file_path
    
    def _start_background_sync(self):
        """Start background sync thread"""
        def background_sync():
            # Use event-based waits for responsive shutdown
            waiter = self._shutdown_event
            while not waiter.is_set():
                try:
                    for provider, config in self.sync_configs.items():
                        if config.auto_sync:
                            last_sync = self._get_last_sync_time(provider)
                            if not last_sync or (datetime.now() - last_sync).seconds >= config.sync_interval:
                                self._sync_provider(provider)
                    
                    # Wait up to 60s but wake immediately on shutdown
                    if waiter.wait(60):
                        break
                    
                except Exception as e:
                    log_error(f"Error in background sync: {e}")
                    # Back off for 5 minutes, interruptible
                    if waiter.wait(300):
                        break
        
        self.sync_thread = threading.Thread(target=background_sync, daemon=True)
        self.sync_thread.start()
        
        # Register thread for cleanup monitoring
        register_thread_cleanup(self.sync_thread, "background_sync", self._cleanup_resources)
        
        log_info("Background sync thread started")
    
    def stop_background_sync(self):
        """Stop the background sync thread"""
        self.sync_running = False
        self._shutdown_event.set()
        
        if self.sync_thread and self.sync_thread.is_alive():
            self.sync_thread.join(timeout=5.0)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        log_info(f"Received signal {signum}, initiating graceful shutdown")
        self.stop_background_sync()
        self._cleanup_resources()

    def _cleanup_on_exit(self):
        """Cleanup function registered with atexit"""
        log_info("Application exiting, cleaning up cloud sync resources")
        self.stop_background_sync()
        self._cleanup_resources()

    def _cleanup_resources(self):
        """Clean up all resources and prevent memory leaks"""
        with self._cleanup_lock:
            try:
                # Stop background sync thread
                if self.sync_thread and self.sync_thread.is_alive():
                    self._shutdown_event.set()
                    self.sync_thread.join(timeout=5.0)
                    if self.sync_thread.is_alive():
                        log_warning("Sync thread did not terminate gracefully")
                
                # Close provider connections
                for provider_name, provider in self.providers.items():
                    try:
                        if hasattr(provider, 'close'):
                            provider.close()
                        elif hasattr(provider, 'disconnect'):
                            provider.disconnect()
                    except Exception as e:
                        log_error(f"Error closing provider {provider_name}: {e}")
                
                # Clear references
                self.providers.clear()
                self.sync_configs.clear()
                self.sync_history.clear()
                self.sync_running = False
                
                # Force garbage collection
                import gc
                gc.collect()
                
                log_info("Cloud sync resources cleaned up successfully")
                
            except Exception as e:
                log_error(f"Error during resource cleanup: {e}")
    
    def get_sync_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent sync history"""
        return self.sync_history[-limit:] if self.sync_history else []
    
    def clear_sync_history(self):
        """Clear sync history"""
        self.sync_history.clear()
        log_info("Sync history cleared")


class DropboxProvider:
    """Dropbox cloud storage provider"""
    
    def __init__(self):
        self.client = None
    
    def connect(self, access_token: str) -> bool:
        """Connect to Dropbox using access token"""
        try:
            self.client = dropbox.Dropbox(access_token)
            # Test connection
            self.client.users_get_current_account()
            return True
        except Exception as e:
            log_error(f"Dropbox connection failed: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Test Dropbox connection"""
        try:
            if self.client:
                self.client.users_get_current_account()
                return True
        except Exception:
            pass
        return False
    
    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """Upload file to Dropbox"""
        try:
            if not self.client:
                log_error("Dropbox client not connected")
                return False
            if not DROPBOX_AVAILABLE or dropbox_files is None:
                log_error("Dropbox SDK not available")
                return False
            with open(local_path, 'rb') as f:
                self.client.files_upload(f.read(), remote_path, mode=dropbox_files.WriteMode.overwrite)
            return True
        except Exception as e:
            log_error(f"Dropbox upload failed: {e}")
            return False
    
    def download_file(self, remote_path: str) -> Optional[Path]:
        """Download file from Dropbox"""
        try:
            if not self.client:
                log_error("Dropbox client not connected")
                return None
            temp_dir = Path(tempfile.gettempdir())
            local_path = temp_dir / f"dropbox_{Path(remote_path).name}"
            
            metadata, response = self.client.files_download(remote_path)
            with open(local_path, 'wb') as f:
                f.write(response.content)
            
            return local_path
        except Exception as e:
            log_error(f"Dropbox download failed: {e}")
            return None


class OneDriveProvider:
    """OneDrive cloud storage provider"""
    
    def __init__(self):
        self.client = None
    
    def connect(self, client_id: str, client_secret: str, redirect_uri: str) -> bool:
        """Connect to OneDrive using OAuth"""
        try:
            # OneDrive SDK is deprecated, need to implement Microsoft Graph API
            log_error("OneDrive SDK is deprecated. Please use Microsoft Graph API instead.")
            return False
        except Exception as e:
            log_error(f"OneDrive connection failed: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Test OneDrive connection"""
        try:
            if self.client:
                self.client.item(drive='me', path='/').get()
                return True
        except Exception:
            pass
        return False
    
    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """Upload file to OneDrive"""
        try:
            if not self.client:
                log_error("OneDrive client not connected")
                return False
            with open(local_path, 'rb') as f:
                self.client.item(drive='me', path=remote_path).upload(f)
            return True
        except Exception as e:
            log_error(f"OneDrive upload failed: {e}")
            return False
    
    def download_file(self, remote_path: str) -> Optional[Path]:
        """Download file from OneDrive"""
        try:
            if not self.client:
                log_error("OneDrive client not connected")
                return None
            temp_dir = Path(tempfile.gettempdir())
            local_path = temp_dir / f"onedrive_{Path(remote_path).name}"
            
            with open(local_path, 'wb') as f:
                self.client.item(drive='me', path=remote_path).download(f)
            
            return local_path
        except Exception as e:
            log_error(f"OneDrive download failed: {e}")
            return None


# Global instance
cloud_sync_manager = CloudSyncManager()
