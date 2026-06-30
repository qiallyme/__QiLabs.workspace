# Install QiOS Scanner as Windows Scheduled Task
# Run as Administrator

$ErrorActionPreference = "Stop"

$TaskName = "QiOS-Daily-Scanner"
$TaskPath = "$PSScriptRoot\windows_task_scheduler.xml"
$ScriptPath = "$PSScriptRoot\scanner_scheduler.ps1"

Write-Host "Installing QiOS Daily Scanner Task..." -ForegroundColor Cyan

# Check if running as admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

# Update XML with actual script path
$xml = [xml](Get-Content $TaskPath)
$xml.Task.Actions.Exec.Arguments = "-ExecutionPolicy Bypass -File `"$ScriptPath`""
$xml.Task.Actions.Exec.WorkingDirectory = (Split-Path -Parent $PSScriptRoot)
$xml.Save($TaskPath)

# Remove existing task if it exists
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Removing existing task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Register the task
Write-Host "Registering scheduled task..." -ForegroundColor Yellow
Register-ScheduledTask -TaskName $TaskName -Xml (Get-Content $TaskPath -Raw) -Force | Out-Null

Write-Host "`n✅ Scheduled task installed successfully!" -ForegroundColor Green
Write-Host "   Task Name: $TaskName" -ForegroundColor Gray
Write-Host "   Schedule: Daily at 2:00 AM" -ForegroundColor Gray
Write-Host "`nTo test immediately, run:" -ForegroundColor Yellow
Write-Host "   Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Cyan
Write-Host "`nTo view task:" -ForegroundColor Yellow
Write-Host "   Get-ScheduledTask -TaskName '$TaskName' | Get-ScheduledTaskInfo" -ForegroundColor Cyan

