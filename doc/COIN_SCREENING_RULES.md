# 📋 COIN SCREENING RULES

Dokumentasi lengkap tentang rules, filter criteria, dan scoring system untuk `screen_coins()`.

---

## 🎯 OVERVIEW

`screen_coins()` adalah fungsi untuk screening multiple coins berdasarkan technical indicators dan metrics. Fungsi ini menggunakan **quick metrics** (tanpa ML atau DeepSeek AI) untuk efisiensi dan kecepatan.

---

## 📊 METRICS YANG DIHITUNG

### 1. **Price Changes**
- **`price_change_1d`**: Perubahan harga 1 hari terakhir (%)
- **`price_change_7d`**: Perubahan harga 7 hari terakhir (%)
  - Jika data < 7 hari, diestimasi: `price_change_1d * 7`

### 2. **Volume Metrics**
- **`volume_ratio`**: Rasio volume saat ini vs rata-rata 7 hari
  - Formula: `current_volume / avg_volume_7d`
  - Nilai > 1.0 = volume lebih tinggi dari rata-rata
  - Nilai < 1.0 = volume lebih rendah dari rata-rata

### 3. **Moving Averages (MA)**
- **`ma_short`**: 5-day Moving Average
- **`ma_long`**: 10-day Moving Average
- **`ma_signal`**: 
  - `"BUY"` jika MA Short > MA Long (bullish crossover)
  - `"SELL"` jika MA Short < MA Long (bearish crossover)
  - `"NEUTRAL"` jika sama

### 4. **RSI (Relative Strength Index)**
- **Period**: Adaptive (min 14, atau sesuai data yang tersedia)
- **`rsi`**: Nilai RSI (0-100)
- **`rsi_signal`**:
  - `"OVERSOLD"` jika RSI < 30 (potensi buy)
  - `"OVERBOUGHT"` jika RSI > 70 (potensi sell)
  - `"NEUTRAL"` jika 30 ≤ RSI ≤ 70

### 5. **Momentum**
- **`momentum`**: Perubahan harga 5 hari terakhir (%)
  - Formula: `(price_now - price_5d_ago) / price_5d_ago * 100`
  - Jika data < 5 hari, menggunakan `price_change_1d`

### 6. **Volatility**
- **`volatility`**: Standard deviation of returns (%)
  - Dihitung dari percentage change harian
  - Nilai tinggi = lebih volatile

### 7. **Combined Score** ⭐
- **Formula**:
  ```
  combined_score = 
    (price_change_7d / 100) * 0.30 +      # 30% weight
    (volume_ratio - 1) * 0.20 +            # 20% weight
    (momentum / 100) * 0.20 +              # 20% weight
    rsi_score * 0.15 +                     # 15% weight
    ma_score * 0.15                        # 15% weight
  ```
  
  Dimana:
  - `rsi_score = (rsi - 50) / 50` → Normalize RSI: -1 to 1
  - `ma_score = 1` jika BUY, `-1` jika SELL, `0` jika NEUTRAL

- **Interpretasi**:
  - Score **positif tinggi** = coin bullish dengan momentum kuat
  - Score **negatif** = coin bearish
  - Score digunakan untuk **ranking** (descending order)

---

## 🔍 FILTER CRITERIA

Coins harus memenuhi **SEMUA** filter berikut untuk masuk ke hasil:

### 1. **Volume Ratio Filter** ✅
```python
volume_ratio >= min_volume_ratio
```
- **Default**: `min_volume_ratio = 0.5`
- **Artinya**: Volume saat ini minimal 50% dari rata-rata 7 hari
- **Tujuan**: Filter coin dengan volume rendah (kurang likuid)

### 2. **Price Change Filter** ✅
```python
min_price_change <= price_change_7d <= max_price_change
```
- **Default**: 
  - `min_price_change = -50.0%`
  - `max_price_change = 100.0%`
- **Artinya**: Perubahan harga 7 hari harus antara -50% sampai +100%
- **Tujuan**: Filter coin dengan pergerakan ekstrem (pump/dump)

### 3. **RSI Range Filter** (Optional) ✅
```python
rsi_range[0] <= rsi <= rsi_range[1]
```
- **Default**: `rsi_range = None` (tidak ada filter)
- **Contoh**: `rsi_range = (30, 70)` → hanya coin dengan RSI 30-70
- **Tujuan**: Filter coin berdasarkan kondisi overbought/oversold

---

## 📈 RANKING & OUTPUT

### Ranking
1. Coins di-sort berdasarkan **`combined_score`** (descending)
2. Score tertinggi = ranking teratas
3. Return **top N** coins (default: `top_n = 10`)

### Output Format
Setiap coin dalam hasil memiliki:
```python
{
    'symbol': 'BTC-USD',
    'current_price': 45000.0,
    'price_change_1d': 2.5,
    'price_change_7d': 15.3,
    'volume_ratio': 1.8,
    'current_volume': 1000000,
    'ma_short': 44800.0,
    'ma_long': 44500.0,
    'ma_signal': 'BUY',
    'rsi': 65.5,
    'rsi_signal': 'NEUTRAL',
    'momentum': 12.3,
    'volatility': 3.2,
    'combined_score': 0.245
}
```

---

## ⚙️ PARAMETER KONFIGURASI

### Required Parameters
- **`coins`**: List of coin symbols (default: `DEFAULT_COINS` = 150+ coins)
- **`days`**: Jumlah hari data historis (default: `90`)

