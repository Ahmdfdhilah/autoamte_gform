"""
Configuration file untuk Google Forms Automation
Semua setting global ada di sini
"""

# ===== FORM CONFIGURATION =====
FORM_URL = ''#===== JOB MAPPING CONFIGURATION =====
# Import job mappings for Google Form automation
try:
    from job_mappings import JOB_MAPPINGS, generate_prefilled_url, get_job_by_id, get_job_by_name
    JOB_MAPPING_ENABLED = True
except ImportError:
    JOB_MAPPINGS = {}
    JOB_MAPPING_ENABLED = False

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