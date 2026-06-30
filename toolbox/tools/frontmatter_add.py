#!/usr/bin/env python3
"""
QiOS Front Matter Inserter
Intelligently adds/merges front matter to markdown files without overwriting existing data.
"""

import os
import re
import yaml
import json
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import hashlib

class FrontMatterProcessor:
    def __init__(self, kb_root: str):
        self.kb_root = Path(kb_root)
        self.stats = {
            'processed': 0,
            'added': 0,
            'merged': 0,
            'skipped': 0,
            'errors': 0
        }
        
    def detect_existing_frontmatter(self, content: str) -> Tuple[Optional[Dict], str]:
        """Extract existing front matter if present, return (frontmatter_dict, body_content)"""
        # Pattern: ---\n...yaml...\n---
        pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
        match = re.match(pattern, content, re.DOTALL)
        
        if match:
            try:
                yaml_content = match.group(1)
                body = match.group(2)
                frontmatter = yaml.safe_load(yaml_content) or {}
                return frontmatter, body
            except yaml.YAMLError:
                # Invalid YAML, treat as no front matter
                return None, content
        return None, content
    
    def generate_file_metadata(self, file_path: Path, relative_path: str) -> Dict[str, Any]:
        """Generate metadata based on file path and content - follows QiOS front matter schema"""
        # Extract directory structure
        parts = relative_path.replace('\\', '/').split('/')
        filename = parts[-1].replace('.md', '')
        
        # Determine realm/category from path
        realm = 'QiVault'
        realm_slug = 'qivault'
        category = 'unknown'
        qi_decimal = None
        type_field = 'doc'
        node = 'file'
        
        if parts[0] == '0_QiEOS':
            realm = 'QiOS'
            realm_slug = 'genesis'
            category = 'governance'
            qi_decimal = '0.00.00-SYS'
            type_field = 'doc'
            node = 'file'
        elif parts[0] == '1_Life':
            realm = 'QiVault'
            realm_slug = 'qivault'
            category = 'personal'
            qi_decimal = '1.00.00-LIFE'
            type_field = 'doc'
            node = 'concept'
        elif parts[0] == '3_Ops':
            realm = 'QiVault'
            realm_slug = 'qivault'
            category = 'operations'
            qi_decimal = '3.00.00-OPS'
            type_field = 'doc'
            node = 'concept'
        elif parts[0] == '3_Work':
            realm = 'QiVault'
            realm_slug = 'qivault'
            category = 'work'
            qi_decimal = '3.00.00-WORK'
            type_field = 'doc'
            node = 'concept'
        elif parts[0] == '4_Clients':
            realm = 'QiVault'
            realm_slug = 'qivault'
            category = 'clients'
            qi_decimal = '4.00.00-CLIENTS'
            type_field = 'doc'
            node = 'entity'
        elif 'finance' in parts[0].lower() or '6' in parts[0]:
            realm = 'QiVault'
            realm_slug = 'qivault'
            category = 'finance'
            qi_decimal = '6.00.00-FINANCE'
            type_field = 'doc'
            node = 'concept'
        elif 'legal' in parts[0].lower() or parts[0] == '7_Legal':
            realm = 'QiVault'
            realm_slug = 'qivault'
            category = 'legal'
            qi_decimal = '7.00.00-LEGAL'
            type_field = 'doc'
            node = 'concept'
        elif 'tech' in parts[0].lower() or parts[0] == '7_Tech':
            realm = 'QiVault'
            realm_slug = 'qivault'
            category = 'tech'
            qi_decimal = '7.00.00-TECH'
            type_field = 'doc'
            node = 'concept'
        elif 'ideas' in parts[0].lower() or '9' in parts[0]:
            realm = 'QiVault'
            realm_slug = 'qivault'
            category = 'ideas'
            qi_decimal = '9.00.00-IDEAS'
            type_field = 'doc'
            node = 'concept'
        elif parts[0] == '_Intake':
            realm = 'QiVault'
            realm_slug = 'qivault'
            category = 'intake'
            qi_decimal = '0.00.00-INTAKE'
            type_field = 'doc'
            node = 'file'
        else:
            # Default for unknown paths
            qi_decimal = '0.00.00-UNKNOWN'
        
        # Generate QID from file path hash (immutable identifier)
        path_hash = hashlib.md5(relative_path.encode()).hexdigest()[:12]
        qid = f"q{path_hash}"
        
        # Generate slug from filename (lowercase, hyphens)
        slug = re.sub(r'[^a-z0-9]+', '_', filename.lower()).strip('_')
        # Ensure slug is not empty
        if not slug:
            slug = 'untitled'
        
        # Get file stats
        stat = file_path.stat()
        created = datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d')
        updated = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d')
        
        # Generate title from filename
        title = filename.replace('_', ' ').replace('-', ' ').strip()
        if not title:
            title = 'Untitled Document'
        
        # Build metadata following QiOS front matter schema
        metadata = {
            # Required fields per QiOS schema
            'title': title,
            'slug': slug,
            'realm': realm,
            'type': type_field,
            'node': node,
            'created': created,
            'updated': updated,
            
            # Optional but recommended
            'realm_slug': realm_slug,
            'qi_decimal': qi_decimal,
            'qid': qid,
            'status': 'active',
            'system': 'qios',
        }
        
        # Add optional fields that might be useful
        if category != 'unknown':
            metadata['keywords'] = [category]
        
        return metadata
    
    def merge_frontmatter(self, existing: Dict, new: Dict) -> Dict:
        """Merge new front matter into existing, preserving existing values"""
        merged = existing.copy()
        
        # Only add fields that don't exist or are empty
        for key, value in new.items():
            if key not in merged or not merged[key] or merged[key] == 'unknown':
                merged[key] = value
            elif isinstance(merged[key], list) and isinstance(value, list):
                # Merge lists, avoiding duplicates
                merged[key] = list(set(merged[key] + value))
            elif isinstance(merged[key], dict) and isinstance(value, dict):
                # Recursively merge dicts
                merged[key] = self.merge_frontmatter(merged[key], value)
        
        return merged
    
    def format_frontmatter(self, frontmatter: Dict) -> str:
        """Format front matter as YAML string following QiOS schema order"""
        # Order keys per QiOS front matter schema priority
        ordered_keys = [
            # Required fields first
            'title', 'slug', 'realm', 'type', 'node', 'created', 'updated',
            # Identity fields
            'realm_slug', 'qi_decimal', 'qid',
            # Status and system
            'status', 'system',
            # Optional semantic fields
            'keywords', 'tags', 'context', 'aliases',
            # Versioning
            'version',
            # Graph fields
            'related', 'parents', 'children', 'siblings', 'references',
            'graph_weight', 'orbit', 'entangled',
            # Classification
            'sensitivity', 'classification',
            # Summary
            'summary',
            # Other fields
        ]
        
        ordered = {}
        remaining = {}
        
        # Add ordered keys first
        for key in ordered_keys:
            if key in frontmatter:
                ordered[key] = frontmatter[key]
        
        # Add remaining keys
        for key, value in frontmatter.items():
            if key not in ordered:
                remaining[key] = value
        
        final = {**ordered, **remaining}
        
        # Format YAML with proper indentation
        yaml_str = yaml.dump(
            final,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            width=1000,
            indent=2
        )
        return f"---\n{yaml_str}---\n"
    
    def process_file(self, file_path: Path) -> bool:
        """Process a single markdown file"""
        try:
            relative_path = str(file_path.relative_to(self.kb_root))
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Detect existing front matter
            existing_fm, body = self.detect_existing_frontmatter(content)
            
            # Generate new metadata
            new_metadata = self.generate_file_metadata(file_path, relative_path)
            
            if existing_fm:
                # Merge with existing
                merged_fm = self.merge_frontmatter(existing_fm, new_metadata)
                if merged_fm != existing_fm:
                    # Only write if changed
                    new_content = self.format_frontmatter(merged_fm) + body
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    self.stats['merged'] += 1
                else:
                    self.stats['skipped'] += 1
            else:
                # Add new front matter
                new_content = self.format_frontmatter(new_metadata) + body
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                self.stats['added'] += 1
            
            self.stats['processed'] += 1
            return True
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            self.stats['errors'] += 1
            return False
    
    def process_directory(self, pattern: str = "*.md", dry_run: bool = False):
        """Process all markdown files in kb_root"""
        md_files = list(self.kb_root.rglob(pattern))
        total = len(md_files)
        
        print(f"Found {total} markdown files")
        print(f"Mode: {'DRY RUN' if dry_run else 'WRITE'}")
        print()
        
        for i, file_path in enumerate(md_files, 1):
            if i % 100 == 0:
                print(f"Progress: {i}/{total} ({i*100//total}%)")
            
            if not dry_run:
                self.process_file(file_path)
            else:
                # Just check what would happen
                relative_path = str(file_path.relative_to(self.kb_root))
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    existing_fm, _ = self.detect_existing_frontmatter(content)
                    if existing_fm:
                        self.stats['skipped'] += 1
                    else:
                        self.stats['added'] += 1
                    self.stats['processed'] += 1
                except:
                    self.stats['errors'] += 1
        
        print()
        print("=" * 50)
        print("PROCESSING COMPLETE")
        print("=" * 50)
        print(f"Processed: {self.stats['processed']}")
        print(f"Added front matter: {self.stats['added']}")
        print(f"Merged front matter: {self.stats['merged']}")
        print(f"Skipped (no changes): {self.stats['skipped']}")
        print(f"Errors: {self.stats['errors']}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Add/merge front matter to QiOS markdown files')
    parser.add_argument('--kb-root', default='realms/qivault/kb',
                       help='Root directory of knowledge base')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without making changes')
    parser.add_argument('--pattern', default='*.md',
                       help='File pattern to match (default: *.md)')
    parser.add_argument('--limit', type=int, default=None,
                       help='Limit number of files to process (for testing)')
    
    args = parser.parse_args()
    
    processor = FrontMatterProcessor(args.kb_root)
    
    if args.limit:
        # Process only first N files for testing
        md_files = list(processor.kb_root.rglob(args.pattern))[:args.limit]
        for file_path in md_files:
            if not args.dry_run:
                processor.process_file(file_path)
            else:
                relative_path = str(file_path.relative_to(processor.kb_root))
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    existing_fm, _ = processor.detect_existing_frontmatter(content)
                    if existing_fm:
                        processor.stats['skipped'] += 1
                    else:
                        processor.stats['added'] += 1
                    processor.stats['processed'] += 1
                except:
                    processor.stats['errors'] += 1
    else:
        processor.process_directory(args.pattern, args.dry_run)
    
    print()
    print("=" * 50)
    print("STATISTICS")
    print("=" * 50)
    for key, value in processor.stats.items():
        print(f"{key}: {value}")


if __name__ == '__main__':
    main()

