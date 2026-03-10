# Tatiana OS Bridge Service Uninstallation Script
# This script completely removes the Tatiana OS Bridge service from the system

#Requires -RunAsAdministrator

<#
.SYNOPSIS
    Uninstalls the Tatiana OS Bridge Windows service using NSSM

.DESCRIPTION
    This script performs a complete uninstallation of the Tatiana OS Bridge service,
    including stopping the service, removing it with NSSM, and cleaning up related files.

.NOTES
    - Must be run as Administrator
    - Uses NSSM (Non-Sucking Service Manager) for service management
    - Includes safety checks and confirmation prompts
    - Handles errors gracefully with proper error messages

.EXAMPLE
    PS> .\uninstall_service.ps1
    Runs the uninstallation script with confirmation prompt

.EXAMPLE
    PS> .\uninstall_service.ps1 -Force
    Runs the uninstallation without confirmation prompt (use with caution)
#>

param(
    [switch]$Force
)

# Set strict error handling
$ErrorActionPreference = "Stop"
$WarningPreference = "Continue"

# ============================================================================
# CONFIGURATION VARIABLES
# ============================================================================

# Service configuration
$ServiceName = "TatianaOSBridge"
$ServiceDisplayName = "Tatiana OS Bridge Service"

# NSSM configuration - adjust these paths if NSSM is installed elsewhere
$NSSMPath = "C:\Program Files\NSSM\nssm.exe"
$AlternativeNSSMPaths = @(
    "C:\Windows\System32\nssm.exe",
    "C:\Windows\nssm.exe",
    ".\nssm.exe",
    "..\nssm.exe"
)

# Optional: Define paths for cleanup (commented out by default for safety)
# $ServiceExecutablePath = "C:\Program Files\TatianaOS\titan_backend.exe"
# $ServiceConfigPath = "C:\Program Files\TatianaOS\config"
# $ServiceLogPath = "C:\ProgramData\TatianaOS\logs"

# ============================================================================
# FUNCTIONS
# ============================================================================

