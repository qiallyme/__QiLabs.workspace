#!/usr/bin/env python3
"""
Compare .md files with CSV records to identify duplicates
"""
import csv
import re
from pathlib import Path
from collections import defaultdict

INBOX_DIR = Path(r"C:\QiOS\_inbox")
EXTRACTED_DIR = INBOX_DIR / "_extracted_csvs"

def parse_md_file(md_path):
    """Parse a .md file and extract key fields."""
    try:
        content = md_path.read_text(encoding='utf-8', errors='ignore')
        lines = content.split('\n')
        
        # Extract title (first line after #)
        title = None
        data = {}
        
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
        
        # Extract key identifiers
        identifiers = {
            'Title': title,
            'UDS': data.get('UDS', ''),
            'UniqueID': data.get('UniqueID', ''),
            'Business Name': data.get('Company 2', '') or title,
            'Email': data.get('Email 2', ''),
            'Phone': data.get('Phone 2', ''),
        }
        
        return identifiers, data
    except Exception as e:
        return None, None

def load_csv_records(csv_path):
    """Load CSV records into a searchable structure."""
    records = []
    try:
        with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(row)
        return records
    except Exception as e:
        print(f"Error loading {csv_path}: {e}")
        return []

def find_matches_in_csv(md_identifiers, csv_records):
    """Find matching records in CSV."""
    matches = []
    
    title = md_identifiers.get('Title', '').upper()
    uds = md_identifiers.get('UDS', '').upper()
    unique_id = md_identifiers.get('UniqueID', '').upper()
    business_name = md_identifiers.get('Business Name', '').upper()
    email = md_identifiers.get('Email', '').upper()
    
    for idx, record in enumerate(csv_records):
        match_score = 0
        match_reasons = []
        
        # Check Business Name field
        record_business = str(record.get('Business Name', '')).upper()
        if business_name and business_name != 'MISSING' and title:
            if title in record_business or record_business in title:
                match_score += 10
                match_reasons.append('Business Name')
        
        # Check UDS field
        record_uds = str(record.get('UDS', '')).upper()
        if uds and uds in record_uds:
            match_score += 20
            match_reasons.append('UDS')
        
        # Check UniqueID
        record_uniqueid = str(record.get('UniqueID', '')).upper()
        if unique_id and unique_id in record_uniqueid:
            match_score += 30
            match_reasons.append('UniqueID')
        
        # Check email
        record_email = str(record.get('Email', '')).upper()
        if email and email != 'MISSING' and email in record_email:
            match_score += 5
            match_reasons.append('Email')
        
        if match_score > 0:
            matches.append({
                'index': idx,
                'score': match_score,
                'reasons': match_reasons,
                'record': record
            })
    
    return sorted(matches, key=lambda x: x['score'], reverse=True)

def main():
    print("=== Comparing .md files with CSV records ===\n")
    
    # Load CSV files
    csv_files = {
        'Contacts': list(INBOX_DIR.glob('*.csv')) + list(EXTRACTED_DIR.glob('*.csv')),
    }
    
    csv_records = {}
    for name, files in csv_files.items():
        all_records = []
        for csv_file in files:
            if 'Contact' in csv_file.name or 'Business' in csv_file.name:
                records = load_csv_records(csv_file)
                all_records.extend(records)
                print(f"Loaded {len(records)} records from {csv_file.name}")
        csv_records[name] = all_records
    
    if not csv_records.get('Contacts'):
        print("No CSV records found!")
        return
    
    # Process .md files
    md_files = list(INBOX_DIR.glob('*.md'))
    print(f"\nProcessing {len(md_files)} .md files...\n")
    
    matched_files = []
    unmatched_files = []
    
    for md_file in md_files[:100]:  # Sample first 100
        identifiers, data = parse_md_file(md_file)
        if not identifiers:
            continue
        
        # Check against all CSV records
        matches = find_matches_in_csv(identifiers, csv_records['Contacts'])
        
        if matches and matches[0]['score'] >= 10:  # At least Business Name match
            matched_files.append({
                'md_file': md_file.name,
                'title': identifiers.get('Title', ''),
                'best_match': matches[0],
                'all_matches': len(matches)
            })
        else:
            unmatched_files.append(md_file.name)
    
    # Report
    print(f"\n=== Results (sample of 100 files) ===")
    print(f"Matched: {len(matched_files)}")
    print(f"Unmatched: {len(unmatched_files)}\n")
    
    print("Sample matches:")
    for match in matched_files[:10]:
        print(f"\n  {match['md_file']}")
        print(f"    Title: {match['title']}")
        print(f"    Match score: {match['best_match']['score']}")
        print(f"    Match reasons: {', '.join(match['best_match']['reasons'])}")
        record = match['best_match']['record']
        print(f"    CSV record: {record.get('Business Name', 'N/A')} | {record.get('UDS', 'N/A')}")
    
    return matched_files, unmatched_files

if __name__ == '__main__':
    main()

