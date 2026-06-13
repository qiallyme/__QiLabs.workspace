import os
import json
import uuid
from pathlib import Path

# ----------------------------
# Color palette & helpers
# ----------------------------

# Logical palette: ROYGBIV (these are Obsidian canvas color IDs as strings)
# You may need to tweak these numbers to match your theme's actual colors.
ROYGBIV = ["2", "3", "4", "5", "6", "7", "1"]  # just an example mapping
ROOT_COLOR = "1"  # treat as "blue" for the top node


def generate_id() -> str:
    """Generate a short unique id for canvas nodes/edges."""
    return uuid.uuid4().hex[:16]


def get_relative_obsidian_path(root: Path, target: Path) -> str:
    """
    Return a relative path in Obsidian format (forward slashes, no .md extension).
    Example: 'QiVault/0_eos/index'
    """
    rel = target.relative_to(root)
    rel_str = str(rel).replace(os.sep, "/")
    if rel_str.lower().endswith(".md"):
        rel_str = rel_str[:-3]  # drop .md
    return rel_str


def ensure_folder_index(root: Path, folder: Path) -> Path:
    """
    Ensure folder has an index.md. If not, create it with a simple template:
    # [[relative/path/index]]
    `Path: relative/path`
    Returns the Path to index.md.
    """
    index_path = folder / "index.md"
    if not index_path.exists():
        folder_rel = folder.relative_to(root)
        folder_rel_str = str(folder_rel).replace(os.sep, "/") if str(folder_rel) != "." else "."
        link_rel = get_relative_obsidian_path(root, index_path)
        index_content = f"# [[{link_rel}]]\n\n`Path: {folder_rel_str}`\n"
        index_path.write_text(index_content, encoding="utf-8")
        print(f"[+] Created index.md for folder: {folder}")
    return index_path


# ----------------------------
# Layout manager
# ----------------------------

class LayoutManager:
    """
    Simple layout engine: stack nodes by depth,
    spaced horizontally by sequence index.
    """
    def __init__(self, x_step=260, y_step=140):
        self.x_step = x_step
        self.y_step = y_step
        # depth -> next x slot index
        self.depth_counters = {}

    def get_position(self, depth: int) -> tuple[int, int]:
        idx = self.depth_counters.get(depth, 0)
        self.depth_counters[depth] = idx + 1
        x = (idx - 3) * self.x_step  # slight left shift
        y = depth * self.y_step
        return x, y


# ----------------------------
# Main builder
# ----------------------------

