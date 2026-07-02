# QiLabs Toolbox Interactive Maintenance Menu
# Run from RUN_TOOLBOX_BUILDER.bat at toolbox root.

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ToolboxRoot = (Resolve-Path (Join-Path $ScriptDir "..")).Path
$ArchiveBase = Join-Path $ToolboxRoot "_archive"
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$SessionArchive = Join-Path $ArchiveBase "maintenance-$Stamp"
$LogDir = Join-Path $ArchiveBase "maintenance_logs"
$LogPath = Join-Path $LogDir "maintenance-$Stamp.log"

Set-Location $ToolboxRoot
New-Item -ItemType Directory -Force $LogDir | Out-Null

function Write-Line {
    param([string]$Message = "")
    Write-Host $Message
    Add-Content -Path $LogPath -Value $Message -Encoding UTF8
}

function Write-Title {
    Clear-Host
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "QiLabs Toolbox Interactive Builder / Cleaner" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "Root: $ToolboxRoot" -ForegroundColor Gray
    Write-Host "Log:  $LogPath" -ForegroundColor Gray
    Write-Host ""
}

function Pause-Menu {
    Write-Host ""
    Read-Host "Press Enter to continue"
}

function Ask-YesNo {
    param(
        [string]$Question,
        [bool]$DefaultYes = $false
    )
    $hint = if ($DefaultYes) { "Y/n" } else { "y/N" }
    while ($true) {
        $answer = Read-Host "$Question [$hint]"
        if ([string]::IsNullOrWhiteSpace($answer)) { return $DefaultYes }
        switch ($answer.Trim().ToLowerInvariant()) {
            "y" { return $true }
            "yes" { return $true }
            "n" { return $false }
            "no" { return $false }
            default { Write-Host "Please answer y or n." -ForegroundColor Yellow }
        }
    }
}

function Ensure-ArchiveFolder {
    if (-not (Test-Path $SessionArchive)) {
        New-Item -ItemType Directory -Force $SessionArchive | Out-Null
    }
}

function Move-ToSessionArchive {
    param([string]$PathToMove)
    if (-not (Test-Path $PathToMove)) { return }

    Ensure-ArchiveFolder
    $full = (Resolve-Path $PathToMove).Path
    $rel = $full.Replace($ToolboxRoot, "").TrimStart("\")
    $dest = Join-Path $SessionArchive $rel
    $destParent = Split-Path $dest -Parent
    New-Item -ItemType Directory -Force $destParent | Out-Null

    if (Test-Path $dest) {
        $dest = "$dest.moved-$Stamp"
    }

    Move-Item -LiteralPath $full -Destination $dest -Force
    Write-Line "  ARCHIVED: $rel"
}

function Stop-ToolboxProcesses {
    Write-Line "[process] Searching for old toolbox processes..."

    $names = @("QiLabsToolbox", "QiOne_Tools", "destroyer")
    foreach ($name in $names) {
        Get-Process -Name $name -ErrorAction SilentlyContinue | ForEach-Object {
            try {
                Write-Line "  Stopping $($_.ProcessName).exe PID $($_.Id)"
                Stop-Process -Id $_.Id -Force -ErrorAction Stop
            } catch {
                Write-Line "  WARN: Could not stop PID $($_.Id): $($_.Exception.Message)"
            }
        }
    }

    $escapedRoot = [Regex]::Escape($ToolboxRoot)
    $pyProcs = Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match "^(python|pythonw|py)\.exe$" -and
        $_.CommandLine -match $escapedRoot -and
        (
            $_.CommandLine -match "main_ui\.py" -or
            $_.CommandLine -match "toolbox_dynamic_ui\.py" -or
            $_.CommandLine -match "QiLabsToolbox" -or
            $_.CommandLine -match "build_toolbox_runtime" -or
            $_.CommandLine -match "interactive_toolbox_maintenance"
        ) -and
        $_.ProcessId -ne $PID
    }

    foreach ($proc in $pyProcs) {
        try {
            Write-Line "  Stopping toolbox Python PID $($proc.ProcessId)"
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop
        } catch {
            Write-Line "  WARN: Could not stop Python PID $($proc.ProcessId): $($_.Exception.Message)"
        }
    }

    Start-Sleep -Milliseconds 600
}

