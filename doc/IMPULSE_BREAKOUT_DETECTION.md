# ⚡🚀 Impulse Move & Breakout Detection

## 🎯 Overview

Impulse Move dan Breakout Detection adalah **feature baru** yang mendeteksi gerakan harga yang kuat dan breakouts dari support/resistance levels. Kedua fitur ini bekerja bersama dengan Pullback dan Reversal detection untuk memberikan informasi lengkap tentang market conditions.

**Status**: ✅ **IMPLEMENTED**

**File**: `src/utils/pullback_detection.py`

---

## ⚡ Impulse Move Detection

### Apa itu Impulse Move?

**Impulse Move** = Gerakan harga yang **kuat dan cepat** dalam satu arah dengan **volume tinggi**.

### Karakteristik:
- **Price Change**: ≥ 2% dalam 5 periods (default)
- **Volume**: ≥ 1.5x average volume (default)
- **Direction**: Bullish (naik) atau Bearish (turun)
- **Speed**: Gerakan cepat, bukan gradual

### Contoh:
```
Bullish Impulse:
Price: $100 → $102.5 (2.5% dalam 5 periods)
Volume: 2.0x average volume
Signal: LONG (Bullish Impulse)
```

---

## 🚀 Breakout Detection

### Apa itu Breakout?

**Breakout** = Harga yang **break melalui** support/resistance level yang signifikan.

### Karakteristik:
- **Bullish Breakout**: Price break **above** resistance
- **Bearish Breakout**: Price break **below** support
- **Volume Confirmation**: Volume ≥ 1.2x average (default)
- **Breakout Threshold**: Minimum 0.5% di atas/bawah level (default)

### Contoh:
```
Bullish Breakout:
Resistance: $100
Price sebelumnya: $99.5
Price sekarang: $100.6 (break above $100.5 = 0.5% threshold)
Volume: 1.5x average
Signal: LONG (Bullish Breakout)
```

---

## 📋 Features yang Ditambahkan

### 1. **Impulse Move Columns**

| Column | Type | Description |
|--------|------|-------------|
| `Impulse_Detected` | bool | Apakah impulse move terdeteksi |
| `Impulse_Type` | str | 'Bullish_Impulse', 'Bearish_Impulse', 'None' |
| `Impulse_Strength` | float | Strength score (0.0 - 1.0) |
| `Impulse_Signal` | int | 1 = LONG, -1 = SHORT, 0 = None |
| `Impulse_Confidence` | float | Confidence score (0.0 - 1.0) |
| `Is_Impulse` | int | Binary indicator (0/1) |
| `Impulse_Opportunity_Score` | float | Overall opportunity score (0-1) |

### 2. **Breakout Columns**

| Column | Type | Description |
|--------|------|-------------|
| `Breakout_Detected` | bool | Apakah breakout terdeteksi |
| `Breakout_Type` | str | 'Bullish_Breakout', 'Bearish_Breakout', 'None' |
| `Breakout_Level` | float | Level support/resistance yang di-break |
| `Breakout_Signal` | int | 1 = LONG, -1 = SHORT, 0 = None |
| `Breakout_Confidence` | float | Confidence score (0.0 - 1.0) |
| `Is_Breakout` | int | Binary indicator (0/1) |
| `Breakout_Opportunity_Score` | float | Overall opportunity score (0-1) |

---

## 🔧 Algoritma

### Impulse Move Detection

1. **Price Change Calculation**
   - Calculate % change dalam window (default: 5 periods)
   - Minimum: 2% (default)

2. **Volume Confirmation**
   - Compare current volume dengan average volume (20 periods)
   - Minimum: 1.5x average (default)

3. **Strength & Confidence**
   - Strength: Berdasarkan price change magnitude
   - Confidence: Kombinasi price change + volume ratio

### Breakout Detection

1. **Support/Resistance Calculation**
   - Auto-calculate dari swing points jika tidak provided
   - Atau gunakan support/resistance dari analisis teknikal

2. **Breakout Check**
   - Bullish: Price break **above** resistance dengan threshold (0.5%)
   - Bearish: Price break **below** support dengan threshold (0.5%)

3. **Volume Confirmation**
   - Volume harus ≥ 1.2x average untuk confirm breakout
   - Volume rendah = kemungkinan false breakout

4. **Confidence Calculation**
   - Base: Breakout strength (jarak dari level)
   - Boost: Volume ratio
   - Final: Weighted combination

---

## 🚀 Cara Menggunakan

### 1. **Automatic Integration**

Impulse Move dan Breakout detection **otomatis aktif** bersama dengan pullback/reversal:

```python
# Di prediksi_next_day.py, semua detections sudah terintegrasi
features = create_features(data, use_enhanced=True)
# Impulse & Breakout features akan otomatis ditambahkan
```

### 2. **Manual Usage**

```python
from src.utils.pullback_detection import (
    detect_impulse_move,
    detect_breakout,
    add_pullback_features
)

# Detect impulse move
df_with_impulse = detect_impulse_move(df)

# Detect breakout
df_with_breakout = detect_breakout(df)

# Atau gunakan add_pullback_features (includes semua)
df_with_all = add_pullback_features(df)
```

### 3. **Output di Console**

Ketika impulse move atau breakout terdeteksi, akan muncul output:

**Impulse Move:**
```
⚡ IMPULSE MOVE DETECTION:
   ✅ Impulse Detected: Bullish_Impulse
   Signal: LONG (Bullish Impulse)
   Strength: 75.0%
   Confidence: 80.0%
   Recommendation: ⚡ BULLISH IMPULSE: Strong upward move detected (80.0% confidence, strength: 75.0%)
```

