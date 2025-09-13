"""
Input validation utilities for Vybe application.
Provides comprehensive validation for API inputs and user data.
"""

import re
from typing import Any, Dict, List, Optional, Union
from flask import jsonify

class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass

class InputValidator:
    """Centralized input validation"""
    
    # Common regex patterns
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_]{3,50}$')
    FILENAME_PATTERN = re.compile(r'^[a-zA-Z0-9._-]+$')
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        if not email or not isinstance(email, str):
            return False
        return bool(InputValidator.EMAIL_PATTERN.match(email))
    
    @staticmethod
    def validate_username(username: str) -> bool:
        """Validate username format"""
        if not username or not isinstance(username, str):
            return False
        return bool(InputValidator.USERNAME_PATTERN.match(username))
    
    @staticmethod
    def validate_filename(filename: str) -> bool:
        """Validate filename format"""
        if not filename or not isinstance(filename, str):
            return False
        return bool(InputValidator.FILENAME_PATTERN.match(filename))
    
    @staticmethod
    def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> List[str]:
        """Check for required fields and return list of missing fields"""
        missing_fields = []
        for field in required_fields:
            if field not in data or data[field] is None or data[field] == '':
                missing_fields.append(field)
        return missing_fields
    
    @staticmethod
    def validate_chat_request(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate chat request data"""
        errors = {}
        
        # Check required fields
        missing = InputValidator.validate_required_fields(data, ['message'])
        if missing:
            errors['missing_fields'] = missing
        
        # Validate message length
        message = data.get('message', '')
        if isinstance(message, str) and len(message) > 10000:
            errors['message'] = 'Message too long (max 10000 characters)'
        
        # Validate temperature
        temp = data.get('temperature')
        if temp is not None:
            try:
                temp_float = float(temp)
                if not 0.0 <= temp_float <= 2.0:
                    errors['temperature'] = 'Temperature must be between 0.0 and 2.0'
            except (ValueError, TypeError):
                errors['temperature'] = 'Temperature must be a number'
        
        # Validate model name
        model = data.get('model', '')
        if model and not isinstance(model, str):
            errors['model'] = 'Model must be a string'
        
        return errors
    
    @staticmethod
    def sanitize_string(text: str, max_length: int = 1000, allow_html: bool = False) -> str:
        """Sanitize string input with optional HTML sanitization"""
        if not isinstance(text, str):
            return ''
        
        if not allow_html:
            # Remove HTML tags and potentially harmful characters
            import html
            text = html.escape(text)  # Escape HTML entities
            # Remove script and style tags and their content
            text = re.sub(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', '', text, flags=re.IGNORECASE)
            text = re.sub(r'<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>', '', text, flags=re.IGNORECASE)
            # Remove remaining HTML tags
            text = re.sub(r'<[^>]+>', '', text)
        else:
            # Only remove potentially harmful characters but keep basic HTML
            text = re.sub(r'[<>"\']', '', text)
        
        # Truncate if too long
        if len(text) > max_length:
            text = text[:max_length]
        
        return text.strip()

def require_json_fields(*required_fields):
    """Decorator to validate required JSON fields in request"""
    def decorator(f):
        def wrapper(*args, **kwargs):
            from flask import request
            
            if not request.is_json:
                return jsonify({'error': 'Content-Type must be application/json'}), 400
            
            data = request.get_json()
            if not data:
                return jsonify({'error': 'Invalid JSON data'}), 400
            
            missing_fields = InputValidator.validate_required_fields(data, list(required_fields))
            if missing_fields:
                return jsonify({
                    'error': 'Missing required fields',
                    'missing_fields': missing_fields
                }), 400
            
            return f(*args, **kwargs)
        
        wrapper.__name__ = f.__name__
        return wrapper
    return decorator
