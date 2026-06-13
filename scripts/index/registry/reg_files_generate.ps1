# Generate comprehensive file registry CSV
# Walks directory tree and exports file/folder metadata to CSV

$ErrorActionPreference = "Stop"

# Clear screen and show header
Clear-Host
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   FILE REGISTRY GENERATOR" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Interactive menu
Write-Host "Please configure the following options:" -ForegroundColor Yellow
Write-Host ""

# 1. Root Path
Write-Host "1. Root Directory Path" -ForegroundColor White
Write-Host "   (Press Enter to use current script directory)" -ForegroundColor Gray
$defaultRoot = $PSScriptRoot
Write-Host "   Default: $defaultRoot" -ForegroundColor DarkGray
$rootPathInput = Read-Host "   Enter path"
$RootPath = if ([string]::IsNullOrWhiteSpace($rootPathInput)) { $defaultRoot } else { $rootPathInput.Trim() }

# Validate root path
if (-not (Test-Path $RootPath)) {
    Write-Host "ERROR: Path does not exist: $RootPath" -ForegroundColor Red
    exit 1
}
Write-Host "   [OK] Using: $RootPath" -ForegroundColor Green
Write-Host ""

# 2. Output File Name
Write-Host "2. Output CSV File Name" -ForegroundColor White
Write-Host "   (Press Enter to use default)" -ForegroundColor Gray
Write-Host "   Default: file_registry.csv" -ForegroundColor DarkGray
$outputFileInput = Read-Host "   Enter filename"
$OutputFile = if ([string]::IsNullOrWhiteSpace($outputFileInput)) { "file_registry.csv" } else { $outputFileInput.Trim() }
if (-not $OutputFile.EndsWith(".csv")) {
    $OutputFile += ".csv"
}
Write-Host "   [OK] Using: $OutputFile" -ForegroundColor Green
Write-Host ""

# 3. Include File Content
Write-Host "3. Include File Content in CSV?" -ForegroundColor White
Write-Host "   (This can make the CSV very large!)" -ForegroundColor Yellow
Write-Host "   [Y]es / [N]o (default: No)" -ForegroundColor Gray
$includeContentInput = Read-Host "   Enter choice"
$IncludeContent = ($includeContentInput -eq "Y" -or $includeContentInput -eq "y" -or $includeContentInput -eq "Yes" -or $includeContentInput -eq "yes")
Write-Host "   [OK] Include Content: $(if ($IncludeContent) { 'Yes' } else { 'No' })" -ForegroundColor Green
Write-Host ""

# 4. Max Content Length (if including content)
$MaxContentLength = 10000
if ($IncludeContent) {
    Write-Host "4. Maximum Content Length (characters)" -ForegroundColor White
    Write-Host "   (Files larger than this will be truncated)" -ForegroundColor Gray
    Write-Host "   Default: 10000" -ForegroundColor DarkGray
    $maxLengthInput = Read-Host "   Enter max length"
    if (-not [string]::IsNullOrWhiteSpace($maxLengthInput)) {
        try {
            $parsedValue = [int]$maxLengthInput
            if ($parsedValue -gt 0) {
                $MaxContentLength = $parsedValue
                Write-Host "   [OK] Max Length: $MaxContentLength characters" -ForegroundColor Green
            } else {
                Write-Host "   [WARN] Number must be greater than 0, using default: 10000" -ForegroundColor Yellow
                $MaxContentLength = 10000
            }
        } catch {
            Write-Host "   [WARN] Invalid number, using default: 10000" -ForegroundColor Yellow
            $MaxContentLength = 10000
        }
    } else {
        Write-Host "   [OK] Using default: 10000 characters" -ForegroundColor Green
    }
    Write-Host ""
}

# 5. Include Folders
Write-Host "$(if ($IncludeContent) { '5' } else { '4' }). Include Folders in Registry?" -ForegroundColor White
Write-Host "   [Y]es / [N]o (default: Yes)" -ForegroundColor Gray
$includeFoldersInput = Read-Host "   Enter choice"
$IncludeFolders = if ([string]::IsNullOrWhiteSpace($includeFoldersInput)) { $true } else { ($includeFoldersInput -eq "Y" -or $includeFoldersInput -eq "y" -or $includeFoldersInput -eq "Yes" -or $includeFoldersInput -eq "yes") }
Write-Host "   [OK] Include Folders: $(if ($IncludeFolders) { 'Yes' } else { 'No' })" -ForegroundColor Green
Write-Host ""

# Generate output path
$outputPath = Join-Path $RootPath $OutputFile

# Show summary and confirm
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   CONFIGURATION SUMMARY" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Root Path:        $RootPath" -ForegroundColor Yellow
Write-Host "Output File:      $outputPath" -ForegroundColor Yellow
Write-Host "Include Content:  $(if ($IncludeContent) { 'Yes' } else { 'No' })" -ForegroundColor Yellow
if ($IncludeContent) {
    Write-Host "Max Content:      $MaxContentLength characters" -ForegroundColor Yellow
}
Write-Host "Include Folders:  $(if ($IncludeFolders) { 'Yes' } else { 'No' })" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press Enter to start processing, or Ctrl+C to cancel..." -ForegroundColor Gray
$null = Read-Host
Write-Host ""

# Initialize results array
$results = @()
$counter = 0
$uniqueId = 1

