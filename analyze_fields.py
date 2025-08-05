#!/usr/bin/env python3
"""
Script untuk menganalisis field types dari URL config dan menyimpannya
"""

from config import FORM_URL
from src.utils.field_analyzer import analyze_field_types_from_url, save_field_types_to_config

def main():
    print("🔍 Analyzing field types from FORM_URL...")
    
    # Analyze field types from URL
    field_types = analyze_field_types_from_url(FORM_URL)
    
    print(f"📊 Found {len(field_types)} fields:")
    
    # Show analysis summary
    type_counts = {}
    for entry_id, info in field_types.items():
        field_type = info['type']
        type_counts[field_type] = type_counts.get(field_type, 0) + 1
    
    for field_type, count in type_counts.items():
        print(f"  - {field_type}: {count} fields")
    
    # Show some examples
    print("\n📋 Examples by type:")
    for field_type in type_counts.keys():
        examples = [(k, v) for k, v in field_types.items() if v['type'] == field_type][:3]
        print(f"\n{field_type.upper()}:")
        for entry_id, info in examples:
            if info['multiple_values']:
                print(f"  {entry_id}: {info['sample_values']} (multiple)")
            else:
                print(f"  {entry_id}: {info['sample_values']}")
    
    # Save to config file
    print(f"\n💾 Saving field types configuration...")
    if save_field_types_to_config(field_types):
        print("✅ Field types saved to field_types.py")
    else:
        print("❌ Failed to save field types")
    
    return field_types

if __name__ == "__main__":
    main()