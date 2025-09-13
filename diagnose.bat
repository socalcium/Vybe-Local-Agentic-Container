@echo off
echo ================================================
echo        VYBE RUNTIME DIAGNOSTICS
echo ================================================

echo Checking Python installation...
python --version
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Python not found in PATH
) else (
    echo ✅ Python found
)

echo.
echo Checking Python packages...
python -c "import flask; print('✅ Flask:', flask.__version__)" 2>nul || echo "❌ Flask not installed"
python -c "import requests; print('✅ Requests:', requests.__version__)" 2>nul || echo "❌ Requests not installed"
python -c "import socketio; print('✅ SocketIO:', socketio.__version__)" 2>nul || echo "❌ SocketIO not installed"

echo.
echo Checking llama-cpp-python backend...
curl -s http://localhost:11435/v1/models >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo ✅ LLM backend is running
    curl -s http://localhost:11435/v1/models
) else (
    echo ❌ LLM backend not running or not accessible
    echo The backend should start automatically with Vybe
)

echo.
echo Checking file structure...
if exist "vybe_app" (
    echo ✅ vybe_app directory found
) else (
    echo ❌ vybe_app directory missing
)

if exist "run.py" (
    echo ✅ run.py found
) else (
    echo ❌ run.py missing
)

if exist "requirements.txt" (
    echo ✅ requirements.txt found
) else (
    echo ❌ requirements.txt missing
)

if exist "instance" (
    echo ✅ instance directory found
) else (
    echo ❌ instance directory missing
    mkdir instance
    echo Created instance directory
)

echo.
echo ================================================
echo Diagnostics complete!
echo ================================================
pause
