# Check secrets and environment variables for all QiOS Workers
# Run from anywhere - script auto-detects repo root

Write-Host "Checking secrets and environment variables for all workers..." -ForegroundColor Cyan
Write-Host ""

# Navigate to repo root (scripts are in workers/scripts/)
$rootDir = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $rootDir

$workers = @(
    @{ name = "orchestrator"; secrets = @("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "OPENAI_API_KEY", "MEMORY_WORKER_URL") },
    @{ name = "memory"; secrets = @("SUPABASE_URL", "SUPABASE_ANON_KEY", "OPENAI_API_KEY") },
    @{ name = "embedder"; secrets = @("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "OPENAI_API_KEY") },
    @{ name = "ingestion"; secrets = @("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY") },
    @{ name = "self_heal"; secrets = @("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY") },
    @{ name = "metadata_naming"; secrets = @("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY") },
    @{ name = "semantic_router"; secrets = @("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY") }
)

foreach ($worker in $workers) {
    $workerName = $worker.name
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host "Worker: $workerName" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Yellow
    
    # Check secrets using wrangler
    Write-Host "Checking secrets..." -ForegroundColor Cyan
    $workerPath = "workers\cloud\$workerName"
    
    if (Test-Path $workerPath) {
        Set-Location $workerPath
        
        # List secrets (this will show which secrets are set)
        Write-Host ""
        Write-Host "Secrets configured for ${workerName}:" -ForegroundColor White
        npx wrangler secret list 2>&1 | Out-String
        
        # Check expected secrets
        Write-Host ""
        Write-Host "Expected secrets:" -ForegroundColor White
        foreach ($secret in $worker.secrets) {
            Write-Host "  - $secret" -ForegroundColor Gray
        }
        
        Set-Location $rootDir
    } else {
        Write-Host "[WARN] $workerPath not found" -ForegroundColor Yellow
    }
    
    Write-Host ""
}

Write-Host "========================================" -ForegroundColor Yellow
Write-Host "Summary" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow
Write-Host ""
Write-Host "To set a secret for a worker:" -ForegroundColor Cyan
Write-Host "  cd workers\cloud\<worker-name>" -ForegroundColor White
Write-Host "  npx wrangler secret put <SECRET_NAME>" -ForegroundColor White
Write-Host ""
Write-Host "Example:" -ForegroundColor Cyan
Write-Host "  cd workers\cloud\embedder" -ForegroundColor White
Write-Host "  npx wrangler secret put SUPABASE_URL" -ForegroundColor White
Write-Host "  npx wrangler secret put SUPABASE_SERVICE_ROLE_KEY" -ForegroundColor White
Write-Host "  npx wrangler secret put OPENAI_API_KEY" -ForegroundColor White

