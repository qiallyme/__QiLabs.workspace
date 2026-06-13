<#
QiOS - Get Deployed Worker URLs

Gets the Cloudflare Worker URLs for all deployed workers.
#>

$ErrorActionPreference = "Continue"

$workers = @(
  "orchestrator",
  "ingestion",
  "semantic_router",
  "embedder",
  "metadata_naming",
  "self_heal"
)

Write-Host "`nQiOS Worker URLs:" -ForegroundColor Green
Write-Host "==================" -ForegroundColor Green

foreach ($worker in $workers) {
  $workerPath = "workers\$worker"
  
  if (Test-Path "$workerPath\wrangler.toml") {
    Write-Host "`n$worker :" -ForegroundColor Cyan
    try {
      cd $workerPath
      $url = npx wrangler whoami 2>&1 | Out-String
      $account = npx wrangler deployments list --format json 2>&1 | ConvertFrom-Json | Select-Object -First 1
      
      # Get worker name from wrangler.toml
      $wranglerContent = Get-Content "wrangler.toml" -Raw
      if ($wranglerContent -match 'name\s*=\s*"([^"]+)"') {
        $workerName = $matches[1]
        Write-Host "  Worker Name: $workerName" -ForegroundColor Yellow
        Write-Host "  URL: https://$workerName.{account}.workers.dev" -ForegroundColor Gray
        Write-Host "  (Check Cloudflare Dashboard for exact URL)" -ForegroundColor DarkGray
      }
    } catch {
      Write-Host "  Could not get URL (may need to check Cloudflare Dashboard)" -ForegroundColor DarkYellow
    }
    cd ..\..
  }
}

Write-Host "`nTo get exact URLs:" -ForegroundColor Cyan
Write-Host "1. Go to: https://dash.cloudflare.com" -ForegroundColor White
Write-Host "2. Navigate to: Workers & Pages > Your Workers" -ForegroundColor White
Write-Host "3. Each worker will show its URL" -ForegroundColor White

