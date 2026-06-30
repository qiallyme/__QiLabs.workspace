# Flatten .inbox and organize files
$inboxPath = ".inbox"
$trashPath = ".inbox\.trash"
if (-not (Test-Path $trashPath)) { New-Item -ItemType Directory -Path $trashPath -Force | Out-Null }

# Get all files recursively from .inbox (excluding _inbox, .trash, and script files)
$allFiles = Get-ChildItem -Path $inboxPath -Recurse -File -ErrorAction SilentlyContinue | Where-Object {
    $_.FullName -notlike "*\_inbox\*" -and
    $_.FullName -notlike "*\.trash\*" -and
    $_.FullName -notlike "*\__pycache__\*" -and
    $_.Extension -notin @('.ps1', '.py', '.bat', '.md') -or ($_.Extension -eq '.md' -and $_.DirectoryName -eq (Resolve-Path $inboxPath))
}

Write-Host "Found $($allFiles.Count) files to process"

# Categorize and move files
$pdfs = 0
$mds = 0
$images = 0
$data = 0
$trash = 0

foreach ($file in $allFiles) {
    try {
        $ext = $file.Extension.ToLower()
        $moved = $false
        
        # PDFs -> docs
        if ($ext -eq '.pdf') {
            $dest = Join-Path "docs" $file.Name
            if (Test-Path $dest) { $dest = Join-Path "docs" "$([System.IO.Path]::GetFileNameWithoutExtension($file.Name))_$([guid]::NewGuid().ToString('N').Substring(0,8)).pdf" }
            Move-Item -LiteralPath $file.FullName -Destination $dest -Force -ErrorAction Stop
            $pdfs++
            $moved = $true
        }
        # MD files -> docs (we'll organize by content later)
        elseif ($ext -eq '.md') {
            $dest = Join-Path "docs" $file.Name
            if (Test-Path $dest) { $dest = Join-Path "docs" "$([System.IO.Path]::GetFileNameWithoutExtension($file.Name))_$([guid]::NewGuid().ToString('N').Substring(0,8)).md" }
            Move-Item -LiteralPath $file.FullName -Destination $dest -Force -ErrorAction Stop
            $mds++
            $moved = $true
        }
        # Images -> assets
        elseif ($ext -in @('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg')) {
            $dest = Join-Path "assets" $file.Name
            if (Test-Path $dest) { $dest = Join-Path "assets" "$([System.IO.Path]::GetFileNameWithoutExtension($file.Name))_$([guid]::NewGuid().ToString('N').Substring(0,8))$ext" }
            Move-Item -LiteralPath $file.FullName -Destination $dest -Force -ErrorAction Stop
            $images++
            $moved = $true
        }
        # CSV/Data files -> data\_inbox
        elseif ($ext -in @('.csv', '.json', '.xlsx', '.xls')) {
            $dest = Join-Path "data\_inbox" $file.Name
            if (Test-Path $dest) { $dest = Join-Path "data\_inbox" "$([System.IO.Path]::GetFileNameWithoutExtension($file.Name))_$([guid]::NewGuid().ToString('N').Substring(0,8))$ext" }
            Move-Item -LiteralPath $file.FullName -Destination $dest -Force -ErrorAction Stop
            $data++
            $moved = $true
        }
        
        # Everything else -> trash
        if (-not $moved) {
            $dest = Join-Path $trashPath $file.Name
            if (Test-Path $dest) { $dest = Join-Path $trashPath "$([System.IO.Path]::GetFileNameWithoutExtension($file.Name))_$([guid]::NewGuid().ToString('N').Substring(0,8))$ext" }
            Move-Item -LiteralPath $file.FullName -Destination $dest -Force -ErrorAction Stop
            $trash++
        }
    } catch {
        Write-Host "Failed: $($file.Name) - $($_.Exception.Message)"
    }
}

Write-Host "`n=== Flattening Summary ==="
Write-Host "PDFs moved to docs: $pdfs"
Write-Host "MD files moved to docs: $mds"
Write-Host "Images moved to assets: $images"
Write-Host "Data files moved to data\_inbox: $data"
Write-Host "Other files moved to trash: $trash"