### Filter Parameters
- **`min_volume_ratio`**: Minimum volume ratio (default: `0.5`)
- **`min_price_change`**: Minimum price change % (default: `-50.0`)
- **`max_price_change`**: Maximum price change % (default: `100.0`)
- **`rsi_range`**: RSI range tuple atau None (default: `None`)

### Output Parameters
- **`top_n`**: Jumlah top coins yang dikembalikan (default: `10`)

### Data Source Parameters
- **`data_source`**: `"yfinance"` atau `"binance"` (default: dari `config.py`)
- **`api_key`**: Binance API key (optional)
- **`api_secret`**: Binance API secret (optional)

---

## 📝 CONTOH PENGGUNAAN

### Contoh 1: Default Screening
```python
results = screen_coins()
# Screening 150+ coins dengan default filters
# Return top 10 coins dengan score tertinggi
```

### Contoh 2: Custom Filters
```python
results = screen_coins(
    coins=["BTC-USD", "ETH-USD", "SOL-USD"],
    days=30,
    min_volume_ratio=1.5,  # Volume harus 1.5x dari rata-rata
    min_price_change=5.0,   # Minimal naik 5% dalam 7 hari
    max_price_change=50.0,  # Maksimal naik 50% dalam 7 hari
    rsi_range=(40, 60),     # RSI antara 40-60 (tidak overbought/oversold)
    top_n=5
)
```

### Contoh 3: Find Oversold Coins
```python
results = screen_coins(
    days=7,
    min_volume_ratio=0.8,
    min_price_change=-20.0,  # Boleh turun sampai 20%
    max_price_change=10.0,    # Tapi tidak boleh pump terlalu tinggi
    rsi_range=(20, 35),        # RSI oversold (20-35)
    top_n=10
)
```

### Contoh 4: Find High Momentum Coins
```python
results = screen_coins(
    days=7,
    min_volume_ratio=1.2,     # Volume tinggi
    min_price_change=10.0,     # Minimal naik 10%
    max_price_change=100.0,
    rsi_range=None,            # Tidak filter RSI
    top_n=20
)
```

---

## 🎯 STRATEGI SCREENING

### 1. **Bullish Momentum Strategy**
- `min_price_change = 5.0`
- `min_volume_ratio = 1.2`
- `rsi_range = (50, 70)` (tidak terlalu overbought)
- `ma_signal = "BUY"` (akan terfilter otomatis jika MA Short > MA Long)

### 2. **Oversold Bounce Strategy**
- `min_price_change = -30.0`
- `max_price_change = 5.0`
- `rsi_range = (20, 35)` (oversold)
- `min_volume_ratio = 0.8`

### 3. **Breakout Strategy**
- `min_price_change = 10.0`
- `min_volume_ratio = 1.5` (volume tinggi = breakout confirmation)
- `rsi_range = (55, 75)` (momentum kuat tapi belum terlalu overbought)

### 4. **Conservative Strategy**
- `min_price_change = 0.0` (hanya coin yang naik)
- `min_volume_ratio = 1.0` (volume normal atau lebih tinggi)
- `rsi_range = (40, 60)` (tidak ekstrem)
- `top_n = 5` (hanya top 5)

---

## ⚠️ CATATAN PENTING

1. **Data Requirements**:
   - Minimal 2 data points untuk price change
   - Minimal 7 data points untuk volume ratio yang akurat
   - Minimal 10 data points untuk MA signal yang reliable

2. **Adaptive Calculations**:
   - Jika data kurang, sistem akan menggunakan estimasi atau default values
   - RSI period disesuaikan dengan jumlah data yang tersedia

3. **Combined Score**:
   - Score adalah **relatif**, bukan absolut
   - Score tinggi tidak berarti coin pasti bagus, hanya ranking terbaik dari pool yang di-screen
   - Selalu lakukan **due diligence** sebelum trading

4. **Volume Ratio**:
   - Ratio < 1.0 = volume rendah (mungkin kurang likuid)
   - Ratio > 1.0 = volume tinggi (lebih likuid, lebih reliable)

5. **RSI Interpretation**:
   - RSI < 30 = Oversold (potensi buy, tapi bisa turun lebih dalam)
   - RSI > 70 = Overbought (potensi sell, tapi bisa naik lebih tinggi)
   - RSI 30-70 = Neutral (trend normal)

---

## 🔧 TIPS OPTIMASI

1. **Untuk Screening Cepat**:
   - Gunakan `days = 7` atau `days = 30`
   - Kurangi `top_n` jika tidak perlu banyak hasil

2. **Untuk Screening Akurat**:
   - Gunakan `days = 90` untuk data lebih lengkap
   - Set `min_volume_ratio` lebih tinggi untuk filter coin likuid

3. **Untuk Find Specific Patterns**:
   - Kombinasikan filter dengan RSI range
   - Gunakan price change range yang spesifik

4. **Untuk Production Use**:
   - Gunakan Binance API (`data_source = "binance"`) untuk data lebih reliable
   - Set API key untuk rate limit lebih tinggi

---

## 📚 REFERENSI

- **RSI**: Relative Strength Index (0-100)
- **MA Crossover**: Moving Average Crossover Strategy
- **Volume Analysis**: Volume Confirmation untuk Price Movement
- **Momentum**: Rate of Change (ROC) indicator

---

**Last Updated**: 2025-01-14

