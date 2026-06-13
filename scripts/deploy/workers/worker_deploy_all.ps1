<#
QiOS - Deploy All Workers (v1)

- Installs deps per worker (if package.json exists)
- Runs wrangler deploy in each worker folder
- Stops on failure
- Assumes you already set secrets at least once per worker:
    npx wrangler secret put SUPABASE_URL
    npx wrangler secret put SUPABASE_SERVICE_ROLE_KEY
    npx wrangler secret put OPENAI_API_KEY   (for embedder/router if needed)

Run from QiOS_v1 root:
    powershell -ExecutionPolicy Bypass -File tools\deploy_all_workers.ps1
#>

$ErrorActionPreference = "Stop"

# ---- CONFIG ----

# Put these in the order the pipeline expects to light up.
# Only Cloudflare Workers (must have wrangler.toml)
$workers = @(
  "workers\orchestrator",
  "workers\ingestion",
  "workers\semantic_router",
  "workers\embedder",
  "workers\metadata_naming",
  "workers\self_heal"
)
# Note: readme_autogen and linter are Python scripts, not Cloudflare Workers

# Optional: if you want to skip deps install each run
$INSTALL_DEPS = $true

# ---- HELPERS ----

function Run-Step($msg, $cmd) {
  Write-Host "`n==> $msg" -ForegroundColor Cyan
  Write-Host "    $cmd" -ForegroundColor DarkGray
  iex $cmd
}

function Ensure-Exists($path) {
  if (!(Test-Path $path)) {
    throw "Missing path: $path"
  }
}

function Is-CloudflareWorker($path) {
  return (Test-Path (Join-Path $path "wrangler.toml"))
}

# ---- START ----

$root = Get-Location

Write-Host "`nQiOS Deploy All Workers: starting from $root" -ForegroundColor Green

foreach ($w in $workers) {
  $workerPath = Join-Path $root $w
  Ensure-Exists $workerPath

  # Skip if not a Cloudflare Worker (no wrangler.toml)
  if (!(Is-CloudflareWorker $workerPath)) {
    Write-Host "`n------------------------------" -ForegroundColor DarkGray
    Write-Host "Skipping: $w (not a Cloudflare Worker - no wrangler.toml)" -ForegroundColor DarkYellow
    continue
  }

  Write-Host "`n------------------------------" -ForegroundColor DarkGray
  Write-Host "Worker: $w" -ForegroundColor Yellow
  Set-Location $workerPath

  if ($INSTALL_DEPS -and (Test-Path "package.json")) {
    Run-Step "npm install" "npm install"
  } else {
    Write-Host "Skipping npm install (no package.json or INSTALL_DEPS=false)" -ForegroundColor DarkYellow
  }

  # Deploy
  Run-Step "wrangler deploy" "npx wrangler deploy"

  Write-Host "Deployed: $w" -ForegroundColor Green
}

Set-Location $root

Write-Host "`nAll workers deployed successfully." -ForegroundColor Green
