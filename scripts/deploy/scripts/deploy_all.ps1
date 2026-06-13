# Deploy all QiOS Workers
# Run from anywhere - script auto-detects repo root

Write-Host "Deploying all QiOS Workers..." -ForegroundColor Cyan
Write-Host ""

$workers = @(
    "orchestrator",
    "memory",
    "embedder",
    "ingestion",
    "self_heal",
    "metadata_naming",
    "semantic_router"
)

# Navigate to repo root (scripts are in workers/scripts/)
$rootDir = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $rootDir

foreach ($worker in $workers) {
    Write-Host "Deploying $worker..." -ForegroundColor Yellow
    $workerPath = "workers\cloud\$worker"
    
    if (Test-Path $workerPath) {
        Set-Location $workerPath
        
        # Check if main file exists
        $wranglerToml = Join-Path $workerPath "wrangler.toml"
        if (Test-Path "wrangler.toml") {
            # Deploy from within the worker directory (wrangler.toml paths are relative)
            npx wrangler deploy
            if ($LASTEXITCODE -eq 0) {
                Write-Host "[OK] $worker deployed successfully" -ForegroundColor Green
            } else {
                Write-Host "[FAIL] $worker deployment failed" -ForegroundColor Red
            }
        } else {
            Write-Host "[WARN] wrangler.toml not found in $workerPath" -ForegroundColor Yellow
        }
        
        Set-Location $rootDir
    } else {
        Write-Host "[WARN] $workerPath not found, skipping..." -ForegroundColor Yellow
    }
    Write-Host ""
}

Write-Host "Deployment complete!" -ForegroundColor Cyan

