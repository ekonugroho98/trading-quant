# 🔧 Konfigurasi LSTM/GRU Models

## 📍 Lokasi Konfigurasi

Konfigurasi LSTM/GRU ada di **2 tempat**:

### 1. **`src/utils/config.py`** - Konfigurasi Parameter LSTM/GRU

```python
# ============================================
# KONFIGURASI LSTM/GRU MODELS
# ============================================
ENABLE_LSTM = True  # Enable/disable LSTM
LSTM_SEQUENCE_LENGTH = 60  # Length of input sequences
LSTM_UNITS = 50  # Number of LSTM/GRU units
LSTM_DROPOUT_RATE = 0.2  # Dropout rate
LSTM_EPOCHS = 50  # Number of training epochs
LSTM_BATCH_SIZE = 32  # Batch size
LSTM_USE_GRU = False  # True = GRU, False = LSTM
```

### 2. **`src/utils/config.py`** - Enable LSTM di Ensemble

```python
ML_MODELS_CONFIG = [
    {
        "model": "random_forest",
        "weight": 0.3,
        "enabled": True
    },
    {
        "model": "xgboost",
        "weight": 0.3,
        "enabled": True
    },
    {
        "model": "lstm",  # ← Tambahkan ini untuk enable LSTM
        "weight": 0.2,
        "enabled": True
    },
    {
        "model": "linear",
        "weight": 0.1,
        "enabled": True
    },
    {
        "model": "moving_avg",
        "weight": 0.1,
        "enabled": True
    }
]
```

---

## ⚙️ Parameter Konfigurasi

### 1. **ENABLE_LSTM** (True/False)
- **Default**: `True`
- **Fungsi**: Enable/disable LSTM models
- **Rekomendasi**: 
  - `True` jika data cukup banyak (>100 points) dan ingin akurasi lebih tinggi
  - `False` jika ingin lebih cepat atau data sedikit

### 2. **LSTM_SEQUENCE_LENGTH** (Integer)
- **Default**: `60`
- **Fungsi**: Berapa banyak data points sebelumnya yang dilihat untuk prediksi
- **Rekomendasi**:
  - **Data 15m**: `60` = 15 jam (60 × 15m)
  - **Data 1h**: `60` = 60 jam (2.5 hari)
  - **Data 1d**: `60` = 60 hari
  - **Range**: 20-100 (tergantung data)
  - **Lebih besar** = melihat lebih jauh ke belakang, tapi lebih lambat

### 3. **LSTM_UNITS** (Integer)
- **Default**: `50`
- **Fungsi**: Jumlah neurons per layer
- **Rekomendasi**:
  - **Kecil (25-50)**: Lebih cepat, cocok untuk data sederhana
  - **Sedang (50-100)**: Balance antara speed dan accuracy (RECOMMENDED)
  - **Besar (100-200)**: Lebih akurat tapi lebih lambat, butuh data banyak
  - **Range**: 25-200

### 4. **LSTM_DROPOUT_RATE** (Float 0.0-1.0)
- **Default**: `0.2`
- **Fungsi**: Percentage neurons yang di-dropout untuk prevent overfitting
- **Rekomendasi**:
  - **0.0-0.2**: Untuk data yang tidak overfit
  - **0.2-0.5**: Untuk data yang cenderung overfit (RECOMMENDED: 0.2)
  - **>0.5**: Terlalu banyak dropout, bisa underfit

### 5. **LSTM_EPOCHS** (Integer)
- **Default**: `50`
- **Fungsi**: Berapa kali model di-train
- **Rekomendasi**:
  - **20-30**: Cepat, cocok untuk testing
  - **50-100**: Balance (RECOMMENDED: 50)
  - **100-200**: Lebih akurat tapi lebih lama
  - **Note**: Early stopping akan stop otomatis jika tidak improve

### 6. **LSTM_BATCH_SIZE** (Integer)
- **Default**: `32`
- **Fungsi**: Berapa banyak samples diproses sekaligus
- **Rekomendasi**:
  - **16-32**: Untuk data kecil atau memory terbatas
  - **32-64**: Balance (RECOMMENDED: 32)
  - **64-128**: Lebih cepat tapi butuh lebih banyak memory
  - **Range**: 16, 32, 64, 128, 256

### 7. **LSTM_USE_GRU** (True/False)
- **Default**: `False` (gunakan LSTM)
- **Fungsi**: Pilih LSTM atau GRU
- **Rekomendasi**:
  - **False (LSTM)**: Lebih powerful, cocok untuk time series kompleks (RECOMMENDED)
  - **True (GRU)**: Lebih cepat, cocok untuk data sederhana atau jika butuh speed

---

## 🎯 Contoh Konfigurasi

### Konfigurasi Cepat (Fast Mode)
```python
ENABLE_LSTM = True
LSTM_SEQUENCE_LENGTH = 30  # Lebih pendek = lebih cepat
LSTM_UNITS = 25  # Lebih sedikit neurons
LSTM_DROPOUT_RATE = 0.2
LSTM_EPOCHS = 30  # Lebih sedikit epochs
LSTM_BATCH_SIZE = 64  # Batch lebih besar = lebih cepat
LSTM_USE_GRU = True  # GRU lebih cepat dari LSTM
```

