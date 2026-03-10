@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo   TitanU OS - Development Environment Setup
echo ==========================================
echo.

set "PROJECT_ROOT=%~dp0.."
set "TOOLS_DIR=%PROJECT_ROOT%\tools"
set "ELECTRON_DIR=%PROJECT_ROOT%\titanu-os\frontend\electron"

:: Create tools directory
if not exist "%TOOLS_DIR%" mkdir "%TOOLS_DIR%"
if not exist "%TOOLS_DIR%\node" mkdir "%TOOLS_DIR%\node"

echo.
echo This script will set up a portable development environment.
echo No global npm/node installation required!
echo.
echo Steps:
echo   1. Download portable Node.js (if not present)
echo   2. Install pnpm locally
echo   3. Install project dependencies
echo.
pause

:: Download Node.js portable (using PowerShell)
echo.
echo [1/3] Checking Node.js...
if not exist "%TOOLS_DIR%\node\node.exe" (
    echo       Downloading Node.js v20.10.0 portable...
    powershell -Command "& { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://nodejs.org/dist/v20.10.0/node-v20.10.0-win-x64.zip' -OutFile '%TOOLS_DIR%\node.zip' }"
    
    if not exist "%TOOLS_DIR%\node.zip" (
        echo [ERROR] Failed to download Node.js. Check your internet connection.
        pause
        exit /b 1
    )
    
    echo       Extracting Node.js...
    powershell -Command "& { Expand-Archive -Path '%TOOLS_DIR%\node.zip' -DestinationPath '%TOOLS_DIR%' -Force }"
    
    :: Move files from nested directory
    xcopy "%TOOLS_DIR%\node-v20.10.0-win-x64\*" "%TOOLS_DIR%\node\" /E /Y /Q
    rmdir /S /Q "%TOOLS_DIR%\node-v20.10.0-win-x64"
    del "%TOOLS_DIR%\node.zip"
    
    echo [OK] Node.js installed to tools\node\
) else (
    echo [OK] Node.js already present
)

:: Add to PATH for this session
set "PATH=%TOOLS_DIR%\node;%PATH%"

:: Verify node works
echo.
echo       Verifying Node.js installation...
"%TOOLS_DIR%\node\node.exe" --version
if errorlevel 1 (
    echo [ERROR] Node.js verification failed
    pause
    exit /b 1
)

:: Install pnpm via corepack
echo.
echo [2/3] Setting up pnpm...
"%TOOLS_DIR%\node\npx.cmd" corepack enable
"%TOOLS_DIR%\node\npx.cmd" corepack prepare pnpm@latest --activate
echo [OK] pnpm activated via corepack

:: Install project dependencies
echo.
echo [3/3] Installing project dependencies...
cd /d "%ELECTRON_DIR%"

if exist "node_modules" (
    echo       Removing existing node_modules...
    rmdir /S /Q node_modules
)

echo       Running pnpm install...
"%TOOLS_DIR%\node\npx.cmd" pnpm install

if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo ==========================================
echo   Setup Complete!
echo ==========================================
echo.
echo Your portable development environment is ready.
echo.
echo To start development, run:
echo   scripts\dev.bat    (Command Prompt)
echo   scripts\dev.ps1    (PowerShell)
echo.
echo Node.js location: %TOOLS_DIR%\node\
echo Project dependencies: %ELECTRON_DIR%\node_modules\
echo.
pause