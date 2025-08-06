import pandas as pd

# Baca file data yang ada
try:
    df = pd.read_excel('raw_data.xlsx')  # Coba baca Excel terlebih dahulu
except:
    try:
        df = pd.read_csv('data_rill.csv')  # Jika Excel gagal, coba CSV
    except:
        print("Error: Tidak dapat membaca file data")
        exit()

print(f"Data berhasil dibaca. Shape: {df.shape}")
print(f"Jumlah baris: {len(df)}")

# Mapping nilai kata ke angka
mapping = {
    'Sangat Tidak Penting': 1,
    'Kurang Penting': 2,
    'Cukup Penting': 3,
    'Penting': 4,
    'Sangat Penting': 5,
    'Sangat Tidak Setuju': 1,
    'Kurang Setuju': 2,
    'Cukup Setuju': 3,
    'Setuju': 4,
    'Sangat Setuju': 5
}

# Tentukan kolom yang ingin dikonversi (sesuaikan dengan kolom aktual)
target_cols = []
for col in df.columns:
    if df[col].dtype == 'object':  # Hanya kolom text
        sample_values = df[col].dropna().astype(str).unique()
        for val in sample_values[:5]:  # Cek beberapa sample
            if any(map_key in str(val) for map_key in mapping.keys()):
                target_cols.append(col)
                break

print(f"Kolom yang akan dikonversi: {target_cols}")

# Buat copy dataframe untuk memastikan kolom lain tidak berubah
df_result = df.copy()

# Ubah nilainya berdasarkan mapping untuk setiap kolom target
for col in target_cols:
    print(f"Memproses kolom: {col}")
    
    # Konversi semua baris sampai akhir data
    original_values = df_result[col].copy()
    mapped_values = df_result[col].map(mapping)
    
    # Hanya update nilai yang berhasil di-map, sisanya tetap original
    df_result[col] = mapped_values.where(mapped_values.notna(), original_values)
    
    print(f"  - Berhasil mengkonversi {mapped_values.notna().sum()} dari {len(df_result)} baris")

print("\nKonversi selesai!")
print(f"Total baris yang diproses: {len(df_result)}")

# Simpan hasil
df_result.to_excel('file_finale.xlsx', index=False)
print("File berhasil disimpan sebagai 'file_finale.xlsx'")
