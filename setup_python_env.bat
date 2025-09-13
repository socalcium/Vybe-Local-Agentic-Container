@echo off
echo Setting up Python environment for Vybe...

REM Try to find Python in various locations
set PYTHON_EXE=

REM Check if python is in PATH
python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set PYTHON_EXE=python
    goto :found_python
)

REM Check common installation locations
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe
    goto :found_python
)

if exist "%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe" (
    set PYTHON_EXE=%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe
    goto :found_python
)

if exist "%PROGRAMFILES%\Python311\python.exe" (
    set PYTHON_EXE=%PROGRAMFILES%\Python311\python.exe
    goto :found_python
)

if exist "%PROGRAMFILES(X86)%\Python311\python.exe" (
    set PYTHON_EXE=%PROGRAMFILES(X86)%\Python311\python.exe
    goto :found_python
)

if exist "C:\Python311\python.exe" (
    set PYTHON_EXE=C:\Python311\python.exe
    goto :found_python
)

echo ERROR: Could not find Python 3.11 installation!
echo Please make sure Python 3.11 is installed and try again.
exit /b 1

:found_python
echo Found Python: %PYTHON_EXE%
echo Running installer backend...
"%PYTHON_EXE%" installer_backend.py
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python environment setup failed!
    exit /b 1
)

echo Python environment setup completed successfully!
exit /b 0
