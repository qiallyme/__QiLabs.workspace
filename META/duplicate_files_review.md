# Duplicate Files Review & Classification

A review of the duplicate files identified in the workspace, classified by risk and cleanup category. No files were deleted during this process.

---

## 1. Environment & Infrastructure Templates (`safe_template_duplicate`)

These are configuration headers, settings profiles, and ignore lists copied across projects or packages. They are normal and safe to leave as-is.

| Filename | Size | Representative Paths |
| :--- | :--- | :--- |
| `.gitignore` | 1 KB - 2 KB | `qiportals/.gitignore`, `10_QiAccess/.gitignore`, `qicare/.gitignore` |
| `.dockerignore` | 0 KB | `qiportals/src/features/qiadmin/.dockerignore`, `10_QiAccess/.dockerignore` |
| `.editorconfig` | 0 KB | `qicare/apps/worker/.editorconfig`, `10_QiAccess/.editorconfig` |
| `.gitattributes` | 0 KB | `qiportals/src/features/qicontacts/.gitattributes`, `qiblogs/.gitattributes` |
| `Dockerfile` | 1 KB | `10_QiAccess/Dockerfile`, `qiportals/app/features/admin/Dockerfile` |

---

## 2. Generated & Build Outputs (`generated_duplicate`)

Files generated dynamically by dependency managers, build steps, or initialization processes.

| Filename | Size | Representative Paths |
| :--- | :--- | :--- |
| `Cargo.lock` | 30 KB | `20_QiSystem/packages/qinode/Cargo.lock`, `packages/qinode/qinode-engine/Cargo.lock` |
| `.gitkeep` / `.keep` | 0 KB | Replicated inside empty dropzones, logs, and adapter folders (e.g. `30_QiServer/data/inbox/.gitkeep`). |
| `.tsbuildinfo` | 1882 KB | TypeScript compiler cache files (automatically ignored/disposable). |

---

## 3. Obsidian Sync Recursions (`archive_candidate`)

Duplicated notes caused by the nested directory sync loop under `70_QiConnect/QiNotesSync`. These are target candidates for archive cleanup once the sync loop is paused.

| Filename | Size | Duplication Locations |
| :--- | :--- | :--- |
| `2026-05-09_s_elliott_st_household_meeting_summary.md` | 15 KB | Duplicated inside recursive `QiNotesSync/Elliot-St/` subpaths. |
| `Chatnotw.md` | 6 KB | Duplicated inside recursive `QiNotesSync/QiNotesSync/` subpaths. |
| `Complete_Legal_Estate_Package.md` | 5 KB | Duplicated inside recursive `QiNotesSync/Templates/` subpaths. |
| `2026-05-125_171438__Entry.md` | 0 KB | Replicated across nested `Voice Entries/` folders. |

---

## 4. Ingestion Imports & Note Records (`review_needed`)

These are raw imported notes, letters, PDF scans, and receipts inside `40_QiCapture` and `50_QiNexus` that exist in multiple places due to imports mapping. They should be reviewed during the RAG indexing phase.

| Filename | Size | Duplication Locations |
| :--- | :--- | :--- |
| `10_BMV_App.md` / `10_Draft.md` | 0 KB | Duplicated inside `20_drive_imports/notes/` and `20_drive_imports/zjk/`. |
| `@February 25, 2025.md` | 0 KB | Duplicated inside `20_drive_imports/` and `20_drive_imports/notes/`. |
| `54706 fill-in.pdf` | 279 KB | Duplicated in `qiportals/app/features/qidocs/public/` and `20_drive_imports/`. |
| `Rice-Velasquez - Tax Return 2023.pdf` | 562 KB | Duplicated personal tax archives. |
| `AES_Usage_Timeline.csv` | 0 KB | Duplicated CSV sheets between capture raw intake and schemas. |

---

## Conclusion & Safety Summary
*   **Duplicate File Deletions:** **0 files deleted.**
*   **Recommendation:** Leave Category 1 and 2 alone. Clean up Category 3 after sync is paused. Use Category 4 to train/test the RAG deduplication pipelines instead of deleting manually.
