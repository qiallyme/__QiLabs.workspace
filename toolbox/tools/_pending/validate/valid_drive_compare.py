#!/usr/bin/env python3
"""
Compare My Drive with QiOS:
1. Find duplicates in My Drive
2. Find files in My Drive not in QiOS
3. Identify outdated .md files for merging
"""
import hashlib
import re
from pathlib import Path
from collections import defaultdict
from difflib import SequenceMatcher

MY_DRIVE = Path(r"G:\My Drive")
QIOS_BASE = Path(r"C:\QiOS")

def get_file_hash(filepath, sample_size=None):
    """Calculate hash of file (full or sample)."""
    sha256 = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            if sample_size:
                chunk = f.read(sample_size)
                sha256.update(chunk)
            else:
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    sha256.update(chunk)
        return sha256.hexdigest()
    except Exception as e:
        return None

def normalize_path_for_comparison(filepath, base_dir):
    """Normalize path for comparison (relative to base)."""
    try:
        rel_path = filepath.relative_to(base_dir)
        # Normalize filename (remove Notion IDs, etc.)
        name = rel_path.name
        name = re.sub(r'[0-9a-f]{32,}', '', name, flags=re.IGNORECASE)
        name = re.sub(r'_all$', '', name, flags=re.IGNORECASE)
        name = name.strip()
        return str(rel_path.parent / name).lower()
    except:
        return None

def find_duplicates_in_mydrive():
    """Find duplicate files in My Drive."""
    print("Finding duplicates in My Drive...")
    files = list(MY_DRIVE.rglob('*'))
    files = [f for f in files if f.is_file()]
    
    # Group by size first (faster)
    size_groups = defaultdict(list)
    for f in files:
        try:
            size = f.stat().st_size
            size_groups[size].append(f)
        except:
            continue
    
    # Check hash for same-size files
    duplicates = []
    processed = set()
    
    for size, file_list in size_groups.items():
        if len(file_list) < 2 or size == 0:
            continue
        
        hash_groups = defaultdict(list)
        for f in file_list:
            if f in processed:
                continue
            file_hash = get_file_hash(f)
            if file_hash:
                hash_groups[file_hash].append(f)
        
        for file_hash, dup_files in hash_groups.items():
            if len(dup_files) > 1:
                # Keep newest, mark others as duplicates
                dup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                duplicates.append((dup_files[0], dup_files[1:]))
                processed.update(dup_files)
    
    return duplicates

def find_files_not_in_qios():
    """Find files in My Drive that don't exist in QiOS."""
    print("Finding files in My Drive not in QiOS...")
    
    # Get all QiOS files (normalized names)
    qios_files = set()
    for qios_file in QIOS_BASE.rglob('*'):
        if qios_file.is_file():
            norm = normalize_path_for_comparison(qios_file, QIOS_BASE)
            if norm:
                qios_files.add(norm)
    
    # Check My Drive files
    missing_in_qios = []
    mydrive_files = list(MY_DRIVE.rglob('*'))
    mydrive_files = [f for f in mydrive_files if f.is_file()]
    
    for md_file in mydrive_files:
        norm = normalize_path_for_comparison(md_file, MY_DRIVE)
        if norm and norm not in qios_files:
            # Check if similar file exists (fuzzy match)
            similar_found = False
            for qios_norm in qios_files:
                similarity = SequenceMatcher(None, norm, qios_norm).ratio()
                if similarity > 0.9:  # 90% similar
                    similar_found = True
                    break
            
            if not similar_found:
                missing_in_qios.append(md_file)
    
    return missing_in_qios

