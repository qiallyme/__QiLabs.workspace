#!/usr/bin/env python3
"""
Debug script to check CSV loading
"""

import csv

def debug_csv():
    slug_mapping = {
        "clients": {},
        "entities": {},
        "topics": {}
    }
    
    try:
        with open('slugs_mapping.csv', mode='r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                type_slug = row['Type'].strip().lower()
                slug = row['Slug'].strip().lower()
                full_name = row['Full Name'].strip()
                
                print(f"Processing: {type_slug} -> {slug} -> {full_name}")
                
                if type_slug in slug_mapping:
                    slug_mapping[type_slug][slug] = full_name
                else:
                    print(f"Warning: Unknown type '{type_slug}'")
    except FileNotFoundError:
        print("CSV file not found")
        return
    
    print("\n=== Final Mapping ===")
    for type_name, mappings in slug_mapping.items():
        print(f"\n{type_name}:")
        for slug, full_name in mappings.items():
            print(f"  {slug} -> {full_name}")
    
    # Test specific lookups
    print("\n=== Test Lookups ===")
    print(f"legal -> {slug_mapping.get('entities', {}).get('legal', 'NOT FOUND')}")
    print(f"cover-letter -> {slug_mapping.get('topics', {}).get('cover-letter', 'NOT FOUND')}")
    print(f"affidavit -> {slug_mapping.get('topics', {}).get('affidavit', 'NOT FOUND')}")

if __name__ == "__main__":
    debug_csv()
