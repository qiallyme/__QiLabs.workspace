#!/usr/bin/env python3
"""
QiOS Index Generator
Creates index files for every folder in the knowledge base, listing all subfolders and files.
Generates a master index at the root.
"""

import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple
import yaml

class IndexGenerator:
    def __init__(self, kb_root: str, index_filename: str = "_INDEX.md"):
        self.kb_root = Path(kb_root)
        # Accept both _INDEX.md and _index.md
        self.index_filename = index_filename
        self.index_filename_alt = index_filename.lower() if index_filename != index_filename.lower() else index_filename.upper()
        self.stats = {
            'folders_processed': 0,
            'indexes_created': 0,
            'indexes_updated': 0,
            'errors': 0
        }
    
    def get_folder_contents(self, folder_path: Path) -> Tuple[List[str], List[str]]:
        """Get lists of subfolders and files in a folder"""
        folders = []
        files = []
        
        try:
            for item in sorted(folder_path.iterdir()):
                if item.name.startswith('.'):
                    continue  # Skip hidden files
                if item.name == self.index_filename or item.name == self.index_filename_alt:
                    continue  # Skip index file itself
                
                if item.is_dir():
                    folders.append(item.name)
                elif item.is_file():
                    files.append(item.name)
        except PermissionError:
            pass
        
        return sorted(folders), sorted(files)
    
    def generate_index_content(self, folder_path: Path, relative_path: str) -> str:
        """Generate markdown content for an index file"""
        folders, files = self.get_folder_contents(folder_path)
        
        # Determine depth for heading level (H2 for root, H3 for level 1, etc.)
        depth = len(relative_path.split('/')) if relative_path else 0
        heading_level = min(depth + 2, 6)  # H2 for root, H3 for level 1, etc.
        heading_prefix = '#' * heading_level
        
        # Generate title
        folder_name = folder_path.name if folder_path.name else "Knowledge Base Root"
        title = f"{folder_name} Index"
        
        # Build front matter
        front_matter = {
            'title': title,
            'slug': f"{folder_path.name.lower().replace(' ', '_')}_index" if folder_path.name else 'kb_index',
            'realm': 'QiVault',
            'realm_slug': 'qivault',
            'type': 'doc',
            'node': 'file',
            'created': datetime.now().strftime('%Y-%m-%d'),
            'updated': datetime.now().strftime('%Y-%m-%d'),
            'status': 'active',
            'system': 'qios',
            'keywords': ['index', 'directory', 'navigation'],
            'tags': ['index', 'auto-generated'],
            'summary': f'Index of folders and files in {folder_name}',
            'sensitivity': 'internal',
            'classification': 'system_darkmatter'
        }
        
        # Format front matter
        yaml_str = yaml.dump(front_matter, default_flow_style=False, sort_keys=False, allow_unicode=True)
        
        # Build content
        content = f"---\n{yaml_str}---\n\n"
        content += f"# {title}\n\n"
        content += f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        content += f"**Path:** `{relative_path}`\n\n"
        content += "---\n\n"
        
        # Add folders section
        if folders:
            content += f"{heading_prefix} Folders ({len(folders)})\n\n"
            for folder in folders:
                folder_path_rel = f"{relative_path}/{folder}" if relative_path else folder
                folder_path_rel = folder_path_rel.replace('\\', '/')
                content += f"- **[{folder}/]({folder_path_rel}/)**\n"
            content += "\n"
        else:
            content += f"{heading_prefix} Folders\n\n*No subfolders*\n\n"
        
        # Add files section
        if files:
            content += f"{heading_prefix} Files ({len(files)})\n\n"
            for file in files:
                file_path_rel = f"{relative_path}/{file}" if relative_path else file
                file_path_rel = file_path_rel.replace('\\', '/')
                # Determine if it's markdown
                if file.endswith('.md'):
                    content += f"- [{file}]({file_path_rel})\n"
                else:
                    content += f"- `{file}`\n"
            content += "\n"
        else:
            content += f"{heading_prefix} Files\n\n*No files*\n\n"
        
        # Add statistics
        content += "---\n\n"
        content += "## Statistics\n\n"
        content += f"- **Subfolders:** {len(folders)}\n"
        content += f"- **Files:** {len(files)}\n"
        content += f"- **Total Items:** {len(folders) + len(files)}\n"
        
        return content
    
    def process_folder(self, folder_path: Path, relative_path: str = "") -> bool:
        """Process a single folder and create its index"""
        try:
            index_path = folder_path / self.index_filename
            
            # Check if index exists and is up to date
            folders, files = self.get_folder_contents(folder_path)
            needs_update = True
            
            if index_path.exists():
                # Check if content matches (simple check)
                try:
                    existing_content = index_path.read_text(encoding='utf-8')
                    # Count folders and files in existing index
                    existing_folders = existing_content.count('**[')
                    existing_files = existing_content.count('.md)')
                    if existing_folders == len(folders) and existing_files == len([f for f in files if f.endswith('.md')]):
                        needs_update = False
                except:
                    pass
            
            if needs_update:
                content = self.generate_index_content(folder_path, relative_path)
                index_path.write_text(content, encoding='utf-8')
                
                if index_path.exists() and index_path.stat().st_size > 0:
                    self.stats['indexes_updated'] += 1
                else:
                    self.stats['indexes_created'] += 1
            else:
                # Index exists and is current
                pass
            
            self.stats['folders_processed'] += 1
            return True
            
        except Exception as e:
            print(f"Error processing {folder_path}: {e}")
            self.stats['errors'] += 1
            return False
    
    def generate_master_index(self) -> bool:
        """Generate master index at kb root listing all sub-indexes"""
        try:
            master_index_path = self.kb_root / self.index_filename
            
            # Collect all index files
            index_files = []
            for index_file in self.kb_root.rglob(self.index_filename):
                if index_file == master_index_path:
                    continue  # Skip master index itself
                
                relative_path = str(index_file.relative_to(self.kb_root))
                folder_path = index_file.parent.relative_to(self.kb_root)
                
                index_files.append({
                    'path': str(folder_path).replace('\\', '/'),
                    'relative': relative_path.replace('\\', '/'),
                    'name': folder_path.name if folder_path.name else 'Root'
                })
            
            # Sort by path
            index_files.sort(key=lambda x: x['path'])
            
            # Generate master index content
            front_matter = {
                'title': 'Knowledge Base Master Index',
                'slug': 'kb_master_index',
                'realm': 'QiVault',
                'realm_slug': 'qivault',
                'type': 'doc',
                'node': 'file',
                'created': datetime.now().strftime('%Y-%m-%d'),
                'updated': datetime.now().strftime('%Y-%m-%d'),
                'status': 'active',
                'system': 'qios',
                'keywords': ['index', 'master', 'navigation', 'directory'],
                'tags': ['index', 'master', 'auto-generated'],
                'summary': f'Master index of all {len(index_files)} folder indexes in the knowledge base',
                'sensitivity': 'internal',
                'classification': 'system_darkmatter'
            }
            
            yaml_str = yaml.dump(front_matter, default_flow_style=False, sort_keys=False, allow_unicode=True)
            
            content = f"---\n{yaml_str}---\n\n"
            content += "# Knowledge Base Master Index\n\n"
            content += f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            content += f"**Total Indexes:** {len(index_files)}\n\n"
            content += "---\n\n"
            content += "## Index Files by Folder\n\n"
            
            # Group by top-level folder
            by_folder = {}
            for idx in index_files:
                top_level = idx['path'].split('/')[0] if '/' in idx['path'] else 'Root'
                if top_level not in by_folder:
                    by_folder[top_level] = []
                by_folder[top_level].append(idx)
            
            for folder in sorted(by_folder.keys()):
                content += f"### {folder}\n\n"
                for idx in sorted(by_folder[folder], key=lambda x: x['path']):
                    content += f"- **[{idx['name']}]({idx['relative']})** - `{idx['path']}`\n"
                content += "\n"
            
            content += "---\n\n"
            content += "## Statistics\n\n"
            content += f"- **Total Folder Indexes:** {len(index_files)}\n"
            content += f"- **Top-Level Folders:** {len(by_folder)}\n"
            
            master_index_path.write_text(content, encoding='utf-8')
            return True
            
        except Exception as e:
            print(f"Error generating master index: {e}")
            return False
    
    def process_all_folders(self, dry_run: bool = False):
        """Process all folders in kb_root"""
        print(f"Scanning folders in: {self.kb_root}")
        print(f"Mode: {'DRY RUN' if dry_run else 'WRITE'}")
        print()
        
        # Collect all folders
        all_folders = []
        for folder in self.kb_root.rglob('*'):
            if folder.is_dir() and not folder.name.startswith('.'):
                relative_path = str(folder.relative_to(self.kb_root)).replace('\\', '/')
                all_folders.append((folder, relative_path))
        
        # Sort by depth (process deeper folders first to avoid parent/child conflicts)
        all_folders.sort(key=lambda x: x[1].count('/'), reverse=True)
        
        total = len(all_folders)
        print(f"Found {total} folders to process")
        print()
        
        if not dry_run:
            for i, (folder_path, relative_path) in enumerate(all_folders, 1):
                if i % 100 == 0:
                    print(f"Progress: {i}/{total} ({i*100//total}%)")
                self.process_folder(folder_path, relative_path)
            
            # Generate master index
            print("\nGenerating master index...")
            self.generate_master_index()
        else:
            # Dry run: just count
            for folder_path, relative_path in all_folders:
                folders, files = self.get_folder_contents(folder_path)
                self.stats['folders_processed'] += 1
                if not (folder_path / self.index_filename).exists():
                    self.stats['indexes_created'] += 1
                else:
                    self.stats['indexes_updated'] += 1
        
        print()
        print("=" * 50)
        print("INDEX GENERATION COMPLETE")
        print("=" * 50)
        print(f"Folders processed: {self.stats['folders_processed']}")
        print(f"Indexes created: {self.stats['indexes_created']}")
        print(f"Indexes updated: {self.stats['indexes_updated']}")
        print(f"Errors: {self.stats['errors']}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate index files for QiOS knowledge base')
    parser.add_argument('--kb-root', default='realms/qivault/kb',
                       help='Root directory of knowledge base')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without making changes')
    parser.add_argument('--index-name', default='_INDEX.md',
                       help='Name of index files (default: _INDEX.md)')
    
    args = parser.parse_args()
    
    generator = IndexGenerator(args.kb_root, args.index_name)
    generator.process_all_folders(args.dry_run)
    
    print()
    print("=" * 50)
    print("STATISTICS")
    print("=" * 50)
    for key, value in generator.stats.items():
        print(f"{key}: {value}")


if __name__ == '__main__':
    main()

