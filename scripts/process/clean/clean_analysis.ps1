# Step 1: Find and move duplicate/unneeded .md files from exports
Write-Host "Step 1: Finding duplicate .md files from exports..."
$mdFiles = Get-ChildItem -Path ".inbox" -Recurse -Filter "*.md" | Where-Object { 
    $_.Name -match ' [a-f0-9]{32}\.md$' -or 
    $_.DirectoryName -like "*ExportBlock*" -or
    $_.DirectoryName -like "*unzip*"
}
Write-Host "Found $($mdFiles.Count) .md files from exports to move to trash"

# Step 2: Unzip remaining zip files
Write-Host "`nStep 2: Finding zip files to unzip..."
$zipFiles = Get-ChildItem -Path ".inbox", "assets" -Recurse -Filter "*.zip" -ErrorAction SilentlyContinue
Write-Host "Found $($zipFiles.Count) zip files"

# Step 3: Find CSV files in .inbox that need to be moved
Write-Host "`nStep 3: Finding CSV files in .inbox..."
$csvFiles = Get-ChildItem -Path ".inbox" -Recurse -Filter "*.csv" -ErrorAction SilentlyContinue | Where-Object {
    $_.DirectoryName -like "*ExportBlock*" -or
    $_.DirectoryName -like "*unzip*" -or
    $_.DirectoryName -like "*_inbox*"
}
Write-Host "Found $($csvFiles.Count) CSV files to organize"

Write-Host "`nSummary prepared. Ready to execute."
