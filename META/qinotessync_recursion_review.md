# Obsidian QiNotesSync Recursion Review

A review of the recursive nested folder structure identified inside the Obsidian sync folder.

---

## 1. Recursion Findings

### Recursive Path Chain
The folder structure has replicated itself down to multiple nested levels:
```text
C:\QiLabs\70_QiConnect\QiNotesSync\
  └── QiNotesSync\
        └── QiNotesSync\
              ├── Elliot-St/
              ├── Luis Palacios/
              ├── Templates/
              ├── Voice Entries/
              └── ...
```

### Duplication Depth
*   **Depth:** At least 3 levels of recursive folder nesting.
*   **Cause:** This usually occurs when a sync client (like Obsidian Sync, git synchronizers, or an automated copy script) is pointed to its own subdirectory or a parent directory, creating an infinite loop of replication.

### Representative Duplicate Files
The following files are replicated at every level of the recursive chain:
*   `2026-05-09_s_elliott_st_household_meeting_summary.md`
    *   `70_QiConnect/QiNotesSync/Elliot-St/2026-05-09_s_elliott_st_household_meeting_summary.md`
    *   `70_QiConnect/QiNotesSync/QiNotesSync/2026-05-09_s_elliott_st_household_meeting_summary.md`
    *   `70_QiConnect/QiNotesSync/QiNotesSync/Elliot-St/2026-05-09_s_elliott_st_household_meeting_summary.md`
    *   `70_QiConnect/QiNotesSync/QiNotesSync/QiNotesSync/2026-05-09_s_elliott_st_household_meeting_summary.md`
*   `Chatnotw.md`
*   `Complete_Legal_Estate_Package.md`
*   Voice Entries: `2026-05-125_171438__Entry.md`, `2026-05-125_171459__Entry.md`

---

## 2. Safety Recommendations & Cleanup Action Plan

> [!CAUTION]
> Do not delete nested directories while the Obsidian application or Obsidian Sync is actively running. This can cause sync conflicts, sync loops, or unintended deletion propagation to your other devices.

### Step-by-Step Recovery Plan
1.  **Pause Sync/Close Obsidian:** Close the Obsidian application on this machine and temporarily pause any automatic file-watchers or sync clients.
2.  **Backup the Vault:** Copy the entire directory `C:\QiLabs\70_QiConnect\QiNotesSync\` to a safe location outside of the workspace (e.g. `C:\QiLabs\_archive\QiNotesSync_backup`).
3.  **Perform Pruning:** Once sync is confirmed paused:
    *   Delete the directory `C:\QiLabs\70_QiConnect\QiNotesSync\QiNotesSync\` (this will clean up the inner nested copies, keeping only the outer `70_QiConnect\QiNotesSync\` vault intact).
4.  **Re-open Obsidian:** Re-open Obsidian and verify that the note vault looks clean and no files were lost.
5.  **Restart Sync:** Resume sync and monitor it to ensure it does not replicate the recursion loop.
