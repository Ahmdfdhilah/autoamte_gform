# Google Forms Automation System

Sistem automasi Google Forms yang clean dan streamlined dengan support CSV, ETA scheduling, dan RabbitMQ.

## 🚀 Features

- ✅ **Single File Solution** - Semua dalam `main.py`
- ✅ **CSV/Excel Support** - Load data dari file CSV atau Excel
- ✅ **ETA Scheduling** - Schedule berdasarkan waktu WIB per row
- ✅ **RabbitMQ Queue** - Message queue untuk reliability
- ✅ **Timezone Support** - Full WIB (Asia/Jakarta) support
- ✅ **Clean Configuration** - Semua setting di `config.py`

## 📦 Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Install RabbitMQ (optional tapi recommended)
# Ubuntu/Debian:
sudo apt install rabbitmq-server

# macOS:
brew install rabbitmq
```

## 🏗️ Project Structure (Clean!)

```
📁 testfor/
├── 📄 main.py           # Main script (all-in-one)
├── 📄 config.py         # All configurations
├── 📄 requirements.txt  # Dependencies
├── 📄 README.md         # This file
└── 📄 *.csv             # Your data files
```

## 🚀 Quick Start

### 1. Setup Configuration

Edit `config.py`:
```python
FORM_URL = "https://docs.google.com/forms/d/e/YOUR_FORM_ID/viewform"
```

### 2. Create Sample Data

```bash
python main.py batch --create-sample
```

### 3. Run Automation

```bash
# Batch mode (process semua langsung)
python main.py batch --csv sample_data.csv

# Scheduled mode (process berdasarkan ETA)
python main.py scheduled --csv sample_data.csv

# Worker mode (dari RabbitMQ queue)
python main.py worker
```

## 📊 CSV Format

```csv
entry.625591749,eta,priority
Option 1,2025-08-05 08:00:00,high
Option 2,2025-08-05 08:15:00,normal
Option 3,2025-08-05 08:30:00,low
```

**Columns:**
- `entry.XXXXXX` - Entry IDs dari Google Form (required)
- `eta` - Waktu WIB format: YYYY-MM-DD HH:MM:SS (optional)
- `priority` - Priority: high, normal, low (optional)

## 🎯 Usage Modes

### 1. Batch Mode
Process semua data langsung:
```bash
python main.py batch --csv data.csv
```

### 2. Scheduled Mode
Process berdasarkan ETA (WIB):
```bash
python main.py scheduled --csv data.csv
```

### 3. Worker Mode
Process jobs dari RabbitMQ queue:
```bash
python main.py worker
```

## 🛠️ Command Line Options

```bash
python main.py <mode> [options]

Modes:
  batch         Process all data immediately
  scheduled     Process based on ETA column (WIB)
  worker        Wait for jobs from RabbitMQ queue

Options:
  --csv FILE           Path to CSV/Excel file
  --create-sample      Create sample CSV file
  --verbose            Verbose output
```

## 🔧 Configuration (config.py)

```python
# Form URL
FORM_URL = "https://docs.google.com/forms/d/e/YOUR_FORM_ID/viewform"

# Timezone (WIB)
AUTOMATION_CONFIG = {
    'timezone': 'Asia/Jakarta',
    'eta_format': '%Y-%m-%d %H:%M:%S'
}

# RabbitMQ
RABBITMQ_CONFIG = {
    'host': 'localhost',
    'username': 'guest',
    'password': 'guest',
    'queue_name': 'google_forms_jobs'
}
```

## 📈 Examples

### Simple Usage
```bash
# Create and run sample data
python main.py batch --create-sample
python main.py batch --csv sample_data.csv
```

### Scheduled with WIB Time
```bash
# CSV dengan ETA WIB
echo "entry.625591749,eta,priority" > my_data.csv
echo "Test Data,2025-08-05 14:30:00,high" >> my_data.csv

# Run scheduled mode
python main.py scheduled --csv my_data.csv
```

### Production with RabbitMQ
```bash
# Terminal 1: Start worker
python main.py worker

# Terminal 2: Schedule jobs
python main.py scheduled --csv production_data.csv
```

## 🐰 RabbitMQ Setup

```bash
# Install dan start RabbitMQ
sudo apt install rabbitmq-server
sudo systemctl start rabbitmq-server

# Optional: Enable management UI
sudo rabbitmq-plugins enable rabbitmq_management
# Access: http://localhost:15672 (guest/guest)
```

## 🕐 Timezone Support

Sistem menggunakan **WIB (Asia/Jakarta)** timezone:
- ETA di CSV dianggap sebagai waktu WIB
- Current time comparison menggunakan WIB
- Logs menampilkan waktu WIB

**Format ETA:**
- `2025-08-05 08:00:00` = 8:00 AM WIB
- `2025-08-05 14:30:00` = 2:30 PM WIB

## 🔍 Troubleshooting

### Common Issues

1. **Entry IDs tidak valid**
   - Buka form di browser
   - View source dan cari `entry.XXXXXXX`
   - Update config.py dan CSV header

2. **RabbitMQ connection failed**
   ```bash
   sudo systemctl status rabbitmq-server
   sudo systemctl restart rabbitmq-server
   ```

3. **ETA sudah lewat**
   - Pastikan format: `YYYY-MM-DD HH:MM:SS`
   - Gunakan tahun 2025 atau tahun yang benar
   - Waktu dianggap WIB

## 📊 System Flow

```
📊 CSV File → 🕐 ETA Parser → 📅 Scheduler → 🐰 RabbitMQ → 👷 Worker → 📝 Google Forms
```

## 🤝 Contributing

System ini sudah clean dan streamlined. Untuk modifikasi:
1. Edit `main.py` untuk logic changes
2. Edit `config.py` untuk setting changes
3. Test dengan `--verbose` flag

## 📝 License

MIT License - Free to use and modify.

---

**Note:** Sistem ini dirancang simple dan powerful. Satu file `main.py` berisi semua yang dibutuhkan untuk automasi Google Forms dengan CSV, ETA, dan RabbitMQ!