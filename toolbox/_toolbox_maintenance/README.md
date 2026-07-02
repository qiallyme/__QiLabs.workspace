# QiLabs Toolbox Interactive Maintenance Kit

Unzip this kit directly into:

```txt
C:\QiLabs\00_QiLabs.workspace\toolbox
```

Then run:

```txt
RUN_TOOLBOX_BUILDER.bat
```

That opens an interactive menu. You do not need to remember CLI flags.

## Recommended first run

Choose:

```txt
3) Full recommended repair + clean + rebuild + launch
```

The cleaner archives clutter instead of deleting it. Archives go under:

```txt
_archive\maintenance-YYYYMMDD-HHMMSS
```

## What it handles

- Stops old background toolbox processes.
- Cleans Python caches: `__pycache__`, `*.pyc`, `*.pyo`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`.
- Neutralizes risky plugin-root `__init__.py` files by backing them up and making them quiet.
- Cleans root clutter by archiving old build outputs, old patch/review folders, old builder files, and loose generated files.
- Trims housekeeping runtime output folders while keeping the actual housekeeping app.
- Refreshes `toolbox_registry.json` and `toolbox_validation_report.md`.
- Runs compile checks.
- Builds `QiLabsToolbox.exe`.
- Launches the toolbox.
