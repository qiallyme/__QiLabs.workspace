# Tree-Aware Docs Compiler

Wraps the QiLabs tree-aware docs compiler inside the desktop toolbox.

## Modes

- `Check`: lint and summarize documentation issues without building output.
- `Build`: rebuild the generated docs target folder.
- `Fix`: apply safe source Markdown normalization fixes.

## Notes

The selected toolbox target directory is used as the repo root. The generated docs target folder is configured separately inside the tool UI.
