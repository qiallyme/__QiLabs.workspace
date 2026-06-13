#!/usr/bin/env python3
"""
Test script to verify abbreviation system is working correctly
"""

from slugs_mapping import SlugMapper

def test_abbreviations():
    mapper = SlugMapper()
    
    print("=== Testing Abbreviation System ===")
    
    # Test basic abbreviations
    print("Basic Abbreviations:")
    print(f"  legal -> {mapper.get_abbreviation('entities', 'legal')}")
    print(f"  cover-letter -> {mapper.get_abbreviation('topics', 'cover-letter')}")
    print(f"  affidavit -> {mapper.get_abbreviation('topics', 'affidavit')}")
    print(f"  personal-statement -> {mapper.get_abbreviation('topics', 'personal-statement')}")
    print(f"  evidence-of-relationship -> {mapper.get_abbreviation('topics', 'evidence-of-relationship')}")
    print(f"  medical-exam -> {mapper.get_abbreviation('topics', 'medical-exam')}")
    print(f"  bio-and-ids -> {mapper.get_abbreviation('topics', 'bio-and-ids')}")
    print(f"  social-security -> {mapper.get_abbreviation('topics', 'social-security')}")
    print(f"  application -> {mapper.get_abbreviation('topics', 'application')}")
    print(f"  documents -> {mapper.get_abbreviation('topics', 'documents')}")
    
    print("\n=== Immigration File Examples with Abbreviations ===")
    
    # I-589 examples
    print("I-589 (Asylum):")
    print(f"  Cover Letter: {mapper.generate_immigration_filename('qia', 'i589', 'cover-letter')}")
    print(f"  Affidavit: {mapper.generate_immigration_filename('qia', 'i589', 'affidavit')}")
    print(f"  Form: {mapper.generate_immigration_filename('qia', 'i589', 'form')}")
    
    # I-360 examples
    print("\nI-360 (Special Immigrant):")
    print(f"  Cover Letter: {mapper.generate_immigration_filename('qia', 'i360', 'cover-letter')}")
    print(f"  Personal Statement: {mapper.generate_immigration_filename('qia', 'i360', 'personal-statement')}")
    
    # I-130 examples
    print("\nI-130 (Family Sponsorship):")
    print(f"  Cover Letter: {mapper.generate_immigration_filename('qia', 'i130', 'cover-letter')}")
    print(f"  Evidence of Relationship: {mapper.generate_immigration_filename('qia', 'i130', 'evidence-of-relationship')}")
    
    # I-765 examples
    print("\nI-765 (Employment Authorization):")
    print(f"  Cover Letter: {mapper.generate_immigration_filename('qia', 'i765', 'cover-letter')}")
    print(f"  Form: {mapper.generate_immigration_filename('qia', 'i765', 'form')}")
    
    # I-485 examples
    print("\nI-485 (Adjustment of Status):")
    print(f"  Cover Letter: {mapper.generate_immigration_filename('qia', 'i485', 'cover-letter')}")
    print(f"  Medical Exam: {mapper.generate_immigration_filename('qia', 'i485', 'medical-exam')}")
    
    # Drafts and Strategy
    print("\nDrafts and Strategy:")
    print(f"  Strategy Plan: {mapper.generate_filename('qia', 'legal', 'strategy', version='v01', status='final')}")
    print(f"  Timeline: {mapper.generate_filename('qia', 'legal', 'timeline', version='v01', status='final')}")
    print(f"  Draft Affidavit: {mapper.generate_filename('qia', 'legal', 'drafts', detail='affidavit', version='v01', status='draft')}")
    
    # Bio and IDs
    print("\nBio and IDs:")
    print(f"  Passport Copy: {mapper.generate_filename('qia', 'legal', 'bio-and-ids', detail='passport-copy')}")
    print(f"  Birth Certificate: {mapper.generate_filename('qia', 'legal', 'bio-and-ids', detail='birth-certificate')}")
    
    # Employment
    print("\nEmployment:")
    print(f"  Offer Letter: {mapper.generate_filename('qia', 'legal', 'employment', detail='offer-letter')}")
    print(f"  Pay Stubs: {mapper.generate_filename('qia', 'legal', 'employment', detail='pay-stubs')}")
    
    # Financial
    print("\nFinancial:")
    print(f"  Tax Returns: {mapper.generate_filename('qia', 'legal', 'financial', detail='tax-returns')}")
    print(f"  Bank Statements: {mapper.generate_filename('qia', 'legal', 'financial', detail='bank-statements')}")

if __name__ == "__main__":
    test_abbreviations()
