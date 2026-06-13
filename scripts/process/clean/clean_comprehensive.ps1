# Comprehensive cleanup script
$trashPath = ".inbox\.trash"
if (-not (Test-Path $trashPath)) { New-Item -ItemType Directory -Path $trashPath -Force | Out-Null }

# Step 1: Move .md files from ExportBlock folders (duplicates of CSV data)
Write-Host "Step 1: Moving .md files from ExportBlock folders..."
$exportMdFiles = Get-ChildItem -Path ".inbox\ExportBlock-*" -Recurse -Filter "*.md" -ErrorAction SilentlyContinue
$moved = 0
foreach ($file in $exportMdFiles) {
    try {
        $dest = Join-Path $trashPath $file.Name
        if (Test-Path $dest) { $dest = Join-Path $trashPath "$([System.IO.Path]::GetFileNameWithoutExtension($file.Name))_$([guid]::NewGuid().ToString('N').Substring(0,8)).md" }
        Move-Item -LiteralPath $file.FullName -Destination $dest -Force -ErrorAction Stop
        $moved++
    } catch {
        Write-Host "Failed: $($file.Name)"
    }
}
Write-Host "Moved $moved .md files from ExportBlock folders"

# Step 2: Unzip zip files
Write-Host "`nStep 2: Unzipping files..."
$zipFiles = @(
    (Get-ChildItem -Path "assets" -Filter "*.zip" -ErrorAction SilentlyContinue),
    (Get-ChildItem -Path ".inbox" -Filter "*.zip" -Recurse -ErrorAction SilentlyContinue)
) | Where-Object { $_ -ne $null } | Select-Object -Unique

$unzipped = 0
foreach ($zip in $zipFiles) {
    try {
        $extractPath = Join-Path $zip.DirectoryName ([System.IO.Path]::GetFileNameWithoutExtension($zip.Name))
        if (-not (Test-Path $extractPath)) {
            Expand-Archive -LiteralPath $zip.FullName -DestinationPath $extractPath -Force
            $unzipped++
            Write-Host "Unzipped: $($zip.Name)"
        }
    } catch {
        Write-Host "Failed to unzip: $($zip.Name) - $($_.Exception.Message)"
    }
}
Write-Host "Unzipped $unzipped zip files"

# Step 3: Move CSV files from ExportBlock to data subdirectories
Write-Host "`nStep 3: Organizing CSV files..."
$csvFiles = Get-ChildItem -Path ".inbox\ExportBlock-*" -Recurse -Filter "*.csv" -ErrorAction SilentlyContinue
$csvMoved = 0
foreach ($csv in $csvFiles) {
    try {
        $name = $csv.Name
        $destDir = "data"
        
        # Determine destination based on filename
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
        } else {
            $destDir = "data\_inbox"
        }
        
        if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir -Force | Out-Null }
        $dest = Join-Path $destDir $csv.Name
        if (Test-Path $dest) { $dest = Join-Path $destDir "$([System.IO.Path]::GetFileNameWithoutExtension($csv.Name))_$([guid]::NewGuid().ToString('N').Substring(0,8)).csv" }
        Move-Item -LiteralPath $csv.FullName -Destination $dest -Force -ErrorAction Stop
        $csvMoved++
    } catch {
        Write-Host "Failed CSV move: $($csv.Name)"
    }
}
Write-Host "Moved $csvMoved CSV files"

Write-Host "`nCleanup complete!"
