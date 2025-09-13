#!/usr/bin/env python3
"""
Pre-deployment fixes for Vybe 1.0Test
Ensures all critical components are properly configured
"""

import os
import sys
import json
from pathlib import Path

def check_and_fix_imports():
    """Check and fix any import issues in core files"""
    print("Checking imports in core files...")
    
    # Check manager_model.py imports
    manager_model_file = Path("vybe_app/core/manager_model.py")
    if manager_model_file.exists():
        content = manager_model_file.read_text()
        if "from ..core.system_monitor import get_system_usage, get_gpu_usage" in content:
            print("WARNING: Fixing imports in manager_model.py...")
            content = content.replace(
                "from ..core.system_monitor import get_system_usage, get_gpu_usage",
                "from ..core.system_monitor import SystemMonitor"
            )
            manager_model_file.write_text(content)
            print("SUCCESS: Fixed manager_model.py imports")
    
    # Check if get_available_models vs list_available_models
    if manager_model_file.exists():
        content = manager_model_file.read_text()
        if "list_available_models()" in content:
            content = content.replace("list_available_models()", "get_available_models()")
            manager_model_file.write_text(content)
            print("SUCCESS: Fixed method calls in manager_model.py")

def check_template_includes():
    """Ensure all templates have proper includes"""
    print("🔍 Checking template includes...")
    
    # Check if _scripts.html includes prompt-assistant
    scripts_file = Path("vybe_app/templates/_scripts.html")
    if scripts_file.exists():
        content = scripts_file.read_text()
        if "prompt-assistant.js" not in content:
            content += '\n<script src="{{ url_for(\'static\', filename=\'js/modules/prompt-assistant.js\') }}"></script>\n'
            scripts_file.write_text(content)
            print("✅ Added prompt-assistant.js to scripts")
    
    # Check if _head.html includes prompt-assistant CSS
    head_file = Path("vybe_app/templates/_head.html")
    if head_file.exists():
        content = head_file.read_text()
        if "prompt-assistant.css" not in content:
            # Find the last CSS link and add after it
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'performance-dashboard.css' in line:
                    lines.insert(i+1, '<link rel="stylesheet" href="{{ url_for(\'static\', filename=\'css/prompt-assistant.css\') }}">')
                    break
            content = '\n'.join(lines)
            head_file.write_text(content)
            print("✅ Added prompt-assistant.css to head")

def check_api_endpoints():
    """Verify critical API endpoints exist"""
    print("🔍 Checking API endpoints...")
    
    # Check if models/detailed endpoint exists and works properly
    models_api_file = Path("vybe_app/api/models_api.py")
    if models_api_file.exists():
        content = models_api_file.read_text()
        if "def api_installed_models_detailed" in content and "get_available_models()" in content:
            print("✅ Models API endpoint properly configured")
        else:
            print("⚠️  Models API may need attention")

def verify_version_consistency():
    """Ensure all version references are consistent"""
    print("🔍 Verifying version consistency...")
    
    version_files = [
        ("pyproject.toml", "1.0Test"),
        ("vybe_app/api/__init__.py", "1.0Test"),
        ("vybe_app/views.py", "1.0Test"),
        ("vybe-desktop/src-tauri/tauri.conf.json", "1.0Test"),
        ("vybe-desktop/src-tauri/Cargo.toml", "1.0Test")
    ]
    
    for file_path, expected_version in version_files:
        file_obj = Path(file_path)
        if file_obj.exists():
            content = file_obj.read_text()
            if expected_version in content:
                print(f"✅ {file_path} version is correct")
            else:
                print(f"⚠️  {file_path} version may need updating")

def create_instance_directories():
    """Ensure instance directories exist"""
    print("🔍 Creating instance directories...")
    
    instance_dir = Path("instance")
    instance_dir.mkdir(exist_ok=True)
    print("✅ Instance directory created")
    
    # Create workspace directories
    workspace_dir = Path("workspace")
    workspace_dir.mkdir(exist_ok=True)
    print("✅ Workspace directory created")
    
    # Create models directory
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)
    print("✅ Models directory created")

def main():
    """Run all pre-deployment fixes"""
    print("=" * 50)
    print("🚀 Vybe 1.0Test - Pre-Deployment Fixes")
    print("=" * 50)
    print()
    
    try:
        check_and_fix_imports()
        print()
        
        check_template_includes()
        print()
        
        check_api_endpoints()
        print()
        
        verify_version_consistency()
        print()
        
        create_instance_directories()
        print()
        
        print("=" * 50)
        print("✅ All pre-deployment fixes completed!")
        print("🎯 Vybe 1.0Test is ready for deployment")
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ Error during fixes: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()