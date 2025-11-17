# 📊 Parameter yang Menentukan Entry Levels

## 🎯 Overview

Entry levels (Entry 1, Entry 2, Entry 3) ditentukan oleh beberapa parameter utama yang dihitung dari analisis teknikal dan konfigurasi trading.

## 📋 Parameter Input

### 1. **Harga & Level Teknikal**

#### `current_price` (Harga Saat Ini)
- **Sumber**: Real-time price dari exchange (Binance API)
- **Penggunaan**: 
  - Entry 1 (Agresif) untuk SHORT: `current_price * 1.002` (0.2% di atas)
  - Entry 1 (Agresif) untuk LONG: `current_price * 1.001` (0.1% di atas)
- **Penting**: Entry harus relatif terhadap current price untuk memastikan relevansi

#### `support` (Level Support)
- **Sumber**: Dihitung dari analisis teknikal (pivot points, swing lows, dll)
- **Penggunaan**:
  - **LONG**: Entry 2 dan Entry 3 di sekitar support
  - **SHORT**: Digunakan untuk validasi dan perhitungan TP
- **Formula**:
  - Entry 2 (LONG): `support * 1.001` (0.1% di atas support)
  - Entry 3 (LONG): `support * 0.998` (0.2% di bawah support)

#### `resistance` (Level Resistance)
- **Sumber**: Dihitung dari analisis teknikal (pivot points, swing highs, dll)
- **Penggunaan**:
  - **SHORT**: Entry 2 dan Entry 3 di sekitar resistance
  - **LONG**: Digunakan untuk validasi dan perhitungan TP
- **Formula**:
  - Entry 2 (SHORT): `resistance * 0.999` (0.1% di bawah resistance)
  - Entry 3 (SHORT): `resistance * 1.002` (0.2% di atas resistance)

### 2. **Fibonacci Retracement Levels**

#### `fib_levels` (Fibonacci Levels)
- **Sumber**: Dihitung dari `calculate_fibonacci_levels(support, resistance, current_price)`
- **Levels yang Digunakan**:
  - **LONG**:
    - Entry 2: `fib_618` (Fibonacci 0.618)
    - Entry 3: `fib_786` (Fibonacci 0.786)
  - **SHORT**:
    - Entry 2: `fib_382_from_top` = `resistance - (range * 0.382)`
    - Entry 3: `fib_236_from_top` = `resistance - (range * 0.236)`

**Formula Fibonacci:**
```python
price_range = resistance - support
fib_236 = support + (price_range * 0.236)  # 23.6%
fib_382 = support + (price_range * 0.382)  # 38.2%
fib_500 = support + (price_range * 0.500)  # 50.0%
fib_618 = support + (price_range * 0.618)  # 61.8%
fib_786 = support + (price_range * 0.786)  # 78.6%
```

### 3. **Trading Signal**

#### `signal` (Trading Signal)
- **Nilai**: `1` = LONG/BUY, `-1` = SHORT/SELL, `0` = NEUTRAL
- **Sumber**: Dari strategi trading (moving average crossover, RSI, dll)
- **Pengaruh**: Menentukan logika perhitungan entry (LONG vs SHORT)

### 4. **Risk Management Parameters**

#### `risk_percent` (Risk Percentage)
- **Default**: `2.5%` (dapat dikonfigurasi berdasarkan `TRADING_STYLE`)
- **Sumber**: Dari `config.py` atau parameter function
- **Penggunaan**: Menghitung Stop Loss
- **Mapping Trading Style**:
  ```python
  SCALPING: 0.75%
  DAY_TRADING: 2.0%
  INTRADAY_TRADING: 1.75%
  SWING_TRADING: 2.5%
  POSITION_TRADING: 3.5%
  ```

#### `tp_multipliers` (Take Profit Multipliers)
- **Default**: `[1.5, 2.5, 3.5]` untuk TP1, TP2, TP3
- **Sumber**: Dari `config.py` atau parameter function
- **Penggunaan**: Menghitung Take Profit levels berdasarkan Risk:Reward ratio
- **Mapping Trading Style**:
  ```python
  SCALPING: [1.2, 1.5, 2.0]
  DAY_TRADING: [1.5, 2.5, 3.5]
  INTRADAY_TRADING: [1.5, 2.5, 3.5]
  SWING_TRADING: [2.0, 3.0, 5.0]
  POSITION_TRADING: [3.0, 5.0, 8.0]
  ```

## 🔢 Logika Perhitungan Entry Levels

### **LONG Position**

#### Entry 1 (Agresif)
```python
if current_price >= support * 1.002:
    entry1 = current_price * 1.001  # 0.1% di atas current
else:
    entry1 = support * 1.002  # 0.2% di atas support
```
**Konsep**: Entry cepat, dekat dengan current price atau sedikit di atas support

#### Entry 2 (Konservatif - Recommended)
```python
if fib_levels:
    entry2 = max(support * 1.001, fib_levels['fib_618'])
else:
    entry2 = support * 1.001  # 0.1% di atas support
```
**Konsep**: Entry aman, di support atau Fibonacci 0.618

#### Entry 3 (Sangat Konservatif)
```python
if fib_levels:
    entry3 = min(support * 0.998, fib_levels['fib_786'])
else:
    entry3 = support * 0.998  # 0.2% di bawah support
```
**Konsep**: Entry paling aman, menunggu pullback ke support atau Fibonacci 0.786

**Urutan**: Entry 3 < Entry 2 < Entry 1 (semua di bawah atau di current price)

### **SHORT Position**

