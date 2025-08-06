# Google Forms Automation - Usage Guide

## Overview
Sistem otomasi pengisian Google Forms dengan support headless Selenium dan queue processing menggunakan RabbitMQ.

## Features
- ✅ Support file CSV dan XLSX
- ✅ Headless Selenium automation 
- ✅ Queue-based processing dengan RabbitMQ
- ✅ Advanced field type detection dan mapping
- ✅ Multi-section form navigation
- ✅ Scheduling dengan ETA support
- ✅ Error handling dan retry mechanism

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Prepare Data File

#### Format CSV (dengan headers)
```csv
entry.574418038,entry.491424067,entry.1076213498,eta,priority
Ya,Tidak,5,2024-01-15 10:00:00,high
Tidak,Ya,3,2024-01-15 11:00:00,normal
```

#### Format XLSX
- Gunakan header row di baris pertama
- Kolom entry.* untuk data form 
- Kolom 'eta' untuk scheduling (opsional)
- Kolom 'priority' untuk prioritas (opsional)

### 3. Run Automation

#### Batch Mode (Process semua data langsung)
```bash
python main.py batch --file data.csv
python main.py batch --file data.xlsx
```

#### Scheduled Mode (Process sesuai ETA)
```bash
python main.py scheduled --file data.csv
python main.py scheduled --file data.xlsx
```

#### Worker Mode (Queue processing)
```bash
python main.py worker
```

## File Format Support

### CSV Files
- **Dengan headers**: Otomatis detect kolom dari header row
- **Tanpa headers**: Menggunakan urutan dari form URL + eta,priority di akhir

### XLSX/XLS Files  
- **Semua format Excel**: Otomatis detect headers dari row pertama
- **Support multiple sheets**: Akan menggunakan sheet pertama

## Advanced Usage

### Debug Mode
```bash
# Untuk melihat detail proses
python main.py batch --file data.xlsx --verbose
```

### Test Form Filling
```bash
# Run selenium debug dengan browser visible
python selenium_debug.py
```

### Data Processing
```bash
# Clean dan transform data sebelum automation
python fix_dataset.py
```

## File Examples

### Raw Data (datas.xlsx)
File Excel dengan data mentah dari survey/form responses.

### Processed Data (file_finale.xlsx)  
File hasil clean dari fix_dataset.py dengan nilai sudah di-mapping ke format yang diperlukan.

### Test Data (test_data.csv)
File sample untuk testing automation.

## Configuration

Edit `config.py` untuk mengatur:
- `FORM_URL`: URL Google Form target
- `REQUEST_CONFIG`: HTTP settings
- `AUTOMATION_CONFIG`: Timing dan behavior
- `RABBITMQ_CONFIG`: Queue settings

## Troubleshooting

### Common Issues

1. **File not found**
   - Pastikan path file benar
   - Support: .csv, .xlsx, .xls

2. **Form tidak submit**
   - Cek apakah form masih accepting responses
   - Periksa field mapping di selenium_debug.py

3. **RabbitMQ connection error**
   - Pastikan RabbitMQ server running
   - Check RABBITMQ_CONFIG di config.py

4. **Excel file error**
   - Pastikan tidak ada protected sheets
   - Close file Excel jika sedang dibuka

### Debug Tools

1. **selenium_debug.py**: Visual debugging dengan browser
2. **analyze_fields.py**: Analisis struktur form fields
3. **fix_dataset.py**: Transform data format

## System Architecture

```
main.py
├── CSV/XLSX Reader (src/data/csv_reader.py)
├── Form Automation (src/automation/forms.py) 
│   ├── Headless Selenium
│   ├── Field Type Analysis
│   └── Multi-section Navigation  
├── Queue System (src/messaging/rabbitmq.py)
├── Scheduler (src/scheduling/scheduler.py)
└── Core System (src/core/system.py)
```

## Performance Tips

1. **Batch Mode**: Paling cepat untuk dataset kecil-menengah
2. **Scheduled Mode**: Gunakan untuk rate limiting
3. **Worker Mode**: Optimal untuk processing continuous
4. **Headless**: 2-3x lebih cepat dari browser visible

## Data Flow

1. **Load**: CSV/XLSX → pandas DataFrame
2. **Parse**: Extract entry fields dari form URL  
3. **Map**: Data mapping dengan field type awareness
4. **Generate**: Prefilled URLs dengan cleaned data
5. **Submit**: Headless Selenium navigation
6. **Verify**: Success/failure detection