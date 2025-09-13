@echo off
title Vybe AI Assistant Shutdown
echo Stopping Vybe AI Assistant...
echo.

REM Stop Python processes running from this installation
echo Stopping Python processes...
for /f "tokens=2" %%i in ('tasklist /fi "imagename eq python.exe" /fo table /nh 2^>nul') do (
    taskkill /pid %%i /f >nul 2>&1
)

REM Note: llama-cpp-python backend runs as part of Vybe process
echo LLM backend will shut down with Vybe Python processes above.

REM Kill any browser processes that might be running Vybe
echo Stopping browser instances...
for /f "tokens=2" %%i in ('tasklist /fi "windowtitle eq*Vybe*" /fo table /nh 2^>nul') do (
    taskkill /pid %%i /f >nul 2>&1
)

echo.
echo Vybe AI Assistant has been stopped.
timeout /t 3 /nobreak >nul
