# Restore LFS hooks from backup
$hooks = @("post-commit", "post-checkout", "post-merge")
$hookDir = ".git\hooks"

foreach ($hook in $hooks) {
    $hookPath = Join-Path $hookDir $hook
    $backupPath = "$hookPath.backup"
    if (Test-Path $backupPath) {
        Copy-Item $backupPath $hookPath -Force
        Write-Host "Restored $hook"
    }
}
Write-Host "LFS hooks restored"

