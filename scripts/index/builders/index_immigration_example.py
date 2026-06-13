#!/usr/bin/env python3
"""
Generate the complete immigration folder structure with abbreviated filenames
"""

from slugs_mapping import SlugMapper

def generate_immigration_structure():
    mapper = SlugMapper()
    
    print("=== Complete Immigration Folder Structure with Abbreviated Filenames ===")
    print()
    
    print("50_Legal")
    print("└── 60_Immigration")
    print()
    
    # 00_Drafts_and_Strategy
    print("    ├── 00_Drafts_and_Strategy")
    print(f"    │   ├── {mapper.generate_filename('qia', 'legal', 'strategy', detail='plan', version='v01', status='final')}")
    print(f"    │   ├── {mapper.generate_filename('qia', 'legal', 'timeline', version='v01', status='final')}")
    print(f"    │   ├── {mapper.generate_filename('qia', 'legal', 'drafts', detail='affidavit', version='v01', status='draft')}")
    print(f"    │   ├── {mapper.generate_filename('qia', 'legal', 'timeline', detail='review', version='v01', status='final')}")
    print()
    
    # 10_Bio_and_IDs
    print("    ├── 10_Bio_and_IDs")
    print(f"    │   ├── {mapper.generate_filename('qia', 'legal', 'bio-and-ids', detail='passport-copy')}")
    print(f"    │   ├── {mapper.generate_filename('qia', 'legal', 'bio-and-ids', detail='birth-certificate')}")
    print(f"    │   ├── {mapper.generate_filename('qia', 'legal', 'bio-and-ids', detail='id-card-copy')}")
    print(f"    │   ├── {mapper.generate_filename('qia', 'legal', 'bio-and-ids', detail='marriage-certificate')}")
    print()
    
    # 20_Employment
    print("    ├── 20_Employment")
    print(f"    │   ├── {mapper.generate_filename('qia', 'legal', 'employment', detail='offer-letter')}")
    print(f"    │   ├── {mapper.generate_filename('qia', 'legal', 'employment', detail='pay-stubs')}")
    print(f"    │   ├── {mapper.generate_filename('qia', 'legal', 'employment', detail='w2-forms')}")
    print()
    
    # 30_Financial
    print("    ├── 30_Financial")
    print(f"    │   ├── {mapper.generate_filename('qia', 'legal', 'financial', detail='tax-returns')}")
    print(f"    │   ├── {mapper.generate_filename('qia', 'legal', 'financial', detail='bank-statements')}")
    print(f"    │   ├── {mapper.generate_filename('qia', 'legal', 'financial', detail='employment-income-statement')}")
    print()
    
    # 40_Other_Evidence
    print("    ├── 40_Other_Evidence")
    print(f"    │   ├── {mapper.generate_filename('qia', 'legal', 'other', detail='photos-relationship')}")
    print(f"    │   ├── {mapper.generate_filename('qia', 'legal', 'other', detail='letters-of-support')}")
    print(f"    │   └── {mapper.generate_filename('qia', 'legal', 'other', detail='utility-bills')}")
    print()
    
    # 50_Form_Filings
    print("    ├── 50_Form_Filings")
    print()
    
    # I-589 (Asylum)
    print("    │   ├── 10_I-589 (Asylum)")
    print(f"    │   │   ├── {mapper.generate_immigration_filename('qia', 'i589', 'cover-letter', status='final')}")
    print(f"    │   │   ├── {mapper.generate_immigration_filename('qia', 'i589', 'affidavit', version='v01', status='draft')}")
    print(f"    │   │   ├── {mapper.generate_immigration_filename('qia', 'i589', 'form', status='final')}")
    print(f"    │   │   ├── {mapper.generate_immigration_filename('qia', 'i589', 'evidence-of-status', status='final')}")
    print(f"    │   │   └── {mapper.generate_immigration_filename('qia', 'i589', 'supporting-docs', status='final')}")
    print()
    
    # I-360 (Special Immigrant)
    print("    │   ├── 20_I-360 (Special Immigrant)")
    print(f"    │   │   ├── {mapper.generate_immigration_filename('qia', 'i360', 'cover-letter', status='final')}")
    print(f"    │   │   ├── {mapper.generate_immigration_filename('qia', 'i360', 'personal-statement', status='final')}")
    print(f"    │   │   ├── {mapper.generate_immigration_filename('qia', 'i360', 'form', status='final')}")
    print(f"    │   │   └── {mapper.generate_immigration_filename('qia', 'i360', 'evidence-of-service', status='final')}")
    print()
    
    # I-130 (Family Sponsorship)
    print("    │   ├── 30_I-130 (Family Sponsorship)")
    print(f"    │   │   ├── {mapper.generate_immigration_filename('qia', 'i130', 'cover-letter', status='final')}")
    print(f"    │   │   ├── {mapper.generate_immigration_filename('qia', 'i130', 'evidence-of-relationship', status='final')}")
    print(f"    │   │   ├── {mapper.generate_immigration_filename('qia', 'i130', 'form', status='final')}")
    print(f"    │   │   └── {mapper.generate_immigration_filename('qia', 'i130', 'sponsor-proof', status='final')}")
    print()
    
    # I-765 (Employment Authorization)
    print("    │   ├── 40_I-765 (Employment Authorization)")
    print(f"    │   │   ├── {mapper.generate_immigration_filename('qia', 'i765', 'cover-letter', status='final')}")
    print(f"    │   │   ├── {mapper.generate_immigration_filename('qia', 'i765', 'form', status='final')}")
    print(f"    │   │   ├── {mapper.generate_immigration_filename('qia', 'i765', 'evidence-of-status', status='final')}")
    print(f"    │   │   └── {mapper.generate_immigration_filename('qia', 'i765', 'eligibility-documents', status='final')}")
    print()
    
    # I-485 (Adjustment of Status)
    print("    │   ├── 50_I-485 (Adjustment of Status)")
    print(f"    │   │   ├── {mapper.generate_immigration_filename('qia', 'i485', 'cover-letter', status='final')}")
    print(f"    │   │   ├── {mapper.generate_immigration_filename('qia', 'i485', 'form', status='final')}")
    print(f"    │   │   ├── {mapper.generate_immigration_filename('qia', 'i485', 'bio-and-ids', status='final')}")
    print(f"    │   │   ├── {mapper.generate_immigration_filename('qia', 'i485', 'evidence-of-status', status='final')}")
    print(f"    │   │   └── {mapper.generate_immigration_filename('qia', 'i485', 'medical-exam', status='final')}")
    print()
    
    # Change of Address
    print("    │   ├── 60_Change_of_Address")
    print(f"    │   │   └── {mapper.generate_filename('qia', 'legal', 'change-of-address', detail='form', status='final')}")
    print()
    
    # Indiana BMV License
    print("    │   ├── 70_Indiana_BMV_License")
    print(f"    │   │   ├── {mapper.generate_filename('qia', 'legal', 'indiana-bmv', detail='application', status='final')}")
    print(f"    │   │   └── {mapper.generate_filename('qia', 'legal', 'indiana-bmv', detail='documents', status='final')}")
    print()
    
    # Social Security Applications
    print("    │   ├── 80_Social_Security_Applications")
    print(f"    │   │   ├── {mapper.generate_filename('qia', 'legal', 'social-security', detail='application', status='final')}")
    print(f"    │   │   └── {mapper.generate_filename('qia', 'legal', 'social-security', detail='documents', status='final')}")
    print()
    
    # Archive
    print("    └── 90_Archive")
    print()
    
    print("=== Key Benefits of This Structure ===")
    print("✅ Filenames are under 80 characters")
    print("✅ Consistent abbreviations across all files")
    print("✅ Clear organization by form type and document category")
    print("✅ Easy to locate specific documents")
    print("✅ Scalable for additional forms and documents")
    print()
    
    print("=== Abbreviation Examples ===")
    print("• legal → Leg")
    print("• cover-letter → CL")
    print("• affidavit → Aff")
    print("• personal-statement → PS")
    print("• evidence-of-relationship → EOR")
    print("• medical-exam → ME")
    print("• bio-and-ids → Bio")
    print("• social-security → Soc-Sec")
    print("• application → Apps")
    print("• documents → Docs")

if __name__ == "__main__":
    generate_immigration_structure()
