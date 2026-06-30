# Repo Triage

Performs a safe first-pass repo cleanup without deleting source files.

## Behavior

- `Scan` inventories the repo and previews root-level junk quarantine moves.
- `Execute` writes directory and file inventories, optionally moves obvious temp/cache folders into `_quarantine`, and ensures the QiOS hygiene block exists in `.gitignore`.