def find_outdated_md_files():
    """Find outdated .md files in My Drive that might need merging."""
    print("Finding outdated .md files for review...")
    
    outdated = []
    md_files = list(MY_DRIVE.rglob('*.md'))
    
    for md_file in md_files:
        try:
            # Check file age
            mtime = md_file.stat().st_mtime
            from datetime import datetime
            file_age_days = (datetime.now().timestamp() - mtime) / 86400
            
            # Check if similar file exists in QiOS
            norm_name = normalize_path_for_comparison(md_file, MY_DRIVE)
            found_in_qios = False
            
            if norm_name:
                for qios_file in QIOS_BASE.rglob('*.md'):
                    qios_norm = normalize_path_for_comparison(qios_file, QIOS_BASE)
                    if qios_norm and SequenceMatcher(None, norm_name, qios_norm).ratio() > 0.8:
                        found_in_qios = True
                        # Compare modification times
                        qios_mtime = qios_file.stat().st_mtime
                        if qios_mtime > mtime:
                            outdated.append({
                                'file': md_file,
                                'age_days': file_age_days,
                                'qios_version': qios_file,
                                'reason': 'newer_version_in_qios'
                            })
                        break
            
            # Files older than 90 days that might have unique info
            if file_age_days > 90 and not found_in_qios:
                outdated.append({
                    'file': md_file,
                    'age_days': file_age_days,
                    'qios_version': None,
                    'reason': 'old_and_not_in_qios'
                })
        except Exception as e:
            continue
    
    return outdated

def main():
    """Main comparison process."""
    print("=== My Drive vs QiOS Comparison ===\n")
    
    # 1. Find duplicates in My Drive
    print("1. Finding duplicates in My Drive...")
    duplicates = find_duplicates_in_mydrive()
    print(f"   Found {len(duplicates)} sets of duplicates\n")
    
    # 2. Find files not in QiOS
    print("2. Finding files in My Drive not in QiOS...")
    missing = find_files_not_in_qios()
    print(f"   Found {len(missing)} files not in QiOS\n")
    
    # 3. Find outdated .md files
    print("3. Finding outdated .md files for review...")
    outdated = find_outdated_md_files()
    print(f"   Found {len(outdated)} outdated .md files\n")
    
    # Generate report
    report = []
    report.append("=== My Drive vs QiOS Comparison Report ===\n\n")
    
    report.append(f"1. DUPLICATES IN MY DRIVE: {len(duplicates)} sets\n")
    report.append("   (These can be removed from My Drive)\n\n")
    total_dup_size = 0
    for keep_file, dup_files in duplicates[:50]:  # Show first 50
        size = sum(f.stat().st_size for f in dup_files)
        total_dup_size += size
        report.append(f"   Keep: {keep_file.relative_to(MY_DRIVE)}\n")
        for dup in dup_files:
            report.append(f"     Remove: {dup.relative_to(MY_DRIVE)}\n")
        report.append(f"     Space to free: {size / 1024 / 1024:.2f} MB\n\n")
    
    report.append(f"\n   Total space that could be freed: {total_dup_size / 1024 / 1024:.2f} MB\n\n")
    
    report.append(f"2. FILES IN MY DRIVE NOT IN QIOS: {len(missing)} files\n")
    report.append("   (These should be copied to QiOS)\n\n")
    for f in missing[:100]:  # Show first 100
        rel_path = f.relative_to(MY_DRIVE)
        size = f.stat().st_size
        report.append(f"   {rel_path} ({size / 1024:.2f} KB)\n")
    
    report.append(f"\n3. OUTDATED .MD FILES FOR REVIEW: {len(outdated)} files\n")
    report.append("   (These may have useful info to merge into QiOS/QiVault KB)\n\n")
    
    # Group by reason
    by_reason = defaultdict(list)
    for item in outdated:
        by_reason[item['reason']].append(item)
    
    for reason, items in by_reason.items():
        report.append(f"   {reason}: {len(items)} files\n")
        for item in items[:20]:  # Show first 20 of each
            rel_path = item['file'].relative_to(MY_DRIVE)
            report.append(f"     {rel_path} (age: {item['age_days']:.0f} days)\n")
            if item['qios_version']:
                qios_rel = item['qios_version'].relative_to(QIOS_BASE)
                report.append(f"       → QiOS version: {qios_rel}\n")
        report.append("\n")
    
    report_path = QIOS_BASE / "_inbox" / "mydrive_qios_comparison.txt"
    report_path.write_text(''.join(report), encoding='utf-8')
    print(f"\nReport saved to: {report_path}")
    
    return duplicates, missing, outdated

if __name__ == '__main__':
    main()
