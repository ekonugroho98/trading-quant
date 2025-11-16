# 📊 Coin Screening - Kriteria Filtering

## Overview

Sistem screening menggunakan **4 kriteria utama** untuk memfilter coins. Coin yang **lolos semua filter** akan masuk ke hasil akhir.

---

## 🚫 Terfilter (Filtered Out)

Coin yang **tidak memenuhi salah satu kriteria** akan di-filter out. Ada **4 jenis filter**:

### 1️⃣ **Volume Ratio Filter** 📊

**Kriteria:** `volume_ratio >= min_volume_ratio`

- **Default:** `min_volume_ratio = 0.3` (30%)
- **Artinya:** Volume saat ini harus >= 30% dari volume rata-rata
- **Tujuan:** Memastikan coin memiliki volume trading yang cukup (likuiditas baik)
- **Terfilter jika:** `volume_ratio < 0.3`

**Contoh:**
- ✅ Coin A: `volume_ratio = 0.5` → **LOLOS** (50% > 30%)
- ❌ Coin B: `volume_ratio = 0.2` → **TERFILTER** (20% < 30%)

---

### 2️⃣ **Price Change Filter** 📈

**Kriteria:** `min_price_change <= price_change_7d <= max_price_change`

- **Default:** `min_price_change = -80%`, `max_price_change = +200%`
- **Artinya:** Perubahan harga 7 hari terakhir harus antara -80% sampai +200%
- **Tujuan:** Menghindari coin dengan volatilitas ekstrem atau pump/dump
- **Terfilter jika:** `price_change_7d < -80%` **ATAU** `price_change_7d > +200%`

**Contoh:**
- ✅ Coin A: `price_change_7d = +50%` → **LOLOS** (-80% < 50% < +200%)
- ❌ Coin B: `price_change_7d = -90%` → **TERFILTER** (-90% < -80%)
- ❌ Coin C: `price_change_7d = +250%` → **TERFILTER** (+250% > +200%)

---

### 3️⃣ **RSI Range Filter** 📉 (Optional)

**Kriteria:** `rsi_range[0] <= rsi <= rsi_range[1]`

- **Default:** `rsi_range = None` (tidak ada filter RSI)
- **Jika di-set:** Coin harus memiliki RSI dalam range yang ditentukan
- **Tujuan:** Filter berdasarkan momentum (oversold/overbought)
- **Terfilter jika:** `rsi < rsi_range[0]` **ATAU** `rsi > rsi_range[1]`

**Contoh dengan `rsi_range = (30, 70)`:**
- ✅ Coin A: `rsi = 50` → **LOLOS** (30 < 50 < 70)
- ❌ Coin B: `rsi = 25` → **TERFILTER** (25 < 30)
- ❌ Coin C: `rsi = 75` → **TERFILTER** (75 > 70)

---

### 4️⃣ **Trade Direction Filter** 🎯

**Kriteria:** Berdasarkan `trade_direction` parameter

#### Jika `trade_direction = "long"`:
- **Kriteria:** `long_score > short_score`
- **Tujuan:** Hanya ambil coin yang lebih baik untuk LONG
- **Terfilter jika:** `long_score <= short_score`

#### Jika `trade_direction = "short"`:
- **Kriteria:** `short_score > long_score`
- **Tujuan:** Hanya ambil coin yang lebih baik untuk SHORT
- **Terfilter jika:** `short_score <= long_score`

#### Jika `trade_direction = "both"` (default):
- **Tidak ada filter:** Semua coin lolos (kecuali filter lainnya)
- **Gunakan:** `combined_score = max(long_score, short_score)`

**Contoh dengan `trade_direction = "long"`:**
- ✅ Coin A: `long_score = 0.8`, `short_score = 0.3` → **LOLOS** (0.8 > 0.3)
- ❌ Coin B: `long_score = 0.4`, `short_score = 0.6` → **TERFILTER** (0.4 <= 0.6)

---

## ✅ Lolos Filter (Passed Filters)

Coin yang **lolos semua 4 filter** akan masuk ke hasil akhir dan diurutkan berdasarkan `combined_score` (tertinggi ke terendah).

**Proses:**
1. ✅ Volume ratio >= 0.3
2. ✅ Price change 7d antara -80% sampai +200%
3. ✅ RSI dalam range (jika di-set)
4. ✅ Trade direction sesuai (jika di-set)

**Hasil:** Coin diurutkan berdasarkan `combined_score` dan diambil top N (default: top 10)

---

## 📊 Statistik Screening

Dari output:
```
📊 Statistik Screening:
   ✅ Metrics berhasil dihitung: 200 coins
   ❌ Metrics gagal dihitung: 0 coins
   🚫 Terfilter: 65 coins
   ✅ Lolos filter: 135 coins
```

**Penjelasan:**
- **Metrics berhasil dihitung:** 200 coins → Semua coin berhasil dihitung metrics-nya
- **Metrics gagal dihitung:** 0 coins → Tidak ada coin yang gagal
- **Terfilter:** 65 coins → 65 coins tidak memenuhi salah satu kriteria filter
- **Lolos filter:** 135 coins → 135 coins lolos semua filter dan masuk hasil

**Rumus:** `Metrics berhasil = Terfilter + Lolos filter`
- 200 = 65 + 135 ✅

---

## 🔧 Customize Filters

Anda bisa customize filter saat memanggil `screen_coins()`:

```python
results = screen_coins(
    coins=None,  # Gunakan default (200 coins dari Binance)
    days=90,
    min_volume_ratio=0.5,      # Lebih ketat: 50% (default: 30%)
    min_price_change=-50.0,     # Lebih ketat: -50% (default: -80%)
    max_price_change=100.0,     # Lebih ketat: +100% (default: +200%)
    rsi_range=(30, 70),         # Filter RSI 30-70 (default: None)
    trade_direction="long",     # Hanya LONG (default: "both")
    top_n=20                    # Top 20 coins (default: 10)
)
```

---

## 🔄 Adaptive Filtering

Jika tidak ada coin yang lolos filter, sistem akan **otomatis relax filters**:

1. **Volume ratio:** 50% dari original (0.3 → 0.15)
2. **Price change:** 50% lebih longgar (-80% → -120%, +200% → +300%)
3. **RSI range:** Tetap sama
4. **Trade direction:** Tetap sama

Jika masih tidak ada hasil, sistem akan mengembalikan **semua coin dengan score terbaik** (tanpa filter).

---

## 📝 Contoh Lengkap

**Scenario:** Screening 200 coins dengan default filters

1. **200 coins** di-screening
2. **200 coins** berhasil dihitung metrics
3. **65 coins** terfilter karena:
   - 20 coins: Volume ratio < 0.3
   - 30 coins: Price change di luar range -80% sampai +200%
   - 10 coins: Trade direction tidak sesuai (long_score <= short_score)
   - 5 coins: Kombinasi beberapa filter
4. **135 coins** lolos semua filter
5. **Top 10 coins** dikembalikan (sorted by combined_score)

---

## 🎯 Tips

1. **Volume ratio rendah:** Coin kurang likuid → Risiko tinggi
2. **Price change ekstrem:** Kemungkinan pump/dump → Hindari
3. **RSI range:** Gunakan untuk momentum trading (30-70 = healthy)
4. **Trade direction:** Pilih sesuai strategi (long/short/both)

