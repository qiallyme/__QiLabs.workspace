import os
import shutil

ROOT_DIR = os.getcwd()
FLAT_DIR = os.path.join(ROOT_DIR, '.flat')
TRASH_DIR = os.path.join(ROOT_DIR, '.trash')

os.makedirs(FLAT_DIR, exist_ok=True)
os.makedirs(TRASH_DIR, exist_ok=True)

conflicts = 0
moved = 0
trashed = 0

for dirpath, _, filenames in os.walk(ROOT_DIR):
    # Skip .flat and .trash to avoid loops
    if any(skip in dirpath for skip in ['.flat', '.trash']):
        continue

    for filename in filenames:
        src_path = os.path.join(dirpath, filename)
        flat_path = os.path.join(FLAT_DIR, filename)

        if not os.path.isfile(src_path):
            continue

        if os.path.exists(flat_path):
            # Compare sizes to resolve conflict
            src_size = os.path.getsize(src_path)
            flat_size = os.path.getsize(flat_path)

            if src_size > flat_size:
                # Move current flat file to trash, replace it
                trash_path = os.path.join(TRASH_DIR, filename)
                shutil.move(flat_path, trash_path)
                shutil.move(src_path, flat_path)
                trashed += 1
                conflicts += 1
            else:
                # Move incoming (smaller) file to trash
                trash_path = os.path.join(TRASH_DIR, filename)
                shutil.move(src_path, trash_path)
                trashed += 1
                conflicts += 1
        else:
            shutil.move(src_path, flat_path)
            moved += 1

print(f'\n✅ Flattened directory structure.')
print(f'📁 Files moved to .flat: {moved}')
print(f'⚠️  Merge conflicts resolved: {conflicts}')
print(f'🗑️  Files sent to .trash: {trashed}')
