#!/usr/bin/env python3
"""
Script Master untuk menjalankan semua analisis quant trading
Menjalankan:
1. Analisis strategi (analisis_quant.py)
2. Prediksi hari berikutnya (prediksi_next_day.py)
"""

import subprocess
import sys
import os
import time
import glob

def run_script(script_name, description, env=None):
    """Jalankan script Python dan tampilkan output"""
    print("\n" + "=" * 70)
    print(f"🚀 MENJALANKAN: {description}")
    print("=" * 70)
    
    try:
        # Gunakan environment dari parent process, atau env yang diberikan
        process_env = os.environ.copy()
        if env:
            process_env.update(env)
        
        result = subprocess.run(
            [sys.executable, script_name],
            capture_output=False,
            text=True,
            check=False,
            env=process_env
        )
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error menjalankan {script_name}: {e}")
        return False

def main():
    print("=" * 70)
    print("📊 QUANT TRADING - WORKFLOW LENGKAP")
    print("=" * 70)
    print()
    
    # Baca konfigurasi untuk menampilkan info
    try:
        from config import TRADING_STYLE, get_interval
        interval = get_interval()
        print(f"📋 Konfigurasi: TRADING_STYLE = {TRADING_STYLE}, INTERVAL = {interval}")
    except ImportError:
        print("⚠️  config.py tidak ditemukan, menggunakan default")
        TRADING_STYLE = "DAY_TRADING"
        interval = "15m"
    
    print()
    print("Workflow ini akan menjalankan:")
    print("  0️⃣  Ambil Data Historical (otomatis sesuai TRADING_STYLE)")
    print("  1️⃣  Analisis Strategi (Moving Average Crossover)")
    print("  2️⃣  Prediksi Hari Berikutnya (Machine Learning)")
    print()
    
    # Cek apakah file ada
    scripts = {
        "get_historical_data.py": "Ambil Data Historical",
        "analisis_quant.py": "Analisis Strategi Trading",
        "prediksi_next_day.py": "Prediksi Hari Berikutnya"
    }
    
    missing_files = []
    for script, desc in scripts.items():
        if not os.path.exists(script):
            missing_files.append(script)
    
    if missing_files:
        print(f"❌ File tidak ditemukan: {', '.join(missing_files)}")
        return
    
    # Step 0: Ambil data historical (otomatis sesuai TRADING_STYLE)
    print("=" * 70)
    print("STEP 0: AMBIL DATA HISTORICAL")
    print("=" * 70)
    print(f"📊 Mengambil data dengan interval: {interval} (sesuai {TRADING_STYLE})")
    
    # Simpan timestamp sebelum mengambil data untuk mencari file terbaru
    csv_files_before = set(glob.glob("*_historical_*.csv"))
    
    success0 = run_script("get_historical_data.py", "Ambil Data Historical")
    
    # Tunggu sebentar untuk memastikan file sudah ditulis
    time.sleep(1)
    
    # Verifikasi file CSV sudah dibuat
    csv_files_after = set(glob.glob("*_historical_*.csv"))
    new_csv_files = csv_files_after - csv_files_before
    
    if not success0:
        print("\n⚠️  Pengambilan data mengalami error, lanjutkan ke analisis? (y/n)")
        choice = input().lower().strip()
        if choice != 'y':
            print("Membatalkan...")
            return
    elif not new_csv_files and not csv_files_after:
        print("\n⚠️  File CSV tidak ditemukan setelah pengambilan data")
        print("⚠️  Mencoba melanjutkan dengan fallback ke yfinance...")
    elif new_csv_files:
        latest_csv = max(new_csv_files, key=os.path.getctime)
        print(f"\n✅ File CSV berhasil dibuat: {latest_csv}")
        print(f"   File size: {os.path.getsize(latest_csv):,} bytes")
    else:
        # File CSV sudah ada sebelumnya
        if csv_files_after:
            latest_csv = max(csv_files_after, key=os.path.getctime)
            print(f"\n✅ Menggunakan file CSV yang ada: {latest_csv}")
    
    # Step 1: Jalankan analisis strategi
    print("\n" + "=" * 70)
    print("STEP 1: ANALISIS STRATEGI")
    print("=" * 70)
    # Set environment variable untuk memberitahu analisis_quant.py bahwa ini dipanggil dari run_all_analysis.py
    # Environment variable akan diteruskan ke subprocess
    success1 = run_script("analisis_quant.py", "Analisis Strategi Trading", 
                        env={'RUN_FROM_MASTER_SCRIPT': '1'})
    
    if not success1:
        print("\n⚠️  Analisis strategi mengalami error, lanjutkan ke prediksi? (y/n)")
        choice = input().lower().strip()
        if choice != 'y':
            print("Membatalkan...")
            return
    
    # Step 2: Jalankan prediksi
    print("\n" + "=" * 70)
    print("STEP 2: PREDIKSI HARI BERIKUTNYA")
    print("=" * 70)
    success2 = run_script("prediksi_next_day.py", "Prediksi Hari Berikutnya")
    
    # Ringkasan
    print("\n" + "=" * 70)
    print("📋 RINGKASAN WORKFLOW")
    print("=" * 70)
    print(f"✅ Ambil Data Historical: {'Berhasil' if success0 else 'Error'}")
    print(f"✅ Analisis Strategi: {'Berhasil' if success1 else 'Error'}")
    print(f"✅ Prediksi Hari Berikutnya: {'Berhasil' if success2 else 'Error'}")
    
    # Hapus file CSV setelah SEMUA proses selesai
    print("\n" + "=" * 70)
    print("🧹 CLEANUP: Menghapus file temporary")
    print("=" * 70)
    csv_files_to_clean = glob.glob("*_historical_*.csv")
    if csv_files_to_clean:
        for csv_file in csv_files_to_clean:
            try:
                os.remove(csv_file)
                print(f"🗑️  File CSV dihapus: {csv_file}")
            except Exception as e:
                print(f"⚠️  Gagal menghapus file CSV {csv_file}: {e}")
    else:
        print("💡 Tidak ada file CSV untuk dihapus")
    
    if success0 and success1 and success2:
        print("\n🎉 Semua analisis selesai!")
        print(f"📊 Setup sudah otomatis sesuai dengan TRADING_STYLE: {TRADING_STYLE}")
    else:
        print("\n⚠️  Beberapa analisis mengalami error, cek output di atas")

if __name__ == "__main__":
    main()

