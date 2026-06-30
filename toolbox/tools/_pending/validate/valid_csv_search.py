#!/usr/bin/env python3
"""
Search CSV files for UDS values from .md files
"""
import csv
import re
from pathlib import Path

INBOX_DIR = Path(r"C:\QiOS\_inbox")

def extract_uds_from_md(md_file):
    """Extract UDS from .md file."""
    try:
        content = md_file.read_text(encoding='utf-8', errors='ignore')
        uds_match = re.search(r'UDS:\s*(UDS-\d+)', content)
        uniqueid_match = re.search(r'UniqueID:\s*([^\n]+)', content)
        title_match = re.search(r'^#\s*(.+)$', content, re.MULTILINE)
        return {
            'uds': uds_match.group(1) if uds_match else None,
            'uniqueid': uniqueid_match.group(1).strip() if uniqueid_match else None,
            'title': title_match.group(1).strip() if title_match else None
        }
    except:
        return None

def search_csv_for_value(csv_file, search_value):
    """Search CSV file for a value in any field."""
    try:
        with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, 1):
                # Search all fields
                row_text = ' '.join(str(v) for v in row.values())
                if search_value in row_text:
                    return {
                        'found': True,
                        'row': row_num,
                        'file': csv_file.name,
                        'sample': {k: v for k, v in list(row.items())[:5] if v}
                    }
        return {'found': False}
    except Exception as e:
        return {'found': False, 'error': str(e)}

def main():
    # Get sample .md file
    sample_md = INBOX_DIR / "ALFONSO RODRIGUEZ VALVERDE LLC 1e4f84a044028152922efb3bcb7b2a6b.md"
    md_data = extract_uds_from_md(sample_md)
    
    print(f"Sample .md file: {sample_md.name}")
    print(f"  Title: {md_data['title']}")
    print(f"  UDS: {md_data['uds']}")
    print(f"  UniqueID: {md_data['uniqueid']}\n")
    
    # Find all CSV files
    csv_files = []
    csv_files.extend(INBOX_DIR.glob('*.csv'))
    csv_files.extend(INBOX_DIR.rglob('*Business*.csv'))
    csv_files.extend(INBOX_DIR.rglob('*Renewal*.csv'))
    if (INBOX_DIR / "_extracted_csvs").exists():
        csv_files.extend((INBOX_DIR / "_extracted_csvs").glob('*.csv'))
    
    print(f"Searching {len(csv_files)} CSV files...\n")
    
    # Search for UDS
    if md_data['uds']:
        print(f"Searching for UDS: {md_data['uds']}")
        for csv_file in csv_files[:10]:  # Sample first 10
            result = search_csv_for_value(csv_file, md_data['uds'])
            if result.get('found'):
                print(f"  ✓ Found in {csv_file.name} row {result['row']}")
                print(f"    Sample: {result.get('sample', {})}")
    
    # Search for UniqueID
    if md_data['uniqueid']:
        print(f"\nSearching for UniqueID: {md_data['uniqueid']}")
        for csv_file in csv_files[:10]:
            result = search_csv_for_value(csv_file, md_data['uniqueid'])
            if result.get('found'):
                print(f"  ✓ Found in {csv_file.name} row {result['row']}")
                print(f"    Sample: {result.get('sample', {})}")
    
    # Search for title
    if md_data['title']:
        print(f"\nSearching for title: {md_data['title']}")
        for csv_file in csv_files[:10]:
            result = search_csv_for_value(csv_file, md_data['title'])
            if result.get('found'):
                print(f"  ✓ Found in {csv_file.name} row {result['row']}")
                print(f"    Sample: {result.get('sample', {})}")

if __name__ == '__main__':
    main()

