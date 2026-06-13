# Deploy only the 3 critical workers
# Run from anywhere - script auto-detects repo root

Write-Host "Deploying critical workers..." -ForegroundColor Cyan
Write-Host ""

# Navigate to repo root (scripts are in workers/scripts/)
$rootDir = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $rootDir

$criticalWorkers = @(
    @{ name = "embedder"; dir = "workers\cloud\embedder" }
    @{ name = "memory"; dir = "workers\cloud\memory" }
    @{ name = "orchestrator"; dir = "workers\cloud\orchestrator" }
)

foreach ($worker in $criticalWorkers) {
    $workerName = $worker.name
    $workerDir = $worker.dir
    
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host "Deploying: $workerName" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Yellow
    
    if (Test-Path $workerDir) {
        Set-Location $workerDir
        
        # Verify main file exists
        $wranglerToml = Get-Content "wrangler.toml" -ErrorAction SilentlyContinue
        if ($wranglerToml) {
            $mainFile = ($wranglerToml | Select-String "main\s*=\s*['""]([^'""]+)['""]").Matches.Groups[1].Value
            if ($mainFile -and (Test-Path $mainFile)) {
                Write-Host "Main file found: $mainFile" -ForegroundColor Gray
                Write-Host "Deploying..." -ForegroundColor Cyan
                npx wrangler deploy
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "[OK] $workerName deployed successfully" -ForegroundColor Green
                } else {
                    Write-Host "[FAIL] $workerName deployment failed" -ForegroundColor Red
                }
            } else {
                Write-Host "[ERROR] Main file not found: $mainFile" -ForegroundColor Red
                Write-Host "Check wrangler.toml in $workerDir" -ForegroundColor Yellow
            }
        } else {
            Write-Host "[ERROR] wrangler.toml not found in $workerDir" -ForegroundColor Red
        }
        
        Set-Location $rootDir
    } else {
        Write-Host "[WARN] Directory not found: $workerDir" -ForegroundColor Yellow
    }
    
    Write-Host ""
}

Write-Host "Deployment complete!" -ForegroundColor Cyan

