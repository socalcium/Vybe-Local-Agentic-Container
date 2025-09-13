@echo off
REM Vybe Desktop Launcher
REM This script ensures the desktop app starts correctly

TITLE Vybe AI - Starting...

REM Get the directory where this script is located
SET "APP_DIR=%~dp0"
SET "EXE_NAME=Vybe AI Desktop.exe"

REM Change to the app directory
CD /D "%APP_DIR%"

REM Check if the executable exists
IF NOT EXIST "%EXE_NAME%" (
    ECHO ERROR: Could not find "%EXE_NAME%"
    ECHO.
    ECHO This launcher should be in the same directory as the Vybe Desktop executable.
    ECHO Please ensure the app is properly installed.
    PAUSE
    EXIT /B 1
)

REM Set environment variables for the app
SET VYBE_DESKTOP_MODE=true
SET VYBE_LAUNCHER=true

REM Start the application
ECHO Starting Vybe AI Desktop...
START "" "%EXE_NAME%"

REM Close this launcher window
EXIT


