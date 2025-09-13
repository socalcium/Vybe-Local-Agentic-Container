#!/usr/bin/env python3
"""
Vybe AI Assistant - Comprehensive Setup Verification Script

This script performs a complete diagnostic check of your Vybe installation.
It verifies system dependencies, Python environment, AI models, and application files.
Run this script to troubleshoot any issues with your Vybe setup.
"""

import os
import sys
import subprocess
import json
import importlib
import sqlite3
from pathlib import Path
from urllib.parse import urlparse


def check_command(command, version_flag="--version"):
    """Check if a command exists and is executable."""
    try:
        result = subprocess.run([command, version_flag], 
                              capture_output=True, text=True, timeout=10)
        return result.returncode == 0, result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        return False, ""


def check_file_exists(filepath, description=""):
    """Check if a file exists."""
    exists = os.path.exists(filepath)
    return exists, f"{description}: {'✓ Found' if exists else '✗ Missing'}"


def check_directory_exists(dirpath, description=""):
    """Check if a directory exists."""
    exists = os.path.isdir(dirpath)
    return exists, f"{description}: {'✓ Found' if exists else '✗ Missing'}"


def check_python_package(package_name, import_name=None):
    """Check if a Python package is installed and importable."""
    if import_name is None:
        import_name = package_name
    
    try:
        importlib.import_module(import_name)
        return True, f"✓ {package_name} installed"
    except ImportError:
        return False, f"✗ {package_name} missing"


def check_model_file(filepath, description, min_size_mb=1):
    """Check if a model file exists and has reasonable size."""
    if not os.path.exists(filepath):
        return False, f"✗ {description}: Missing"
    
    size_mb = os.path.getsize(filepath) / (1024 * 1024)
    if size_mb < min_size_mb:
        return False, f"✗ {description}: Too small ({size_mb:.1f}MB)"
    
    return True, f"✓ {description}: {size_mb:.1f}MB"


