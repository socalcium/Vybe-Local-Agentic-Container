#!/usr/bin/env python3
"""
Pre-build validation script for Vybe Desktop App
Checks all prerequisites and resources before building the Tauri app
"""

import os
import sys
import subprocess
import json
from pathlib import Path

# Replace Unicode emojis with ASCII fallbacks for Windows consoles
import builtins as _builtins
def _safe_print(*args, **kwargs):
    replacements = {
        '✅': '[OK]',
        '❌': '[X]',
        '📋': '[TOOLS]',
        '🐍': '[PY]',
        '📁': '[FILES]',
        '🏗️': '[TAURI]',
        '🖼️': '[ICONS]',
        '🎉': '[READY]',
    }
    safe_args = []
    for a in args:
        if isinstance(a, str):
            for k, v in replacements.items():
                a = a.replace(k, v)
        safe_args.append(a)
    return _builtins.print(*safe_args, **kwargs)

# Monkey-patch print to be safe across code pages
print = _safe_print  # type: ignore

def check_command(cmd, name):
    """Check if a command is available in PATH"""
    try:
        result = subprocess.run([cmd, '--version'], 
                              capture_output=True, text=True, timeout=10, shell=True)
        if result.returncode == 0:
            version = result.stdout.strip().split('\n')[0] if result.stdout else 'Found'
            print(f"✅ {name}: {version}")
            return True
        else:
            print(f"❌ {name}: Command failed (exit code {result.returncode})")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError) as e:
        print(f"❌ {name}: Not found or not working ({e})")
        return False

def check_file_exists(path, description):
    """Check if a file or directory exists"""
    if os.path.exists(path):
        if os.path.isdir(path):
            file_count = len(list(Path(path).rglob('*')))
            print(f"✅ {description}: Found ({file_count} files)")
        else:
            size = os.path.getsize(path)
            print(f"✅ {description}: Found ({size:,} bytes)")
        return True
    else:
        print(f"❌ {description}: Not found at {path}")
        return False

def check_python_env():
    """Check Python environment and dependencies"""
    env_path = "vybe-env-311-fixed"
    python_exe = os.path.join(env_path, "Scripts", "python.exe")
    
    if not check_file_exists(env_path, "Python virtual environment"):
        return False
        
    if not check_file_exists(python_exe, "Python executable"):
        return False
    
    # Try to run Python and check version
    try:
        result = subprocess.run([python_exe, '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✅ Python version: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ Python executable not working")
            return False
    except Exception as e:
        print(f"❌ Python check failed: {e}")
        return False

def main():
    print("=" * 60)
    print("        VYBE DESKTOP APP - BUILD VALIDATION")
    print("=" * 60)
    print()
    
    all_good = True
    
    print("📋 Checking build tools...")
    all_good &= check_command('cargo', 'Rust/Cargo')
    all_good &= check_command('node', 'Node.js')
    all_good &= check_command('npm', 'npm')
    print()
    
    print("🐍 Checking Python environment...")
    all_good &= check_python_env()
    print()
    
    print("📁 Checking required directories and files...")
    all_good &= check_file_exists('vybe_app', 'Vybe application directory')
    all_good &= check_file_exists('models', 'Models directory')
    all_good &= check_file_exists('run.py', 'Main Python script')
    all_good &= check_file_exists('requirements.txt', 'Requirements file')
    all_good &= check_file_exists('instance', 'Instance directory')
    print()
    
    print("🏗️ Checking Tauri configuration...")
    all_good &= check_file_exists('vybe-desktop/src-tauri/Cargo.toml', 'Tauri Cargo.toml')
    all_good &= check_file_exists('vybe-desktop/src-tauri/tauri.conf.json', 'Tauri config')
    all_good &= check_file_exists('vybe-desktop/src-tauri/src/main.rs', 'Tauri main.rs')
    all_good &= check_file_exists('vybe-desktop/package.json', 'Node.js package.json')
    all_good &= check_file_exists('vybe-desktop/src/main.js', 'Frontend main.js')
    print()
    
    print("🖼️ Checking icons...")
    icon_dir = "vybe-desktop/src-tauri/icons"
    all_good &= check_file_exists(f'{icon_dir}/32x32.png', 'App icon 32x32')
    all_good &= check_file_exists(f'{icon_dir}/128x128.png', 'App icon 128x128')
    print()
    
    if all_good:
        print("🎉 All checks passed! Ready to build the desktop app.")
        print()
        print("Next steps:")
        print("1. Run: build_desktop.bat")
        print("2. The executable will be in: vybe-desktop/src-tauri/target/release/")
        sys.exit(0)
    else:
        print("❌ Some checks failed. Please fix the issues above before building.")
        print()
        print("Common solutions:")
        print("• Install missing tools (Rust, Node.js)")
        print("• Create Python virtual environment: python -m venv vybe-env-311-fixed")
        print("• Install Python dependencies: pip install -r requirements.txt")
        print("• Ensure all project files are in the correct locations")
        sys.exit(1)

if __name__ == "__main__":
    main()
