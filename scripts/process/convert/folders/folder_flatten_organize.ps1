# Flatten .inbox and organize files
$inboxPath = ".inbox"
$trashPath = ".inbox\.trash"
if (-not (Test-Path $trashPath)) { New-Item -ItemType Directory -Path $trashPath -Force | Out-Null }

Write-Host "=== Flattening .inbox and organizing files ==="

# Step 1: Flatten - move all files from subdirectories to .inbox root (temporarily)
Write-Host "`nStep 1: Flattening folder structure..."
$subdirs = Get-ChildItem -Path $inboxPath -Directory -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -ne "_inbox" -and $_.Name -ne ".trash" -and $_.Name -ne "__pycache__"
}

$flattened = 0
foreach ($dir in $subdirs) {
    $files = Get-ChildItem -Path $dir.FullName -Recurse -File -ErrorAction SilentlyContinue
    foreach ($file in $files) {
        try {
            # Create unique name if needed
            $newName = $file.Name
            $counter = 1
            while (Test-Path (Join-Path $inboxPath $newName)) {
                $namePart = [System.IO.Path]::GetFileNameWithoutExtension($file.Name)
                $ext = $file.Extension
                $newName = "${namePart}_${counter}${ext}"
                $counter++
            }
            Move-Item -LiteralPath $file.FullName -Destination (Join-Path $inboxPath $newName) -Force -ErrorAction Stop
            $flattened++
        } catch {
            Write-Host "Failed to flatten: $($file.FullName)"
        }
    }
}
Write-Host "Flattened $flattened files"

# Step 2: Organize files from .inbox root
Write-Host "`nStep 2: Organizing files..."
$files = Get-ChildItem -Path $inboxPath -File -ErrorAction SilentlyContinue | Where-Object {
    $_.Extension -notin @('.ps1', '.py', '.bat') -or ($_.Extension -eq '.md' -and $_.Name -notlike "*cleanup*" -and $_.Name -notlike "*compare*" -and $_.Name -notlike "*find*")
}

$pdfs = 0
$mds = 0
$images = 0
$data = 0
$audio = 0
$video = 0
$trash = 0

foreach ($file in $files) {
    try {
        $ext = $file.Extension.ToLower()
        $moved = $false
        
        # PDFs -> docs
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
        # MD files -> docs
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
        # Images -> assets
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
        # Audio -> assets
        elseif ($ext -in @('.mp3', '.wav', '.m4a', '.aac', '.ogg')) {
            $dest = Join-Path "assets" $file.Name
            if (Test-Path $dest) {
                $namePart = [System.IO.Path]::GetFileNameWithoutExtension($file.Name)
                $dest = Join-Path "assets" "${namePart}_$([guid]::NewGuid().ToString('N').Substring(0,8))$ext"
            }
            Move-Item -LiteralPath $file.FullName -Destination $dest -Force -ErrorAction Stop
            $audio++
            $moved = $true
        }
        # Video -> assets
        elseif ($ext -in @('.mp4', '.mov', '.avi', '.mkv', '.webm')) {
            $dest = Join-Path "assets" $file.Name
            if (Test-Path $dest) {
                $namePart = [System.IO.Path]::GetFileNameWithoutExtension($file.Name)
                $dest = Join-Path "assets" "${namePart}_$([guid]::NewGuid().ToString('N').Substring(0,8))$ext"
            }
            Move-Item -LiteralPath $file.FullName -Destination $dest -Force -ErrorAction Stop
            $video++
            $moved = $true
        }
        # Data files -> data\_inbox
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
        
        # Everything else -> trash
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
        Write-Host "Failed: $($file.Name) - $($_.Exception.Message)"
    }
}

Write-Host "`n=== Organization Summary ==="
Write-Host "PDFs moved to docs: $pdfs"
Write-Host "MD files moved to docs: $mds"
Write-Host "Images moved to assets: $images"
Write-Host "Audio moved to assets: $audio"
Write-Host "Video moved to assets: $video"
Write-Host "Data files moved to data\_inbox: $data"
Write-Host "Other files moved to trash: $trash"

# Step 3: Remove empty directories
Write-Host "`nStep 3: Removing empty directories..."
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
