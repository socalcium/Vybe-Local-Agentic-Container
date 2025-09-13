@echo off
REM Vybe Desktop Build Script for Windows
REM This script helps build and package the Vybe desktop application

echo 🚀 Vybe Desktop Build Script
echo ==============================

REM Check prerequisites
echo 🔍 Checking prerequisites...

where cargo >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Rust/Cargo not found. Please install Rust: https://rustup.rs/
    exit /b 1
)

where node >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Node.js not found. Please install Node.js: https://nodejs.org/
    exit /b 1
)

where npm >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ npm not found. Please install npm with Node.js
    exit /b 1
)

echo ✅ Prerequisites checked

REM Change to the vybe-desktop directory
cd /d "%~dp0"

REM Install dependencies
echo 📦 Installing dependencies...
npm install

REM Check mode
set MODE=%1
if "%MODE%"=="" set MODE=dev

if "%MODE%"=="build" (
    echo 🏗️  Building Vybe Desktop for production...
    
    echo 🎨 Generating app icons...
    REM Note: In a real build, you'd use tools to convert SVG to PNG/ICO
    
    echo 📁 Preparing Python environment for bundling...
    REM In production, you might want to create a minimal Python distribution
    
    REM Build the application
    npm run build
    
    echo ✅ Build completed! Check src-tauri\target\release\ for the executable
    
) else if "%MODE%"=="dev" (
    echo 🧪 Starting Vybe Desktop in development mode...
    
    echo 🐍 Checking Python environment...
    if not exist "..\vybe-env\" (
        echo ⚠️  Warning: vybe-env not found. Make sure to create the Python virtual environment first.
        echo    Run: conda create -n vybe-env python=3.10
        echo    Then: conda activate vybe-env ^&^& pip install -r ..\requirements.txt
    )
    
    REM Start development server
    npm run dev
    
) else (
    echo ❌ Unknown mode: %MODE%
    echo Usage: %~nx0 [dev^|build]
    echo   dev   - Start development server ^(default^)
    echo   build - Build for production
    exit /b 1
)

pause
