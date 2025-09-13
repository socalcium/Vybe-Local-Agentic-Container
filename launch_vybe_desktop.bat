@echo off
echo.
echo ================================================================
echo               VYBE AI DESKTOP LAUNCHER
echo ================================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python and ensure it's in PATH.
    pause
    exit /b 1
)

REM Check if we're in the right directory
if not exist "run.py" (
    echo ERROR: Please run this script from the Vybe root directory.
    echo Expected to find 'run.py' in current directory.
    pause
    exit /b 1
)

echo [1/3] Starting Flask backend...
echo --------------------------------

REM Start Flask backend in background
start "Vybe Backend" python run.py

echo Waiting for backend to start...
timeout /t 5 /nobreak >nul

echo.
echo [2/3] Checking backend status...
echo --------------------------------

REM Check if backend is responding
for /L %%i in (1,1,10) do (
    curl -s http://localhost:8000/health >nul 2>&1
    if not errorlevel 1 (
        echo ✅ Backend is responding!
        goto :backend_ready
    )
    echo Attempt %%i/10: Backend not ready yet...
    timeout /t 2 /nobreak >nul
)

echo ⚠️  Backend may not be fully ready, but launching desktop app anyway...

:backend_ready
echo.
echo [3/3] Launching desktop application...
echo --------------------------------

REM Check if desktop app exists
set DESKTOP_EXE="vybe-desktop\src-tauri\target\release\Vybe AI Desktop.exe"
if exist %DESKTOP_EXE% (
    echo Starting Vybe AI Desktop...
    start "" %DESKTOP_EXE%
    echo.
    echo ✅ Vybe AI Desktop launched successfully!
    echo.
    echo The application should open shortly.
    echo If you see a 404 error, wait a moment for the backend to fully start.
    echo.
) else (
    echo ERROR: Desktop application not found.
    echo Expected location: %DESKTOP_EXE%
    echo.
    echo Please build the desktop application first by running:
    echo   cd vybe-desktop
    echo   npm run tauri build
    echo.
    pause
    exit /b 1
)

echo ================================================================
echo Both backend and desktop app have been started!
echo Backend: http://localhost:8000
echo.
echo To stop the backend later, close the "Vybe Backend" window
echo or press Ctrl+C in the terminal window.
echo ================================================================
echo.
pause
