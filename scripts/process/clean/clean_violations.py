import os
import shutil
from pathlib import Path

REPO_ROOT = Path("c:/_QiOne_MonoRepo_v2")

def move_migrations():
    migration_targets = [
        ("apps/qione/src/features/admin/exp_tududi/backend/migrations", "tududi"),
        ("apps/qione/src/features/ai/gina-ai-chat/data/migrations", "gina_chat"),
        ("apps/qione/src/features/ai/gina-ai-chat/workers/orchestrator/migrations", "gina_orchestrator"),
        ("apps/qione/src/features/contracts/accounts/migrations", "contracts_accounts"),
        ("apps/qione/src/features/contracts/cases/migrations", "contracts_cases"),
        ("apps/qione/src/features/contracts/contacts/migrations", "contracts_contacts"),
        ("apps/qione/src/features/contracts/QiCase/db/migrations", "qicase"),
        ("apps/qione/src/features/documents/app_QiNoteOS_ph00/data/migrations", "qinote_ph00"),
        ("apps/qione/src/features/documents/app_QiNoteOS_ph02_Paperless/src/documents/migrations", "paperless_docs"),
        ("apps/qione/src/features/documents/app_QiNoteOS_ph02_Paperless/src/paperless/migrations", "paperless_core"),
        ("apps/qione/src/features/documents/app_QiNoteOS_ph02_Paperless/src/paperless_mail/migrations", "paperless_mail"),
        ("apps/qione/src/features/documents/app_QiNoteOS_ph04_GINA/data/migrations", "gina_ph04"),
        ("apps/qione/src/features/documents/app_QiNoteOS_ph04_GINA/workers/orchestrator/migrations", "gina_ph04_orch"),
        ("apps/qione/supabase/migrations", "qione_old")
    ]
    
    dest_base = REPO_ROOT / "supabase/migrations"
    dest_base.mkdir(parents=True, exist_ok=True)
    
    for src_rel, prefix in migration_targets:
        src_path = REPO_ROOT / src_rel
        if src_path.exists():
            print(f"Moving migrations from {src_rel}...")
            for item in os.listdir(src_path):
                s = src_path / item
                d = dest_base / f"{prefix}_{item}"
                if s.is_file():
                    shutil.move(str(s), str(d))
                elif s.is_dir():
                    # If it's a directory, maybe merge? For now let's just move it with prefix
                    shutil.move(str(s), str(dest_base / f"{prefix}_{item}"))
            shutil.rmtree(src_path)

def move_workers():
    worker_targets = [
        ("apps/qione/src/app/(app)/admin/workers", "admin"),
        ("apps/qione/src/features/admin/exp_cases/workers", "cases"),
        ("apps/qione/src/features/ai/workers", "ai"),
        ("apps/qione/src/features/ai/exp_lina-lumara-ai-vite-full/workers", "lina"),
        ("apps/qione/src/features/ai/gina-ai-chat/workers", "gina"),
        ("apps/qione/src/features/documents/app_QiNoteOS_ph00/workers", "qinote_ph00"),
        ("apps/qione/src/features/documents/app_QiNoteOS_ph04_GINA/workers", "gina_processor")
    ]
    
    dest_base = REPO_ROOT / "workers"
    dest_base.mkdir(parents=True, exist_ok=True)
    
    for src_rel, name in worker_targets:
        src_path = REPO_ROOT / src_rel
        if src_path.exists():
            dest_path = dest_base / name
            print(f"Moving worker {src_rel} to {dest_path}...")
            if dest_path.exists():
                # Merge logic? For now let's append a suffix if exists
                dest_path = dest_base / f"{name}_migrated"
            shutil.move(str(src_path), str(dest_path))

def cleanup_archive():
    src = REPO_ROOT / "apps/qione/src/features/documents/app_QiNoteOS_ph02_Paperless/src/documents/tests/samples/documents/archive"
    dest = REPO_ROOT / "archive/legacy/samples/paperless_tests"
    if src.exists():
        print(f"Moving archive from {src} to {dest}...")
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))

if __name__ == "__main__":
    move_migrations()
    move_workers()
    cleanup_archive()
    print("Cleanup complete.")
