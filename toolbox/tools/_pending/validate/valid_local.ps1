# Local Environment Validation Script
# Validates Python FastAPI setup, health, status, and logs

$ErrorActionPreference = "Continue"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "QiMemory Local Environment Validation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Set UTF-8 console encoding
try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $env:PYTHONIOENCODING = "utf-8"
    Write-Host "OK UTF-8 console encoding set" -ForegroundColor Green
} catch {
    Write-Host "WARN Could not set UTF-8 encoding: $_" -ForegroundColor Yellow
}

# Get script directory and repo root
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir

# Check Python version
Write-Host "`n[1/5] Checking Python..." -ForegroundColor Cyan
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCmd) {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match "Python 3") {
        Write-Host "  OK $pythonVersion" -ForegroundColor Green
    } else {
        Write-Host "  WARN $pythonVersion (expected 3.10+)" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ERROR Python not found. Install from https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}

# Check uvicorn
Write-Host "`n[2/5] Checking uvicorn..." -ForegroundColor Cyan
$uvicornCheck = python -c "import uvicorn; print(uvicorn.__version__)" 2>&1
if ($LASTEXITCODE -eq 0 -and $uvicornCheck) {
    Write-Host "  OK uvicorn $uvicornCheck" -ForegroundColor Green
} else {
    Write-Host "  WARN uvicorn not installed. Run: pip install uvicorn" -ForegroundColor Yellow
}

# Check if FastAPI server is running
Write-Host "`n[3/5] Checking FastAPI server..." -ForegroundColor Cyan
# Default port is 8010, but check PORT env var or try both common ports
$apiPort = if ($env:PORT) { [int]$env:PORT } else { 8010 }
$apiUrl = "http://127.0.0.1:$apiPort"

try {
    $healthResponse = Invoke-WebRequest -Uri "$apiUrl/health" -Method GET -TimeoutSec 2 -ErrorAction Stop
    if ($healthResponse.StatusCode -eq 200) {
        Write-Host "  OK Server is running on port $apiPort" -ForegroundColor Green
    }
} catch {
    Write-Host "  WARN Server not running. Starting server..." -ForegroundColor Yellow
    
    # Activate venv if it exists
    $venvPath = Join-Path $repoRoot ".venv"
    if (Test-Path $venvPath) {
        & (Join-Path $venvPath "Scripts\Activate.ps1")
        Write-Host "  OK Activated virtual environment" -ForegroundColor Green
    }
    
    # Start server in background
    $apiScript = Join-Path $repoRoot "local\5_rag\qi_rag_api_supabase.py"
    if (Test-Path $apiScript) {
        Write-Host "  Starting server at $apiUrl (this may take a few seconds)..." -ForegroundColor Yellow
        Start-Process python -ArgumentList $apiScript -WindowStyle Hidden
        
        # Wait for server to start
        $maxWait = 10
        $waited = 0
        $serverReady = $false
        while ($waited -lt $maxWait) {
            Start-Sleep -Seconds 1
            $waited++
            try {
                $testResponse = Invoke-WebRequest -Uri "$apiUrl/health" -Method GET -TimeoutSec 1 -ErrorAction Stop
                if ($testResponse.StatusCode -eq 200) {
                    $serverReady = $true
                    break
                }
            } catch {
                continue
            }
        }
        
        if ($serverReady) {
            Write-Host "  OK Server started successfully" -ForegroundColor Green
        } else {
            Write-Host "  ERROR Server did not start within $maxWait seconds" -ForegroundColor Red
            Write-Host "    Run manually: python local\5_rag\qi_rag_api_supabase.py" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  ERROR API script not found: $apiScript" -ForegroundColor Red
    }
}

# Test /health endpoint
Write-Host "`n[4/5] Testing /health endpoint..." -ForegroundColor Cyan
try {
    $healthResponse = Invoke-RestMethod -Uri "$apiUrl/health" -Method GET -TimeoutSec 5
    if ($healthResponse.ok -eq $true) {
        Write-Host "  OK Health check passed" -ForegroundColor Green
    } else {
        Write-Host "  ERROR Health check failed: $healthResponse" -ForegroundColor Red
    }
} catch {
    Write-Host "  ERROR Health check failed: $_" -ForegroundColor Red
    Write-Host "    Ensure server is running: python local\5_rag\qi_rag_api_supabase.py" -ForegroundColor Yellow
}

# Test /status endpoint
Write-Host "`n[5/5] Testing /status endpoint..." -ForegroundColor Cyan
try {
    $statusResponse = Invoke-RestMethod -Uri "$apiUrl/status" -Method GET -TimeoutSec 10
    Write-Host "  OK Status endpoint accessible" -ForegroundColor Green
    
    # Display status summary
    Write-Host "`n  Status Summary:" -ForegroundColor Cyan
    if ($statusResponse.kb) {
        $kb = $statusResponse.kb
        Write-Host "    KB Embeddings: $($kb.embeddings_rows)" -ForegroundColor White
        Write-Host "    KB Files: $($kb.files_indexed)" -ForegroundColor White
        Write-Host "    KB Errors (24h): $($kb.recent_errors_24h)" -ForegroundColor $(if ($kb.recent_errors_24h -gt 0) { "Yellow" } else { "White" })
    }
    if ($statusResponse.watcher) {
        $watcher = $statusResponse.watcher
        $watcherStatus = if ($watcher.running) { "Running" } else { "Stopped" }
        $watcherColor = if ($watcher.running) { "Green" } else { "Yellow" }
        Write-Host "    Watcher: $watcherStatus (Queue: $($watcher.queue_len))" -ForegroundColor $watcherColor
    }
} catch {
    Write-Host "  ERROR Status check failed: $_" -ForegroundColor Red
    Write-Host "    This may indicate missing Supabase credentials or connectivity issues" -ForegroundColor Yellow
}

# Show recent logs
Write-Host "`n[6/6] Recent ingest logs (last 100 lines)..." -ForegroundColor Cyan
$logFile = Join-Path $repoRoot "local\meta\ingest.log"
if (Test-Path $logFile) {
    Write-Host "  Log file: $logFile" -ForegroundColor White
    try {
        $logLines = Get-Content $logFile -Tail 100 -ErrorAction Stop
        Write-Host "  Last 10 lines:" -ForegroundColor Cyan
        $logLines[-10..-1] | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
    } catch {
        Write-Host "  WARN Could not read log file: $_" -ForegroundColor Yellow
    }
} else {
    Write-Host "  WARN Log file not found: $logFile" -ForegroundColor Yellow
    Write-Host "    This is normal if no ingestion has run yet" -ForegroundColor Gray
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Validation Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

