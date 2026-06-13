# Temporarily disable LFS hooks by making them exit successfully
$hooks = @("post-commit", "post-checkout", "post-merge")
$hookDir = ".git\hooks"

foreach ($hook in $hooks) {
    $hookPath = Join-Path $hookDir $hook
    if (Test-Path $hookPath) {
        # Backup original
        Copy-Item $hookPath "$hookPath.backup" -ErrorAction SilentlyContinue
        # Replace with simple no-op
        @"
#!/bin/sh
# LFS hook disabled - exit successfully
exit 0
"@ | Out-File -FilePath $hookPath -Encoding ASCII -NoNewline
        Write-Host "Disabled $hook"
    }
}
Write-Host "LFS hooks disabled. To restore, delete the hook files and restore from .backup files"

