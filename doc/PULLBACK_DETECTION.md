# 📊 Pullback Detection Feature

## 🎯 Overview

Pullback Detection adalah **feature baru** yang mendeteksi pullback dalam trend untuk memberikan informasi tambahan tentang timing entry yang lebih baik. **Feature ini TIDAK mengubah entry/TP/SL yang sudah ada**, hanya memberikan informasi tambahan.

---

## ✅ Status

**Status**: ✅ **IMPLEMENTED**

**File**: `src/utils/pullback_detection.py`

**Integration**: 
- ✅ Integrated ke `enhanced_feature_engineering.py`
- ✅ Integrated ke `prediksi_next_day.py`
- ✅ Available sebagai features untuk ML models

---

## 🔍 Apa itu Pullback?

**Pullback** = Retracement sementara dalam trend yang sedang berlangsung:

- **Uptrend**: Harga naik → Pullback = harga turun sementara → Lanjut naik
- **Downtrend**: Harga turun → Pullback = harga naik sementara → Lanjut turun

### Contoh:
```
Uptrend:
Price: $100 → $110 → $105 (pullback) → $115 → $120
         ↑        ↑         ↑              ↑
      Start    Swing High  Pullback    Continue
```

---

## 📋 Features yang Ditambahkan

### 1. **Pullback Detection Columns**

Setelah pullback detection, DataFrame akan memiliki kolom-kolom berikut:

| Column | Type | Description |
|--------|------|-------------|
| `Pullback_Detected` | bool | Apakah pullback terdeteksi |
| `Pullback_Type` | str | 'Shallow', 'Medium', 'Deep', 'None' |
| `Pullback_Depth` | float | Depth retracement (0.0 - 1.0) |
| `Pullback_Signal` | int | 1 = LONG opportunity, -1 = SHORT opportunity, 0 = None |
| `Pullback_Confidence` | float | Confidence score (0.0 - 1.0) |
| `Pullback_Signal_Confirmed` | int | Signal setelah volume confirmation |
| `Is_Pullback` | int | Binary indicator (0/1) |
| `Pullback_Strength` | float | Pullback strength score |
| `Pullback_Opportunity_Score` | float | Overall opportunity score (0-1) |

### 2. **Pullback Classification**

- **Shallow Pullback** (23.6% - 38.2% retracement)
  - Trend masih sangat kuat
  - Confidence: **High (0.8)**
  - Entry timing: **Excellent**

- **Medium Pullback** (38.2% - 61.8% retracement)
  - Trend masih intact
  - Confidence: **Medium (0.6)**
  - Entry timing: **Good**

- **Deep Pullback** (61.8% - 78.6% retracement)
  - Trend masih valid tapi lemah
  - Confidence: **Low (0.4)**
  - Entry timing: **Caution** (bisa jadi reversal)

- **Reversal** (> 78.6% retracement)
  - Bukan pullback, kemungkinan reversal
  - Tidak dianggap sebagai pullback opportunity

---

## 🚀 Cara Menggunakan

### 1. **Automatic Integration**

Pullback detection **otomatis aktif** ketika menggunakan enhanced features:

```python
# Di prediksi_next_day.py, pullback detection sudah terintegrasi
features = create_features(data, use_enhanced=True)
# Pullback features akan otomatis ditambahkan
```

### 2. **Manual Usage**

```python
from src.utils.pullback_detection import (
    add_pullback_features,
    get_current_pullback_status
)

# Add pullback features ke DataFrame
df_with_pullback = add_pullback_features(df)

# Get current pullback status untuk coin (misalnya XAN)
pullback_status = get_current_pullback_status(df)
print(pullback_status['recommendation'])
```

### 3. **Output di Console**

Ketika pullback terdeteksi, akan muncul output seperti ini:

```
📊 PULLBACK DETECTION:
   ✅ Pullback Detected: Medium (45.2% retracement)
   Signal: LONG
   Confidence: 60.0%
   Recommendation: LONG opportunity detected: Medium pullback (45.2% retracement)
   Entry Levels:
      Entry 1 (Shallow): $0.123456
      Entry 2 (Medium): $0.120000
      Entry 3 (Deep): $0.118000
```

---

## 📊 Pullback Entry Levels

Pullback detection juga menyediakan **suggested entry levels** berdasarkan Fibonacci retracement:

- **Entry 1 (Shallow)**: Fibonacci 38.2% - untuk entry cepat
- **Entry 2 (Medium)**: Fibonacci 61.8% - untuk entry balance
- **Entry 3 (Deep)**: Fibonacci 78.6% - untuk entry sangat konservatif

