# TitanU OS v3.0 Genesis - Developer Mode (PowerShell)
$ErrorActionPreference = "Stop"

Write-Host "========================================"
Write-Host "  TitanU OS v3.0 Genesis - Developer Mode"
Write-Host "========================================"
Write-Host ""

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VenvPath = Join-Path $ProjectRoot "venv"
$ElectronDir = Join-Path $ProjectRoot "titanu-os\frontend\electron"
$ToolsDir = Join-Path $ProjectRoot "tools"

# Check for portable Node
$PortableNode = Join-Path $ToolsDir "node\node.exe"
if (Test-Path $PortableNode) {
    Write-Host "[OK] Using portable Node.js" -ForegroundColor Green
    $env:PATH = "$(Join-Path $ToolsDir 'node');$env:PATH"
}

# Activate venv
$ActivateScript = Join-Path $VenvPath "Scripts\Activate.ps1"
if (Test-Path $ActivateScript) {
    Write-Host "[OK] Activating Python virtual environment" -ForegroundColor Green
    & $ActivateScript
} else {
    Write-Host "[WARN] Python venv not found at $VenvPath" -ForegroundColor Yellow
}

# Check for pnpm
$pnpmAvailable = $null -ne (Get-Command pnpm -ErrorAction SilentlyContinue)
if ($pnpmAvailable) {
    Write-Host "[OK] Using pnpm" -ForegroundColor Green
    $PkgManager = "pnpm"
} else {
    Write-Host "[INFO] pnpm not found, using npx" -ForegroundColor Cyan
    $PkgManager = "npx"
}

# Change to electron directory
Set-Location $ElectronDir

# Install dependencies if needed
if (-not (Test-Path "node_modules")) {
    Write-Host "[INFO] Installing dependencies..." -ForegroundColor Yellow
    if ($PkgManager -eq "pnpm") {
        pnpm install
    } else {
        npx pnpm install
    }
}

# Launch development environment
Write-Host ""
Write-Host "[START] Launching TitanU OS in development mode..." -ForegroundColor Cyan
Write-Host "        Backend: Python FastAPI on port 8765" -ForegroundColor Gray
Write-Host "        Frontend: Vite on port 5173" -ForegroundColor Gray
Write-Host "        Electron: Will launch when Vite is ready" -ForegroundColor Gray
Write-Host ""

# Use concurrently via npx to avoid npm issues
npx concurrently -n "vite,electron" -c "cyan,yellow" "npx vite" "npx wait-on http://localhost:5173 && npx electron ."