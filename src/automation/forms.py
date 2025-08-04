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
    
    def extract_form_info(self) -> tuple[List[str], Optional[str]]:
        """Extract entry IDs and action URL from Google Form"""
        try:
            response = self.session.get(self.form_url, timeout=self.request_config.get('timeout', 30))
            response.raise_for_status()
            
            # Extract entry IDs
            entry_pattern = r'entry\.(\d+)'
            entries = re.findall(entry_pattern, response.text)
            self.entry_fields = list(set(entries))
            
            # Generate action URL
            self.action_url = self.form_url.replace('/viewform', '/formResponse')
            
            return self.entry_fields, self.action_url
        except Exception as e:
            logger.error(f"Error extracting form info: {e}")
            return [], None
    
    def submit_form(self, form_data: Dict) -> bool:
        """Submit data to Google Form"""
        try:
            processed_data = {}
            for key, value in form_data.items():
                if isinstance(value, list):
                    processed_data[key] = ', '.join(str(item) for item in value)
                else:
                    processed_data[key] = str(value)
            
            response = self.session.post(
                self.action_url, 
                data=processed_data, 
                timeout=self.request_config.get('timeout', 30)
            )
            
            if response.status_code == 200:
                return True
            else:
                logger.error(f"HTTP Error: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Submit error: {e}")
            return False