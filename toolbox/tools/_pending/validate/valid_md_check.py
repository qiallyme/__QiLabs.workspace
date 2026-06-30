#!/usr/bin/env python3
"""
Comprehensive check: Find .md files whose content appears in CSV files
"""
import csv
import re
from pathlib import Path
from collections import defaultdict

INBOX_DIR = Path(r"C:\QiOS\_inbox")

def parse_md_file(md_file):
    """Parse .md file and extract all key information."""
    try:
        content = md_file.read_text(encoding='utf-8', errors='ignore')
        lines = content.split('\n')
        
        data = {}
        title = None
        
        for line in lines:
            line = line.strip()
            if line.startswith('# '):
                title = line[2:].strip()
                data['Title'] = title
            elif ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                data[key] = value
        
        # Extract key fields
        return {
            'title': title,
            'company_name': title,  # Usually the title is the company name
            'uds': data.get('UDS', ''),
            'uniqueid': data.get('UniqueID', ''),
            'email': data.get('Email 2', ''),
            'phone': data.get('Phone 2', ''),
            'address': data.get('Address', ''),
            'city': data.get('City', ''),
            'state': data.get('State', ''),
            'zip': data.get('ZIP', ''),
            'source': data.get('Source 2', ''),
            'full_content': content
        }
    except:
        return None

def search_csv_for_md_data(csv_file, md_data):
    """Search CSV for any matching data from .md file."""
    matches = []
    
    try:
        with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, 1):
                match_score = 0
                match_fields = []
                
                # Get all values from CSV row as text
                row_text = ' '.join(str(v) for v in row.values() if v).upper()
                
                # Check title/company name
                if md_data['company_name']:
                    company_upper = md_data['company_name'].upper()
                    if company_upper in row_text or any(company_upper in str(v).upper() for v in row.values() if v):
                        match_score += 10
                        match_fields.append('Company Name')
                
                # Check UDS
                if md_data['uds'] and md_data['uds'] != 'missing':
                    if md_data['uds'] in row_text:
                        match_score += 20
                        match_fields.append('UDS')
                
                # Check UniqueID
                if md_data['uniqueid'] and md_data['uniqueid'] != 'missing':
                    if md_data['uniqueid'] in row_text:
                        match_score += 30
                        match_fields.append('UniqueID')
                
                # Check address components
                if md_data['city'] and md_data['city'] != 'missing':
                    if md_data['city'].upper() in row_text:
                        match_score += 2
                        match_fields.append('City')
                
                if md_data['state'] and md_data['state'] != 'missing':
                    if md_data['state'].upper() in row_text:
                        match_score += 2
                        match_fields.append('State')
                
                if match_score >= 10:  # At least company name match
                    matches.append({
                        'row': row_num,
                        'score': match_score,
                        'fields': match_fields,
                        'csv_row': {k: v for k, v in row.items() if v}
                    })
    except Exception as e:
        pass
    
    return matches

def main():
    print("=== Comprehensive .md to CSV Comparison ===\n")
    
    # Find all CSV files
    csv_files = []
    csv_files.extend(INBOX_DIR.glob('*.csv'))
    csv_files.extend(INBOX_DIR.rglob('*Business*.csv'))
    csv_files.extend(INBOX_DIR.rglob('*Renewal*.csv'))
    csv_files.extend(INBOX_DIR.rglob('*Contact*.csv'))
    if (INBOX_DIR / "_extracted_csvs").exists():
        csv_files.extend((INBOX_DIR / "_extracted_csvs").glob('*.csv'))
    
    # Remove duplicates
    csv_files = list(set(csv_files))
    
    print(f"Found {len(csv_files)} CSV files")
    print(f"Sample: {[f.name for f in csv_files[:5]]}\n")
    
    # Process .md files
    md_files = list(INBOX_DIR.glob('*.md'))
    print(f"Processing {len(md_files)} .md files...\n")
    
    matched_files = []
    unmatched_files = []
    
    # Sample first 50 for testing
    for md_file in md_files[:50]:
        md_data = parse_md_file(md_file)
        if not md_data or not md_data.get('title'):
            continue
        
        all_matches = []
        for csv_file in csv_files:
            matches = search_csv_for_md_data(csv_file, md_data)
            for match in matches:
                match['csv_file'] = csv_file.name
                all_matches.append(match)
        
        if all_matches:
            # Get best match
            best_match = max(all_matches, key=lambda x: x['score'])
            matched_files.append({
                'md_file': md_file.name,
                'title': md_data['title'],
                'best_match': best_match,
                'total_matches': len(all_matches)
            })
        else:
            unmatched_files.append({
                'file': md_file.name,
                'title': md_data['title']
            })
    
    # Report
    print(f"\n=== Results (sample of 50) ===")
    print(f"Matched: {len(matched_files)}")
    print(f"Unmatched: {len(unmatched_files)}\n")
    
    print("Sample matches:")
    for match in matched_files[:10]:
        print(f"\n  {match['md_file']}")
        print(f"    Title: {match['title']}")
        print(f"    Best match: {match['best_match']['csv_file']} row {match['best_match']['row']}")
        print(f"    Score: {match['best_match']['score']} (matched: {', '.join(match['best_match']['fields'])})")
        csv_row = match['best_match']['csv_row']
        print(f"    CSV data: {dict(list(csv_row.items())[:3])}")
    
    return matched_files

if __name__ == '__main__':
    main()

