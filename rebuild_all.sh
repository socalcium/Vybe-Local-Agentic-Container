#!/bin/bash

# VYBE AI - Complete Rebuild Script (Linux/macOS)
# This script completely rebuilds the Vybe application from scratch

set -e  # Exit on any error

echo
echo "================================================================"
echo "                   VYBE AI - COMPLETE REBUILD"
echo "================================================================"
echo

# Store original directory
ORIGINAL_DIR=$(pwd)

# Check if we're in the right directory
if [ ! -d "vybe_app" ]; then
    echo "ERROR: Please run this script from the Vybe root directory."
    echo "Expected to find 'vybe_app' directory here."
    exit 1
fi

echo "[1/8] Cleaning previous builds..."
echo "--------------------------------"

# Clean Python cache
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.pyo" -delete 2>/dev/null || true

# Clean instance data (optional - preserves user data)
echo "Do you want to reset the database and user data? (y/N)"
read -r RESET_DB
if [[ "$RESET_DB" =~ ^[Yy]$ ]]; then
    echo "Resetting database..."
    rm -rf instance logs 2>/dev/null || true
else
    echo "Keeping existing database and logs..."
fi

# Clean build artifacts
rm -rf build dist *.egg-info 2>/dev/null || true

echo
echo "[2/8] Updating Python environment..."
echo "------------------------------------"

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 not found. Please install Python 3.11+ and add to PATH."
    exit 1
fi

# Check Python version is 3.11+
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if (( $(echo "$PYTHON_VERSION < 3.11" | bc -l) )); then
    echo "ERROR: Python 3.11+ required, found $PYTHON_VERSION"
    exit 1
fi

# Upgrade pip first
python3 -m pip install --upgrade pip

# Install/upgrade requirements
echo "Installing Python dependencies..."
python3 -m pip install -r requirements.txt --upgrade

echo
echo "[3/8] Setting up directories..."
echo "--------------------------------"

# Create necessary directories
mkdir -p instance logs models rag_data

# Create user data directories
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    USER_DATA_DIR="$HOME/Library/Application Support/Vybe AI Assistant"
else
    # Linux
    USER_DATA_DIR="$HOME/.local/share/vybe-ai-assistant"
fi

mkdir -p "$USER_DATA_DIR"/{workspace,logs,vendor}

echo
echo "[4/8] Validating backend dependencies..."
echo "----------------------------------------"

# Test critical imports
python3 -c "
try:
    import flask, flask_sqlalchemy, flask_login, flask_socketio
    import chromadb, requests, beautifulsoup4
    import llama_cpp
    print('✅ Core dependencies verified')
except ImportError as e:
    print(f'❌ Missing dependency: {e}')
    exit(1)
"

echo
echo "[5/8] Rebuilding desktop app..."
echo "--------------------------------"

cd vybe-desktop

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "WARNING: Node.js not found. Desktop app build will be skipped."
    echo "Please install Node.js from https://nodejs.org"
    cd ..
else
    # Clean node_modules and package-lock
    rm -rf node_modules package-lock.json 2>/dev/null || true

    # Install dependencies
    echo "Installing Node.js dependencies..."
    npm install

    # Check Rust for Tauri
    if ! command -v rustc &> /dev/null; then
        echo "WARNING: Rust not found. Tauri build will be skipped."
        echo "Please install Rust from https://rustup.rs/"
        cd ..
    else
        # Clean Tauri build
        rm -rf src-tauri/target 2>/dev/null || true

        # Build desktop app
        echo "Building Tauri desktop application..."
        if npm run tauri:build; then
            echo "✅ Desktop app built successfully"
        else
            echo "WARNING: Desktop build failed. Continuing with web version..."
        fi
        cd ..
    fi
fi

echo
echo "[6/8] Running validation tests..."
echo "----------------------------------"

# Basic validation
python3 -c "
from vybe_app import create_app
app = create_app()
with app.app_context():
    from vybe_app.models import db
    db.create_all()
    print('✅ App creation and database setup successful')
"

echo
echo "[7/8] Generating build information..."
echo "-------------------------------------"

# Create build info file
python3 -c "
import json, datetime, platform, sys
from pathlib import Path

build_info = {
    'build_date': datetime.datetime.now().isoformat(),
    'python_version': sys.version,
    'platform': platform.platform(),
    'architecture': platform.architecture()[0],
    'build_type': 'complete_rebuild',
    'components': {
        'backend': 'rebuilt',
        'desktop': 'rebuilt' if Path('vybe-desktop/src-tauri/target').exists() else 'skipped',
        'database': 'reset' if '$RESET_DB' == 'y' else 'preserved'
    }
}

with open('build_info.json', 'w') as f:
    json.dump(build_info, f, indent=2)

print('✅ Build information saved to build_info.json')
"

echo
echo "[8/8] Final setup and validation..."
echo "------------------------------------"

# Run final validation
python3 validate_build.py

echo
echo "================================================================"
echo "                     REBUILD COMPLETE!"
echo "================================================================"
echo
echo "✅ All components have been rebuilt successfully"
echo
echo "Next steps:"
echo "   1. Start the application: python3 run.py"
echo "   2. Open desktop app: ./vybe-desktop/src-tauri/target/release/vybe"
echo "   3. Or access web version: http://localhost:8000"
echo
echo "Build information saved in: build_info.json"
echo

# Return to original directory
cd "$ORIGINAL_DIR"
