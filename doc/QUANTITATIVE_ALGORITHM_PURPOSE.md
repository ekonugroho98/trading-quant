# 🎯 Fungsi Algoritma Quantitative dalam Trading System

## 📊 Overview

Algoritma quantitative dalam sistem trading ini berfungsi untuk **menganalisis data pasar secara matematis dan statistik** untuk menghasilkan **trading signals, prediksi harga, dan rekomendasi trading** yang objektif dan berbasis data.

---

## 🔍 Fungsi Utama Algoritma Quantitative

### 1️⃣ **Feature Engineering** (Ekstraksi Fitur)

**Tujuan**: Mengubah data mentah (harga, volume) menjadi **indikator teknis** yang dapat digunakan untuk analisis.

**Yang Dilakukan**:
- ✅ **Technical Indicators**:
  - Moving Averages (MA_5, MA_10, MA_20, MA_short, MA_long, EMA_20, EMA_50, EMA_200)
  - RSI (Relative Strength Index) - mengukur momentum
  - MACD (Moving Average Convergence Divergence) - mengukur perubahan trend
  - Bollinger Bands - mengukur volatilitas
  - Volume indicators (VWAP, Volume Ratio, Volume Spike)

- ✅ **Advanced Features**:
  - Z-Score - untuk mean reversion strategy
  - Cycle Detection (FFT-based) - mendeteksi pola siklus
  - Pattern Recognition (Head & Shoulders, Double Top/Bottom)
  - Market Microstructure (Price Efficiency, Price Impact, Spread Proxy)

**Output**: DataFrame dengan kolom-kolom indikator yang siap digunakan untuk analisis

---

### 2️⃣ **Trading Signal Generation** (Pembuatan Sinyal Trading)

**Tujuan**: Menghasilkan sinyal **BELI (LONG)**, **JUAL (SHORT)**, atau **NETRAL** berdasarkan analisis teknikal.

**Yang Dilakukan**:
```python
# Kombinasi sinyal dari multiple indicators:
# 1. EMA Alignment (trend detection)
ema_bullish = (Price > EMA_20 > EMA_50 > EMA_200)
ema_bearish = (Price < EMA_20 < EMA_50 < EMA_200)

# 2. MACD Signal (momentum detection)
macd_bullish = (MACD > Signal) & (Histogram > 0)
macd_bearish = (MACD < Signal) & (Histogram < 0)

# 3. Kombinasi: EMA + MACD harus align
Signal = 1 (LONG) jika ema_bullish & macd_bullish
Signal = -1 (SHORT) jika ema_bearish & macd_bearish
Signal = 0 (NEUTRAL) jika tidak ada alignment
```

**Output**: 
- `Signal` column: 1 (BELI), -1 (JUAL), 0 (NETRAL)
- `Buy_Signal`: Deteksi crossover dari non-buy ke buy
- `Sell_Signal`: Deteksi crossover dari non-sell ke sell

---

### 3️⃣ **Support & Resistance Calculation** (Perhitungan Level Support/Resistance)

**Tujuan**: Menentukan **level kunci** di mana harga kemungkinan akan **bounce** (support) atau **reject** (resistance).

**Yang Dilakukan**:
- Menggunakan **Pivot Points** dan **Local Extrema** (scipy.signal.argrelextrema)
- Menghitung rolling min/max untuk support/resistance dinamis
- Mengidentifikasi level-level penting untuk entry/exit

**Output**:
- `Support`: Level support (harga kemungkinan bounce naik)
- `Resistance`: Level resistance (harga kemungkinan reject turun)
- `Support_Pivot` & `Resistance_Pivot`: Pivot points

**Digunakan untuk**: Menentukan entry levels, stop loss, dan take profit

---

### 4️⃣ **Fibonacci Retracement Calculation** (Perhitungan Fibonacci)

**Tujuan**: Menghitung **level Fibonacci retracement** untuk menentukan entry/exit yang optimal.

**Yang Dilakukan**:
```python
price_range = resistance - support
fib_236 = support + (price_range * 0.236)  # 23.6%
fib_382 = support + (price_range * 0.382)  # 38.2%
fib_500 = support + (price_range * 0.500)  # 50.0%
fib_618 = support + (price_range * 0.618)  # 61.8%
fib_786 = support + (price_range * 0.786)  # 78.6%
```

