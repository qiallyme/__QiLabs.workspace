import os
from pathlib import Path

def identify_stubs(root_path):
    root = Path(root_path)
    if not root.exists():
        return

    results = []
    for d in [d for d in root.iterdir() if d.is_dir() and d.name != "experiments"]:
        total_files = 0
        total_size = 0
        file_list = []
        try:
            for p in d.rglob("*"):
                if p.is_file():
                    if p.name in [".DS_Store", "desktop.ini", ".gitignore"]: continue
                    total_files += 1
                    total_size += p.stat().st_size
                    if len(file_list) < 5: file_list.append(p.name)
        except: continue
        results.append({"name": d.name, "count": total_files, "size_kb": round(total_size / 1024, 2), "samples": file_list})

    # Sort results
    stubs = sorted([r for r in results if r["count"] <= 5], key=lambda x: x["count"])
    active = sorted([r for r in results if r["count"] > 5], key=lambda x: x["count"], reverse=True)

    with open(root / "stubs_report.md", "w", encoding="utf-8") as f:
        f.write("# 📂 Experiment Stub Report\n\n")
        f.write("## ⚠️ Potential Stubs (5 or fewer files)\n")
        if not stubs:
            f.write("No obvious stubs found.\n")
        else:
            for s in stubs:
                f.write(f"### 📁 `{s['name']}`\n")
                f.write(f"- **Files**: {s['count']}\n")
                f.write(f"- **Size**: {s['size_kb']} KB\n")
                f.write(f"- **Contents**: {', '.join(s['samples'])}\n\n")

        f.write("\n## 🚀 Populated Projects\n")
        for a in active:
            f.write(f"- `{a['name']}` ({a['count']} files)\n")

    print(f"Report written to {root / 'stubs_report.md'}")

if __name__ == "__main__":
    target = r"c:\_QiOne_MonoRepo_v2\experiments"
    identify_stubs(target)
