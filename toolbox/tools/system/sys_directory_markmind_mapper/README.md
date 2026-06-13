# Directory Markmind Mapper

## Purpose

Directory Markmind Mapper walks a selected root directory and creates a Markmind/Markmap-friendly Markdown outline of the folder and file tree.

It is designed for the QiOne Desktop Tools UI and follows the QiLabs toolbox module pattern.

## Location

`tools/system/sys_directory_markmind_mapper/`

## Files

- `directory_markmind_mapper.py`
- `manifest.yaml`
- `README.md`

## Tool Class

`DirectoryMarkmindMapperTool`

Compatibility alias:

`SysDirectoryMarkmindMapperTool`

## Inputs

The tool uses the target directory selected in the QiOne Desktop Tools UI.

Additional options:

- Include files
- Include build/dependency artifacts
- Include YAML metadata header
- Max depth
- Output folder
- Output filename
- Extra excluded folders
- Extra excluded files
- Extra excluded extensions

## Outputs

A generated Markdown file:

`YYYY-MM-DD_directory_map_{root_slug}.md`

The file includes:

- YAML metadata header
- Generated timestamp
- Root path
- Nested Markdown bullet tree

## Default Exclusions

The tool skips common junk folders by default:

- `.git`
- `node_modules`
- `dist`
- `build`
- `.next`
- `coverage`
- `__pycache__`
- `.venv`
- `.cache`
- `logs`
- `tmp`

It also skips common junk/lock files:

- `.DS_Store`
- `Thumbs.db`
- `desktop.ini`
- `package-lock.json`
- `pnpm-lock.yaml`
- `yarn.lock`

## Safety

This tool is read-only against the selected directory.

It does not delete, move, rename, or modify source files.

It only writes the generated Markdown output file.
