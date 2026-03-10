# Tatiana OS Bridge - Uninstall Script
# Requires Administrator

$ServiceName = "TatianaOSBridge"
$NSSM = "C:\Tatiana-OS-Bridge\bin\nssm.exe" # Match the path in the install script

Write-Host "Stopping and removing Tatiana OS Bridge service..."

if (Get-Service $ServiceName -ErrorAction SilentlyContinue) {
    Stop-Service $ServiceName -Force
    # NSSM remove requires 'confirm' to bypass the prompt
    & $NSSM remove $ServiceName confirm

    Write-Host "Tatiana OS Bridge removed."
} else {
    Write-Host "Service not found."
}
