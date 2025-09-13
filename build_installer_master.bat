@echo off
setlocal enabledelayedexpansion

echo ======================================================
echo   VYBE AI ASSISTANT 0.8 ALPHA - INSTALLER BUILD
echo ======================================================
echo.

REM Set build timestamp
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c-%%a-%%b)
for /f "tokens=1-2 delims=/:" %%a in ('time /t') do (set mytime=%%a%%b)
set timestamp=%mydate%_%mytime%

echo [1/6] Checking prerequisites...

REM Check if Inno Setup is installed
where iscc.exe >nul 2>&1
if errorlevel 1 (
    echo ERROR: Inno Setup Compiler (iscc.exe) not found!
    echo Please install Inno Setup from: https://jrsoftware.org/isinfo.php
    pause
    exit /b 1
)
echo   - Inno Setup Compiler: FOUND

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found! Please install Python 3.11+
    pause
    exit /b 1
)
echo   - Python: FOUND

echo.
echo [2/6] Creating build directories...

REM Create dist directory if it doesn't exist
if not exist "dist" (mkdir dist)
if not exist "temp" (mkdir temp)

echo   - Build directories created

echo.
echo [3/6] Running pre-build verification...

REM Run the verification script
python validate_build.py >nul 2>nul
if errorlevel 1 (
    echo WARNING: Build verification had issues. Continue anyway? (Y/N)
    set /p continue=
    if /i not "!continue!"=="y" exit /b 1
)

python pre_deploy_fixes.py
if errorlevel 1 (
    echo WARNING: Pre-deployment checks found issues. Review above and press any key to continue...
    pause
)

echo.
echo [4/6] Generating installer manifest...

python generate_installer_manifest.py
if errorlevel 1 (
    echo ERROR: Failed to generate installer manifest
    pause
    exit /b 1
)

echo.
echo [5/6] Building installer with Inno Setup...

REM Backup any existing installer
if exist "dist\Vybe_Setup_Master.exe" (
    echo   - Backing up previous installer...
    move "dist\Vybe_Setup_Master.exe" "dist\Vybe_Setup_Master_backup_%timestamp%.exe" >nul 2>nul
)

REM Compile the installer
iscc.exe "Vybe_Setup_Master.iss"
if errorlevel 1 (
    echo ERROR: Installer compilation failed!
    echo Check the Inno Setup output above for details.
    pause
    exit /b 1
)

echo   - Installer compiled successfully!

echo.
echo [6/6] Verifying installer...

if exist "dist\Vybe_Setup_Master.exe" (
    for %%A in ("dist\Vybe_Setup_Master.exe") do set size=%%~zA
    set /a sizeMB=!size!/1048576
    echo   - Installer size: !sizeMB! MB
    echo   - Location: %CD%\dist\Vybe_Setup_Master.exe
) else (
    echo ERROR: Installer file not found!
    pause
    exit /b 1
)

echo.
echo ======================================================
echo   BUILD COMPLETED SUCCESSFULLY!
echo ======================================================
echo.
echo   Installer: dist\Vybe_Setup_Master.exe
echo   Manifest:  installer_manifest.json
echo   Build Log: Available in Inno Setup output
echo.
echo   Next Steps:
echo   1. Test the installer on a clean system
echo   2. Verify all components install correctly
echo   3. Test the application functionality
echo.
echo ======================================================

REM Optionally open the dist folder
set /p open="Open installer folder? (Y/N): "
if /i "%open%"=="y" explorer dist

echo.
echo Build process complete! Press any key to exit...
pause >nul