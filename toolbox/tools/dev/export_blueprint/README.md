# Export Blueprint

## Purpose

`export_blueprint.py` is a QiOne Desktop Tools module in the `dev` bucket.

## Toolbox Metadata

- **Tool ID:** `toolbox.dev.export_blueprint`
- **Bucket:** `dev`
- **Entrypoint class:** `ExportBlueprintTool`
- **Source file:** `export_blueprint.py`

## Usage

This tool is loaded by the QiOne Desktop Tools launcher.

Typical import:

```python
from tools.dev.export_blueprint import ExportBlueprintTool
```

## Safety

Use scan/dry-run mode before live execution when the tool supports it.

## Files

```txt
export_blueprint/
  __init__.py
  export_blueprint.py
  README.md
  manifest.yaml
```
