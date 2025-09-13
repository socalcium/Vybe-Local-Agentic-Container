@echo off
TITLE Vybe Environment Repair Tool

echo ================================================
echo        VYBE ENVIRONMENT REPAIR TOOL
echo ================================================
echo.

:: Get the directory where this batch file is located
SET "VYBE_DIR=%~dp0"
SET "PYTHON_EXE=%VYBE_DIR%vybe-env\Scripts\python.exe"

echo Installation Directory: %VYBE_DIR%
echo.

echo Step 1: Checking Python installation...
python --version
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not found in PATH.
    echo Please install Python 3.11 from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo.
echo Step 2: Removing old virtual environment (if exists)...
if exist "%VYBE_DIR%vybe-env" (
    rmdir /s /q "%VYBE_DIR%vybe-env"
    echo Old environment removed.
) else (
    echo No old environment found.
)

echo.
echo Step 3: Creating fresh virtual environment...
python -m venv "%VYBE_DIR%vybe-env"
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to create virtual environment.
    pause
    exit /b 1
)

echo.
echo Step 4: Upgrading pip...
"%PYTHON_EXE%" -m pip install --upgrade pip

echo.
echo Step 5: Installing dependencies...
"%PYTHON_EXE%" -m pip install -r "%VYBE_DIR%requirements.txt"
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo Step 6: Installing Playwright browsers...
"%PYTHON_EXE%" -m playwright install
if %ERRORLEVEL% NEQ 0 (
    echo WARNING: Playwright browser installation failed (non-critical).
)

echo.
echo Step 7: Creating setup completion flag...
if not exist "%VYBE_DIR%instance" mkdir "%VYBE_DIR%instance"
echo. > "%VYBE_DIR%instance\setup_complete.flag"

echo.
echo ================================================
echo ✅ REPAIR COMPLETED SUCCESSFULLY!
echo ================================================
echo.
echo You can now run Vybe using launch_vybe.bat
echo.
pause
