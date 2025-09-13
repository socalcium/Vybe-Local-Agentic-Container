@echo off
setlocal enabledelayedexpansion
REM Build Professional Vybe Installer
REM This script compiles the professional installer with all enhancements

TITLE Building Vybe Professional Installer

echo =====================================================
echo Building Vybe AI Assistant Professional Installer
echo =====================================================
echo.

REM Change to script directory
cd /d "%~dp0"

REM Check for Inno Setup
SET INNO_PATH=
SET INNO_FOUND=0

REM Check standard Inno Setup 6 locations
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    SET "INNO_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    SET INNO_FOUND=1
    goto :found_inno
)

if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    SET "INNO_PATH=C:\Program Files\Inno Setup 6\ISCC.exe"
    SET INNO_FOUND=1
    goto :found_inno
)

REM Check Inno Setup 5 as fallback
if exist "C:\Program Files (x86)\Inno Setup 5\ISCC.exe" (
    SET "INNO_PATH=C:\Program Files (x86)\Inno Setup 5\ISCC.exe"
    SET INNO_FOUND=1
    echo WARNING: Using Inno Setup 5 - some features may not work correctly
    goto :found_inno
)

if %INNO_FOUND%==0 (
    echo ERROR: Inno Setup not found!
    echo.
    echo Please install Inno Setup 6 from: https://jrsoftware.org/isdl.php
    echo.
    echo Checked locations:
    echo - C:\Program Files (x86)\Inno Setup 6\
    echo - C:\Program Files\Inno Setup 6\
    echo.
    pause
    exit /b 1
)

:found_inno
echo Found Inno Setup at: %INNO_PATH%
echo.

REM Create dist directory if it doesn't exist
if not exist "dist" (
    echo Creating dist directory...
    mkdir dist
)

REM Clean up old installers
echo Cleaning up old installers...
if exist "dist\Vybe_Setup_*.exe" (
    del /Q "dist\Vybe_Setup_*.exe" 2>nul
    echo Removed old installer files.
)

REM Check if required files exist
echo.
echo Checking required files...
SET MISSING_FILES=0

if not exist "Vybe_Setup_Professional.iss" (
    echo ERROR: Missing Vybe_Setup_Professional.iss
    SET MISSING_FILES=1
)

if not exist "assets\VybeLight.ico" (
    echo ERROR: Missing assets\VybeLight.ico
    SET MISSING_FILES=1
)

if not exist "installer_status_window.py" (
    echo ERROR: Missing installer_status_window.py
    SET MISSING_FILES=1
)

if not exist "LICENSE" (
    echo ERROR: Missing LICENSE file
    SET MISSING_FILES=1
)

if %MISSING_FILES%==1 (
    echo.
    echo Please ensure all required files are present before building.
    echo Current directory: %CD%
    echo.
    dir /B *.iss
    echo.
    pause
    exit /b 1
)

echo All required files found.
echo.

REM Build the professional installer
echo Building Professional Installer...
echo =====================================================
echo.
echo Running Inno Setup Compiler...
echo Command: "%INNO_PATH%" /O"dist" "Vybe_Setup_Professional.iss"
echo.

REM Run without /Q first to see full output
"%INNO_PATH%" /O"dist" "Vybe_Setup_Professional.iss"

SET BUILD_RESULT=%ERRORLEVEL%

if %BUILD_RESULT% NEQ 0 (
    echo.
    echo =====================================================
    echo ERROR: Failed to build installer!
    echo Error code: %BUILD_RESULT%
    echo.
    echo Common issues:
    echo - Check for syntax errors in Vybe_Setup_Professional.iss
    echo - Ensure all referenced files exist
    echo - Verify Inno Setup version compatibility
    echo.
    pause
    exit /b %BUILD_RESULT%
)

echo.
echo =====================================================
echo Professional installer built successfully!
echo =====================================================
echo.

REM Check if output file exists
if not exist "dist\Vybe_Setup_v0.8_Professional.exe" (
    echo WARNING: Expected output file not found!
    echo Looking for any generated installers...
    dir /B "dist\*.exe" 2>nul
    if %ERRORLEVEL% NEQ 0 (
        echo No installer files found in dist directory!
        pause
        exit /b 1
    )
) else (
    echo Output file: dist\Vybe_Setup_v0.8_Professional.exe
    
    REM Get file size
    for %%F in ("dist\Vybe_Setup_v0.8_Professional.exe") do (
        set /a size=%%~zF/1048576
        set /a remainder=%%~zF%%1048576/104858
        echo File size: !size!.!remainder! MB
    )
)

echo.
echo The professional installer includes:
echo - Silent installation without popup windows
echo - Real-time status window with progress tracking
echo - Comprehensive error handling and logging
echo - Automatic rollback for failed installations
echo - Copy-able error messages for support
echo - Professional UI and user experience
echo.

REM Optionally sign the installer if certificate is available
if exist "code_signing_cert.pfx" (
    echo Signing installer...
    if defined CERT_PASSWORD (
        signtool sign /f "code_signing_cert.pfx" /p "%CERT_PASSWORD%" /t http://timestamp.digicert.com /d "Vybe AI Assistant" "dist\Vybe_Setup_v0.8_Professional.exe"
        if !ERRORLEVEL! EQU 0 (
            echo Installer signed successfully!
        ) else (
            echo Warning: Failed to sign installer
        )
    ) else (
        echo Warning: CERT_PASSWORD not set, skipping signing
    )
    echo.
)

echo Build completed successfully!
echo.

REM Ask if user wants to test the installer
choice /C YN /T 10 /D N /M "Would you like to test the installer now"
if %ERRORLEVEL%==1 (
    echo.
    echo Launching installer...
    if exist "dist\Vybe_Setup_v0.8_Professional.exe" (
        start "" "dist\Vybe_Setup_v0.8_Professional.exe"
    ) else (
        REM Launch whatever installer we found
        for %%F in ("dist\Vybe_Setup_*.exe") do (
            echo Launching %%F...
            start "" "%%F"
            goto :end
        )
    )
)

:end
echo.
echo Done.
pause
