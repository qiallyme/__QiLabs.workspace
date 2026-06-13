# Rule Tester

## Purpose

`rule_tester.py` is a QiOne Desktop Tools module in the `dev` bucket.

## Toolbox Metadata

- **Tool ID:** `toolbox.dev.rule_tester`
- **Bucket:** `dev`
- **Entrypoint class:** `RuleTesterTool`
- **Source file:** `rule_tester.py`

## Usage

This tool is loaded by the QiOne Desktop Tools launcher.

Typical import:

```python
from tools.dev.rule_tester import RuleTesterTool
```

## Safety

Use scan/dry-run mode before live execution when the tool supports it.

## Files

```txt
rule_tester/
  __init__.py
  rule_tester.py
  README.md
  manifest.yaml
```
