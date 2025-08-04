"""
Configuration file untuk Google Forms Automation
Edit file ini untuk mengkonfigurasi form dan data yang akan disubmit
"""

# ===== FORM CONFIGURATION =====
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdQ19RFNrDI5ptQAqMthhS3k_j8sCrl9Sqrp2cxzh5ssrQbhg/viewform"

# ===== FORM DATA =====
FORM_DATA = {
    # Text Field
    'entry.625591749': 'Option 1',
    
    # Contoh field lainnya (uncomment sesuai kebutuhan):
    # 'entry.123456': 'Nama Anda',                    # Text
    # 'entry.789012': 'email@example.com',            # Email
    # 'entry.345678': 'Pilihan A',                    # Multiple Choice
    # 'entry.567890': ['Option 1', 'Option 2'],       # Checkbox
    # 'entry.111222': 'Jakarta',                      # Dropdown
    # 'entry.333444': '4',                            # Linear Scale
    # 'entry.555666': '2024-01-15',                   # Date
    # 'entry.777888': '14:30',                        # Time
    # 'entry.999000': '100',                          # Number
}

# ===== REQUEST SETTINGS =====
REQUEST_CONFIG = {
    'headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    },
    'timeout': 30,  # seconds
    'retries': 3
}

# ===== AUTOMATION SETTINGS =====
AUTOMATION_CONFIG = {
    'verbose': True,          # Show detailed output
    'dry_run': False,        # Set True untuk test tanpa submit
    'delay_between_submits': 1,  # seconds (jika submit multiple)
    'auto_extract_fields': True  # Otomatis extract field IDs dari form
}