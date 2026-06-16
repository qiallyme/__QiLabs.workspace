# C:\QiLabs Structure Cleanup & DNA Alignment Plan (June 2026)

This document is the local record of the archive-first structure cleanup and directory renames performed to align the workspace with QiOS DNA guidelines.

---

## 1. System Layer Renames & Reference Updates

### Active Renames
*   **Rename:** `C:\QiLabs\70_QiConnect` -> `C:\QiLabs\60_QiConnect`
    *   *Rationale:* Align with standard numbering in QiOS DNA schemas.
*   **Rename:** `C:\QiLabs\1100_QiApp_QiLife` -> `C:\QiLabs\1100_QiLife`
    *   *Rationale:* Standardize the app naming structure.

### Files Updated for References
*   `C:\QiLabs\__QiLabs.workspace\toolbox\tools\system\qilabs_structure_checker\qilabs_structure_checker.py`
    *   Updated `70_QiConnect` / `70_qiconnect` references to `60_QiConnect` / `60_qiconnect`.
*   `C:\QiLabs\__QiLabs.workspace\scripts\qilabs_final_target_tree.md`
    *   Updated `70_QiConnect` reference to `60_QiConnect`.

---

## 2. Archive Actions (Obsolete Portal Code)

Obsolete/legacy folder structures in `qiportals` are moved to `_archive` directories to prevent context window bloat and configuration noise during local compilation.

### Moves to Archive
*   `C:\QiLabs\1000_QiApps\qiportals\app`
    -> `C:\QiLabs\1000_QiApps\qiportals\_archive\app_legacy`
*   `C:\QiLabs\1000_QiApps\qiportals\USBLegalAidv2`
    -> `C:\QiLabs\1000_QiApps\qiportals\_archive\USBLegalAidv2_legacy`
*   `C:\QiLabs\1000_QiApps\qiportals\src\features\qiadmin\src`
    -> `C:\QiLabs\1000_QiApps\qiportals\_archive\qiadmin_nested_vue_app`

---

## 3. Files & Directories Not Touched

For safety, the following resources are explicitly excluded from modifications:
1.  **Google Takeout Extraction Folder (`C:\QiLabs\50_QiNexus\My Drive\00_inbox\10_ingestion\20_drive_imports\Takeout`)**
    *   Currently being written to by the background unzip task.
2.  **Recursion Pruning (`QiNotesSync/QiNotesSync/QiNotesSync`)**
    *   Not modified during this phase. Obsidian sync should be paused and audited separately (see `C:\QiLabs\META\qinotessync_recursion_review.md`).
3.  **Duplicate Files (799 groups)**
    *   No automatic duplicate files were deleted to prevent breaking project assets, templates, and script dependencies.
4.  **Credentials/Environments (`.env` files)**
    *   No environment variables or `.env` files were deleted. They are listed for review in `C:\QiLabs\META\env_security_review.md`.

---

## 4. Risks & Verification Notes

*   **Risk:** Breaking local links to `70_QiConnect` in external tools or untracked scripts.
*   **Verification:**
    *   Ran build and dev targets in `qiportals` to ensure compilation is clean.
    *   Verified that the active unzip background task continues to run unaffected.
