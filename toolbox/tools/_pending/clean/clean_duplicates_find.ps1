# Comprehensive duplicate finder
Write-Host "=== Duplicate File Analysis ==="

# Find files with _1, _2, _3 suffixes (common duplicate pattern)
Write-Host "`n1. Finding files with duplicate suffixes (_1, _2, etc.)..."
$duplicateSuffixFiles = Get-ChildItem -Path "data", ".inbox" -Recurse -File -ErrorAction SilentlyContinue | Where-Object {
    $_.BaseName -match '_(\d+)$' -and $_.BaseName -notmatch '^\d{8}_'  # Exclude date prefixes
} | Group-Object { $_.BaseName -replace '_\d+$', '' } | Where-Object { $_.Count -gt 1 }

Write-Host "Found $($duplicateSuffixFiles.Count) groups of files with duplicate suffixes"
$duplicateSuffixFiles | Select-Object -First 10 | ForEach-Object {
    Write-Host "  Group: $($_.Name) - $($_.Count) files"
    $_.Group | ForEach-Object { Write-Host "    - $($_.FullName)" }
}

# Find files with exact duplicate names in different locations
Write-Host "`n2. Finding files with same name in different locations..."
$allFiles = Get-ChildItem -Path "data", ".inbox" -Recurse -File -ErrorAction SilentlyContinue
$duplicateNames = $allFiles | Group-Object Name | Where-Object { $_.Count -gt 1 } | Where-Object {
    ($_.Group | Select-Object -Unique DirectoryName).Count -gt 1
}

Write-Host "Found $($duplicateNames.Count) files with duplicate names in different locations"
$duplicateNames | Select-Object -First 10 | ForEach-Object {
    Write-Host "  File: $($_.Name) - appears in $($_.Count) locations"
    $_.Group | Select-Object -Unique DirectoryName | ForEach-Object { Write-Host "    - $($_.DirectoryName)" }
}

# Find CSV files with _1 suffix that have a base version
Write-Host "`n3. Finding CSV files with _1 suffix that likely have originals..."
$csvFiles = Get-ChildItem -Path "data" -Recurse -Filter "*.csv" -ErrorAction SilentlyContinue
$csvDuplicates = $csvFiles | Where-Object { $_.BaseName -match '_1$' } | ForEach-Object {
    $baseName = $_.BaseName -replace '_1$', ''
    $original = $csvFiles | Where-Object { $_.BaseName -eq $baseName -and $_.FullName -ne $_.FullName }
    if ($original) {
        [PSCustomObject]@{
            Original = $original.FullName
            Duplicate = $_.FullName
        }
    }
}

Write-Host "Found $($csvDuplicates.Count) CSV files with _1 suffix that have originals"
$csvDuplicates | Select-Object -First 10 | ForEach-Object {
    Write-Host "  Original: $($_.Original)"
    Write-Host "  Duplicate: $($_.Duplicate)"
}

Write-Host "`n=== Analysis Complete ==="
