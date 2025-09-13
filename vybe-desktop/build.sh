#!/bin/bash
# Vybe Desktop Build Script
# This script helps build and package the Vybe desktop application

set -e

echo "🚀 Vybe Desktop Build Script"
echo "=============================="

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo "🔍 Checking prerequisites..."

if ! command_exists "cargo"; then
    echo "❌ Rust/Cargo not found. Please install Rust: https://rustup.rs/"
    exit 1
fi

if ! command_exists "node"; then
    echo "❌ Node.js not found. Please install Node.js: https://nodejs.org/"
    exit 1
fi

if ! command_exists "npm"; then
    echo "❌ npm not found. Please install npm with Node.js"
    exit 1
fi

echo "✅ Prerequisites checked"

# Change to the vybe-desktop directory
cd "$(dirname "$0")"

# Install dependencies
echo "📦 Installing dependencies..."
npm install

# Check if we're in development or build mode
MODE=${1:-dev}

if [ "$MODE" = "build" ]; then
    echo "🏗️  Building Vybe Desktop for production..."
    
    # Generate icons from SVG if needed
    echo "🎨 Generating app icons..."
    # Note: In a real build, you'd use tools like imagemagick to convert SVG to PNG/ICO
    # convert src-tauri/icons/icon.svg -resize 32x32 src-tauri/icons/32x32.png
    # convert src-tauri/icons/icon.svg -resize 128x128 src-tauri/icons/128x128.png
    # etc.
    
    echo "📁 Preparing Python environment for bundling..."
    # In production, you might want to create a minimal Python distribution
    # or use tools like PyInstaller to create a standalone executable
    
    # Build the application
    npm run build
    
    echo "✅ Build completed! Check src-tauri/target/release/ for the executable"
    
elif [ "$MODE" = "dev" ]; then
    echo "🧪 Starting Vybe Desktop in development mode..."
    
    # Check if Flask backend is ready
    echo "🐍 Checking Python environment..."
    if [ ! -d "../vybe-env" ]; then
        echo "⚠️  Warning: vybe-env not found. Make sure to create the Python virtual environment first."
        echo "   Run: conda create -n vybe-env python=3.10"
        echo "   Then: conda activate vybe-env && pip install -r ../requirements.txt"
    fi
    
    # Start development server
    npm run dev
    
else
    echo "❌ Unknown mode: $MODE"
    echo "Usage: $0 [dev|build]"
    echo "  dev   - Start development server (default)"
    echo "  build - Build for production"
    exit 1
fi
