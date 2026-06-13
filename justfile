# ── QiLabs Justfile ──────────────────────────────────────────────────
# Requires: https://just.systems  (install: scoop install just)
# Usage:    just <target>
# -----------------------------------------------------------------

# Default: list available commands
default:
    @just --list

# ── SETUP ─────────────────────────────────────────────────────────────
# Verify deps, install, create local data folders, migrate, seed, print URLs
setup:
    @echo "=== QiLabs Setup ==="
    @echo "Checking required tools..."
    node --version
    pnpm --version
    python --version
    @echo "Installing JS dependencies..."
    pnpm install
    @echo "Creating local data directories..."
    -mkdir C:\QiData\inbox
    -mkdir C:\QiData\staging
    -mkdir C:\QiData\reviewed
    -mkdir C:\QiData\failed
    -mkdir C:\QiData\manifests
    -mkdir C:\QiData\logs
    -mkdir C:\QiData\extracted_text
    -mkdir C:\QiData\embeddings_cache
    @echo "Setting up Python environment..."
    python -m venv python/.venv
    python/.venv/Scripts/pip install -r python/requirements.txt
    @echo "Running Supabase migrations..."
    -pnpm supabase db push
    @echo ""
    @echo "=== Setup complete ==="
    @echo "Admin portal: http://localhost:5173"
    @echo "Local API:    http://localhost:8000"
    @echo ""
    @echo "Next: just dev"

# ── DEV ───────────────────────────────────────────────────────────────
# Run admin portal + local API in dev mode
dev:
    @echo "=== Starting QiLabs Dev ==="
    pnpm --filter @qi/admin-portal dev

# Run everything in parallel (portal + python API)
dev-all:
    @echo "=== Starting all services ==="
    start /B pnpm --filter @qi/admin-portal dev
    start /B python/.venv/Scripts/python python/qiarchive/api/main.py
    @echo "Admin portal: http://localhost:5173"
    @echo "Python API:   http://localhost:8000"

# ── STATUS ────────────────────────────────────────────────────────────
# Check DB, storage, worker health, data dirs
status:
    @echo "=== QiLabs Status ==="
    @echo "Checking data directories..."
    @if exist C:\QiData\inbox (echo "[OK]  C:/QiData/inbox") else (echo "[MISSING] C:/QiData/inbox — run: just setup")
    @if exist C:\QiData\staging (echo "[OK]  C:/QiData/staging") else (echo "[MISSING] C:/QiData/staging")
    @if exist C:\QiData\reviewed (echo "[OK]  C:/QiData/reviewed") else (echo "[MISSING] C:/QiData/reviewed")
    @if exist C:\QiData\failed (echo "[OK]  C:/QiData/failed") else (echo "[MISSING] C:/QiData/failed")
    @echo ""
    @echo "Checking Python API..."
    -curl -s http://localhost:8000/health || echo "[OFFLINE] Python API not running — run: just dev-all"
    @echo ""
    @echo "Done. Check .env for SUPABASE and R2 credentials."

# ── INGEST ────────────────────────────────────────────────────────────
# Trigger a scan + ingest of C:/QiData/inbox/
ingest:
    @echo "=== Triggering Ingest ==="
    python/.venv/Scripts/python python/qiarchive/scan/scan.py --inbox C:\QiData\inbox

# ── REPAIR ────────────────────────────────────────────────────────────
# Run repair/reindex job on failed records
repair:
    @echo "=== Running Repair ==="
    python/.venv/Scripts/python python/qiarchive/repair/repair.py

# ── RESET ─────────────────────────────────────────────────────────────
# Clear local state (data dirs) — does NOT affect DB
reset:
    @echo "=== Resetting local data (does NOT touch DB) ==="
    -del /Q C:\QiData\staging\*
    -del /Q C:\QiData\logs\*
    @echo "Local staging and logs cleared."
    @echo "Run: just setup to re-create if needed."

# ── BUILD ─────────────────────────────────────────────────────────────
build:
    pnpm --filter @qi/admin-portal build

# ── LINT / TYPECHECK ──────────────────────────────────────────────────
lint:
    pnpm --filter @qi/admin-portal lint

typecheck:
    pnpm --filter @qi/admin-portal typecheck
