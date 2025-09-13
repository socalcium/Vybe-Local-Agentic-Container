#!/usr/bin/env python3
"""
Enhanced Input Validation Utilities for Vybe AI Desktop Application
Provides robust input validation, sanitization, and advanced security features
"""

import re
import json
import os
import html
import urllib.parse
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
    magic = None
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple, Callable
from flask import request, jsonify
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom exception for validation errors"""
    def __init__(self, message: str, field: Optional[str] = None, code: Optional[str] = None):
        super().__init__(message)
        self.field = field
        self.code = code
        self.message = message


class SecurityValidator:
    """Advanced security validation and threat detection"""
    
    # Security threat patterns
    THREAT_PATTERNS = {
        'sql_injection': [
            # Basic SQL injection patterns
            r"(?i)(union\s+select|or\s+1\s*=\s*1|drop\s+table|insert\s+into|delete\s+from)",
            r"(?i)(select\s+.*from\s+|insert\s+into\s+|update\s+.*set\s+|delete\s+from\s+)",
            r"(?i)(\'\s*or\s*\'\s*=\s*\'|\"\s*or\s*\"\s*=\s*\")",
            r"(?i)(exec\s*\(|execute\s*\(|sp_executesql)",
            
            # Enhanced SQL syntax patterns
            r"(?i)(--\s|/\*.*\*/|#\s)",  # SQL comments
            r"(?i)(;\s*drop\s+|;\s*delete\s+|;\s*insert\s+|;\s*update\s+)",  # Stacked queries
            r"(?i)(or\s+1\s*=\s*1|and\s+1\s*=\s*1|or\s+true|and\s+false)",  # Boolean-based injection
            r"(?i)(information_schema|sys\.tables|mysql\.user|pg_catalog)",  # System table access
            r"(?i)(char\s*\(|ascii\s*\(|substring\s*\(|concat\s*\()",  # SQL functions often used in injection
            r"(?i)(waitfor\s+delay|benchmark\s*\(|sleep\s*\(|pg_sleep\s*\()",  # Time-based injection
            r"(?i)(load_file\s*\(|into\s+outfile|into\s+dumpfile)",  # File operations
            r"(?i)(\'\s*\+\s*\'|\"\s*\+\s*\"|concat\s*\(\s*\')",  # String concatenation patterns
            r"(?i)(having\s+.*group\s+by|group\s+by\s+.*having)",  # HAVING/GROUP BY exploitation
            r"(?i)(0x[0-9a-f]+|char\([0-9,\s]+\))",  # Hex encoding and CHAR() functions
        ],
        'xss': [
            r"(?i)(<script[^>]*>.*?</script>|javascript:|vbscript:)",
            r"(?i)(onload\s*=|onerror\s*=|onclick\s*=|onmouseover\s*=)",
            r"(?i)(<iframe|<object|<embed|<applet)",
            r"(?i)(expression\s*\(|url\s*\(|@import)"
        ],
        'command_injection': [
            r"(?i)(;\s*rm\s+|;\s*cat\s+|;\s*ls\s+|;\s*pwd)",
            r"(?i)(\|\s*nc\s+|\|\s*netcat|\|\s*wget|\|\s*curl)",
            r"(?i)(&&\s*rm\s+|&&\s*cat\s+|`.*`|\$\(.*\))"
        ],
        'path_traversal': [
            r"(\.\./|\.\.\backslash|%2e%2e%2f|%2e%2e%5c)",
            r"(?i)(\.\.\\|\.\.\/|%252e%252e%252f)",
            r"(?i)(file://|ftp://|gopher://)"
        ],
        'ldap_injection': [
            r"(\*|\)|\(|\|\||&|\|)",
            r"(?i)(objectclass=|cn=|uid=|ou=)"
        ],
        'nosql_injection': [
            r"(?i)(\$ne|\$gt|\$lt|\$gte|\$lte|\$in|\$nin)",
            r"(?i)(\$where|\$regex|\$exists|\$size)"
        ]
    }
    
    def __init__(self):
        self.compiled_patterns = {}
        for category, patterns in self.THREAT_PATTERNS.items():
            self.compiled_patterns[category] = [re.compile(pattern) for pattern in patterns]
    
    def scan_for_threats(self, data: str) -> Dict[str, List[str]]:
        """Scan input data for security threats"""
        threats = {}
        
        for category, patterns in self.compiled_patterns.items():
            matches = []
            for pattern in patterns:
                if pattern.search(data):
                    matches.append(pattern.pattern)
            
            if matches:
                threats[category] = matches
        
        return threats
    
    def is_safe_content(self, content: str, allowed_threats: Optional[List[str]] = None) -> bool:
        """Check if content is safe from security threats"""
        allowed_threats = allowed_threats or []
        threats = self.scan_for_threats(content)
        
        # Remove allowed threat types
        for allowed in allowed_threats:
            threats.pop(allowed, None)
        
        return len(threats) == 0


class AdvancedInputValidator:
    """Enhanced input validation with security features"""
    
    # Enhanced validation patterns
    PATTERNS = {
        'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        'username': r'^[a-zA-Z0-9_-]{3,20}$',
        'password': r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d@$!%*?&]{8,}$',
        'strong_password': r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{12,}$',
        'filename': r'^[a-zA-Z0-9._-]+$',
        'safe_filename': r'^[a-zA-Z0-9._-]{1,255}$',
        'url': r'^https?://[^\s/$.?#].[^\s]*$',
        'secure_url': r'^https://[^\s/$.?#].[^\s]*$',
        'ip_address': r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$',
        'ipv6_address': r'^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$',
        'port': r'^[1-9]\d{0,4}$',
        'uuid': r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        'hex_color': r'^#[0-9a-fA-F]{6}$',
        'date_iso': r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{3})?Z?$',
        'safe_string': r'^[a-zA-Z0-9\s\-_.,!?()]+$',
        'alphanumeric': r'^[a-zA-Z0-9]+$',
        'api_key': r'^[a-zA-Z0-9_-]{32,}$',
        'jwt_token': r'^[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+$',
        'model_name': r'^[a-zA-Z0-9\-_.]{1,100}$',
        'system_prompt': r'^[a-zA-Z0-9\s\-_.,!?()\[\]{}\'\":\n\r]{1,5000}$'
    }
    
    # Enhanced file type restrictions
    ALLOWED_EXTENSIONS = {
        'image': {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.ico'},
        'audio': {'.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac', '.wma'},
        'video': {'.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv'},
        'document': {'.pdf', '.txt', '.md', '.doc', '.docx', '.rtf', '.odt'},
        'archive': {'.zip', '.tar', '.gz', '.rar', '.7z', '.bz2'},
        'code': {'.py', '.js', '.html', '.css', '.json', '.xml', '.yaml', '.yml', '.toml'},
        'model': {'.gguf', '.bin', '.safetensors', '.pt', '.pth'},
        'data': {'.csv', '.tsv', '.jsonl', '.parquet'}
    }
    
    # Content length limits
    CONTENT_LIMITS = {
        'username': 20,
        'email': 254,
        'password': 128,
        'filename': 255,
        'url': 2048,
        'message': 10000,
        'system_prompt': 5000,
        'description': 1000,
        'title': 200,
        'api_key': 128,
        'general_text': 5000
    }
    
    def __init__(self):
        self.security_validator = SecurityValidator()
        self.compiled_patterns = {
            name: re.compile(pattern) 
            for name, pattern in self.PATTERNS.items()
        }
    
    def validate_field(self, value: Any, field_type: str, field_name: Optional[str] = None, 
                      required: bool = True, custom_pattern: Optional[str] = None,
                      min_length: Optional[int] = None, max_length: Optional[int] = None,
                      security_check: bool = True) -> Any:
        """Enhanced field validation with security checks"""
        
        # Handle None/empty values
        if value is None or (isinstance(value, str) and not value.strip()):
            if required:
                raise ValidationError(f"Field '{field_name or field_type}' is required", field_name, "required")
            return value
        
        # Convert to string for validation
        str_value = str(value).strip()
        
        # Security threat scanning
        if security_check and isinstance(value, str):
            threats = self.security_validator.scan_for_threats(str_value)
            if threats:
                logger.warning(f"Security threats detected in field '{field_name}': {threats}")
                raise ValidationError(
                    f"Security violation detected in field '{field_name or field_type}'",
                    field_name, "security_violation"
                )
        
        # Length validation
        content_limit = max_length or self.CONTENT_LIMITS.get(field_type, 1000)
        if len(str_value) > content_limit:
            raise ValidationError(
                f"Field '{field_name or field_type}' exceeds maximum length of {content_limit}",
                field_name, "max_length"
            )
        
        if min_length and len(str_value) < min_length:
            raise ValidationError(
                f"Field '{field_name or field_type}' must be at least {min_length} characters",
                field_name, "min_length"
            )
        
        # Pattern validation
        pattern = custom_pattern or self.PATTERNS.get(field_type)
        if pattern:
            compiled_pattern = re.compile(pattern) if isinstance(pattern, str) else self.compiled_patterns.get(field_type)
            if compiled_pattern and not compiled_pattern.match(str_value):
                raise ValidationError(
                    f"Field '{field_name or field_type}' has invalid format",
                    field_name, "invalid_format"
                )
        
        # Type-specific validation
        return self._validate_specific_type(value, field_type, field_name)
    
    def _validate_specific_type(self, value: Any, field_type: str, field_name: Optional[str]) -> Any:
        """Type-specific validation logic"""
        
        if field_type == 'email':
            return self._validate_email(value, field_name or 'email')
        elif field_type == 'password':
            return self._validate_password(value, field_name or 'password')
        elif field_type == 'url':
            return self._validate_url(value, field_name or 'url')
        elif field_type == 'filename':
            return self._validate_filename(value, field_name or 'filename')
        elif field_type == 'json':
            return self._validate_json(value, field_name or 'json')
        elif field_type in ['port', 'integer']:
            return self._validate_integer(value, field_name or 'integer')
        elif field_type == 'float':
            return self._validate_float(value, field_name or 'float')
        elif field_type == 'boolean':
            return self._validate_boolean(value, field_name or 'boolean')
        elif field_type == 'api_key':
            return self._validate_api_key(value, field_name or 'api_key')
        
        return value
    
    def _validate_email(self, value: str, field_name: str) -> str:
        """Enhanced email validation"""
        email = value.lower().strip()
        
        # Check for dangerous characters
        dangerous_chars = ['<', '>', '"', '\'', '&', '\n', '\r', '\t']
        if any(char in email for char in dangerous_chars):
            raise ValidationError(f"Email contains invalid characters", field_name, "invalid_email")
        
        # Additional domain validation
        if '@' in email:
            domain = email.split('@')[1]
            if len(domain) > 253 or '..' in domain:
                raise ValidationError(f"Invalid email domain", field_name, "invalid_email")
        
        return email
    
    def _validate_password(self, value: str, field_name: str) -> str:
        """Enhanced password validation"""
        # Check for common weak patterns
        weak_patterns = [
            r'12345', r'password', r'qwerty', r'admin', r'letmein',
            r'welcome', r'monkey', r'login', r'abc123'
        ]
        
        value_lower = value.lower()
        for pattern in weak_patterns:
            if pattern in value_lower:
                raise ValidationError(
                    f"Password contains common weak pattern", 
                    field_name, "weak_password"
                )
        
        # Check for repeated characters (more than 3 in a row)
        if re.search(r'(.)\1{3,}', value):
            raise ValidationError(
                f"Password contains too many repeated characters", 
                field_name, "weak_password"
            )
        
        return value
    
    def _validate_url(self, value: str, field_name: str) -> str:
        """Enhanced URL validation"""
        # URL decode to check for obfuscated malicious content
        decoded_url = urllib.parse.unquote(value)
        
        # Check for suspicious schemes
        suspicious_schemes = ['javascript:', 'data:', 'vbscript:', 'file:', 'ftp:']
        for scheme in suspicious_schemes:
            if decoded_url.lower().startswith(scheme):
                raise ValidationError(f"URL scheme not allowed", field_name, "invalid_url")
        
        # Check for IP addresses instead of domains (potential security risk)
        parsed = urllib.parse.urlparse(value)
        if parsed.hostname and re.match(r'^\d+\.\d+\.\d+\.\d+$', parsed.hostname):
            logger.warning(f"URL uses IP address instead of domain: {value}")
        
        return value
    
    def _validate_filename(self, value: str, field_name: str) -> str:
        """Enhanced filename validation"""
        # Check for path traversal
        if '..' in value or '/' in value or '\\' in value:
            raise ValidationError(f"Filename contains path traversal", field_name, "invalid_filename")
        
        # Check for suspicious extensions
        suspicious_extensions = ['.exe', '.bat', '.cmd', '.com', '.scr', '.pif', '.vbs', '.js', '.jar']
        ext = Path(value).suffix.lower()
        if ext in suspicious_extensions:
            raise ValidationError(f"File extension not allowed", field_name, "invalid_filename")
        
        return value
    
    def _validate_json(self, value: Union[str, dict], field_name: str) -> dict:
        """JSON validation"""
        if isinstance(value, dict):
            return value
        
        try:
            parsed = json.loads(value)
            if not isinstance(parsed, dict):
                raise ValidationError(f"JSON must be an object", field_name, "invalid_json")
            return parsed
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON format: {str(e)}", field_name, "invalid_json")
    
    def _validate_integer(self, value: Union[str, int], field_name: str) -> int:
        """Integer validation"""
        try:
            return int(value)
        except (ValueError, TypeError):
            raise ValidationError(f"Invalid integer value", field_name, "invalid_integer")
    
    def _validate_float(self, value: Union[str, float, int], field_name: str) -> float:
        """Float validation"""
        try:
            return float(value)
        except (ValueError, TypeError):
            raise ValidationError(f"Invalid float value", field_name, "invalid_float")
    
    def _validate_boolean(self, value: Union[str, bool], field_name: str) -> bool:
        """Boolean validation"""
        if isinstance(value, bool):
            return value
        
        if isinstance(value, str):
            if value.lower() in ['true', '1', 'yes', 'on']:
                return True
            elif value.lower() in ['false', '0', 'no', 'off']:
                return False
        
        raise ValidationError(f"Invalid boolean value", field_name, "invalid_boolean")
    
    def _validate_api_key(self, value: str, field_name: str) -> str:
        """API key validation"""
        # Additional entropy check for API keys
        if len(set(value)) < len(value) * 0.6:  # Less than 60% unique characters
            raise ValidationError(f"API key has insufficient entropy", field_name, "weak_api_key")
        
        return value
    
    def sanitize_html(self, value: str) -> str:
        """Sanitize HTML content"""
        return html.escape(value)
    
    def sanitize_sql(self, value: str) -> str:
        """Basic SQL sanitization"""
        # Remove common SQL injection patterns
        dangerous_patterns = [
            r"'", r'"', r';', r'--', r'/*', r'*/', r'xp_', r'sp_'
        ]
        
        sanitized = value
        for pattern in dangerous_patterns:
            sanitized = sanitized.replace(pattern, '')
        
        return sanitized


class InputValidator(AdvancedInputValidator):
    """Legacy compatibility class - extends AdvancedInputValidator"""
    
    # Size limits (in bytes)
    SIZE_LIMITS = {
        'image': 10 * 1024 * 1024,  # 10MB
        'audio': 50 * 1024 * 1024,  # 50MB
        'video': 500 * 1024 * 1024,  # 500MB
        'document': 20 * 1024 * 1024,  # 20MB
        'archive': 100 * 1024 * 1024,  # 100MB
        'code': 5 * 1024 * 1024,  # 5MB
        'default': 10 * 1024 * 1024  # 10MB
    }
    
    @classmethod
    def validate_json_request(cls, required_fields: Optional[List[str]] = None, 
                            optional_fields: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Validate JSON request data
        
        Args:
            required_fields: List of required field names
            optional_fields: Dict of field_name: validation_rules for optional fields
            
        Returns:
            Validated and sanitized data
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            if not request.is_json:
                raise ValidationError("Request must be JSON")
            
            data = request.get_json()
            if data is None:
                raise ValidationError("Invalid JSON data")
            
            # Validate required fields
            if required_fields is not None:
                for field in required_fields:
                    if field not in data:
                        raise ValidationError(f"Missing required field: {field}")
                    if data[field] is None:
                        raise ValidationError(f"Required field cannot be null: {field}")
            
            # Validate optional fields
            if optional_fields is not None:
                for field, rules in optional_fields.items():
                    if field in data and data[field] is not None:
                        cls._validate_field(field, data[field], rules)
            
            return data
            
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Request validation failed: {str(e)}")
    
    @classmethod
    def validate_form_data(cls, required_fields: Optional[List[str]] = None,
                          optional_fields: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Validate form data
        
        Args:
            required_fields: List of required field names
            optional_fields: Dict of field_name: validation_rules for optional fields
            
        Returns:
            Validated and sanitized data
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            data = request.form.to_dict()
            
            # Validate required fields
            if required_fields:
                for field in required_fields:
                    if field not in data or not data[field]:
                        raise ValidationError(f"Missing required field: {field}")
            
            # Validate optional fields
            if optional_fields:
                for field, rules in optional_fields.items():
                    if field in data and data[field]:
                        cls._validate_field(field, data[field], rules)
            
            return data
            
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Form validation failed: {str(e)}")
    
    @classmethod
    def validate_file_upload(cls, field_name: str, allowed_types: Optional[List[str]] = None,
                           max_size: Optional[int] = None, required: bool = True) -> Optional[Dict[str, Any]]:
        """
        Validate file upload
        
        Args:
            field_name: Name of the file field
            allowed_types: List of allowed file types (e.g., ['image', 'document'])
            max_size: Maximum file size in bytes
            required: Whether the file is required
            
        Returns:
            File information if valid
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            if field_name not in request.files:
                if required:
                    raise ValidationError(f"Missing required file: {field_name}")
                return None
            
            file = request.files[field_name]
            
            if file.filename == '':
                if required:
                    raise ValidationError(f"Empty file provided for: {field_name}")
                return None
            
            # Validate file extension
            if allowed_types:
                if file.filename is None:
                    raise ValidationError("File has no filename")
                file_ext = Path(file.filename).suffix.lower()
                allowed_extensions = set()
                for file_type in allowed_types:
                    if file_type in cls.ALLOWED_EXTENSIONS:
                        allowed_extensions.update(cls.ALLOWED_EXTENSIONS[file_type])
                
                if file_ext not in allowed_extensions:
                    raise ValidationError(f"File type not allowed: {file_ext}")
                
                # Enhanced security: Validate content against extension using magic numbers
                cls._validate_file_content(file, file_ext)
            
            # Validate file size
            if max_size is None:
                # Use default size limit based on file type
                if file.filename is None:
                    raise ValidationError("File has no filename")
                file_ext = Path(file.filename).suffix.lower()
                file_type = cls._get_file_type(file_ext)
                max_size = cls.SIZE_LIMITS.get(file_type, cls.SIZE_LIMITS['default'])
            
            # Read file size (this might not work for all file objects)
            file.seek(0, 2)  # Seek to end
            file_size = file.tell()
            file.seek(0)  # Reset to beginning
            
            if file_size > max_size:
                raise ValidationError(f"File too large: {file_size} bytes (max: {max_size})")
            
            return {
                'filename': file.filename,
                'content_type': file.content_type,
                'size': file_size,
                'file': file
            }
            
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"File validation failed: {str(e)}")
    
    @classmethod
    def validate_path(cls, path_str: str, must_exist: bool = False, 
                     must_be_file: bool = False, must_be_dir: bool = False,
                     allow_absolute: bool = False) -> Path:
        """
        Validate and sanitize file path
        
        Args:
            path_str: Path string to validate
            must_exist: Whether the path must exist
            must_be_file: Whether the path must be a file
            must_be_dir: Whether the path must be a directory
            allow_absolute: Whether absolute paths are allowed
            
        Returns:
            Path object if valid
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            # Basic path validation
            if not path_str or not isinstance(path_str, str):
                raise ValidationError("Invalid path provided")
            
            # Check for path traversal attempts
            if '..' in path_str or '//' in path_str:
                raise ValidationError("Path traversal not allowed")
            
            # Convert to Path object
            if path_str is None:
                raise ValidationError("Path cannot be None")
            path = Path(path_str)
            
            # Check for absolute paths
            if not allow_absolute and path.is_absolute():
                raise ValidationError("Absolute paths not allowed")
            
            # Check if path exists
            if must_exist and not path.exists():
                raise ValidationError(f"Path does not exist: {path_str}")
            
            # Check if it's a file
            if must_be_file and not path.is_file():
                raise ValidationError(f"Path is not a file: {path_str}")
            
            # Check if it's a directory
            if must_be_dir and not path.is_dir():
                raise ValidationError(f"Path is not a directory: {path_str}")
            
            return path
            
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Path validation failed: {str(e)}")
    
    @classmethod
    def validate_string(cls, value: str, min_length: int = 0, max_length: Optional[int] = None,
                       pattern: Optional[str] = None, allowed_chars: Optional[str] = None) -> str:
        """
        Validate string value
        
        Args:
            value: String to validate
            min_length: Minimum length
            max_length: Maximum length
            pattern: Regex pattern to match
            allowed_chars: String of allowed characters
            
        Returns:
            Sanitized string if valid
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            if not isinstance(value, str):
                raise ValidationError("Value must be a string")
            
            # Check length
            if len(value) < min_length:
                raise ValidationError(f"String too short (min: {min_length})")
            
            if max_length and len(value) > max_length:
                raise ValidationError(f"String too long (max: {max_length})")
            
            # Check pattern
            if pattern:
                if pattern in cls.PATTERNS:
                    pattern = cls.PATTERNS[pattern]
                if not re.match(pattern, value):
                    raise ValidationError(f"String does not match pattern: {pattern}")
            
            # Check allowed characters
            if allowed_chars:
                if not all(c in allowed_chars for c in value):
                    raise ValidationError(f"String contains disallowed characters")
            
            return value.strip()
            
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"String validation failed: {str(e)}")
    
    @classmethod
    def validate_integer(cls, value: Any, min_value: Optional[int] = None, max_value: Optional[int] = None) -> int:
        """
        Validate integer value
        
        Args:
            value: Value to validate
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            
        Returns:
            Integer if valid
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            # Convert to int
            if isinstance(value, str):
                value = int(value)
            elif not isinstance(value, int):
                raise ValidationError("Value must be an integer")
            
            # Check range
            if min_value is not None and value < min_value:
                raise ValidationError(f"Value too small (min: {min_value})")
            
            if max_value is not None and value > max_value:
                raise ValidationError(f"Value too large (max: {max_value})")
            
            return value
            
        except (ValueError, TypeError):
            raise ValidationError("Invalid integer value")
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Integer validation failed: {str(e)}")
    
    @classmethod
    def validate_float(cls, value: Any, min_value: Optional[float] = None, max_value: Optional[float] = None) -> float:
        """
        Validate float value
        
        Args:
            value: Value to validate
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            
        Returns:
            Float if valid
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            # Convert to float
            if isinstance(value, str):
                value = float(value)
            elif not isinstance(value, (int, float)):
                raise ValidationError("Value must be a number")
            
            # Check range
            if min_value is not None and value < min_value:
                raise ValidationError(f"Value too small (min: {min_value})")
            
            if max_value is not None and value > max_value:
                raise ValidationError(f"Value too large (max: {max_value})")
            
            return float(value)
            
        except (ValueError, TypeError):
            raise ValidationError("Invalid number value")
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Float validation failed: {str(e)}")
    
    @classmethod
    def validate_boolean(cls, value: Any) -> bool:
        """
        Validate boolean value
        
        Args:
            value: Value to validate
            
        Returns:
            Boolean if valid
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            if isinstance(value, bool):
                return value
            elif isinstance(value, str):
                value_lower = value.lower()
                if value_lower in ('true', '1', 'yes', 'on'):
                    return True
                elif value_lower in ('false', '0', 'no', 'off'):
                    return False
                else:
                    raise ValidationError("Invalid boolean value")
            elif isinstance(value, int):
                return bool(value)
            else:
                raise ValidationError("Value must be a boolean")
                
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Boolean validation failed: {str(e)}")
    
    @classmethod
    def validate_list(cls, value: Any, min_length: int = 0, max_length: Optional[int] = None,
                     item_validator: Optional[Callable] = None) -> List:
        """
        Validate list value
        
        Args:
            value: Value to validate
            min_length: Minimum list length
            max_length: Maximum list length
            item_validator: Function to validate each item
            
        Returns:
            List if valid
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            if not isinstance(value, list):
                raise ValidationError("Value must be a list")
            
            # Check length
            if len(value) < min_length:
                raise ValidationError(f"List too short (min: {min_length})")
            
            if max_length and len(value) > max_length:
                raise ValidationError(f"List too long (max: {max_length})")
            
            # Validate items
            if item_validator:
                validated_items = []
                for i, item in enumerate(value):
                    try:
                        validated_items.append(item_validator(item))
                    except Exception as e:
                        raise ValidationError(f"Invalid item at index {i}: {str(e)}")
                return validated_items
            
            return value
            
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"List validation failed: {str(e)}")
    
    @classmethod
    def sanitize_html(cls, html_content: str) -> str:
        """
        Basic HTML sanitization (remove script tags and dangerous attributes)
        
        Args:
            html_content: HTML content to sanitize
            
        Returns:
            Sanitized HTML content
        """
        if not html_content:
            return html_content
        
        # Remove script tags and their content
        html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove dangerous attributes
        dangerous_attrs = ['onclick', 'onload', 'onerror', 'onmouseover', 'onfocus', 'onblur']
        for attr in dangerous_attrs:
            html_content = re.sub(rf'{attr}\s*=\s*["\'][^"\']*["\']', '', html_content, flags=re.IGNORECASE)
        
        # Remove javascript: URLs
        html_content = re.sub(r'javascript:', '', html_content, flags=re.IGNORECASE)
        
        return html_content
    
    @classmethod
    def _validate_field(cls, field_name: str, value: Any, rules: Dict[str, Any]):
        """Internal method to validate a field based on rules"""
        try:
            # Type validation
            if 'type' in rules:
                expected_type = rules['type']
                if expected_type == 'string':
                    value = cls.validate_string(value, 
                                              min_length=rules.get('min_length', 0),
                                              max_length=rules.get('max_length'),
                                              pattern=rules.get('pattern'),
                                              allowed_chars=rules.get('allowed_chars'))
                elif expected_type == 'integer':
                    value = cls.validate_integer(value,
                                               min_value=rules.get('min_value'),
                                               max_value=rules.get('max_value'))
                elif expected_type == 'float':
                    value = cls.validate_float(value,
                                             min_value=rules.get('min_value'),
                                             max_value=rules.get('max_value'))
                elif expected_type == 'boolean':
                    value = cls.validate_boolean(value)
                elif expected_type == 'list':
                    value = cls.validate_list(value,
                                            min_length=rules.get('min_length', 0),
                                            max_length=rules.get('max_length'),
                                            item_validator=rules.get('item_validator'))
            
            # Custom validation
            if 'custom_validator' in rules:
                custom_validator = rules['custom_validator']
                if callable(custom_validator):
                    custom_validator(value)
            
        except Exception as e:
            raise ValidationError(f"Field '{field_name}' validation failed: {str(e)}")
    
    @classmethod
    def _get_file_type(cls, extension: str) -> str:
        """Get file type from extension"""
        for file_type, extensions in cls.ALLOWED_EXTENSIONS.items():
            if extension in extensions:
                return file_type
        return 'default'

    @classmethod
    def _validate_file_content(cls, file, expected_extension: str):
        """
        Validate file content matches its extension using magic numbers
        
        Args:
            file: File object to validate
            expected_extension: Expected file extension
            
        Raises:
            ValidationError: If file content doesn't match extension
        """
        try:
            # Map of extensions to expected MIME types
            extension_mime_map = {
                '.jpg': ['image/jpeg'],
                '.jpeg': ['image/jpeg'], 
                '.png': ['image/png'],
                '.gif': ['image/gif'],
                '.bmp': ['image/bmp'],
                '.webp': ['image/webp'],
                '.pdf': ['application/pdf'],
                '.txt': ['text/plain'],
                '.md': ['text/plain', 'text/markdown'],
                '.json': ['application/json', 'text/plain'],
                '.xml': ['application/xml', 'text/xml'],
                '.csv': ['text/csv', 'text/plain'],
                '.html': ['text/html'],
                '.css': ['text/css'],
                '.js': ['application/javascript', 'text/javascript'],
                '.py': ['text/plain'],
                '.mp3': ['audio/mpeg'],
                '.wav': ['audio/wav', 'audio/x-wav'],
                '.mp4': ['video/mp4'],
                '.avi': ['video/x-msvideo'],
                '.zip': ['application/zip'],
                '.tar': ['application/x-tar'],
                '.gz': ['application/gzip'],
            }
            
            expected_mimes = extension_mime_map.get(expected_extension.lower())
            if not expected_mimes:
                # If we don't have mapping for this extension, skip content validation
                return
            
            # Try to detect file type using python-magic (if available)
            if not MAGIC_AVAILABLE:
                # python-magic not available, log warning and skip content validation
                logger.warning("python-magic not available, skipping content validation")
                return
                
            try:
                # Save current position
                current_pos = file.tell()
                file.seek(0)
                
                # Read a small chunk for magic number detection
                chunk = file.read(2048)
                file.seek(current_pos)  # Restore position
                
                # Try to detect MIME type
                if magic is not None:
                    detected_mime = magic.from_buffer(chunk, mime=True)
                else:
                    logger.warning("Magic module is None, skipping detection")
                    return
                
                # Check if detected MIME type matches expected
                if detected_mime not in expected_mimes:
                    raise ValidationError(
                        f"File content ({detected_mime}) does not match extension {expected_extension}"
                    )
                
            except Exception as e:
                # If magic detection fails, log warning but don't fail validation
                logger.warning(f"Content validation failed: {e}")
                return
                
        except ValidationError:
            raise
        except Exception as e:
            logger.warning(f"File content validation error: {e}")
            # Don't fail validation on content check errors, just log

    @staticmethod
    def validate_theme_mode(mode: str) -> str:
        """
        Validate theme mode value
        
        Args:
            mode: Theme mode string to validate
            
        Returns:
            Validated theme mode string
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            if not isinstance(mode, str):
                raise ValidationError("Theme mode must be a string", "theme_mode")
            
            mode = mode.strip().lower()
            valid_modes = ['light', 'dark', 'system', 'auto']
            
            if mode not in valid_modes:
                raise ValidationError(f"Invalid theme mode. Must be one of: {', '.join(valid_modes)}", "theme_mode")
            
            return mode
            
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Theme mode validation failed: {str(e)}", "theme_mode")

    @staticmethod
    def validate_system_prompt(prompt_data: dict) -> dict:
        """
        Validate system prompt data
        
        Args:
            prompt_data: Dictionary containing prompt information
            
        Returns:
            Validated prompt data dictionary
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            if not isinstance(prompt_data, dict):
                raise ValidationError("Prompt data must be a dictionary", "prompt_data")
            
            # Required fields
            required_fields = ['name', 'content']
            for field in required_fields:
                if field not in prompt_data:
                    raise ValidationError(f"Missing required field: {field}", field)
                if not prompt_data[field] or not isinstance(prompt_data[field], str):
                    raise ValidationError(f"Field '{field}' must be a non-empty string", field)
            
            # Validate name
            name = prompt_data['name'].strip()
            if len(name) < 1:
                raise ValidationError("Prompt name cannot be empty", "name")
            if len(name) > 100:
                raise ValidationError("Prompt name cannot exceed 100 characters", "name")
            
            # Validate content
            content = prompt_data['content'].strip()
            if len(content) < 1:
                raise ValidationError("Prompt content cannot be empty", "content")
            if len(content) > 10000:
                raise ValidationError("Prompt content cannot exceed 10000 characters", "content")
            
            # Optional fields with validation
            validated_data = {
                'name': name,
                'content': content
            }
            
            # Validate optional description
            if 'description' in prompt_data and prompt_data['description']:
                description = prompt_data['description'].strip()
                if len(description) > 500:
                    raise ValidationError("Description cannot exceed 500 characters", "description")
                validated_data['description'] = description
            else:
                validated_data['description'] = ''
            
            # Validate optional category
            if 'category' in prompt_data and prompt_data['category']:
                category = prompt_data['category'].strip()
                valid_categories = ['general', 'creative', 'technical', 'business', 'educational', 'custom']
                if category not in valid_categories:
                    raise ValidationError(f"Invalid category. Must be one of: {', '.join(valid_categories)}", "category")
                validated_data['category'] = category
            else:
                validated_data['category'] = 'general'
            
            return validated_data
            
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"System prompt validation failed: {str(e)}", "prompt_data")


