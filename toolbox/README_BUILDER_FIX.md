# QiOne Bucketed Builder Fix

## Files

- `build_QiOne_Tools.py`
- `build_qione.bat`

## Where to Put Them

Copy both files into:

```txt
c:\QiLabs\toolbox\
```

Replace your existing builder file if needed.

## What Changed

The builder now scans the final bucketed structure:

```txt
tools/<bucket>/<tool>/<tool>.py
```

Example:

```txt
tools/docs/pdf_splitter/pdf_splitter.py
```

It injects imports like:

```python
from tools.docs.pdf_splitter import BulkPdfSplitterTool
```

## Use

Double-click:

```txt
build_qione.bat
```

or open `build_QiOne_Tools.py` in the IDE and hit Run.
