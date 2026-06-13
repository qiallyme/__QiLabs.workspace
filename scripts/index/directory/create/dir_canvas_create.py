#!/usr/bin/env python3
"""
generate_obsidian_canvas.py

Create an Obsidian Canvas mind map (.canvas) that visualizes a folder tree.

- Each *folder* becomes a "text" node (markdown), optionally listing its files.
- Each *file* can become a "file" node (Obsidian will open it) using vault‑relative paths.
- Parent/child relationships are connected with edges.
- Simple tree layout with configurable spacing.

USAGE
-----
python generate_obsidian_canvas.py \
  --root "/path/to/your/vault/Subfolder" \
  --vault-root "/path/to/your/vault" \
  --out "/path/to/save/YourMap.canvas" \
  --max-depth 3 \
  --include-files \
  --ignore ".git" ".obsidian" "node_modules" "venv" "__pycache__" \
  --h-gap 320 --v-gap 140

Notes
-----
- If you pass --vault-root, file nodes will be written using vault‑relative paths (recommended).
- If you omit --vault-root, file nodes will use paths relative to --root.
- Obsidian supports node types: "text", "file", "link", "group". We use "text" for folders, "file" for files.
- This produces a lightweight hierarchical layout. You can drag things around after opening in Obsidian.

Canvas JSON shape (compatible with Obsidian):
{
  "nodes": [
    {"id": "...","type":"text","text":"...","x":0,"y":0,"width":260,"height":160,"color":"4"},
    {"id": "...","type":"file","file":"Path/To/Note.md","x":0,"y":0,"width":260,"height":80,"color":"3"}
  ],
  "edges": [
    {"id":"...","fromNode":"...","fromSide":"bottom","toNode":"...","toSide":"top"}
  ]
}
"""
import argparse
import json
from pathlib import Path
import uuid

def gen_id() -> str:
    return uuid.uuid4().hex[:16]

def is_ignored(path: Path, ignore_names: set[str]) -> bool:
    parts = set(p.name for p in path.parts)
    return any(name in parts for name in ignore_names)

def shorten(text: str, limit: int = 120) -> str:
    s = text.strip()
    return s if len(s) <= limit else s[: limit - 1] + "…"

def folder_markdown(folder: Path, files: list[Path], relbase: Path, max_files: int = 25) -> str:
    """Build markdown for a folder node: a header + a bulleted list of contained files (truncated)."""
    header = f"## {folder.name}"
    bullet_lines = []
    for fp in files[:max_files]:
        rel = fp.relative_to(relbase) if fp.is_absolute() and relbase and fp.is_relative_to(relbase) else fp
        bullet_lines.append(f"- {rel.as_posix()}")
    if len(files) > max_files:
        bullet_lines.append(f"- …(+{len(files) - max_files} more)")
    return header + ("\n" + "\n".join(bullet_lines) if bullet_lines else "")

def collect_tree(root: Path, max_depth: int, include_files: bool, ignore: set[str]) -> dict:
    """Walk the directory up to max_depth and return {folder: {"subfolders": [...], "files": [...]}}"""
    root = root.resolve()
    tree = {}

    for current, dirs, files in _walk(root, max_depth, ignore):
        cur_path = Path(current)
        subfolders = [cur_path / d for d in dirs if not is_ignored(cur_path / d, ignore)]
        file_paths = [cur_path / f for f in files] if include_files else []
        tree[cur_path] = {"subfolders": subfolders, "files": file_paths}

    return tree

def _walk(root: Path, max_depth: int, ignore: set[str]):
    """Like os.walk with depth limit and ignore set."""
    import os
    root = root.resolve()
    for current, dirs, files in os.walk(root):
        # filter dirs in-place for depth & ignore
        rel = Path(current).relative_to(root)
        depth = len(rel.parts)
        # remove ignored dirs
        dirs[:] = [d for d in dirs if not is_ignored(Path(current) / d, ignore)]
        if max_depth is not None and depth >= max_depth:
            # don't descend further
            dirs[:] = []
        yield current, dirs, files

