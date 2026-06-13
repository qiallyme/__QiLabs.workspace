#!/usr/bin/env python3
"""
Slug Mapping Generator for Wiki Content
Generates consistent file naming with abbreviations to prevent long filenames
"""

import csv
import json
import yaml
from datetime import datetime
from typing import Dict, Optional

class SlugMapper:
    def __init__(self, csv_file: str = 'slugs_mapping.csv'):
        self.slug_mapping = {
            "client": {},
            "entity": {},
            "topic": {}
        }
        self.load_slug_mapping(csv_file)
    
    def load_slug_mapping(self, csv_file: str):
        """Load slug mapping from CSV file"""
        try:
            with open(csv_file, mode='r', encoding='utf-8') as file:
                csv_reader = csv.DictReader(file)
                for row in csv_reader:
                    type_slug = row['Type'].strip().lower()
                    slug = row['Slug'].strip().lower()
                    full_name = row['Full Name'].strip()
                    
                    if type_slug in self.slug_mapping:
                        self.slug_mapping[type_slug][slug] = full_name
        except FileNotFoundError:
            print(f"Warning: {csv_file} not found. Using empty mapping.")
    
    def get_abbreviation(self, type_slug: str, slug: str) -> str:
        """Get abbreviation for a given type and slug"""
        return self.slug_mapping.get(type_slug, {}).get(slug.lower(), slug)
    
    def generate_filename(self, 
                         client_slug: str,
                         entity: str,
                         topic: str,
                         date: str = None,
                         version: str = None,
                         detail: str = None,
                         status: str = None,
                         extension: str = "pdf") -> str:
        """
        Generate filename with abbreviations to keep length manageable
        
        Format: {date}_{client}_{entity}_{topic}_{version}_{detail}_{status}.{ext}
        Max length: 80 characters (including extension)
        """
        
        # Get abbreviations
        client_abbr = self.get_abbreviation('client', client_slug)
        entity_abbr = self.get_abbreviation('entity', entity)
        topic_abbr = self.get_abbreviation('topic', topic)
        
        # Use current date if not provided
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        # Build filename parts
        parts = [date, client_abbr, entity_abbr, topic_abbr]
        
        # Add optional parts if provided
        if version:
            parts.append(version)
        if detail:
            # Get abbreviation for detail
            detail_abbr = self.get_abbreviation('topic', detail)
            if len(detail_abbr) > 15:
                detail_abbr = detail_abbr[:15]
            parts.append(detail_abbr)
        if status:
            parts.append(status)
        
        # Join parts with underscores
        filename = "_".join(parts) + f".{extension}"
        
        # Ensure filename doesn't exceed 80 characters
        if len(filename) > 80:
            # Truncate detail part if it exists
            if detail and len(parts) > 4:
                detail_index = 4
                if len(parts) > 5:  # If status exists, detail is at index 4
                    detail_index = 4
                else:
                    detail_index = 4
                
                # Truncate detail to fit
                max_detail_length = 80 - len("_".join(parts[:detail_index] + parts[detail_index+1:])) - len(extension) - 2
                parts[detail_index] = parts[detail_index][:max_detail_length]
                filename = "_".join(parts) + f".{extension}"
        
        return filename
    
    def generate_immigration_filename(self,
                                    client_slug: str,
                                    form_type: str,
                                    document_type: str,
                                    date: str = None,
                                    version: str = "v01",
                                    status: str = "final",
                                    extension: str = "pdf") -> str:
        """
        Generate immigration-specific filename with abbreviations
        
        Examples:
        - 2025-09-28_qia_Leg_i589_CL_v01_final.pdf
        - 2025-09-28_qia_Leg_i360_PS_v01_final.pdf
        """
        # Get abbreviations
        client_abbr = self.get_abbreviation('client', client_slug)
        entity_abbr = self.get_abbreviation('entity', 'legal')
        topic_abbr = self.get_abbreviation('topic', document_type)
        
        # Use current date if not provided
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        # Build filename parts
        parts = [date, client_abbr, entity_abbr, form_type, topic_abbr, version, status]
        
        # Join parts with underscores
        filename = "_".join(parts) + f".{extension}"
        
        # Ensure filename doesn't exceed 80 characters
        if len(filename) > 80:
            # Truncate topic abbreviation if too long
            if len(topic_abbr) > 10:
                topic_abbr = topic_abbr[:10]
                parts[4] = topic_abbr
                filename = "_".join(parts) + f".{extension}"
        
        return filename
    
    def export_to_json(self, output_file: str = 'slugs_mapping.json'):
        """Export slug mapping to JSON"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.slug_mapping, f, indent=2, ensure_ascii=False)
    
    def export_to_yaml(self, output_file: str = 'slugs_mapping.yaml'):
        """Export slug mapping to YAML"""
        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.dump(self.slug_mapping, f, default_flow_style=False, allow_unicode=True)

def main():
    """Main function to demonstrate usage"""
    mapper = SlugMapper()
    
    # Export mappings
    mapper.export_to_json()
    mapper.export_to_yaml()
    
    # Example usage
    print("=== Immigration File Naming Examples ===")
    
    # I-589 (Asylum) examples
    print("I-589 (Asylum):")
    print(f"  Cover Letter: {mapper.generate_immigration_filename('qia', 'i589', 'cover-letter')}")
    print(f"  Affidavit: {mapper.generate_immigration_filename('qia', 'i589', 'affidavit')}")
    print(f"  Form: {mapper.generate_immigration_filename('qia', 'i589', 'form')}")
    
    # I-360 (Special Immigrant) examples
    print("\nI-360 (Special Immigrant):")
    print(f"  Cover Letter: {mapper.generate_immigration_filename('qia', 'i360', 'cover-letter')}")
    print(f"  Personal Statement: {mapper.generate_immigration_filename('qia', 'i360', 'personal-statement')}")
    
    # I-130 (Family Sponsorship) examples
    print("\nI-130 (Family Sponsorship):")
    print(f"  Cover Letter: {mapper.generate_immigration_filename('qia', 'i130', 'cover-letter')}")
    print(f"  Evidence of Relationship: {mapper.generate_immigration_filename('qia', 'i130', 'evidence-of-relationship')}")
    
    # I-765 (Employment Authorization) examples
    print("\nI-765 (Employment Authorization):")
    print(f"  Cover Letter: {mapper.generate_immigration_filename('qia', 'i765', 'cover-letter')}")
    print(f"  Form: {mapper.generate_immigration_filename('qia', 'i765', 'form')}")
    
    # I-485 (Adjustment of Status) examples
    print("\nI-485 (Adjustment of Status):")
    print(f"  Cover Letter: {mapper.generate_immigration_filename('qia', 'i485', 'cover-letter')}")
    print(f"  Medical Exam: {mapper.generate_immigration_filename('qia', 'i485', 'medical-exam')}")
    
    # Drafts and Strategy examples
    print("\nDrafts and Strategy:")
    print(f"  Strategy Plan: {mapper.generate_filename('qia', 'legal', 'strategy-plan', version='v01', status='final')}")
    print(f"  Timeline: {mapper.generate_filename('qia', 'legal', 'timeline', version='v01', status='final')}")
    print(f"  Draft Affidavit: {mapper.generate_filename('qia', 'legal', 'drafts', detail='affidavit', version='v01', status='draft')}")
    
    # Bio and IDs examples
    print("\nBio and IDs:")
    print(f"  Passport Copy: {mapper.generate_filename('qia', 'legal', 'bio-and-ids', detail='passport-copy')}")
    print(f"  Birth Certificate: {mapper.generate_filename('qia', 'legal', 'bio-and-ids', detail='birth-certificate')}")
    
    # Employment examples
    print("\nEmployment:")
    print(f"  Offer Letter: {mapper.generate_filename('qia', 'legal', 'employment', detail='offer-letter')}")
    print(f"  Pay Stubs: {mapper.generate_filename('qia', 'legal', 'employment', detail='pay-stubs')}")
    
    # Financial examples
    print("\nFinancial:")
    print(f"  Tax Returns: {mapper.generate_filename('qia', 'legal', 'financial', detail='tax-returns')}")
    print(f"  Bank Statements: {mapper.generate_filename('qia', 'legal', 'financial', detail='bank-statements')}")

if __name__ == "__main__":
    main()
