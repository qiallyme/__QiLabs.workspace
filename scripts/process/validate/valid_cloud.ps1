# Cloudflare Worker Validation Script
# Validates Worker secrets, dev server, and endpoints

$ErrorActionPreference = "Continue"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "QiMemory Cloud Environment Validation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Get script directory and repo root
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
$workerDir = Join-Path $repoRoot "cloud\worker"

if (-not (Test-Path $workerDir)) {
    Write-Host "ERROR Worker directory not found: $workerDir" -ForegroundColor Red
    exit 1
}

Set-Location $workerDir

# Check wrangler
Write-Host "[1/4] Checking wrangler..." -ForegroundColor Cyan
try {
    $wranglerVersion = wrangler --version 2>&1
    Write-Host "  OK $wranglerVersion" -ForegroundColor Green
} catch {
    Write-Host "  ERROR wrangler not found. Install: npm install -g wrangler" -ForegroundColor Red
    Write-Host "    Or use: npx wrangler --version" -ForegroundColor Yellow
    exit 1
}

# Check secrets
Write-Host "`n[2/4] Checking Worker secrets..." -ForegroundColor Cyan
try {
    $secrets = wrangler secret list 2>&1
    if ($LASTEXITCODE -eq 0) {
        $requiredSecrets = @("OPENAI_API_KEY", "SUPABASE_URL", "SUPABASE_ANON_KEY")
        $foundSecrets = @()
        
        foreach ($line in $secrets) {
            foreach ($req in $requiredSecrets) {
                if ($line -match $req) {
                    $foundSecrets += $req
                    break
                }
            }
        }
        
        Write-Host "  Found secrets:" -ForegroundColor White
        foreach ($req in $requiredSecrets) {
            if ($foundSecrets -contains $req) {
                Write-Host "    OK $req" -ForegroundColor Green
            } else {
                Write-Host "    ERROR $req (missing)" -ForegroundColor Red
            }
        }
        
        # Check optional CHAT_MODEL
        $hasChatModel = $secrets -match "CHAT_MODEL"
        if ($hasChatModel) {
            Write-Host "    OK CHAT_MODEL (optional)" -ForegroundColor Green
        } else {
            Write-Host "    WARN CHAT_MODEL (optional, not set)" -ForegroundColor Yellow
        }
        
        if ($foundSecrets.Count -lt $requiredSecrets.Count) {
            Write-Host "`n  WARN Some required secrets are missing!" -ForegroundColor Yellow
            Write-Host "    Run: wrangler secret put SECRET_NAME" -ForegroundColor Yellow
            Write-Host "    Or use: .\sync-secrets.ps1" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  WARN Could not list secrets: $secrets" -ForegroundColor Yellow
        Write-Host "    Ensure you're logged in: wrangler login" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  WARN Could not check secrets: $_" -ForegroundColor Yellow
    Write-Host "    Ensure you're logged in: wrangler login" -ForegroundColor Yellow
}

# Start dev server and test
Write-Host "`n[3/4] Testing dev server..." -ForegroundColor Cyan
Write-Host "  Starting wrangler dev (this may take a moment)..." -ForegroundColor Yellow

try {
    # Start wrangler dev in background
    $devProcess = Start-Process wrangler -ArgumentList "dev","--local","--port","8787" -PassThru -WindowStyle Hidden
    
    # Wait for server to start
    $maxWait = 15
    $waited = 0
    $serverReady = $false
    $devUrl = "http://127.0.0.1:8787"
    
    Write-Host "  Waiting for server to start..." -ForegroundColor Yellow
    while ($waited -lt $maxWait) {
        Start-Sleep -Seconds 1
        $waited++
        try {
            $testResponse = Invoke-WebRequest -Uri "$devUrl/health" -Method GET -TimeoutSec 1 -ErrorAction Stop
            if ($testResponse.StatusCode -eq 200) {
                $serverReady = $true
                break
            }
        } catch {
            continue
        }
    }
    
    if ($serverReady) {
        Write-Host "  OK Dev server started" -ForegroundColor Green
        
        # Test /health
        Write-Host "`n  Testing /health..." -ForegroundColor Cyan
        try {
            $healthResponse = Invoke-RestMethod -Uri "$devUrl/health" -Method GET -TimeoutSec 5
            if ($healthResponse.ok -eq $true) {
                Write-Host "    OK /health endpoint working" -ForegroundColor Green
            } else {
                Write-Host "    ERROR /health returned unexpected response: $healthResponse" -ForegroundColor Red
            }
        } catch {
            Write-Host "    ERROR /health failed: $_" -ForegroundColor Red
        }
        
        # Test /status
        Write-Host "`n  Testing /status..." -ForegroundColor Cyan
        try {
            $statusResponse = Invoke-RestMethod -Uri "$devUrl/status" -Method GET -TimeoutSec 10
            Write-Host "    OK /status endpoint working" -ForegroundColor Green
            
            # Display status summary
            Write-Host "`n    Status Summary:" -ForegroundColor Cyan
            if ($statusResponse.env_ok) {
                if ($statusResponse.env_ok.Count -eq 0) {
                    Write-Host "      Environment: OK All vars present" -ForegroundColor Green
                } else {
                    Write-Host "      Environment: ERROR Missing: $($statusResponse.env_ok -join ', ')" -ForegroundColor Red
                }
            }
            if ($statusResponse.supabase_ok) {
                Write-Host "      Supabase: OK Connected" -ForegroundColor Green
                if ($statusResponse.supabase_payload) {
                    $payload = $statusResponse.supabase_payload
                    Write-Host "        Embeddings: $($payload.embeddings_rows)" -ForegroundColor White
                    Write-Host "        Files: $($payload.files_indexed)" -ForegroundColor White
                }
            } else {
                Write-Host "      Supabase: ERROR Not connected" -ForegroundColor Red
                if ($statusResponse.supabase_payload) {
                    Write-Host "        Error: $($statusResponse.supabase_payload.error)" -ForegroundColor Yellow
                }
            }
            if ($statusResponse.rpc_ok) {
                Write-Host "      RPC (match_kb): OK Working" -ForegroundColor Green
            } else {
                Write-Host "      RPC (match_kb): ERROR Failed" -ForegroundColor Red
                if ($statusResponse.rpc_error) {
                    Write-Host "        Error: $($statusResponse.rpc_error)" -ForegroundColor Yellow
                }
            }
        } catch {
            Write-Host "    ERROR /status failed: $_" -ForegroundColor Red
        }
        
        # Stop dev server
        Write-Host "`n  Stopping dev server..." -ForegroundColor Yellow
        try {
            Stop-Process -Id $devProcess.Id -Force -ErrorAction SilentlyContinue
            Write-Host "    OK Dev server stopped" -ForegroundColor Green
        } catch {
            Write-Host "    WARN Could not stop dev server (may need manual cleanup)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  ERROR Dev server did not start within $maxWait seconds" -ForegroundColor Red
        Write-Host "    Check for errors in wrangler output" -ForegroundColor Yellow
        try {
            Stop-Process -Id $devProcess.Id -Force -ErrorAction SilentlyContinue
        } catch {}
    }
} catch {
    Write-Host "  ERROR Failed to start dev server: $_" -ForegroundColor Red
    Write-Host "    Run manually: cd cloud\worker && wrangler dev" -ForegroundColor Yellow
}

# Final guidance
Write-Host "`n[4/4] Validation Summary..." -ForegroundColor Cyan
Write-Host "`nIf any checks failed:" -ForegroundColor Yellow
Write-Host "  1. Secrets: Run 'wrangler secret put SECRET_NAME' or use sync-secrets.ps1" -ForegroundColor White
Write-Host "  2. Dev server: Check .dev.vars file exists and has correct values" -ForegroundColor White
Write-Host "  3. Supabase: Verify SUPABASE_URL and SUPABASE_ANON_KEY are correct" -ForegroundColor White
Write-Host "  4. RPC errors: Ensure Supabase SQL (01_init.sql, 03_status.sql) are applied" -ForegroundColor White

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Validation Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

Set-Location $repoRoot

