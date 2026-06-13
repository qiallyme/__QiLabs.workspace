# File Cleaner

## Purpose

`file_cleaner.py` is a QiOne Desktop Tools module in the `organize` bucket.

## Toolbox Metadata

- **Tool ID:** `toolbox.organize.file_cleaner`
- **Bucket:** `organize`
- **Entrypoint class:** `FilenameCleanerTool`
- **Source file:** `file_cleaner.py`

## Usage

This tool is loaded by the QiOne Desktop Tools launcher.

Typical import:

```python
from tools.organize.file_cleaner import FilenameCleanerTool
```

## Safety

Use scan/dry-run mode before live execution when the tool supports it.

## Files

```txt
file_cleaner/
  __init__.py
  file_cleaner.py
  README.md
  manifest.yaml
```
