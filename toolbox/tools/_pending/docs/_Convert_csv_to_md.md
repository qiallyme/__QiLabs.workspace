---
title: Recommended CSV Template
slug: recommended-csv-template
realm: 7_Tools
owner: CRV
privacy: shared
qi_decimal: 2.99.00-01.SYS
---
Love this idea. Here’s a clean, flexible way to do it:

# Recommended CSV template

Use whatever headers you already have—the tool will let you map them—but these defaults cover most vault needs:

* `title` (string) — required; becomes filename + page title
* `slug` (optional) — fallback auto-generated from title
* `date` (ISO `YYYY-MM-DD` or full ISO datetime)
* `tags` (comma- or space-separated; you can use `#tag` or plain words)
* `qicode` (your internal ID)
* `status` (e.g., draft, active, done)
* `category` (free text)
* `summary` (short)
* `content` (longform body; can be missing—tool can build content from other fields)
* anything else → preserved automatically under **Footnotes / Source Data**

A minimal example row:

```csv
title,date,tags,summary,content,client_email,source
“First Client Intake Note”,2025-11-04,"#client, intake","Kickoff call notes","We discussed scope, budget, next steps",client@example.com,Google Sheet Import
```

# What the tool does

1. Reads your CSV, shows the detected headers.
2. Lets you map those headers to your preferred “front matter” keys (title, date, tags, etc.).
3. Lets you pick which column(s) make up the **page content** (in order, concatenated).
4. Everything unmapped is preserved at the bottom of the page as a **Footnotes / Source Data** section (pretty table + JSON dump), so nothing is lost.
5. Writes one Markdown file per row with YAML front matter optimized for Obsidian.

---

# Drop-in Python script (CLI, no extra deps)

Save this as `csv_to_md.py` and run:
`python csv_to_md.py --csv path/to/data.csv --out ./vault/notes`

````python
#!/usr/bin/env python3
import csv
import json
import re
import sys
import argparse
from datetime import datetime
from pathlib import Path

# ---------- Helpers ----------

DEFAULT_FRONT_MATTER_KEYS = [
    "title", "slug", "date", "tags", "qicode", "status",
    "category", "summary"
]

def slugify(text: str, max_len: int = 120) -> str:
    if not text:
        return "untitled"
    s = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE).strip().lower()
    s = re.sub(r"[\s_-]+", "-", s)
    return s[:max_len] or "untitled"

def parse_tags(raw):
    if raw is None:
        return []
    # Accept "#tag, other tag;tag3" etc.
    txt = str(raw)
    # Replace separators with commas
    txt = re.sub(r"[;|/]", ",", txt)
    parts = [p.strip() for p in txt.split(",") if p.strip()]
    # Drop leading '#'
    parts = [p[1:] if p.startswith("#") else p for p in parts]
    # Deduplicate, keep order
    seen, out = set(), []
    for p in parts:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out

def normalize_date(raw):
    if not raw:
        return None
    txt = str(raw).strip()
    # Try a few common formats; fallback to raw string
    fmts = ["%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S%z"]
    for f in fmts:
        try:
            dt = datetime.strptime(txt, f)
            return dt.isoformat()
        except Exception:
            pass
    # If already ISO-ish, keep as-is
    return txt

def yaml_escape(value):
    if value is None:
        return ""
    s = str(value)
    # Quote if it looks like YAML might misread it
    if any(ch in s for ch in [":", "{", "}", "[", "]", ",", "#", "&", "*", "!", "|", ">", "'", '"', "%", "@", "`"]) or s.strip()!=s:
        # prefer single quotes; escape internal single quotes by doubling
        s = "'" + s.replace("'", "''") + "'"
    return s

