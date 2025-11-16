import requests
import pandas as pd
import time
from datetime import datetime, timedelta

# Konfigurasi
url = "https://indodax.com/api/trades/btcidr"

# REKOMENDASI DURASI PENGAMBILAN DATA:
# - Minimum: 15-20 menit (untuk MA 15 menit bisa dihitung dengan baik)
# - Optimal: 30-60 menit (untuk analisis intraday yang lebih akurat)
# - Ideal: 2-4 jam (untuk mendapatkan pola yang lebih jelas)
# - Komprehensif: 8-24 jam (untuk analisis jangka panjang intraday)
DURATION_MINUTES = 60  # Durasi pengambilan data (menit) - Optimal untuk analisis akurat

# REKOMENDASI INTERVAL:
# - 30 detik: untuk data real-time (banyak data, lebih akurat)
# - 60 detik: untuk data menit (balance antara akurasi dan jumlah request)
# - 5 menit: untuk data jangka panjang (lebih sedikit request)
INTERVAL_SECONDS = 30  # Interval pengambilan data (detik)

print(f"Memulai pengambilan data selama {DURATION_MINUTES} menit...")
print(f"Interval pengambilan: setiap {INTERVAL_SECONDS} detik")
print("-" * 50)

# Simpan semua data yang dikumpulkan
all_data = []
start_time = datetime.now()
end_time = start_time + timedelta(minutes=DURATION_MINUTES)
iteration = 0

try:
    while datetime.now() < end_time:
        iteration += 1
        current_time = datetime.now()
        elapsed = (current_time - start_time).total_seconds() / 60
        
        # Ambil data dari Indodax
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            # Tambahkan timestamp pengambilan data
            for item in data:
                item['fetch_time'] = current_time.isoformat()
            
            all_data.extend(data)
            
            print(f"[{current_time.strftime('%H:%M:%S')}] Iterasi {iteration} - "
                  f"Data terkumpul: {len(all_data)} records "
                  f"(Elapsed: {elapsed:.1f} menit)")
            
        except requests.exceptions.RequestException as e:
            print(f"[{current_time.strftime('%H:%M:%S')}] Error mengambil data: {e}")
        
        # Tunggu sampai interval berikutnya (kecuali sudah mencapai waktu akhir)
        if datetime.now() < end_time:
            time.sleep(INTERVAL_SECONDS)
    
    print("-" * 50)
    print(f"Pengambilan data selesai! Total: {len(all_data)} records")
    
    if len(all_data) == 0:
        print("Tidak ada data yang berhasil dikumpulkan.")
    else:
        # Ubah ke DataFrame
        df = pd.DataFrame(all_data)
        df['date'] = pd.to_datetime(df['date'], unit='s', errors='coerce')
        df['price'] = pd.to_numeric(df['price'], errors='coerce')
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
        df['fetch_time'] = pd.to_datetime(df['fetch_time'], errors='coerce')
        
        # Hapus baris dengan data tidak valid
        df = df.dropna(subset=['date', 'price'])
        
        # Urutkan berdasarkan waktu
        df = df.sort_values('date').reset_index(drop=True)
        
        print(f"\nData setelah cleaning: {len(df)} records")
        print("\n5 data terbaru:")
        print(df[['tid', 'type', 'price', 'amount', 'date']].tail())
        
        # Hitung harga rata-rata per menit (resampling)
        df.set_index('date', inplace=True)
        df_min = df['price'].resample('1min').mean().dropna()
        
        print(f"\nHarga rata-rata per menit ({len(df_min)} menit):")
        print(df_min.head(10))
        
        # Statistik
        print("\n" + "=" * 50)
        print("STATISTIK DATA:")
        print("=" * 50)
        print(f"Total records: {len(df)}")
        print(f"Periode: {df.index.min()} sampai {df.index.max()}")
        print(f"Harga tertinggi: {df['price'].max():,.0f}")
        print(f"Harga terendah: {df['price'].min():,.0f}")
        print(f"Harga rata-rata: {df['price'].mean():,.0f}")
        print(f"Total volume: {df['amount'].sum():.8f} BTC")
        
        # Simpan ke CSV (opsional)
        filename = f"btc_data_{start_time.strftime('%Y%m%d_%H%M%S')}.csv"
        df.reset_index().to_csv(filename, index=False)
        print(f"\nData disimpan ke: {filename}")

except KeyboardInterrupt:
    print("\n\nPengambilan data dihentikan oleh user.")
    if len(all_data) > 0:
        print(f"Data yang sudah terkumpul: {len(all_data)} records")
