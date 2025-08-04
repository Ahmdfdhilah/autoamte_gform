# Google Forms Automation System

Sistem automasi Google Forms yang canggih dengan support CSV/Excel, cron jobs, dan RabbitMQ untuk reliability.

## 🚀 Features

- ✅ **CSV/Excel Support** - Load data dari file CSV atau Excel
- ✅ **Multiple Field Types** - Text, multiple choice, checkbox, dropdown, dll
- ✅ **Cron Jobs & Scheduling** - Schedule berdasarkan ETA per row
- ✅ **RabbitMQ Queue** - Message queue untuk reliability
- ✅ **Worker Pool** - Multiple workers untuk concurrent processing
- ✅ **Retry Mechanism** - Auto retry untuk failed jobs
- ✅ **Class-based OOP** - Clean, maintainable code
- ✅ **Dry Run Mode** - Test tanpa submit real
- ✅ **Priority System** - High, normal, low priority jobs
- ✅ **Comprehensive Logging** - Detail logging dan statistics

## 📦 Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Install RabbitMQ (optional)
# Ubuntu/Debian:
sudo apt install rabbitmq-server

# macOS:
brew install rabbitmq

# Windows: Download dari https://www.rabbitmq.com/install-windows.html
```

## 🏗️ Project Structure

```
📁 testfor/
├── 📄 main_advanced.py          # Main script dengan CLI
├── 📄 config.py                 # Konfigurasi global
├── 📄 google_forms_automation.py # Core automation class
├── 📄 data_reader.py            # CSV/Excel reader
├── 📄 scheduler.py              # Cron job scheduler
├── 📄 rabbitmq_handler.py       # RabbitMQ queue handler
├── 📄 job_processor.py          # Job processor & worker system
├── 📄 requirements.txt          # Dependencies
└── 📄 README.md                 # This file
```

## 🚀 Quick Start

### 1. Setup Configuration

Edit `config.py`:
```python
FORM_URL = "https://docs.google.com/forms/d/e/YOUR_FORM_ID/viewform"

FORM_DATA = {
    'entry.625591749': 'Test Value'  # Update dengan entry IDs dari form Anda
}
```

### 2. Create Sample Data

```bash
python main_advanced.py batch --create-sample
```

### 3. Run Automation

```bash
# Batch mode (process semua data langsung)
python main_advanced.py batch --csv sample_forms_data.csv

# Scheduled mode (process berdasarkan ETA)
python main_advanced.py scheduled --csv sample_forms_data.csv

# Consumer mode (dari RabbitMQ queue)
python main_advanced.py consumer
```

## 📊 CSV File Format

```csv
entry.625591749,entry.123456789,eta,priority
Option 1,Test User 1,2024-08-05 10:00:00,high
Option 2,Test User 2,2024-08-05 10:05:00,normal
Option 3,Test User 3,2024-08-05 10:10:00,low
```

**Columns:**
- `entry.XXXXXX` - Entry IDs dari Google Form fields
- `eta` - Estimated Time of Arrival (YYYY-MM-DD HH:MM:SS) - Optional
- `priority` - Priority level (high, normal, low) - Optional

## 🎯 Usage Modes

### 1. Batch Mode
Process semua data langsung tanpa scheduling:
```bash
python main_advanced.py batch --csv data.csv --workers 5
```

### 2. Scheduled Mode
Process berdasarkan ETA column di CSV:
```bash
python main_advanced.py scheduled --csv data.csv
```

### 3. Consumer Mode
Wait for jobs dari RabbitMQ queue:
```bash
python main_advanced.py consumer --rabbitmq-host localhost
```

### 4. Worker Mode
Dedicated worker untuk process jobs:
```bash
python main_advanced.py worker --workers 3
```

## 🛠️ Command Line Options

```bash
python main_advanced.py <mode> [options]

Modes:
  batch         Process all data immediately
  scheduled     Process based on ETA column
  consumer      Wait for jobs from RabbitMQ
  worker        Dedicated worker mode