def validate_api_request(required_fields: Optional[List[str]] = None,
                        optional_fields: Optional[Dict[str, Any]] = None,
                        allow_files: bool = False) -> Dict[str, Any]:
    """
    Convenience function to validate API requests
    
    Args:
        required_fields: List of required field names
        optional_fields: Dict of field_name: validation_rules for optional fields
        allow_files: Whether to allow file uploads
        
    Returns:
        Validated request data
        
    Raises:
        ValidationError: If validation fails
    """
    try:
        # Validate JSON data
        data = InputValidator.validate_json_request(required_fields, optional_fields)
        
        # Validate files if needed
        if allow_files and request.files:
            for field_name in request.files:
                file_info = InputValidator.validate_file_upload(field_name, required=False)
                if file_info:
                    data[field_name] = file_info
        
        return data
        
    except ValidationError:
        raise
    except Exception as e:
        raise ValidationError(f"Request validation failed: {str(e)}")


def handle_validation_error(error: ValidationError) -> Tuple[Dict[str, Any], int]:
    """
    Handle validation errors and return appropriate response
    
    Args:
        error: ValidationError instance
        
    Returns:
        Tuple of (response_dict, status_code)
    """
    logger.warning(f"Validation error: {str(error)}")
    
    response_data = {
        "status": "error",
        "message": "Validation failed",
        "error": str(error),
        "error_type": "validation_error"
    }
    
    return response_data, 400


# Decorator for API endpoints
def validate_request(required_fields: Optional[List[str]] = None,
                    optional_fields: Optional[Dict[str, Any]] = None,
                    allow_files: bool = False):
    """
    Decorator to validate API request data
    
    Args:
        required_fields: List of required field names
        optional_fields: Dict of field_name: validation_rules for optional fields
        allow_files: Whether to allow file uploads
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                # Validate request
                validated_data = validate_api_request(required_fields, optional_fields, allow_files)
                
                # Add validated data to request context
                setattr(request, 'validated_data', validated_data)
                
                # Call original function
                return func(*args, **kwargs)
                
            except ValidationError as e:
                return handle_validation_error(e)
            except Exception as e:
                logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
                return jsonify({
                    "status": "error",
                    "message": "Internal server error",
                    "error_type": "internal_error"
                }), 500
        
        wrapper.__name__ = func.__name__
        return wrapper
    return decorator
