# PowerShell script to deploy Cloudflare Worker
# Run this from the project root

Write-Host "🚀 Deploying QiCockpit Gina Worker to Cloudflare..." -ForegroundColor Cyan

# Check if wrangler is installed
$wranglerCheck = Get-Command wrangler -ErrorAction SilentlyContinue
if (-not $wranglerCheck) {
    Write-Host "❌ Wrangler CLI not found. Installing..." -ForegroundColor Yellow
    npm install -g wrangler
}

# Navigate to worker directory
Set-Location worker

# Check if secrets are set
Write-Host "`n📋 Checking required secrets..." -ForegroundColor Cyan
Write-Host "Required secrets:" -ForegroundColor Yellow
Write-Host "  - SUPABASE_URL"
Write-Host "  - SUPABASE_SERVICE_ROLE_KEY"
Write-Host "  - OPENAI_API_KEY"
Write-Host "`nOptional secrets:" -ForegroundColor Yellow
Write-Host "  - ZOHO_MCP_URL"
Write-Host "  - ZOHO_MCP_KEY"
Write-Host "`nTo set secrets, run:" -ForegroundColor Cyan
Write-Host "  wrangler secret put SUPABASE_URL" -ForegroundColor White
Write-Host "  wrangler secret put SUPABASE_SERVICE_ROLE_KEY" -ForegroundColor White
Write-Host "  wrangler secret put OPENAI_API_KEY" -ForegroundColor White
Write-Host "  wrangler secret put ZOHO_MCP_URL" -ForegroundColor White
Write-Host "  wrangler secret put ZOHO_MCP_KEY" -ForegroundColor White

$continue = Read-Host "`nContinue with deployment? (y/n)"
if ($continue -ne 'y') {
    Write-Host "Deployment cancelled." -ForegroundColor Yellow
    Set-Location ..
    exit
}

# Install dependencies if needed
if (-not (Test-Path "node_modules")) {
    Write-Host "`n📦 Installing dependencies..." -ForegroundColor Cyan
    npm install
}

# Deploy
Write-Host "`n🚀 Deploying worker..." -ForegroundColor Cyan
wrangler deploy

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Deployment successful!" -ForegroundColor Green
    Write-Host "`nTest your worker:" -ForegroundColor Cyan
    Write-Host "  curl https://qicockpit-gina.your-subdomain.workers.dev/health" -ForegroundColor White
} else {
    Write-Host "`n❌ Deployment failed. Check the errors above." -ForegroundColor Red
}

Set-Location ..

