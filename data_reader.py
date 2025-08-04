"""
CSV/Excel Data Reader untuk Google Forms Automation
Membaca data dari file CSV/Excel dan convert ke format yang sesuai
"""

import pandas as pd
import os
from typing import List, Dict, Optional, Union
from datetime import datetime, timedelta
import json

class DataReader:
    """
    Class untuk membaca data dari CSV/Excel file
    """
    
    def __init__(self, file_path: str):
        """
        Initialize data reader
        
        Args:
            file_path: Path ke file CSV/Excel
        """
        self.file_path = file_path
        self.df = None
        self.headers = []
        
    def load_data(self) -> bool:
        """
        Load data dari file CSV/Excel
        
        Returns:
            True jika berhasil load, False jika gagal
        """
        try:
            file_ext = os.path.splitext(self.file_path)[1].lower()
            
            if file_ext == '.csv':
                self.df = pd.read_csv(self.file_path)
            elif file_ext in ['.xlsx', '.xls']:
                self.df = pd.read_excel(self.file_path)
            else:
                print(f"❌ Unsupported file format: {file_ext}")
                return False
            
            # Get headers (row 1)
            self.headers = list(self.df.columns)
            
            print(f"✅ Loaded {len(self.df)} rows from {self.file_path}")
            print(f"📋 Headers: {self.headers}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error loading file: {e}")
            return False
    
    def validate_headers(self, required_columns: List[str] = None) -> bool:
        """
        Validate headers dari file
        
        Args:
            required_columns: List kolom yang wajib ada
            
        Returns:
            True jika valid, False jika tidak
        """
        if self.df is None:
            print("❌ Data belum di-load!")
            return False
        
        # Check for entry columns (harus ada minimal 1)
        entry_columns = [col for col in self.headers if col.startswith('entry.')]
        
        if not entry_columns:
            print("❌ Tidak ada kolom entry.* ditemukan!")
            print("💡 Header file harus berisi kolom seperti: entry.123456789")
            return False
        
        print(f"✅ Ditemukan {len(entry_columns)} entry columns:")
        for col in entry_columns:
            print(f"   - {col}")
        
        # Check required columns
        if required_columns:
            missing_cols = [col for col in required_columns if col not in self.headers]
            if missing_cols:
                print(f"❌ Missing required columns: {missing_cols}")
                return False
        
        return True
    
    def get_form_data_list(self, eta_column: str = 'eta', priority_column: str = 'priority') -> List[Dict]:
        """
        Convert DataFrame ke list of form data dengan scheduling info
        
        Args:
            eta_column: Nama kolom untuk ETA (estimated time of arrival)
            priority_column: Nama kolom untuk priority
            
        Returns:
            List of dictionaries berisi form data dan scheduling info
        """
        if self.df is None:
            print("❌ Data belum di-load!")
            return []
        
        result = []
        
        for index, row in self.df.iterrows():
            # Form data (hanya kolom entry.*)
            form_data = {}
            for col in self.headers:
                if col.startswith('entry.'):
                    value = row[col]
                    # Handle NaN values
                    if pd.isna(value):
                        continue
                    
                    # Handle different data types
                    if isinstance(value, (int, float)):
                        form_data[col] = str(value)
                    else:
                        form_data[col] = str(value)
            
            # Scheduling info
            scheduling_info = {
                'row_id': index + 1,  # 1-based row ID
                'form_data': form_data
            }
            
            # ETA (estimated time of arrival)
            if eta_column in self.headers and not pd.isna(row[eta_column]):
                scheduling_info['eta'] = str(row[eta_column])
            else:
                scheduling_info['eta'] = None
            
            # Priority
            if priority_column in self.headers and not pd.isna(row[priority_column]):
                scheduling_info['priority'] = str(row[priority_column])
            else:
                scheduling_info['priority'] = 'normal'
            
            # Additional metadata
            scheduling_info['created_at'] = datetime.now().isoformat()
            scheduling_info['status'] = 'pending'
            
            result.append(scheduling_info)
        
        print(f"✅ Converted {len(result)} rows to form data")
        return result
    
    def get_summary(self) -> Dict:
        """
        Get summary informasi dari data
        
        Returns:
            Dictionary berisi summary info
        """
        if self.df is None:
            return {}
        
        entry_columns = [col for col in self.headers if col.startswith('entry.')]
        
        return {
            'file_path': self.file_path,
            'total_rows': len(self.df),
            'total_columns': len(self.headers),
            'entry_columns': entry_columns,
            'entry_columns_count': len(entry_columns),
            'headers': self.headers,
            'has_eta': 'eta' in self.headers,
            'has_priority': 'priority' in self.headers
        }
    
    def preview_data(self, n: int = 5) -> None:
        """
        Preview beberapa baris pertama data
        
        Args:
            n: Jumlah baris yang akan ditampilkan
        """
        if self.df is None:
            print("❌ Data belum di-load!")
            return
        
        print(f"📊 Preview {n} baris pertama:")
        print("-" * 50)
        
        # Show only entry columns for preview
        entry_columns = [col for col in self.headers if col.startswith('entry.')]
        other_columns = ['eta', 'priority'] if 'eta' in self.headers or 'priority' in self.headers else []
        
        preview_columns = entry_columns + other_columns
        available_columns = [col for col in preview_columns if col in self.headers]
        
        if available_columns:
            print(self.df[available_columns].head(n).to_string(index=True))
        else:
            print(self.df.head(n).to_string(index=True))
        
        print("-" * 50)

def create_sample_csv(file_path: str = "sample_data.csv") -> str:
    """
    Create sample CSV file untuk testing
    
    Args:
        file_path: Path file yang akan dibuat
        
    Returns:
        Path file yang dibuat
    """
    import csv
    
    # Sample data
    data = [
        # Headers
        ['entry.625591749', 'entry.123456789', 'eta', 'priority'],
        # Data rows
        ['Option 1', 'Test User 1', '2024-08-05 10:00:00', 'high'],
        ['Option 2', 'Test User 2', '2024-08-05 10:05:00', 'normal'],
        ['Option 3', 'Test User 3', '2024-08-05 10:10:00', 'low'],
        ['Option 1', 'Test User 4', '2024-08-05 10:15:00', 'high'],
        ['Option 2', 'Test User 5', '2024-08-05 10:20:00', 'normal'],
    ]
    
    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(data)
    
    print(f"✅ Sample CSV created: {file_path}")
    return file_path

if __name__ == "__main__":
    # Create sample file
    sample_file = create_sample_csv()
    
    # Test data reader
    reader = DataReader(sample_file)
    
    if reader.load_data():
        reader.validate_headers()
        reader.preview_data()
        
        # Get form data list
        form_data_list = reader.get_form_data_list()
        
        # Show summary
        summary = reader.get_summary()
        print(f"\n📈 Summary: {json.dumps(summary, indent=2)}")
        
        # Show first form data
        if form_data_list:
            print(f"\n📝 First form data:")
            print(json.dumps(form_data_list[0], indent=2))