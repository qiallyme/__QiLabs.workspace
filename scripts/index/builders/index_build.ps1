# Simple PowerShell Build Script for Timeline
Write-Host ""
Write-Host "Building timeline..." -ForegroundColor Cyan
Write-Host ""

$eventsDir = "G:\My Drive\QiOne\5_Apps\QiTimeline\events"
$distDir = "G:\My Drive\QiOne\5_Apps\QiTimeline\dist"
$outputFile = Join-Path $distDir "timeline.json"

# Create dist directory
if (-not (Test-Path $distDir))
{
    New-Item -ItemType Directory -Path $distDir | Out-Null
    Write-Host "Created dist/ directory" -ForegroundColor Gray
    Write-Host ""
}

# Copy files to dist
$filesToCopy = @("index.html", "styles.css", "script.js", "timeline-loader-json.js")
Write-Host "Copying files to dist/..." -ForegroundColor Gray
foreach ($file in $filesToCopy)
{
    $srcPath = Join-Path "G:\My Drive\QiOne\5_Apps\QiTimeline" $file
    $destPath = Join-Path $distDir $file
    if (Test-Path $srcPath)
    {
        Copy-Item $srcPath $destPath -Force
        Write-Host "  ✓ $file" -ForegroundColor Green
    }
}
Write-Host ""

# Get all markdown files
$files = Get-ChildItem -Path $eventsDir -Filter "*.md" | Where-Object { $_.Name -notlike "_*" -and $_.Name -notlike "TEMPLATE*" }
Write-Host "Found $($files.Count) markdown files" -ForegroundColor Gray
Write-Host ""

$events = @()
$successCount = 0

foreach ($file in $files)
{
    $content = Get-Content $file.FullName -Raw -Encoding UTF8
    
    # Parse front matter using regex
    if ($content -match '(?s)^---\s*[\r]?\n(.*?)[\r]?\n---\s*[\r]?\n(.*)$')
    {
        $frontMatter = $Matches[1]
        $body = $Matches[2].Trim()
        
        # Extract fields
        $date = ""
        if ($frontMatter -match 'date:\s*(.+)')
        {
            $date = $Matches[1].Trim()
        }
        
        $title = ""
        if ($frontMatter -match 'title:\s*(.+)')
        {
            $title = $Matches[1].Trim()
        }
        
        $category = ""
        if ($frontMatter -match 'category:\s*(.+)')
        {
            $category = $Matches[1].Trim()
        }
        
        $critical = $false
        if ($frontMatter -match 'critical:\s*(true|false)')
        {
            $critical = $Matches[1] -eq 'true'
        }
        
        # Extract tags
        $tags = @()
        $lines = $frontMatter -split "`n"
        $inTags = $false
        foreach ($line in $lines)
        {
            $line = $line.Trim()
            if ($line -eq 'tags:')
            {
                $inTags = $true
                continue
            }
            if ($inTags)
            {
                if ($line -match '^-\s*(.+)$')
                {
                    $tags += $Matches[1].Trim()
                }
                elseif ($line -match '^[a-zA-Z]')
                {
                    # Next field started, stop reading tags
                    break
                }
            }
        }
        
        $event = [PSCustomObject]@{
            id = $file.BaseName
            date = $date
            title = $title
            category = $category
            critical = $critical
            tags = $tags
            description = $body
        }
        
        $events += $event
        Write-Host "  ✓ $($file.Name)" -ForegroundColor Green
        $successCount++
    }
}

# Sort by date (newest first)
$events = $events | Sort-Object { [DateTime]$_.date } -Descending

# Convert to JSON
$json = $events | ConvertTo-Json -Depth 10
Set-Content -Path $outputFile -Value $json -Encoding UTF8

Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Successfully built timeline.json" -ForegroundColor Green
Write-Host "Total events: $($events.Count)" -ForegroundColor Gray
Write-Host "Success: $successCount" -ForegroundColor Gray
Write-Host "Output: $outputFile" -ForegroundColor Gray
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# Statistics
$criticalCount = ($events | Where-Object { $_.critical }).Count
$categories = $events | Group-Object category

Write-Host "Statistics:" -ForegroundColor Cyan
Write-Host "  Critical events: $criticalCount" -ForegroundColor Gray
Write-Host "  By category:" -ForegroundColor Gray
foreach ($cat in ($categories | Sort-Object Name))
{
    Write-Host "    - $($cat.Name): $($cat.Count)" -ForegroundColor Gray
}
Write-Host ""
Write-Host "Done! You can now open dist/index.html in your browser." -ForegroundColor Green
Write-Host ""
