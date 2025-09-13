"""
AI File Management Tools for Vybe

This module provides safe file management capabilities for the AI assistant,
strictly confined to a designated workspace directory to prevent unauthorized
access to system files.
"""

import os
import json
import hashlib
import mimetypes
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor
import tempfile
import logging
import time
from contextlib import contextmanager

from flask import current_app

from ..logger import log_info, log_warning, log_error


def log_audit(action: str, filepath: str, user: str = "system") -> None:
    """
    Log security audit information for file operations
    
    Args:
        action: The action performed (e.g., 'READ', 'WRITE', 'DELETE')
        filepath: The file path being operated on
        user: The user performing the action
    """
    try:
        # Get canonical path to prevent path traversal obfuscation
        canonical_path = os.path.realpath(filepath)
        
        audit_data = {
            'timestamp': datetime.now().isoformat(),
            'action': action.upper(),
            'filepath': canonical_path,
            'user': user,
            'process_id': os.getpid()
        }
        
        # Log as structured JSON for easy parsing
        log_info(f"FILE_AUDIT: {json.dumps(audit_data)}")
        
    except Exception as e:
        log_error(f"Failed to log audit for {action} on {filepath}: {e}")


@dataclass
class FileInfo:
    """File information structure"""
    path: str
    name: str
    size: int
    mime_type: str
    hash: str
    created_at: datetime
    modified_at: datetime
    is_directory: bool
    permissions: str


@dataclass 
class BackupInfo:
    """Backup information structure"""
    original_path: str
    backup_path: str
    timestamp: datetime
    size: int
    hash: str


class FileOperationError(Exception):
    """Custom exception for file operation errors"""
    def __init__(self, message: str, error_code: str = "GENERIC", details: Optional[Dict] = None):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}


@contextmanager
def safe_file_operation(operation_name: str, file_path: Optional[str] = None):
    """Context manager for safe file operations with comprehensive error handling"""
    start_time = time.time()
    temp_files = []
    
    try:
        yield temp_files
        
    except PermissionError as e:
        log_error(f"{operation_name} failed - Permission denied for {file_path}: {e}")
        raise FileOperationError(
            f"Permission denied accessing {file_path}", 
            "PERMISSION_DENIED",
            {"file_path": file_path, "original_error": str(e)}
        )
        
    except FileNotFoundError as e:
        log_error(f"{operation_name} failed - File not found {file_path}: {e}")
        raise FileOperationError(
            f"File not found: {file_path}", 
            "FILE_NOT_FOUND",
            {"file_path": file_path, "original_error": str(e)}
        )
        
    except OSError as e:
        log_error(f"{operation_name} failed - OS error for {file_path}: {e}")
        raise FileOperationError(
            f"Operating system error: {e}", 
            "OS_ERROR",
            {"file_path": file_path, "original_error": str(e)}
        )
        
    except Exception as e:
        log_error(f"{operation_name} failed - Unexpected error: {e}")
        raise FileOperationError(
            f"Unexpected error during {operation_name}: {e}", 
            "UNEXPECTED_ERROR",
            {"operation": operation_name, "original_error": str(e)}
        )
        
    finally:
        # Cleanup temporary files
        for temp_file in temp_files:
            try:
                if isinstance(temp_file, Path) and temp_file.exists():
                    temp_file.unlink()
            except Exception as cleanup_error:
                log_warning(f"Failed to cleanup temp file {temp_file}: {cleanup_error}")
        
        # Log operation duration for performance monitoring
        duration = time.time() - start_time
        if duration > 5.0:  # Log slow operations
            log_warning(f"{operation_name} took {duration:.2f} seconds - consider optimization")


