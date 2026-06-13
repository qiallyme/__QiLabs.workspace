# file: build_QiOne_Tools.py
# purpose: Interactive build script for QiOne Desktop Tools using the final bucketed toolbox/tools structure.
# usage: Open in IDE and hit Run, or run build_qione.bat.
# inputs: main_ui.py, tools/<bucket>/<tool>/<tool>.py, requirements.txt, file_version_info.txt.
# outputs: PyInstaller build artifacts in build/ and dist/.
# safety: Interactive. Kills running app only when selected. Does not modify tools; only injects imports/registrations into main_ui.py and optionally bumps version.
# owner: QiLabs

import argparse
import os
import re
import subprocess
import sys
from collections import Counter

APP_NAME = "QiOne_Tools"
ENTRY_FILE = "main_ui.py"
TOOLS_DIR = "tools"
VERSION_FILE = "file_version_info.txt"
REQUIREMENTS_FILE = "requirements.txt"
DEFAULT_HIDDEN_IMPORTS = ["send2trash"]

AUTO_IMPORTS_START = "# --- AUTO-IMPORTS START ---"
AUTO_IMPORTS_END = "# --- AUTO-IMPORTS END ---"
AUTO_REGISTER_START = "# --- AUTO-REGISTER START ---"
AUTO_REGISTER_END = "# --- AUTO-REGISTER END ---"

PRESETS = {
    "dev-fast": {
        "mode": "dev",
        "clean": False,
        "console": False,
        "debug": False,
        "install": False,
        "kill": True,
        "bump": False,
        "description": "Fast dev build -> onedir, windowed, no clean",
    },
    "dev-clean": {
        "mode": "dev",
        "clean": True,
        "console": False,
        "debug": False,
        "install": False,
        "kill": True,
        "bump": False,
        "description": "Clean dev build -> onedir, windowed, clean first",
    },
    "dev-debug": {
        "mode": "dev",
        "clean": False,
        "console": True,
        "debug": True,
        "install": False,
        "kill": True,
        "bump": False,
        "description": "Debug dev build -> onedir, console, bootloader debug",
    },
    "release": {
        "mode": "release",
        "clean": False,
        "console": False,
        "debug": False,
        "install": False,
        "kill": True,
        "bump": True,
        "description": "Release build -> onefile, windowed, version bump",
    },
    "release-clean": {
        "mode": "release",
        "clean": True,
        "console": False,
        "debug": False,
        "install": False,
        "kill": True,
        "bump": True,
        "description": "Clean release build -> onefile, windowed, clean first, version bump",
    },
}


def run(cmd, check=True, shell=False, stdout=None, stderr=None):
    return subprocess.run(
        cmd,
        check=check,
        shell=shell,
        stdout=stdout,
        stderr=stderr,
        text=False,
    )


def print_header():
    print("=" * 72)
    print("                    QILABS UNIFIED BUILD SYSTEM")
    print("=" * 72)
    print()


