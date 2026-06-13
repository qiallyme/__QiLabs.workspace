#!/usr/bin/env python3
import os, sys, json, csv, re, time, subprocess, shutil, importlib.util
from pathlib import Path
from datetime import datetime

# ----------------- tiny YAML loader (same style as qi_codex_tool) -----------------
def load_yaml(path: Path) -> dict:
    import ast
    data = {}
    stack = [(-1, data)]
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            # Remove inline comments (but preserve # in quoted strings)
            if "#" in line:
                # Simple check: if # is after a quote, it's part of the value
                # Otherwise, strip everything after #
                parts = line.split("#", 1)
                if len(parts) == 2:
                    # Check if # is inside quotes (rough heuristic)
                    before_hash = parts[0]
                    quote_count = before_hash.count('"') + before_hash.count("'")
                    if quote_count % 2 == 0:  # Even = not inside quotes
                        line = parts[0].rstrip()
            if not line.strip() or line.strip().startswith("#"):
                continue
            indent = len(line) - len(line.lstrip(" "))
            key, sep, val = line.strip().partition(":")
            if not sep:
                continue
            while stack and indent <= stack[-1][0]:
                stack.pop()
            parent = stack[-1][1]
            val = val.strip()
            if val == "":
                parent[key] = {}
                stack.append((indent, parent[key]))
            else:
                if val.startswith("[") and val.endswith("]"):
                    try:
                        parent[key] = ast.literal_eval(val)
                    except Exception:
                        parent[key] = [v.strip() for v in val.strip("[]").split(",") if v.strip()]
                elif val.lower() in ("true","false"):
                    parent[key] = (val.lower() == "true")
                else:
                    parent[key] = val.strip('"').strip("'")
    return data

def slugify(s: str) -> str:
    s = re.sub(r"[^\w\s-]", "", str(s)).strip().lower()
    s = re.sub(r"[\s_-]+", "-", s)
    return s or "untitled"

def has_important_filename_pattern(filename: str) -> bool:
    """Check if filename has important patterns that should be preserved."""
    stem = Path(filename).stem.lower()
    # QiDecimal pattern: X.XX.XX-XX or X.XX.XX.XX
    if re.match(r"^\d+\.\d+\.\d+[.-]\d+", stem):
        return True
    # Date prefix: YYYY-MM-DD or YYYYMMDD
    if re.match(r"^\d{4}[.-]\d{2}[.-]\d{2}", stem) or re.match(r"^\d{8}", stem):
        return True
    # Numbered prefix for ordering: NN_ or 0N_
    if re.match(r"^\d{1,3}[_-]", stem):
        return True
    return False

def fm_parse(text: str):
    if not text.startswith("---"):
        return {}, text
    parts = text.split("\n")
    if parts[0].strip() != "---":
        return {}, text
    try:
        end_idx = 1 + parts[1:].index("---")
    except ValueError:
        return {}, text
    block = "\n".join(parts[1:end_idx])
    body  = "\n".join(parts[end_idx+1:])
    fm = {}
    for ln in block.splitlines():
        if not ln.strip() or ln.strip().startswith("#"): continue
        k, sep, v = ln.partition(":")
        if not sep: continue
        k = k.strip()
        v = v.strip()
        if v.startswith("[") and v.endswith("]"):
            v = [x.strip().strip("'").strip('"') for x in v[1:-1].split(",") if x.strip()]
        else:
            v = v.strip().strip("'").strip('"')
        fm[k] = v
    return fm, body

def fm_dump(fm: dict) -> str:
    out = ["---"]
    for k, v in fm.items():
        if isinstance(v, list):
            out.append(f"{k}: [{', '.join(str(x) for x in v)}]")
        else:
            s = str(v)
            if any(ch in s for ch in [":","{","}","[","]",",","#","&","*","!","|",">","'","\"","%","@","`"]) or s.strip()!=s:
                s = "'" + s.replace("'", "''") + "'"
            out.append(f"{k}: {s}")
    out.append("---\n")
    return "\n".join(out)

