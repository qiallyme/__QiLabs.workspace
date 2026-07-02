from __future__ import annotations

import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    try:
        from toolbox_core.plugin_registry import build_registry, save_registry, validation_report_markdown
    except Exception:
        print("[ERROR] Could not import toolbox_core.plugin_registry")
        traceback.print_exc()
        return 2

    try:
        registry_path = save_registry(ROOT)
        registry = build_registry(ROOT)
        report = validation_report_markdown(registry)
        report_path = ROOT / "toolbox_validation_report.md"
        report_path.write_text(report, encoding="utf-8")

        print(f"Registry: {registry_path}")
        print(f"Report:   {report_path}")
        print(f"Plugins:  {registry.get('plugin_count', len(registry.get('plugins', [])))}")
        print(f"Errors:   {registry.get('errors', 0)}")
        print(f"Warnings: {registry.get('warnings', 0)}")
        return 0 if registry.get("errors", 0) == 0 else 1
    except Exception:
        print("[ERROR] Registry refresh failed")
        traceback.print_exc()
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