function Should-SkipCachePath {
    param([string]$FullName)
    $n = $FullName.Replace("/", "\")
    foreach ($part in @("\.venv\", "\venv\", "\node_modules\", "\_archive\", "\dist\", "\build\")) {
        if ($n.Contains($part)) { return $true }
    }
    return $false
}

function Clean-PythonRuntime {
    param([bool]$NormalizePluginInits = $true)

    Write-Line "[python] Cleaning Python runtime artifacts..."

    $cacheNames = @("__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache")
    $dirs = Get-ChildItem $ToolboxRoot -Recurse -Directory -Force -ErrorAction SilentlyContinue |
        Where-Object { $cacheNames -contains $_.Name -and -not (Should-SkipCachePath $_.FullName) } |
        Sort-Object FullName -Descending

    foreach ($dir in $dirs) {
        Write-Line "  Removing cache folder: $($dir.FullName.Replace($ToolboxRoot, '').TrimStart('\'))"
        Remove-Item -LiteralPath $dir.FullName -Recurse -Force -ErrorAction SilentlyContinue
    }

    foreach ($pattern in @("*.pyc", "*.pyo")) {
        Get-ChildItem $ToolboxRoot -Recurse -File -Force -Filter $pattern -ErrorAction SilentlyContinue |
            Where-Object { -not (Should-SkipCachePath $_.FullName) } |
            ForEach-Object {
                Write-Line "  Removing compiled file: $($_.FullName.Replace($ToolboxRoot, '').TrimStart('\'))"
                Remove-Item -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue
            }
    }

    if (-not $NormalizePluginInits) { return }

    $ToolsRoot = Join-Path $ToolboxRoot "tools"
    if (-not (Test-Path $ToolsRoot)) { return }

    Write-Line "[python] Checking risky plugin-root __init__.py files..."
    $initBackupRoot = Join-Path $SessionArchive "plugin_init_backups"

    $pluginInits = Get-ChildItem $ToolsRoot -Recurse -File -Filter "__init__.py" -ErrorAction SilentlyContinue |
        Where-Object {
            $rel = $_.FullName.Replace($ToolsRoot, "").TrimStart("\")
            $parts = $rel -split "\\"
            # Only tools\category\plugin\__init__.py. Do not touch deeper package inits.
            $parts.Count -eq 3 -and $parts[2] -eq "__init__.py"
        }

    foreach ($init in $pluginInits) {
        $text = Get-Content -LiteralPath $init.FullName -Raw -ErrorAction SilentlyContinue
        if ($null -eq $text) { $text = "" }

        $looksRisky = $text -match "from\s+\." -or $text -match "__all__" -or $text -match "import\s+"
        if (-not $looksRisky) { continue }

        Ensure-ArchiveFolder
        $rel = $init.FullName.Replace($ToolboxRoot, "").TrimStart("\")
        $dest = Join-Path $initBackupRoot $rel
        New-Item -ItemType Directory -Force (Split-Path $dest -Parent) | Out-Null
        Copy-Item -LiteralPath $init.FullName -Destination ($dest + ".bak") -Force

        $safeText = @"
# Intentionally quiet for QiLabs dynamic plugin host.
# Old contents backed up by RUN_TOOLBOX_BUILDER.bat under _archive.
# Plugins are loaded by manifest target file path, not by package auto-import.
"@
        Set-Content -LiteralPath $init.FullName -Value $safeText -Encoding UTF8
        Write-Line "  Neutralized risky plugin init: $rel"
    }
}

function Clean-BuildArtifacts {
    Write-Line "[build] Cleaning build artifacts..."
    foreach ($p in @("build", "dist")) {
        $full = Join-Path $ToolboxRoot $p
        if (Test-Path $full) {
            Write-Line "  Removing: $p"
            Remove-Item -LiteralPath $full -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
    Get-ChildItem $ToolboxRoot -File -Filter "*.spec" -ErrorAction SilentlyContinue | ForEach-Object {
        Write-Line "  Removing spec: $($_.Name)"
        Remove-Item -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue
    }
}

function Get-ClutterItems {
    $items = New-Object System.Collections.Generic.List[string]

    $rootNames = @(
        "_patch_backups",
        "_legacy_static_builder",
        "_legacy_toolbox_builder",
        "_legacy_reference",
        "_review_bundles_for_chatgpt",
        "extracted_toolbox",
        "_cleanup_archive",
        "payloads",
        "build",
        "dist"
    )

    foreach ($name in $rootNames) {
        $p = Join-Path $ToolboxRoot $name
        if (Test-Path $p) { $items.Add($p) }
    }

    $rootFilePatterns = @(
        "*.spec",
        "*.zip",
        "README_DYNAMIC_TOOLBOX*.md",
        "README_QIACCESS_BOOKMARKS_TOOL.md",
        "TOOLBOX_ARCHITECTURE_NOTES.md",
        "README_BUILDER_FIX.md",
        "build_QiOne_Tools.py",
        "build_qione.bat",
        "toolbox_dynamic_ui.py",
        "toolbox_autofix_report.json",
        "toolbox_plugin_audit.*",
        "plugin_migration_queue.csv",
        "make_toolbox_review_bundles.ps1",
        "cleanup_toolbox_folder.ps1",
        "file_version_info.txt.old",
        "main_ui.old.py"
    )

    foreach ($pattern in $rootFilePatterns) {
        Get-ChildItem $ToolboxRoot -File -Filter $pattern -ErrorAction SilentlyContinue | ForEach-Object {
            # Do not archive this active menu BAT.
            if ($_.Name -ne "RUN_TOOLBOX_BUILDER.bat") { $items.Add($_.FullName) }
        }
    }

    $pending = Join-Path $ToolboxRoot "tools\_pending"
    if (Test-Path $pending) { $items.Add($pending) }

    # Loose files directly inside tools root are usually salvage scripts, not active plugins.
    $toolsRoot = Join-Path $ToolboxRoot "tools"
    if (Test-Path $toolsRoot) {
        Get-ChildItem $toolsRoot -File -ErrorAction SilentlyContinue | Where-Object { $_.Name -ne "__init__.py" } | ForEach-Object {
            $items.Add($_.FullName)
        }
    }

    return $items | Sort-Object -Unique
}

function Show-CleanupPreview {
    Write-Line "[cleanup] Preview of clutter to archive:"
    $items = Get-ClutterItems
    if (-not $items -or $items.Count -eq 0) {
        Write-Line "  No obvious clutter found."
        return
    }
    foreach ($item in $items) {
        Write-Line "  WOULD ARCHIVE: $($item.Replace($ToolboxRoot, '').TrimStart('\'))"
    }
}

function Apply-ClutterCleanup {
    Write-Line "[cleanup] Applying safe clutter cleanup..."
    $items = Get-ClutterItems
    if (-not $items -or $items.Count -eq 0) {
        Write-Line "  No obvious clutter found."
        return
    }
    foreach ($item in $items) {
        if (Test-Path $item) { Move-ToSessionArchive $item }
    }
    Write-Line "[cleanup] Archive folder: $SessionArchive"
}

function Trim-HousekeepingRuntime {
    Write-Line "[housekeeping] Archiving runtime output folders, keeping app files..."
    $hk = Join-Path $ToolboxRoot "_housekeeping"
    if (-not (Test-Path $hk)) {
        Write-Line "  No _housekeeping folder found."
        return
    }

    foreach ($sub in @("backups", "logs", "plans", "reports", "summaries", "manifests")) {
        $folder = Join-Path $hk $sub
        if (-not (Test-Path $folder)) { continue }
        Get-ChildItem $folder -Force -ErrorAction SilentlyContinue | Where-Object { $_.Name -ne ".gitkeep" } | ForEach-Object {
            Move-ToSessionArchive $_.FullName
        }
    }
}

function Ensure-PyInstaller {
    Write-Line "[build] Checking PyInstaller..."
    & py -m PyInstaller --version *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Line "  PyInstaller not found. Installing..."
        & py -m pip install pyinstaller
        if ($LASTEXITCODE -ne 0) { throw "PyInstaller install failed." }
    } else {
        Write-Line "  PyInstaller is available."
    }
}

function Refresh-Registry {
    Write-Line "[registry] Refreshing toolbox registry and validation report..."
    $helper = Join-Path $ScriptDir "refresh_registry.py"
    if (-not (Test-Path $helper)) {
        Write-Line "  ERROR: Missing refresh_registry.py"
        return $false
    }
    & py $helper
    if ($LASTEXITCODE -ne 0) {
        Write-Line "  WARN: Registry refresh returned exit code $LASTEXITCODE"
        return $false
    }
    return $true
}

function Compile-Check {
    Write-Line "[check] Running compile check..."
    & py -m compileall main_ui.py toolbox_core core
    if ($LASTEXITCODE -ne 0) {
        Write-Line "  WARN: compileall reported errors. Check output above."
        return $false
    }
    Write-Line "  Compile check passed."
    return $true
}

function Build-Exe {
    Write-Line "[build] Starting EXE build..."
    Stop-ToolboxProcesses
    Clean-PythonRuntime -NormalizePluginInits $true
    Clean-BuildArtifacts
    Ensure-PyInstaller
    Refresh-Registry | Out-Null
    Compile-Check | Out-Null

    $args = @(
        "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name", "QiLabsToolbox"
    )

    if (Test-Path (Join-Path $ToolboxRoot "file_version_info.txt")) {
        $args += @("--version-file", "file_version_info.txt")
    }

    $args += @(
        "--collect-submodules", "toolbox_core",
        "--add-data", "toolbox_core;toolbox_core",
        "--add-data", "core;core",
        "main_ui.py"
    )

    Write-Line "[build] Running: py $($args -join ' ')"
    & py @args
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed." }

    $distExe = Join-Path $ToolboxRoot "dist\QiLabsToolbox.exe"
    $rootExe = Join-Path $ToolboxRoot "QiLabsToolbox.exe"
    if (-not (Test-Path $distExe)) { throw "Built EXE not found: $distExe" }
    Copy-Item $distExe $rootExe -Force
    Write-Line "[build] Built: $rootExe"
}

function Launch-Toolbox {
    $exe = Join-Path $ToolboxRoot "QiLabsToolbox.exe"
    if (Test-Path $exe) {
        Write-Line "[launch] Opening QiLabsToolbox.exe"
        Start-Process -FilePath $exe -WorkingDirectory $ToolboxRoot
    } else {
        Write-Line "[launch] EXE missing. Launching Python UI."
        Start-Process -FilePath "py" -ArgumentList "main_ui.py" -WorkingDirectory $ToolboxRoot
    }
}

function Install-BuilderShortcuts {
    Write-Line "[install] Repairing convenience builder files..."

    $buildBat = Join-Path $ToolboxRoot "build_qione_dynamic.bat"
    if (Test-Path $buildBat) {
        Copy-Item $buildBat "$buildBat.bak-$Stamp" -Force
    }

    $batText = @'
@echo off
setlocal
cd /d "%~dp0"

if exist "%~dp0RUN_TOOLBOX_BUILDER.bat" (
  call "%~dp0RUN_TOOLBOX_BUILDER.bat"
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_toolbox_runtime.ps1"
  pause
)
'@
    Set-Content -LiteralPath $buildBat -Value $batText -Encoding ASCII
    Write-Line "  Updated: build_qione_dynamic.bat now opens the interactive menu."
}

function Recommended-Repair {
    Write-Line "[recommended] Running repair: stop, cleanup, registry, compile..."
    Stop-ToolboxProcesses
    Clean-PythonRuntime -NormalizePluginInits $true
    Apply-ClutterCleanup
    if (Ask-YesNo "Also trim old housekeeping runtime plans/reports/backups?" $true) {
        Trim-HousekeepingRuntime
    }
    Refresh-Registry | Out-Null
    Compile-Check | Out-Null
    Write-Line "[recommended] Done."
}

function Full-Rebuild-And-Launch {
    Recommended-Repair
    Build-Exe
    if (Ask-YesNo "Launch toolbox now?" $true) { Launch-Toolbox }
}

function Show-RootSnapshot {
    Write-Line "[snapshot] Current top-level items:"
    Get-ChildItem $ToolboxRoot -Force | Sort-Object Name | ForEach-Object {
        $kind = if ($_.PSIsContainer) { "DIR " } else { "FILE" }
        Write-Line ("  {0}  {1}" -f $kind, $_.Name)
    }
}

function Show-Menu {
    Write-Title
    Write-Host "Choose one:" -ForegroundColor White
    Write-Host ""
    Write-Host "  1) Recommended repair only" -ForegroundColor Green
    Write-Host "     stop old processes, clean caches, neutralize risky plugin inits, refresh registry, compile check"
    Write-Host ""
    Write-Host "  2) Build EXE only" -ForegroundColor Green
    Write-Host "     includes process kill, cache cleanup, registry refresh, compile check, PyInstaller build"
    Write-Host ""
    Write-Host "  3) Full recommended repair + clean + rebuild + launch" -ForegroundColor Cyan
    Write-Host "     best option when the folder feels messy or plugins are acting weird"
    Write-Host ""
    Write-Host "  4) Preview folder clutter cleanup" -ForegroundColor Yellow
    Write-Host "  5) Apply folder clutter cleanup" -ForegroundColor Yellow
    Write-Host "  6) Clean Python caches and risky plugin __init__.py only" -ForegroundColor Yellow
    Write-Host "  7) Refresh registry / validation report only" -ForegroundColor Yellow
    Write-Host "  8) Launch toolbox" -ForegroundColor Yellow
    Write-Host "  9) Install/repair convenience builder BAT" -ForegroundColor Yellow
    Write-Host "  S) Show root snapshot" -ForegroundColor Gray
    Write-Host "  Q) Quit" -ForegroundColor Gray
    Write-Host ""
}

while ($true) {
    try {
        Show-Menu
        $choice = Read-Host "Selection"
        switch ($choice.Trim().ToLowerInvariant()) {
            "1" { Recommended-Repair; Pause-Menu }
            "2" { Build-Exe; if (Ask-YesNo "Launch toolbox now?" $true) { Launch-Toolbox }; Pause-Menu }
            "3" { Full-Rebuild-And-Launch; Pause-Menu }
            "4" { Show-CleanupPreview; Pause-Menu }
            "5" { if (Ask-YesNo "Archive the listed clutter now?" $false) { Apply-ClutterCleanup }; Pause-Menu }
            "6" { Stop-ToolboxProcesses; Clean-PythonRuntime -NormalizePluginInits $true; Pause-Menu }
            "7" { Refresh-Registry | Out-Null; Pause-Menu }
            "8" { Launch-Toolbox; Pause-Menu }
            "9" { Install-BuilderShortcuts; Pause-Menu }
            "s" { Show-RootSnapshot; Pause-Menu }
            "q" { break }
            "quit" { break }
            default { Write-Host "Unknown option." -ForegroundColor Yellow; Start-Sleep -Seconds 1 }
        }
    }
    catch {
        Write-Host "" 
        Write-Host "ERROR:" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
        Add-Content -Path $LogPath -Value ("ERROR: " + $_.Exception.ToString()) -Encoding UTF8
        Pause-Menu
    }
}

Write-Host ""
Write-Host "Done. Log saved to:" -ForegroundColor Cyan
Write-Host $LogPath -ForegroundColor Gray
