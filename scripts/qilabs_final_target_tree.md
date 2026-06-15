# QiLabs Final Target Tree

```text
C:\QiLabs\
  .github\
  .qios\
  .vscode\

  00_QiEOS\
  10_QiOS_Start\
  20_QiSystem\
  30_QiServer\
  40_QiCapture\
  50_QiNexus\
    My Drive\
  60_QiApps\
  60_QiConnect\

  packages\
  scripts\
  toolbox\
```

## QiNexus/My Drive Buckets

```text
50_QiNexus\My Drive\
  00_inbox\
  01_workbench\
  02_timeline\
  03_life\
  04_people\
  05_business\
  06_finance\
  07_legal\
  08_tech\
  09_assets\
  10_data\
  11_reference\
  12_archive\
  13_system\
```

## Rules

- `50_QiNexus\My Drive` is QiNexus.
- Do not keep duplicate root-system folders inside `My Drive`, such as `20_qinexus`, `30_qiarchive`, `40_qisystem`, or `60_qiconnect`.
- `scripts` is thin repo automation only.
- `toolbox` is reusable human-operated tools.
- Generated/cache folders should be ignored or disposable: `.next`, `dist`, `build`, `.venv`, `venv`, `__pycache__`, `.cache`, `tmp`, `temp`.
