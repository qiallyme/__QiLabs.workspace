# Continue cleanup
Write-Host "Step 4: Handling 'unzip and flatten' folder..."
$unzipFolder = ".inbox\unzip and flatten"
if (Test-Path $unzipFolder) {
    # Move .md files from unzip folder to trash
    $unzipMdFiles = Get-ChildItem -Path $unzipFolder -Recurse -Filter "*.md" -ErrorAction SilentlyContinue | Where-Object {
        $_.Name -match ' [a-f0-9]{32}\.md$'
    }
    $moved = 0
    foreach ($file in $unzipMdFiles) {
        try {
            $dest = Join-Path ".inbox\.trash" $file.Name
            if (Test-Path $dest) { $dest = Join-Path ".inbox\.trash" "$([System.IO.Path]::GetFileNameWithoutExtension($file.Name))_$([guid]::NewGuid().ToString('N').Substring(0,8)).md" }
            Move-Item -LiteralPath $file.FullName -Destination $dest -Force -ErrorAction Stop
            $moved++
        } catch { }
    }
    Write-Host "Moved $moved .md files from unzip folder"
    
    # Move CSV files from unzip folder
    $unzipCsvFiles = Get-ChildItem -Path $unzipFolder -Recurse -Filter "*.csv" -ErrorAction SilentlyContinue
    $csvMoved = 0
    foreach ($csv in $unzipCsvFiles) {
        try {
            $name = $csv.Name
            $destDir = "data\_inbox"
            
            if ($name -like "*Contact*" -or $name -like "*Business*") {
                $destDir = "data\contacts"
            } elseif ($name -like "*Domain*" -or $name -like "*DNS*") {
                $destDir = "data\web"
            } elseif ($name -like "*Drive*" -or $name -like "*Device*") {
                $destDir = "data\devices"
            } elseif ($name -like "*API*" -or $name -like "*Key*" -or $name -like "*Secret*") {
                $destDir = "data\secrets"
            } elseif ($name -like "*Trigger*" -or $name -like "*Flow*") {
                $destDir = "data\flows"
            } elseif ($name -like "*Notification*") {
                $destDir = "data\notifications"
            } elseif ($name -like "*Registry*" -or $name -like "*Core*") {
                $destDir = "data\registry"
            }
            
            if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir -Force | Out-Null }
            $dest = Join-Path $destDir $csv.Name
            if (Test-Path $dest) { $dest = Join-Path $destDir "$([System.IO.Path]::GetFileNameWithoutExtension($csv.Name))_$([guid]::NewGuid().ToString('N').Substring(0,8)).csv" }
            Move-Item -LiteralPath $csv.FullName -Destination $dest -Force -ErrorAction Stop
            $csvMoved++
        } catch { }
    }
    Write-Host "Moved $csvMoved CSV files from unzip folder"
}

# Step 5: Find and unzip zip files in assets
Write-Host "`nStep 5: Unzipping zip files in assets..."
$assetZips = Get-ChildItem -Path "assets" -Filter "*.zip" -ErrorAction SilentlyContinue
$unzipped = 0
foreach ($zip in $assetZips) {
    try {
        $extractPath = Join-Path "assets" ([System.IO.Path]::GetFileNameWithoutExtension($zip.Name))
        if (-not (Test-Path $extractPath)) {
            Expand-Archive -LiteralPath $zip.FullName -DestinationPath $extractPath -Force
            $unzipped++
            Write-Host "Unzipped: $($zip.Name)"
        }
    } catch {
        Write-Host "Failed: $($zip.Name)"
    }
}
Write-Host "Unzipped $unzipped zip files from assets"

Write-Host "`nAdditional cleanup complete!"