def check_git_repo(repo_path, expected_remote=None):
    """Check if a directory is a valid git repository."""
    git_dir = os.path.join(repo_path, '.git')
    if not os.path.exists(git_dir):
        return False, "Not a git repository"
    
    if expected_remote:
        try:
            result = subprocess.run(['git', '-C', repo_path, 'remote', 'get-url', 'origin'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                remote_url = result.stdout.strip()
                if expected_remote.lower() in remote_url.lower():
                    return True, f"✓ Correct repository: {remote_url}"
                else:
                    return False, f"✗ Wrong repository: {remote_url}"
        except Exception as e:
            print(f"Warning: Git remote check failed: {e}")
            pass
    
    return True, "✓ Valid git repository"


def check_llm_backend_connection():
    """Check if integrated LLM backend is running and accessible."""
    try:
        import requests
        response = requests.get('http://localhost:11435/v1/models', timeout=5)
        if response.status_code == 200:
            models = response.json().get('data', [])
            return True, f"✓ LLM backend running with {len(models)} models"
        else:
            return False, "✗ LLM backend not responding"
    except Exception as e:
        return False, f"✗ LLM backend not accessible: {e}"


def check_database_integrity(db_path):
    """Check if SQLite database exists and is valid."""
    if not os.path.exists(db_path):
        return False, "Database file missing"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        conn.close()
        return True, f"✓ Database valid with {len(tables)} tables"
    except Exception as e:
        return False, f"✗ Database corrupted: {str(e)}"


def main():
    print("🔍 Vybe AI Assistant - Comprehensive Setup Verification")
    print("=" * 60)
    
    # Get the current working directory
    current_dir = Path.cwd()
    if current_dir.name == "vybe-desktop":
        project_root = current_dir.parent
    elif (current_dir / "vybe-desktop").exists():
        project_root = current_dir
    else:
        # Look for key files to identify project root
        for parent in [current_dir] + list(current_dir.parents):
            if (parent / "run.py").exists() and (parent / "vybe_app").exists():
                project_root = parent
                break
        else:
            project_root = current_dir
    
    desktop_dir = project_root / "vybe-desktop"
    
    print(f"📂 Project Root: {project_root}")
    print(f"📂 Desktop Dir: {desktop_dir}")
    print()
    
    all_checks_passed = True
    warnings = []
    
    # ===================
    # SYSTEM DEPENDENCIES
    # ===================
    print("🛠️  System Dependencies:")
    print("-" * 25)
    
    # Core system tools
    system_checks = [
        ("python", "python", "--version", "Python interpreter"),
        ("pip", "pip", "--version", "Python package manager"),
        ("git", "git", "--version", "Git version control"),
        ("node", "node", "--version", "Node.js runtime"),
        ("npm", "npm", "--version", "NPM package manager"),
    ]
    
    for name, command, flag, description in system_checks:
        success, output = check_command(command, flag)
        status = "✓" if success else "✗"
        version = output.split()[0] if success and output else 'Not found'
        print(f"  {status} {description}: {version}")
        if not success:
            all_checks_passed = False
    
    # Rust and Cargo (for desktop app)
    rust_success, rust_output = check_command("rustc", "--version")
    cargo_success, cargo_output = check_command("cargo", "--version")
    
    print(f"  {'✓' if rust_success else '✗'} Rust compiler: {rust_output.split()[1] if rust_success and rust_output else 'Not found'}")
    print(f"  {'✓' if cargo_success else '✗'} Cargo package manager: {cargo_output.split()[1] if cargo_success and cargo_output else 'Not found'}")
    
    if not rust_success or not cargo_success:
        warnings.append("Rust/Cargo missing - desktop app cannot be built")
    
    print()
    
    # ==================
    # PYTHON ENVIRONMENT
    # ==================
    print("🐍 Python Environment:")
    print("-" * 20)
    
    vybe_env_path = project_root / "vybe-env"
    env_exists, env_msg = check_directory_exists(vybe_env_path, "Virtual environment")
    print(f"  {env_msg}")
    if not env_exists:
        all_checks_passed = False
    
    # Check Python executable in virtual environment
    if os.name == 'nt':  # Windows
        python_exe = vybe_env_path / "Scripts" / "python.exe"
        pip_exe = vybe_env_path / "Scripts" / "pip.exe"
    else:  # Unix-like
        python_exe = vybe_env_path / "bin" / "python"
        pip_exe = vybe_env_path / "bin" / "pip"
    
    python_exists, python_msg = check_file_exists(python_exe, "Python executable")
    print(f"  {python_msg}")
    if not python_exists:
        all_checks_passed = False
    
    pip_exists, pip_msg = check_file_exists(pip_exe, "Pip executable")
    print(f"  {pip_msg}")
    
    print()
    
    # ====================
    # PYTHON PACKAGES
    # ====================
    print("📦 Python Packages:")
    print("-" * 18)
    
    # Key packages required by Vybe
    required_packages = [
        ("flask", "Flask"),
        ("requests", "requests"),
        ("openai", "openai"),
        ("langchain", "langchain"),
        ("chromadb", "chromadb"),
        ("sentence-transformers", "sentence_transformers"),
        ("torch", "torch"),
        ("transformers", "transformers"),
        ("Pillow", "PIL"),
        ("numpy", "numpy"),
        ("pandas", "pandas"),
        ("sqlalchemy", "sqlalchemy"),
        ("beautifulsoup4", "bs4"),
        ("python-dotenv", "dotenv"),
        ("pydantic", "pydantic"),
    ]
    
    # Only check packages if Python environment exists
    if python_exists:
        # Add the virtual environment to Python path temporarily
        venv_site_packages = vybe_env_path / ("Lib" if os.name == 'nt' else "lib") / "site-packages"
        if venv_site_packages.exists():
            sys.path.insert(0, str(venv_site_packages))
        
        package_issues = 0
        for package_name, import_name in required_packages:
            success, msg = check_python_package(package_name, import_name)
            print(f"  {msg}")
            if not success:
                package_issues += 1
        
        if package_issues > 0:
            warnings.append(f"{package_issues} Python packages missing")
            print(f"    💡 Install with: pip install -r requirements.txt")
    else:
        print("  ⚠️  Cannot check packages - Python environment not found")
        all_checks_passed = False
    
    print()
    
    # ===================
    # APPLICATION FILES
    # ===================
    print("📁 Application Files:")
    print("-" * 19)
    
    app_files = [
        (project_root / "run.py", "Flask application entry point"),
        (project_root / "requirements.txt", "Python requirements"),
        (project_root / "vybe_app" / "__init__.py", "Vybe app module"),
        (project_root / "vybe_app" / "views.py", "Flask views"),
        (project_root / "vybe_app" / "models.py", "Data models"),
        (project_root / "vybe_app" / "config.py", "Configuration"),
    ]
    
    for filepath, description in app_files:
        exists, msg = check_file_exists(filepath, description)
        print(f"  {msg}")
        if not exists:
            all_checks_passed = False
    
    print()
    
    # ===================
    # DESKTOP APPLICATION
    # ===================
    print("🖥️  Desktop Application:")
    print("-" * 22)
    
    desktop_files = [
        (desktop_dir / "package.json", "Package configuration"),
        (desktop_dir / "src" / "loading.html", "Loading screen"),
        (desktop_dir / "src" / "main.js", "Main JavaScript"),
        (desktop_dir / "src-tauri" / "Cargo.toml", "Rust dependencies"),
        (desktop_dir / "src-tauri" / "tauri.conf.json", "Tauri configuration"),
        (desktop_dir / "src-tauri" / "src" / "main.rs", "Rust application"),
        (desktop_dir / "src-tauri" / "build.rs", "Build script"),
    ]
    
    desktop_missing = 0
    for filepath, description in desktop_files:
        exists, msg = check_file_exists(filepath, description)
        print(f"  {msg}")
        if not exists:
            desktop_missing += 1
    
    if desktop_missing > 0:
        warnings.append(f"Desktop app incomplete ({desktop_missing} files missing)")
    
    # Node modules check
    node_modules = desktop_dir / "node_modules"
    nm_exists, nm_msg = check_directory_exists(node_modules, "Node.js dependencies")
    print(f"  {nm_msg}")
    if not nm_exists:
        warnings.append("Run 'npm install' in vybe-desktop directory")
    
    print()
    
    # ===================
    # VENDOR REPOSITORIES
    # ===================
    print("📦 Vendor Repositories:")
    print("-" * 21)
    
    vendor_dir = project_root / "vybe_app" / "vendor"
    vendor_exists, vendor_msg = check_directory_exists(vendor_dir, "Vendor directory")
    print(f"  {vendor_msg}")
    
    if vendor_exists:
        # Check AUTOMATIC1111
        auto1111_path = vendor_dir / "stable-diffusion-webui"
        auto1111_exists = auto1111_path.exists()
        if auto1111_exists:
            success, msg = check_git_repo(auto1111_path, "AUTOMATIC1111/stable-diffusion-webui")
            print(f"  ✓ AUTOMATIC1111: {msg}")
        else:
            print("  ✗ AUTOMATIC1111: Missing")
            warnings.append("Clone AUTOMATIC1111/stable-diffusion-webui to vybe_app/vendor/")
        
        # Check Whisper.cpp
        whisper_path = vendor_dir / "whisper.cpp"
        whisper_exists = whisper_path.exists()
        if whisper_exists:
            success, msg = check_git_repo(whisper_path, "ggerganov/whisper.cpp")
            print(f"  ✓ Whisper.cpp: {msg}")
        else:
            print("  ✗ Whisper.cpp: Missing")
            warnings.append("Clone ggerganov/whisper.cpp to vybe_app/vendor/")
    else:
        warnings.append("Create vendor directory and clone required repositories")
    
    print()
    
    # ===================
    # AI MODELS
    # ===================
    print("🤖 AI Models:")
    print("-" * 11)
    
    models_dir = project_root / "vybe_app" / "models"
    models_exists, models_msg = check_directory_exists(models_dir, "Models directory")
    print(f"  {models_msg}")
    
    if models_exists:
        # Check Whisper models
        whisper_models_dir = models_dir / "whisper"
        if whisper_models_dir.exists():
            whisper_base = whisper_models_dir / "ggml-base.bin"
            whisper_tiny = whisper_models_dir / "ggml-tiny.bin"
            
            base_success, base_msg = check_model_file(whisper_base, "Whisper Base", 100)
            tiny_success, tiny_msg = check_model_file(whisper_tiny, "Whisper Tiny", 30)
            
            print(f"  {base_msg}")
            print(f"  {tiny_msg}")
        else:
            print("  ✗ Whisper models: Directory missing")
            warnings.append("Download Whisper models")
        
        # Check Stable Diffusion models
        sd_models_dir = models_dir / "stable_diffusion"
        if sd_models_dir.exists():
            sd_model = sd_models_dir / "v1-5-pruned-emaonly.safetensors"
            sd_success, sd_msg = check_model_file(sd_model, "Stable Diffusion 1.5", 3000)
            print(f"  {sd_msg}")
        else:
            print("  ✗ Stable Diffusion models: Directory missing")
            warnings.append("Download Stable Diffusion models")
        
        # Check model configuration
        model_config = models_dir / "model_config.json"
        config_exists, config_msg = check_file_exists(model_config, "Model configuration")
        print(f"  {config_msg}")
    else:
        warnings.append("Create models directory and download AI models")
    
    print()
    
    # ===================
    # EXTERNAL SERVICES
    # ===================
    print("🌐 External Services:")
    print("-" * 19)
    
    # Check LLM Backend
    llm_success, llm_msg = check_llm_backend_connection()
    print(f"  {llm_msg}")
    if not llm_success:
        warnings.append("Start Vybe to initialize integrated LLM backend")
    
    print()
    
    # ===================
    # WORKSPACE & DATA
    # ===================
    print("💾 Workspace & Data:")
    print("-" * 17)
    
    workspace_dirs = [
        (project_root / "workspace", "Workspace directory"),
        (project_root / "workspace" / "uploads", "Uploads directory"),
        (project_root / "workspace" / "generated_images", "Generated images"),
        (project_root / "workspace" / "generated_audio", "Generated audio"),
        (project_root / "logs", "Logs directory"),
        (project_root / "instance", "Instance directory"),
    ]
    
    for dirpath, description in workspace_dirs:
        exists, msg = check_directory_exists(dirpath, description)
        print(f"  {msg}")
        if not exists:
            dirpath.mkdir(parents=True, exist_ok=True)
            print(f"    💡 Created {description.lower()}")
    
    # Check database
    db_path = project_root / "instance" / "site.db"
    if db_path.exists():
        db_success, db_msg = check_database_integrity(db_path)
        print(f"  {db_msg}")
    else:
        print("  ⚠️  Database: Will be created on first run")
    
    print()
    
    # ===================
    # FINAL SUMMARY
    # ===================
    print("📋 Summary:")
    print("-" * 10)
    
    if all_checks_passed and len(warnings) == 0:
        print("  🎉 All checks passed! Vybe is ready to use.")
        print("     Start with: python run.py")
        if desktop_dir.exists():
            print("     Desktop app: cd vybe-desktop && npm run tauri:dev")
    elif all_checks_passed and len(warnings) > 0:
        print("  ⚠️  Core components ready, but some issues found:")
        for warning in warnings:
            print(f"     • {warning}")
        print("     Vybe should still work, but some features may be limited.")
    else:
        print("  ❌ Critical issues found. Please resolve the following:")
        print("     • Install missing system dependencies")
        print("     • Set up Python virtual environment")
        print("     • Install Python packages: pip install -r requirements.txt")
        if len(warnings) > 0:
            print("     • Address warnings listed above")
    
    print()
    
    # ===================
    # HELP & RESOURCES
    # ===================
    print("🆘 Quick Fixes:")
    print("-" * 13)
    print("  Setup virtual env:  python -m venv vybe-env")
    print("  Activate (Windows):  vybe-env\\Scripts\\activate")
    print("  Activate (Unix):     source vybe-env/bin/activate")
    print("  Install packages:    pip install -r requirements.txt")
    print("  Desktop setup:       cd vybe-desktop && npm install")
    print("  Generate icons:      npm run tauri icon")
    print("  Integrated LLM Backend: Included with Vybe")
    print("  Install Rust:        https://rustup.rs/")
    
    return 0 if all_checks_passed and len(warnings) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