def layout_tree(tree: dict, root: Path, h_gap: int, v_gap: int) -> tuple[list[dict], list[dict]]:
    """
    Produce nodes/edges for the canvas with a simple top-down tree layout.
    Folders become 'text' nodes; files become 'file' nodes under their parent folder.
    """
    nodes = []
    edges = []
    color_cycle = ["1","2","3","4","5","6"]

    # We'll compute x/y by DFS, tracking column (x) by depth and row (y) incrementally
    y_cursor = {0: 0}  # depth -> next y
    node_id_for_path = {}

    def place_folder(folder: Path, depth: int):
        nonlocal nodes, edges
        col_x = depth * h_gap
        y = y_cursor.get(depth, 0)

        info = tree.get(folder, {"subfolders": [], "files": []})
        # build markdown with a short file list preview
        md = folder_markdown(folder, info["files"], folder, max_files=20)

        nid = gen_id()
        node_id_for_path[folder] = nid
        nodes.append({
            "id": nid,
            "type": "text",
            "text": md,
            "x": col_x,
            "y": y,
            "width": 260,
            "height": 180,
            "color": color_cycle[depth % len(color_cycle)],
        })

        # increment y for next node at this depth
        y_cursor[depth] = y + v_gap

        # add file nodes beneath (slightly indented)
        file_y = y + 30
        for f in info["files"][:25]:
            fid = gen_id()
            nodes.append({
                "id": fid,
                "type": "file",
                "file": f.as_posix(),  # We adjust to vault-relative later if requested
                "x": col_x + int(h_gap * 0.35),
                "y": file_y,
                "width": 340,
                "height": 60,
                "color": color_cycle[(depth + 1) % len(color_cycle)],
            })
            edges.append({
                "id": gen_id(),
                "fromNode": nid,
                "fromSide": "bottom",
                "toNode": fid,
                "toSide": "top",
            })
            file_y += 70

        # recurse into subfolders
        for sub in info["subfolders"]:
            place_folder(sub, depth + 1)
            # connect folder -> subfolder
            if sub in node_id_for_path:
                edges.append({
                    "id": gen_id(),
                    "fromNode": nid,
                    "fromSide": "bottom",
                    "toNode": node_id_for_path[sub],
                    "toSide": "top",
                })

    place_folder(root, 0)
    return nodes, edges

def make_paths_vault_relative(nodes: list[dict], vault_root: Path, root: Path):
    """Convert any 'file' node paths to be relative to the vault root (best for Obsidian)."""
    vault_root = vault_root.resolve()
    for n in nodes:
        if n.get("type") == "file" and "file" in n:
            fp = Path(n["file"])
            if not fp.is_absolute():
                # file path currently relative to root; make absolute so we can relativize to vault
                fp = (root / fp).resolve()
            try:
                rel = fp.relative_to(vault_root)
                n["file"] = rel.as_posix()
            except ValueError:
                # file not inside vault_root; leave as-is (Obsidian may not open it)
                pass

def main():
    ap = argparse.ArgumentParser(description="Generate an Obsidian Canvas mind map from a folder tree.")
    ap.add_argument("--root", type=Path, required=True, help="Folder to visualize (can be your whole vault or any subfolder).")
    ap.add_argument("--vault-root", type=Path, default=None, help="Vault root (so file nodes are vault‑relative).")
    ap.add_argument("--out", type=Path, required=True, help="Output .canvas file path.")
    ap.add_argument("--max-depth", type=int, default=3, help="How many folder levels to include (0 = only the root).")
    ap.add_argument("--include-files", action="store_true", help="Include file nodes below each folder.")
    ap.add_argument("--h-gap", type=int, default=320, help="Horizontal gap (px) between columns.")
    ap.add_argument("--v-gap", type=int, default=140, help="Vertical gap (px) between rows.")
    ap.add_argument("--ignore", nargs="*", default=[".git",".obsidian","node_modules","venv","__pycache__",".idea",".vscode"],
                    help="Folder names to ignore anywhere in the path.")
    args = ap.parse_args()

    root = args.root.resolve()
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"Root folder does not exist or is not a directory: {root}")

    tree = collect_tree(root=root, max_depth=args.max_depth, include_files=args.include_files, ignore=set(args.ignore))
    nodes, edges = layout_tree(tree, root, h_gap=args.h_gap, v_gap=args.v_gap)

    # If vault-root is provided, normalize file node paths to be vault‑relative.
    if args.vault_root:
        make_paths_vault_relative(nodes, args.vault_root, root)

    canvas = {"nodes": nodes, "edges": edges}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(canvas, indent=2), encoding="utf-8")
    print(f"Wrote canvas: {args.out} (nodes={len(nodes)}, edges={len(edges)})")

if __name__ == "__main__":
    main()
