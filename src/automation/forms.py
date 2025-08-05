"""
Google Forms automation module
"""

import logging
import re
from typing import Dict, List, Optional
import requests

logger = logging.getLogger(__name__)


class GoogleFormAutomation:
    """Google Forms automation class"""
    
    def __init__(self, form_url: str, request_config: Dict = None):
        self.form_url = form_url
        self.action_url = None
        self.entry_fields = []
        self.request_config = request_config or {}
        self.session = requests.Session()
        if self.request_config.get('headers'):
            self.session.headers.update(self.request_config['headers'])
    
    def extract_form_info(self, csv_headers: List[str] = None) -> tuple[List[str], Optional[str]]:
        """Extract entry IDs from CSV headers or form HTML"""
        try:
            # If we have CSV headers, use them directly
            if csv_headers:
                entry_fields = []
                for header in csv_headers:
                    if header.startswith('entry.'):
                        entry_id = header.replace('entry.', '')
                        entry_fields.append(entry_id)
                
                if entry_fields:
                    self.entry_fields = entry_fields
                    # Generate CLEAN action URL (remove prefilled parameters)
                    base_url = self.form_url.split('?')[0]  # Remove all URL parameters
                    self.action_url = base_url.replace('/viewform', '/formResponse')
                    logger.info(f"Using CSV headers: {len(entry_fields)} entry fields found")
                    logger.info(f"Clean action URL: {self.action_url}")
                    return self.entry_fields, self.action_url
            
            # Fallback to HTML extraction if no CSV headers provided
            response = self.session.get(self.form_url, timeout=self.request_config.get('timeout', 30))
            response.raise_for_status()
            
            # Extract entry IDs
            entry_pattern = r'entry\.(\d+)'
            entries = re.findall(entry_pattern, response.text)
            self.entry_fields = list(set(entries))
            
            # Generate CLEAN action URL (remove prefilled parameters)
            base_url = self.form_url.split('?')[0]  # Remove all URL parameters
            self.action_url = base_url.replace('/viewform', '/formResponse')
            
            return self.entry_fields, self.action_url
        except Exception as e:
            logger.error(f"Error extracting form info: {e}")
            return [], None
    
    def submit_form(self, form_data: Dict) -> bool:
        """Submit data to Google Form"""
        try:
            # Process form data
            processed_data = {}
            for key, value in form_data.items():
                if value is None or value == '':
                    continue  # Skip empty values
                    
                if isinstance(value, list):
                    # Handle multiple selections
                    for v in value:
                        if str(v).strip():  # Only non-empty values
                            processed_data[key] = str(v)
                else:
                    processed_data[key] = str(value)
            
            # Ensure proper headers for form submission
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            logger.info(f"Submitting to: {self.action_url}")
            logger.info(f"Data fields: {len(processed_data)}")
            logger.debug(f"Form data: {processed_data}")
            
            response = self.session.post(
                self.action_url,
                data=processed_data,
                headers=headers,
                timeout=self.request_config.get('timeout', 30),
                allow_redirects=True
            )
            
            logger.info(f"Response status: {response.status_code}")
            logger.debug(f"Response URL: {response.url}")
            
            # Google Forms usually returns 200 and redirects to a thank you page
            if response.status_code == 200:
                # Check if we got redirected to the confirmation page
                if 'formResponse' in response.url or 'closedform' in response.url:
                    logger.info("✅ Form submitted successfully")
                    return True
                else:
                    logger.warning("Form submitted but no confirmation redirect detected")
                    return True
            else:
                logger.error(f"HTTP Error: {response.status_code}")
                logger.error(f"Response content: {response.text[:500]}")
                return False
                
        except Exception as e:
            logger.error(f"Submit error: {e}")
            return False