Options:
  --csv FILE           Path to CSV/Excel file
  --create-sample      Create sample CSV file
  --workers N          Number of worker threads (default: 3)
  --no-rabbitmq        Disable RabbitMQ (direct execution)
  --rabbitmq-host HOST RabbitMQ host (default: localhost)
  --dry-run            Test mode (don't submit forms)
  --verbose            Verbose output
```

## 🔧 Configuration

### Basic Config (`config.py`)
```python
# Form configuration
FORM_URL = "https://docs.google.com/forms/d/e/YOUR_FORM_ID/viewform"

# Form data (akan di-override oleh CSV data)
FORM_DATA = {
    'entry.625591749': 'Default Value'
}

# Request settings
REQUEST_CONFIG = {
    'headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    },
    'timeout': 30,
    'retries': 3
}

# Automation settings
AUTOMATION_CONFIG = {
    'verbose': True,
    'dry_run': False,
    'delay_between_submits': 1,
    'auto_extract_fields': True
}
```

### RabbitMQ Config
```python
rabbitmq_config = {
    'host': 'localhost',
    'port': 5672,
    'username': 'guest',
    'password': 'guest',
    'queue_name': 'google_forms_jobs'
}
```

## 📈 Examples

### Simple Batch Processing
```bash
# Create sample data
python main_advanced.py batch --create-sample

# Process immediately
python main_advanced.py batch --csv sample_forms_data.csv
```

### Scheduled Processing
```bash
# Process berdasarkan ETA column
python main_advanced.py scheduled --csv scheduled_data.csv
```

### High Performance Processing
```bash
# Multiple workers dengan RabbitMQ
python main_advanced.py worker --workers 10 --rabbitmq-host production-server
```

### Testing & Development
```bash
# Dry run mode
python main_advanced.py batch --csv test_data.csv --dry-run --verbose

# Without RabbitMQ
python main_advanced.py batch --csv data.csv --no-rabbitmq
```

## 🐰 RabbitMQ Setup

### Install RabbitMQ
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install rabbitmq-server

# Start service
sudo systemctl start rabbitmq-server
sudo systemctl enable rabbitmq-server

# Enable management plugin (optional)
sudo rabbitmq-plugins enable rabbitmq_management
```

### Access Management UI
- URL: http://localhost:15672
- Username: guest
- Password: guest

## 📊 Monitoring & Statistics

Sistem menyediakan real-time statistics:
- Jobs processed
- Success/failure rates
- Processing duration
- Queue status
- Worker performance

## 🔍 Troubleshooting

### Common Issues

1. **RabbitMQ Connection Failed**
   ```bash
   # Check RabbitMQ status
   sudo systemctl status rabbitmq-server
   
   # Restart RabbitMQ
   sudo systemctl restart rabbitmq-server
   ```

2. **Google Forms Entry IDs Not Found**
   - Inspect form HTML source
   - Look for `entry.XXXXXXXXX` patterns
   - Update `config.py` dengan entry IDs yang benar

3. **CSV Format Errors**
   - Pastikan header row berisi `entry.XXXXXX` columns
   - Check ETA format: `YYYY-MM-DD HH:MM:SS`
   - Pastikan no missing values di required columns

4. **Form Submission Failed**
   - Check form URL masih aktif
   - Verify entry IDs masih valid
   - Test dengan `--dry-run` mode

### Debug Mode
```bash
python main_advanced.py batch --csv data.csv --verbose --dry-run
```

## 🤝 Contributing

1. Fork repository
2. Create feature branch
3. Add tests untuk new features
4. Submit pull request

## 📝 License

MIT License - Feel free to use dan modify.

## 🆘 Support

Jika ada issues atau questions:
1. Check troubleshooting section
2. Run dengan `--verbose` untuk detail logs  
3. Test dengan `--dry-run` mode
4. Create issue di GitHub repository