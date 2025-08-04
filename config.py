"""
Configuration file untuk Google Forms Automation
Semua setting global ada di sini
"""

# ===== FORM CONFIGURATION =====
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdQ19RFNrDI5ptQAqMthhS3k_j8sCrl9Sqrp2cxzh5ssrQbhg/viewform"

# ===== HTTP REQUEST SETTINGS =====
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
    'auto_extract_fields': True,  # Otomatis extract field IDs dari form
    
    # ===== TIMEZONE SETTINGS =====
    'timezone': 'Asia/Jakarta',   # WIB timezone
    'eta_format': '%Y-%m-%d %H:%M:%S',  # Format ETA di CSV
    'show_timezone_info': True    # Show timezone info dalam logs
}

# ===== RABBITMQ CONFIGURATION =====
RABBITMQ_CONFIG = {
    'host': 'localhost',
    'port': 5672,
    'username': 'guest',
    'password': 'guest',
    'virtual_host': '/',
    'queue_name': 'google_forms_jobs'
}

# ===== CSV FORMAT CONFIGURATION =====
CSV_CONFIG = {
    'required_columns': ['entry.*'],  # Minimal harus ada kolom entry.*
    'optional_columns': ['eta', 'priority'],  # Kolom opsional
    'eta_column': 'eta',
    'priority_column': 'priority',
    'default_priority': 'normal'
}

# ===== WORKER CONFIGURATION =====
WORKER_CONFIG = {
    'max_workers': 3,
    'retry_attempts': 3,
    'retry_delay': 30,  # seconds
    'job_timeout': 300  # seconds
}