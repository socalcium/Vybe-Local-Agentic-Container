#!/usr/bin/env python3
"""
Validate which TODO items are still relevant by checking actual file contents
"""

import os
import re
from pathlib import Path

def check_file_exists(file_path):
    """Check if a file exists"""
    return Path(file_path).exists()

def check_import_exists(file_path, import_statement):
    """Check if an import statement exists in a file"""
    if not check_file_exists(file_path):
        return False, "File does not exist"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if import_statement in content:
                return True, "Import exists"
            else:
                return False, "Import not found"
    except Exception as e:
        return False, f"Error reading file: {e}"

def check_class_structure(file_path, class_name):
    """Check if a class has proper structure"""
    if not check_file_exists(file_path):
        return False, "File does not exist"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check for class definition
        class_pattern = f"class {class_name}"
        if class_pattern not in content:
            return False, f"Class {class_name} not found"
        
        # Check for malformed event listener calls
        malformed_pattern = r'window\.eventManager\.add\([^,]+,\s*[^,]+,\s*\([^)]*\)\s*=>\s*{\s*/\*[^*]*\*/\s*},\s*{}\)'
        if re.search(malformed_pattern, content):
            return False, "Malformed event listener calls found"
        
        return True, "Class structure appears correct"
    except Exception as e:
        return False, f"Error reading file: {e}"

# Critical issues to check
critical_checks = [
    {
        'name': 'Agent Manager Import',
        'type': 'import',
        'file': 'vybe_app/core/agent_manager.py',
        'check': 'from ..tools import ai_write_file'
    },
    {
        'name': 'Marketplace Manager Class',
        'type': 'class',
        'file': 'vybe_app/static/js/marketplace_manager.js',
        'class': 'MarketplaceManager'
    },
    {
        'name': 'Mobile Navigation Class',
        'type': 'class',
        'file': 'vybe_app/static/js/mobile-navigation.js',
        'class': 'MobileNavigation'
    },
    {
        'name': 'Settings Manager Class',
        'type': 'class',
        'file': 'vybe_app/static/js/settings.js',
        'class': 'SettingsManager'
    },
    {
        'name': 'Audio IO File',
        'type': 'file',
        'file': 'vybe_app/core/audio_io.py'
    }
]

print("Validating TODO items...\n")

for check in critical_checks:
    file_path = check['file']
    
    if check['type'] == 'import':
        exists, message = check_import_exists(file_path, check['check'])
        status = "✅ FIXED" if exists else "❌ NEEDS FIX"
        print(f"{status} - {check['name']}: {message}")
    
    elif check['type'] == 'class':
        exists, message = check_class_structure(file_path, check['class'])
        status = "✅ FIXED" if exists else "❌ NEEDS FIX"
        print(f"{status} - {check['name']}: {message}")
    
    elif check['type'] == 'file':
        exists = check_file_exists(file_path)
        status = "✅ EXISTS" if exists else "❌ MISSING"
        print(f"{status} - {check['name']}: {'File exists' if exists else 'File not found'}")

print("\nValidation complete.")