def build_canvas_for_directory(root_dir: Path, max_depth: int, include_files: bool) -> dict:
    """
    Walk the directory tree and produce a canvas JSON dict.
    Color rules:
      - Root node: ROOT_COLOR
      - Children of root: ROYGBIV sequence by sibling index
      - All deeper descendants: inherit parent's color
    """
    nodes = []
    edges = []

    layout = LayoutManager()

    # Maps
    path_to_id: dict[Path, str] = {}
    node_colors: dict[str, str] = {}

    root_dir = root_dir.resolve()

    # Root node
    root_id = "root-" + generate_id()
    path_to_id[root_dir] = root_id
    x, y = layout.get_position(0)

    root_label = root_dir.name
    root_node = {
        "id": root_id,
        "type": "text",
        "text": root_label,
        "x": x,
        "y": y - 200,  # shift root up a bit
        "width": 260,
        "height": 70,
        "color": ROOT_COLOR
    }
    nodes.append(root_node)
    node_colors[root_id] = ROOT_COLOR

    # Track which color to use for each first-level child of root (ROYGBIV rotation)
    first_level_index = 0

    # Walk directory
    for current_dir, dirnames, filenames in os.walk(root_dir):
        current_path = Path(current_dir)
        rel = current_path.relative_to(root_dir)
        depth = 0 if str(rel) == "." else len(rel.parts)

        if depth > max_depth:
            # Stop scanning deeper
            dirnames[:] = []
            continue

        # Ensure there is a node for this directory (except root, already done)
        if current_path not in path_to_id:
            # This case shouldn't occur often, but keep it safe.
            dir_id = "dir-" + generate_id()
            path_to_id[current_path] = dir_id
            x, y = layout.get_position(depth)

            # Find parent path to get color
            if current_path == root_dir:
                parent_color = ROOT_COLOR
            else:
                parent_path = current_path.parent
                parent_id = path_to_id.get(parent_path, root_id)
                parent_color = node_colors.get(parent_id, ROOT_COLOR)

            color = parent_color
            index_path = ensure_folder_index(root_dir, current_path)
            link = get_relative_obsidian_path(root_dir, index_path)
            node = {
                "id": dir_id,
                "type": "text",
                "text": f"[[{link}]]",
                "x": x,
                "y": y,
                "width": 220,
                "height": 60,
                "color": color
            }
            nodes.append(node)
            node_colors[dir_id] = color

        parent_id = path_to_id[current_path]
        parent_color = node_colors[parent_id]

        # Handle subdirectories
        for d in sorted(dirnames):
            child_dir = current_path / d
            child_rel = child_dir.relative_to(root_dir)
            child_depth = len(child_rel.parts)

            if child_depth > max_depth:
                continue

            dir_id = "dir-" + generate_id()
            path_to_id[child_dir] = dir_id
            x, y = layout.get_position(child_depth)

            # Color selection:
            # - If parent is root -> ROYGBIV sequence
            # - Else -> inherit parent's color
            if parent_id == root_id:
                color = ROYGBIV[first_level_index % len(ROYGBIV)]
                first_level_index += 1
            else:
                color = parent_color

            index_path = ensure_folder_index(root_dir, child_dir)
            link = get_relative_obsidian_path(root_dir, index_path)
            node = {
                "id": dir_id,
                "type": "text",
                "text": f"[[{link}]]",
                "x": x,
                "y": y,
                "width": 220,
                "height": 60,
                "color": color
            }
            nodes.append(node)
            node_colors[dir_id] = color

            edge = {
                "id": "edge-" + generate_id(),
                "fromNode": parent_id,
                "fromSide": "bottom",
                "toNode": dir_id,
                "toSide": "top"
            }
            edges.append(edge)

        # Handle files
        if include_files:
            for f in sorted(filenames):
                # Skip canvas files & index to avoid redundant nodes
                if f.lower().endswith(".canvas"):
                    continue
                if f.lower() == "index.md":
                    continue

                file_path = current_path / f
                file_rel = file_path.relative_to(root_dir)
                file_depth = len(file_rel.parts)

                if file_depth > max_depth:
                    continue

                file_id = "file-" + generate_id()
                path_to_id[file_path] = file_id
                x, y = layout.get_position(file_depth)

                color = parent_color  # inherit folder color
                link = get_relative_obsidian_path(root_dir, file_path)
                node = {
                    "id": file_id,
                    "type": "text",
                    "text": f"[[{link}]]",
                    "x": x,
                    "y": y,
                    "width": 240,
                    "height": 60,
                    "color": color
                }
                nodes.append(node)

                edge = {
                    "id": "edge-" + generate_id(),
                    "fromNode": parent_id,
                    "fromSide": "bottom",
                    "toNode": file_id,
                    "toSide": "top"
                }
                edges.append(edge)

    return {"nodes": nodes, "edges": edges}


# ----------------------------
# CLI / Mini-app
# ----------------------------

def main():
    print("=== QiOS / Obsidian Directory → Canvas Exporter ===")

    root_input = input("Root directory to scan (vault root or subfolder): ").strip().strip('"')
    if not root_input:
        print("No directory given. Exiting.")
        return

    root_dir = Path(root_input)
    if not root_dir.exists() or not root_dir.is_dir():
        print(f"Path does not exist or is not a directory: {root_dir}")
        return

    depth_input = input("Max depth (0 = only this folder, 1 = +children, etc.): ").strip()
    try:
        max_depth = int(depth_input)
    except ValueError:
        print("Invalid depth. Using default = 3.")
        max_depth = 3

    include_files_input = input("Include files as nodes? (y/n): ").strip().lower()
    include_files = include_files_input in ("y", "yes")

    canvas_filename = input("Canvas output filename (default: dir_map.canvas): ").strip()
    if not canvas_filename:
        canvas_filename = "dir_map.canvas"
    if not canvas_filename.lower().endswith(".canvas"):
        canvas_filename += ".canvas"

    print(f"\n[•] Scanning: {root_dir}")
    print(f"[•] Max depth: {max_depth}")
    print(f"[•] Include files: {include_files}")
    print(f"[•] Output canvas: {canvas_filename}\n")

    canvas_data = build_canvas_for_directory(root_dir, max_depth, include_files)

    out_path = root_dir / canvas_filename
    out_path.write_text(json.dumps(canvas_data, indent=2), encoding="utf-8")
    print(f"[✓] Canvas written to: {out_path}")
    print("Open it in Obsidian (it’s just a .canvas file).")


if __name__ == "__main__":
    main()
