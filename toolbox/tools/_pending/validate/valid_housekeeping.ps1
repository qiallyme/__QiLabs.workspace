Param(
  [switch]$DryRun,
  [switch]$Backfill
)

if ($Backfill) {
  Write-Host "🔄 Running backfill..."
  python 7_Tools/7.10_python/qi_backfill.py
  python 7_Tools/7.10_python/qi_codex_tool/qi_codex_tool.py index
  exit $LASTEXITCODE
}

$Script = "housekeeper.py"
$Args = @()
if ($DryRun) { $Args += "--dry-run" }

Write-Host "🏁 Housekeeping start..."
python $Script @Args
$exit = $LASTEXITCODE
if ($exit -eq 0) {
  Write-Host "✅ Housekeeping complete"
} else {
  Write-Host "❌ Housekeeping failed with exit code $exit"
  exit $exit
}
