@echo off
REM Silent shutdown for uninstaller - terminates Vybe processes without user interaction
setlocal enabledelayedexpansion

REM Kill Python processes running from this installation
for /f "tokens=2" %%i in ('tasklist /fi "imagename eq python.exe" /fo table /nh 2^>nul') do (
    taskkill /pid %%i /f >nul 2>&1
)

REM Kill Python processes (including llama-cpp-python server)
taskkill /f /im python.exe >nul 2>&1

REM Kill any browser processes that might be running Vybe
for /f "tokens=2" %%i in ('tasklist /fi "windowtitle eq*Vybe*" /fo table /nh 2^>nul') do (
    taskkill /pid %%i /f >nul 2>&1
)

REM Wait a moment for processes to terminate
timeout /t 2 >nul 2>&1

exit /b 0