**Catatan**: Entry levels ini adalah **saran tambahan**, entry/TP/SL utama tetap menggunakan calculation yang sudah ada di `analisis_quant.py`.

---

## 🔧 Configuration

Pullback detection menggunakan default parameters yang bisa disesuaikan:

```python
# Di pullback_detection.py
min_retracement = 0.236  # Minimum 23.6%
max_retracement = 0.786  # Maximum 78.6%
swing_window = 5  # Window untuk detect swing points
min_swing_size = 0.01  # Minimum 1% swing size
volume_threshold = 0.8  # Volume confirmation threshold
```

---

## 💡 Manfaat Pullback Detection

### 1. **Better Entry Timing**
- Entry di pullback biasanya lebih baik daripada entry di puncak/lembah
- Risk/Reward ratio lebih baik

### 2. **Filter False Signals**
- Hanya ambil signal jika ada pullback confirmation
- Mengurangi false breakouts

### 3. **Additional Features untuk ML**
- Pullback features bisa digunakan sebagai input untuk ML models
- Meningkatkan akurasi prediksi

### 4. **Information Only**
- **TIDAK mengubah** entry/TP/SL calculation yang sudah ada
- Hanya memberikan informasi tambahan untuk decision making

---

## 📈 Integration dengan Existing System

### Entry/TP/SL Calculation

**TIDAK BERUBAH** - Pullback detection hanya memberikan informasi tambahan:

```python
# Entry/TP/SL tetap menggunakan generate_trading_setup() di analisis_quant.py
setup = generate_trading_setup(
    symbol="XANUSDT",
    current_price=current_price,
    support=support,
    resistance=resistance,
    signal=signal,
    risk_percent=2.5,
    tp_multipliers=[1.5, 2.5, 3.5]
)

# Pullback status hanya untuk informasi
pullback_status = get_current_pullback_status(df)
if pullback_status['has_pullback']:
    print(f"💡 Info: Pullback detected - {pullback_status['recommendation']}")
    # Entry/TP/SL tetap menggunakan setup di atas
```

### ML Features

Pullback features otomatis ditambahkan ke feature engineering:

```python
features = create_features(data, use_enhanced=True)
# Features sekarang include:
# - Pullback_Detected
# - Pullback_Type
# - Pullback_Depth
# - Pullback_Signal
# - Pullback_Confidence
# - Pullback_Opportunity_Score
# dll
```

---

## 🎯 Use Cases

### 1. **XAN Coin Analysis**

```python
# Get pullback status untuk XAN
pullback_status = get_current_pullback_status(xan_data)

if pullback_status['has_pullback']:
    if pullback_status['pullback_signal'] == 1:  # LONG
        print(f"✅ XAN: LONG opportunity - {pullback_status['pullback_type']} pullback")
    elif pullback_status['pullback_signal'] == -1:  # SHORT
        print(f"✅ XAN: SHORT opportunity - {pullback_status['pullback_type']} pullback")
```

### 2. **Enhanced ML Prediction**

Pullback features bisa digunakan sebagai input untuk ML models:

```python
# Features include pullback indicators
features = create_features(data, use_enhanced=True)

# ML models bisa menggunakan pullback features
# untuk meningkatkan akurasi prediksi
model.fit(features, target)
```

### 3. **Signal Confirmation**

Gunakan pullback untuk konfirmasi signal:

```python
# Jika ML signal = LONG dan pullback detected = LONG opportunity
if ml_signal == "BELI" and pullback_status['pullback_signal'] == 1:
    print("✅ Strong LONG signal - ML + Pullback aligned")
```

---

## ⚠️ Important Notes

1. **Entry/TP/SL Tidak Berubah**
   - Pullback detection **TIDAK mengubah** calculation entry/TP/SL
   - Hanya memberikan informasi tambahan

2. **Information Only**
   - Pullback status adalah **saran**, bukan perintah trading
   - Tetap gunakan risk management yang proper

3. **Volume Confirmation**
   - Pullback yang valid biasanya memiliki volume rendah
   - Volume tinggi saat pullback = kemungkinan reversal

4. **Trend Context**
   - Pullback hanya valid dalam trend yang jelas
   - Di ranging market, pullback detection kurang reliable

---

## 📝 Example Output

```
📊 PULLBACK DETECTION:
   ✅ Pullback Detected: Medium (45.2% retracement)
   Signal: LONG
   Confidence: 60.0%
   Recommendation: LONG opportunity detected: Medium pullback (45.2% retracement)
   Entry Levels:
      Entry 1 (Shallow): $0.123456
      Entry 2 (Medium): $0.120000
      Entry 3 (Deep): $0.118000
```

---

**Last Updated**: 2025-01-XX
**Status**: ✅ Implemented & Integrated

