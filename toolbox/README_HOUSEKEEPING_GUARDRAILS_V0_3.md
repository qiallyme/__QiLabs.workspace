# QiLabs Housekeeping Guardrails v0.3

Unzip this package directly into:

`C:\QiLabs\00_QiLabs.workspace\toolbox`

Then double-click:

`INSTALL_HOUSEKEEPING_GUARDRAILS.bat`

This installer:

- backs up the current housekeeping config
- installs a conservative scoped config
- creates `C:\QiLabs\_qiconfig\master_template.md` if missing
- creates `C:\QiLabs\_qiconfig\tags.json` if missing
- quarantines the rejected over-broad dry-run plan `20260702-000419`

After install, run Housekeeping Console with:

- Include filename renames: OFF
- Push: OFF
- Manual steps only first:
  1. Preflight
  2. Validate tags
  3. Validate master template
  4. Scan inventory

Do not approve/apply Full Run until the manual preview is clean.
