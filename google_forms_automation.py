"""
Google Forms Automation Class
Class-based implementation untuk automasi Google Forms
"""

import requests
from bs4 import BeautifulSoup
import re
import time
from typing import Dict, List, Union, Tuple, Optional

class GoogleFormAutomation:
    """
    Class untuk automasi Google Forms submission
    """
    
    def __init__(self, form_url: str, request_config: Dict = None):
        """
        Initialize Google Form Automation
        
        Args:
            form_url: URL Google Form
            request_config: Configuration untuk HTTP requests
        """
        self.form_url = form_url
        self.action_url = None
        self.entry_fields = []
        
        # Default request config
        self.request_config = request_config or {
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            'timeout': 30,
            'retries': 3
        }
        
        self.session = requests.Session()
        self.session.headers.update(self.request_config['headers'])
    
    def extract_form_info(self) -> Tuple[List[str], Optional[str]]:
        """
        Extract entry IDs dan action URL dari Google Form
        
        Returns:
            Tuple berisi (entry_fields, action_url)
        """
        try:
            response = self.session.get(self.form_url, timeout=self.request_config['timeout'])
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract entry IDs
            entry_pattern = r'entry\.(\d+)'
            entries = re.findall(entry_pattern, response.text)
            self.entry_fields = list(set(entries))
            
            # Generate action URL
            self.action_url = self.form_url.replace('/viewform', '/formResponse')
            
            return self.entry_fields, self.action_url
            
        except requests.RequestException as e:
            print(f"❌ Error extracting form info: {e}")
            return [], None
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return [], None
    
    def process_form_data(self, form_data: Dict[str, Union[str, List[str]]]) -> Dict[str, str]:
        """
        Process form data untuk handle berbagai tipe field
        
        Args:
            form_data: Dictionary berisi entry fields dan values
            
        Returns:
            Processed data untuk dikirim ke Google Forms
        """
        processed_data = {}
        
        for key, value in form_data.items():
            if isinstance(value, list):
                # Handle checkbox (multiple values)
                # Google Forms expects multiple entries dengan key yang sama
                # Untuk simplicity, kita gabung dengan koma
                processed_data[key] = ', '.join(str(item) for item in value)
            else:
                # Handle single value
                processed_data[key] = str(value)
        
        return processed_data
    
    def submit_form(self, form_data: Dict[str, Union[str, List[str]]], dry_run: bool = False) -> bool:
        """
        Submit data ke Google Form
        
        Args:
            form_data: Data yang akan disubmit
            dry_run: Jika True, hanya simulate tanpa submit real
            
        Returns:
            True jika berhasil, False jika gagal
        """
        if not self.action_url:
            print("❌ Action URL belum di-extract. Jalankan extract_form_info() terlebih dahulu.")
            return False
        
        # Process form data
        processed_data = self.process_form_data(form_data)
        
        if dry_run:
            print("🧪 DRY RUN MODE - Data yang akan dikirim:")
            for key, value in processed_data.items():
                print(f"   {key}: {value}")
            print("✅ Dry run selesai (tidak ada data yang dikirim)")
            return True
        
        # Submit dengan retry mechanism
        for attempt in range(self.request_config['retries']):
            try:
                response = self.session.post(
                    self.action_url, 
                    data=processed_data, 
                    timeout=self.request_config['timeout']
                )
                
                if response.status_code == 200:
                    print("✅ Form berhasil disubmit!")
                    return True
                else:
                    print(f"❌ Error: HTTP {response.status_code}")
                    
            except requests.RequestException as e:
                print(f"❌ Attempt {attempt + 1} failed: {e}")
                if attempt < self.request_config['retries'] - 1:
                    time.sleep(1)  # Wait before retry
                    
        print(f"❌ Failed after {self.request_config['retries']} attempts")
        return False
    
    def submit_multiple(self, form_data_list: List[Dict], delay: float = 1.0, dry_run: bool = False) -> List[bool]:
        """
        Submit multiple form data dengan delay
        
        Args:
            form_data_list: List of form data dictionaries
            delay: Delay antar submission (seconds)
            dry_run: Dry run mode
            
        Returns:
            List of success status untuk setiap submission
        """
        results = []
        
        for i, form_data in enumerate(form_data_list, 1):
            print(f"📤 Submitting form {i}/{len(form_data_list)}...")
            
            success = self.submit_form(form_data, dry_run)
            results.append(success)
            
            # Delay antar submission (kecuali yang terakhir)
            if i < len(form_data_list) and delay > 0:
                print(f"⏳ Waiting {delay}s before next submission...")
                time.sleep(delay)
        
        return results
    
    def validate_form_data(self, form_data: Dict) -> Tuple[bool, List[str]]:
        """
        Validate form data sebelum submit
        
        Args:
            form_data: Data yang akan divalidasi
            
        Returns:
            Tuple (is_valid, error_messages)
        """
        errors = []
        
        if not form_data:
            errors.append("Form data kosong")
        
        # Check if entry fields valid
        for key in form_data.keys():
            if not key.startswith('entry.'):
                errors.append(f"Invalid entry field: {key}")
        
        # Check if form info sudah di-extract
        if not self.entry_fields:
            errors.append("Form fields belum di-extract. Jalankan extract_form_info() dulu.")
        
        return len(errors) == 0, errors
    
    def get_form_info(self) -> Dict:
        """
        Get informasi form yang sudah di-extract
        
        Returns:
            Dictionary berisi informasi form
        """
        return {
            'form_url': self.form_url,
            'action_url': self.action_url,
            'entry_fields': self.entry_fields,
            'total_fields': len(self.entry_fields)
        }
    
    def print_form_template(self):
        """
        Print template FORM_DATA berdasarkan entry fields yang ditemukan
        """
        if not self.entry_fields:
            print("❌ Extract form info terlebih dahulu!")
            return
        
        print("📝 Template FORM_DATA:")
        print("FORM_DATA = {")
        for entry in self.entry_fields:
            print(f"    'entry.{entry}': 'Your Value Here',")
        print("}")