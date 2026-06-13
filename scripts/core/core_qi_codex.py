#!/usr/bin/env python3
import csv, json, re, sys, argparse, os, io
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# ------------------------- Minimal YAML loader (no third-party deps) -------------------------
def load_yaml(path: Path) -> dict:
    """
    Extremely small YAML reader for our simple config.
    Accepts key: value, key: [list], and simple nested maps.
    If you want full YAML, switch to PyYAML, but we're keeping it dependency-free for now.
    """
    import ast
    data = {}
    stack = [(-1, data)]
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip() or line.strip().startswith("#"):
                continue
            indent = len(line) - len(line.lstrip(" "))
            key, sep, val = line.strip().partition(":")
            if not sep:
                continue
            # unwind stack
            while stack and indent <= stack[-1][0]:
                stack.pop()
            parent = stack[-1][1]
            val = val.strip()
            if val == "":
                # start of nested dict
                parent[key] = {}
                stack.append((indent, parent[key]))
            else:
                # try parse list or simple scalar
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

# ------------------------- Utilities -------------------------
def read_csv(fp: Path) -> List[Dict[str, str]]:
    with fp.open("r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        return list(r), (r.fieldnames or [])

def write_csv(fp: Path, rows: List[Dict[str, str]], fieldnames: List[str]):
    fp.parent.mkdir(parents=True, exist_ok=True)
    with fp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow(row)

def fetch_to_file(url: str, dest: Path):
    import urllib.request
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as resp:
        data = resp.read()
    dest.write_bytes(data)

def slugify(text: str, max_len: int = 120) -> str:
    s = re.sub(r"[^\w\s-]", "", str(text), flags=re.UNICODE).strip().lower()
    s = re.sub(r"[\s_-]+", "-", s)
    return (s[:max_len] or "untitled")

def fm_parse(text: str) -> (dict, str):
    """
    Parse YAML-like front matter at top of file: ---\n...\n---\n
    Returns (fm_dict, content_without_fm)
    """
    if not text.startswith("---"):
        return {}, text
    parts = text.split("\n")
    if len(parts) < 3:
        return {}, text
    if parts[0].strip() != "---":
        return {}, text
    # find closing ---
    try:
        end_idx = 1 + parts[1:].index("---")
    except ValueError:
        return {}, text
    block = "\n".join(parts[1:end_idx])
    body = "\n".join(parts[end_idx+1:])
    # naive parse: key: value / key: [list]
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
            out.append(f"{k}: [{', '.join(str(x).replace(']', '').replace('[','') for x in v)}]")
        else:
            s = str(v)
            # quote if needed
            if any(ch in s for ch in [":","{","}","[","]",",","#","&","*","!","|",">","'","\"","%","@","`"]) or s.strip()!=s:
                s = "'" + s.replace("'", "''") + "'"
            out.append(f"{k}: {s}")
    out.append("---\n")
    return "\n".join(out)

def ensure_date_iso(dt: Optional[str]) -> Optional[str]:
    if not dt: return None
    txt = str(dt).strip()
    fmts = ["%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S"]
    for f in fmts:
        try:
            return datetime.strptime(txt, f).isoformat()
        except Exception:
            pass
    if re.match(r"^\d{4}-\d{2}-\d{2}", txt):
        return txt
    return txt

# ------------------------- QiDecimal helpers -------------------------
def parse_qidec(q: str):
    # AAA.BB.CC-SS.TYPE
    m = re.match(r"^(\d{1,3}(?:\.\d{1,3}){2})-(\d{1,3})\.([A-Za-z0-9]+)$", q or "")
    if not m:
        return None
    return {"prefix": m.group(1), "seq": int(m.group(2)), "type": m.group(3)}

def next_qidec(prefix: str, codex_rows: List[Dict[str,str]], pad_seq: int = 2, typ: str = "SYS"):
    max_seq = 0
    for r in codex_rows:
        qi = (r.get("QiDecimal") or "").strip()
        p = parse_qidec(qi)
        if p and p["prefix"] == prefix:
            max_seq = max(max_seq, p["seq"])
    new_seq = max_seq + 1
    return f"{prefix}-{str(new_seq).zfill(pad_seq)}.{typ}"

# ------------------------- Commands -------------------------
def cmd_sync(args, cfg):
    url = cfg["qi_codex"]["sheet_csv_url"]
    local_csv = Path(cfg["qi_codex"]["local_csv"])
    fetch_to_file(url, local_csv)
    print(f"Synced sheet → {local_csv}")

def cmd_index(args, cfg):
    local_csv = Path(cfg["qi_codex"]["local_csv"])
    rows, headers = read_csv(local_csv)
    idx_cols = cfg["qi_codex"]["index"]["columns"]
    group_by = cfg["qi_codex"]["index"].get("group_by")
    md_path = Path(cfg["qi_codex"]["local_md_index"])

    # render table, optionally grouped
    out = []
    out.append("---")
    out.append("title: QiCodex Index")
    out.append("realm: 1_QiEos")
    out.append("privacy: shared")
    out.append("---\n")
    out.append("# QiCodex Index\n")

    if group_by and group_by in headers:
        groups = {}
        for r in rows:
            g = r.get(group_by,"(none)")
            groups.setdefault(g, []).append(r)
        for g in sorted(groups.keys()):
            out.append(f"\n## {g}\n")
            out.append("| " + " | ".join(idx_cols) + " |")
            out.append("|" + "|".join(["---"]*len(idx_cols)) + "|")
            for r in groups[g]:
                out.append("| " + " | ".join(r.get(c,"") for c in idx_cols) + " |")
    else:
        out.append("\n| " + " | ".join(idx_cols) + " |")
        out.append("|" + "|".join(["---"]*len(idx_cols)) + "|")
        for r in rows:
            out.append("| " + " | ".join(r.get(c,"") for c in idx_cols) + " |")

    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(out), encoding="utf-8")
    print(f"Wrote index → {md_path}")

