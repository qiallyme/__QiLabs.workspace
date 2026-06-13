#!/usr/bin/env python3
"""
Check if .md files in Downloads are duplicates of CSV records
"""
import csv
import re
from pathlib import Path
from collections import defaultdict

DOWNLOADS_DIR = Path(r"C:\Users\codyr\Downloads")

def parse_md_file(md_file):
    """Parse .md file and extract key information."""
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
        
        return {
            'title': title,
            'company_name': title,
            'uds': data.get('UDS', ''),
            'uniqueid': data.get('UniqueID', ''),
            'email': data.get('Email 2', ''),
            'phone': data.get('Phone 2', ''),
            'city': data.get('City', ''),
            'state': data.get('State', ''),
            'source': data.get('Source 2', ''),
        }
    except:
        return None

def search_csv_for_md_data(csv_file, md_data):
    """Search CSV for matching data from .md file."""
    matches = []
    
    try:
        with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, 1):
                match_score = 0
                match_fields = []
                
                row_text = ' '.join(str(v) for v in row.values() if v).upper()
                
                # Check UDS
                if md_data['uds'] and md_data['uds'] != 'missing':
                    if md_data['uds'] in row_text:
                        match_score += 30
                        match_fields.append('UDS')
                
                # Check UniqueID
                if md_data['uniqueid'] and md_data['uniqueid'] != 'missing':
                    if md_data['uniqueid'] in row_text:
                        match_score += 30
                        match_fields.append('UniqueID')
                
                # Check company name
                if md_data['company_name'] and len(md_data['company_name']) > 3:
                    company_upper = md_data['company_name'].upper()
                    for key, value in row.items():
                        if value and company_upper in str(value).upper():
                            if len(company_upper) > 5 or company_upper in ['LLC', 'INC', 'CORP']:
                                match_score += 10
                                match_fields.append('Company Name')
                                break
                
                if match_score >= 10:
                    matches.append({
                        'row': row_num,
                        'score': match_score,
                        'fields': match_fields,
                        'csv_file': csv_file.name
                    })
    except:
        pass
    
    return matches

def main():
    print("=== Checking .md files against CSV records ===\n")
    
    # Find CSV files
    csv_files = list(DOWNLOADS_DIR.glob('*.csv'))
    if (DOWNLOADS_DIR / "_extracted_csvs").exists():
        csv_files.extend((DOWNLOADS_DIR / "_extracted_csvs").glob('*.csv'))
    
    print(f"Found {len(csv_files)} CSV files")
    
    # Process .md files (sample first 1000 for speed)
    md_files = list(DOWNLOADS_DIR.glob('*.md'))
    print(f"Found {len(md_files)} .md files")
    print(f"Checking first 1000 for matches...\n")
    
    matched_files = []
    
    for idx, md_file in enumerate(md_files[:1000]):
        if idx % 100 == 0:
            print(f"  Processed {idx}/1000...")
        
        md_data = parse_md_file(md_file)
        if not md_data or not md_data.get('title'):
            continue
        
        all_matches = []
        for csv_file in csv_files:
            matches = search_csv_for_md_data(csv_file, md_data)
            all_matches.extend(matches)
        
        if all_matches:
            best_match = max(all_matches, key=lambda x: x['score'])
            matched_files.append({
                'md_file': md_file.name,
                'title': md_data['title'],
                'best_match': best_match
            })
    
    print(f"\n=== Results (sample of 1000) ===")
    print(f"Matched: {len(matched_files)}")
    print(f"Match rate: {len(matched_files)/1000*100:.1f}%\n")
    
    if matched_files:
        print("Sample matches:")
        for match in matched_files[:10]:
            print(f"  {match['md_file']}")
            print(f"    → {match['best_match']['csv_file']} (score: {match['best_match']['score']})")
    
    return len(matched_files), len(md_files)

if __name__ == '__main__':
    main()

