from pathlib import Path
from datetime import datetime

ROOT = Path.cwd()
CHRONICLE = ROOT / "00_QiEOS" / "exports" / "QiOS_DNA_Chronicle.md"
MANIFEST = ROOT / "20_QiSystem" / "manifests" / "QiOS_DNA_File_Manifest.md"

INCLUDE_EXTS = {".md", ".mdx", ".txt", ".json", ".yaml", ".yml", ".toml", ".sql"}
SKIP_DIRS = {
    ".git", "node_modules", "dist", "build", ".next", ".vite", "__pycache__",
    ".venv", "venv", ".wrangler", ".cache", ".pytest_cache"
}
SKIP_NAMES = {"QiOS_DNA_Chronicle.md"}


def should_skip(path: Path) -> bool:
    if set(path.parts) & SKIP_DIRS:
        return True
    if path.name in SKIP_NAMES:
        return True
    if path.suffix in {".log", ".tsbuildinfo"}:
        return True
    return False


def main() -> None:
    CHRONICLE.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)

    files = sorted(
        p for p in ROOT.rglob("*")
        if p.is_file()
        and p.suffix.lower() in INCLUDE_EXTS
        and not should_skip(p)
    )

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with MANIFEST.open("w", encoding="utf-8") as m:
        m.write("# QiOS DNA File Manifest\n\n")
        m.write(f"Generated: {now}\n\n")
        m.write(f"Total files indexed: {len(files)}\n\n")
        for p in files:
            m.write(f"- `{p.relative_to(ROOT)}`\n")

    with CHRONICLE.open("w", encoding="utf-8") as c:
        c.write("# QiOS DNA Chronicle\n\n")
        c.write(f"Generated: {now}\n\n")
        c.write("This is a generated review export. It is not canonical doctrine by itself.\n\n")
        c.write("---\n\n")
        for p in files:
            rel = p.relative_to(ROOT)
            c.write(f"# FILE: `{rel}`\n\n")
            c.write("```text\n")
            c.write(p.read_text(encoding="utf-8", errors="replace"))
            c.write("\n```\n\n---\n\n")

    print(f"Wrote {MANIFEST}")
    print(f"Wrote {CHRONICLE}")
    print(f"Indexed {len(files)} files.")


if __name__ == "__main__":
    main()
