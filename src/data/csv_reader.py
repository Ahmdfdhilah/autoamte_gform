"""
CSV data reader module for form data
"""

import logging
import os
from datetime import datetime
from typing import Dict, List
import pandas as pd
import pytz

logger = logging.getLogger(__name__)


class CSVDataReader:
    """CSV data reader for form data"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.df = None
        self.headers = []
    
    def load_data(self) -> bool:
        """Load data from CSV file"""
        try:
            file_ext = os.path.splitext(self.file_path)[1].lower()
            
            if file_ext == '.csv':
                self.df = pd.read_csv(self.file_path)
            elif file_ext in ['.xlsx', '.xls']:
                self.df = pd.read_excel(self.file_path)
            else:
                logger.error(f"Unsupported file format: {file_ext}")
                return False
            
            self.headers = list(self.df.columns)
            logger.info(f"✅ Loaded {len(self.df)} rows from {self.file_path}")
            return True
        except Exception as e:
            logger.error(f"Error loading file: {e}")
            return False
    
    def get_job_list(self, timezone_str: str = 'Asia/Jakarta') -> List[Dict]:
        """Convert DataFrame to job list"""
        if self.df is None:
            return []
        
        jobs = []
        timezone = pytz.timezone(timezone_str)
        
        for index, row in self.df.iterrows():
            # Form data
            form_data = {}
            for col in self.headers:
                if col.startswith('entry.'):
                    value = row[col]
                    if pd.notna(value):
                        form_data[col] = str(value)
            
            # Job info
            job = {
                'row_id': index + 1,
                'form_data': form_data,
                'priority': str(row.get('priority', 'normal')) if 'priority' in self.headers else 'normal',
                'eta': None
            }
            
            # Handle ETA
            if 'eta' in self.headers and pd.notna(row['eta']):
                try:
                    eta_str = str(row['eta'])
                    naive_dt = datetime.strptime(eta_str, '%Y-%m-%d %H:%M:%S')
                    eta_dt = timezone.localize(naive_dt)
                    job['eta'] = eta_dt
                except ValueError as e:
                    logger.warning(f"Row {job['row_id']}: Invalid ETA format: {eta_str}")
            
            jobs.append(job)
        
        return jobs