#### Entry 1 (Agresif)
```python
entry1_agresif = current_price * 1.002  # 0.2% di atas current
entry1_resistance = resistance * 0.999  # Di resistance
entry1 = min(entry1_agresif, entry1_resistance)  # Ambil yang lebih rendah
if entry1 < current_price:
    entry1 = current_price * 1.002  # Force di atas current
```
**Konsep**: Entry cepat, dekat dengan current price (0.2% di atas)

#### Entry 2 (Konservatif - Recommended)
```python
if fib_levels:
    fib_382_from_top = resistance - (price_range * 0.382)
    entry2 = max(resistance * 0.999, fib_382_from_top)
else:
    entry2 = resistance * 0.999  # 0.1% di bawah resistance
if entry2 <= entry1:
    entry2 = max(entry1 * 1.001, resistance * 0.999)
```
**Konsep**: Entry aman, di resistance atau Fibonacci 0.382 dari atas

#### Entry 3 (Sangat Konservatif)
```python
if fib_levels:
    fib_236_from_top = resistance - (price_range * 0.236)
    entry3 = max(resistance * 1.002, fib_236_from_top)
else:
    entry3 = resistance * 1.002  # 0.2% di atas resistance
if entry3 < entry2:
    entry3 = entry2 * 1.001  # Force lebih tinggi dari entry2
```
**Konsep**: Entry paling aman, menunggu pullback di atas resistance

**Urutan**: Entry 1 < Entry 2 < Entry 3 (semua di atas current price)

## 🔄 Validasi & Constraints

### Validasi untuk LONG
1. **Entry 3 < Entry 2 < Entry 1** (semua di bawah atau di current price)
2. **Entry 1 >= current_price** (untuk agresif, bisa di atas current)
3. **Entry 2 >= support** (konservatif di support atau di atas)
4. **Entry 3 <= support** (sangat konservatif di bawah support)

### Validasi untuk SHORT
1. **Entry 1 < Entry 2 < Entry 3** (semua di atas current price)
2. **Entry 1 >= current_price** (agresif dekat current)
3. **Entry 2 >= entry1** (konservatif lebih tinggi dari agresif)
4. **Entry 3 >= entry2** (sangat konservatif paling tinggi)

## 📊 Contoh Perhitungan

### Contoh LONG
```
current_price = 0.01487
support = 0.013101
resistance = 0.015577
signal = 1 (LONG)

Entry 1 (Agresif):
  - current_price >= support * 1.002? 0.01487 >= 0.013131? YES
  - entry1 = 0.01487 * 1.001 = 0.01489

Entry 2 (Konservatif):
  - entry2 = max(0.013101 * 1.001, fib_618) = max(0.013114, 0.01461) = 0.01461

Entry 3 (Sangat Konservatif):
  - entry3 = min(0.013101 * 0.998, fib_786) = min(0.013075, 0.01305) = 0.01305
```

### Contoh SHORT
```
current_price = 0.01487
support = 0.013101
resistance = 0.015577
signal = -1 (SHORT)

Entry 1 (Agresif):
  - entry1_agresif = 0.01487 * 1.002 = 0.01490
  - entry1_resistance = 0.015577 * 0.999 = 0.01556
  - entry1 = min(0.01490, 0.01556) = 0.01490

Entry 2 (Konservatif):
  - price_range = 0.015577 - 0.013101 = 0.002476
  - fib_382_from_top = 0.015577 - (0.002476 * 0.382) = 0.01463
  - entry2 = max(0.015577 * 0.999, 0.01463) = max(0.01556, 0.01463) = 0.01556

Entry 3 (Sangat Konservatif):
  - fib_236_from_top = 0.015577 - (0.002476 * 0.236) = 0.01499
  - entry3 = max(0.015577 * 1.002, 0.01499) = max(0.01560, 0.01499) = 0.01560
```

## 🎛️ Konfigurasi di `config.py`

### Parameter yang Dapat Dikonfigurasi

```python
# Risk Management
SETUP_RISK_PERCENT = None  # Auto berdasarkan TRADING_STYLE
SETUP_TP_MULTIPLIERS = None  # Auto berdasarkan TRADING_STYLE

# Trading Style (mempengaruhi risk_percent dan tp_multipliers)
TRADING_STYLE = "SWING_TRADING"  # SCALPING, DAY_TRADING, INTRADAY_TRADING, SWING_TRADING, POSITION_TRADING
```

## 📝 Summary

**Parameter Utama yang Menentukan Entry Levels:**

1. ✅ **current_price** - Harga saat ini (wajib)
2. ✅ **support** - Level support (opsional, tapi sangat penting)
3. ✅ **resistance** - Level resistance (opsional, tapi sangat penting)
4. ✅ **signal** - Trading signal (1 = LONG, -1 = SHORT)
5. ✅ **fib_levels** - Fibonacci retracement levels (dihitung dari support/resistance)
6. ✅ **risk_percent** - Risk percentage untuk stop loss (default 2.5%)
7. ✅ **tp_multipliers** - Multiplier untuk take profit (default [1.5, 2.5, 3.5])

**Prioritas:**
- Jika ada **support & resistance**: Gunakan untuk Entry 2 dan Entry 3
- Jika ada **Fibonacci levels**: Gunakan untuk Entry 2 dan Entry 3 (lebih akurat)
- **Entry 1**: Selalu dekat dengan current price (agresif)
- **Entry 2**: Di support/resistance atau Fibonacci (konservatif - recommended)
- **Entry 3**: Di bawah support atau di atas resistance (sangat konservatif)

