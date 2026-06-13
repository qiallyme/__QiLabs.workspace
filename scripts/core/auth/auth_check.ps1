# Check Cloudflare authentication status
# Run from anywhere

Write-Host "Checking Cloudflare authentication..." -ForegroundColor Cyan
Write-Host ""

# Check if API token is set
if ($env:CLOUDFLARE_API_TOKEN) {
    Write-Host "[INFO] CLOUDFLARE_API_TOKEN is set" -ForegroundColor Gray
    Write-Host "Token (first 10 chars): $($env:CLOUDFLARE_API_TOKEN.Substring(0, [Math]::Min(10, $env:CLOUDFLARE_API_TOKEN.Length)))..." -ForegroundColor Gray
} else {
    Write-Host "[INFO] CLOUDFLARE_API_TOKEN not set in environment" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Testing authentication..." -ForegroundColor Cyan

try {
    $whoami = npx wrangler whoami 2>&1
    Write-Host $whoami
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "[OK] Authentication successful!" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "[ERROR] Authentication failed!" -ForegroundColor Red
        Write-Host ""
        Write-Host "To fix:" -ForegroundColor Yellow
        Write-Host "1. Update API token permissions:" -ForegroundColor White
        Write-Host "   https://dash.cloudflare.com/c81fe0732cbc0d6ba912dbcabb0c1164/api-tokens" -ForegroundColor Gray
        Write-Host ""
        Write-Host "2. Or use interactive login:" -ForegroundColor White
        Write-Host "   npx wrangler login" -ForegroundColor Gray
    }
} catch {
    Write-Host "[ERROR] Failed to check authentication: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "Required permissions for Workers:" -ForegroundColor Cyan
Write-Host "  - Workers Scripts → Edit" -ForegroundColor White
Write-Host "  - Workers Tail → Read" -ForegroundColor White
Write-Host "  - Workers Secrets → Edit" -ForegroundColor White

