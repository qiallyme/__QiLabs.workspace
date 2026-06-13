# Simple GINA Chat Test (PowerShell)
# Quick test to see what error we're getting

Write-Host "Testing GINA Chat..." -ForegroundColor Cyan
Write-Host ""

$body = @{
    messages = @(
        @{
            role = "user"
            content = "Hello"
        }
    )
} | ConvertTo-Json -Depth 10

Write-Host "Request:" -ForegroundColor Yellow
Write-Host $body
Write-Host ""

try {
    $response = Invoke-WebRequest -Uri "http://localhost:7130/gina/chat" `
        -Method POST `
        -Body $body `
        -ContentType "application/json" `
        -ErrorAction Stop
    
    Write-Host "✅ SUCCESS!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Response:" -ForegroundColor Yellow
    $response.Content | ConvertFrom-Json | ConvertTo-Json -Depth 10
} catch {
    Write-Host "❌ ERROR!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Status Code: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Yellow
    Write-Host ""
    
    # Try to get error detail
    try {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "Error Response:" -ForegroundColor Yellow
        Write-Host $responseBody
    } catch {
        Write-Host "Could not read error response: $_" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "💡 Check the Local Core service window for detailed error logs" -ForegroundColor Cyan
}

