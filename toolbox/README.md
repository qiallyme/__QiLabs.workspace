# QiOne Toolbox — Developer Guide

> **QiOne Desktop Tools** is a Python/Tkinter desktop application that hosts a collection of
> file and system operation tools. This guide explains exactly how to add a new tool.

---

## Table of Contents

1. [Project Structure](#project-structure)
2. [Architecture Overview](#architecture-overview)
3. [Creating a New Tool — Step-by-Step](#creating-a-new-tool--step-by-step)
   - [Step 1 — Choose a Bucket](#step-1--choose-a-bucket)
   - [Step 2 — Create the Tool Folder](#step-2--create-the-tool-folder)
   - [Step 3 — Write the Tool Class](#step-3--write-the-tool-class)
   - [Step 4 — Create `__init__.py`](#step-4--create-__init__py)
   - [Step 5 — Create `manifest.yaml`](#step-5--create-manifestyaml)
   - [Step 6 — Create `README.md`](#step-6--create-readmemd)
4. [BaseTool API Reference](#basetool-api-reference)
5. [The Build System](#the-build-system)
6. [Build Presets](#build-presets)
7. [Naming Conventions](#naming-conventions)
8. [Tool Checklist](#tool-checklist)
9. [Full Tool Example](#full-tool-example)

---

## Project Structure

```
toolbox/
├── build_QiOne_Tools.py      # Main interactive build script
├── build_qione.bat           # One-click Windows launcher for the build
├── main_ui.py                # Application shell — DO NOT edit manually
├── requirements.txt          # Shared pip dependencies
├── file_version_info.txt     # Windows EXE version metadata
├── QiOne_Tools.spec          # PyInstaller spec (auto-generated)
│
├── core/
│   └── base_tool.py          # BaseTool ABC — all tools inherit from this
│
└── tools/                    # All user-facing tools live here
    ├── README.md             # Tools index (this doc is in toolbox/)
    ├── build/                # Bucket: build & template tools
    ├── dev/                  # Bucket: developer workflow tools
    ├── docs/                 # Bucket: document operations
    ├── finance/              # Bucket: financial document tools
    ├── media/                # Bucket: audio/video/image tools
    ├── organize/             # Bucket: file cleanup and sorting
    └── system/               # Bucket: system administration tools
```

Each **bucket** is a folder. Each **tool** inside a bucket is its own folder with a fixed set of files.

---

## Architecture Overview

```
main_ui.py  (QiOneShell)
    │
    ├── sidebar  ──  one button per tool (tool.get_name())
    │
    ├── target directory bar  ──  shared across all tools
    │
    ├── tool settings card  ──  tool.build_ui(parent_frame)
    │
    └── action buttons
            Scan    ──  tool.execute(path, is_live=False, log, prog)
            Execute ──  tool.execute(path, is_live=True,  log, prog)
            Cancel  ──  sets tool.cancel_requested = True
```

The build script (`build_QiOne_Tools.py`) scans `tools/<bucket>/<tool>/<tool>.py`,
finds every class that inherits from `BaseTool`, then **auto-injects** the imports and
registrations into `main_ui.py` between the marker comments before compiling with PyInstaller.

You never need to manually edit `main_ui.py`.

---

## Creating a New Tool — Step-by-Step

### Step 1 — Choose a Bucket

Pick the single bucket that best fits your tool's purpose:

| Bucket     | Purpose                                                              |
|------------|----------------------------------------------------------------------|
| `build`    | Toolbox support, templates, packagers, tool-generation helpers       |
| `dev`      | Developer workflow — repos, code extraction, rules, project support  |
| `docs`     | PDF operations, text extraction, Markdown, document prep             |
| `finance`  | Money, tax, accounting, receipts, statements, financial documents    |
| `media`    | Audio, video, and image conversion or processing                     |
| `organize` | Digital housekeeping: cleanup, sorting, flattening, vault routing    |
| `system`   | Machine, environment, SSH, service checks, system administration     |

> **Rule:** A tool lives in exactly one bucket. Bucket names are **fixed** — do not add new buckets.

---

### Step 2 — Create the Tool Folder

Use `snake_case` for both the folder name and the main Python file.
The folder name and the Python file name **must match**.

```
tools/
└── <bucket>/
    └── <tool_name>/          ← folder name
        ├── <tool_name>.py    ← source file (SAME name as folder)
        ├── __init__.py
        ├── manifest.yaml
        └── README.md
```

**Example** — a new tool called "Duplicate Finder" in the `organize` bucket:

```
tools/
└── organize/
    └── duplicate_finder/
        ├── duplicate_finder.py
        ├── __init__.py
        ├── manifest.yaml
        └── README.md
```

---

### Step 3 — Write the Tool Class

Your tool file must:

1. Have the standard **file header comment** at the top.
2. Import `BaseTool` from `core.base_tool`.
3. Define a class that **inherits `BaseTool`**.
4. Implement three methods: `get_name`, `build_ui`, and `execute`.
5. Set `self.cancel_requested = False` in `__init__`.

#### Skeleton

```python
# file: duplicate_finder.py
# purpose: Toolbox tool module for Duplicate Finder in the organize bucket.
# usage: Loaded by the QiOne toolbox build system and launched from main_ui.py.
# inputs: User-selected target directory and tool-specific UI options.
# outputs: Tool-specific logs, generated files, or file operations.
# safety: Supports scan/dry-run vs live execution through the QiOne toolbox shell.
# owner: QiLabs

import os
import tkinter as tk
from tkinter import ttk
from core.base_tool import BaseTool


class DuplicateFinderTool(BaseTool):

    def __init__(self):
        self.cancel_requested = False
        # Add any instance variables your UI or logic needs here

    def get_name(self):
        """Return the label shown in the sidebar. Emojis are fine."""
        return "🔍 Duplicate Finder"

    def build_ui(self, parent):
        """
        Build tool-specific input widgets inside the tool settings card.
        Use the dark theme colors to match the shell:
            bg="#0f0f11"  (label background)
            bg="#1c1c1e"  (entry/widget background)
            fg="white"
        """
        ttk.Label(
            parent,
            text="Minimum file size (bytes):",
            background="#0f0f11",
            foreground="white"
        ).pack(anchor="w", pady=(0, 5))

        self.min_size_var = tk.StringVar(value="1024")
        tk.Entry(
            parent,
            textvariable=self.min_size_var,
            bg="#1c1c1e",
            fg="white",
            insertbackground="white",
            relief="flat"
        ).pack(fill="x", pady=(0, 15), ipady=5)

    def execute(self, target_path, is_live, log, prog):
        """
        Run the tool logic.

        Parameters
        ----------
        target_path : str
            Absolute path to the directory selected by the user.
        is_live : bool
            False  → dry run / scan only (preview what would happen).
            True   → live execution (actually make changes).
        log : callable
            Call log("message") to append a line to the console output.
            Always thread-safe — call freely from any thread.
        prog : callable
            Call prog(0–100) to update the progress bar.
        """
        self.cancel_requested = False

        log(f"🔍 DUPLICATE FINDER — {'LIVE' if is_live else 'DRY RUN'}")
        log("-" * 40)

        # Example: walk the directory
        files_seen = {}
        all_files = []
        for root, dirs, files in os.walk(target_path):
            for f in files:
                all_files.append(os.path.join(root, f))

        total = len(all_files)
        if total == 0:
            log("✅ No files found.")
            prog(100)
            return

        for i, filepath in enumerate(all_files):
            if self.cancel_requested:
                log("🛑 Cancelled by user.")
                break

            # --- your logic here ---
            # Example: just list files in dry run
            if not is_live:
                log(f"🔎 Would check: {os.path.basename(filepath)}")

            prog(int(((i + 1) / total) * 100))

        log("-" * 40)
        log("✅ Scan complete.")
```

#### Class Naming Rule

Class name must be `PascalCase` + `Tool` suffix.
The build scanner detects classes matching `class <Name>(... BaseTool ...)`.

| Folder name        | Class name              |
|--------------------|-------------------------|
| `duplicate_finder` | `DuplicateFinderTool`   |
| `vault_router`     | `VaultRouterTool`       |
| `git_push`         | `GitPushTool`           |

---

### Step 4 — Create `__init__.py`

This re-exports your class so the build system can import it cleanly.

```python
"""Tool module export for QiOne Desktop Tools."""

from .duplicate_finder import DuplicateFinderTool

__all__ = ["DuplicateFinderTool"]
```

---

### Step 5 — Create `manifest.yaml`

The manifest is metadata only — it does **not** drive the build.
It exists for documentation, tooling, and future automation.

```yaml
id: toolbox.organize.duplicate_finder
name: Duplicate Finder
type: toolbox_tool
language: python
status: active
owner: QiLabs

module:
  package: tools.organize.duplicate_finder
  file: duplicate_finder.py
  class_name: DuplicateFinderTool
  entrypoint: DuplicateFinderTool

toolbox:
  ui_enabled: true
  bucket: organize
  category: organize
  launch_surface:
    - QiOne Desktop Tools
  requires_target_directory: true

runtime:
  requires_network: false
  requires_secrets: false

safety:
  supports_dry_run: true
  supports_live_run: true
  deletes_files: false
  moves_files: false
  modifies_files: false
  review_before_live: true

paths:
  source: tools/organize/duplicate_finder/duplicate_finder.py
  readme: tools/organize/duplicate_finder/README.md

tags:
  - toolbox
  - organize
  - qione
```

---

### Step 6 — Create `README.md`

A short tool-level README for humans and future AI context.

```markdown
# Duplicate Finder

Scans a directory for duplicate files and optionally removes them.

## Dry Run

Click **Scan** to preview which files would be flagged as duplicates.

## Live Run

Click **Execute** to permanently remove duplicate files (sends to Recycle Bin).

## Options

- **Minimum file size** — only check files larger than this many bytes.
```

---

## BaseTool API Reference

Located at [`core/base_tool.py`](core/base_tool.py).

```python
class BaseTool:

    def get_name(self) -> str:
        """
        The display name shown in the sidebar button.
        Emojis are encouraged for quick visual identification.
        Must not be empty.
        """
        raise NotImplementedError

    def build_ui(self, parent_frame):
        """
        Called once when the user clicks the tool in the sidebar.
        Build all input widgets inside parent_frame.
        Store widget variables (tk.StringVar, tk.IntVar, etc.) as self attributes
        so execute() can read them.
        """
        raise NotImplementedError

    def execute(self, target_path: str, is_dry_run: bool, log_callback, progress_callback):
        """
        Called when the user clicks Scan (is_dry_run=True) or Execute (is_dry_run=False).
        Runs in a background thread — never block the UI here.
        Use log_callback("msg") and progress_callback(0-100) freely.
        Check self.cancel_requested in loops to support cancellation.
        """
        raise NotImplementedError
```

> **Important:** `execute` is called in a **daemon thread**. Never call Tkinter widget
> methods directly inside `execute`. Use `log_callback` and `progress_callback` — both
> are already thread-safe wrappers in the shell.

---

## The Build System

The build is handled by [`build_QiOne_Tools.py`](build_QiOne_Tools.py).

### What the Builder Does

1. **Scans** `tools/<bucket>/<tool>/<tool>.py` for classes inheriting `BaseTool`.
2. **Injects** import statements into `main_ui.py` between:
   ```
   # --- AUTO-IMPORTS START ---
   # --- AUTO-IMPORTS END ---
   ```
3. **Injects** tool registrations into `main_ui.py` between:
   ```
   # --- AUTO-REGISTER START ---
   # --- AUTO-REGISTER END ---
   ```
4. **Optionally bumps** the patch version in `file_version_info.txt`.
5. **Runs PyInstaller** to produce the `.exe` in `dist/`.

### How to Run the Build

**Option A — Interactive (recommended):**
```
Double-click build_qione.bat
```
or
```
python build_QiOne_Tools.py
```
Follow the prompts to pick a preset.

**Option B — CLI (non-interactive):**
```bash
python build_QiOne_Tools.py --preset dev-fast
python build_QiOne_Tools.py --preset release --clean --bump-version
```

### Auto-Discovery Rules

The scanner:

- Looks for `tools/<bucket>/<tool>/<tool>.py` (preferred file).
- Falls back to the **first** `.py` file found in the tool folder if the preferred name is missing.
- **Skips** any folder or file whose name starts with `_` (e.g., `_legacy_stubs`, `_archive`).
- **Skips** `__init__.py` files.
- Finds the class by regex: `class <Name>(<...BaseTool...>):`

If two tools have the **same class name**, the builder auto-generates a unique alias using the
bucket and tool folder name — no manual aliasing needed.

---

## Build Presets

| Preset          | Mode    | Clean | Console | Debug | Version Bump |
|-----------------|---------|-------|---------|-------|--------------|
| `dev-fast`      | dev     | No    | No      | No    | No           |
| `dev-clean`     | dev     | Yes   | No      | No    | No           |
| `dev-debug`     | dev     | No    | Yes     | Yes   | No           |
| `release`       | release | No    | No      | No    | Yes          |
| `release-clean` | release | Yes   | No      | No    | Yes          |

- **dev** → `--onedir` output in `dist/QiOne_Tools/`
- **release** → `--onefile` output in `dist/QiOne_Tools.exe`

---

## Naming Conventions

| Thing              | Convention                            | Example                   |
|--------------------|---------------------------------------|---------------------------|
| Bucket folder      | `snake_case`, singular noun           | `organize`                |
| Tool folder        | `snake_case`, descriptive             | `duplicate_finder`        |
| Source file        | Same as folder + `.py`                | `duplicate_finder.py`     |
| Class name         | `PascalCase` + `Tool`                 | `DuplicateFinderTool`     |
| `get_name()` value | Human-readable, optional emoji prefix | `"🔍 Duplicate Finder"`  |
| `manifest.yaml` id | `toolbox.<bucket>.<tool_folder>`      | `toolbox.organize.duplicate_finder` |

---

## Tool Checklist

Before running the build, verify your new tool has all of these:

- [ ] Tool folder exists at `tools/<bucket>/<tool_name>/`
- [ ] Source file name matches folder: `<tool_name>.py`
- [ ] Class inherits `BaseTool` (import: `from core.base_tool import BaseTool`)
- [ ] `__init__` sets `self.cancel_requested = False`
- [ ] `get_name()` returns a non-empty string
- [ ] `build_ui(self, parent)` builds widgets and stores state in `self.<var>`
- [ ] `execute(self, target_path, is_live, log, prog)` handles both dry-run and live modes
- [ ] `execute` loops check `self.cancel_requested` to support cancellation
- [ ] `__init__.py` re-exports the class with `from .<module> import <Class>`
- [ ] `manifest.yaml` created with correct bucket, class name, and paths
- [ ] `README.md` created with basic usage docs
- [ ] Any new pip dependencies added to `requirements.txt`
- [ ] Build runs cleanly: `python build_QiOne_Tools.py --preset dev-fast`
- [ ] Tool appears in the sidebar and responds to Scan and Execute

---

## Full Tool Example

The best reference implementations in this repo:

| Tool | Bucket | Highlights |
|------|--------|------------|
| [`vault_router.py`](tools/organize/vault_router/vault_router.py) | organize | Custom UI widgets (text box, secondary browse button), fuzzy matching, dry/live pattern |
| [`git_push.py`](tools/dev/git_push/git_push.py) | dev | Subprocess calls, bottom-up repo walk, error log file, cancel support |

Study either of these as a starting template for your own tool.
