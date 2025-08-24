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
                # Excel files have NO HEADERS - all rows are data
                # Trust URL order for column mapping (like selenium_debug.py does)
                if not self.entry_order:
                    logger.error("❌ Excel without headers requires form_url to determine column order")
                    return False
                
                # Read Excel without headers (header=None)
                self.df = pd.read_excel(self.file_path, header=None)
                
                # Map columns to entry order (skip last 2 columns which are eta, priority)
                num_cols = len(self.df.columns)
                if num_cols >= 3:  # At least some data + eta + priority
                    entry_cols = num_cols - 2  # Last 2 are eta, priority
                    
                    # Check if we have enough entry fields from URL
                    if entry_cols > len(self.entry_order):
                        logger.warning(f"⚠️ Excel has {entry_cols} data columns but URL only has {len(self.entry_order)} entry fields")
                        logger.info(f"🔧 Using all {len(self.entry_order)} available entries + eta,priority")
                        # Use all available entries + fill remaining with generic names + eta, priority
                        available_entries = self.entry_order
                        remaining_cols = entry_cols - len(self.entry_order)
                        generic_entries = [f'extra_col_{i+1}' for i in range(remaining_cols)]
                        headers = available_entries + generic_entries + ['eta', 'priority']
                        # Truncate DataFrame to match available entries + eta,priority
                        self.df = self.df.iloc[:, :(len(self.entry_order) + 2)]
                        headers = self.entry_order + ['eta', 'priority']
                    else:
                        # Use first N-2 entries from URL order
                        headers = self.entry_order[:entry_cols] + ['eta', 'priority']
                    
                    self.df.columns = headers
                    self.headers = headers
                    logger.info(f"✅ Excel file (no headers): {len(self.df)} rows, mapped to {len(headers)-2} entries + eta,priority")
                else:
                    # Fallback: use all columns as entries
                    headers = self.entry_order[:num_cols]
                    self.df.columns = headers
                    self.headers = headers
                    logger.info(f"✅ Excel file (no headers): {len(self.df)} rows, mapped to {num_cols} entries")
                
                logger.info(f"📊 Excel column mapping: {len(self.headers)} columns mapped to URL entry order")
            else:
                logger.error(f"Unsupported file format: {file_ext}")
                return False
            
            logger.info(f"📊 Headers: {self.headers[:5]}..." if len(self.headers) > 5 else f"📊 Headers: {self.headers}")
            return True
        except Exception as e:
            logger.error(f"Error loading file: {e}")
            return False
    
    def get_job_list(self, timezone_str: str = 'Asia/Jakarta') -> List[Dict]:
        """Convert DataFrame to job list following selenium_debug.py logic"""
        if self.df is None:
            return []
        
        jobs = []
        timezone = pytz.timezone(timezone_str)
        
        # Process each row like selenium_debug.py does
        for index, row in self.df.iterrows():
            # Convert row to list (like selenium_debug.py: first_row = df.iloc[0].tolist())
            row_data = row.tolist()
            
            # Map Excel data to entry fields with cleaning (exactly like selenium_debug.py)
            form_data = {}
            for i, entry_key in enumerate(self.entry_order):
                if i < len(row_data) - 2:  # Skip eta and priority columns (last 2)
                    value = row_data[i]
                    if pd.notna(value) and str(value).strip():
                        # Clean value: normalize multiple spaces to single space and strip
                        cleaned_value = ' '.join(str(value).strip().split())
                        
                        # Remove .0 from float numbers (e.g., 9.0 -> 9, but keep 9.5 as 9.5)
                        try:
                            # Check if it's a number that ends with .0
                            if '.' in cleaned_value and cleaned_value.replace('.', '').replace('-', '').isdigit():
                                float_val = float(cleaned_value)
                                if float_val.is_integer():
                                    cleaned_value = str(int(float_val))
                        except ValueError:
                            # Not a number, keep as is
                            pass
                        
                        form_data[entry_key] = cleaned_value
            
            # Get eta and priority from last 2 columns
            eta_value = None
            priority_value = 'normal'
            
            if len(row_data) >= 2:
                # Second to last column is eta
                if len(row_data) >= 2 and pd.notna(row_data[-2]):
                    eta_value = row_data[-2]
                
                # Last column is priority
                if len(row_data) >= 1 and pd.notna(row_data[-1]):
                    priority_value = str(row_data[-1])
            
            # Job info
            job = {
                'row_id': index + 1,
                'form_data': form_data,
                'priority': priority_value,
                'eta': None
            }
            
            # Handle ETA
            if eta_value is not None:
                try:
                    eta_str = str(eta_value).strip()
                    
                    # Skip numeric-only values that aren't timestamps
                    if eta_str.isdigit() and len(eta_str) < 8:
                        logger.debug(f"Row {job['row_id']}: Skipping numeric ETA value: {eta_str}")
                        job['eta'] = None
                    elif eta_str.lower() in ['', 'nan', 'none', 'null']:
                        # Skip empty/null values
                        job['eta'] = None
                    else:
                        # Try different datetime formats (all will be interpreted as WIB timezone)
                        formats = [
                            '%Y-%m-%d %H:%M:%S',    # 2025-08-23 17:40:00
                            '%Y-%m-%d %H:%M',       # 2025-08-23 17:40
                            '%Y-%m-%d',             # 2025-08-23
                            '%d/%m/%Y %H:%M:%S',    # 23/08/2025 17:40:00
                            '%d/%m/%Y %H:%M',       # 23/08/2025 17:40
                            '%d/%m/%Y',             # 23/08/2025
                            '%m/%d/%Y %H:%M:%S',    # 8/23/2025 17:40:00 (American format)
                            '%m/%d/%Y %H:%M',       # 8/23/2025 17:40 (American format) 
                            '%m/%d/%Y',             # 8/23/2025 (American format)
                            '%d-%m-%Y %H:%M:%S',    # 23-08-2025 17:40:00
                            '%d-%m-%Y %H:%M',       # 23-08-2025 17:40
                            '%d-%m-%Y'              # 23-08-2025
                        ]
                        
                        for fmt in formats:
                            try:
                                naive_dt = datetime.strptime(eta_str, fmt)
                                # Always localize to WIB timezone (Asia/Jakarta)
                                eta_dt = timezone.localize(naive_dt)
                                job['eta'] = eta_dt
                                logger.info(f"Row {job['row_id']}: Parsed ETA as WIB: {eta_dt.strftime('%Y-%m-%d %H:%M:%S %Z')} (format: {fmt})")
                                break
                            except ValueError:
                                continue
                        
                        if job['eta'] is None:
                            logger.debug(f"Row {job['row_id']}: Could not parse ETA format: '{eta_str}' - using immediate execution")
                except Exception as e:
                    logger.debug(f"Row {job['row_id']}: ETA processing error: {e}")
            
            jobs.append(job)
            
            logger.debug(f"Row {index + 1}: Mapped {len(form_data)} fields from Excel data")
        
        logger.info(f"📊 Created {len(jobs)} jobs from Excel data (selenium_debug.py logic)")
        return jobs