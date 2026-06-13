# install_git_hooks.ps1
# Installs a safe pre-commit hook that runs docs compiler in --check mode only.
# Run from repo root.

param(
    [string]$RepoRoot = "C:\QiLabs",
    [string]$Target = "C:\QiLabs\00_QiAccess\docs"
)

$ErrorActionPreference = "Stop"

$gitDir = Join-Path $RepoRoot ".git"
$hooksDir = Join-Path $gitDir "hooks"
$hookPath = Join-Path $hooksDir "pre-commit"

if (!(Test-Path $gitDir)) {
    throw "No .git folder found at $gitDir"
}

if (!(Test-Path $hooksDir)) {
    New-Item -ItemType Directory -Path $hooksDir | Out-Null
}

$hook = @"
#!/bin/sh
echo "Running QiLabs docs compiler check..."
python scripts/docs_build/sys_docs_compiler.py --root "$RepoRoot" --target "$Target" --check
status=`$?
if [ `$status -ne 0 ]; then
  echo "Docs check failed. Fix docs issues or commit with --no-verify if you intentionally need to bypass."
  exit `$status
fi
"@

Set-Content -Path $hookPath -Value $hook -Encoding ASCII
Write-Host "Installed pre-commit docs check hook: $hookPath"
