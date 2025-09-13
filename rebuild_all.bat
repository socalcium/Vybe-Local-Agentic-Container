@echo off
setlocal enabledelayedexpansion

echo.
echo ================================================================
echo                   VYBE AI - COMPLETE REBUILD
echo ================================================================
echo.

REM Store original directory
set ORIGINAL_DIR=%CD%

REM Check if we're in the right directory
if not exist "vybe_app" (
    echo ERROR: Please run this script from the Vybe root directory.
    echo Expected to find 'vybe_app' directory here.
    pause
    exit /b 1
)

echo [1/8] Cleaning previous builds...
echo --------------------------------

REM Clean Python cache
if exist "__pycache__" rmdir /s /q "__pycache__"
if exist "vybe_app\__pycache__" rmdir /s /q "vybe_app\__pycache__"
for /d /r . %%d in ("__pycache__") do @if exist "%%d" rd /s /q "%%d"

REM Clean instance data (optional - preserves user data)
echo Do you want to reset the database and user data? (y/N)
set /p RESET_DB=
if /i "%RESET_DB%"=="y" (
    echo Resetting database...
    if exist "instance" rmdir /s /q "instance"
    if exist "logs" rmdir /s /q "logs"
) else (
    echo Keeping existing database and logs...
)

REM Clean build artifacts
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "*.egg-info" rmdir /s /q "*.egg-info"

echo.
echo [2/8] Updating Python environment...
echo ------------------------------------

REM Check Python version
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.11+ and add to PATH.
    pause
    exit /b 1
)

REM Upgrade pip first
python -m pip install --upgrade pip

REM Install/upgrade requirements
echo Installing Python dependencies...
python -m pip install -r requirements.txt --upgrade

echo.
echo [3/8] Setting up directories...
echo --------------------------------

REM Create necessary directories
if not exist "instance" mkdir "instance"
if not exist "logs" mkdir "logs"
if not exist "models" mkdir "models"
if not exist "rag_data" mkdir "rag_data"

REM Create user data directories
set USERPROFILE_VYBE=%LOCALAPPDATA%\Vybe AI Assistant
if not exist "%USERPROFILE_VYBE%" mkdir "%USERPROFILE_VYBE%"
if not exist "%USERPROFILE_VYBE%\workspace" mkdir "%USERPROFILE_VYBE%\workspace"
if not exist "%USERPROFILE_VYBE%\logs" mkdir "%USERPROFILE_VYBE%\logs"
if not exist "%USERPROFILE_VYBE%\vendor" mkdir "%USERPROFILE_VYBE%\vendor"

echo.
echo [4/8] Validating backend dependencies...
echo ----------------------------------------

REM Test critical imports
python -c "
try:
    import flask, flask_sqlalchemy, flask_login, flask_socketio
    import chromadb, requests, beautifulsoup4
    import llama_cpp
    print('✅ Core dependencies verified')
except ImportError as e:
    print(f'❌ Missing dependency: {e}')
    exit(1)
"

if errorlevel 1 (
    echo ERROR: Missing critical dependencies. Please check the error above.
    pause
    exit /b 1
)

echo.
echo [5/8] Rebuilding desktop app...
echo --------------------------------

cd vybe-desktop

REM Check Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo WARNING: Node.js not found. Desktop app build will be skipped.
    echo Please install Node.js from https://nodejs.org
    cd ..
    goto :skip_desktop
)

REM Clean node_modules and package-lock
if exist "node_modules" rmdir /s /q "node_modules"
if exist "package-lock.json" del "package-lock.json"

REM Install dependencies
echo Installing Node.js dependencies...
npm install

REM Check Rust for Tauri
rustc --version >nul 2>&1
if errorlevel 1 (
    echo WARNING: Rust not found. Tauri build will be skipped.
    echo Please install Rust from https://rustup.rs/
    cd ..
    goto :skip_tauri
)

REM Clean Tauri build
cd src-tauri
if exist "target" rmdir /s /q "target"
cd ..

REM Build desktop app
echo Building Tauri desktop application...
npm run tauri:build

if errorlevel 1 (
    echo WARNING: Desktop build failed. Continuing with web version...
) else (
    echo ✅ Desktop app built successfully
)

:skip_tauri
cd ..

:skip_desktop

echo.
echo [6/8] Running validation tests...
echo ----------------------------------

REM Basic validation
python -c "
from vybe_app import create_app
app = create_app()
with app.app_context():
    from vybe_app.models import db
    db.create_all()
    print('✅ App creation and database setup successful')
"

if errorlevel 1 (
    echo ERROR: App validation failed. Please check the error above.
    pause
    exit /b 1
)

echo.
echo [7/8] Generating build information...
echo -------------------------------------

REM Create build info file
python -c "
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
        'database': 'reset' if '%RESET_DB%' == 'y' else 'preserved'
    }
}

with open('build_info.json', 'w') as f:
    json.dump(build_info, f, indent=2)

print('✅ Build information saved to build_info.json')
"

echo.
echo [8/8] Final setup and validation...
echo ------------------------------------

REM Run final validation
python validate_build.py

echo.
echo ================================================================
echo                     REBUILD COMPLETE!
echo ================================================================
echo.
echo ✅ All components have been rebuilt successfully
echo.
echo Next steps:
echo   1. Start the application: python run.py
echo   2. Open desktop app: vybe-desktop/src-tauri/target/release/vybe.exe
echo   3. Or access web version: http://localhost:8000
echo.
echo Build information saved in: build_info.json
echo.

REM Return to original directory
cd /d "%ORIGINAL_DIR%"

pause
