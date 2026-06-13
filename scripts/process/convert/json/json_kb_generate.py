#!/usr/bin/env python3
"""
Generate ClientOS KB files from templates using client_profile.json

This script:
1. Reads client_profile.json (single source of truth)
2. Reads kb_templates.json (template map)
3. Loads markdown templates from .c.template
4. Replaces placeholders with values from client_profile.json
5. Writes personalized files to client's QiVault/

Usage:
    python tools/automations/generate_kb_from_json.py [client_id]

If client_id not provided, uses current directory to detect client OS.
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List


def resolve_paths() -> tuple[Path, Path]:
    """Resolve paths for template and client directories."""
    script_path = Path(__file__).resolve()
    # Script is at: QiOS/tools/automations/generate_kb_from_json.py
    # So parents[2] = QiOS root
    qios_root = script_path.parents[2]
    
    # Get client_id from command line argument
    if len(sys.argv) > 1:
        client_id = sys.argv[1]
    else:
        raise SystemExit("Error: Must provide client_id as argument\nUsage: python generate_kb_from_json.py <client_id>")
    
    template_root = qios_root / 'clnts' / '.c.template'
    client_root = qios_root / 'clnts' / client_id
    
    return template_root, client_root


def load_json(path: Path) -> Dict[str, Any]:
    """Load JSON file."""
    if not path.exists():
        raise SystemExit(f"Error: {path} not found")
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '_') -> Dict[str, Any]:
    """Flatten nested dictionary for easy placeholder lookup."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            # Convert lists to comma-separated strings for simple replacements
            items.append((new_key, ', '.join(str(item) for item in v)))
        else:
            items.append((new_key, v))
    return dict(items)


def format_capabilities_list(capabilities: List[str]) -> str:
    """Format AI capabilities as markdown list."""
    return '\n'.join(f"● {cap.replace('_', ' ').title()}" for cap in capabilities)


def format_restrictions_list(restrictions: List[str]) -> str:
    """Format AI restrictions as markdown list."""
    return '\n'.join(f"● {rest.replace('_', ' ').title()}" for rest in restrictions)


def get_placeholder_value(placeholder: str, profile: Dict[str, Any], flattened: Dict[str, Any]) -> str:
    """Get value for a placeholder from profile."""
    # Remove {{ }} brackets
    key = placeholder.strip('{}')
    
    # Special handling for complex placeholders
    if key == 'assistant_name':
        return profile.get('ai_agent', {}).get('name', 'Your Assistant')
    
    if key == 'ai_capabilities_list':
        capabilities = profile.get('ai_agent', {}).get('capabilities', [])
        return format_capabilities_list(capabilities)
    
    if key == 'ai_restrictions_list':
        restrictions = profile.get('ai_agent', {}).get('restrictions', [])
        return format_restrictions_list(restrictions)
    
    if key == 'base_plan_name':
        return profile.get('engagement', {}).get('engagement_name', 'Your Plan')
    
    # Try direct lookup first
    if key in flattened:
        value = flattened[key]
        return str(value) if value is not None else ''
    
    # Try nested lookup
    keys = key.split('_')
    current = profile
    for k in keys:
        if isinstance(current, dict) and k in current:
            current = current[k]
        else:
            return ''
    
    return str(current) if current is not None else ''


def replace_placeholders(content: str, profile: Dict[str, Any], flattened: Dict[str, Any]) -> str:
    """Replace all placeholders in content with values from profile."""
    # Find all placeholders
    pattern = r'\{\{([^}]+)\}\}'
    placeholders = re.findall(pattern, content)
    
    for placeholder_key in placeholders:
        placeholder = f"{{{{{placeholder_key}}}}}"
        value = get_placeholder_value(placeholder, profile, flattened)
        content = content.replace(placeholder, value)
    
    return content


def generate_kb_files(template_root: Path, client_root: Path):
    """Generate KB files from templates."""
    # Load configs
    template_config_path = template_root / 'sys' / 'config' / 'kb_templates.json'
    client_profile_path = client_root / 'sys' / 'config' / 'client_profile.json'
    
    if not client_profile_path.exists():
        raise SystemExit(f"Error: {client_profile_path} not found. Run spawn_client_os.py first.")
    
    template_config = load_json(template_config_path)
    client_profile = load_json(client_profile_path)
    flattened_profile = flatten_dict(client_profile)
    
    print(f"📋 Generating KB files for {client_profile.get('client_name', 'client')}...")
    print(f"   Template root: {template_root}")
    print(f"   Client root: {client_root}\n")
    
    generated_count = 0
    skipped_count = 0
    
    for template_entry in template_config.get('templates', []):
        template_path = template_entry['path']
        template_id = template_entry.get('template_id', '')
        placeholders = template_entry.get('placeholders', [])
        
        # Source: template file
        source_file = template_root / template_path
        # Target: client file
        target_file = client_root / template_path
        
        if not source_file.exists():
            print(f"⚠️  Template not found: {source_file}")
            skipped_count += 1
            continue
        
        # Read template
        with open(source_file, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        # Replace placeholders
        generated_content = replace_placeholders(template_content, client_profile, flattened_profile)
        
        # Ensure target directory exists
        target_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Write generated file
        with open(target_file, 'w', encoding='utf-8') as f:
            f.write(generated_content)
        
        print(f"✅ {template_path}")
        generated_count += 1
    
    print(f"\n=== Generation Complete ===")
    print(f"✅ Generated: {generated_count} files")
    if skipped_count > 0:
        print(f"⚠️  Skipped: {skipped_count} files")
    print(f"\n📁 Client KB ready at: {client_root / 'QiVault'}")


def main():
    """Main function."""
    try:
        template_root, client_root = resolve_paths()
        
        if not client_root.exists():
            raise SystemExit(f"Error: Client directory not found: {client_root}")
        
        generate_kb_files(template_root, client_root)
        
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

