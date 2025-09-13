"""
Enhanced API Documentation Generator
Comprehensive OpenAPI/Swagger documentation for Vybe AI Desktop APIs
with automatic endpoint discovery and interactive documentation
"""

from flask import Blueprint, jsonify, request, render_template, current_app
from flask_swagger_ui import get_swaggerui_blueprint
import json
import inspect
import re
from functools import wraps
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime
import os

# Enhanced API metadata tracking
@dataclass
class APIEndpoint:
    """Represents an API endpoint with comprehensive metadata"""
    path: str
    method: str
    summary: str
    description: str
    tags: List[str]
    parameters: List[Dict[str, Any]]
    request_body: Optional[Dict[str, Any]]
    responses: Dict[str, Dict[str, Any]]
    security: List[Dict[str, List[str]]]
    examples: List[Dict[str, Any]]
    deprecated: bool = False
    version_added: str = "1.0.0"
    rate_limit: Optional[str] = None

class DocumentationGenerator:
    """Enhanced documentation generator with automatic discovery"""
    
    def __init__(self):
        self.endpoints: Dict[str, APIEndpoint] = {}
        self.schemas: Dict[str, Dict[str, Any]] = {}
        self.security_schemes = {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT"
            },
            "apiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key"
            },
            "sessionAuth": {
                "type": "apiKey",
                "in": "cookie",
                "name": "session"
            }
        }
    
    def register_endpoint(self, endpoint: APIEndpoint):
        """Register an API endpoint for documentation"""
        key = f"{endpoint.method.upper()}:{endpoint.path}"
        self.endpoints[key] = endpoint
    
    def discover_endpoints(self, app):
        """Automatically discover API endpoints from Flask app"""
        for rule in app.url_map.iter_rules():
            if self._should_document_endpoint(rule):
                endpoint = self._extract_endpoint_info(rule, app)
                if endpoint:
                    self.register_endpoint(endpoint)
    
    def _should_document_endpoint(self, rule) -> bool:
        """Determine if endpoint should be documented"""
        # Skip static files and internal endpoints
        skip_patterns = [
            r'^/static/',
            r'^/_',
            r'^/admin/',
            r'^/debug/',
            r'^/swagger',
            r'^/docs'
        ]
        
        for pattern in skip_patterns:
            if re.match(pattern, rule.rule):
                return False
        
        return True
    
    def _extract_endpoint_info(self, rule, app) -> Optional[APIEndpoint]:
        """Extract endpoint information from Flask rule"""
        try:
            endpoint_func = app.view_functions.get(rule.endpoint)
            if not endpoint_func:
                return None
            
            # Extract docstring information
            docstring = inspect.getdoc(endpoint_func) or ""
            summary, description = self._parse_docstring(docstring)
            
            # Determine tags from endpoint path
            tags = self._determine_tags(rule.rule)
            
            # Extract parameters from route
            parameters = self._extract_parameters(rule)
            
            # Try to determine request/response schemas
            request_body = self._infer_request_body(endpoint_func)
            responses = self._infer_responses(endpoint_func)
            
            # Check for security requirements
            security = self._determine_security(endpoint_func)
            
            for method in rule.methods:
                if method in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                    return APIEndpoint(
                        path=rule.rule,
                        method=method,
                        summary=summary or f"{method} {rule.rule}",
                        description=description or f"Endpoint for {rule.rule}",
                        tags=tags,
                        parameters=parameters,
                        request_body=request_body if method in ['POST', 'PUT', 'PATCH'] else None,
                        responses=responses,
                        security=security,
                        examples=[]
                    )
        except Exception as e:
            print(f"Error extracting endpoint info for {rule.rule}: {e}")
            return None
    
    def _parse_docstring(self, docstring: str) -> tuple[str, str]:
        """Parse docstring to extract summary and description"""
        if not docstring:
            return "", ""
        
        lines = docstring.strip().split('\n')
        summary = lines[0].strip() if lines else ""
        
        # Find description (everything after first line, before any special sections)
        description_lines = []
        for line in lines[1:]:
            line = line.strip()
            if line.startswith(('Args:', 'Returns:', 'Raises:', 'Note:')):
                break
            if line:
                description_lines.append(line)
        
        description = ' '.join(description_lines).strip()
        return summary, description
    
    def _determine_tags(self, path: str) -> List[str]:
        """Determine appropriate tags based on endpoint path"""
        path_segments = [seg for seg in path.split('/') if seg and not seg.startswith('<')]
        
        tag_mapping = {
            'api': 'API',
            'auth': 'Authentication',
            'login': 'Authentication',
            'logout': 'Authentication',
            'chat': 'Chat',
            'message': 'Chat',
            'conversation': 'Chat',
            'model': 'Models',
            'models': 'Models',
            'audio': 'Audio',
            'tts': 'Audio',
            'voice': 'Audio',
            'image': 'Images',
            'images': 'Images',
            'generate': 'Generation',
            'video': 'Video',
            'upload': 'File Management',
            'download': 'File Management',
            'file': 'File Management',
            'settings': 'Configuration',
            'config': 'Configuration',
            'admin': 'Administration',
            'user': 'User Management',
            'users': 'User Management',
            'feedback': 'Feedback',
            'analytics': 'Analytics',
            'health': 'System',
            'status': 'System',
            'rag': 'RAG',
            'search': 'Search'
        }
        
        tags = []
        for segment in path_segments:
            if segment.lower() in tag_mapping:
                tag = tag_mapping[segment.lower()]
                if tag not in tags:
                    tags.append(tag)
        
        return tags or ['General']
    
    def _extract_parameters(self, rule) -> List[Dict[str, Any]]:
        """Extract parameters from Flask route rule"""
        parameters = []
        
        # Path parameters
        for arg in rule.arguments:
            param_type = "string"  # Default
            # Try to infer type from converter
            if hasattr(rule, '_converters') and arg in rule._converters:
                converter = rule._converters[arg]
                if 'int' in str(converter):
                    param_type = "integer"
                elif 'float' in str(converter):
                    param_type = "number"
            
            parameters.append({
                "name": arg,
                "in": "path",
                "required": True,
                "schema": {"type": param_type},
                "description": f"Path parameter: {arg}"
            })
        
        return parameters
    
    def _infer_request_body(self, func) -> Optional[Dict[str, Any]]:
        """Infer request body schema from function"""
        # This is a simplified inference - in a real implementation,
        # you might use type hints or decorators for more accurate schemas
        return {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "data": {
                                "type": "object",
                                "description": "Request data"
                            }
                        }
                    }
                }
            }
        }
    
    def _infer_responses(self, func) -> Dict[str, Dict[str, Any]]:
        """Infer response schemas from function"""
        return {
            "200": {
                "description": "Successful operation",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "success": {"type": "boolean"},
                                "data": {"type": "object"}
                            }
                        }
                    }
                }
            },
            "400": {
                "description": "Bad request",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "error": {"type": "string"},
                                "message": {"type": "string"}
                            }
                        }
                    }
                }
            },
            "500": {
                "description": "Internal server error",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "error": {"type": "string"},
                                "message": {"type": "string"}
                            }
                        }
                    }
                }
            }
        }
    
    def _determine_security(self, func) -> List[Dict[str, List[str]]]:
        """Determine security requirements for endpoint"""
        # Check if function has authentication decorators
        if hasattr(func, '__wrapped__'):
            # Look for common auth decorators
            auth_decorators = ['login_required', 'auth_required', 'api_key_required']
            for decorator in auth_decorators:
                if decorator in str(func):
                    if 'api_key' in decorator:
                        return [{"apiKeyAuth": []}]
                    else:
                        return [{"sessionAuth": []}]
        
        return []  # No security required

