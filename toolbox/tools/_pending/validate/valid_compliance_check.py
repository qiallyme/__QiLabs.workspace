import sys
import io

# Force UTF-8 for output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import csv
import os
from pathlib import Path

REPO_ROOT = Path("c:/_QiOne_MonoRepo_v2")
TARGET_CSV = REPO_ROOT / "docs/architecture/target-state.csv"
RULES_CSV = REPO_ROOT / "docs/architecture/non-negociable-rule.csv"

def get_target_state():
    targets = []
    if not TARGET_CSV.exists():
        return []
    with open(TARGET_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('path'):
                targets.append(row)
    return targets

def get_rules():
    rules = []
    if not RULES_CSV.exists():
        return []
    with open(RULES_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rules.append(row)
    return rules

def check():
    targets = get_target_state()
    rules = get_rules()
    
    report = ["# Architecture Compliance Report\n"]
    
    # 1. Check for missing required paths
    report.append("## ❌ Missing Required Paths")
    missing_count = 0
    for target in targets:
        path_str = target['path']
        if path_str == "QiOne_Organism": continue
        
        full_path = REPO_ROOT / path_str
        req = target.get('required', 'no').lower()
        if req == 'yes':
            if not full_path.exists():
                report.append(f"- `[MISSING]` {path_str} ({target.get('type', 'unknown')})")
                missing_count += 1
    if missing_count == 0:
        report.append("All required paths exist.")
    report.append("")

    # 2. Check for R001: Root folders not in CSV
    report.append("## ⚠️ Unexpected Root Items (R001 Violation)")
    root_items = os.listdir(REPO_ROOT)
    target_roots = set()
    for row in targets:
        p = row['path']
        if p == "QiOne_Organism": continue
        target_roots.add(p.split('/')[0])
    
    unexpected_roots = []
    allowed_roots = target_roots | {".git", "node_modules", ".trunk", ".idea", ".vscode", ".husky", "pnpm-lock.yaml", "package-lock.json", "yarn.lock"}
    for item in root_items:
        if item == "QiOne_Organism": continue
        if item not in allowed_roots:
            unexpected_roots.append(item)
            report.append(f"- {item}")
    if not unexpected_roots:
        report.append("No unexpected root items.")
    report.append("")

    # 3. Check for specific violations
    report.append("## 🛠️ Rule Violations")
    violations = []
    
    for root, dirs, files in os.walk(REPO_ROOT / "apps"):
        rel_root = Path(root).relative_to(REPO_ROOT)
        rel_root_str = str(rel_root).replace('\\', '/')
        
        # R003: No workers inside apps
        if "workers" in dirs and "qione" in rel_root_str:
             violations.append(f"- R003: worker folder found at {rel_root_str}/workers")
        
        # R004: No migrations in app folders (except the root supabase one)
        if "migrations" in dirs:
             # Allowed: root supabase/migrations
             if rel_root_str != "supabase":
                violations.append(f"- R004: migrations folder found at {rel_root_str}/migrations")

        # R005: No archive in app folders
        if "archive" in [d.lower() for d in dirs]:
             violations.append(f"- R005: archive folder found at {rel_root_str}/archive")

    if not violations:
        report.append("No rule violations detected in common areas.")
    else:
        report.extend(violations)
    
    report.append("")
    
    print("\n".join(report))

if __name__ == "__main__":
    check()