function Write-Status {
    param(
        [string]$Message,
        [string]$Type = "Info",
        [switch]$NoNewline
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $prefix = switch ($Type) {
        "Success" { "[SUCCESS]" }
        "Warning" { "[WARNING]" }
        "Error" { "[ERROR]" }
        "Info" { "[INFO]" }
        default { "[INFO]" }
    }
    
    $color = switch ($Type) {
        "Success" { "Green" }
        "Warning" { "Yellow" }
        "Error" { "Red" }
        "Info" { "Cyan" }
        default { "White" }
    }
    
    Write-Host -NoNewline -ForegroundColor Gray "[$timestamp] "
    Write-Host -NoNewline -ForegroundColor $color $prefix
    Write-Host -NoNewline " "
    if ($NoNewline) {
        Write-Host -NoNewline $Message
    } else {
        Write-Host $Message
    }
}

function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Find-NSSM {
    Write-Status "Searching for NSSM executable..." -Type Info
    
    # Check primary path first
    if (Test-Path $NSSMPath) {
        Write-Status "Found NSSM at: $NSSMPath" -Type Success
        return $NSSMPath
    }
    
    # Check alternative paths
    foreach ($path in $AlternativeNSSMPaths) {
        if (Test-Path $path) {
            Write-Status "Found NSSM at: $path" -Type Success
            return $path
        }
    }
    
    # Try to find in PATH environment variable
    $nssmInPath = Get-Command "nssm.exe" -ErrorAction SilentlyContinue
    if ($nssmInPath) {
        Write-Status "Found NSSM in PATH: $($nssmInPath.Source)" -Type Success
        return $nssmInPath.Source
    }
    
    Write-Status "NSSM executable not found!" -Type Error
    Write-Status "Please install NSSM or update the script paths." -Type Warning
    Write-Status "Download NSSM from: https://nssm.cc/download" -Type Info
    
    return $null
}

function Test-ServiceExists {
    param([string]$Name)
    
    try {
        $service = Get-Service -Name $Name -ErrorAction SilentlyContinue
        return ($null -ne $service)
    } catch {
        return $false
    }
}

function Get-ServiceStatus {
    param([string]$Name)
    
    try {
        $service = Get-Service -Name $Name -ErrorAction SilentlyContinue
        if ($null -eq $service) {
            return "NotFound"
        }
        return $service.Status.ToString()
    } catch {
        return "Unknown"
    }
}

function Stop-ServiceSafely {
    param(
        [string]$Name,
        [int]$TimeoutSeconds = 30
    )
    
    Write-Status "Checking service status..." -Type Info
    $status = Get-ServiceStatus -Name $Name
    
    if ($status -eq "NotFound") {
        Write-Status "Service '$Name' not found - skipping stop operation" -Type Warning
        return $true
    }
    
    if ($status -eq "Stopped") {
        Write-Status "Service '$Name' is already stopped" -Type Success
        return $true
    }
    
    Write-Status "Stopping service '$Name' (timeout: ${TimeoutSeconds}s)..." -Type Info -NoNewline
    
    try {
        # Try graceful stop first
        Stop-Service -Name $Name -Force -ErrorAction Stop
        
        # Wait for service to stop
        $elapsed = 0
        while ((Get-ServiceStatus -Name $Name) -eq "Running" -and $elapsed -lt $TimeoutSeconds) {
            Start-Sleep -Seconds 1
            $elapsed++
            Write-Host -NoNewline "."
        }
        Write-Host "" # New line after dots
        
        $finalStatus = Get-ServiceStatus -Name $Name
        if ($finalStatus -eq "Stopped") {
            Write-Status "Service stopped successfully" -Type Success
            return $true
        } else {
            Write-Status "Service failed to stop within timeout period (status: $finalStatus)" -Type Error
            return $false
        }
    } catch {
        Write-Host "" # New line if error occurred
        Write-Status "Failed to stop service: $($_.Exception.Message)" -Type Error
        return $false
    }
}

function Remove-ServiceWithNSSM {
    param(
        [string]$NSSMPath,
        [string]$ServiceName
    )
    
    Write-Status "Removing service with NSSM..." -Type Info
    
    if (-not (Test-Path $NSSMPath)) {
        Write-Status "NSSM executable not found at: $NSSMPath" -Type Error
        return $false
    }
    
    try {
        # Use NSSM to remove the service with confirm flag to bypass GUI
        $processInfo = New-Object System.Diagnostics.ProcessStartInfo
        $processInfo.FileName = $NSSMPath
        $processInfo.Arguments = "remove $ServiceName confirm"
        $processInfo.RedirectStandardOutput = $true
        $processInfo.RedirectStandardError = $true
        $processInfo.UseShellExecute = $false
        $processInfo.CreateNoWindow = $true
        
        $process = New-Object System.Diagnostics.Process
        $process.StartInfo = $processInfo
        $process.Start() | Out-Null
        
        $stdout = $process.StandardOutput.ReadToEnd()
        $stderr = $process.StandardError.ReadToEnd()
        $process.WaitForExit()
        
        if ($process.ExitCode -eq 0) {
            Write-Status "Service removed successfully with NSSM" -Type Success
            if ($stdout) {
                Write-Status "NSSM Output: $stdout" -Type Info
            }
            return $true
        } else {
            Write-Status "NSSM failed to remove service (Exit Code: $($process.ExitCode))" -Type Error
            if ($stderr) {
                Write-Status "NSSM Error: $stderr" -Type Error
            }
            if ($stdout) {
                Write-Status "NSSM Output: $stdout" -Type Info
            }
            return $false
        }
    } catch {
        Write-Status "Exception occurred while removing service: $($_.Exception.Message)" -Type Error
        return $false
    }
}

function Show-UninstallationSummary {
    param(
        [bool]$Success,
        [string]$ServiceName
    )
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "UNINSTALLATION SUMMARY" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    
    if ($Success) {
        Write-Host "✓ Service uninstallation completed successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Service '$ServiceName' has been completely removed." -ForegroundColor White
    } else {
        Write-Host "✗ Service uninstallation failed!" -ForegroundColor Red
        Write-Host ""
        Write-Host "The service may still be installed or partially removed." -ForegroundColor Yellow
        Write-Host "Please check the error messages above and try again." -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "Additional cleanup steps (if needed):" -ForegroundColor Cyan
    Write-Host "- Remove service executable files manually" -ForegroundColor Gray
    Write-Host "- Clean up configuration files" -ForegroundColor Gray
    Write-Host "- Remove log files" -ForegroundColor Gray
    Write-Host "- Check Event Viewer for related entries" -ForegroundColor Gray
    Write-Host ""
    Write-Host "To verify service removal, run: Get-Service -Name '$ServiceName'" -ForegroundColor Gray
    Write-Host "========================================" -ForegroundColor Cyan
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

try {
    # Clear console and show header
    Clear-Host
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "TATIANA OS BRIDGE SERVICE UNINSTALLER" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    
    # Check for Administrator privileges
    Write-Status "Checking Administrator privileges..." -Type Info
    if (-not (Test-Administrator)) {
        Write-Status "This script requires Administrator privileges!" -Type Error
        Write-Status "Please right-click and select 'Run as Administrator'" -Type Warning
        exit 1
    }
    Write-Status "Administrator privileges confirmed" -Type Success
    
    # Show configuration summary
    Write-Host ""
    Write-Status "Configuration Summary:" -Type Info
    Write-Status "  Service Name: $ServiceName" -Type Info
    Write-Status "  Display Name: $ServiceDisplayName" -Type Info
    Write-Status "  NSSM Path: $NSSMPath" -Type Info
    Write-Host ""
    
    # Check if service exists
    Write-Status "Checking if service exists..." -Type Info
    $serviceExists = Test-ServiceExists -Name $ServiceName
    
    if (-not $serviceExists) {
        Write-Status "Service '$ServiceName' not found on this system" -Type Warning
        Write-Status "The service may have already been uninstalled" -Type Info
        
        # Ask if user wants to continue anyway
        if (-not $Force) {
            $continue = Read-Host "Continue with cleanup operations? (y/N)"
            if ($continue -ne 'y' -and $continue -ne 'Y') {
                Write-Status "Uninstallation cancelled by user" -Type Info
                exit 0
            }
        }
    } else {
        $status = Get-ServiceStatus -Name $ServiceName
        Write-Status "Service found with status: $status" -Type Success
    }
    
    # Safety confirmation prompt (unless -Force is used)
    if (-not $Force) {
        Write-Host ""
        Write-Host "WARNING: This will completely remove the Tatiana OS Bridge service!" -ForegroundColor Yellow
        Write-Host "This action cannot be undone." -ForegroundColor Yellow
        $confirm = Read-Host "Are you sure you want to continue? (yes/N)"
        
        if ($confirm -ne "yes") {
            Write-Status "Uninstallation cancelled by user" -Type Info
            exit 0
        }
    }
    
    Write-Host ""
    Write-Host "Starting uninstallation process..." -ForegroundColor Cyan
    Write-Host ""
    
    $uninstallationSuccess = $true
    
    # Find NSSM executable
    $foundNSSMPath = Find-NSSM
    if ($null -eq $foundNSSMPath) {
        Write-Status "Cannot proceed without NSSM. Please install NSSM first." -Type Error
        exit 1
    }
    
    # Stop the service if it exists and is running
    if ($serviceExists) {
        $stopResult = Stop-ServiceSafely -Name $ServiceName -TimeoutSeconds 30
        if (-not $stopResult) {
            Write-Status "Warning: Could not stop service gracefully" -Type Warning
            $uninstallationSuccess = $false
        }
    }
    
    # Remove the service using NSSM
    if ($serviceExists) {
        $removeResult = Remove-ServiceWithNSSM -NSSMPath $foundNSSMPath -ServiceName $ServiceName
        if (-not $removeResult) {
            $uninstallationSuccess = $false
        }
        
        # Verify removal
        Start-Sleep -Seconds 2
        $stillExists = Test-ServiceExists -Name $ServiceName
        if ($stillExists) {
            Write-Status "Service still exists after removal attempt!" -Type Error
            $uninstallationSuccess = $false
        } else {
            Write-Status "Service verification: Successfully removed" -Type Success
        }
    }
    
    # Optional cleanup section (commented out by default for safety)
    <#
    Write-Host ""
    Write-Status "Performing additional cleanup..." -Type Info
    
    # Remove service executable if it exists
    if (Test-Path $ServiceExecutablePath) {
        try {
            Remove-Item -Path $ServiceExecutablePath -Force -ErrorAction Stop
            Write-Status "Removed service executable: $ServiceExecutablePath" -Type Success
        } catch {
            Write-Status "Could not remove executable: $($_.Exception.Message)" -Type Warning
        }
    }
    
    # Remove configuration directory
    if (Test-Path $ServiceConfigPath) {
        try {
            Remove-Item -Path $ServiceConfigPath -Recurse -Force -ErrorAction Stop
            Write-Status "Removed configuration directory: $ServiceConfigPath" -Type Success
        } catch {
            Write-Status "Could not remove config directory: $($_.Exception.Message)" -Type Warning
        }
    }
    
    # Remove log files
    if (Test-Path $ServiceLogPath) {
        try {
            Remove-Item -Path $ServiceLogPath -Recurse -Force -ErrorAction Stop
            Write-Status "Removed log files: $ServiceLogPath" -Type Success
        } catch {
            Write-Status "Could not remove log files: $($_.Exception.Message)" -Type Warning
        }
    }
    #>
    
    # Show final summary
    Show-UninstallationSummary -Success $uninstallationSuccess -ServiceName $ServiceName
    
    if ($uninstallationSuccess) {
        exit 0
    } else {
        exit 1
    }
    
} catch {
    Write-Status "Fatal error occurred: $($_.Exception.Message)" -Type Error
    Write-Status "Stack trace: $($_.ScriptStackTrace)" -Type Error
    exit 1
}