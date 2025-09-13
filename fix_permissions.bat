@echo off
REM Emergency Permission Fix for Vybe AI
REM Run this if you encounter permission errors during startup

TITLE Vybe AI - Permission Fix

echo ===============================================
echo        Vybe AI - Permission Fix Utility
echo ===============================================
echo.

echo Creating user data directories...

REM Create user data directory structure
SET "USER_DATA=%LOCALAPPDATA%\Vybe AI Assistant"
IF NOT EXIST "%USER_DATA%" mkdir "%USER_DATA%"
IF NOT EXIST "%USER_DATA%\ai_tools" mkdir "%USER_DATA%\ai_tools"
IF NOT EXIST "%USER_DATA%\models" mkdir "%USER_DATA%\models"
IF NOT EXIST "%USER_DATA%\logs" mkdir "%USER_DATA%\logs"

echo User data directories created at: %USER_DATA%

REM Copy models from installation to user directory if they exist
SET "INSTALL_DIR=%~dp0"
IF EXIST "%INSTALL_DIR%models\*.gguf" (
    echo Copying models to user directory...
    copy "%INSTALL_DIR%models\*.gguf" "%USER_DATA%\models\"
)

REM Set environment variable for the session
setx VYBE_USER_DATA_DIR "%USER_DATA%" >nul 2>&1

echo.
echo ✅ Permission fix completed!
echo.
echo The app will now use:
echo - Database: %USER_DATA%\site.db
echo - AI Tools: %USER_DATA%\ai_tools
echo - Models: %USER_DATA%\models
echo - Logs: %USER_DATA%\logs
echo.
pause
