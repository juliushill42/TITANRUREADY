# Tatiana OS Bridge - Install Script
# Requires Administrator

$ServiceName = "TatianaOSBridge"
$BaseDir = "C:\Tatiana-OS-Bridge"
$ExePath = "$BaseDir\bin\tatiana_os_bridge.exe"
$NSSM = "$BaseDir\bin\nssm.exe" # Assuming nssm.exe is inside the bin folder

if (!(Test-Path $ExePath)) {
    Write-Error "Executable not found: $ExePath. Please ensure it is in the bin folder."
    exit 1
}

# --- Create Base and Log Directories ---
New-Item -ItemType Directory -Force -Path $BaseDir | Out-Null
New-Item -ItemType Directory -Force -Path "$BaseDir\logs" | Out-Null

# --- Install and Configure service using NSSM ---
# This registers the service with Windows
& $NSSM install $ServiceName $ExePath

# Set service parameters (CWD, logging, environment)
& $NSSM set $ServiceName AppDirectory $BaseDir
& $NSSM set $ServiceName AppStdout "$BaseDir\logs\stdout.log"
& $NSSM set $ServiceName AppStderr "$BaseDir\logs\stderr.log"

# IMPORTANT: These environment variables tell the bridge where to find the existing Tatiana backend
& $NSSM set $ServiceName AppEnvironmentExtra `"TATIANA_HOST=127.0.0.1"` `"TATIANA_PORT=7878"`

# Set restart policy (Starts automatically on boot, restarts after 5 seconds if it fails)
& $NSSM set $ServiceName Start SERVICE_AUTO_START
& $NSSM set $ServiceName AppRestartDelay 5000 

Start-Service $ServiceName
Write-Host "Tatiana OS Bridge installed and started."
