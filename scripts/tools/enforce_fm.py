#!/usr/bin/env python3
import os
import re
import yaml
import uuid
from datetime import date
import json

# This script enforces the Universal Front Matter Schema across the monorepo.
# Rules: 
# 1. dna_id is immutable.
# 2. canonical_name is stable.
# 3. Path-based classification.

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '../..'))
CONFIG_PATH = os.path.join(SCRIPT_DIR, 'fm_config.json')

with open(CONFIG_PATH, 'r') as f:
    CONFIG = json.load(f)

def log_action(action, target_path, details=""):
    import datetime
    timestamp = datetime.datetime.now().isoformat()
    log_file = os.path.join(ROOT_DIR, 'logs', 'scripts.log')
    log_dir = os.path.dirname(log_file)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] [ENFORCER] {action:<10} | {target_path} {details}\n")

def get_iso_date():
    return date.today().isoformat()

def slugify(text):
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    return re.sub(r'[-\s]+', '-', text).strip('-')

class FrontMatterEnforcer:
    def __init__(self, file_path):
        self.file_path = file_path
        self.rel_path = os.path.relpath(file_path, ROOT_DIR).replace('\\', '/')
        self.content = ""
        self.fm = {}
        self.body = ""
        self.has_changed = False

    def load(self):
        with open(self.file_path, 'r', encoding='utf-8') as f:
            self.content = f.read()
        
        # Split Front Matter
        match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$', self.content, re.DOTALL)
        if match:
            try:
                self.fm = yaml.safe_load(match.group(1)) or {}
                self.body = match.group(2)
            except yaml.YAMLError:
                self.fm = {}
                self.body = self.content
        else:
            self.fm = {}
            self.body = self.content

    def infer_metadata(self):
        # 1. Path Based Mapping
        mapping = None
        for m in CONFIG['path_mappings']:
            if m['pattern'] in self.rel_path:
                mapping = m
                break
        
        # 2. Key Enforcements
        if 'dna_id' not in self.fm:
            self.fm['dna_id'] = str(uuid.uuid4())
            self.has_changed = True
        
        if 'canonical_name' not in self.fm:
            # Try to find a title in the body or use filename
            title_match = re.search(r'^#\s+(.+)$', self.body, re.MULTILINE)
            if title_match:
                self.fm['canonical_name'] = title_match.group(1).strip()
            else:
                self.fm['canonical_name'] = os.path.basename(os.path.dirname(self.file_path)).replace('_', ' ').replace('-', ' ').title()
            self.has_changed = True

        if 'title' not in self.fm:
            self.fm['title'] = self.fm['canonical_name']

        if mapping:
            if self.fm.get('module') != mapping['module']:
                self.fm['module'] = mapping['module']
                self.has_changed = True
            if self.fm.get('visibility') != mapping['visibility']:
                self.fm['visibility'] = mapping['visibility']
                self.has_changed = True
            if 'type' not in self.fm:
                self.fm['type'] = mapping['type']
                self.has_changed = True

        if 'status' not in self.fm:
            self.fm['status'] = CONFIG['default_status']
            self.has_changed = True

        if 'created' not in self.fm:
            self.fm['created'] = get_iso_date()
            self.has_changed = True

        if 'version' not in self.fm:
            self.fm['version'] = 1
            self.has_changed = True

        if self.has_changed:
            self.fm['updated'] = get_iso_date()

    def save(self):
        if not self.has_changed:
            return

        # Order the keys for consistency
        ordered_keys = [
            'dna_id', 'canonical_name', 'title', 'type', 'module', 
            'slug', 'visibility', 'status', 'tags', 'version', 
            'created', 'updated'
        ]
        
        new_fm = {}
        # First add ordered keys
        for key in ordered_keys:
            if key in self.fm:
                new_fm[key] = self.fm[key]
            elif key == 'tags' and key not in self.fm:
                new_fm[key] = []
            elif key == 'slug' and key not in self.fm:
                new_fm[key] = ""
        
        # Then add any extra keys (Starlight etc)
        for key in self.fm:
            if key not in ordered_keys:
                new_fm[key] = self.fm[key]

        # Dump with specific formatting
        fm_yaml = yaml.dump(new_fm, sort_keys=False, allow_unicode=True, default_flow_style=False)
        new_content = f"---\n{fm_yaml}---\n{self.body}"
        
        with open(self.file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"[SYNC] Enforced: {self.rel_path}")
        log_action('ENFORCED', self.rel_path, f"DNA: {self.fm.get('dna_id')}")

def main():
    log_action('START', 'all', 'Universal Front Matter enforcement sweep started.')
    targets = [
        os.path.join(ROOT_DIR, 'content'),
        os.path.join(ROOT_DIR, 'apps')
    ]
    
    for target in targets:
        for root, dirs, files in os.walk(target):
            if 'node_modules' in dirs: dirs.remove('node_modules')
            if '.git' in dirs: dirs.remove('.git')
            
            for file in files:
                if file.endswith(('.md', '.mdx')):
                    path = os.path.join(root, file)
                    enforcer = FrontMatterEnforcer(path)
                    enforcer.load()
                    enforcer.infer_metadata()
                    enforcer.save()

if __name__ == "__main__":
    main()
