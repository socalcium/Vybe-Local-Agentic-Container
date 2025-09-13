"""
Validation utilities for CLI commands
"""

import os
import re
import time
from pathlib import Path
from typing import Tuple, Dict, Any, Optional
from ..logger import log_error, log_info


def check_rate_limit(command_name: str) -> Tuple[bool, str]:
    """Check rate limiting for commands"""
    try:
        # Simple rate limiting - can be enhanced with Redis/database
        current_time = time.time()
        # For now, just return success
        return True, ""
    except Exception as e:
        log_error(f"Rate limiting check failed: {e}")
        return True, ""  # Allow on error


def validate_file_access(filepath: str) -> bool:
    """Validate file access permissions"""
    try:
        abs_path = os.path.abspath(filepath)
        safe_dir = os.path.abspath("workspace")
        
        # Check if file is within safe directory
        if not abs_path.startswith(safe_dir):
            return False
        
        # Check if file exists and is readable
        return os.path.isfile(abs_path) and os.access(abs_path, os.R_OK)
    except Exception as e:
        log_error(f"File access validation failed: {e}")
        return False


def validate_file_size(filepath: str, max_size_mb: int = 50) -> Tuple[bool, str]:
    """Validate file size"""
    try:
        file_size = os.path.getsize(filepath)
        max_size_bytes = max_size_mb * 1024 * 1024
        
        if file_size > max_size_bytes:
            return False, f"File too large: {file_size / (1024*1024):.1f}MB (max: {max_size_mb}MB)"
        
        return True, ""
    except Exception as e:
        log_error(f"File size validation failed: {e}")
        return False, f"Error checking file size: {e}"


def scan_for_malicious_content(filepath: str) -> Tuple[bool, str]:
    """Scan file for potentially malicious content"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(1024)  # Read first 1KB for scanning
        
        # Check for suspicious patterns
        suspicious_patterns = [
            r'<script[^>]*>',
            r'javascript:',
            r'data:text/html',
            r'vbscript:',
            r'onload\s*=',
            r'onerror\s*=',
            r'eval\s*\(',
            r'exec\s*\(',
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return False, f"Potentially malicious content detected: {pattern}"
        
        return True, ""
    except Exception as e:
        log_error(f"Malicious content scan failed: {e}")
        return False, f"Error scanning file: {e}"


def validate_content(content: str) -> bool:
    """Validate content is text-based and safe"""
    try:
        # Check if content is mostly text
        text_chars = sum(1 for c in content if c.isprintable() or c.isspace())
        text_ratio = text_chars / len(content) if content else 0
        
        if text_ratio < 0.8:  # Less than 80% printable characters
            return False
        
        # Check for null bytes or other binary indicators
        if '\x00' in content:
            return False
        
        return True
    except Exception as e:
        log_error(f"Content validation failed: {e}")
        return False


def log_command_usage(command: str, success: bool, details: Optional[Dict[str, Any]] = None):
    """Log command usage for analytics"""
    try:
        log_info(f"Command executed: {command} - Success: {success} - Details: {details or {}}")
    except Exception as e:
        log_error(f"Failed to log command usage: {e}")


def get_safe_directory() -> str:
    """Get the safe directory for file operations"""
    return os.path.abspath("workspace")


def validate_directory_access(dirpath: str) -> bool:
    """Validate directory access permissions"""
    try:
        abs_path = os.path.abspath(dirpath)
        safe_dir = os.path.abspath("workspace")
        
        # Check if directory is within safe directory
        if not abs_path.startswith(safe_dir):
            return False
        
        # Check if directory exists and is readable
        return os.path.isdir(abs_path) and os.access(abs_path, os.R_OK)
    except Exception as e:
        log_error(f"Directory access validation failed: {e}")
        return False
