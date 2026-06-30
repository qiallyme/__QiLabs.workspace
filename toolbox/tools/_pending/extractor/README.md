# Extractor

## Purpose

`extractor.py` is a QiOne Desktop Tools module in the `dev` bucket.

## Toolbox Metadata

- **Tool ID:** `toolbox.dev.extractor`
- **Bucket:** `dev`
- **Entrypoint class:** `TextExtractorTool`
- **Source file:** `extractor.py`

## Usage

This tool is loaded by the QiOne Desktop Tools launcher.

Typical import:

```python
from tools.dev.extractor import TextExtractorTool
```

## Safety

Use scan/dry-run mode before live execution when the tool supports it.

## Files

```txt
extractor/
  __init__.py
  extractor.py
  README.md
  manifest.yaml
```
