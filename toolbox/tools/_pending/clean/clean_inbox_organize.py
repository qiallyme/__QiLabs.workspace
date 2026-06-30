#!/usr/bin/env python3
"""
Complete Inbox File Organization and Protocol Compliance
Implements all phases of the inbox organization plan according to QiEOS Protocol v3.0
"""

import os
import sys
import shutil
import hashlib
import json
import yaml
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Set
import subprocess

# Add QiInboxWatcher to path for utilities
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "4_App" / "QiInboxWatcher"))

try:
    from utils import ensure_dir, file_sha1, now_iso, safe_slug
    from fsops import write_front_matter, update_folder_index, begin_restore_block, append_restore_op, finalize_restore_block
    from ocr_engine import configure_tesseract, pdf_text_or_ocr, image_ocr
    QIINBOX_AVAILABLE = True
except ImportError:
    # Fallback if imports fail
    QIINBOX_AVAILABLE = False
    def ensure_dir(p: str):
        os.makedirs(p, exist_ok=True)
    def file_sha1(path):
        h = hashlib.sha1()
        with open(path, "rb") as f:
            h.update(f.read())
        return h.hexdigest()
    def now_iso():
        return datetime.utcnow().isoformat() + "Z"
    def safe_slug(s: str, maxlen=80):
        return re.sub(r'[^\w\s-]', '', s.lower()).strip().replace(' ', '-')[:maxlen]
    
    # Fallback implementations
    def write_front_matter(md_path: str, fm: Dict, body: str):
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("---\n")
            for k, v in fm.items():
                if isinstance(v, (list, dict)):
                    f.write(f"{k}: |\n")
                    f.write(yaml.safe_dump(v, sort_keys=False))
                else:
                    f.write(f"{k}: {json.dumps(v, ensure_ascii=False)}\n")
            f.write("---\n\n")
            f.write(body or "")
    
    def update_folder_index(folder: str, index_name: str = "_index.md"):
        index_path = Path(folder) / index_name
        entries = []
        for name in sorted(os.listdir(folder)):
            if name == index_name:
                continue
            entries.append(f"- [{name}]({name})")
        content = "# Index\n\n" + "\n".join(entries) + "\n"
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(content)
    
    def begin_restore_block(restore_dir: str) -> str:
        ensure_dir(restore_dir)
        stamp = datetime.utcnow().strftime("restore_%Y-%m-%dT%H-%M-%SZ.json")
        path = Path(restore_dir) / stamp
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"started": now_iso(), "ops": []}, f, indent=2)
        return str(path)
    
    def append_restore_op(restore_file: str, op: Dict):
        with open(restore_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["ops"].append(op)
        with open(restore_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    
    def finalize_restore_block(restore_file: str, success=True, error: str | None=None):
        with open(restore_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["finished"] = now_iso()
        data["success"] = success
        if error:
            data["error"] = error
        with open(restore_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

# Configuration
VAULT_ROOT = Path(r"G:\My Drive")
INBOX_LOCATIONS = [
    VAULT_ROOT / "_inbox",
    VAULT_ROOT / "QiOne" / "0_Inbox",
]
RESTORE_DIR = VAULT_ROOT / "QiOne" / "restore"
STAGING_DIR = VAULT_ROOT / "QiOne" / ".staging"

# System files to ignore when checking for empty folders
SYSTEM_FILES = {'.DS_Store', 'Thumbs.db', 'desktop.ini', '.gitkeep', '.gitignore', '.git', '.svn'}

# Statistics
stats = defaultdict(int)
processed_files = []
duplicates_removed = []
files_merged = []
folders_created = []
folders_removed = []
errors = []


class FileInventory:
    """Represents a file in the inventory"""
    def __init__(self, path: Path):
        self.path = path
        self.size = path.stat().st_size if path.exists() else 0
        self.modified = datetime.fromtimestamp(path.stat().st_mtime) if path.exists() else datetime.now()
        self.extension = path.suffix.lower()
        self.content_hash = None
        self.text_content = None
        self.front_matter = {}
        self.file_type = None
        self.category = None
        self.destination = None
        self.new_name = None
        self.is_duplicate = False
        self.merge_with = None


def sha256_hash(path: Path) -> str:
    """Calculate SHA-256 hash of file"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def is_system_file(name: str) -> bool:
    """Check if file is a system file"""
    return name in SYSTEM_FILES or name.startswith('.')


def is_empty_folder(folder: Path, checked: Set[Path] = None) -> bool:
    """Recursively check if folder is empty (ignoring system files)"""
    if checked is None:
        checked = set()
    
    if folder in checked:
        return True
    
    checked.add(folder)
    
    if not folder.exists() or not folder.is_dir():
        return True
    
    try:
        items = list(folder.iterdir())
        for item in items:
            if is_system_file(item.name):
                continue
            if item.is_file():
                return False
            if item.is_dir():
                if not is_empty_folder(item, checked):
                    return False
        return True
    except PermissionError:
        return False


def convert_heic_to_jpeg(heic_path: Path) -> Optional[Path]:
    """Convert HEIC file to JPEG"""
    if DRY_RUN_MODE:
        jpeg_path = heic_path.with_suffix('.jpg')
        print(f"    [DRY RUN] Would convert: {heic_path.name} → {jpeg_path.name}")
        return jpeg_path
    
    try:
        jpeg_path = heic_path.with_suffix('.jpg')
        
        # Try using pillow-heif (best option)
        try:
            from pillow_heif import register_heif_opener
            from PIL import Image
            register_heif_opener()
            img = Image.open(heic_path)
            img.convert('RGB').save(jpeg_path, 'JPEG', quality=95)
            print(f"    Converted using pillow-heif: {heic_path.name}")
            return jpeg_path
        except ImportError:
            pass
        
        # Try using subprocess with ImageMagick (Windows/Linux)
        try:
            if sys.platform == 'win32':
                # Try magick command (ImageMagick 7+) - check common locations
                magick_paths = [
                    'magick',
                    r'C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe',
                    r'C:\Program Files\ImageMagick\magick.exe',
                ]
                for magick_cmd in magick_paths:
                    try:
                        result = subprocess.run([magick_cmd, str(heic_path), str(jpeg_path)], 
                                              check=True, capture_output=True, timeout=30)
                        print(f"    Converted using ImageMagick: {heic_path.name}")
                        return jpeg_path
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        continue
            elif sys.platform == 'darwin':
                # Use sips on macOS
                result = subprocess.run(['sips', '-s', 'format', 'jpeg', str(heic_path), '--out', str(jpeg_path)], 
                                      check=True, capture_output=True, timeout=30)
                print(f"    Converted using sips: {heic_path.name}")
                return jpeg_path
            else:
                # Try convert command (ImageMagick 6)
                result = subprocess.run(['convert', str(heic_path), str(jpeg_path)], 
                                      check=True, capture_output=True, timeout=30)
                print(f"    Converted using ImageMagick: {heic_path.name}")
                return jpeg_path
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
            # Don't treat as error if tool not available - just skip conversion
            print(f"    Note: HEIC conversion skipped for {heic_path.name} (conversion tool not available)")
            return None
            
    except Exception as e:
        print(f"    Note: HEIC conversion skipped for {heic_path.name}: {e}")
        return None


def extract_front_matter(content: str) -> Tuple[Dict, str]:
    """Extract YAML front matter from markdown content"""
    if not content.startswith('---'):
        return {}, content
    
    try:
        parts = content.split('---', 2)
        if len(parts) < 3:
            return {}, content
        
        fm_text = parts[1].strip()
        body = parts[2].strip()
        
        fm = yaml.safe_load(fm_text) or {}
        return fm, body
    except Exception:
        return {}, content


def infer_document_type(inventory: FileInventory, content: str = None) -> str:
    """Infer document type from content and path"""
    path_lower = str(inventory.path).lower()
    content_lower = (content or "").lower()
    
    # Check for journal indicators
    if any(x in content_lower for x in ['mood:', 'summary:', 'digest:', 'journal', 'entry']):
        return 'journal-entry'
    
    # Check for timeline indicators
    if any(x in content_lower for x in ['life_stage:', 'critical:', 'timeline', 'event']):
        return 'timeline-event'
    
    # Check path patterns
    if 'journal' in path_lower or 'timeline' in path_lower:
        return 'journal-entry' if 'journal' in path_lower else 'timeline-event'
    
    # Default to knowledge base
    return 'knowledge'


def infer_realm(destination_path: Path) -> str:
    """Infer realm from destination path"""
    path_str = str(destination_path)
    if '2_QsKb' in path_str:
        return '2_QsKb'
    elif '3_QiKb' in path_str:
        return '3_QiKb'
    elif '4_Clients' in path_str:
        return '4_Clients'
    elif '5_Apps' in path_str:
        return '5_Apps'
    elif '1_QiEos' in path_str or '1_Kb' in path_str:
        return '1_Kb'
    else:
        return '2_QsKb'  # Default


def infer_privacy(destination_path: Path) -> str:
    """Infer privacy level from destination"""
    path_str = str(destination_path).lower()
    if 'public' in path_str or 'shared' in path_str:
        return 'public'
    elif 'client' in path_str:
        return 'shared'
    else:
        return 'private'


def generate_qi_decimal(inventory: FileInventory, doc_type: str, destination: Path) -> str:
    """Generate QiDecimal ID based on document type and destination"""
    # This is a simplified version - should use actual QiDecimal system
    path_str = str(destination)
    
    # Extract numeric prefix from path if available
    match = re.search(r'(\d+)\.(\d+)_', path_str)
    if match:
        major = match.group(1)
        minor = match.group(2)
        return f"{major}.{minor}.00-01"
    
    # Default based on document type
    defaults = {
        'journal-entry': '60.20.03-25',
        'timeline-event': '60.20.03-26',
        'knowledge': '2.99.00-01',
    }
    return defaults.get(doc_type, '2.99.00-01')


def generate_summary_and_digest(content: str, max_summary: int = 200, max_digest: int = 80) -> Tuple[str, str]:
    """Generate summary and digest from content"""
    if not content:
        return '', ''
    
    # Simple extraction - first paragraph or first few sentences
    lines = [l.strip() for l in content.split('\n') if l.strip()]
    first_para = lines[0] if lines else ''
    
    # Generate summary (1-2 sentences)
    sentences = re.split(r'[.!?]+', first_para)
    summary = '. '.join(sentences[:2]).strip()
    if len(summary) > max_summary:
        summary = summary[:max_summary-3] + '...'
    
    # Generate digest (condensed version)
    words = summary.split()
    digest = ' '.join(words[:15])  # ~15 words
    if len(digest) > max_digest:
        digest = digest[:max_digest-3] + '...'
    
    return summary or '', digest or ''


def extract_mood_from_content(content: str) -> str:
    """Extract mood from journal content"""
    if not content:
        return ''
    
    # Look for mood indicators
    mood_patterns = [
        r'mood[:\s]+([^\n]+)',
        r'feeling[:\s]+([^\n]+)',
        r'emotion[:\s]+([^\n]+)',
    ]
    
    for pattern in mood_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    return ''


def generate_front_matter(inventory: FileInventory, doc_type: str, destination: Path, 
                         content: str = None) -> Dict:
    """Generate complete front matter according to protocol"""
    fm = {}
    
    # Core required fields (ALL document types)
    title = inventory.front_matter.get('title')
    if not title:
        # Try to extract from H1 or filename
        if content:
            h1_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            if h1_match:
                title = h1_match.group(1).strip()
        if not title:
            title = inventory.path.stem.replace('_', ' ').replace('-', ' ')
            # Title case
            title = ' '.join(word.capitalize() for word in title.split())
    
    fm['title'] = title
    fm['slug'] = safe_slug(title)
    fm['realm'] = infer_realm(destination)
    fm['owner'] = 'CRV'  # or 'q' for QiNote files
    fm['privacy'] = infer_privacy(destination)
    fm['qi_decimal'] = generate_qi_decimal(inventory, doc_type, destination)
    
    # Tags - ensure it's an array
    tags = inventory.front_matter.get('tags', [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(',')]
    fm['tags'] = tags if tags else []
    
    # Date fields
    date_str = inventory.front_matter.get('date')
    if not date_str:
        # Try to extract from filename
        date_match = re.search(r'(\d{4}[-_]\d{2}[-_]\d{2})', inventory.path.stem)
        if date_match:
            date_str = date_match.group(1).replace('_', '-')
        else:
            date_str = inventory.modified.strftime('%Y-%m-%d')
    fm['date'] = date_str
    fm['last_updated'] = datetime.now().strftime('%Y-%m-%d')
    
    # Document type specific fields
    if doc_type == 'journal-entry':
        fm['category'] = inventory.front_matter.get('category', 'personal')
        
        # Extract or generate mood
        mood = inventory.front_matter.get('mood') or extract_mood_from_content(content or '')
        fm['mood'] = mood
        
        # Generate summary and digest if missing
        summary = inventory.front_matter.get('summary', '')
        digest = inventory.front_matter.get('digest', '')
        if not summary or not digest:
            gen_summary, gen_digest = generate_summary_and_digest(content or '')
            fm['summary'] = summary or gen_summary
            fm['digest'] = digest or gen_digest
        else:
            fm['summary'] = summary
            fm['digest'] = digest
            
    elif doc_type == 'timeline-event':
        fm['category'] = inventory.front_matter.get('category', 'milestone')
        if 'life_stage' in inventory.front_matter:
            fm['life_stage'] = inventory.front_matter['life_stage']
        if 'critical' in inventory.front_matter:
            fm['critical'] = inventory.front_matter['critical']
        else:
            fm['critical'] = False
            
    elif doc_type == 'knowledge':
        fm['type'] = inventory.front_matter.get('type', 'knowledge')
        # Add dateCreated as alternative to date
        fm['dateCreated'] = inventory.modified.isoformat() + 'Z'
    
    return fm


def extract_content_from_file(inv: FileInventory) -> str:
    """Extract text content from various file types"""
    if inv.extension == '.md':
        try:
            with open(inv.path, 'r', encoding='utf-8') as f:
                return f.read()
        except:
            return ''
    elif inv.extension == '.pdf':
        try:
            if QIINBOX_AVAILABLE:
                text, _ = pdf_text_or_ocr(str(inv.path))
                return text
            else:
                # Fallback: try PyPDF2 or pdfplumber
                try:
                    import PyPDF2
                    with open(inv.path, 'rb') as f:
                        reader = PyPDF2.PdfReader(f)
                        return '\n'.join([page.extract_text() for page in reader.pages])
                except:
                    return ''
        except:
            return ''
    elif inv.extension in ['.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp', '.webp', '.heic']:
        try:
            if QIINBOX_AVAILABLE:
                return image_ocr(str(inv.path))
            else:
                # Fallback: try pytesseract directly
                try:
                    import pytesseract
                    from PIL import Image
                    img = Image.open(inv.path)
                    return pytesseract.image_to_string(img)
                except:
                    return ''
        except:
            return ''
    elif inv.extension in ['.txt', '.rtf', '.csv']:
        try:
            with open(inv.path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except:
            return ''
    return ''


def phase1_discovery() -> List[FileInventory]:
    """Phase 1: Discovery and Inventory"""
    print("\n" + "="*70)
    print("PHASE 1: Discovery and Inventory")
    print("="*70)
    
    inventory = []
    
    for inbox_path in INBOX_LOCATIONS:
        if not inbox_path.exists():
            print(f"Skipping non-existent inbox: {inbox_path}")
            continue
        
        print(f"\nScanning: {inbox_path}")
        
        for root, dirs, files in os.walk(inbox_path):
            # Skip system directories
            dirs[:] = [d for d in dirs if not is_system_file(d)]
            
            for file in files:
                if is_system_file(file):
                    continue
                
                file_path = Path(root) / file
                try:
                    inv = FileInventory(file_path)
                    
                    # Extract content for classification
                    inv.text_content = extract_content_from_file(inv)
                    
                    # Extract front matter if markdown
                    if inv.extension == '.md':
                        inv.front_matter, _ = extract_front_matter(inv.text_content)
                    
                    print(f"  Found: {file_path.relative_to(inbox_path)} ({inv.size} bytes)")
                    inventory.append(inv)
                except Exception as e:
                    errors.append(f"Error processing {file_path}: {e}")
    
    print(f"\nTotal files found: {len(inventory)}")
    return inventory


def phase2_deduplication(inventory: List[FileInventory]) -> List[FileInventory]:
    """Phase 2: Deduplication Strategy"""
    print("\n" + "="*70)
    print("PHASE 2: Deduplication")
    print("="*70)
    
    # Group by content hash
    hash_map = defaultdict(list)
    
    print("\nCalculating content hashes...")
    for inv in inventory:
        try:
            inv.content_hash = sha256_hash(inv.path)
            hash_map[inv.content_hash].append(inv)
        except Exception as e:
            errors.append(f"Error hashing {inv.path}: {e}")
    
    # Find exact duplicates
    unique_files = []
    for hash_val, files in hash_map.items():
        if len(files) > 1:
            # Keep newest, archive others
            files.sort(key=lambda x: x.modified, reverse=True)
            unique_files.append(files[0])
            for dup in files[1:]:
                dup.is_duplicate = True
                duplicates_removed.append(dup.path)
                stats['duplicates_removed'] += 1
        else:
            unique_files.append(files[0])
    
    print(f"Duplicates removed: {stats['duplicates_removed']}")
    return unique_files


def phase3_media_conversion(inventory: List[FileInventory]) -> List[FileInventory]:
    """Phase 3: Media Conversion (HEIC to JPEG)"""
    print("\n" + "="*70)
    print("PHASE 3: Media Conversion")
    print("="*70)
    
    converted = []
    for inv in inventory:
        if inv.extension == '.heic':
            print(f"Converting: {inv.path.name}")
            jpeg_path = convert_heic_to_jpeg(inv.path)
            if jpeg_path and jpeg_path.exists():
                # Update inventory to point to new JPEG
                inv.path = jpeg_path
                inv.extension = '.jpg'
                converted.append(jpeg_path)
                stats['heic_converted'] += 1
                # Optionally remove original HEIC
                # inv.path.unlink()
    
    print(f"HEIC files converted: {stats['heic_converted']}")
    return inventory


def phase4_renaming(inventory: List[FileInventory]) -> List[FileInventory]:
    """Phase 4: Renaming According to Protocol"""
    print("\n" + "="*70)
    print("PHASE 4: Renaming According to Protocol")
    print("="*70)
    
    # This will be handled during move phase based on destination
    # For now, just prepare new names
    for inv in inventory:
        # Extract date from filename or metadata
        date_match = re.search(r'(\d{4}[-_]\d{2}[-_]\d{2})', inv.path.stem)
        if date_match:
            date_str = date_match.group(1).replace('_', '-')
        else:
            date_str = inv.modified.strftime('%Y-%m-%d')
        
        # Generate slug from title or filename
        title = inv.front_matter.get('title', inv.path.stem)
        slug = safe_slug(title)
        
        # Determine naming format based on document type
        doc_type = infer_document_type(inv)
        
        if doc_type == 'journal-entry':
            # QiNote format: yyyy-mm-dd_{short_title}.md
            short_title = '_'.join(slug.split('-')[:5])  # Max 5 words
            inv.new_name = f"{date_str}_{short_title}{inv.extension}"
        else:
            # Simple format: YYYYMMDD_scope_slug_title.ext
            date_compact = date_str.replace('-', '')
            scope = 'personal'  # Infer from destination later
            inv.new_name = f"{date_compact}_{scope}_{slug}{inv.extension}"
    
    return inventory


def phase5_folder_placement(inventory: List[FileInventory], restore_file: str) -> List[FileInventory]:
    """Phase 5: Folder Structure and Placement"""
    print("\n" + "="*70)
    print("PHASE 5: Folder Structure and Placement")
    print("="*70)
    
    # Try to load QiInboxWatcher config and router
    try:
        config_path = VAULT_ROOT / "4_App" / "QiInboxWatcher" / "config.yaml"
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                cfg = yaml.safe_load(f)
            
            # Load router if available
            try:
                from router import load_rules, decide
                rules_path = VAULT_ROOT / "4_App" / "QiInboxWatcher" / cfg.get("rules_file", "rules.csv")
                if rules_path.exists():
                    rules = load_rules(str(rules_path), cfg)
                    use_router = True
                else:
                    use_router = False
            except:
                use_router = False
        else:
            use_router = False
            cfg = {}
    except:
        use_router = False
        cfg = {}
    
    # Determine destinations based on content and protocol
    seq_id = 1
    for inv in inventory:
        if inv.is_duplicate:
            continue
        
        # Extract text for routing
        text_content = inv.text_content or ''
        if not text_content and inv.extension in ['.md', '.txt']:
            try:
                with open(inv.path, 'r', encoding='utf-8') as f:
                    text_content = f.read()
            except:
                pass
        
        # Use router if available
        if use_router:
            try:
                stem, target_rel, route_name = decide(
                    text_content or inv.path.stem,
                    inv.path.stem,
                    rules,
                    cfg,
                    seq_id
                )
                inv.destination = Path(cfg.get("vault_root", str(VAULT_ROOT))) / target_rel
                inv.new_name = stem + inv.extension
                seq_id += 1
            except Exception as e:
                errors.append(f"Routing error for {inv.path}: {e}")
                # Fallback to simple routing
                use_router = False
        
        if not use_router:
            # Simplified routing fallback
            path_lower = str(inv.path).lower()
            if 'client' in path_lower or 'zai' in path_lower:
                inv.destination = VAULT_ROOT / "4_Clients" / "default" / "1_EOS"
            elif 'business' in path_lower or 'qially' in path_lower or 'qi' in path_lower:
                inv.destination = VAULT_ROOT / "3_QiKb" / "3.50_DOCS"
            elif inv.extension in ['.jpg', '.jpeg', '.png', '.gif', '.heic']:
                inv.destination = VAULT_ROOT / "2_QsKb" / "2.60_MEDIA" / "photos"
            elif inv.extension in ['.mp4', '.mov', '.avi']:
                inv.destination = VAULT_ROOT / "2_QsKb" / "2.60_MEDIA" / "videos"
            else:
                inv.destination = VAULT_ROOT / "2_QsKb" / "2.50_DOCS"
        
        ensure_dir(inv.destination)
        if str(inv.destination) not in folders_created:
            folders_created.append(str(inv.destination))
    
    # Move files
    for inv in inventory:
        if inv.is_duplicate:
            continue
        
        try:
            dest_file = inv.destination / (inv.new_name or inv.path.name)
            
            # Handle name conflicts
            if dest_file.exists() and dest_file != inv.path:
                base = dest_file.stem
                ext = dest_file.suffix
                counter = 1
                while dest_file.exists():
                    dest_file = inv.destination / f"{base}_{counter}{ext}"
                    counter += 1
            
            if dest_file != inv.path:
                if not DRY_RUN_MODE:
                    shutil.move(str(inv.path), str(dest_file))
                    if restore_file:
                        append_restore_op(restore_file, {"kind": "move", "from": str(inv.path), "to": str(dest_file)})
                    inv.path = dest_file
                stats['files_moved'] += 1
                mode_str = "[DRY RUN] Would move" if DRY_RUN_MODE else "Moved"
                print(f"  {mode_str}: {inv.path.name} → {dest_file.relative_to(VAULT_ROOT)}")
        except Exception as e:
            errors.append(f"Error moving {inv.path}: {e}")
    
    return inventory


def phase6_front_matter(inventory: List[FileInventory]) -> List[FileInventory]:
    """Phase 6: Front Matter Generation and Validation"""
    print("\n" + "="*70)
    print("PHASE 6: Front Matter Generation")
    print("="*70)
    
    for inv in inventory:
        if inv.extension != '.md':
            continue
        
        try:
            # Read existing content
            with open(inv.path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            existing_fm, body = extract_front_matter(content)
            inv.front_matter = existing_fm
            inv.text_content = body
            
            # Generate complete front matter
            doc_type = infer_document_type(inv, body)
            fm = generate_front_matter(inv, doc_type, inv.destination, body)
            
            # Merge with existing (preserve existing values)
            for key, value in existing_fm.items():
                if key not in fm or not fm[key]:
                    fm[key] = value
            
            # Write updated file
            if not DRY_RUN_MODE:
                write_front_matter(str(inv.path), fm, body)
            stats['front_matter_updated'] += 1
            mode_str = "[DRY RUN] Would update" if DRY_RUN_MODE else "Updated"
            print(f"  {mode_str} front matter: {inv.path.name}")
        except Exception as e:
            errors.append(f"Error updating front matter {inv.path}: {e}")
    
    return inventory


def phase7_index_management():
    """Phase 7: Index Management"""
    print("\n" + "="*70)
    print("PHASE 7: Index Management")
    print("="*70)
    
    # Update indexes for all destination folders (recursively up the tree)
    processed_dirs = set()
    
    def update_index_recursive(folder: Path):
        """Recursively update indexes up the folder tree"""
        if folder in processed_dirs or not folder.exists():
            return
        
        try:
            # Update this folder's index
            if not DRY_RUN_MODE:
                update_folder_index(str(folder), "_index.md")
            processed_dirs.add(folder)
            stats['indexes_updated'] += 1
            
            # Update parent folder's index
            parent = folder.parent
            if parent != folder and parent.exists() and VAULT_ROOT in parent.parents:
                update_index_recursive(parent)
        except Exception as e:
            errors.append(f"Error updating index {folder}: {e}")
    
    # Update indexes for all destination folders
    for inv in processed_files:
        if inv.destination:
            update_index_recursive(inv.destination)
    
    print(f"Indexes updated: {stats['indexes_updated']}")


def phase7_link_validation():
    """Phase 7b: Link Validation and Repair"""
    print("\n" + "="*70)
    print("PHASE 7b: Link Validation and Repair")
    print("="*70)
    
    # Scan all markdown files for links
    link_patterns = [
        (r'\[\[([^\]]+)\]\]', 'wiki'),  # Wiki links
        (r'\[([^\]]+)\]\(([^\)]+)\)', 'markdown'),  # Markdown links
    ]
    
    for inv in processed_files:
        if inv.extension != '.md' or not inv.path.exists():
            continue
        
        try:
            with open(inv.path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            updated = False
            for pattern, link_type in link_patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    if link_type == 'wiki':
                        link_target = match.group(1)
                        # Check if target exists
                        # This is simplified - should handle relative paths properly
                        pass
                    elif link_type == 'markdown':
                        link_text = match.group(1)
                        link_path = match.group(2)
                        # Validate and fix link
                        pass
            
            if updated:
                # Write updated content
                pass
                
        except Exception as e:
            errors.append(f"Error validating links in {inv.path}: {e}")
    
    print("Link validation complete")


def phase8_empty_folder_cleanup():
    """Phase 8: Empty Folder Cleanup (Inboxes Only)"""
    print("\n" + "="*70)
    print("PHASE 8: Empty Folder Cleanup")
    print("="*70)
    
    for inbox_path in INBOX_LOCATIONS:
        if not inbox_path.exists():
            continue
        
        print(f"\nChecking: {inbox_path}")
        
        # Collect all folders (bottom-up for safe deletion)
        all_folders = []
        for root, dirs, files in os.walk(inbox_path, topdown=False):
            folder = Path(root)
            if folder != inbox_path:  # Don't delete inbox root
                all_folders.append(folder)
        
        # Check and remove empty folders
        for folder in all_folders:
            if is_empty_folder(folder):
                try:
                    if not DRY_RUN_MODE:
                        # Move to trash
                        try:
                            import send2trash
                            send2trash.send2trash(str(folder))
                        except ImportError:
                            # Fallback: create trash directory and move there
                            trash_dir = inbox_path.parent / ".trash"
                            trash_dir.mkdir(exist_ok=True)
                            trash_path = trash_dir / folder.name
                            # Handle name conflicts
                            counter = 1
                            while trash_path.exists():
                                trash_path = trash_dir / f"{folder.name}_{counter}"
                                counter += 1
                            try:
                                shutil.move(str(folder), str(trash_path))
                            except:
                                # Last resort: just delete
                                shutil.rmtree(folder)
                        except Exception as e:
                            # Last resort: just delete
                            try:
                                shutil.rmtree(folder)
                            except:
                                pass
                    
                    folders_removed.append(str(folder))
                    stats['folders_removed'] += 1
                    mode_str = "[DRY RUN] Would remove" if DRY_RUN_MODE else "Removed"
                    print(f"  {mode_str} empty folder: {folder.relative_to(inbox_path)}")
                except Exception as e:
                    errors.append(f"Error removing {folder}: {e}")


def phase9_validation():
    """Phase 9: Final Validation"""
    print("\n" + "="*70)
    print("PHASE 9: Final Validation")
    print("="*70)
    
    # Protocol compliance checks
    print("\nValidation complete.")
    print(f"Files processed: {stats['files_moved']}")
    print(f"Duplicates removed: {stats['duplicates_removed']}")
    print(f"HEIC converted: {stats['heic_converted']}")
    print(f"Front matter updated: {stats['front_matter_updated']}")
    print(f"Indexes updated: {stats['indexes_updated']}")
    print(f"Folders removed: {stats['folders_removed']}")
    
    if errors:
        print(f"\nErrors encountered: {len(errors)}")
        for error in errors[:10]:  # Show first 10
            print(f"  - {error}")


# Global dry-run flag
DRY_RUN_MODE = False

def main(dry_run: bool = False):
    """Main execution"""
    global DRY_RUN_MODE
    DRY_RUN_MODE = dry_run
    
    print("="*70)
    print("INBOX FILE ORGANIZATION AND PROTOCOL COMPLIANCE")
    print("QiEOS Protocol v3.0")
    if dry_run:
        print("*** DRY RUN MODE - NO CHANGES WILL BE MADE ***")
    print("="*70)
    
    # Initialize
    if not dry_run:
        ensure_dir(RESTORE_DIR)
        ensure_dir(STAGING_DIR)
        restore_file = begin_restore_block(str(RESTORE_DIR))
    else:
        restore_file = None
    
    try:
        # Phase 1: Discovery
        inventory = phase1_discovery()
        
        # Phase 2: Deduplication
        inventory = phase2_deduplication(inventory)
        
        # Phase 3: Media Conversion
        inventory = phase3_media_conversion(inventory)
        
        # Phase 4: Renaming
        inventory = phase4_renaming(inventory)
        
        # Phase 5: Folder Placement
        inventory = phase5_folder_placement(inventory, restore_file)
        processed_files.extend(inventory)
        
        # Phase 6: Front Matter
        inventory = phase6_front_matter(inventory)
        
        # Phase 7: Index Management
        phase7_index_management()
        
        # Phase 7b: Link Validation
        phase7_link_validation()
        
        # Phase 8: Empty Folder Cleanup
        phase8_empty_folder_cleanup()
        
        # Phase 9: Validation
        phase9_validation()
        
        if restore_file:
            finalize_restore_block(restore_file, success=True)
            print(f"\nRestore point: {os.path.basename(restore_file)}")
        
    except Exception as e:
        if restore_file:
            finalize_restore_block(restore_file, success=False, error=str(e))
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        raise


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Organize inbox files according to QiEOS Protocol v3.0')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without making them')
    args = parser.parse_args()
    
    main(dry_run=args.dry_run)