# Global documentation generator instance
doc_generator = DocumentationGenerator()

# OpenAPI Specification with enhanced structure
OPENAPI_SPEC = {
    "openapi": "3.0.3",
    "info": {
        "title": "Vybe AI Desktop API",
        "description": "Comprehensive API for Vybe AI Desktop - Local AI Assistant Platform with advanced features",
        "version": "2.1.0",
        "contact": {
            "name": "Vybe AI Support",
            "url": "https://github.com/socalcium/Vybe-Local-Agentic-Container"
        },
        "license": {
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT"
        }
    },
    "servers": [
        {
            "url": "http://localhost:5000",
            "description": "Development server"
        },
        {
            "url": "https://localhost:5443",
            "description": "Development server (HTTPS)"
        }
    ],
    "tags": [
        {
            "name": "Authentication",
            "description": "User authentication and session management"
        },
        {
            "name": "Chat",
            "description": "AI chat functionality and conversation management"
        },
        {
            "name": "Models",
            "description": "AI model management and configuration"
        },
        {
            "name": "RAG",
            "description": "Retrieval-Augmented Generation and document processing"
        },
        {
            "name": "Audio",
            "description": "Audio processing, TTS, and voice features"
        },
        {
            "name": "Images",
            "description": "Image generation and processing"
        },
        {
            "name": "Video",
            "description": "Video generation and processing"
        },
        {
            "name": "Agents",
            "description": "AI agent management and automation"
        },
        {
            "name": "Collaboration",
            "description": "Multi-user collaboration features"
        },
        {
            "name": "System",
            "description": "System management and monitoring"
        },
        {
            "name": "Settings",
            "description": "Application settings and configuration"
        },
        {
            "name": "Tools",
            "description": "External tool integration and management"
        },
        {
            "name": "Plugins",
            "description": "Plugin system and marketplace"
        },
        {
            "name": "Cloud Sync",
            "description": "Cloud synchronization and backup"
        },
        {
            "name": "RPG",
            "description": "AI-powered RPG and gaming features"
        }
    ],
    "paths": {},
    "components": {
        "schemas": {
            "Error": {
                "type": "object",
                "properties": {
                    "error": {
                        "type": "string",
                        "description": "Error message"
                    },
                    "code": {
                        "type": "integer",
                        "description": "HTTP status code"
                    },
                    "details": {
                        "type": "object",
                        "description": "Additional error details"
                    }
                }
            },
            "Success": {
                "type": "object",
                "properties": {
                    "success": {
                        "type": "boolean",
                        "description": "Success status"
                    },
                    "message": {
                        "type": "string",
                        "description": "Success message"
                    },
                    "data": {
                        "type": "object",
                        "description": "Response data"
                    }
                }
            },
            "ChatMessage": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "Message ID"
                    },
                    "content": {
                        "type": "string",
                        "description": "Message content"
                    },
                    "role": {
                        "type": "string",
                        "enum": ["user", "assistant", "system"],
                        "description": "Message role"
                    },
                    "timestamp": {
                        "type": "string",
                        "format": "date-time",
                        "description": "Message timestamp"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Additional message metadata"
                    }
                }
            },
            "Model": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "Model ID"
                    },
                    "name": {
                        "type": "string",
                        "description": "Model name"
                    },
                    "type": {
                        "type": "string",
                        "description": "Model type (llm, embedding, etc.)"
                    },
                    "status": {
                        "type": "string",
                        "enum": ["available", "loading", "error"],
                        "description": "Model status"
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Model parameters"
                    }
                }
            },
            "Document": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "Document ID"
                    },
                    "name": {
                        "type": "string",
                        "description": "Document name"
                    },
                    "type": {
                        "type": "string",
                        "description": "Document type"
                    },
                    "content": {
                        "type": "string",
                        "description": "Document content"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Document metadata"
                    }
                }
            },
            "User": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "User ID"
                    },
                    "username": {
                        "type": "string",
                        "description": "Username"
                    },
                    "email": {
                        "type": "string",
                        "format": "email",
                        "description": "User email"
                    },
                    "role": {
                        "type": "string",
                        "enum": ["user", "admin"],
                        "description": "User role"
                    },
                    "preferences": {
                        "type": "object",
                        "description": "User preferences"
                    }
                }
            }
        },
        "securitySchemes": {
            "sessionAuth": {
                "type": "apiKey",
                "in": "cookie",
                "name": "session",
                "description": "Session-based authentication"
            },
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "JWT token authentication"
            }
        }
    }
}