# Function to get file content (with safety checks)
function Get-FileContentRaw {
    param(
        [string]$FilePath,
        [int]$MaxLength = 10000
    )
    
    if (-not (Test-Path $FilePath)) {
        return ""
    }
    
    try {
        $item = Get-Item $FilePath -Force -ErrorAction SilentlyContinue
        if ($item.PSIsContainer) {
            return "[DIRECTORY]"
        }
        
        # Skip binary files (check by extension)
        $ext = [System.IO.Path]::GetExtension($FilePath).ToLower()
        $binaryExts = @('.exe', '.dll', '.bin', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', 
                        '.pdf', '.zip', '.rar', '.7z', '.tar', '.gz', '.mp3', '.mp4', '.avi', 
                        '.mov', '.wmv', '.flv', '.webm', '.ogg', '.wav', '.flac', '.aac',
                        '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.odt', '.ods', '.odp')
        
        if ($binaryExts -contains $ext) {
            return "[BINARY_FILE]"
        }
        
        # Try to read as text
        $content = Get-Content -Path $FilePath -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
        if ($null -eq $content) {
            return "[READ_ERROR]"
        }
        
        if ($content.Length -gt $MaxLength) {
            return $content.Substring(0, $MaxLength) + "...[TRUNCATED]"
        }
        
        return $content
    }
    catch {
        return "[ERROR: $($_.Exception.Message)]"
    }
}

# Function to check if item is hidden
function Test-IsHidden {
    param([System.IO.FileSystemInfo]$Item)
    
    if ($null -eq $Item) { return "No" }
    
    try {
        return if (($Item.Attributes -band [System.IO.FileAttributes]::Hidden) -eq [System.IO.FileAttributes]::Hidden) { "Yes" } else { "No" }
    }
    catch {
        return "Unknown"
    }
}

# Function to check if item is read-only
function Test-IsReadOnly {
    param([System.IO.FileSystemInfo]$Item)
    
    if ($null -eq $Item) { return "No" }
    
    try {
        return if (($Item.Attributes -band [System.IO.FileAttributes]::ReadOnly) -eq [System.IO.FileAttributes]::ReadOnly) { "Yes" } else { "No" }
    }
    catch {
        return "Unknown"
    }
}

Write-Host "Scanning directory tree..." -ForegroundColor Green

# Get all items (files and optionally folders)
$items = Get-ChildItem -Path $RootPath -Recurse -Force -ErrorAction SilentlyContinue | 
    Where-Object { 
        if ($IncludeFolders) {
            $true  # Include both files and folders
        } else {
            -not $_.PSIsContainer  # Only files
        }
    }

$totalItems = $items.Count
Write-Host "Found $totalItems items to process" -ForegroundColor Cyan
Write-Host ""

# Process each item
foreach ($item in $items) {
    $counter++
    
    if ($counter % 100 -eq 0) {
        Write-Progress -Activity "Processing files" -Status "Processing item $counter of $totalItems" -PercentComplete (($counter / $totalItems) * 100)
    }
    
    try {
        $isDirectory = $item.PSIsContainer
        $extension = if ($isDirectory) { "[FOLDER]" } else { [System.IO.Path]::GetExtension($item.Name) }
        
        # Get file content if requested
        $contentRaw = ""
        if ($IncludeContent -and -not $isDirectory) {
            $contentRaw = Get-FileContentRaw -FilePath $item.FullName -MaxLength $MaxContentLength
        }
        elseif ($isDirectory) {
            $contentRaw = "[DIRECTORY]"
        }
        
        # Create result object
        $result = [PSCustomObject]@{
            UniqueId = $uniqueId++
            FileFolderName = $item.Name
            FullPath = $item.FullName
            RelativePath = $item.FullName.Replace($RootPath, "").TrimStart('\', '/')
            FileContentRaw = $contentRaw
            Created = $item.CreationTime.ToString("yyyy-MM-dd HH:mm:ss")
            CreatedDate = $item.CreationTime.ToString("yyyy-MM-dd")
            CreatedTime = $item.CreationTime.ToString("HH:mm:ss")
            Updated = $item.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")
            UpdatedDate = $item.LastWriteTime.ToString("yyyy-MM-dd")
            UpdatedTime = $item.LastWriteTime.ToString("HH:mm:ss")
            Accessed = $item.LastAccessTime.ToString("yyyy-MM-dd HH:mm:ss")
            Extension = $extension
            Hidden = Test-IsHidden -Item $item
            ReadOnly = Test-IsReadOnly -Item $item
            IsDirectory = if ($isDirectory) { "Yes" } else { "No" }
            Size = if ($isDirectory) { 0 } else { $item.Length }
            SizeKB = if ($isDirectory) { 0 } else { [math]::Round($item.Length / 1KB, 2) }
            SizeMB = if ($isDirectory) { 0 } else { [math]::Round($item.Length / 1MB, 2) }
            ParentDirectory = $item.DirectoryName
            Depth = ($item.FullName.Replace($RootPath, "").Split([System.IO.Path]::DirectorySeparatorChar) | Where-Object { $_.Length -gt 0 }).Count
            Attributes = $item.Attributes.ToString()
        }
        
        $results += $result
    }
    catch {
        Write-Warning "Error processing $($item.FullName): $($_.Exception.Message)"
    }
}

Write-Progress -Activity "Processing files" -Completed

# Export to CSV
Write-Host "Exporting to CSV..." -ForegroundColor Green
$results | Export-Csv -Path $outputPath -NoTypeInformation -Encoding UTF8

Write-Host ""
Write-Host "=== SUMMARY ===" -ForegroundColor Magenta
Write-Host "Total items processed: $counter" -ForegroundColor Cyan
Write-Host "Output file: $outputPath" -ForegroundColor Green
Write-Host "File size: $([math]::Round((Get-Item $outputPath).Length / 1KB, 2)) KB" -ForegroundColor Yellow
Write-Host ""
Write-Host "Done!" -ForegroundColor Green

