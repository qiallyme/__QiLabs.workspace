# QiOne Toolbox Tools

The `tools/` directory contains user-facing tools loaded by the QiOne Desktop Tools executable.

## Final Seven Buckets

- `build` — Toolbox build support, templates, packagers, and tool-generation helpers.
- `dev` — Developer workflow tools for repos, code extraction, rules, and project support.
- `docs` — Document operations such as PDF splitting, text extraction, Markdown, and document prep.
- `finance` — Money, tax, accounting, receipts, statements, and financial document workflows.
- `media` — Audio, video, and image conversion or processing tools.
- `organize` — Digital housekeeping: cleanup, sorting, flattening, downloads, archives, and vault routing.
- `system` — Machine, environment, remote access, service checks, SSH, and system administration tools.

## Standard Tool Module Shape

```txt
tools/
  bucket/
    tool_name/
      __init__.py
      tool_name.py
      README.md
      manifest.yaml
```

## Rules

1. Each toolbox tool lives in exactly one bucket.
2. Each tool gets its own folder.
3. Each tool folder contains README.md, manifest.yaml, __init__.py, and the source file.
4. The source file has a self-identifying header comment.
5. Bucket names are stable and intentionally limited to seven.

## Import Pattern

```python
from tools.docs.pdf_splitter import BulkPdfSplitterTool
```