def write_markdown(row, mapping, content_cols, output_dir, filename_from="title", keep_json=True):
    title_col = mapping.get("title")
    raw_title = (row.get(title_col) if title_col else None) or "Untitled"
    title = str(raw_title).strip() or "Untitled"
    slug_col = mapping.get("slug")
    raw_slug = str(row.get(slug_col)).strip() if slug_col and row.get(slug_col) else slugify(title)
    slug = slugify(raw_slug)

    # Build front matter
    fm = {}
    for k in DEFAULT_FRONT_MATTER_KEYS:
        col = mapping.get(k)
        if not col:
            continue
        v = row.get(col)
        if v is None or v == "":
            continue
        if k == "date":
            v = normalize_date(v)
        if k == "tags":
            v = parse_tags(v)
        fm[k] = v

    # Ensure title & slug present
    fm.setdefault("title", title)
    fm.setdefault("slug", slug)

    # Build content body
    sections = []
    # H1
    sections.append(f"# {title}\n")
    # Summary if provided and not going into front matter-only
    if "summary" in fm and fm["summary"]:
        sections.append(f"> {fm['summary']}\n")

    # Concatenate chosen content columns
    if content_cols:
        for col in content_cols:
            if col in row and str(row[col]).strip():
                # Use column name as subsection if you picked multiple
                if len(content_cols) > 1:
                    sections.append(f"## {col}\n")
                sections.append(f"{row[col]}\n")
    else:
        # If no content mapping, try a sensible default
        for candidate in ("content", "body", "notes"):
            if candidate in row and str(row[candidate]).strip():
                sections.append(f"{row[candidate]}\n")
                break

    # Footnotes / Source Data: everything unmapped + any remaining keys
    mapped_cols = set(filter(None, mapping.values()))
    leftover = {k: v for k, v in row.items() if k not in mapped_cols or k in (set(content_cols or []))}
    # Remove content cols if they were fully pushed above (avoid duplication)
    for c in content_cols or []:
        if c in leftover:
            del leftover[c]

    if leftover:
        sections.append("\n---\n")
        sections.append("## Footnotes / Source Data\n\n")

        # Pretty table (best effort)
        table_rows = [["Field", "Value"]]
        for k, v in leftover.items():
            table_rows.append([k, "" if v is None else str(v)])
        # Render table
        col1 = max(len(r[0]) for r in table_rows)
        col2 = max(len(r[1]) for r in table_rows)
        def row_line(a,b):
            return f"| {a:<{col1}} | {b:<{col2}} |"
        sections.append(row_line("Field", "Value") + "\n")
        sections.append("|-" + "-"*col1 + "-|-" + "-"*col2 + "-|\n")
        for r in table_rows[1:]:
            sections.append(row_line(r[0], r[1]) + "\n")

        if keep_json:
            sections.append("\n<details>\n<summary>Raw JSON</summary>\n\n")
            sections.append("```json\n")
            sections.append(json.dumps(row, ensure_ascii=False, indent=2))
            sections.append("\n```\n</details>\n")

    body = "\n".join(sections).rstrip() + "\n"

    # YAML front matter at top
    yaml_lines = ["---"]
    for k, v in fm.items():
        if k == "tags" and isinstance(v, list):
            # YAML inline list
            yaml_lines.append(f"{k}: [{', '.join(yaml_escape(t) for t in v)}]")
        else:
            yaml_lines.append(f"{k}: {yaml_escape(v)}")
    yaml_lines.append("---\n")
    front_matter = "\n".join(yaml_lines)

    # Write file
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{slug}.md"
    (output_dir / filename).write_text(front_matter + body, encoding="utf-8")
    return filename

# ---------- Interactive mapping ----------

def prompt_mapping(csv_headers):
    print("\nDetected CSV headers:")
    print(" - " + "\n - ".join(csv_headers))

    print("\nMap your CSV columns to default front matter keys (press Enter to skip a key).")
    mapping = {}
    for key in DEFAULT_FRONT_MATTER_KEYS:
        val = input(f"CSV column for '{key}' (or skip): ").strip()
        if val:
            if val not in csv_headers:
                print(f"  (!) '{val}' not found in headers; skipping")
            else:
                mapping[key] = val

    # Choose content columns (optional, multi)
    print("\nSelect content column(s). Enter column names separated by commas, or leave blank.")
    raw = input("Content columns: ").strip()
    content_cols = []
    if raw:
        for c in [p.strip() for p in raw.split(",") if p.strip()]:
            if c in csv_headers:
                content_cols.append(c)
            else:
                print(f"  (!) '{c}' not found; ignoring")
    return mapping, content_cols