class APIDocumentation:
    """API Documentation Manager"""
    
    def __init__(self, app=None):
        self.app = app
        self.endpoints = {}
        self.spec = OPENAPI_SPEC.copy()
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the API documentation with Flask app"""
        self.app = app
        
        # Register Swagger UI blueprint
        swagger_ui_blueprint = get_swaggerui_blueprint(
            '/api/docs',
            '/api/swagger.json',
            config={
                'app_name': "Vybe AI Desktop API",
                'deepLinking': True,
                'displayOperationId': True,
                'defaultModelsExpandDepth': 2,
                'defaultModelExpandDepth': 2,
                'docExpansion': 'list',
                'filter': True,
                'showExtensions': True,
                'showCommonExtensions': True,
                'syntaxHighlight.theme': 'monokai'
            }
        )
        app.register_blueprint(swagger_ui_blueprint, url_prefix='/api')
        
        # Register API documentation routes
        api_docs_bp = Blueprint('api_docs', __name__, url_prefix='/api')
        
        @api_docs_bp.route('/swagger.json')
        def swagger_json():
            """Serve OpenAPI specification"""
            return jsonify(self.spec)
        
        @api_docs_bp.route('/docs')
        def api_docs():
            """Serve API documentation page"""
            return render_template('api_docs.html', spec=self.spec)
        
        @api_docs_bp.route('/endpoints')
        def list_endpoints():
            """List all registered API endpoints"""
            return jsonify({
                'endpoints': list(self.endpoints.keys()),
                'total': len(self.endpoints)
            })
        
        app.register_blueprint(api_docs_bp)
    
    def document_endpoint(self, path: str, method: str, **kwargs):
        """Decorator to document API endpoints"""
        def decorator(func):
            # Store endpoint information
            endpoint_key = f"{method.upper()} {path}"
            self.endpoints[endpoint_key] = {
                'function': func,
                'path': path,
                'method': method.upper(),
                'kwargs': kwargs
            }
            
            # Add to OpenAPI spec
            if path not in self.spec['paths']:
                self.spec['paths'][path] = {}
            
            self.spec['paths'][path][method.lower()] = {
                'summary': kwargs.get('summary', func.__name__),
                'description': kwargs.get('description', func.__doc__ or ''),
                'tags': kwargs.get('tags', []),
                'parameters': kwargs.get('parameters', []),
                'requestBody': kwargs.get('requestBody'),
                'responses': kwargs.get('responses', {
                    '200': {
                        'description': 'Success',
                        'content': {
                            'application/json': {
                                'schema': {
                                    '$ref': '#/components/schemas/Success'
                                }
                            }
                        }
                    },
                    '400': {
                        'description': 'Bad Request',
                        'content': {
                            'application/json': {
                                'schema': {
                                    '$ref': '#/components/schemas/Error'
                                }
                            }
                        }
                    },
                    '401': {
                        'description': 'Unauthorized',
                        'content': {
                            'application/json': {
                                'schema': {
                                    '$ref': '#/components/schemas/Error'
                                }
                            }
                        }
                    },
                    '500': {
                        'description': 'Internal Server Error',
                        'content': {
                            'application/json': {
                                'schema': {
                                    '$ref': '#/components/schemas/Error'
                                }
                            }
                        }
                    }
                }),
                'security': kwargs.get('security', [{'sessionAuth': []}])
            }
            
            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    def generate_endpoint_docs(self, blueprint):
        """Generate documentation for all endpoints in a blueprint"""
        for rule in blueprint.url_map.iter_rules():
            if rule.endpoint != 'static':
                for method in rule.methods:
                    if method != 'HEAD' and method != 'OPTIONS':
                        endpoint_func = blueprint.view_functions[rule.endpoint]
                        self.document_endpoint(
                            path=rule.rule,
                            method=method,
                            summary=endpoint_func.__name__,
                            description=endpoint_func.__doc__ or '',
                            tags=[blueprint.name.replace('_', ' ').title()]
                        )
    
    def create_response_schema(self, schema_name: str, properties: Dict[str, Any]):
        """Create a new response schema"""
        self.spec['components']['schemas'][schema_name] = {
            'type': 'object',
            'properties': properties
        }
        return f'#/components/schemas/{schema_name}'
    
    def add_parameter(self, name: str, param_type: str, description: str, required: bool = False, schema: Optional[Dict] = None):
        """Add a parameter definition"""
        param = {
            'name': name,
            'in': param_type,
            'description': description,
            'required': required
        }
        
        if schema:
            param['schema'] = schema
        
        return param
    
    def add_request_body(self, content_type: str, schema_ref: str, description: str = ''):
        """Add a request body definition"""
        return {
            'description': description,
            'required': True,
            'content': {
                content_type: {
                    'schema': {
                        '$ref': schema_ref
                    }
                }
            }
        }

# Global API documentation instance
api_docs = APIDocumentation()

# Predefined parameter schemas
def create_parameter_schemas():
    """Create common parameter schemas"""
    schemas = {
        'Pagination': {
            'type': 'object',
            'properties': {
                'page': {
                    'type': 'integer',
                    'default': 1,
                    'minimum': 1,
                    'description': 'Page number'
                },
                'per_page': {
                    'type': 'integer',
                    'default': 20,
                    'minimum': 1,
                    'maximum': 100,
                    'description': 'Items per page'
                }
            }
        },
        'SearchQuery': {
            'type': 'object',
            'properties': {
                'query': {
                    'type': 'string',
                    'description': 'Search query'
                },
                'filters': {
                    'type': 'object',
                    'description': 'Search filters'
                },
                'sort': {
                    'type': 'string',
                    'description': 'Sort field'
                },
                'order': {
                    'type': 'string',
                    'enum': ['asc', 'desc'],
                    'default': 'desc',
                    'description': 'Sort order'
                }
            }
        },
        'ModelConfig': {
            'type': 'object',
            'properties': {
                'model_id': {
                    'type': 'string',
                    'description': 'Model identifier'
                },
                'parameters': {
                    'type': 'object',
                    'description': 'Model parameters'
                },
                'context_length': {
                    'type': 'integer',
                    'description': 'Context length'
                },
                'temperature': {
                    'type': 'number',
                    'minimum': 0,
                    'maximum': 2,
                    'description': 'Sampling temperature'
                },
                'top_p': {
                    'type': 'number',
                    'minimum': 0,
                    'maximum': 1,
                    'description': 'Top-p sampling'
                }
            }
        }
    }
    
    for name, schema in schemas.items():
        api_docs.spec['components']['schemas'][name] = schema

# Initialize parameter schemas
create_parameter_schemas()

# Example usage decorators
def chat_endpoint(func):
    """Decorator for chat-related endpoints"""
    return api_docs.document_endpoint(
        path=func.__name__,
        method='POST',
        tags=['Chat'],
        summary=func.__name__.replace('_', ' ').title(),
        description=func.__doc__ or '',
        requestBody=api_docs.add_request_body(
            'application/json',
            '#/components/schemas/ChatMessage',
            'Chat message data'
        )
    )(func)

def model_endpoint(func):
    """Decorator for model-related endpoints"""
    return api_docs.document_endpoint(
        path=func.__name__,
        method='GET',
        tags=['Models'],
        summary=func.__name__.replace('_', ' ').title(),
        description=func.__doc__ or ''
    )(func)

def rag_endpoint(func):
    """Decorator for RAG-related endpoints"""
    return api_docs.document_endpoint(
        path=func.__name__,
        method='POST',
        tags=['RAG'],
        summary=func.__name__.replace('_', ' ').title(),
        description=func.__doc__ or '',
        requestBody=api_docs.add_request_body(
            'application/json',
            '#/components/schemas/Document',
            'Document data'
        )
    )(func)

# Export the API documentation instance
__all__ = ['api_docs', 'APIDocumentation', 'chat_endpoint', 'model_endpoint', 'rag_endpoint']