class BackupManager:
    """Manages file backups with versioning and cleanup"""
    
    def __init__(self, backup_dir: Optional[Path] = None):
        # Use lazy initialization for workspace path to avoid Flask context issues
        if backup_dir:
            self.backup_dir = backup_dir
        else:
            try:
                self.backup_dir = get_workspace_path() / ".backups"
            except Exception:
                # Fallback to temp directory if workspace path fails
                self.backup_dir = Path(tempfile.gettempdir()) / "vybe_backups"
        
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.max_backups_per_file = 5
        self.backup_retention_days = 30
    
    def create_backup(self, file_path: Path) -> Optional[BackupInfo]:
        """Create a backup of the specified file"""
        if not file_path.exists() or not file_path.is_file():
            return None
        
        with safe_file_operation("backup_creation", str(file_path)):
            # Generate backup filename with timestamp
            timestamp = datetime.now()
            backup_name = f"{file_path.name}_{timestamp.strftime('%Y%m%d_%H%M%S')}.bak"
            backup_path = self.backup_dir / backup_name
            
            # Copy file to backup location
            shutil.copy2(file_path, backup_path)
            
            # Calculate file hash for integrity
            file_hash = self._calculate_file_hash(backup_path)
            
            backup_info = BackupInfo(
                original_path=str(file_path),
                backup_path=str(backup_path),
                timestamp=timestamp,
                size=backup_path.stat().st_size,
                hash=file_hash
            )
            
            # Cleanup old backups
            self._cleanup_old_backups(file_path.name)
            
            log_info(f"Created backup: {backup_path}")
            return backup_info
    
    def restore_backup(self, backup_info: BackupInfo, verify_integrity: bool = True) -> bool:
        """Restore a file from backup"""
        backup_path = Path(backup_info.backup_path)
        original_path = Path(backup_info.original_path)
        
        if not backup_path.exists():
            log_error(f"Backup file not found: {backup_path}")
            return False
        
        with safe_file_operation("backup_restoration", str(original_path)):
            # Verify backup integrity if requested
            if verify_integrity:
                current_hash = self._calculate_file_hash(backup_path)
                if current_hash != backup_info.hash:
                    log_error(f"Backup integrity check failed: {backup_path}")
                    return False
            
            # Create backup of current file before restoration
            if original_path.exists():
                self.create_backup(original_path)
            
            # Copy backup to original location
            original_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup_path, original_path)
            
            log_info(f"Restored file from backup: {original_path}")
            return True
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file (synchronous version for internal use)"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def _calculate_file_hash_async(self, file_path: Path, callback=None) -> threading.Thread:
        """
        Calculate SHA-256 hash of file in a separate thread
        
        Args:
            file_path: Path to the file
            callback: Optional callback function to call with result
            
        Returns:
            Thread object for the hash calculation
        """
        def hash_worker():
            try:
                result = self._calculate_file_hash(file_path)
                if callback:
                    callback(result, None)
                return result
            except Exception as e:
                if callback:
                    callback(None, e)
                raise
        
        thread = threading.Thread(target=hash_worker, daemon=True)
        thread.start()
        return thread
    
    def _cleanup_old_backups(self, filename: str):
        """Remove old backups beyond retention limits"""
        # Find all backups for this file
        backup_pattern = f"{filename}_*.bak"
        backups = list(self.backup_dir.glob(backup_pattern))
        
        # Sort by modification time (newest first)
        backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        # Remove excess backups
        if len(backups) > self.max_backups_per_file:
            for backup in backups[self.max_backups_per_file:]:
                try:
                    backup.unlink()
                    log_info(f"Removed old backup: {backup}")
                except Exception as e:
                    log_warning(f"Failed to remove old backup {backup}: {e}")
        
        # Remove backups older than retention period
        cutoff_time = time.time() - (self.backup_retention_days * 24 * 3600)
        for backup in backups:
            if backup.stat().st_mtime < cutoff_time:
                try:
                    backup.unlink()
                    log_info(f"Removed expired backup: {backup}")
                except Exception as e:
                    log_warning(f"Failed to remove expired backup {backup}: {e}")


