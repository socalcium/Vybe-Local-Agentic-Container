@echo off
TITLE Building Vybe Desktop App

ECHO ============================================
ECHO          Building Vybe Desktop App
ECHO ============================================
ECHO.

ECHO Running enhanced dependency validation...
python validate_build.py
IF %ERRORLEVEL% NEQ 0 (
    ECHO ERROR: Pre-build validation failed!
    PAUSE
    EXIT /B 1
)
ECHO.

SET "SCRIPT_DIR=%~dp0"
SET "DESKTOP_DIR=%SCRIPT_DIR%vybe-desktop"

ECHO Checking for Node.js and npm...
WHERE node >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    ECHO ERROR: Node.js is not installed or not in PATH.
    ECHO Please install Node.js from https://nodejs.org/
    PAUSE
    EXIT /B 1
)

WHERE npm >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    ECHO ERROR: npm is not available.
    ECHO Please ensure Node.js is properly installed.
    PAUSE
    EXIT /B 1
)

ECHO Checking for Rust and Cargo...
WHERE cargo >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    ECHO ERROR: Rust/Cargo is not installed or not in PATH.
    ECHO Please install Rust from https://rustup.rs/
    PAUSE
    EXIT /B 1
)

ECHO.
ECHO Navigating to desktop app directory...
CD /D "%DESKTOP_DIR%"
IF %ERRORLEVEL% NEQ 0 (
    ECHO ERROR: Could not navigate to desktop directory: %DESKTOP_DIR%
    PAUSE
    EXIT /B 1
)

ECHO.
ECHO Installing npm dependencies...
CALL npm install
IF %ERRORLEVEL% NEQ 0 (
    ECHO ERROR: Failed to install npm dependencies.
    PAUSE
    EXIT /B 1
)

ECHO.
ECHO Building desktop application...
ECHO This may take several minutes as it compiles Rust code and bundles resources...
ECHO.
CALL npm run tauri:build
IF %ERRORLEVEL% NEQ 0 (
    ECHO ERROR: Failed to build desktop application.
    ECHO.
    ECHO Common issues and solutions:
    ECHO 1. Make sure Rust is up to date: rustup update
    ECHO 2. Check that all Python dependencies are properly installed
    ECHO 3. Ensure the vybe-env-311-fixed directory exists with Python environment
    ECHO 4. Verify all resource files exist in the specified paths
    ECHO.
    PAUSE
    EXIT /B 1
)

ECHO.
ECHO ============================================
ECHO        Desktop App Build Completed!
ECHO ============================================
ECHO.
ECHO The desktop executable should be in:
ECHO %DESKTOP_DIR%\src-tauri\target\release\
ECHO.

PAUSE
