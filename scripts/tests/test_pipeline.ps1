# QiOS Pipeline Test Script
# Tests: Scanner → Queue → API Endpoints

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
Set-Location $RootDir

Write-Host "`n=== QiOS Pipeline Test ===" -ForegroundColor Cyan

# Test 1: Scanner
Write-Host "`n[TEST 1] Running FS Scanner (dry-run)..." -ForegroundColor Yellow
python tools\fs_scanner.py --dry-run | ConvertFrom-Json | Select-Object -First 5
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Scanner test failed" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Scanner test passed" -ForegroundColor Green

# Test 2: Queue Loader (dry-run)
Write-Host "`n[TEST 2] Testing Queue Loader (dry-run)..." -ForegroundColor Yellow
# First, run scanner to generate events
python tools\fs_scanner.py --manual-push 2>&1 | Out-Null
if (Test-Path "data\outputs\fs_scan_events.jsonl") {
    python tools\queue_loader.py --dry-run --limit 5 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Queue loader test failed" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Queue loader test passed" -ForegroundColor Green
    
    # Check if env vars are set for actual queue loading
    if (-not $env:SUPABASE_URL -or -not $env:SUPABASE_SERVICE_ROLE_KEY) {
        Write-Host "⚠️  Supabase env vars not set - queue loader will only work in dry-run mode" -ForegroundColor Yellow
        Write-Host "   Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY to test actual queue insertion" -ForegroundColor Gray
    }
} else {
    Write-Host "⚠️  No events file found, skipping queue loader test" -ForegroundColor Yellow
}

# Test 3: Check output files
Write-Host "`n[TEST 3] Checking output files..." -ForegroundColor Yellow
$snapshot = Test-Path "data\outputs\fs_scan_snapshot.json"
$events = Test-Path "data\outputs\fs_scan_events.jsonl"
if ($snapshot -and $events) {
    Write-Host "✅ Output files created" -ForegroundColor Green
    $snapshotSize = (Get-Item "data\outputs\fs_scan_snapshot.json").Length
    $eventsCount = (Get-Content "data\outputs\fs_scan_events.jsonl" | Measure-Object -Line).Lines
    Write-Host "   Snapshot: $snapshotSize bytes" -ForegroundColor Gray
    Write-Host "   Events: $eventsCount lines" -ForegroundColor Gray
} else {
    Write-Host "❌ Missing output files" -ForegroundColor Red
    exit 1
}

# Test 4: Check for UI endpoints (if orchestrator is running)
Write-Host "`n[TEST 4] Checking UI endpoint availability..." -ForegroundColor Yellow
$orchestratorRunning = $false
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8787/health" -TimeoutSec 2 -ErrorAction SilentlyContinue
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ Orchestrator is running" -ForegroundColor Green
        $orchestratorRunning = $true
    }
} catch {
    Write-Host "⚠️  Orchestrator not running (expected if not deployed)" -ForegroundColor Yellow
    Write-Host "   Start with: wrangler dev workers/orchestrator/worker_orchestrator.ts" -ForegroundColor Gray
}

if ($orchestratorRunning) {
    Write-Host "`nAvailable UI endpoints:" -ForegroundColor Cyan
    Write-Host "  GET /health - System health check" -ForegroundColor Gray
    Write-Host "  GET /queue - Ingestion queue status" -ForegroundColor Gray
    Write-Host "  GET /errors - Recent errors" -ForegroundColor Gray
    Write-Host "  GET /workers - Worker status" -ForegroundColor Gray
    Write-Host "  GET /file_history - File change history" -ForegroundColor Gray
}

Write-Host "`n=== All Tests Passed ===" -ForegroundColor Green

