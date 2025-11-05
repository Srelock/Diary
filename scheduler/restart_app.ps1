# ========================================
# Restart Building Management Diary App
# ========================================
# PowerShell script to restart the Flask app
# More robust than batch script - recommended for Task Scheduler
# 
# Usage: .\restart_app.ps1

# Get the script directory and project root
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Split-Path -Parent $scriptDir
$appPath = Join-Path $projectDir "app.py"
$logFile = Join-Path $scriptDir "restart_log.txt"

# Change to project directory
Set-Location $projectDir

# Function to write log
function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] $Message"
    Add-Content -Path $logFile -Value $logMessage
    Write-Host $logMessage
}

# Function to find processes running app.py
function Get-AppProcesses {
    $processes = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -like "*app.py*" -or
        (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine -like "*app.py*"
    }
    return $processes
}

Write-Log "=== Restart script executed ==="

# Find and stop existing app processes
Write-Log "Searching for running app instances..."
$runningProcesses = Get-AppProcesses

if ($runningProcesses) {
    foreach ($proc in $runningProcesses) {
        try {
            $commandLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($proc.Id)").CommandLine
            if ($commandLine -like "*app.py*") {
                Write-Log "Stopping process PID: $($proc.Id)"
                Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
                Start-Sleep -Seconds 1
                Write-Log "Process PID: $($proc.Id) stopped"
            }
        } catch {
            Write-Log "Error stopping process PID: $($proc.Id) - $_"
        }
    }
} else {
    Write-Log "No running app instances found"
}

# Wait for processes to fully terminate
Write-Log "Waiting for processes to terminate..."
Start-Sleep -Seconds 3

# Verify all processes are stopped
$remainingProcesses = Get-AppProcesses
if ($remainingProcesses) {
    Write-Log "WARNING: Some processes may still be running, attempting force stop..."
    $remainingProcesses | ForEach-Object {
        try {
            Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
        } catch {}
    }
    Start-Sleep -Seconds 2
}

# Start the app
Write-Log "Starting new app instance..."
try {
    $processInfo = New-Object System.Diagnostics.ProcessStartInfo
    $processInfo.FileName = "python"
    $processInfo.Arguments = "`"$appPath`""
    $processInfo.WorkingDirectory = $projectDir
    $processInfo.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Minimized
    $processInfo.UseShellExecute = $true
    
    $process = [System.Diagnostics.Process]::Start($processInfo)
    
    Write-Log "App started with PID: $($process.Id)"
    
    # Wait and verify
    Start-Sleep -Seconds 3
    
    $checkProcess = Get-Process -Id $process.Id -ErrorAction SilentlyContinue
    if ($checkProcess) {
        Write-Log "App restart completed successfully (PID: $($process.Id))"
        exit 0
    } else {
        Write-Log "ERROR: App process terminated unexpectedly"
        exit 1
    }
} catch {
    Write-Log "ERROR: Failed to start app - $_"
    exit 1
}