def iter_md_files(roots: List[str]) -> List[Path]:
    out = []
    for root in roots:
        p = Path(root)
        if not p.exists(): continue
        for fp in p.rglob("*.md"):
            out.append(fp)
    return out

def cmd_validate(args, cfg):
    rules = cfg["qi_codex"]["rules"]
    realm_priv = rules.get("enforce_privacy_default_by_realm", {})
    scan_roots = cfg["qi_codex"]["scan_roots"]

    errors, fixes = [], []
    files = iter_md_files(scan_roots)
    for fp in files:
        txt = fp.read_text(encoding="utf-8", errors="ignore")
        fm, body = fm_parse(txt)
        if rules["require_front_matter"] and not fm:
            errors.append((fp, "Missing front matter"))
            continue

        # Required fields
        for req in rules.get("require_fields", []):
            if not fm.get(req):
                errors.append((fp, f"Missing required field '{req}'"))

        # Date hygiene
        if fm.get("date"):
            fm["date"] = ensure_date_iso(fm["date"])

        # Privacy default by realm
        realm = fm.get("realm")
        if realm and not fm.get("privacy") and realm in realm_priv:
            fm["privacy"] = realm_priv[realm]
            fixes.append((fp, "Set default privacy", f"{realm_priv[realm]}"))

        # Slug from title
        if rules.get("enforce_slug_from_title") and fm.get("title"):
            correct = slugify(fm.get("title"))
            if fm.get("slug") != correct:
                fm["slug"] = correct
                fixes.append((fp, "Normalize slug", correct))
                # align filename
                new_name = fp.with_name(f"{correct}.md")
                if new_name != fp:
                    os.rename(fp, new_name)
                    fp = new_name

        # Write back if we fixed anything
        if fixes and fixes[-1][0] == fp:
            fp.write_text(fm_dump(fm) + body, encoding="utf-8")

    # Report
    if errors:
        print("\nValidation errors:")
        for f, msg in errors:
            print(f" - {f}: {msg}")
    else:
        print("No blocking validation errors.")

    if fixes:
        print("\nApplied fixes:")
        for f, msg, detail in fixes:
            print(f" - {f}: {msg} → {detail}")

    # exit code
    sys.exit(1 if errors and not args.force else 0)

def cmd_suggest(args, cfg):
    local_csv = Path(cfg["qi_codex"]["local_csv"])
    rows, headers = read_csv(local_csv)
    pattern = cfg["qi_codex"]["pattern"]
    prefix = args.prefix.strip()
    typ = args.type or pattern["default_type"]
    q = next_qidec(prefix, rows, pad_seq=pattern["sequence_pad"], typ=typ)
    print(q)

def cmd_register(args, cfg):
    # Append a new row to the Codex CSV with a fresh ID
    local_csv = Path(cfg["qi_codex"]["local_csv"])
    rows, headers = read_csv(local_csv)
    pattern = cfg["qi_codex"]["pattern"]
    typ = args.type or pattern["default_type"]
    qi = next_qidec(args.prefix, rows, pad_seq=pattern["sequence_pad"], typ=typ)

    if not headers:
        headers = cfg["qi_codex"]["required_columns"]

    new = {
        "QiDecimal": qi,
        "Name": args.name,
        "Realm": args.realm,
        "Owner": args.owner,
        "Description": args.description or "",
        "Status": args.status or "active",
        "Version": args.version or "1.0.0",
        "Path": args.path or "",
        "Tags": args.tags or ""
    }
    # Ensure headers cover all fields
    for k in new.keys():
        if k not in headers: headers.append(k)

    rows.append(new)
    write_csv(local_csv, rows, headers)
    print(f"Registered: {qi}  ({args.name})")
    # Optionally rebuild index
    cmd_index(args, cfg)

# ------------------------- Main -------------------------
def main():
    ap = argparse.ArgumentParser(description="QiCodex Automations")
    ap.add_argument("--config", default="1_QiEos/1.50_Meta/metadata/qi_codex.config.yaml")

    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("sync", help="Sync Codex from Google Sheet CSV → local CSV")
    s.set_defaults(fn=cmd_sync)

    s = sub.add_parser("index", help="Render Markdown index table from local CSV")
    s.set_defaults(fn=cmd_index)

    s = sub.add_parser("validate", help="Validate notes across roots")
    s.add_argument("--force", action="store_true", help="Exit 0 even if errors")
    s.set_defaults(fn=cmd_validate)

    s = sub.add_parser("suggest", help="Suggest next QiDecimal by prefix (e.g. 7.10.03)")
    s.add_argument("prefix", help="Prefix like 7.10.03")
    s.add_argument("--type", help="TYPE part (default from config)")
    s.set_defaults(fn=cmd_suggest)

    s = sub.add_parser("register", help="Reserve + append new QiDecimal row into Codex")
    s.add_argument("prefix", help="Prefix like 7.10.03")
    s.add_argument("--name", required=True)
    s.add_argument("--realm", required=True)
    s.add_argument("--owner", default="CRV")
    s.add_argument("--description")
    s.add_argument("--status")
    s.add_argument("--version")
    s.add_argument("--path")
    s.add_argument("--tags")
    s.add_argument("--type")
    s.set_defaults(fn=cmd_register)

    args = ap.parse_args()
    cfg = load_yaml(Path(args.config))
    args.fn(args, cfg)

if __name__ == "__main__":
    main()
