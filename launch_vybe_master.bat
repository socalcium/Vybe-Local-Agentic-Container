@echo off
TITLE Vybe AI Assistant - Master Launcher

:: --- DEFINE CORE PATHS ---
SET "VYBE_DIR=%~dp0"
SET "PYTHON_EXE=%VYBE_DIR%vybe-env-311-fixed\Scripts\python.exe"
SET "TAURI_APP=%VYBE_DIR%vybe-desktop\src-tauri\target\release\Vybe AI Desktop.exe"
SET "SHUTDOWN_SCRIPT=%VYBE_DIR%shutdown.bat"
SET "LOCK_FILE=%VYBE_DIR%vybe.lock"

:: --- CONFLICT PREVENTION ---
IF EXIST "%LOCK_FILE%" (
    ECHO Vybe is already running or a previous session didn't shut down properly.
    ECHO Lock file found: %LOCK_FILE%
    ECHO.
    ECHO To force start, delete the lock file and run again.
    ECHO To check if Vybe is actually running, look for Python processes.
    ECHO.
    PAUSE
    EXIT /B 1
)

:: Create lock file to prevent multiple launches
ECHO %DATE% %TIME% > "%LOCK_FILE%"

CLS
ECHO #############################################################
ECHO #                  Starting Vybe AI Assistant                 #
ECHO #############################################################
ECHO.

:: --- STAGE 1: LAUNCH FLASK BACKEND (includes integrated LLM server) ---
ECHO [1/3] Starting the Vybe Backend Server...

:: Check if backend is already running
powershell -Command "$ProgressPreference='SilentlyContinue'; try { $r=Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/api/health -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }"
IF %ERRORLEVEL% EQU 0 (
    ECHO Backend is already running!
    GOTO LAUNCH_DESKTOP
)

:: Start backend only if not already running
start "Vybe Backend" /B cmd /c "CALL "%VYBE_DIR%vybe-env-311-fixed\Scripts\activate.bat" && python "%VYBE_DIR%run.py""

:: --- STAGE 2: WAIT FOR BACKEND HEALTH (HTTP) ---
ECHO [2/3] Waiting for Vybe Backend to report healthy...
set /a _attempts=0
:WAIT_LOOP
powershell -Command "$ProgressPreference='SilentlyContinue'; try { $r=Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/api/system/health -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }"
IF %ERRORLEVEL% NEQ 0 (
    set /a _attempts+=1
    IF %_attempts% GEQ 60 GOTO HEALTH_TIMEOUT
    timeout /t 1 >nul
    GOTO WAIT_LOOP
)
ECHO ... Backend is healthy!
GOTO LAUNCH_DESKTOP

:HEALTH_TIMEOUT
ECHO Backend health check timed out; continuing to launch UI (may still be initializing)...

:LAUNCH_DESKTOP
ECHO.

:: --- STAGE 3: LAUNCH DESKTOP APP (OR WEB FALLBACK) ---
ECHO [3/3] Launching Desktop App...
IF EXIST "%TAURI_APP%" (
    ECHO Found desktop app, launching...
    CALL "%TAURI_APP%"
) ELSE (
    ECHO Desktop app not found, opening web version...
    start http://localhost:8000
    ECHO Web version opened in browser. Press any key to shutdown when done.
    pause >nul
)

:: --- FINAL STAGE: SHUTDOWN ---
ECHO.
ECHO Desktop app has been closed. Shutting down backend services...
CALL "%SHUTDOWN_SCRIPT%"

:: Clean up lock file
IF EXIST "%LOCK_FILE%" DEL "%LOCK_FILE%"

ECHO Shutdown complete.
timeout /t 3
EXIT