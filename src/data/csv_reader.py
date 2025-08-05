"""
CSV data reader module for form data
"""

import logging
import os
from datetime import datetime
from typing import Dict, List
import pandas as pd
import pytz
from ..utils.url_parser import extract_entry_order_from_url

logger = logging.getLogger(__name__)


class CSVDataReader:
    """CSV data reader for form data"""
    
    def __init__(self, file_path: str, form_url: str = None):
        self.file_path = file_path
        self.form_url = form_url
        self.df = None
        self.headers = []
        self.entry_order = []  # Entry IDs in URL order
    
    def load_data(self) -> bool:
        """Load data from CSV file"""
        try:
            file_ext = os.path.splitext(self.file_path)[1].lower()
            
            # First extract entry order from URL if provided
            if self.form_url:
                self.entry_order = extract_entry_order_from_url(self.form_url)
                logger.info(f"📋 Entry order from URL: {len(self.entry_order)} entries")
            
            if file_ext == '.csv':
                # Check if CSV has headers by examining first line
                with open(self.file_path, 'r') as f:
                    first_line = f.readline().strip()
                
                # If first line starts with "entry." it's a header, otherwise it's data
                has_headers = first_line.startswith('entry.')
                
                if has_headers:
                    self.df = pd.read_csv(self.file_path)
                    self.headers = list(self.df.columns)
                    logger.info(f"✅ CSV with headers: {len(self.df)} rows")
                else:
                    # CSV without headers - trust URL order + eta, priority at end
                    if not self.entry_order:
                        logger.error("❌ CSV without headers requires form_url to determine column order")
                        return False
                    
                    # Create headers from URL order + eta, priority
                    expected_headers = self.entry_order + ['eta', 'priority']
                    
                    self.df = pd.read_csv(self.file_path, header=None)
                    
                    # Validate minimum columns (must have at least 3: some entries + eta + priority)
                    if len(self.df.columns) < 3:
                        logger.error(f"❌ CSV must have at least 3 columns, found {len(self.df.columns)}")
                        return False
                    
                    # Assign column names based on actual CSV columns
                    if len(self.df.columns) == len(expected_headers):
                        # Perfect match
                        self.df.columns = expected_headers
                        self.headers = expected_headers
                    elif len(self.df.columns) == len(self.entry_order) + 2:
                        # Has all entries + eta + priority
                        self.df.columns = expected_headers
                        self.headers = expected_headers
                    else:
                        # Partial entries + eta + priority (minimum case)
                        # Use first N-2 columns as entry fields, last 2 as eta, priority
                        entry_cols = len(self.df.columns) - 2
                        headers = self.entry_order[:entry_cols] + ['eta', 'priority']
                        self.df.columns = headers
                        self.headers = headers
                        logger.warning(f"⚠️ Using first {entry_cols} entries from URL order")
                    
                    logger.info(f"✅ CSV without headers: {len(self.df)} rows, {len(self.headers)} columns")
                    
            elif file_ext in ['.xlsx', '.xls']:
                self.df = pd.read_excel(self.file_path)
                self.headers = list(self.df.columns)
                logger.info(f"✅ Excel file: {len(self.df)} rows")
            else:
                logger.error(f"Unsupported file format: {file_ext}")
                return False
            
            logger.info(f"📊 Headers: {self.headers[:5]}..." if len(self.headers) > 5 else f"📊 Headers: {self.headers}")
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