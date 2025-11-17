# 🔵 Binance Futures Auto-Configuration

## 📋 Overview

Sistem sekarang **otomatis mengaktifkan** derivatives modeling dan mengatur strategies ke long-short mode ketika menggunakan **Binance Futures API**.

---

## ✅ Fitur Auto-Configuration

Ketika `BINANCE_API_TYPE = "futures"`, sistem akan **otomatis**:

1. ✅ **Enable Derivatives Modeling**
   - `ENABLE_DERIVATIVES_MODELING = True`
   - `ENABLE_OPTIONS_STRATEGIES = True`

2. ✅ **Set Strategies ke Long-Short Mode**
   - `PAIRS_LONG_ONLY = False` (long-short untuk futures)
   - `STAT_ARB_LONG_ONLY = False` (long-short untuk futures)

---

## 🚀 Cara Menggunakan

### 1. Set Binance API Type ke Futures

**Option A: Via .env file**
```bash
BINANCE_API_TYPE=futures
```

**Option B: Via config.py**
```python
BINANCE_API_TYPE = "futures"
```

### 2. Sistem Akan Auto-Configure

Saat file `config.py` di-load, sistem akan otomatis:
- Detect `BINANCE_API_TYPE = "futures"`
- Enable derivatives modeling
- Set strategies ke long-short mode
- Print konfirmasi di console

**Output Console:**
```
🔵 [AUTO-CONFIG] Binance Futures detected - Auto-configuring:
   ✅ Derivatives modeling: ENABLED
   ✅ Options strategies: ENABLED
   ✅ Pairs trading: Long-Short mode
   ✅ Statistical arbitrage: Long-Short mode
✅ [AUTO-CONFIG] Konfigurasi Futures selesai
```

---

## 📊 Konfigurasi yang Di-Auto-Set

### Untuk Futures (`BINANCE_API_TYPE = "futures"`):

| Setting | Value | Keterangan |
|---------|-------|------------|
| `ENABLE_DERIVATIVES_MODELING` | `True` | Auto-enabled |
| `ENABLE_OPTIONS_STRATEGIES` | `True` | Auto-enabled |
| `PAIRS_LONG_ONLY` | `False` | Long-short mode |
| `STAT_ARB_LONG_ONLY` | `False` | Long-short mode |

### Untuk Spot (`BINANCE_API_TYPE = "spot"`):

| Setting | Value | Keterangan |
|---------|-------|------------|
| `ENABLE_DERIVATIVES_MODELING` | Manual | User set sendiri |
| `ENABLE_OPTIONS_STRATEGIES` | Manual | User set sendiri |
| `PAIRS_LONG_ONLY` | `True` | Long-only mode (default) |
| `STAT_ARB_LONG_ONLY` | `True` | Long-only mode (default) |

---

## 🔧 Manual Override

Jika ingin **override** auto-config, set nilai **setelah** section `AUTO-CONFIGURATION EXECUTION` di `config.py`:

```python
# Setelah AUTO-CONFIGURATION EXECUTION section

# Contoh: Disable derivatives modeling meskipun menggunakan futures
ENABLE_DERIVATIVES_MODELING = False

# Contoh: Set pairs trading ke long-only meskipun futures
PAIRS_LONG_ONLY = True
```

---

## 📝 Contoh Konfigurasi

### Scenario 1: Futures Trading dengan Auto-Config

```python
# .env atau config.py
BINANCE_API_TYPE = "futures"

# Sistem akan otomatis:
# - Enable derivatives modeling
# - Enable options strategies
# - Set pairs trading ke long-short
# - Set statistical arbitrage ke long-short
```

### Scenario 2: Futures Trading dengan Manual Override

```python
# .env atau config.py
BINANCE_API_TYPE = "futures"

# Di akhir config.py (setelah AUTO-CONFIGURATION EXECUTION)
ENABLE_DERIVATIVES_MODELING = False  # Override: disable derivatives
PAIRS_LONG_ONLY = True  # Override: use long-only untuk pairs trading
```

### Scenario 3: Spot Trading (Default)

```python
# .env atau config.py
BINANCE_API_TYPE = "spot"  # atau tidak di-set (default = "spot")

# Sistem akan:
# - Derivatives modeling: Manual (user set sendiri)
# - Pairs trading: Long-only (default)
# - Statistical arbitrage: Long-only (default)
```

---

## 🎯 Benefits

1. **Kemudahan**: Tidak perlu manual enable/disable setiap kali switch antara spot dan futures
2. **Konsistensi**: Konfigurasi otomatis sesuai dengan jenis trading
3. **Fleksibilitas**: Masih bisa manual override jika diperlukan
4. **Safety**: Default spot trading tetap long-only (aman untuk spot trading)

---

## ⚠️ Catatan Penting

1. **Auto-config dijalankan saat file config.py di-load**
   - Pastikan `BINANCE_API_TYPE` sudah di-set sebelum import config

2. **Manual override harus setelah AUTO-CONFIGURATION EXECUTION**
   - Jika set sebelum auto-config, akan ter-override

3. **Environment Variable Priority**
   - `.env` file akan di-load terlebih dahulu
   - Nilai di `.env` akan override nilai di `config.py`

4. **Strategies yang Terpengaruh**
   - Hanya **Pairs Trading** dan **Statistical Arbitrage** yang auto-set
   - **Grid Trading** dan **DCA** tetap long-only (cocok untuk spot dan futures)

---

## 🔍 Debugging

Jika auto-config tidak bekerja, check:

1. **BINANCE_API_TYPE sudah di-set?**
   ```python
   print(f"BINANCE_API_TYPE: {BINANCE_API_TYPE}")
   ```

2. **Console output menunjukkan auto-config?**
   - Harus ada message `[AUTO-CONFIG]` di console

3. **Nilai sudah ter-override manual?**
   - Check apakah ada set manual setelah auto-config section

---

## 📚 Related Documentation

- [Binance Futures API Setup](./BINANCE_FUTURES_API_CURL.md)
- [Trading Algorithm Evaluation](./TRADING_ALGORITHM_EVALUATION.md)
- [Derivatives Modeling](./IMPLEMENTATION_COMPLETE.md#2-derivatives-modeling)

---

**Last Updated:** 2025-01-27  
**Status:** ✅ Implemented