class FileProcessor:
    """Advanced file processing and management"""
    
    def __init__(self):
        self.processing_queue = []
        self.processing_lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.supported_formats = {
            'text': ['.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml', '.csv'],
            'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'],
            'audio': ['.mp3', '.wav', '.flac', '.ogg', '.m4a'],
            'video': ['.mp4', '.avi', '.mov', '.mkv', '.webm'],
            'document': ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']
        }
        self.max_file_size = 100 * 1024 * 1024  # 100MB
    
    def validate_file(self, file_path: Path) -> Tuple[bool, str]:
        """Validate file for processing"""
        try:
            # Check file exists
            if not file_path.exists():
                return False, "File does not exist"
            
            # Check file size
            file_size = file_path.stat().st_size
            if file_size > self.max_file_size:
                return False, f"File too large ({file_size} bytes, max {self.max_file_size})"
            
            # Check file type
            file_extension = file_path.suffix.lower()
            supported_extensions = []
            for extensions in self.supported_formats.values():
                supported_extensions.extend(extensions)
            
            if file_extension not in supported_extensions:
                return False, f"Unsupported file type: {file_extension}"
            
            return True, "File is valid"
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def get_file_info(self, file_path: Path, async_hash: bool = False) -> Optional[FileInfo]:
        """
        Get comprehensive file information
        
        Args:
            file_path: Path to the file
            async_hash: Whether to calculate hash asynchronously
            
        Returns:
            FileInfo object or None if error
        """
        try:
            if not file_path.exists():
                return None
            
            stat = file_path.stat()
            mime_type, _ = mimetypes.guess_type(str(file_path))
            
            # Calculate file hash
            if async_hash:
                # For async mode, return placeholder hash and calculate in background
                file_hash = "calculating..."
                self.calculate_file_hash_async(file_path)
            else:
                file_hash = self._calculate_file_hash(file_path)
            
            return FileInfo(
                path=str(file_path),
                name=file_path.name,
                size=stat.st_size,
                mime_type=mime_type or 'application/octet-stream',
                hash=file_hash,
                created_at=datetime.fromtimestamp(stat.st_ctime),
                modified_at=datetime.fromtimestamp(stat.st_mtime),
                is_directory=file_path.is_dir(),
                permissions=oct(stat.st_mode)[-3:]
            )
            
        except Exception as e:
            log_error(f"Error getting file info for {file_path}: {e}")
            return None
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file (synchronous version)"""
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            log_error(f"Error calculating file hash: {e}")
            return ""
    
    def calculate_file_hash_async(self, file_path: Path, callback=None) -> Dict[str, Any]:
        """
        Calculate SHA-256 hash of file in a separate thread to prevent UI blocking
        
        Args:
            file_path: Path to the file
            callback: Optional callback function to call with (result, error)
            
        Returns:
            Dict with status and thread info for tracking
        """
        def hash_worker():
            try:
                result = self._calculate_file_hash(file_path)
                if callback:
                    callback(result, None)
                return result
            except Exception as e:
                log_error(f"Async hash calculation failed for {file_path}: {e}")
                if callback:
                    callback(None, e)
                raise
        
        thread = threading.Thread(target=hash_worker, daemon=True)
        thread.start()
        
        return {
            'status': 'processing',
            'thread': thread,
            'file_path': str(file_path),
            'message': 'Hash calculation started in background'
        }
    
    def process_file_upload(self, uploaded_file, destination_path: str) -> Dict[str, Any]:
        """Process file upload with validation and processing"""
        try:
            # Validate destination path
            target_path = validate_workspace_path(destination_path)
            if not target_path:
                return {
                    'success': False,
                    'error': f"Invalid destination path: {destination_path}"
                }
            
            # Create destination directory if needed
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save uploaded file
            uploaded_file.save(str(target_path))
            
            # Validate saved file
            is_valid, validation_message = self.validate_file(target_path)
            if not is_valid:
                # Remove invalid file
                target_path.unlink(missing_ok=True)
                return {
                    'success': False,
                    'error': f"File validation failed: {validation_message}"
                }
            
            # Get file info
            file_info = self.get_file_info(target_path)
            
            log_info(f"File uploaded successfully: {target_path}")
            
            return {
                'success': True,
                'file_info': {
                    'path': str(target_path),
                    'name': target_path.name,
                    'size': file_info.size if file_info else 0,
                    'mime_type': file_info.mime_type if file_info else 'unknown'
                }
            }
            
        except Exception as e:
            log_error(f"File upload error: {e}")
            return {
                'success': False,
                'error': f"Upload failed: {str(e)}"
            }
    
    def process_file_download(self, file_path: str) -> Dict[str, Any]:
        """Process file download with validation"""
        try:
            # Validate file path
            target_path = validate_workspace_path(file_path)
            if not target_path:
                return {
                    'success': False,
                    'error': f"Invalid file path: {file_path}"
                }
            
            if not target_path.exists():
                return {
                    'success': False,
                    'error': f"File not found: {file_path}"
                }
            
            if not target_path.is_file():
                return {
                    'success': False,
                    'error': f"Path is not a file: {file_path}"
                }
            
            # Get file info
            file_info = self.get_file_info(target_path)
            
            return {
                'success': True,
                'file_path': str(target_path),
                'file_info': {
                    'name': file_info.name,
                    'size': file_info.size,
                    'mime_type': file_info.mime_type,
                    'modified_at': file_info.modified_at.isoformat()
                } if file_info else None
            }
            
        except Exception as e:
            log_error(f"File download error: {e}")
            return {
                'success': False,
                'error': f"Download failed: {str(e)}"
            }
    
    def batch_process_files(self, file_paths: List[str], operation: str) -> Dict[str, Any]:
        """Process multiple files in batch"""
        results = {
            'success': True,
            'processed': 0,
            'failed': 0,
            'errors': []
        }
        
        for file_path in file_paths:
            try:
                target_path = validate_workspace_path(file_path)
                if not target_path:
                    results['failed'] += 1
                    results['errors'].append(f"Invalid path: {file_path}")
                    continue
                
                # Process based on operation
                if operation == 'validate':
                    is_valid, message = self.validate_file(target_path)
                    if not is_valid:
                        results['failed'] += 1
                        results['errors'].append(f"{file_path}: {message}")
                    else:
                        results['processed'] += 1
                
                elif operation == 'info':
                    file_info = self.get_file_info(target_path)
                    if file_info:
                        results['processed'] += 1
                    else:
                        results['failed'] += 1
                        results['errors'].append(f"Could not get info for: {file_path}")
                
                else:
                    results['failed'] += 1
                    results['errors'].append(f"Unknown operation: {operation}")
                
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"{file_path}: {str(e)}")
        
        return results


def get_workspace_path() -> Path:
    """
    Get the configured workspace path, creating it if it doesn't exist.
    
    Returns:
        Path object for the workspace directory
    """
    try:
        from ..models import AppSetting
        
        # Try to get workspace path from settings if Flask context is available
        try:
            setting = AppSetting.query.filter_by(key='vybe_workspace_path').first()
            if setting and setting.value:
                workspace_path = Path(setting.value)
            else:
                # Default to vybe_workspace subdirectory in app root
                try:
                    app_root = Path(current_app.root_path).parent
                    workspace_path = app_root / 'vybe_workspace'
                except RuntimeError:
                    # No Flask context available, use fallback
                    workspace_path = Path.cwd() / 'workspace'
                
                # Save default path to settings if possible
                if not setting:
                    from ..models import db
                    try:
                        setting = AppSetting()
                        setting.key = 'vybe_workspace_path'
                        setting.value = str(workspace_path.absolute())
                        db.session.add(setting)
                        db.session.commit()
                    except Exception as e:
                        try:
                            db.session.rollback()
                        except:
                            pass
                        log_error(f"Failed to save workspace path setting: {e}")
                        # Continue anyway, we can use the default path
        except RuntimeError:
            # Flask context not available, use fallback
            workspace_path = Path.cwd() / 'workspace'
    
    except Exception as e:
        log_error(f"Error getting workspace path: {e}")
        # Ultimate fallback
        workspace_path = Path.cwd() / 'workspace'
    
    # Ensure workspace directory exists
    workspace_path.mkdir(parents=True, exist_ok=True)
    
    return workspace_path


def validate_workspace_path(relative_path: str) -> Optional[Path]:
    """
    Validate that a relative path stays within the workspace and return resolved path.
    
    Args:
        relative_path: Relative path within workspace
        
    Returns:
        Resolved Path object if valid, None if invalid
    """
    try:
        workspace = get_workspace_path()
        
        # Resolve the path and ensure it's within workspace
        resolved_path = (workspace / relative_path).resolve()
        
        # Check if resolved path is within workspace (prevents path traversal)
        if not str(resolved_path).startswith(str(workspace.resolve())):
            return None
            
        return resolved_path
    except (ValueError, OSError):
        return None


def ai_list_files_in_directory(path: str = "") -> str:
    """
    List files and directories within the AI workspace.
    
    Args:
        path: Relative path within workspace (empty string for root)
        
    Returns:
        Formatted string listing directory contents
    """
    try:
        target_path = validate_workspace_path(path)
        if not target_path:
            return f"Error: Invalid path '{path}' or path outside workspace."
            
        if not target_path.exists():
            return f"Error: Directory '{path}' does not exist in workspace."
            
        if not target_path.is_dir():
            return f"Error: '{path}' is not a directory."
        
        # List contents with file processor
        files = []
        directories = []
        
        for item in target_path.iterdir():
            file_info = get_file_processor().get_file_info(item)
            if file_info:
                if file_info.is_directory:
                    directories.append(file_info)
                else:
                    files.append(file_info)
        
        # Sort by name
        directories.sort(key=lambda x: x.name.lower())
        files.sort(key=lambda x: x.name.lower())
        
        # Format output
        result = f"Directory listing for '{path}':\n\n"
        
        if directories:
            result += "📁 Directories:\n"
            for dir_info in directories:
                result += f"  • {dir_info.name}/\n"
            result += "\n"
        
        if files:
            result += "📄 Files:\n"
            for file_info in files:
                size_str = f"{file_info.size:,} bytes" if file_info.size < 1024 else f"{file_info.size/1024:.1f} KB"
                result += f"  • {file_info.name} ({size_str}, {file_info.mime_type})\n"
        
        if not directories and not files:
            result += "  (empty directory)"
        
        return result
        
    except Exception as e:
        return f"Error listing directory '{path}': {str(e)}"


def ai_read_file(file_path: str) -> str:
    """
    Read content from a file within the AI workspace.
    
    Args:
        file_path: Relative path to file within workspace
        
    Returns:
        File content as string, or error message
    """
    try:
        target_path = validate_workspace_path(file_path)
        if not target_path:
            return f"Error: Invalid file path '{file_path}' or path outside workspace."
        
        if not target_path.exists():
            return f"Error: File '{file_path}' does not exist in workspace."
        
        if not target_path.is_file():
            return f"Error: '{file_path}' is not a file."
        
        # Validate file before reading
        is_valid, validation_message = get_file_processor().validate_file(target_path)
        if not is_valid:
            return f"Error: File validation failed - {validation_message}"
        
        # Log audit event for file read
        log_audit('READ', str(target_path), 'ai_assistant')
        
        # Read file content
        with open(target_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return f"File '{file_path}' content:\n\n{content}"
        
    except UnicodeDecodeError:
        return f"Error: File '{file_path}' contains binary data and cannot be read as text."
    except Exception as e:
        return f"Error reading file '{file_path}': {str(e)}"


def ai_write_file(file_path: str, content: str, mode: str = "w") -> str:
    """
    Write content to a file within the AI workspace with enhanced error handling and backup.
    
    Args:
        file_path: Relative path within workspace
        content: Content to write
        mode: File mode ('w' for write, 'a' for append)
        
    Returns:
        Success/error message
    """
    try:
        # Validate file path
        target_path = validate_workspace_path(file_path)
        if not target_path:
            return f"Error: Invalid file path '{file_path}' or path outside workspace."
        
        # Check for path traversal attempts
        if '..' in file_path or file_path.startswith('/') or ':' in file_path:
            return f"Error: Invalid file path '{file_path}' - path traversal not allowed."
        
        # Validate file mode
        if mode not in ['w', 'a']:
            return f"Error: Invalid file mode '{mode}'. Use 'w' for write or 'a' for append."
        
        # Check file size limits (prevent memory exhaustion)
        if len(content) > 10 * 1024 * 1024:  # 10MB limit
            return f"Error: File content too large ({len(content)} bytes). Maximum size: 10MB."
        
        # Check for potentially harmful content
        if contains_harmful_content(content):
            return f"Error: File content contains potentially harmful content."
        
        with safe_file_operation("file_write", file_path) as temp_files:
            # Create backup of existing file if it exists
            backup_info = None
            if target_path.exists() and mode == 'w':
                backup_info = get_backup_manager().create_backup(target_path)
                if backup_info:
                    log_info(f"Created backup before overwriting: {backup_info.backup_path}")
            
            # Ensure parent directory exists
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Check for file conflicts (if appending to existing file)
            if mode == 'a' and target_path.exists():
                # Check if file is currently being written by another process
                try:
                    with open(target_path, 'r') as f:
                        f.read(1)  # Try to read first byte
                except (PermissionError, OSError):
                    return f"Error: File '{file_path}' is currently in use by another process."
            
            # Write to temporary file first for atomic operation
            temp_file = target_path.with_suffix(target_path.suffix + '.tmp')
            temp_files.append(temp_file)
            
            if mode == 'a' and target_path.exists():
                # For append mode, copy existing content first
                shutil.copy2(target_path, temp_file)
                with open(temp_file, 'a', encoding='utf-8') as f:
                    f.write(content)
            else:
                # For write mode, write content directly
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            # Atomic rename to final location
            temp_file.replace(target_path)
            temp_files.remove(temp_file)  # Don't clean up, we moved it
            
            # Log audit event for file write
            log_audit('WRITE', str(target_path), 'ai_assistant')
            
            # Verify write success
            if not target_path.exists():
                if backup_info:
                    get_backup_manager().restore_backup(backup_info, verify_integrity=True)
                return f"Error: File write verification failed for '{file_path}'"
            
            log_info(f"Successfully wrote {len(content)} characters to '{file_path}'")
            return f"Successfully wrote {len(content)} characters to '{file_path}'."
        
    except FileOperationError as e:
        log_error(f"File operation error writing '{file_path}': {e}")
        return f"Error: {e}"
    except PermissionError:
        return f"Error: Permission denied writing to '{file_path}'."
    except OSError as e:
        return f"Error writing file '{file_path}': {str(e)}"
    except Exception as e:
        log_error(f"Unexpected error writing file '{file_path}': {e}")
        return f"Unexpected error writing file '{file_path}': {str(e)}"


def contains_harmful_content(content: str) -> bool:
    """
    Check if content contains potentially harmful patterns.
    
    Args:
        content: Content to check
        
    Returns:
        True if harmful content detected, False otherwise
    """
    harmful_patterns = [
        r'<script[^>]*>',  # Script tags
        r'javascript:',     # JavaScript protocol
        r'data:text/html',  # Data URLs
        r'vbscript:',       # VBScript protocol
        r'<iframe[^>]*>',   # Iframe tags
        r'<object[^>]*>',   # Object tags
        r'<embed[^>]*>',    # Embed tags
        r'<form[^>]*>',     # Form tags with potential for CSRF
    ]
    
    import re
    content_lower = content.lower()
    
    for pattern in harmful_patterns:
        if re.search(pattern, content_lower, re.IGNORECASE):
            return True
    
    return False


def ai_delete_file(file_path: str) -> str:
    """
    Delete a file or empty directory within the AI workspace.
    
    Args:
        file_path: Relative path within workspace
        
    Returns:
        Success/error message
    """
    try:
        target_path = validate_workspace_path(file_path)
        if not target_path:
            return f"Error: Invalid file path '{file_path}' or path outside workspace."
        
        if not target_path.exists():
            return f"Error: File or directory '{file_path}' does not exist in workspace."
        
        # Check if it's a directory
        if target_path.is_dir():
            # Only allow deletion of empty directories
            if any(target_path.iterdir()):
                return f"Error: Directory '{file_path}' is not empty. Please remove contents first."
            
            target_path.rmdir()
            return f"Successfully deleted empty directory '{file_path}'."
        else:
            # Delete file
            target_path.unlink()
            return f"Successfully deleted file '{file_path}'."
        
    except PermissionError:
        return f"Error: Permission denied deleting '{file_path}'."
    except OSError as e:
        return f"Error deleting '{file_path}': {str(e)}"
    except Exception as e:
        return f"Unexpected error deleting '{file_path}': {str(e)}"


def ai_query_rag_collections_wrapper(query: str, collection_names: str = "") -> str:
    """
    AI tool wrapper for querying RAG collections.
    
    Args:
        query: The natural language query to ask the RAG system
        collection_names: Comma-separated list of collection names (optional)
        
    Returns:
        Combined relevant chunks of text as a single string
    """
    from ..tools import ai_query_rag_collections
    
    # Parse collection names if provided
    collections_list = None
    if collection_names.strip():
        collections_list = [name.strip() for name in collection_names.split(',') if name.strip()]
    
    return ai_query_rag_collections(query, collections_list)


def get_enabled_tools() -> list:
    """
    Get list of currently enabled tools from settings.
    
    Returns:
        List of enabled tool names
    """
    from ..models import AppSetting
    
    setting = AppSetting.query.filter_by(key='enabled_tools').first()
    if setting and setting.value:
        try:
            return json.loads(setting.value)
        except json.JSONDecodeError:
            return []
    
    # Default enabled tools if no setting exists
    return ['ai_list_files_in_directory', 'ai_read_file', 'ai_write_file', 'ai_delete_file', 'web_search', 'ai_query_rag_collections']


def set_enabled_tools(tool_list: list) -> bool:
    """
    Set the list of enabled tools.
    
    Args:
        tool_list: List of tool names to enable
        
    Returns:
        True if successful, False otherwise
    """
    try:
        from ..models import db, AppSetting
        
        setting = AppSetting.query.filter_by(key='enabled_tools').first()
        if not setting:
            setting = AppSetting()
            setting.key = 'enabled_tools'
        
        setting.value = json.dumps(tool_list)
        db.session.add(setting)
        db.session.commit()
        return True
    except Exception as e:
        try:
            db.session.rollback()
        except:
            pass  # In case db.session is not available
        log_error(f"Failed to save enabled tools: {e}")
        return False


def is_tool_enabled(tool_name: str) -> bool:
    """
    Check if a specific tool is enabled.
    
    Args:
        tool_name: Name of the tool to check
        
    Returns:
        True if enabled, False otherwise
    """
    enabled_tools = get_enabled_tools()
    return tool_name in enabled_tools


# Tool registry for easy access
AVAILABLE_TOOLS = {
    'ai_list_files_in_directory': {
        'function': ai_list_files_in_directory,
        'description': 'List files and directories in the AI workspace',
        'category': 'File Management'
    },
    'ai_write_file': {
        'function': ai_write_file,
        'description': 'Write content to a file in the AI workspace',
        'category': 'File Management'
    },
    'ai_read_file': {
        'function': ai_read_file,
        'description': 'Read content from a file in the AI workspace',
        'category': 'File Management'
    },
    'ai_delete_file': {
        'function': ai_delete_file,
        'description': 'Delete a file or empty directory in the AI workspace',
        'category': 'File Management'
    },
    'ai_query_rag_collections': {
        'function': ai_query_rag_collections_wrapper,
        'description': 'Query specific RAG collections or all available collections for relevant information',
        'category': 'Knowledge Retrieval'
    },
    'web_search': {
        'function': None,  # Import and set below
        'description': 'Search the web for information',
        'category': 'Information Retrieval'
    }
}

# Import and set the web_search function
try:
    from ..tools import web_search
    AVAILABLE_TOOLS['web_search']['function'] = web_search
except ImportError:
    # web_search function not available
    pass


def call_ai_tool(tool_name: str, **kwargs) -> str:
    """
    Call an AI tool if it's enabled and available.
    
    Args:
        tool_name: Name of the tool to call
        **kwargs: Arguments to pass to the tool
        
    Returns:
        Tool result or error message
    """
    if not is_tool_enabled(tool_name):
        return f"Error: Tool '{tool_name}' is disabled. Enable it in Settings > Tool Management."
    
    if tool_name not in AVAILABLE_TOOLS:
        return f"Error: Tool '{tool_name}' is not available."
    
    tool_info = AVAILABLE_TOOLS[tool_name]
    if tool_info['function'] is None:
        return f"Error: Tool '{tool_name}' requires special handling."
    
    try:
        return tool_info['function'](**kwargs)
    except TypeError as e:
        return f"Error calling tool '{tool_name}': {str(e)}"
    except Exception as e:
        return f"Error in tool '{tool_name}': {str(e)}"


# Global instances - use lazy initialization to avoid Flask context issues
backup_manager = None
file_processor = None

def get_backup_manager():
    """Get or create backup manager instance"""
    global backup_manager
    if backup_manager is None:
        backup_manager = BackupManager()
    return backup_manager

def get_file_processor():
    """Get or create file processor instance"""
    global file_processor
    if file_processor is None:
        file_processor = FileProcessor()
    return file_processor
