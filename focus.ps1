@echo off
setlocal

:: Title
title TitanU OS Dev Launcher

:: Paths
set "PROJECT_ROOT=%~dp0.."
set "BACKEND_DIR=%PROJECT_ROOT%\titanu-os\backend"
set "FRONTEND_DIR=%PROJECT_ROOT%\titanu-os\frontend\electron"

echo [TitanU OS] Launching Developer Mode...

:: 1. Check/Install Backend Environment
echo [Backend] Checking environment...
if not exist "%BACKEND_DIR%\venv" (
    echo [Backend] Creating virtual environment...
    cd /d "%BACKEND_DIR%"
    python -m venv venv
    call venv\Scripts\activate
    echo [Backend] Installing dependencies...
    pip install -r requirements.txt
    pip install uvicorn fastapi
) else (
    echo [Backend] Virtual environment found.
)

:: 2. Start Backend Server
:: echo [Backend] Starting Uvicorn server...
:: start "TitanU Backend" cmd /k "cd /d %BACKEND_DIR% && venv\Scripts\activate && python -m uvicorn core.main:app --reload --host 127.0.0.1 --port 8000"


:: 3. Check/Install Frontend Dependencies
echo [Frontend] Checking environment...
if not exist "%FRONTEND_DIR%\node_modules" (
    echo [Frontend] Installing dependencies...
    cd /d "%FRONTEND_DIR%"
    call npm install
)

:: 4. Start Frontend
echo [Frontend] Starting Electron Dev...
cd /d "%FRONTEND_DIR%"
start "TitanU Frontend" cmd /k "npm run dev"

echo [TitanU OS] Launch initiated!
echo Check the separate terminal windows for logs.
pause
