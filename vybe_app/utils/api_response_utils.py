"""
Standardized API response utilities for consistent error handling
"""

from flask import jsonify, Response
from typing import Dict, Any, Optional, Tuple, Union
from ..logger import log_error


def format_success_response(data: Dict[str, Any], status_code: int = 200) -> Tuple[Response, int]:
    """Format standardized success response"""
    try:
        return jsonify({
            'success': True,
            'data': data,
            'error': None,
            'error_type': None
        }), status_code
    except Exception as e:
        log_error(f"Error formatting success response: {e}")
        return jsonify({
            'success': False,
            'data': None,
            'error': 'Internal error formatting response',
            'error_type': 'response_format_error'
        }), 500


def format_error_response(
    error_message: str, 
    error_type: str = 'internal_error',
    status_code: int = 500,
    details: Optional[Dict[str, Any]] = None
) -> Tuple[Response, int]:
    """Format standardized error response"""
    try:
        response = {
            'success': False,
            'data': None,
            'error': error_message,
            'error_type': error_type
        }
        
        if details:
            response['details'] = details
        
        return jsonify(response), status_code
    except Exception as e:
        log_error(f"Error formatting error response: {e}")
        return jsonify({
            'success': False,
            'data': None,
            'error': 'Critical error in response formatting',
            'error_type': 'response_format_error'
        }), 500


def format_validation_error(field: str, message: str, value: Any = None) -> Tuple[Response, int]:
    """Format validation error response"""
    return format_error_response(
        error_message=f"Validation error for field '{field}': {message}",
        error_type='validation_error',
        status_code=400,
        details={
            'field': field,
            'value': value,
            'message': message
        }
    )


def format_not_found_error(resource: str, resource_id: Any = None) -> Tuple[Response, int]:
    """Format not found error response"""
    message = f"{resource} not found"
    if resource_id:
        message += f" with id: {resource_id}"
    
    return format_error_response(
        error_message=message,
        error_type='not_found',
        status_code=404,
        details={
            'resource': resource,
            'resource_id': resource_id
        }
    )


def format_permission_error(action: str, resource: Optional[str] = None) -> Tuple[Response, int]:
    """Format permission error response"""
    message = f"Permission denied for action: {action}"
    if resource:
        message += f" on resource: {resource}"
    
    return format_error_response(
        error_message=message,
        error_type='permission_denied',
        status_code=403,
        details={
            'action': action,
            'resource': resource
        }
    )


def format_rate_limit_error(limit: int, window: str = 'minute') -> Tuple[Response, int]:
    """Format rate limit error response"""
    return format_error_response(
        error_message=f"Rate limit exceeded. Maximum {limit} requests per {window}.",
        error_type='rate_limit_exceeded',
        status_code=429,
        details={
            'limit': limit,
            'window': window
        }
    )


def handle_api_exception(e: Exception, context: Optional[Dict[str, Any]] = None) -> Tuple[Response, int]:
    """Handle API exceptions with standardized error responses"""
    try:
        error_type = type(e).__name__
        
        # Log the error with context
        log_error(f"API Exception: {error_type}: {str(e)}", extra={
            'exception_type': error_type,
            'exception_details': str(e),
            'context': context or {}
        })
        
        # Handle specific exception types
        if isinstance(e, ValueError):
            return format_error_response(
                error_message=str(e),
                error_type='validation_error',
                status_code=400
            )
        elif isinstance(e, KeyError):
            return format_error_response(
                error_message=f"Missing required field: {str(e)}",
                error_type='validation_error',
                status_code=400
            )
        elif isinstance(e, TypeError):
            return format_error_response(
                error_message=f"Invalid data type: {str(e)}",
                error_type='validation_error',
                status_code=400
            )
        else:
            # Generic internal server error
            return format_error_response(
                error_message="Internal server error",
                error_type='internal_error',
                status_code=500
            )
    except Exception as inner_e:
        log_error(f"Critical error in exception handler: {inner_e}")
        return jsonify({
            'success': False,
            'data': None,
            'error': 'Critical system error',
            'error_type': 'system_error'
        }), 500


def standardize_model_response(model_data: Dict[str, Any]) -> Dict[str, Any]:
    """Standardize model response format to use snake_case consistently"""
    try:
        if not isinstance(model_data, dict):
            log_error(f"Invalid model_data type: {type(model_data)}")
            return {}
            
        standardized = {}
        
        for key, value in model_data.items():
            try:
                # Convert camelCase to snake_case
                if isinstance(key, str):
                    # Simple camelCase to snake_case conversion
                    snake_key = ''.join(['_' + c.lower() if c.isupper() else c for c in key]).lstrip('_')
                    standardized[snake_key] = value
                else:
                    standardized[str(key)] = value
            except Exception as e:
                log_error(f"Error processing key {key}: {e}")
                # Use original key as fallback
                standardized[str(key)] = value
        
        return standardized
    except Exception as e:
        log_error(f"Error standardizing model response: {e}")
        return model_data if isinstance(model_data, dict) else {}


def standardize_list_response(items: list, item_key: str = 'items') -> Dict[str, Any]:
    """Standardize list response format"""
    try:
        if not isinstance(items, list):
            log_error(f"Invalid items type: {type(items)}")
            items = []
            
        if not isinstance(item_key, str):
            log_error(f"Invalid item_key type: {type(item_key)}")
            item_key = 'items'
            
        return {
            'success': True,
            'data': {
                item_key: items,
                'count': len(items),
                'total': len(items)
            },
            'error': None,
            'error_type': None
        }
    except Exception as e:
        log_error(f"Error standardizing list response: {e}")
        return {
            'success': False,
            'data': None,
            'error': 'Error formatting list response',
            'error_type': 'response_format_error'
        }


def standardize_paginated_response(
    items: list, 
    page: int, 
    per_page: int, 
    total: int,
    item_key: str = 'items'
) -> Dict[str, Any]:
    """Standardize paginated response format"""
    try:
        # Validate inputs
        if not isinstance(items, list):
            log_error(f"Invalid items type: {type(items)}")
            items = []
            
        if not isinstance(page, int) or page < 1:
            log_error(f"Invalid page number: {page}")
            page = 1
            
        if not isinstance(per_page, int) or per_page < 1:
            log_error(f"Invalid per_page value: {per_page}")
            per_page = 10
            
        if not isinstance(total, int) or total < 0:
            log_error(f"Invalid total value: {total}")
            total = len(items)
            
        if not isinstance(item_key, str):
            log_error(f"Invalid item_key type: {type(item_key)}")
            item_key = 'items'
        
        # Calculate pagination values safely
        pages = max(1, (total + per_page - 1) // per_page)
        has_next = page * per_page < total
        has_prev = page > 1
        
        return {
            'success': True,
            'data': {
                item_key: items,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': pages,
                    'has_next': has_next,
                    'has_prev': has_prev
                }
            },
            'error': None,
            'error_type': None
        }
    except Exception as e:
        log_error(f"Error standardizing paginated response: {e}")
        return {
            'success': False,
            'data': None,
            'error': 'Error formatting paginated response',
            'error_type': 'response_format_error'
        }