### Konfigurasi Balance (Recommended)
```python
ENABLE_LSTM = True
LSTM_SEQUENCE_LENGTH = 60
LSTM_UNITS = 50
LSTM_DROPOUT_RATE = 0.2
LSTM_EPOCHS = 50
LSTM_BATCH_SIZE = 32
LSTM_USE_GRU = False  # LSTM lebih akurat
```

### Konfigurasi Akurat (Accuracy Mode)
```python
ENABLE_LSTM = True
LSTM_SEQUENCE_LENGTH = 100  # Lihat lebih jauh
LSTM_UNITS = 100  # Lebih banyak neurons
LSTM_DROPOUT_RATE = 0.3  # Lebih banyak dropout
LSTM_EPOCHS = 100  # Lebih banyak epochs
LSTM_BATCH_SIZE = 32
LSTM_USE_GRU = False  # LSTM lebih powerful
```

---

## 📊 Cara Enable LSTM di Ensemble

### Step 1: Edit `src/utils/config.py`

Tambahkan LSTM ke `ML_MODELS_CONFIG`:

```python
ML_MODELS_CONFIG = [
    {
        "model": "random_forest",
        "weight": 0.3,
        "enabled": True
    },
    {
        "model": "xgboost",
        "weight": 0.3,
        "enabled": True
    },
    {
        "model": "lstm",  # ← Tambahkan ini
        "weight": 0.2,
        "enabled": True
    },
    {
        "model": "linear",
        "weight": 0.1,
        "enabled": True
    },
    {
        "model": "moving_avg",
        "weight": 0.1,
        "enabled": True
    }
]
```

### Step 2: Pastikan ENABLE_LSTM = True

```python
ENABLE_LSTM = True  # Pastikan ini True
```

### Step 3: Install Dependencies

```bash
pip install tensorflow keras
```

---

## ⚠️ Catatan Penting

1. **Data Requirements**:
   - Minimal **100+ data points** untuk LSTM
   - Lebih baik jika **200+ data points**

2. **Training Time**:
   - LSTM lebih lambat dari Random Forest/XGBoost
   - Jika terlalu lambat, disable LSTM atau kurangi `LSTM_EPOCHS`

3. **Memory Requirements**:
   - LSTM butuh lebih banyak memory
   - Jika out of memory, kurangi `LSTM_BATCH_SIZE` atau `LSTM_UNITS`

4. **Overfitting**:
   - Jika accuracy tinggi di training tapi rendah di validation = overfitting
   - Solusi: Tingkatkan `LSTM_DROPOUT_RATE` atau kurangi `LSTM_UNITS`

5. **Early Stopping**:
   - LSTM sudah punya early stopping otomatis
   - Akan stop jika validation loss tidak improve selama 10 epochs

---

## 🔍 Troubleshooting

### Problem: LSTM terlalu lambat
**Solusi**:
- Set `LSTM_USE_GRU = True` (GRU lebih cepat)
- Kurangi `LSTM_EPOCHS` ke 20-30
- Kurangi `LSTM_SEQUENCE_LENGTH` ke 30-40
- Kurangi `LSTM_UNITS` ke 25-30

### Problem: Out of Memory
**Solusi**:
- Kurangi `LSTM_BATCH_SIZE` ke 16
- Kurangi `LSTM_UNITS` ke 25-30
- Kurangi `LSTM_SEQUENCE_LENGTH` ke 30-40

### Problem: Overfitting (accuracy tinggi di training, rendah di validation)
**Solusi**:
- Tingkatkan `LSTM_DROPOUT_RATE` ke 0.3-0.5
- Kurangi `LSTM_UNITS` ke 25-50
- Kurangi `LSTM_EPOCHS` (early stopping akan handle)

### Problem: Underfitting (accuracy rendah di training dan validation)
**Solusi**:
- Tingkatkan `LSTM_UNITS` ke 100-200
- Tingkatkan `LSTM_EPOCHS` ke 100-200
- Kurangi `LSTM_DROPOUT_RATE` ke 0.1-0.2

---

## 📝 Quick Reference

| Parameter | Default | Range | Effect jika ↑ |
|-----------|---------|------|---------------|
| `LSTM_SEQUENCE_LENGTH` | 60 | 20-100 | Lebih akurat, lebih lambat |
| `LSTM_UNITS` | 50 | 25-200 | Lebih powerful, lebih lambat |
| `LSTM_DROPOUT_RATE` | 0.2 | 0.0-1.0 | Kurangi overfitting |
| `LSTM_EPOCHS` | 50 | 20-200 | Lebih akurat, lebih lama |
| `LSTM_BATCH_SIZE` | 32 | 16-256 | Lebih cepat, lebih banyak memory |
| `LSTM_USE_GRU` | False | True/False | GRU lebih cepat, LSTM lebih akurat |

---

**Last Updated**: 2025-01-XX

