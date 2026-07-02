# QiLabs Toolbox Validation Report

- Generated: 2026-07-02T00:45:03
- Plugins: 26
- Errors: 0
- Warnings: 9

## Plugins

- `access.qiaccess.bookmarks` - QiAccess Bookmarks (access)
- `beta.audio` - Audio (beta)
- `beta.notion_pipeline` - Notion Pipeline (beta)
- `finance.cashapp.to.sample.bankstatement` - Cashapp To Sample Bankstatement (finance)
- `finance.firefly.bills.importer` - Firefly Bills Importer (finance)
- `finance.tax.compiler` - Tax Compiler (finance)
- `finance.zai.ledger.importer` - Zai Ledger Importer (finance)
- `media.video.converter` - Video Converter (media)
- `organize.archivist` - Archivist (organize)
- `organize.bloat.destroyer` - Bloat Destroyer (organize)
- `organize.downloads.inspector` - Downloads Inspector (organize)
- `organize.file.cleaner` - File Cleaner (organize)
- `organize.folder.flattener` - Folder Flattener (organize)
- `organize.unlock.downloads` - Unlock Downloads (organize)
- `organize.unzip.sync` - Unzip Sync (organize)
- `organize.vault.router` - Vault Router (organize)
- `organize.xlsx.tabs.to.csv` - XLSX Tabs to CSV (organize)
- `system.creator_smoke_plugin` - Creator Smoke Plugin (system)
- `system.sys.directory.markmind.mapper` - Directory Markmind Mapper (system)
- `system.housekeeping.console` - Housekeeping Console (system)
- `system.plugin_host_demo` - Plugin Host Demo (system)
- `system.qilabs.structure.checker` - QiLabs Structure Checker (system)
- `system.remote.ssh` - Remote Ssh (system)
- `system.toolbox_manager` - Toolbox Manager (system)
- `system.sys.docs.compiler` - Tree-Aware Docs Compiler (system)
- `system.bat.launcher` - bat_launcher (system)

## Findings

- **WARNING** `missing_requirement` - Requirement may be missing: dlt
  - Path: `C:\QiLabs\00_QiLabs.workspace\toolbox\tools\beta\notion_pipeline\manifest.yaml`
  - Plugin: `beta.notion_pipeline`
  - Fixable: yes
- **WARNING** `missing_requirement` - Requirement may be missing: notion
  - Path: `C:\QiLabs\00_QiLabs.workspace\toolbox\tools\beta\notion_pipeline\manifest.yaml`
  - Plugin: `beta.notion_pipeline`
  - Fixable: yes
- **WARNING** `missing_requirement` - Requirement may be missing: requests
  - Path: `C:\QiLabs\00_QiLabs.workspace\toolbox\tools\finance\firefly_bills_importer\manifest.yaml`
  - Plugin: `finance.firefly.bills.importer`
  - Fixable: yes
- **WARNING** `missing_requirement` - Requirement may be missing: pillow
  - Path: `C:\QiLabs\00_QiLabs.workspace\toolbox\tools\finance\tax_compiler\manifest.yaml`
  - Plugin: `finance.tax.compiler`
  - Fixable: yes
- **WARNING** `missing_requirement` - Requirement may be missing: pillow_heif
  - Path: `C:\QiLabs\00_QiLabs.workspace\toolbox\tools\finance\tax_compiler\manifest.yaml`
  - Plugin: `finance.tax.compiler`
  - Fixable: yes
- **WARNING** `missing_requirement` - Requirement may be missing: requests
  - Path: `C:\QiLabs\00_QiLabs.workspace\toolbox\tools\finance\zai_ledger_importer\manifest.yaml`
  - Plugin: `finance.zai.ledger.importer`
  - Fixable: yes
- **WARNING** `missing_requirement` - Requirement may be missing: Send2Trash
  - Path: `C:\QiLabs\00_QiLabs.workspace\toolbox\tools\organize\vault_router\manifest.yaml`
  - Plugin: `organize.vault.router`
  - Fixable: yes
- **WARNING** `missing_requirement` - Requirement may be missing: rapidfuzz
  - Path: `C:\QiLabs\00_QiLabs.workspace\toolbox\tools\organize\vault_router\manifest.yaml`
  - Plugin: `organize.vault.router`
  - Fixable: yes
- **WARNING** `missing_requirement` - Requirement may be missing: openpyxl
  - Path: `C:\QiLabs\00_QiLabs.workspace\toolbox\tools\organize\xlsx_tabs_to_csv\manifest.yaml`
  - Plugin: `organize.xlsx.tabs.to.csv`
  - Fixable: yes
