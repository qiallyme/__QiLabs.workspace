# Finish flattening remaining directories
$inboxPath = ".inbox"
$trashPath = ".inbox\.trash"

Write-Host "=== Finishing flattening remaining directories ==="

# Get remaining directories (excluding _inbox, .trash, __pycache__)
$remainingDirs = Get-ChildItem -Path $inboxPath -Directory -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -ne "_inbox" -and $_.Name -ne ".trash" -and $_.Name -ne "__pycache__"
}

$totalFlattened = 0
foreach ($dir in $remainingDirs) {
    $files = Get-ChildItem -Path $dir.FullName -Recurse -File -ErrorAction SilentlyContinue
    Write-Host "Processing $($dir.Name): $($files.Count) files"
    
    foreach ($file in $files) {
        try {
            $newName = $file.Name
            $counter = 1
            while (Test-Path (Join-Path $inboxPath $newName)) {
                $namePart = [System.IO.Path]::GetFileNameWithoutExtension($file.Name)
                $ext = $file.Extension
                $newName = "${namePart}_${counter}${ext}"
                $counter++
            }
            Move-Item -LiteralPath $file.FullName -Destination (Join-Path $inboxPath $newName) -Force -ErrorAction Stop
            $totalFlattened++
        } catch {
            Write-Host "  Failed: $($file.Name)"
        }
    }
}

Write-Host "`nFlattened $totalFlattened additional files"

# Now organize these newly flattened files
$files = Get-ChildItem -Path $inboxPath -File -ErrorAction SilentlyContinue | Where-Object {
    $_.Extension -notin @('.ps1', '.py', '.bat')
}

$pdfs = 0
$mds = 0
$images = 0
$data = 0
$trash = 0

foreach ($file in $files) {
    try {
        $ext = $file.Extension.ToLower()
        $moved = $false
        
        if ($ext -eq '.pdf') {
            $dest = Join-Path "docs" $file.Name
            if (Test-Path $dest) {
                $namePart = [System.IO.Path]::GetFileNameWithoutExtension($file.Name)
                $dest = Join-Path "docs" "${namePart}_$([guid]::NewGuid().ToString('N').Substring(0,8)).pdf"
            }
            Move-Item -LiteralPath $file.FullName -Destination $dest -Force -ErrorAction Stop
            $pdfs++
            $moved = $true
        }
        elseif ($ext -eq '.md') {
            $dest = Join-Path "docs" $file.Name
            if (Test-Path $dest) {
                $namePart = [System.IO.Path]::GetFileNameWithoutExtension($file.Name)
                $dest = Join-Path "docs" "${namePart}_$([guid]::NewGuid().ToString('N').Substring(0,8)).md"
            }
            Move-Item -LiteralPath $file.FullName -Destination $dest -Force -ErrorAction Stop
            $mds++
            $moved = $true
        }
        elseif ($ext -in @('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.ico')) {
            $dest = Join-Path "assets" $file.Name
            if (Test-Path $dest) {
                $namePart = [System.IO.Path]::GetFileNameWithoutExtension($file.Name)
                $dest = Join-Path "assets" "${namePart}_$([guid]::NewGuid().ToString('N').Substring(0,8))$ext"
            }
            Move-Item -LiteralPath $file.FullName -Destination $dest -Force -ErrorAction Stop
            $images++
            $moved = $true
        }
        elseif ($ext -in @('.csv', '.json', '.xlsx', '.xls', '.xml')) {
            $dest = Join-Path "data\_inbox" $file.Name
            if (Test-Path $dest) {
                $namePart = [System.IO.Path]::GetFileNameWithoutExtension($file.Name)
                $dest = Join-Path "data\_inbox" "${namePart}_$([guid]::NewGuid().ToString('N').Substring(0,8))$ext"
            }
            Move-Item -LiteralPath $file.FullName -Destination $dest -Force -ErrorAction Stop
            $data++
            $moved = $true
        }
        
        if (-not $moved) {
            $dest = Join-Path $trashPath $file.Name
            if (Test-Path $dest) {
                $namePart = [System.IO.Path]::GetFileNameWithoutExtension($file.Name)
                $dest = Join-Path $trashPath "${namePart}_$([guid]::NewGuid().ToString('N').Substring(0,8))$ext"
            }
            Move-Item -LiteralPath $file.FullName -Destination $dest -Force -ErrorAction Stop
            $trash++
        }
    } catch {
        Write-Host "Failed: $($file.Name)"
    }
}

Write-Host "`n=== Final Organization ==="
Write-Host "PDFs: $pdfs, MDs: $mds, Images: $images, Data: $data, Trash: $trash"

# Remove empty directories
$emptyDirs = Get-ChildItem -Path $inboxPath -Directory -Recurse -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -ne "_inbox" -and $_.Name -ne ".trash" -and $_.Name -ne "__pycache__" -and
    (Get-ChildItem -Path $_.FullName -Recurse -ErrorAction SilentlyContinue | Measure-Object).Count -eq 0
}
$removed = 0
foreach ($dir in $emptyDirs) {
    try {
        Remove-Item -LiteralPath $dir.FullName -Force -ErrorAction Stop
        $removed++
    } catch { }
}
Write-Host "Removed $removed empty directories"
Write-Host "`n=== Complete ==="
