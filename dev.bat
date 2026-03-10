@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo   TitanU OS - Production Build
echo ==========================================
echo.

set "PROJECT_ROOT=%~dp0.."
set "VENV_PATH=%PROJECT_ROOT%\venv"
set "ELECTRON_DIR=%PROJECT_ROOT%\titanu-os\frontend\electron"
set "BACKEND_DIR=%PROJECT_ROOT%\titanu-os\backend"
set "TOOLS_DIR=%PROJECT_ROOT%\tools"

:: Use portable Node if available
if exist "%TOOLS_DIR%\node\node.exe" (
    echo [OK] Using portable Node.js
    set "PATH=%TOOLS_DIR%\node;%PATH%"
) else (
    echo [INFO] Using system Node.js
)

:: Activate venv
if exist "%VENV_PATH%\Scripts\activate.bat" (
    echo [OK] Activating Python virtual environment
    call "%VENV_PATH%\Scripts\activate.bat"
) else (
    echo [WARN] Python venv not found at %VENV_PATH%
    echo        Backend packaging may fail
)

echo.
echo Starting production build process...
echo.

:: Step 1: Build Python backend
echo [1/3] Building Python backend with PyInstaller...
echo ------------------------------------------------
cd /d "%BACKEND_DIR%"

:: Check if pyinstaller is installed
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo       Installing PyInstaller...
    pip install pyinstaller
)

:: Create dist directory if it doesn't exist
if not exist "dist" mkdir dist

:: Build backend executable
echo       Packaging backend into single executable...
pyinstaller --onefile --name titan_backend --distpath dist --specpath dist core/main.py --clean

if errorlevel 1 (
    echo [ERROR] Backend build failed
    pause
    exit /b 1
)
echo [OK] Backend built: %BACKEND_DIR%\dist\titan_backend.exe

:: Step 2: Build frontend with Vite
echo.
echo [2/3] Building frontend with Vite...
echo ------------------------------------
cd /d "%ELECTRON_DIR%"

:: Check if node_modules exists
if not exist "node_modules" (
    echo       Installing dependencies first...
    npx pnpm install
)

:: Run Vite build
echo       Running Vite production build...
npx vite build

if errorlevel 1 (
    echo [ERROR] Frontend build failed
    pause
    exit /b 1
)
echo [OK] Frontend built: %ELECTRON_DIR%\dist\

:: Step 3: Package with electron-builder
echo.
echo [3/3] Packaging with electron-builder...
echo ----------------------------------------
echo       Creating Windows distributable...
npx electron-builder --win --config.compression=normal

if errorlevel 1 (
    echo [ERROR] Electron packaging failed
    pause
    exit /b 1
)

echo.
echo ==========================================
echo   Build Complete!
echo ==========================================
echo.
echo Output locations:
echo   Backend executable: %BACKEND_DIR%\dist\titan_backend.exe
echo   Frontend build:     %ELECTRON_DIR%\dist\
echo   Electron package:   %ELECTRON_DIR%\dist-electron\
echo.
echo The packaged application is ready for distribution.
echo.
pause