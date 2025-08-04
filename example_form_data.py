# CONTOH FORM_DATA untuk berbagai tipe field Google Forms

FORM_DATA_EXAMPLES = {
    # ===== TEXT FIELDS =====
    'entry.123456': 'Nama saya',
    'entry.789012': 'email@example.com',
    
    # ===== MULTIPLE CHOICE (Radio Button) =====
    # Pilih SATU opsi saja
    'entry.345678': 'Pilihan A',
    
    # ===== CHECKBOX =====
    # Pilih BANYAK opsi (array/list)
    'entry.567890': ['Option 1', 'Option 3', 'Option 5'],
    
    # ===== DROPDOWN =====
    # Pilih dari dropdown list
    'entry.111222': 'Jakarta',
    
    # ===== LINEAR SCALE (1-5, 1-10, etc) =====
    'entry.333444': '4',  # Rating 4 dari skala
    
    # ===== DATE =====
    'entry.555666': '2024-01-15',  # Format: YYYY-MM-DD
    
    # ===== TIME =====
    'entry.777888': '14:30',  # Format: HH:MM
    
    # ===== NUMBER =====
    'entry.999000': '100',
    
    # ===== PARAGRAPH TEXT =====
    'entry.111333': 'Ini adalah teks panjang untuk paragraph field...',
    
    # ===== FILE UPLOAD =====
    # File upload lebih kompleks, butuh handling khusus
    # 'entry.222444': 'file_path_or_base64',
}

# CONTOH REAL untuk form dengan berbagai field types:
REAL_EXAMPLE = {
    # Nama (Text)
    'entry.1234567890': 'John Doe',
    
    # Email (Email)
    'entry.2345678901': 'john.doe@email.com',
    
    # Gender (Multiple Choice)
    'entry.3456789012': 'Laki-laki',
    
    # Hobi (Checkbox - bisa pilih banyak)
    'entry.4567890123': ['Membaca', 'Olahraga', 'Gaming'],
    
    # Kota (Dropdown)
    'entry.5678901234': 'Jakarta',
    
    # Rating Layanan (Linear Scale 1-5)
    'entry.6789012345': '5',
    
    # Tanggal Lahir (Date)
    'entry.7890123456': '1990-05-15',
    
    # Jam Interview (Time)
    'entry.8901234567': '10:30',
    
    # Gaji yang Diharapkan (Number)
    'entry.9012345678': '5000000',
    
    # Pesan Tambahan (Paragraph)
    'entry.0123456789': 'Saya sangat tertarik dengan posisi ini karena...'
}

print("Copy salah satu contoh di atas ke FORM_DATA di main.py!")