def validate_marker_blocks():
    if not os.path.isfile(ENTRY_FILE):
        raise FileNotFoundError(f"{ENTRY_FILE} not found.")

    with open(ENTRY_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    missing = []
    for marker in [AUTO_IMPORTS_START, AUTO_IMPORTS_END, AUTO_REGISTER_START, AUTO_REGISTER_END]:
        if marker not in content:
            missing.append(marker)

    if missing:
        joined = "\n  - ".join(missing)
        raise RuntimeError(
            f"{ENTRY_FILE} is missing required auto-generation markers:\n"
            f"  - {joined}\n\n"
            f"Fix {ENTRY_FILE} first. The builder will not inject imports or tools without those blocks."
        )


def kill_active_app():
    print("[0/6] Sweeping for running app instances...")
    if os.name == "nt":
        run(
            ["taskkill", "/f", "/im", f"{APP_NAME}.exe", "/t"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print("      -> Background app sweep complete.")
    else:
        print("      -> Skipped (non-Windows).")


def install_requirements():
    print("[1/6] Installing requirements...")
    if not os.path.isfile(REQUIREMENTS_FILE):
        print(f"      -> {REQUIREMENTS_FILE} not found. Skipping.")
        return

    run([sys.executable, "-m", "pip", "install", "-r", REQUIREMENTS_FILE, "--break-system-packages"], check=True)
    print("      -> Requirements installed successfully.")


def make_unique_alias(module_name, class_name):
    base = module_name.replace(".py", "")
    parts = [p for p in base.split("_") if p]
    prefix = "".join(p.capitalize() for p in parts)

    if prefix.endswith("Tool") and class_name.startswith(prefix):
        return class_name

    return f"{prefix}{class_name}"


def get_tool_modules():
    """
    Scan final bucketed toolbox modules.

    Final expected shape:
        tools/<bucket>/<tool>/<tool>.py

    Example:
        tools/docs/pdf_splitter/pdf_splitter.py
        -> import module: tools.docs.pdf_splitter
        -> injected line: from tools.docs.pdf_splitter import BulkPdfSplitterTool
    """
    print("[1/6] Scanning bucketed tool modules...")

    if not os.path.isdir(TOOLS_DIR):
        raise FileNotFoundError(f"Tools directory not found: {TOOLS_DIR}")

    raw_tools = []

    skip_dirs = {
        "__pycache__",
        "_legacy_stubs",
        "_archive",
        "_audit",
        "_backup",
        "_migration_reports",
    }

    skip_files = {"__init__.py"}

    def scan_file(filepath, import_module_name):
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        match = re.search(r"class\s+([A-Za-z0-9_]+)\s*\(([^)]*BaseTool[^)]*)\)\s*:", content)
        if not match:
            return

        raw_tools.append({
            "module": import_module_name,
            "class_name": match.group(1),
            "path": filepath,
        })

    for bucket in sorted(os.listdir(TOOLS_DIR)):
        bucket_path = os.path.join(TOOLS_DIR, bucket)

        if not os.path.isdir(bucket_path):
            continue
        if bucket.startswith("_") or bucket in skip_dirs:
            continue

        for tool_name in sorted(os.listdir(bucket_path)):
            tool_path = os.path.join(bucket_path, tool_name)

            if not os.path.isdir(tool_path):
                continue
            if tool_name.startswith("_") or tool_name in skip_dirs:
                continue

            preferred_file = os.path.join(tool_path, f"{tool_name}.py")
            import_module_name = f"{bucket}.{tool_name}"

            if os.path.isfile(preferred_file):
                scan_file(preferred_file, import_module_name)
                continue

            # Fallback: scan the first real Python source file inside the tool folder.
            for filename in sorted(os.listdir(tool_path)):
                if not filename.endswith(".py") or filename in skip_files:
                    continue

                fallback_file = os.path.join(tool_path, filename)
                scan_file(fallback_file, import_module_name)
                break

    if not raw_tools:
        return []

    class_counts = Counter(t["class_name"] for t in raw_tools)

    for tool in raw_tools:
        if class_counts[tool["class_name"]] == 1:
            tool["alias"] = tool["class_name"]
        else:
            safe_module_name = tool["module"].replace(".", "_")
            tool["alias"] = make_unique_alias(safe_module_name, tool["class_name"])

    print(f"      -> Found {len(raw_tools)} valid bucketed tool modules.")
    for tool in raw_tools:
        print(f"         - tools.{tool['module']}::{tool['class_name']}")

    return raw_tools



def update_main_ui(tool_data):
    print("[2/6] Injecting tools into main_ui.py...")
    validate_marker_blocks()

    with open(ENTRY_FILE, "r", encoding="utf-8") as f:
        ui_content = f.read()

    imports_lines = []
    register_items = []

    for tool in tool_data:
        module_name = tool["module"]
        class_name = tool["class_name"]
        alias = tool["alias"]

        if alias == class_name:
            imports_lines.append(f"from tools.{module_name} import {class_name}")
        else:
            imports_lines.append(f"from tools.{module_name} import {class_name} as {alias}")

        register_items.append(f"{alias}()")

    imports_str = "\n".join(imports_lines)
    register_str = "self.tools = [" + ", ".join(register_items) + "]"

    ui_content = re.sub(
        rf"{re.escape(AUTO_IMPORTS_START)}.*?{re.escape(AUTO_IMPORTS_END)}",
        f"{AUTO_IMPORTS_START}\n{imports_str}\n{AUTO_IMPORTS_END}",
        ui_content,
        flags=re.DOTALL,
    )

    ui_content = re.sub(
        rf"{re.escape(AUTO_REGISTER_START)}.*?{re.escape(AUTO_REGISTER_END)}",
        f"{AUTO_REGISTER_START}\n        {register_str}\n        {AUTO_REGISTER_END}",
        ui_content,
        flags=re.DOTALL,
    )

    with open(ENTRY_FILE, "w", encoding="utf-8") as f:
        f.write(ui_content)

    print(f"      -> Successfully registered {len(tool_data)} tools.")


def bump_version():
    print("[3/6] Bumping application version...")

    if not os.path.isfile(VERSION_FILE):
        print(f"      -> {VERSION_FILE} not found. Skipping version bump.")
        return

    with open(VERSION_FILE, "r", encoding="utf-8") as f:
        v_content = f.read()

    match = re.search(r"filevers=\((\d+),\s*(\d+),\s*(\d+),\s*(\d+)\)", v_content)
    if not match:
        print("      -> Could not find filevers tuple. Skipping bump.")
        return

    major, minor, patch, build = match.groups()
    old_patch = int(patch)
    new_patch = old_patch + 1

    old_tuple = f"({major}, {minor}, {old_patch}, {build})"
    new_tuple = f"({major}, {minor}, {new_patch}, {build})"

    old_str = f"u'{major}.{minor}.{old_patch}'"
    new_str = f"u'{major}.{minor}.{new_patch}'"

    v_content = v_content.replace(old_tuple, new_tuple)
    v_content = v_content.replace(old_str, new_str)

    with open(VERSION_FILE, "w", encoding="utf-8") as f:
        f.write(v_content)

    print(f"      -> Version bumped from {major}.{minor}.{old_patch} to {major}.{minor}.{new_patch}")


def clean_build_artifacts():
    print("[4/6] Cleaning old build artifacts...")

    if os.name == "nt":
        run("rmdir /s /q build", check=False, shell=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        run("rmdir /s /q dist", check=False, shell=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        run("del /q *.spec", check=False, shell=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    else:
        run(["rm", "-rf", "build"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        run(["rm", "-rf", "dist"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        run(["sh", "-c", "rm -f *.spec"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print("      -> Clean complete.")


def compile_exe(*, mode="dev", clean=False, console=False, debug=False):
    if clean:
        clean_build_artifacts()
    else:
        print("[4/6] Skipping clean for faster incremental build.")

    print("[5/6] Triggering PyInstaller...\n")

    pyinstaller_cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--name",
        APP_NAME,
        "--version-file",
        VERSION_FILE,
    ]

    if console:
        pyinstaller_cmd.append("--console")
    else:
        pyinstaller_cmd.append("--windowed")

    if debug:
        pyinstaller_cmd.append("--debug=bootloader")

    for hidden_import in DEFAULT_HIDDEN_IMPORTS:
        pyinstaller_cmd.extend(["--hidden-import", hidden_import])

    if mode == "release":
        pyinstaller_cmd.append("--onefile")
    else:
        pyinstaller_cmd.append("--onedir")

    pyinstaller_cmd.append(ENTRY_FILE)

    run(pyinstaller_cmd, check=True)

    print("\n" + "=" * 72)
    print(f"[DONE] {mode.upper()} BUILD COMPLETE. Check the 'dist' folder.")
    print("=" * 72)


def run_pipeline(config):
    print()
    print("=" * 72)
    print("Running build...")
    print("=" * 72)

    if config["kill"]:
        kill_active_app()
    else:
        print("[0/6] Skipping running-app sweep.")

    if config["install"]:
        install_requirements()
    else:
        print("[0.5/6] Skipping requirements install for faster build.")

    tools = get_tool_modules()
    if not tools:
        raise RuntimeError("No valid tools found in the /tools directory.")

    update_main_ui(tools)

    if config["bump"]:
        bump_version()
    else:
        print("[3/6] Skipping version bump.")

    compile_exe(
        mode=config["mode"],
        clean=config["clean"],
        console=config["console"],
        debug=config["debug"],
    )


def prompt_choice():
    print("Choose build type:")
    print("  1) Dev Fast       -> onedir, windowed, no clean")
    print("  2) Dev Clean      -> onedir, windowed, clean first")
    print("  3) Dev Debug      -> onedir, console, bootloader debug")
    print("  4) Release        -> onefile, windowed, version bump")
    print("  5) Release Clean  -> onefile, windowed, clean first, version bump")
    print("  Q) Quit")
    print()

    mapping = {
        "1": "dev-fast",
        "2": "dev-clean",
        "3": "dev-debug",
        "4": "release",
        "5": "release-clean",
    }

    while True:
        choice = input("Selection: ").strip().lower()
        if choice == "q":
            return None
        if choice in mapping:
            return mapping[choice]
        print("Invalid choice. Pick 1, 2, 3, 4, 5, or Q.\n")


def prompt_yes_no(message, default=False):
    suffix = " [Y/n]: " if default else " [y/N]: "
    while True:
        raw = input(message + suffix).strip().lower()
        if raw == "":
            return default
        if raw in {"y", "yes"}:
            return True
        if raw in {"n", "no"}:
            return False
        print("Please answer y or n.")


def interactive_main():
    print_header()
    preset_name = prompt_choice()

    if preset_name is None:
        print("Exiting.")
        return

    config = PRESETS[preset_name].copy()

    print()
    print(f"Preset:         {preset_name}")
    print(f"Description:    {config['description']}")
    print()

    config["install"] = prompt_yes_no("Install requirements first?", default=config["install"])
    config["kill"] = prompt_yes_no("Kill running packaged app first?", default=config["kill"])
    config["bump"] = prompt_yes_no("Bump version before build?", default=config["bump"])

    if config["mode"] == "dev":
        config["clean"] = prompt_yes_no("Clean build artifacts first?", default=config["clean"])
        if preset_name != "dev-debug":
            debug_mode = prompt_yes_no("Use debug console build?", default=False)
            if debug_mode:
                config["console"] = True
                config["debug"] = True
        else:
            print("Debug console build already enabled for this preset.")
    else:
        config["clean"] = prompt_yes_no("Clean build artifacts first?", default=config["clean"])

    print()
    print("Final build config:")
    print(f"  mode:         {config['mode']}")
    print(f"  clean:        {config['clean']}")
    print(f"  console:      {config['console']}")
    print(f"  debug:        {config['debug']}")
    print(f"  install:      {config['install']}")
    print(f"  kill:         {config['kill']}")
    print(f"  bump:         {config['bump']}")
    print()

    if not prompt_yes_no("Start build now?", default=True):
        print("Cancelled.")
        return

    try:
        run_pipeline(config)
    except subprocess.CalledProcessError as e:
        print("\n" + "!" * 72)
        print("BUILD FAILED.")
        print(f"Command exited with code: {e.returncode}")
        print("!" * 72)
    except Exception as e:
        print("\n" + "!" * 72)
        print("BUILD FAILED.")
        print(str(e))
        print("!" * 72)

    print()
    input("Press Enter to close...")


def parse_args():
    parser = argparse.ArgumentParser(description="QiLabs unified build system")
    parser.add_argument(
        "--preset",
        choices=sorted(PRESETS.keys()),
        help="Run non-interactively using a named preset.",
    )
    parser.add_argument("--install", action="store_true", help="Install requirements before building.")
    parser.add_argument("--clean", action="store_true", help="Clean build artifacts before building.")
    parser.add_argument("--bump-version", action="store_true", help="Bump version before building.")
    parser.add_argument("--no-kill", action="store_true", help="Do not kill running packaged app before build.")
    parser.add_argument("--console", action="store_true", help="Force console build.")
    parser.add_argument("--windowed", action="store_true", help="Force windowed build.")
    parser.add_argument("--debug", action="store_true", help="Enable PyInstaller bootloader debug.")
    parser.add_argument(
        "--mode",
        choices=["dev", "release"],
        help="Override mode from preset.",
    )
    return parser.parse_args()


def cli_main(args):
    if not args.preset:
        interactive_main()
        return

    config = PRESETS[args.preset].copy()

    if args.mode:
        config["mode"] = args.mode
    if args.install:
        config["install"] = True
    if args.clean:
        config["clean"] = True
    if args.bump_version:
        config["bump"] = True
    if args.no_kill:
        config["kill"] = False
    if args.console:
        config["console"] = True
    if args.windowed:
        config["console"] = False
    if args.debug:
        config["debug"] = True

    print_header()
    print(f"Preset: {args.preset}")
    print(f"Description: {PRESETS[args.preset]['description']}")
    print()
    print("Resolved config:")
    print(f"  mode:         {config['mode']}")
    print(f"  clean:        {config['clean']}")
    print(f"  console:      {config['console']}")
    print(f"  debug:        {config['debug']}")
    print(f"  install:      {config['install']}")
    print(f"  kill:         {config['kill']}")
    print(f"  bump:         {config['bump']}")
    print()

    try:
        run_pipeline(config)
    except subprocess.CalledProcessError as e:
        print("\n" + "!" * 72)
        print("BUILD FAILED.")
        print(f"Command exited with code: {e.returncode}")
        print("!" * 72)
        sys.exit(e.returncode)
    except Exception as e:
        print("\n" + "!" * 72)
        print("BUILD FAILED.")
        print(str(e))
        print("!" * 72)
        sys.exit(1)


def main():
    args = parse_args()
    cli_main(args)


if __name__ == "__main__":
    # Ensure script runs from its own directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    main()
