@echo off
echo ====================================
echo Vybe 1.0Test - Build Verification
echo ====================================
echo.

echo [1/6] Checking Python installation...
python --version
if %errorlevel% neq 0 (
    echo ERROR: Python not found!
    exit /b 1
)

echo [2/6] Checking virtual environment...
if exist "vybe-env-311" (
    echo Virtual environment found: vybe-env-311
) else (
    echo ERROR: Virtual environment not found!
    exit /b 1
)

echo [3/6] Checking core files...
if exist "vybe_app\__init__.py" (
    echo Core Flask app: OK
) else (
    echo ERROR: Core Flask app missing!
    exit /b 1
)

if exist "vybe_app\core\manager_model.py" (
    echo Manager Model: OK
) else (
    echo ERROR: Manager Model missing!
    exit /b 1
)

if exist "vybe_app\core\hardware_manager.py" (
    echo Hardware Manager: OK
) else (
    echo ERROR: Hardware Manager missing!
    exit /b 1
)

echo [4/6] Checking Tauri desktop...
if exist "vybe-desktop\src-tauri\Cargo.toml" (
    echo Tauri config: OK
) else (
    echo ERROR: Tauri config missing!
    exit /b 1
)

echo [5/6] Checking static assets...
if exist "vybe_app\static\js\modules\prompt-assistant.js" (
    echo Prompt Assistant JS: OK
) else (
    echo ERROR: Prompt Assistant JS missing!
    exit /b 1
)

if exist "vybe_app\static\css\prompt-assistant.css" (
    echo Prompt Assistant CSS: OK
) else (
    echo ERROR: Prompt Assistant CSS missing!
    exit /b 1
)

echo [6/6] Checking installer components...
if exist "installer_backend.py" (
    echo Installer backend: OK
) else (
    echo ERROR: Installer backend missing!
    exit /b 1
)

echo.
echo ====================================
echo All build verification checks PASSED!
echo Ready for 1.0Test deployment
echo ====================================

pause