**Output**: Dictionary dengan Fibonacci levels

**Digunakan untuk**: Entry 2 dan Entry 3 (konservatif dan sangat konservatif)

---

### 5️⃣ **Machine Learning Prediction** (Prediksi dengan ML)

**Tujuan**: Memprediksi **harga masa depan** dan **probabilitas arah pergerakan harga** menggunakan model machine learning.

**Yang Dilakukan**:
- ✅ **Linear Regression** - prediksi harga kontinu
- ✅ **Random Forest** - Classifier (BELI/JUAL) & Regressor (prediksi harga)
- ✅ **Ensemble Methods** - kombinasi multiple models dengan weighting
- ✅ **Moving Average + Momentum** - baseline model

**Output**:
- `Predicted_Price`: Prediksi harga untuk periode berikutnya
- `Buy_Probability`: Probabilitas harga akan naik (0-100%)
- `Signal_ML`: Rekomendasi dari ML (BELI/JUAL)

**Digunakan untuk**: Konfirmasi sinyal dari strategi teknikal

---

### 6️⃣ **Backtesting & Performance Metrics** (Validasi Strategi)

**Tujuan**: Mengukur **kinerja strategi trading** secara historis untuk memvalidasi apakah strategi profitable.

**Yang Dilakukan**:
- ✅ **Accuracy Score** - akurasi prediksi (untuk classification)
- ✅ **Expected Value** - nilai ekspektasi return
- ✅ **Sharpe Ratio** - risk-adjusted return
- ✅ **Maximum Drawdown** - penurunan maksimal dari peak
- ✅ **Win Rate** - persentase trade yang profit
- ✅ **Profit Factor** - ratio profit vs loss
- ✅ **Monte Carlo Simulation** - simulasi berbagai skenario
- ✅ **Transaction Costs** - mempertimbangkan biaya trading

**Output**:
```python
{
    'accuracy': 49%,           # Akurasi prediksi
    'sharpe_ratio': 1.56,     # Risk-adjusted return
    'expected_value': -0.57%, # Expected return (bisa negatif)
    'max_drawdown': 5.2%,     # Maximum drawdown
    'win_rate': 52%,          # Win rate
    'profit_factor': 1.15     # Profit factor
}
```

**Digunakan untuk**: Evaluasi strategi dan pengambilan keputusan

---

### 7️⃣ **Risk Metrics Calculation** (Perhitungan Metrik Risiko)

**Tujuan**: Mengukur **risiko trading** untuk manajemen risiko yang lebih baik.

**Yang Dilakukan**:
- ✅ **VaR (Value at Risk)** - potensi kerugian maksimal pada confidence level tertentu
- ✅ **CVaR (Conditional VaR)** - expected loss jika melewati VaR
- ✅ **Expected Shortfall** - average loss dalam worst-case scenario
- ✅ **Volatility** - ukuran volatilitas harga

**Output**: Risk metrics untuk berbagai confidence levels (90%, 95%, 99%)

**Digunakan untuk**: Manajemen risiko dan position sizing

---

### 8️⃣ **Trading Setup Generation** (Pembuatan Setup Trading)

**Tujuan**: Menghasilkan **entry levels, stop loss, dan take profit** yang optimal berdasarkan analisis teknikal.

**Yang Dilakukan**:
- Menghitung **3 entry levels** (agresif, konservatif, sangat konservatif)
- Menghitung **stop loss** berdasarkan risk percentage
- Menghitung **3 take profit levels** berdasarkan risk:reward ratio
- Menggunakan **Fibonacci levels** untuk entry yang lebih akurat

**Output**:
```python
{
    'entry1': 0.01497,      # Entry agresif
    'entry2': 0.015561,     # Entry konservatif (recommended)
    'entry3': 0.015608,     # Entry sangat konservatif
    'stop_loss': 0.015833,  # Stop loss
    'tp1': 0.014334,        # Take profit 1
    'tp2': 0.01372,         # Take profit 2
    'tp3': 0.013107         # Take profit 3
}
```

**Digunakan untuk**: Rekomendasi trading yang konkret dan actionable

---

### 9️⃣ **Market Context Analysis** (Analisis Konteks Pasar)

**Tujuan**: Memahami **kondisi pasar saat ini** (trending vs ranging, volatilitas, dll).

