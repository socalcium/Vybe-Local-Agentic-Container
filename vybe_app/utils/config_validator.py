#!/usr/bin/env python3
"""
Configuration Validation and Management Utilities for Vybe AI Desktop Application
Provides comprehensive configuration validation, schema checking, and environment management
"""

import os
import json
import yaml
import toml
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Type, get_type_hints, Callable
from dataclasses import dataclass, field
from datetime import datetime
import logging
import re
from urllib.parse import urlparse
import socket
import socket
import ssl

import socket
import ssl

# Initialize logger first
logger = logging.getLogger(__name__)

# Create fallback classes first
class FallbackValidationError(Exception):
    """Fallback ValidationError class"""
    def __init__(self, message="Validation error", field_name=None, error_type=None):
        super().__init__(message)
        self.message = message
        self.field_name = field_name
        self.error_type = error_type

class FallbackInputValidator:
    """Fallback AdvancedInputValidator class"""
    @staticmethod
    def validate_string(value, pattern=None):
        return isinstance(value, str)
    
    @staticmethod 
    def validate_number(value, min_val=None, max_val=None):
        return isinstance(value, (int, float))

class FallbackApplicationError(Exception):
    """Fallback ApplicationError class"""
    def __init__(self, message="Application error", code=None, details=None, cause=None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details
        self.cause = cause

class FallbackErrorCode:
    """Fallback ErrorCode class"""
    VALIDATION_ERROR = 2000
    CONFIG_ERROR = 7000
    INVALID_CONFIG = 7002
    FILE_NOT_FOUND = 5001
    CONFIG_PARSE_ERROR = 7003

# Import dependencies with fallback handling
try:
    from .input_validation import AdvancedInputValidator, ValidationError
    INPUT_VALIDATION_AVAILABLE = True
except ImportError:
    logger.warning("input_validation module not found, using fallback classes")
    INPUT_VALIDATION_AVAILABLE = False
    AdvancedInputValidator = FallbackInputValidator
    ValidationError = FallbackValidationError

try:
    from .error_handling import ApplicationError, ErrorCode
    ERROR_HANDLING_AVAILABLE = True
except ImportError:
    logger.warning("error_handling module not found, using fallback classes")
    ERROR_HANDLING_AVAILABLE = False
    ApplicationError = FallbackApplicationError
    ErrorCode = FallbackErrorCode


@dataclass
class ConfigField:
    """Configuration field definition with validation rules"""
    name: str
    field_type: Type
    required: bool = True
    default: Any = None
    description: str = ""
    validation_pattern: Optional[str] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    allowed_values: Optional[List[Any]] = None
    env_var: Optional[str] = None
    sensitive: bool = False
    validator_func: Optional[Callable[[Any], bool]] = None


@dataclass
class ConfigSchema:
    """Configuration schema definition"""
    name: str
    version: str
    fields: List[ConfigField]
    sections: Optional[Dict[str, 'ConfigSchema']] = None
    description: str = ""


class ConfigValidator:
    """Advanced configuration validation with schema support"""
    
    def __init__(self):
        # Initialize input validator
        self.input_validator = AdvancedInputValidator()
        self.schemas: Dict[str, ConfigSchema] = {}
        self.environment_validators = {}
        self._register_builtin_validators()
    
    def _register_builtin_validators(self):
        """Register built-in validation functions"""
        
        def validate_url_accessible(url: str) -> bool:
            """Validate that a URL is accessible"""
            try:
                import urllib.request
                with urllib.request.urlopen(url, timeout=5) as response:
                    return response.status == 200
            except Exception:
                return False
        
        def validate_port_available(port: Union[str, int]) -> bool:
            """Validate that a port is available"""
            try:
                port_num = int(port)
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    result = s.connect_ex(('localhost', port_num))
                    return result != 0  # Port is available if connection fails
            except Exception:
                return False
        
        def validate_file_readable(path: str) -> bool:
            """Validate that a file is readable"""
            try:
                return Path(path).is_file() and os.access(path, os.R_OK)
            except Exception:
                return False
        
        def validate_directory_writable(path: str) -> bool:
            """Validate that a directory is writable"""
            try:
                return Path(path).is_dir() and os.access(path, os.W_OK)
            except Exception:
                return False
        
        def validate_ssl_cert(cert_path: str) -> bool:
            """Validate SSL certificate"""
            try:
                with open(cert_path, 'r') as f:
                    cert_data = f.read()
                # Basic validation - check if it looks like a certificate
                return '-----BEGIN CERTIFICATE-----' in cert_data
            except Exception:
                return False
        
        self.environment_validators.update({
            'url_accessible': validate_url_accessible,
            'port_available': validate_port_available,
            'file_readable': validate_file_readable,
            'directory_writable': validate_directory_writable,
            'ssl_cert_valid': validate_ssl_cert
        })
    
    def register_schema(self, schema: ConfigSchema):
        """Register a configuration schema"""
        self.schemas[schema.name] = schema
        logger.info(f"Registered configuration schema: {schema.name} v{schema.version}")
    
    def register_validator(self, name: str, validator_func: Callable[[Any], bool]):
        """Register a custom validator function"""
        self.environment_validators[name] = validator_func
        logger.info(f"Registered custom validator: {name}")
    
    def validate_config(self, config: Dict[str, Any], schema_name: str,
                       environment_check: bool = True) -> Dict[str, Any]:
        """Validate configuration against a schema"""
        
        try:
            if schema_name not in self.schemas:
                raise ApplicationError(
                    f"Unknown configuration schema: {schema_name}",
                    ErrorCode.CONFIG_ERROR
                )
            
            if not isinstance(config, dict):
                raise ApplicationError(
                    f"Configuration must be a dictionary, got {type(config)}",
                    ErrorCode.VALIDATION_ERROR
                )
            
            schema = self.schemas[schema_name]
            validated_config = {}
            errors = []
            warnings = []
            
            # Validate each field
            for field_def in schema.fields:
                try:
                    field_name = field_def.name
                    field_value = config.get(field_name)
                    
                    # Check if required field is missing
                    if field_def.required and field_value is None:
                        errors.append(f"Required field '{field_name}' is missing")
                        continue
                    
                    # Use default value if provided and field is None
                    if field_value is None and field_def.default is not None:
                        field_value = field_def.default
                    
                    # Skip validation for None values (optional fields)
                    if field_value is None:
                        validated_config[field_name] = None
                        continue
                    
                    # Validate field
                    try:
                        validation_result = self._validate_field(field_def, field_value, environment_check)
                        if validation_result['valid']:
                            validated_config[field_name] = validation_result['value']
                            if validation_result.get('warnings'):
                                warnings.extend(validation_result['warnings'])
                        else:
                            errors.extend(validation_result['errors'])
                    except Exception as e:
                        logger.error(f"Error validating field {field_name}: {e}")
                        errors.append(f"Validation error for field '{field_name}': {str(e)}")
                        
                except Exception as e:
                    logger.error(f"Error processing field definition: {e}")
                    errors.append(f"Error processing field configuration: {str(e)}")
            
            # Validate sections if present
            if schema.sections:
                try:
                    for section_name, section_schema in schema.sections.items():
                        if section_name in config:
                            section_result = self.validate_config(
                                config[section_name], 
                                section_schema.name, 
                                environment_check
                            )
                            validated_config[section_name] = section_result['config']
                            errors.extend([f"{section_name}.{err}" for err in section_result['errors']])
                            warnings.extend([f"{section_name}.{warn}" for warn in section_result['warnings']])
                except Exception as e:
                    logger.error(f"Error validating sections: {e}")
                    errors.append(f"Error validating configuration sections: {str(e)}")
            
            return {
                'valid': len(errors) == 0,
                'config': validated_config,
                'errors': errors,
                'warnings': warnings,
                'schema_name': schema_name,
                'schema_version': schema.version
            }
            
        except ApplicationError:
            raise  # Re-raise ApplicationErrors as-is
        except Exception as e:
            logger.error(f"Unexpected error in validate_config: {e}")
            raise ApplicationError(
                f"Configuration validation failed: {str(e)}",
                ErrorCode.VALIDATION_ERROR,
                details={'schema_name': schema_name, 'error': str(e)}
            )
    
    def _validate_field(self, field_def: ConfigField, field_value: Any, environment_check: bool = True) -> Dict[str, Any]:
        """Validate a single field against its definition"""
        try:
            errors = []
            warnings = []
            validated_value = field_value
            
            # Type validation
            if not self._validate_type(field_value, field_def.field_type):
                errors.append(f"Field '{field_def.name}' must be of type {field_def.field_type.__name__}, got {type(field_value).__name__}")
                return {'valid': False, 'errors': errors, 'warnings': warnings}
            
            # Pattern validation for strings
            if field_def.validation_pattern and isinstance(field_value, str):
                if not re.match(field_def.validation_pattern, field_value):
                    errors.append(f"Field '{field_def.name}' does not match required pattern: {field_def.validation_pattern}")
                    return {'valid': False, 'errors': errors, 'warnings': warnings}
            
            # Range validation for numbers
            if isinstance(field_value, (int, float)):
                if field_def.min_value is not None and field_value < field_def.min_value:
                    errors.append(f"Field '{field_def.name}' must be >= {field_def.min_value}")
                    return {'valid': False, 'errors': errors, 'warnings': warnings}
                
                if field_def.max_value is not None and field_value > field_def.max_value:
                    errors.append(f"Field '{field_def.name}' must be <= {field_def.max_value}")
                    return {'valid': False, 'errors': errors, 'warnings': warnings}
            
            # Allowed values validation
            if field_def.allowed_values and field_value not in field_def.allowed_values:
                errors.append(f"Field '{field_def.name}' must be one of: {field_def.allowed_values}")
                return {'valid': False, 'errors': errors, 'warnings': warnings}
            
            # Custom validator function
            if field_def.validator_func:
                try:
                    if not field_def.validator_func(field_value):
                        errors.append(f"Field '{field_def.name}' failed custom validation")
                        return {'valid': False, 'errors': errors, 'warnings': warnings}
                except Exception as e:
                    logger.error(f"Custom validator error for {field_def.name}: {e}")
                    errors.append(f"Field '{field_def.name}' custom validation error: {str(e)}")
                    return {'valid': False, 'errors': errors, 'warnings': warnings}
            
            # Environment-specific validation
            if environment_check and field_def.name in self.environment_validators:
                try:
                    validator = self.environment_validators[field_def.name]
                    if not validator(field_value):
                        warnings.append(f"Field '{field_def.name}' may have environment issues")
                except Exception as e:
                    logger.error(f"Environment validation error for {field_def.name}: {e}")
                    warnings.append(f"Field '{field_def.name}' environment validation failed: {str(e)}")
            
            return {
                'valid': True,
                'value': validated_value,
                'errors': errors,
                'warnings': warnings
            }
            
        except Exception as e:
            logger.error(f"Error validating field {field_def.name}: {e}")
            return {
                'valid': False,
                'errors': [f"Validation error for field '{field_def.name}': {str(e)}"],
                'warnings': []
            }
        for field_def in schema.fields:
            try:
                value = self._validate_config_field(config, field_def, environment_check)
                if value is not None:
                    validated_config[field_def.name] = value
            except ValidationError as e:
                errors.append(f"{field_def.name}: {e.message}")
            except Exception as e:
                errors.append(f"{field_def.name}: {str(e)}")
        
        # Validate nested sections
        if schema.sections:
            for section_name, section_schema in schema.sections.items():
                if section_name in config:
                    try:
                        validated_section = self.validate_config(
                            config[section_name], section_schema.name, environment_check
                        )
                        validated_config[section_name] = validated_section
                    except ApplicationError as e:
                        errors.append(f"{section_name}: {e.message}")
        
        # Check for unknown fields
        schema_fields = {f.name for f in schema.fields}
        if schema.sections:
            schema_fields.update(schema.sections.keys())
        
        unknown_fields = set(config.keys()) - schema_fields
        if unknown_fields:
            warnings.append(f"Unknown configuration fields: {', '.join(unknown_fields)}")
        
        if errors:
            raise ApplicationError(
                f"Configuration validation failed: {'; '.join(errors)}",
                ErrorCode.INVALID_CONFIG,
                details={'errors': errors, 'warnings': warnings}
            )
        
        if warnings:
            logger.warning(f"Configuration warnings: {'; '.join(warnings)}")
        
        return validated_config
    
    def _validate_config_field(self, config: Dict[str, Any], field_def: ConfigField,
                              environment_check: bool) -> Any:
        """Validate a single configuration field"""
        
        # Get value from config, environment, or default
        value = None
        
        # 1. Check environment variable first
        if field_def.env_var and field_def.env_var in os.environ:
            value = os.environ[field_def.env_var]
            # Convert from string if needed
            value = self._convert_env_value(value, field_def.field_type)
        
        # 2. Check config dict
        elif field_def.name in config:
            value = config[field_def.name]
        
        # 3. Use default value
        elif field_def.default is not None:
            value = field_def.default
        
        # 4. Check if required
        elif field_def.required:
            raise ValidationError(
                f"Required field '{field_def.name}' is missing",
                field_def.name,
                "required"
            )
        
        # Skip validation if value is None/empty and not required
        if value is None:
            return None
        
        # Type validation
        if not self._validate_type(value, field_def.field_type):
            raise ValidationError(
                f"Field '{field_def.name}' must be of type {field_def.field_type.__name__}",
                field_def.name,
                "invalid_type"
            )
        
        # Pattern validation
        if field_def.validation_pattern and isinstance(value, str):
            if not re.match(field_def.validation_pattern, value):
                raise ValidationError(
                    f"Field '{field_def.name}' does not match required pattern",
                    field_def.name,
                    "invalid_pattern"
                )
        
        # Range validation
        if isinstance(value, (int, float)):
            if field_def.min_value is not None and value < field_def.min_value:
                raise ValidationError(
                    f"Field '{field_def.name}' must be >= {field_def.min_value}",
                    field_def.name,
                    "out_of_range"
                )
            
            if field_def.max_value is not None and value > field_def.max_value:
                raise ValidationError(
                    f"Field '{field_def.name}' must be <= {field_def.max_value}",
                    field_def.name,
                    "out_of_range"
                )
        
        # Allowed values validation
        if field_def.allowed_values and value not in field_def.allowed_values:
            raise ValidationError(
                f"Field '{field_def.name}' must be one of: {field_def.allowed_values}",
                field_def.name,
                "invalid_value"
            )
        
        # Custom validator function
        if field_def.validator_func:
            if not field_def.validator_func(value):
                raise ValidationError(
                    f"Field '{field_def.name}' failed custom validation",
                    field_def.name,
                    "custom_validation_failed"
                )
        
        # Environment validation (if enabled and applicable)
        if environment_check and isinstance(value, str):
            self._validate_environment_constraints(field_def, value)
        
        return value
    
    def _convert_env_value(self, value: str, target_type: Type) -> Any:
        """Convert environment variable string to target type"""
        
        if target_type == bool:
            return value.lower() in ('true', '1', 'yes', 'on')
        elif target_type == int:
            return int(value)
        elif target_type == float:
            return float(value)
        elif target_type == list:
            # Assume comma-separated values
            return [item.strip() for item in value.split(',') if item.strip()]
        elif target_type == dict:
            # Assume JSON format
            return json.loads(value)
        else:
            return value
    
    def _validate_type(self, value: Any, expected_type: Type) -> bool:
        """Validate value type"""
        
        # Handle Union types (e.g., Optional[str])
        if hasattr(expected_type, '__origin__'):
            if expected_type.__origin__ is Union:
                return any(isinstance(value, t) for t in expected_type.__args__ if t is not type(None))
        
        return isinstance(value, expected_type)
    
    def _validate_environment_constraints(self, field_def: ConfigField, value: str):
        """Validate environment-specific constraints"""
        
        # URL accessibility check
        if 'url' in field_def.name.lower() and value.startswith(('http://', 'https://')):
            if 'url_accessible' in self.environment_validators:
                if not self.environment_validators['url_accessible'](value):
                    logger.warning(f"URL {value} is not accessible")
        
        # Port availability check
        if 'port' in field_def.name.lower() and value.isdigit():
            if 'port_available' in self.environment_validators:
                if not self.environment_validators['port_available'](value):
                    logger.warning(f"Port {value} appears to be in use")
        
        # File/directory checks
        if 'path' in field_def.name.lower() or 'file' in field_def.name.lower():
            if value and os.path.exists(value):
                if Path(value).is_file():
                    if not os.access(value, os.R_OK):
                        logger.warning(f"File {value} is not readable")
                elif Path(value).is_dir():
                    if not os.access(value, os.W_OK):
                        logger.warning(f"Directory {value} is not writable")


class ConfigManager:
    """Enhanced configuration management with hot reloading and validation"""
    
    def __init__(self, config_dir: str = "instance/config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.validator = ConfigValidator()
        self.configs: Dict[str, Dict[str, Any]] = {}
        self.file_watchers: Dict[str, float] = {}  # filename -> last_modified
        self.hot_reload_enabled = True
        
        # Register built-in schemas
        self._register_builtin_schemas()
    
    def _register_builtin_schemas(self):
        """Register built-in configuration schemas"""
        
        # Application configuration schema
        app_schema = ConfigSchema(
            name="application",
            version="1.0",
            description="Main application configuration",
            fields=[
                ConfigField("debug", bool, default=False, env_var="DEBUG"),
                ConfigField("host", str, default="127.0.0.1", env_var="HOST",
                          validation_pattern=r'^[\d.]+$'),
                ConfigField("port", int, default=5000, env_var="PORT",
                          min_value=1, max_value=65535),
                ConfigField("secret_key", str, required=True, env_var="SECRET_KEY",
                          sensitive=True, min_value=32),
                ConfigField("max_content_length", int, default=16777216,
                          min_value=1024, max_value=104857600),
                ConfigField("session_timeout", int, default=3600,
                          min_value=300, max_value=86400),
                ConfigField("log_level", str, default="INFO",
                          allowed_values=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
                ConfigField("timezone", str, default="UTC"),
                ConfigField("language", str, default="en",
                          validation_pattern=r'^[a-z]{2}(-[A-Z]{2})?$')
            ]
        )
        
        # Database configuration schema
        db_schema = ConfigSchema(
            name="database",
            version="1.0",
            description="Database configuration",
            fields=[
                ConfigField("url", str, required=True, env_var="DATABASE_URL"),
                ConfigField("pool_size", int, default=5, min_value=1, max_value=50),
                ConfigField("pool_timeout", int, default=30, min_value=5, max_value=300),
                ConfigField("pool_recycle", int, default=3600, min_value=300),
                ConfigField("echo", bool, default=False),
                ConfigField("backup_enabled", bool, default=True),
                ConfigField("backup_interval", int, default=3600, min_value=300),
                ConfigField("migration_auto", bool, default=False)
            ]
        )
        
        # AI model configuration schema
        ai_schema = ConfigSchema(
            name="ai_models",
            version="1.0",
            description="AI model configuration",
            fields=[
                ConfigField("default_model", str, required=True),
                ConfigField("model_path", str, default="models/"),
                ConfigField("max_context_length", int, default=4096,
                          min_value=512, max_value=32768),
                ConfigField("temperature", float, default=0.7,
                          min_value=0.0, max_value=2.0),
                ConfigField("top_p", float, default=0.9,
                          min_value=0.0, max_value=1.0),
                ConfigField("max_tokens", int, default=1024,
                          min_value=1, max_value=8192),
                ConfigField("gpu_enabled", bool, default=True),
                ConfigField("gpu_memory_fraction", float, default=0.8,
                          min_value=0.1, max_value=1.0),
                ConfigField("parallel_requests", int, default=1,
                          min_value=1, max_value=10)
            ]
        )
        
        # Security configuration schema
        security_schema = ConfigSchema(
            name="security",
            version="1.0",
            description="Security configuration",
            fields=[
                ConfigField("enable_https", bool, default=False),
                ConfigField("ssl_cert_path", str, env_var="SSL_CERT_PATH"),
                ConfigField("ssl_key_path", str, env_var="SSL_KEY_PATH"),
                ConfigField("rate_limit_enabled", bool, default=True),
                ConfigField("rate_limit_requests", int, default=100,
                          min_value=1, max_value=10000),
                ConfigField("rate_limit_window", int, default=3600,
                          min_value=60, max_value=86400),
                ConfigField("cors_enabled", bool, default=True),
                ConfigField("cors_origins", list, default=["*"]),
                ConfigField("csrf_enabled", bool, default=True),
                ConfigField("session_secure", bool, default=False),
                ConfigField("content_security_policy", str, default="default-src 'self'")
            ]
        )
        
        self.validator.register_schema(app_schema)
        self.validator.register_schema(db_schema)
        self.validator.register_schema(ai_schema)
        self.validator.register_schema(security_schema)
    
    def load_config(self, filename: str, schema_name: Optional[str] = None,
                   validate: bool = True) -> Dict[str, Any]:
        """Load and validate configuration file"""
        
        config_path = self.config_dir / filename
        
        if not config_path.exists():
            raise ApplicationError(
                f"Configuration file not found: {filename}",
                ErrorCode.FILE_NOT_FOUND
            )
        
        try:
            # Load based on file extension
            with open(config_path, 'r', encoding='utf-8') as f:
                if filename.endswith('.json'):
                    raw_config = json.load(f)
                elif filename.endswith(('.yaml', '.yml')):
                    raw_config = yaml.safe_load(f)
                elif filename.endswith('.toml'):
                    raw_config = toml.load(f)
                else:
                    # Try to detect format
                    content = f.read()
                    try:
                        raw_config = json.loads(content)
                    except json.JSONDecodeError:
                        try:
                            raw_config = yaml.safe_load(content)
                        except yaml.YAMLError:
                            raise ApplicationError(
                                f"Unsupported configuration format: {filename}",
                                ErrorCode.CONFIG_PARSE_ERROR
                            )
            
            # Ensure we have a dictionary
            if not isinstance(raw_config, dict):
                raise ApplicationError(
                    f"Configuration must be a dictionary/object: {filename}",
                    ErrorCode.CONFIG_PARSE_ERROR
                )
            
            config: Dict[str, Any] = raw_config
            
            # Validate if schema provided
            if validate and schema_name:
                config = self.validator.validate_config(config, schema_name)
            
            # Cache configuration
            self.configs[filename] = config
            self.file_watchers[filename] = config_path.stat().st_mtime
            
            logger.info(f"Loaded configuration: {filename}")
            return config
            
        except Exception as e:
            if isinstance(e, ApplicationError):
                raise e
            else:
                raise ApplicationError(
                    f"Failed to load configuration {filename}: {str(e)}",
                    ErrorCode.CONFIG_PARSE_ERROR,
                    cause=e
                )
    
    def check_for_updates(self) -> List[str]:
        """Check for configuration file updates"""
        updated_files = []
        
        for filename, last_modified in self.file_watchers.items():
            config_path = self.config_dir / filename
            
            if config_path.exists():
                current_modified = config_path.stat().st_mtime
                if current_modified > last_modified:
                    updated_files.append(filename)
        
        return updated_files
    
    def reload_config(self, filename: str, schema_name: Optional[str] = None) -> Dict[str, Any]:
        """Reload a configuration file"""
        logger.info(f"Reloading configuration: {filename}")
        return self.load_config(filename, schema_name, validate=True)
    
    def get_config(self, filename: str) -> Dict[str, Any]:
        """Get cached configuration"""
        if filename not in self.configs:
            raise ApplicationError(
                f"Configuration not loaded: {filename}",
                ErrorCode.CONFIG_ERROR
            )
        
        return self.configs[filename]
    
    def create_config_template(self, schema_name: str, filename: str, format: str = 'yaml'):
        """Create a configuration template from schema"""
        
        if schema_name not in self.validator.schemas:
            raise ApplicationError(
                f"Unknown schema: {schema_name}",
                ErrorCode.CONFIG_ERROR
            )
        
        schema = self.validator.schemas[schema_name]
        template = {}
        
        # Add description as comment
        if format == 'yaml':
            template['_description'] = schema.description
        
        # Generate template from schema fields
        for field_def in schema.fields:
            if not field_def.sensitive:  # Don't include sensitive fields in templates
                value = field_def.default if field_def.default is not None else f"<{field_def.field_type.__name__}>"
                if field_def.description:
                    if format == 'yaml':
                        template[f"#{field_def.name}_description"] = field_def.description
                template[field_def.name] = value
        
        # Add nested sections
        if schema.sections:
            for section_name, section_schema in schema.sections.items():
                template[section_name] = self._generate_section_template(section_schema)
        
        # Save template
        template_path = self.config_dir / filename
        
        with open(template_path, 'w', encoding='utf-8') as f:
            if format == 'json':
                json.dump(template, f, indent=2)
            elif format in ('yaml', 'yml'):
                yaml.dump(template, f, default_flow_style=False, sort_keys=False)
            elif format == 'toml':
                toml.dump(template, f)
        
        logger.info(f"Created configuration template: {filename}")
    
    def _generate_section_template(self, schema: ConfigSchema) -> Dict[str, Any]:
        """Generate template for a schema section"""
        section = {}
        
        for field_def in schema.fields:
            if not field_def.sensitive:
                value = field_def.default if field_def.default is not None else f"<{field_def.field_type.__name__}>"
                section[field_def.name] = value
        
        return section


# Global configuration manager instance
config_manager = ConfigManager()
