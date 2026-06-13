# Move duplicate files (ending with space+number or _number) to .trash

$qivaultRoot = $PSScriptRoot
$trashDir = Join-Path $qivaultRoot ".trash"

# Create .trash folder if it doesn't exist
if (-not (Test-Path $trashDir)) {
    New-Item -ItemType Directory -Path $trashDir | Out-Null
    Write-Host "Created .trash folder" -ForegroundColor Green
}

# Find all .md files in root that end with:
# - Space followed by one or more digits: " 1.md", " 2.md", etc.
# - Underscore followed by one or more digits: "_1.md", "_2.md", "_3.md", etc.
$files = Get-ChildItem -Path $qivaultRoot -Filter "*.md" -File | 
    Where-Object { 
        ($_.Name -match ' \d+\.md$') -or ($_.Name -match '_\d+\.md$')
    }

$moved = 0
$skipped = 0

foreach ($file in $files) {
    $destPath = Join-Path $trashDir $file.Name
    
    if (Test-Path $destPath) {
        Write-Host "SKIP (exists): $($file.Name)" -ForegroundColor Yellow
        $skipped++
    } else {
        Move-Item -Path $file.FullName -Destination $destPath -Force
        Write-Host "MOVED: $($file.Name)" -ForegroundColor Green
        $moved++
    }
}

Write-Host "`n=== SUMMARY ===" -ForegroundColor Magenta
Write-Host "Moved: $moved files" -ForegroundColor Green
Write-Host "Skipped (already exists): $skipped files" -ForegroundColor Yellow
Write-Host "Total found: $($files.Count) files" -ForegroundColor Cyan