**Yang Dilakukan**:
- ✅ **Market Regime Detection** - Trending vs Ranging market
- ✅ **Volatility Regime** - High volatility vs Low volatility
- ✅ **Higher Timeframe Context** - Analisis timeframe yang lebih tinggi
- ✅ **Volume Analysis** - Akumulasi vs Distribusi

**Output**: Market context yang membantu interpretasi sinyal

**Digunakan untuk**: Filter sinyal dan meningkatkan akurasi

---

### 🔟 **Cointegration Analysis** (Analisis Kointegrasi)

**Tujuan**: Mencari **pairs trading opportunities** dengan menemukan aset yang bergerak bersama (cointegrated).

**Yang Dilakukan**:
- Menggunakan **Engle-Granger test** untuk mendeteksi kointegrasi
- Menghitung **spread** antara dua aset
- Menghasilkan sinyal berdasarkan mean reversion dari spread

**Output**: Pairs yang cointegrated dan sinyal trading

**Digunakan untuk**: Pairs trading dan statistical arbitrage strategies

---

## 🎯 Alur Kerja Algoritma Quantitative

```
1. Data Collection
   ↓
2. Feature Engineering (Technical Indicators)
   ↓
3. Trading Signal Generation (EMA + MACD)
   ↓
4. Support/Resistance Calculation
   ↓
5. Fibonacci Levels Calculation
   ↓
6. Machine Learning Prediction
   ↓
7. Backtesting & Performance Metrics
   ↓
8. Risk Metrics Calculation
   ↓
9. Trading Setup Generation (Entry, SL, TP)
   ↓
10. Market Context Analysis
    ↓
11. Final Recommendation (DeepSeek AI Integration)
```

---

## 💡 Manfaat Algoritma Quantitative

### 1. **Objektivitas**
- Keputusan trading berdasarkan **data dan statistik**, bukan emosi
- Menghilangkan bias manusia dalam trading

### 2. **Konsistensi**
- Strategi yang sama diterapkan secara konsisten
- Tidak ada perubahan aturan di tengah-tengah trading

### 3. **Backtesting**
- Dapat diuji secara historis sebelum digunakan
- Memvalidasi apakah strategi profitable

### 4. **Risk Management**
- Perhitungan risiko yang akurat
- Position sizing yang tepat

### 5. **Scalability**
- Dapat menganalisis banyak aset sekaligus
- Dapat diotomatisasi sepenuhnya

### 6. **Multi-Timeframe Analysis**
- Analisis dari berbagai timeframe
- Konfirmasi sinyal dari multiple timeframes

---

## 📊 Output Algoritma Quantitative

### Untuk Trading Decision:
1. ✅ **Trading Signal**: BELI/JUAL/NETRAL
2. ✅ **Entry Levels**: 3 level entry (agresif, konservatif, sangat konservatif)
3. ✅ **Stop Loss**: Level stop loss dengan risk percentage
4. ✅ **Take Profit**: 3 level take profit dengan risk:reward ratio
5. ✅ **Confidence Score**: Tingkat kepercayaan sinyal (0-100%)

### Untuk Strategy Evaluation:
1. ✅ **Accuracy**: Akurasi prediksi
2. ✅ **Sharpe Ratio**: Risk-adjusted return
3. ✅ **Expected Value**: Expected return
4. ✅ **Win Rate**: Persentase trade yang profit
5. ✅ **Maximum Drawdown**: Penurunan maksimal

### Untuk Risk Management:
1. ✅ **VaR**: Value at Risk
2. ✅ **CVaR**: Conditional VaR
3. ✅ **Volatility**: Ukuran volatilitas
4. ✅ **Risk:Reward Ratio**: Ratio risiko vs reward

---

## 🎓 Kesimpulan

**Algoritma quantitative berfungsi untuk**:

1. ✅ **Menganalisis data pasar** secara matematis dan statistik
2. ✅ **Menghasilkan trading signals** yang objektif
3. ✅ **Memprediksi pergerakan harga** dengan machine learning
4. ✅ **Menentukan entry/exit levels** yang optimal
5. ✅ **Mengukur kinerja strategi** secara historis
6. ✅ **Mengelola risiko** dengan perhitungan yang akurat
7. ✅ **Menyediakan rekomendasi trading** yang actionable

**Tujuan Utama**: Membantu trader membuat **keputusan trading yang lebih baik** dengan **data-driven approach** dan **risk management yang proper**.