# ----------------- dependency checking -----------------
def _module_ok(name: str) -> bool:
    return importlib.util.find_spec(name) is not None

def _bin_ok(cmd: str) -> bool:
    return shutil.which(cmd) is not None

def deps_check(cfg, logger) -> dict:
    """Check Python modules + binaries (Tesseract/Poppler)."""
    results = {
        "pdf2image": _module_ok("pdf2image"),
        "PIL(Pillow)": _module_ok("PIL"),
        "pytesseract": _module_ok("pytesseract"),
        "tesseract": _bin_ok("tesseract"),
        "poppler(pdftoppm)": _bin_ok("pdftoppm"),
    }

    # If poppler not on PATH, allow configured poppler_path
    poppler_path = (cfg.get("inbox", {}).get("ocr", {}) or {}).get("poppler_path", "")
    if not results["poppler(pdftoppm)"] and poppler_path:
        # Try executing pdftoppm from the given folder
        candidate = str(Path(poppler_path) / ("pdftoppm.exe" if os.name == "nt" else "pdftoppm"))
        try:
            subprocess.run([candidate, "-h"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=2)
            results["poppler(pdftoppm)"] = True
        except Exception:
            pass

    # Log
    logger.write("🔎 Dependency check:")
    for k, ok in results.items():
        logger.write(f"  - {k}: {'✅' if ok else '❌'}")

    # Helpful hints
    if not results["tesseract"]:
        logger.write("   → Install Tesseract and add it to PATH (Windows: UB-Mannheim build).")
    if not results["poppler(pdftoppm)"]:
        logger.write("   → Install Poppler and add its bin to PATH or set inbox.ocr.poppler_path.")

    return results

# ----------------- logging/locking -----------------
def now_iso():
    return datetime.now().isoformat(timespec="seconds")

class Logger:
    def __init__(self, log_dir: Path):
        log_dir.mkdir(parents=True, exist_ok=True)
        self.fp = log_dir / f"housekeeper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    def write(self, msg):
        line = f"[{now_iso()}] {msg}"
        # Safe print: handle Unicode encoding errors on Windows console
        try:
            print(line)
        except UnicodeEncodeError:
            # Fallback: replace problematic characters
            safe_line = line.encode('ascii', 'replace').decode('ascii')
            print(safe_line)
        with self.fp.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

class Lock:
    def __init__(self, path: Path):
        self.path = path
    def acquire(self):
        if self.path.exists():
            raise RuntimeError("Another housekeeping run is in progress.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(now_iso(), encoding="utf-8")
    def release(self):
        try: self.path.unlink()
        except FileNotFoundError: pass

# ----------------- steps -----------------
def run_qicodex(cfg, logger, counters):
    if not cfg.get("enabled", True):
        return
    tool = Path("7_Tools/7.10_python/qi_codex_tool/qi_codex_tool.py")
    conf = cfg["config"]
    if not tool.exists():
        logger.write("⚠️ qi_codex_tool not found; skipping Codex steps.")
        return
    logger.write("🔁 Codex: sync")
    subprocess.run([sys.executable, str(tool), "--config", conf, "sync"], check=False)
    logger.write("🧱 Codex: index")
    subprocess.run([sys.executable, str(tool), "--config", conf, "index"], check=False)
    logger.write("🧪 Codex: validate")
    result = subprocess.run([sys.executable, str(tool), "--config", conf, "validate", "--force"], check=False)
    # Rough validation count (increment per validation run)
    counters["validated"] += 1
    # Refresh Codex index documentation
    update_codex_index(logger)

def update_codex_index(logger):
    """Update QiCodex_Index.md after codex changes."""
    tool = Path("7_Tools/7.10_python/qi_codex_tool/qi_codex_tool.py")
    if tool.exists():
        subprocess.run([sys.executable, str(tool), "index"], check=False)
        logger.write("✅ QiCodex_Index.md refreshed.")

def process_inbox(cfg, logger, counters, dry_run=False, deps_ok=True):
    if not cfg.get("enabled", True):
        return
    inbox = Path(cfg["path"])
    if not inbox.exists():
        logger.write(f"ℹ️ Inbox not found: {inbox}")
        return

    # CSV → MD
    csv_cfg = cfg.get("csv", {})
    if csv_cfg.get("enabled", True):
        mapping_ref = csv_cfg.get("mapping_preset")
        out_dir = Path(csv_cfg.get("out_dir", "3_QiKb/3.10_Inbox"))
        out_dir.mkdir(parents=True, exist_ok=True)
        preset_path, preset_key = None, None
        if mapping_ref and "::" in mapping_ref:
            preset_path, preset_key = mapping_ref.split("::", 1)

        for csv_file in inbox.glob("*.csv"):
            logger.write(f"📄 CSV import: {csv_file.name}")
            cfg_json = None
            if preset_path and Path(preset_path).exists():
                # extract that preset into a temp JSON the csv_to_md script expects
                mapping_yaml = load_yaml(Path(preset_path))
                preset = mapping_yaml.get("presets", {}).get(preset_key, {})
                mapping = preset.get("mapping", {})
                tmp = Path(".housekeeping/tmp_mapping.json")
                tmp.parent.mkdir(parents=True, exist_ok=True)
                tmp.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
                cfg_json = tmp

            cmd = [
                sys.executable, "7_Tools/7.10_python/csv_to_md/csv_to_md.py",
                "--csv", str(csv_file),
                "--out", str(out_dir)
            ]
            if cfg_json: cmd += ["--config", str(cfg_json)]
            if dry_run:  logger.write(f"DRY: {' '.join(cmd)}")
            else:        
                subprocess.run(cmd, check=False)
                # Count CSV rows (rough estimate)
                try:
                    with csv_file.open("r", encoding="utf-8", errors="ignore") as f:
                        reader = csv.reader(f)
                        counters["csv_rows"] += sum(1 for _ in reader) - 1  # subtract header
                except Exception:
                    pass

    run_ocr_on_pdfs(cfg, logger, counters, dry_run=dry_run, deps_ok=deps_ok)

def run_ocr_on_pdfs(inbox_cfg, logger, counters, dry_run=False, deps_ok=True):
    ocfg = inbox_cfg.get("ocr", {})
    if not ocfg.get("enabled", False) or not deps_ok:
        if not deps_ok:
            logger.write("⚠️ Skipping OCR (deps check failed).")
        return

    inbox = Path(inbox_cfg["path"])
    pdfs = list(inbox.rglob("*.pdf"))
    if not pdfs:
        return

    ocr_script = Path("7_Tools/7.10_python/ocr/pdf_to_text_via_images.py")
    if not ocr_script.exists():
        logger.write("⚠️ OCR script missing: 7_Tools/7.10_python/ocr/pdf_to_text_via_images.py")
        return

    dpi    = str(ocfg.get("dpi", 300))
    lang   = ocfg.get("lang", "eng")
    as_md  = bool(ocfg.get("as_markdown", True))
    max_pg = int(ocfg.get("max_pages", 0))
    poppl  = ocfg.get("poppler_path", "")

    for pdf in pdfs:
        out = pdf.with_suffix(".md") if as_md else pdf.with_suffix(".txt")
        cmd = [sys.executable, str(ocr_script), str(pdf), "-o", str(out), "--dpi", dpi, "--lang", lang]
        if not as_md:
            cmd.append("--plain-text")
        if max_pg > 0:
            cmd += ["--max-pages", str(max_pg)]
        if poppl:
            cmd += ["--poppler-path", poppl]

        logger.write(f"🧾 OCR: {pdf.name} → {out.name}")
        if dry_run:
            logger.write("DRY: " + " ".join(cmd))
        else:
            subprocess.run(cmd, check=False)
            counters["ocr_pages"] += max_pg if max_pg > 0 else 1


def normalize_and_route(route_cfg, naming_cfg, logger, counters, dry_run=False):
    if not route_cfg.get("enabled", True):
        return
    # scan for md files in common places (inbox + knowledge areas)
    roots = ["3_QiKb", "2_QsKb", "4_Clients", "5_Apps", "6_Data", "7_Tools"]
    candidates = []
    for r in roots:
        p = Path(r)
        if p.exists():
            candidates += list(p.rglob("*.md"))
    # also check temp inbox target
    p = Path("3_QiKb/3.10_Inbox")
    if p.exists(): candidates += list(p.rglob("*.md"))

    moved = 0
    for fp in candidates:
        try:
            txt = fp.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        fm, body = fm_parse(txt)
        if not fm: 
            continue

        # Enforce slug from title if requested (only update front matter, never rename files)
        # Filenames with important patterns (QiDecimal, dates, ordering prefixes) are preserved
        if naming_cfg.get("enabled", True) and naming_cfg.get("enforce_slug_from_title", True):
            if fm.get("title"):
                expected_slug = slugify(fm["title"])
                if fm.get("slug") != expected_slug:
                    fm["slug"] = expected_slug
                    new_txt = fm_dump(fm) + body
                    if dry_run:
                        logger.write(f"DRY: normalize slug {fp.name} (front matter only: {expected_slug})")
                    else:
                        fp.write_text(new_txt, encoding="utf-8")
                    counters["slugs"] = counters.get("slugs", 0) + 1

        # Decide destination by realm
        realm = fm.get("realm")
        dest_root = route_cfg.get("by_realm", {}).get(realm)
        if not realm or not dest_root:
            continue
        dest_dir = Path(dest_root)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / fp.name
        if dest.resolve() == fp.resolve():
            continue

        if dry_run:
            logger.write(f"DRY: move {fp} → {dest}")
        else:
            # ensure unique name if exists
            target = dest
            i = 2
            while target.exists():
                target = dest_dir / f"{dest.stem}-{i}{dest.suffix}"
                i += 1
            shutil.move(str(fp), str(target))
            moved += 1
            counters["moved"] = counters.get("moved", 0) + 1
    logger.write(f"🚚 routed {moved} files.")

def run_autoname(naming_cfg, logger):
    if not naming_cfg.get("enabled", True): return
    auto = naming_cfg.get("autoname", {})
    if not auto.get("enabled", False): return
    args = [
        sys.executable, "qd_autoname.py",
        "--base-dir", auto.get("base_dir", "."),
        "--index", auto.get("index", "meta/QiIndex.csv"),
    ]
    if auto.get("write", False):
        args.append("--write")
    logger.write("🔖 qd_autoname: " + " ".join(args))
    subprocess.run(args, check=False)

def run_validate_again(logger, counters):
    tool = Path("7_Tools/7.10_python/qi_codex_tool/qi_codex_tool.py")
    conf = "1_QiEos/1.50_Meta/metadata/qi_codex.config.yaml"
    if tool.exists():
        logger.write("🧪 post-route validate")
        subprocess.run([sys.executable, str(tool), "--config", conf, "validate"], check=False)
        counters["validated"] += 1

def run_legacy_organizer(post_cfg, logger):
    if not post_cfg.get("legacy_organizer", False):
        return
    cmd = [sys.executable, "organize_all_inbox.py"]
    logger.write("♻️ legacy organize_all_inbox")
    subprocess.run(cmd, check=False)

def run_backfill(cfg, logger):
    if not cfg.get("enabled", False):
        return
    backfill_script = Path("7_Tools/7.10_python/qi_backfill.py")
    if not backfill_script.exists():
        logger.write("⚠️ Backfill script missing: 7_Tools/7.10_python/qi_backfill.py")
        return
    logger.write("🔄 Backfill: titles, slugs, qi_decimal")
    subprocess.run([sys.executable, str(backfill_script)], check=False)

def run_large_file_audit(logger):
    audit_script = Path("7_Tools/7.10_python/large_file_audit.py")
    if not audit_script.exists():
        return
    logger.write("📊 Large file audit")
    result = subprocess.run([sys.executable, str(audit_script)], capture_output=True, text=True, check=False)
    if result.returncode == 0:
        logger.write(result.stdout.strip())
    return result.returncode == 0

def update_dashboard(counters: dict, deps: dict):
    dash = Path("STATUS_DASHBOARD.md")
    ts = datetime.now().isoformat(timespec="seconds")
    dep_line = ", ".join([f"{k}:{'OK' if v else 'MISS'}" for k,v in deps.items()])
    
    # Read large file audit if available
    large_files = []
    large_file_count = 0
    audit_file = Path(".housekeeping/large_files.json")
    if audit_file.exists():
        try:
            import json
            large_files = json.loads(audit_file.read_text(encoding="utf-8"))
            large_file_count = len(large_files)
        except Exception:
            pass
    
    lines = [
        "---",
        "title: Housekeeping Status",
        "realm: 2_QsKb",
        "privacy: shared",
        "---",
        "# 🧹 Housekeeping Status",
        f"**Latest Run:** {ts}  ",
        "**Mode:** normal  ",
        "**Lock:** released",
        "",
        "## Dependencies",
        f"{dep_line}",
        "",
        "## Counters",
        f"- Notes validated: {counters.get('validated', 0)}",
        f"- Slugs normalized: {counters.get('slugs', 0)}",
        f"- Moved (routed): {counters.get('moved', 0)}",
        f"- CSV rows imported: {counters.get('csv_rows', 0)}",
        f"- OCR pages: {counters.get('ocr_pages', 0)}",
        f"- Errors: {counters.get('errors', 0)}",
        "",
        "## Large Files",
        f"- Files ≥50 MB: {large_file_count}",
        "",
        "## Last Log",
        "```\n(see .housekeeping/logs/...)\n```",
        "",
        "## Policy Snapshot",
        "- Inbox: `2_QsKb/2.00_Inbox` (personal only)",
        "- Business/Client routing requires: `realm: 3_QiKb|4_Clients` **and** `privacy: shared|public`",
        "- Git LFS: Auto-tracks files ≥80MB, blocks ≥100MB",
    ]
    dash.write_text("\n".join(lines), encoding="utf-8")

def main():
    import argparse
    ap = argparse.ArgumentParser(description="Qi Housekeeper")
    ap.add_argument("--config", default="housekeeping.yaml")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfg = load_yaml(Path(args.config))
    logs_dir = Path(cfg.get("logs_dir", ".housekeeping/logs"))
    lockfile = Path(cfg.get("lockfile", ".housekeeping/housekeeper.lock"))

    logger = Logger(logs_dir)
    lock = Lock(lockfile)
    # Initialize counters and deps before steps run
    counters = {"validated": 0, "slugs": 0, "moved": 0, "csv_rows": 0, "ocr_pages": 0, "errors": 0}
    deps = {"pdf2image": False, "PIL(Pillow)": False, "pytesseract": False, "tesseract": False, "poppler(pdftoppm)": False}

    try:
        lock.acquire()
        logger.write("🏁 Housekeeping start")
        # Dependency check
        deps = deps_check(cfg, logger)
        deps_ok = all(deps.values())
        # 1) Codex
        run_qicodex(cfg.get("codex", {}), logger, counters)
        # 2) Inbox
        process_inbox(cfg.get("inbox", {}), logger, counters, dry_run=args.dry_run, deps_ok=deps_ok)
        # 3) Normalize & route
        normalize_and_route(cfg.get("routing", {}), cfg.get("naming", {}), logger, counters, dry_run=args.dry_run)
        # 4) Backfill (titles, slugs, qi_decimal)
        if cfg.get("backfill", {}).get("enabled", False):
            run_backfill(cfg.get("backfill", {}), logger)
            # Refresh Codex index after backfill (may have added new entries)
            update_codex_index(logger)
        # 5) Large file audit
        run_large_file_audit(logger)
        # 6) Post-validate
        if cfg.get("validate", {}).get("enabled", True):
            run_validate_again(logger, counters)
        logger.write("✅ Housekeeping complete")
    except Exception as e:
        logger.write(f"❌ Error: {e}")
        counters["errors"] = counters.get("errors", 0) + 1
        sys.exit(1)
    finally:
        update_dashboard(counters, deps)
        lock.release()

if __name__ == "__main__":
    main()
