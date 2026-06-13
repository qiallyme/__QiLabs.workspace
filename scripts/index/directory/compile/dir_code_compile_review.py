#!/usr/bin/env python3
"""
Compile Code Review Document
Reads all source files and creates a comprehensive code review document.
"""

import os
from pathlib import Path
from typing import List, Tuple

def get_file_list(root: Path) -> List[Path]:
    """Get all source files recursively."""
    files = []
    for path in root.rglob('*'):
        if path.is_file():
            # Skip the extraction summary and this script
            if path.name in {'EXTRACTION_SUMMARY.md', 'CODE_REVIEW.md'}:
                continue
            files.append(path)
    return sorted(files)

def read_file_safe(path: Path) -> Tuple[str, bool]:
    """Read file content, handling binary files."""
    try:
        # Try reading as text first
        content = path.read_text(encoding='utf-8', errors='replace')
        return content, True
    except UnicodeDecodeError:
        # Binary file - return placeholder
        return f"[Binary file: {path.name} - {path.stat().st_size} bytes]", False
    except Exception as e:
        return f"[Error reading file: {e}]", False

def format_file_content(rel_path: Path, content: str, is_text: bool) -> str:
    """Format file content for markdown."""
    lines = content.split('\n')
    line_count = len(lines)
    
    # Determine language from extension
    ext = rel_path.suffix.lower()
    lang_map = {
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.json': 'json',
        '.css': 'css',
        '.html': 'html',
        '.md': 'markdown',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.toml': 'toml',
        '.patch': 'diff',
        '.svg': 'xml',
        '.wasm': None,  # Binary
    }
    lang = lang_map.get(ext, 'text')
    
    header = f"## `{rel_path}`\n\n"
    if not is_text:
        header += f"*Binary file - {content}*\n\n"
        return header
    
    header += f"*{line_count} lines*\n\n"
    
    if lang:
        code_block = f"```{lang}\n{content}\n```\n\n"
    else:
        code_block = f"```\n{content}\n```\n\n"
    
    return header + code_block

def compile_review(source_dir: Path, output_file: Path):
    """Compile all files into a code review document."""
    source_dir = Path(source_dir).resolve()
    output_file = Path(output_file).resolve()
    
    files = get_file_list(source_dir)
    
    # Group files by directory
    by_dir = {}
    for file in files:
        rel_path = file.relative_to(source_dir)
        dir_path = rel_path.parent
        if dir_path not in by_dir:
            by_dir[dir_path] = []
        by_dir[dir_path].append((rel_path, file))
    
    # Build document
    doc_parts = [
        "# Code Review Document\n\n",
        f"**Source:** `{source_dir}`\n\n",
        f"**Total Files:** {len(files)}\n\n",
        "---\n\n",
    ]
    
    # Add table of contents
    doc_parts.append("## Table of Contents\n\n")
    for dir_path in sorted(by_dir.keys()):
        if dir_path == Path('.'):
            section = "Root Files"
        else:
            section = f"`{dir_path}/`"
        doc_parts.append(f"- [{section}](#{section.lower().replace(' ', '-').replace('/', '-').replace('`', '')})\n")
    doc_parts.append("\n---\n\n")
    
    # Add file contents organized by directory
    for dir_path in sorted(by_dir.keys()):
        if dir_path == Path('.'):
            doc_parts.append("## Root Files\n\n")
        else:
            doc_parts.append(f"## `{dir_path}/`\n\n")
        
        for rel_path, file_path in sorted(by_dir[dir_path]):
            content, is_text = read_file_safe(file_path)
            doc_parts.append(format_file_content(rel_path, content, is_text))
            doc_parts.append("---\n\n")
    
    # Write document
    output_file.write_text(''.join(doc_parts), encoding='utf-8')
    print(f"Code review document created: {output_file}")
    print(f"Total files: {len(files)}")
    print(f"Document size: {output_file.stat().st_size / 1024 / 1024:.2f} MB")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python compile_code_review.py <source_dir> [output_file]")
        sys.exit(1)
    
    source_dir = Path(sys.argv[1])
    if len(sys.argv) > 2:
        output_file = Path(sys.argv[2])
    else:
        output_file = source_dir / 'CODE_REVIEW.md'
    
    compile_review(source_dir, output_file)

