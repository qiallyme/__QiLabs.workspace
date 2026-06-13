---
title: CSV → MD Converter
qi_decimal: 7.10.03-00.SYS
realm: 7_Tools
owner: CRV
privacy: shared
status: active
version: 1.0.0
summary: 'Convert CSV rows into Obsidian-ready Markdown files with YAML front matter, preserving unmapped data.'
slug: csv-md-converter
---

# CSV → MD Converter (QiCode Tool)

### Purpose
This utility transforms any CSV dataset into a folder of Markdown notes compliant with **QiEOS** and **QiDecimal** naming standards.  
Each row becomes an Obsidian-ready `.md` file containing YAML front matter and structured content.

---

## ⚙️ Features
- Interactive or JSON-config header mapping
- YAML front matter generation (`title`, `slug`, `date`, `tags`, `qicode`, etc.)
- Preservation of all unmapped data as “Footnotes / Source Data”
- Automatic slug generation and safe filename handling
- Optional raw JSON dump for downstream processing
- Direct compatibility with Obsidian, QiNote, and RAG ingestion

---

## 🧩 Input Contract
| Field | Type | Notes |
|-------|------|-------|
| **CSV file** | UTF-8 or UTF-8-SIG | Requires header row |
| **Headers** | string | Column names auto-detected |
| **Mapping** | interactive or config JSON | Maps CSV headers → QiEOS front matter keys |
| **Date formats** | multiple | ISO 8601 preferred (`YYYY-MM-DD`) |
| **Tags** | string | comma, semicolon, or `#` prefixes supported |

---

## 🪶 Output Schema (QiEOS Front Matter)
```yaml
title: ""
slug: ""
date: ""          # ISO 8601
tags: []          # YAML list
qicode: ""        # optional per-note code
status: "active"  # draft|active|done|archived
category: ""
summary: ""
qi_decimal: ""
owner: "CRV"
realm: ""
privacy: "shared"
created: ""
last_updated: ""
