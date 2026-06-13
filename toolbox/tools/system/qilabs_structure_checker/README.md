# QiLabs Structure Checker

Audits a selected QiLabs workspace root against the expected top-level layout, QiNexus bucket model, generated folder hygiene, heavy `scripts/` logic, and long path risk.

## Behavior

- `Scan` reports findings in the run console and previews the output location.
- `Execute` writes JSON, CSV, and Markdown reports into the configured report folder under the selected root.

## Outputs

- `qilabs_structure_check.json`
- `qilabs_structure_check.csv`
- `qilabs_structure_check.md`
