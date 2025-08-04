#!/usr/bin/env python3
"""
Google Forms Automation - Main Script
Jalankan script ini untuk automasi Google Forms submission
"""

from google_forms_automation import GoogleFormAutomation
from config import FORM_URL, FORM_DATA, REQUEST_CONFIG, AUTOMATION_CONFIG

def main():
    """Main function untuk menjalankan automation"""
    
    print("🚀 Google Forms Automation (Class-Based)")
    print("=" * 50)
    
    # Initialize automation class
    automation = GoogleFormAutomation(
        form_url=FORM_URL,
        request_config=REQUEST_CONFIG
    )
    
    if AUTOMATION_CONFIG['verbose']:
        print(f"📋 Form URL: {FORM_URL}")
        print(f"🔧 Dry Run Mode: {AUTOMATION_CONFIG['dry_run']}")
        print("-" * 50)
    
    # Step 1: Extract form information
    if AUTOMATION_CONFIG['auto_extract_fields']:
        if AUTOMATION_CONFIG['verbose']:
            print("📊 Extracting form fields...")
        
        entries, action_url = automation.extract_form_info()
        
        if not entries:
            print("❌ Tidak dapat menemukan entry IDs dari form!")
            return False
        
        if AUTOMATION_CONFIG['verbose']:
            form_info = automation.get_form_info()
            print(f"✅ Ditemukan {form_info['total_fields']} field(s):")
            for i, entry in enumerate(entries, 1):
                print(f"   {i}. entry.{entry}")
            print(f"🎯 Action URL: {action_url}")
            print("-" * 50)
    
    # Step 2: Validate form data
    is_valid, errors = automation.validate_form_data(FORM_DATA)
    
    if not is_valid:
        print("❌ Form data tidak valid:")
        for error in errors:
            print(f"   - {error}")
        
        if not FORM_DATA or all(not key.startswith('entry.') for key in FORM_DATA.keys()):
            print("\n📝 Template FORM_DATA yang benar:")
            automation.print_form_template()
        
        return False
    
    if AUTOMATION_CONFIG['verbose']:
        print("✅ Form data valid")
        print("📝 Data yang akan disubmit:")
        for key, value in FORM_DATA.items():
            if isinstance(value, list):
                print(f"   {key}: {value} (checkbox)")
            else:
                print(f"   {key}: {value}")
        print("-" * 50)
    
    # Step 3: Submit form
    print("📤 Submitting form...")
    
    success = automation.submit_form(
        form_data=FORM_DATA,
        dry_run=AUTOMATION_CONFIG['dry_run']
    )
    
    # Step 4: Result
    if success:
        print("🎉 Automation berhasil!")
        if AUTOMATION_CONFIG['dry_run']:
            print("💡 Untuk submit real, set 'dry_run': False di config.py")
    else:
        print("💥 Automation gagal!")
        return False
    
    return True

def submit_multiple_example():
    """
    Contoh untuk submit multiple data sekaligus
    Uncomment dan edit sesuai kebutuhan
    """
    
    # Contoh multiple data
    multiple_data = [
        {'entry.625591749': 'Data 1'},
        {'entry.625591749': 'Data 2'},
        {'entry.625591749': 'Data 3'},
    ]
    
    automation = GoogleFormAutomation(FORM_URL, REQUEST_CONFIG)
    automation.extract_form_info()
    
    results = automation.submit_multiple(
        form_data_list=multiple_data,
        delay=AUTOMATION_CONFIG['delay_between_submits'],
        dry_run=AUTOMATION_CONFIG['dry_run']
    )
    
    success_count = sum(results)
    print(f"✅ {success_count}/{len(results)} submissions berhasil")

if __name__ == "__main__":
    try:
        main()
        
        # Uncomment untuk test multiple submissions:
        # submit_multiple_example()
        
    except KeyboardInterrupt:
        print("\n⚠️  Automation dibatalkan oleh user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()