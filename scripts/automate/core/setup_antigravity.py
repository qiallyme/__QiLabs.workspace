import os
from pathlib import Path

def setup_antigravity_rules():
    """Generates the strict compliance and ADR workflows for the Antigravity agent."""
    root_dir = Path.cwd()
    agents_dir = root_dir / ".agents" / "rules"

    # Ensure directories exist
    agents_dir.mkdir(parents=True, exist_ok=True)

    # 1. Strict Compliance Rule
    compliance_path = agents_dir / "strict-compliance.md"
    compliance_content = """# strict-compliance

Before planning or writing any code, you MUST review our core QiOS Blueprint documentation to ensure strict alignment. All blueprint files are located within the `__QiOS_Master_Blueprint_v0.4` directory:

- @/__QiOS_Master_Blueprint_v0.4/docs/01_governance/policies.md
- @/__QiOS_Master_Blueprint_v0.4/docs/01_governance/standards.md
- @/__QiOS_Master_Blueprint_v0.4/docs/03_structure/placement_rules.md
- @/__QiOS_Master_Blueprint_v0.4/docs/04_data/schema.md

You must adhere to the QiOS constraints:
1. Respect the 3-Band Model (Core, Platform, Domain).
2. Do not write domain logic or new tables into the `public` schema.
3. Ensure every domain table carries a `tenant_id` for RLS isolation.
4. Do not bypass the "Spine" ingestion flow for file tracking.

If your proposed solution falls OUTSIDE the bounds of these documents, HALT coding. Provide an "Out-of-Bounds Alert" detailing the deviation, the Ripple-Check impact on the system, the Pros & Cons, and ask for approval to run `/update-adr`.
"""

    # 2. Update ADR Workflow
    adr_path = agents_dir / "update-adr.md"
    adr_content = """# update-adr
Description: Formalizes an approved architectural deviation by updating the QiOS Blueprint, creating an ADR, and modifying the changelog.

Step 1: Identify the approved out-of-bounds change from our current conversation context.
Step 2: Update the relevant governance files to officially incorporate this new rule.
Step 3: Check `@/__QiOS_Master_Blueprint_v0.4/docs/adr/` to determine the next sequential four-digit number.
Step 4: Read `@/__QiOS_Master_Blueprint_v0.4/docs/adr/ADR-0000_template.md` to get the required formatting.
Step 5: Generate the new Architecture Decision Record using the exact structure from the template. Format as `ADR-XXXX_brief_description.md`.
Step 6: Append a new entry to `@/__QiOS_Master_Blueprint_v0.4/docs/appendices/changelog.md` linking the ADR and explaining why.
Step 7: Confirm to the user that all blueprint documentation is synchronized.
"""

    # Write files
    with open(compliance_path, "w", encoding="utf-8") as f:
        f.write(compliance_content)
    with open(adr_path, "w", encoding="utf-8") as f:
        f.write(adr_content)

    print(f"✅ Antigravity rules successfully generated in {agents_dir}")

if __name__ == "__main__":
    setup_antigravity_rules()