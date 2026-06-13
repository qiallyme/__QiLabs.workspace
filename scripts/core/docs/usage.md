---
title: 1) Pull The Latest Codex From Google Sheets
slug: 1-pull-the-latest-codex-from-google-sheets
realm: 7_Tools
owner: CRV
privacy: shared
qi_decimal: 2.99.00-01.SYS
---
# 1) Pull the latest Codex from Google Sheets
python qi_codex_tool.py sync

# 2) Rebuild the pretty Markdown index page
python qi_codex_tool.py index

# 3) Validate your vault (front matter, slugs, privacy, etc.)
python qi_codex_tool.py validate

# 4) Suggest an ID for a new item under prefix 7.10.03
python qi_codex_tool.py suggest 7.10.03
# → 7.10.03-01.SYS (or next available)

# 5) Register a new item into the Codex and rebuild index
python qi_codex_tool.py register 7.10.03 --name "CSV→MD Converter" \
  --realm "7_Tools" --description "CLI for CSV→MD with QiEOS FM" \
  --path "7_Tools/7.10_python/csv_to_md" --tags "tools,converter"