**Breakout:**
```
🚀 BREAKOUT DETECTION:
   ✅ Breakout Detected: Bullish_Breakout
   Signal: LONG (Bullish Breakout)
   Level: $0.123456
   Confidence: 75.0%
   Recommendation: 🚀 BULLISH BREAKOUT: Price break above resistance $0.123456 (75.0% confidence)
```

---

## 📊 Prioritas Display

Sistem akan menampilkan dengan prioritas berikut:

1. **Reversal** (prioritas tertinggi) - Perubahan trend
2. **Breakout** (prioritas kedua) - Break support/resistance
3. **Impulse Move** (prioritas ketiga) - Gerakan kuat dengan volume
4. **Pullback** (prioritas terendah) - Retracement sementara

**Alasan**: Reversal dan Breakout lebih penting karena menunjukkan perubahan fundamental, sedangkan Impulse Move menunjukkan momentum kuat, dan Pullback hanya retracement sementara.

---

## 💡 Manfaat

### Impulse Move Detection

1. **Momentum Trading**
   - Deteksi gerakan harga yang kuat
   - Entry di awal momentum (risk/reward lebih baik)

2. **Volume Confirmation**
   - Hanya ambil signal jika volume tinggi
   - Mengurangi false signals

3. **Strength Measurement**
   - Measure kekuatan gerakan
   - Filter berdasarkan strength threshold

### Breakout Detection

1. **Key Level Breakthrough**
   - Deteksi break dari support/resistance
   - Entry setelah breakout confirmed

2. **False Breakout Filter**
   - Volume confirmation mengurangi false breakouts
   - Threshold memastikan breakout signifikan

3. **Trend Continuation**
   - Breakout biasanya melanjutkan trend
   - Entry timing yang lebih baik

---

## 📱 Telegram Integration

Impulse Move dan Breakout otomatis ditampilkan di Telegram dengan prioritas yang sesuai:

**Impulse Move:**
```
⚡ IMPULSE MOVE DETECTION:
   🟢 BULLISH IMPULSE (LONG)
   Type: Bullish_Impulse
   Strength: 75.0%
   Confidence: 80.0%
```

**Breakout:**
```
🚀 BREAKOUT DETECTION:
   🟢 BULLISH BREAKOUT (LONG)
   Type: Bullish_Breakout
   Level: 0.123456
   Confidence: 75.0%
```

---

## ⚙️ Configuration

### Impulse Move Parameters

```python
# Di detect_impulse_move()
volume_threshold = 1.5  # Minimum 1.5x average volume
price_change_threshold = 0.02  # Minimum 2% price change
window = 5  # Window untuk calculate price change
```

### Breakout Parameters

```python
# Di detect_breakout()
volume_confirmation = True  # Use volume untuk confirm
breakout_threshold = 0.005  # Minimum 0.5% di atas/bawah level
```

---

## ⚠️ Important Notes

1. **Entry/TP/SL Tidak Berubah**
   - Impulse Move & Breakout detection **TIDAK mengubah** calculation entry/TP/SL
   - Hanya memberikan informasi tambahan

2. **Information Only**
   - Status adalah **saran**, bukan perintah trading
   - Tetap gunakan risk management yang proper

3. **Volume Confirmation**
   - Impulse Move: Volume tinggi = strong signal
   - Breakout: Volume tinggi = valid breakout, volume rendah = false breakout

4. **False Signals**
   - Breakout bisa false jika volume rendah
   - Impulse Move bisa false jika tidak sustain

5. **Combination Signals**
   - Impulse Move + Breakout = Very strong signal
   - Reversal + Breakout = Trend change confirmed

---

## 📝 Example Scenarios

### Scenario 1: Bullish Impulse + Breakout
```
Price: $100 → $103 (3% dalam 5 periods)
Volume: 2.0x average
Resistance: $102
Price break above: $102.5

Result:
- ✅ Impulse Move: Bullish (strength: 80%)
- ✅ Breakout: Bullish (level: $102)
- Signal: STRONG LONG
```

### Scenario 2: Bearish Impulse
```
Price: $100 → $97 (3% turun dalam 5 periods)
Volume: 1.8x average
No breakout

Result:
- ✅ Impulse Move: Bearish (strength: 75%)
- Signal: SHORT
```

### Scenario 3: Breakout tanpa Impulse
```
Price: $100 → $100.6 (0.6% dalam 5 periods)
Volume: 1.3x average
Resistance: $100.5
Price break above: $100.6

Result:
- ✅ Breakout: Bullish (level: $100.5)
- ❌ Impulse Move: Tidak terdeteksi (price change < 2%)
- Signal: MODERATE LONG
```

---

## 🔄 Integration dengan Existing System

### ML Features

Impulse Move dan Breakout features otomatis ditambahkan ke feature engineering:

```python
features = create_features(data, use_enhanced=True)
# Features sekarang include:
# - Impulse_Detected
# - Impulse_Type
# - Impulse_Signal
# - Impulse_Confidence
# - Impulse_Strength
# - Breakout_Detected
# - Breakout_Type
# - Breakout_Signal
# - Breakout_Confidence
# - Breakout_Level
# dll
```

### Entry/TP/SL Calculation

**TIDAK BERUBAH** - Hanya informasi tambahan:

```python
# Entry/TP/SL tetap menggunakan generate_trading_setup()
setup = generate_trading_setup(...)

# Impulse/Breakout status hanya untuk informasi
status = get_current_pullback_status(df)
if status['has_impulse']:
    print(f"💡 Info: Impulse detected - {status['impulse_type']}")
if status['has_breakout']:
    print(f"💡 Info: Breakout detected - {status['breakout_type']}")
```

---

**Last Updated**: 2025-01-XX
**Status**: ✅ Implemented & Integrated