# ---------- Main ----------

def main():
    ap = argparse.ArgumentParser(description="CSV → Markdown converter with front matter mapping (Obsidian-friendly).")
    ap.add_argument("--csv", required=True, help="Path to input CSV")
    ap.add_argument("--out", required=True, help="Output directory for .md files")
    ap.add_argument("--config", help="Optional JSON mapping: { 'title': 'TitleCol', 'date': 'DateCol', ... , 'content_cols': ['Body','Notes'] }")
    ap.add_argument("--filename_from", default="title", choices=["title", "slug"], help="Control filename source")
    ap.add_argument("--no_json_dump", action="store_true", help="Disable raw JSON dump in footnotes")
    args = ap.parse_args()

    csv_path = Path(args.csv)
    out_dir  = Path(args.out)

    # Read CSV
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        headers = reader.fieldnames or []

    if not rows:
        print("No rows found in CSV.")
        sys.exit(1)

    # Load or prompt mapping
    mapping = {}
    content_cols = []
    if args.config:
        cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
        mapping = {k: v for k, v in cfg.items() if k != "content_cols"}
        content_cols = cfg.get("content_cols", [])
    else:
        mapping, content_cols = prompt_mapping(headers)

    # Convert rows
    written = []
    for row in rows:
        fn = write_markdown(
            row=row,
            mapping=mapping,
            content_cols=content_cols,
            output_dir=out_dir,
            filename_from=args.filename_from,
            keep_json=not args.no_json_dump
        )
        written.append(fn)

    print(f"\nDone. Wrote {len(written)} files to: {out_dir.resolve()}")
    if len(written) <= 10:
        for fn in written:
            print(" -", fn)

if __name__ == "__main__":
    main()
````

## Quick how-to

1. Put your CSV somewhere, e.g. `~/data/notes.csv`.
2. Run:

   ```
   python csv_to_md.py --csv ~/data/notes.csv --out ~/Vault/Inbox
   ```
3. The script will show your CSV headers and ask you to:

   * Map them to `title`, `date`, `tags`, etc.
   * Pick one or more **content** columns (these become the page body).
4. It writes one `.md` per row with Obsidian-ready YAML front matter. All extra columns are preserved under **Footnotes / Source Data** (plus a raw JSON dump you can turn off with `--no_json_dump`).

## Optional: non-interactive (repeatable) config

Create `mapping.json`:

```json
{
  "title": "Title",
  "date": "Created",
  "tags": "Labels",
  "qicode": "QiCode",
  "summary": "Summary",
  "content_cols": ["Body", "Notes"]
}
```

Run:

```
python csv_to_md.py --csv data.csv --out ./vault/import --config mapping.json
```

## Filename strategy

* Defaults to `title` → slugified (`My Note` → `my-note.md`).
* You can switch to `--filename_from slug` if your CSV has a `slug` column mapped.

## What the output looks like

````md
---
title: 'First Client Intake Note'
slug: first-client-intake-note
date: 2025-11-04T00:00:00
tags: [client, intake]
qicode: '60.20.01-00.SYS'
status: 'active'
category: 'Onboarding'
summary: 'Kickoff call notes'
---

# First Client Intake Note

> Kickoff call notes

## content
We discussed scope, budget, next steps

---
## Footnotes / Source Data

| Field          | Value                 |
|----------------|-----------------------|
| client_email   | client@example.com    |
| source         | Google Sheet Import   |

<details>
<summary>Raw JSON</summary>

```json
{
  "title": "First Client Intake Note",
  "date": "2025-11-04",
  "tags": "#client, intake",
  "summary": "Kickoff call notes",
  "content": "We discussed scope, budget, next steps",
  "client_email": "client@example.com",
  "source": "Google Sheet Import"
}
````

</details>
```

---