import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, accuracy_score, classification_report
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import glob
import os

# ============================================
# QUANT MODEL: PREDICTIVE MACHINE LEARNING
# Sesuai dengan komponen Quant Trading:
# 1. Data Historis (Historical Data)
# 2. Feature Engineering
# 3. Model Statistik/ML
# 4. Signal Generator (Beli/Jual dengan probabilitas)
# 5. Backtesting (Evaluasi matematis)
# ============================================

# Konfigurasi
USE_CSV_DATA = True
CSV_FILE = None
PREDICTION_METHOD = "ensemble"  # "linear", "random_forest", "moving_avg", "ensemble"
USE_CLASSIFICATION = True  # True = prediksi Beli/Jual, False = prediksi harga

def load_data(csv_file=None):
    """Load data untuk prediksi"""
    if csv_file is None:
        # Cari file CSV terbaru (prioritas: historical, lalu data real-time)
        # Pattern lebih fleksibel: btc_*.csv, btcusd_*.csv, atau *_historical_*.csv
        csv_files = []
        # Cari file historical dulu (prioritas)
        csv_files.extend(glob.glob("*_historical_*.csv"))
        # Cari file dengan pattern btc
        csv_files.extend(glob.glob("btc*.csv"))
        # Cari file dengan pattern umum
        if not csv_files:
            csv_files.extend(glob.glob("*_*.csv"))  # Fallback: semua file dengan underscore
        
        if not csv_files:
            raise FileNotFoundError("Tidak ada file CSV ditemukan. Jalankan get_data.py atau get_historical_data.py terlebih dahulu.")
        csv_file = max(csv_files, key=os.path.getctime)
        print(f"Menggunakan file: {csv_file}")
    
    df = pd.read_csv(csv_file)
    
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        
        if 'Close' in df.columns:
            data = df[['Close']].copy()
        elif 'price' in df.columns:
            # Resample tick data
            data = pd.DataFrame()
            data['Close'] = df['price'].resample('1h').last()
        else:
            raise ValueError("Kolom 'Close' atau 'price' tidak ditemukan")
    else:
        raise ValueError("Kolom 'date' tidak ditemukan")
    
    data = data.dropna()
    return data

def create_features(df, lookback=20):
    """Buat fitur untuk prediksi"""
    features = pd.DataFrame(index=df.index)
    
    # Harga historis
    features['Close'] = df['Close']
    features['Return'] = df['Close'].pct_change()
    
    # Moving Averages
    features['MA_5'] = df['Close'].rolling(window=5).mean()
    features['MA_10'] = df['Close'].rolling(window=10).mean()
    features['MA_20'] = df['Close'].rolling(window=20).mean()
    
    # Volatilitas
    features['Volatility'] = df['Close'].rolling(window=10).std()
    
    # Momentum
    features['Momentum_5'] = df['Close'].pct_change(5)
    features['Momentum_10'] = df['Close'].pct_change(10)
    
    # RSI (Relative Strength Index)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    features['RSI'] = 100 - (100 / (1 + rs))
    
    # Bollinger Bands
    features['BB_Middle'] = df['Close'].rolling(window=20).mean()
    bb_std = df['Close'].rolling(window=20).std()
    features['BB_Upper'] = features['BB_Middle'] + (bb_std * 2)
    features['BB_Lower'] = features['BB_Middle'] - (bb_std * 2)
    features['BB_Width'] = features['BB_Upper'] - features['BB_Lower']
    
    # Harga relatif terhadap MA
    features['Price_MA5_Ratio'] = df['Close'] / features['MA_5']
    features['Price_MA20_Ratio'] = df['Close'] / features['MA_20']
    
    # Lag features (harga kemarin, 2 hari lalu, dll)
    for lag in [1, 2, 3, 5]:
        features[f'Close_Lag_{lag}'] = df['Close'].shift(lag)
    
    return features.dropna()

def predict_linear_regression(features, target_col='Close', test_size=0.2):
    """Prediksi menggunakan Linear Regression"""
    # Siapkan data
    feature_cols = [col for col in features.columns if col != target_col]
    X = features[feature_cols].values
    y = features[target_col].values
    
    # Split data (80% training, 20% validation)
    split_idx = int(len(X) * (1 - test_size))
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    # Normalisasi
    scaler_X = StandardScaler()
    scaler_y = StandardScaler()
    X_train_scaled = scaler_X.fit_transform(X_train)
    X_test_scaled = scaler_X.transform(X_test)
    y_train_scaled = scaler_y.fit_transform(y_train.reshape(-1, 1)).ravel()
    
    # Training
    model = LinearRegression()
    model.fit(X_train_scaled, y_train_scaled)
    
    # Prediksi validation
    y_pred_scaled = model.predict(X_test_scaled)
    y_pred = scaler_y.inverse_transform(y_pred_scaled.reshape(-1, 1)).ravel()
    
    # Evaluasi
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    
    # Prediksi untuk hari berikutnya (menggunakan data terakhir)
    X_last = X[-1:].reshape(1, -1)
    X_last_scaled = scaler_X.transform(X_last)
    y_next_scaled = model.predict(X_last_scaled)
    y_next = scaler_y.inverse_transform(y_next_scaled.reshape(-1, 1))[0][0]
    
    return {
        'prediction': y_next,
        'mae': mae,
        'rmse': rmse,
        'model': model,
        'scaler_X': scaler_X,
        'scaler_y': scaler_y,
        'feature_cols': feature_cols
    }

def predict_random_forest(features, df, use_classification=True, test_size=0.2):
    """
    Prediksi menggunakan RandomForest (sesuai contoh di Quant Model)
    - Regressor: prediksi harga
    - Classifier: prediksi Beli/Jual dengan probabilitas
    """
    current_price = df['Close'].iloc[-1]
    
    if use_classification:
        # Classification: Prediksi Beli (1) atau Jual (0)
        # Target: 1 jika harga naik besok, 0 jika turun
        target = (df['Close'].shift(-1) > df['Close']).astype(int)
        target = target[features.index]
        
        feature_cols = [col for col in features.columns if col != 'Close']
        X = features[feature_cols].values
        y = target.values
        
        # Hapus NaN
        valid_idx = ~np.isnan(y)
        X = X[valid_idx]
        y = y[valid_idx]
        
        if len(X) < 50:
            raise ValueError("Data terlalu sedikit untuk RandomForest")
        
        # Split data
        split_idx = int(len(X) * (1 - test_size))
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
        
        # Training
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)
        
        # Prediksi validation
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)
        
        # Evaluasi
        accuracy = accuracy_score(y_test, y_pred)
        
        # Prediksi untuk hari berikutnya
        X_last = X[-1:].reshape(1, -1)
        signal_proba = model.predict_proba(X_last)[0]
        signal = model.predict(X_last)[0]
        
        signal_text = "BELI" if signal == 1 else "JUAL"
        buy_probability = signal_proba[1] * 100  # Probabilitas BELI
        
        return {
            'signal': signal_text,
            'buy_probability': buy_probability,
            'sell_probability': signal_proba[0] * 100,
            'accuracy': accuracy,
            'model': model,
            'feature_cols': feature_cols,
            'current_price': current_price
        }
    else:
        # Regression: Prediksi harga
        feature_cols = [col for col in features.columns if col != 'Close']
        X = features[feature_cols].values
        y = features['Close'].values
        
        # Split data
        split_idx = int(len(X) * (1 - test_size))
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
        
        # Training
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)
        
        # Prediksi validation
        y_pred = model.predict(X_test)
        
        # Evaluasi
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        
        # Prediksi untuk hari berikutnya
        X_last = X[-1:].reshape(1, -1)
        prediction = model.predict(X_last)[0]
        
        return {
            'prediction': prediction,
            'mae': mae,
            'rmse': rmse,
            'model': model,
            'feature_cols': feature_cols,
            'current_price': current_price
        }

def predict_moving_average(df, window=20):
    """Prediksi menggunakan Moving Average dengan momentum"""
    current_price = df['Close'].iloc[-1]
    ma = df['Close'].rolling(window=window).mean().iloc[-1]
    momentum = df['Close'].pct_change(window).iloc[-1]
    
    # Prediksi = MA + (momentum * current_price)
    prediction = ma + (momentum * current_price * 0.5)  # Dampen momentum
    
    return {
        'prediction': prediction,
        'current_price': current_price,
        'ma': ma,
        'momentum': momentum
    }

def predict_ensemble(features, df, use_classification=True):
    """Prediksi menggunakan ensemble method (gabungan beberapa metode)"""
    results = {}
    
    # Method 1: RandomForest (prioritas jika classification)
    if use_classification:
        try:
            rf_result = predict_random_forest(features, df, use_classification=True)
            results['rf'] = rf_result
        except Exception as e:
            print(f"⚠️  RandomForest error: {e}, menggunakan metode lain")
    
    # Method 2: Linear Regression
    try:
        lr_result = predict_linear_regression(features)
        results['lr'] = lr_result
    except Exception as e:
        print(f"⚠️  Linear Regression error: {e}")
    
    # Method 3: Moving Average
    ma_result = predict_moving_average(df)
    results['ma'] = ma_result
    
    if use_classification and 'rf' in results:
        # Untuk classification, gunakan RandomForest sebagai utama
        return {
            'signal': results['rf']['signal'],
            'buy_probability': results['rf']['buy_probability'],
            'sell_probability': results['rf']['sell_probability'],
            'accuracy': results['rf']['accuracy'],
            'current_price': results['rf']['current_price'],
            'model_type': 'RandomForestClassifier'
        }
    else:
        # Untuk regression, ensemble semua metode
        lr_weight = 0.5 if 'lr' in results else 0
        ma_weight = 0.5 if 'lr' in results else 1.0
        
        ensemble_pred = (results['lr']['prediction'] * lr_weight) + (results['ma']['prediction'] * ma_weight)
        confidence_interval = results['lr']['rmse'] if 'lr' in results else results['ma']['prediction'] * 0.02
        
        return {
            'prediction': ensemble_pred,
            'lr_prediction': results['lr']['prediction'] if 'lr' in results else None,
            'ma_prediction': results['ma']['prediction'],
            'confidence_interval': confidence_interval,
            'lr_mae': results['lr']['mae'] if 'lr' in results else None,
            'lr_rmse': results['lr']['rmse'] if 'lr' in results else None,
            'current_price': results['ma']['current_price']
        }

def backtest_strategy(features, df, model_result, use_classification=True):
    """
    Backtesting: Evaluasi matematis strategi
    - accuracy_score (untuk classification)
    - Expected Value
    - Sharpe Ratio
    """
    print("\n" + "=" * 60)
    print("📊 [5] BACKTESTING")
    print("=" * 60)
    print("Mengukur apakah strategi ini menguntungkan...")
    
    if use_classification and 'accuracy' in model_result:
        # Classification backtesting
        accuracy = model_result['accuracy']
        print(f"✅ Accuracy Score: {accuracy*100:.2f}%")
        print(f"   (Menggunakan accuracy_score dari sklearn)")
        
        # Hitung expected value dari probabilitas
        buy_prob = model_result.get('buy_probability', 50) / 100
        sell_prob = model_result.get('sell_probability', 50) / 100
        
        # Simulasi return jika ikuti sinyal berdasarkan probabilitas
        returns = df['Close'].pct_change().dropna()
        
        if len(returns) > 10:
            # Hitung expected return berdasarkan probabilitas
            # Expected return = (buy_prob * avg_positive_return) - (sell_prob * avg_negative_return)
            positive_returns = returns[returns > 0]
            negative_returns = returns[returns < 0]
            
            if len(positive_returns) > 0 and len(negative_returns) > 0:
                avg_positive = positive_returns.mean()
                avg_negative = abs(negative_returns.mean())
                
                expected_return = (buy_prob * avg_positive) - (sell_prob * avg_negative)
                expected_value = expected_return * 100
                
                # Sharpe Ratio
                strategy_returns = []
                for ret in returns[-50:]:  # Ambil 50 data terakhir
                    if buy_prob > 0.5:
                        strategy_returns.append(ret)  # Ikuti sinyal BELI
                    else:
                        strategy_returns.append(-ret)  # Ikuti sinyal JUAL
                
                if len(strategy_returns) > 0 and np.std(strategy_returns) > 0:
                    sharpe_ratio = (np.mean(strategy_returns) / np.std(strategy_returns)) * np.sqrt(252)
                else:
                    sharpe_ratio = 0
                
                print(f"📈 Expected Value: {expected_value:.2f}%")
                print(f"   (Berdasarkan probabilitas dan historical returns)")
                print(f"📊 Sharpe Ratio: {sharpe_ratio:.2f}")
                print(f"   (Sharpe > 1 = bagus, > 2 = sangat bagus)")
                
                return {
                    'accuracy': accuracy,
                    'expected_value': expected_value,
                    'sharpe_ratio': sharpe_ratio
                }
    else:
        # Regression backtesting
        if 'lr_mae' in model_result and model_result['lr_mae']:
            print(f"✅ MAE (Mean Absolute Error): ${model_result['lr_mae']:,.2f}")
            print(f"✅ RMSE (Root Mean Squared Error): ${model_result['lr_rmse']:,.2f}")
            
            # Hitung expected value dari prediksi
            current_price = model_result['current_price']
            predicted_price = model_result['prediction']
            expected_return = ((predicted_price - current_price) / current_price) * 100
            
            print(f"📈 Expected Return: {expected_return:.2f}%")
            print(f"   (Berdasarkan prediksi harga)")
            
            # Bisa tambah perhitungan return (seperti di gambar)
            returns = df['Close'].pct_change().dropna()
            if len(returns) > 0:
                avg_return = returns.mean() * 100
                print(f"📊 Average Historical Return: {avg_return:.2f}%")
            
            return {
                'mae': model_result['lr_mae'],
                'rmse': model_result['lr_rmse'],
                'expected_return': expected_return
            }
    
    print("⚠️  Backtesting tidak bisa dilakukan dengan data yang tersedia")
    return {}

def main():
    print("=" * 60)
    print("⚙️  QUANT MODEL: PREDICTIVE MACHINE LEARNING")
    print("=" * 60)
    print()
    
    # ============================================
    # 1. DATA HISTORIS (Historical Data)
    # ============================================
    print("📊 [1] DATA HISTORIS")
    print("-" * 60)
    try:
        data = load_data(CSV_FILE)
        print(f"✅ Data dimuat: {len(data)} records")
        print(f"   Periode: {data.index.min()} sampai {data.index.max()}")
        print(f"   Sumber: {'CSV' if USE_CSV_DATA else 'yfinance'}")
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # ============================================
    # 2. FEATURE ENGINEERING
    # ============================================
    print("\n🔧 [2] FEATURE ENGINEERING")
    print("-" * 60)
    print("Menyusun pola matematis dari harga...")
    features = create_features(data)
    print(f"✅ Fitur dibuat: {len(features.columns)} fitur")
    feature_examples = ['Return', 'MA_5', 'RSI', 'Volatility', 'Momentum_5']
    available_features = [f for f in feature_examples if f in features.columns]
    print(f"   Contoh fitur: {', '.join(available_features)}")
    
    if len(features) < 50:
        print("⚠️  PERINGATAN: Data terlalu sedikit untuk prediksi yang akurat!")
        print("   Minimal butuh 50-100 data points")
        if len(features) < 20:
            print("❌ Data tidak cukup, tidak bisa melanjutkan prediksi")
            return
    
    # ============================================
    # 3. MODEL STATISTIK / ML
    # ============================================
    print(f"\n🤖 [3] MODEL STATISTIK / ML")
    print("-" * 60)
    print(f"Metode: {PREDICTION_METHOD}")
    if USE_CLASSIFICATION:
        print(f"Mode: Classification (Beli/Jual dengan probabilitas)")
    else:
        print(f"Mode: Regression (Prediksi harga)")
    
    result = None
    if PREDICTION_METHOD == "linear":
        result = predict_linear_regression(features)
        print(f"✅ Model: LinearRegression")
        print(f"   Prediksi harga: ${result['prediction']:,.2f}")
        
    elif PREDICTION_METHOD == "random_forest":
        result = predict_random_forest(features, data, use_classification=USE_CLASSIFICATION)
        if USE_CLASSIFICATION:
            print(f"✅ Model: RandomForestClassifier")
            print(f"   Signal: {result['signal']}")
            print(f"   Probabilitas BELI: {result['buy_probability']:.2f}%")
            print(f"   Probabilitas JUAL: {result['sell_probability']:.2f}%")
        else:
            print(f"✅ Model: RandomForestRegressor")
            print(f"   Prediksi harga: ${result['prediction']:,.2f}")
        
    elif PREDICTION_METHOD == "moving_avg":
        result = predict_moving_average(data)
        print(f"✅ Model: Moving Average + Momentum")
        print(f"   Prediksi harga: ${result['prediction']:,.2f}")
        
    elif PREDICTION_METHOD == "ensemble":
        result = predict_ensemble(features, data, use_classification=USE_CLASSIFICATION)
        if USE_CLASSIFICATION and 'signal' in result:
            print(f"✅ Model: Ensemble (RandomForestClassifier)")
            print(f"   Signal: {result['signal']}")
            print(f"   Probabilitas BELI: {result['buy_probability']:.2f}%")
            print(f"   Probabilitas JUAL: {result['sell_probability']:.2f}%")
        else:
            print(f"✅ Model: Ensemble (LinearRegression + MovingAverage)")
            if result.get('lr_prediction'):
                print(f"   - Linear Regression: ${result['lr_prediction']:,.2f}")
            print(f"   - Moving Average: ${result['ma_prediction']:,.2f}")
            print(f"   - Ensemble: ${result['prediction']:,.2f}")
    
    if result is None:
        print("❌ Error: Tidak ada hasil prediksi")
        return
    
    # ============================================
    # 4. SIGNAL GENERATOR
    # ============================================
    print(f"\n📡 [4] SIGNAL GENERATOR")
    print("-" * 60)
    print("Output 'Beli / Jual' berdasarkan probabilitas:")
    
    current_price = result.get('current_price', data['Close'].iloc[-1])
    
    if USE_CLASSIFICATION and 'signal' in result:
        # Classification: Signal dengan probabilitas
        signal = result['signal']
        buy_prob = result.get('buy_probability', 0)
        sell_prob = result.get('sell_probability', 0)
        
        print(f"   Prediksi besok: {signal}")
        print(f"   Probabilitas BELI: {buy_prob:.2f}%")
        print(f"   Probabilitas JUAL: {sell_prob:.2f}%")
        
        if buy_prob > 60:
            print(f"   💪 Signal Kuat: {signal} (Probabilitas tinggi)")
        elif buy_prob > 50:
            print(f"   ⚠️  Signal Lemah: {signal} (Probabilitas rendah)")
        else:
            print(f"   ⚠️  Signal Lemah: {signal} (Probabilitas rendah)")
    else:
        # Regression: Convert ke signal
        predicted_price = result.get('prediction', current_price)
        change = predicted_price - current_price
        change_pct = (change / current_price) * 100
        
        print(f"   Harga saat ini: ${current_price:,.2f}")
        print(f"   Prediksi besok: ${predicted_price:,.2f}")
        print(f"   Perubahan: {change_pct:+.2f}%")
        
        if change_pct > 1:
            signal = "BELI"
            prob = min(50 + (change_pct * 10), 95)
        elif change_pct < -1:
            signal = "JUAL"
            prob = min(50 + (abs(change_pct) * 10), 95)
        else:
            signal = "HOLD"
            prob = 50
        
        print(f"   Signal: {signal}")
        print(f"   Confidence: {prob:.1f}%")
    
    # ============================================
    # 5. BACKTESTING
    # ============================================
    backtest_result = backtest_strategy(features, data, result, use_classification=USE_CLASSIFICATION)
    
    # ============================================
    # RINGKASAN
    # ============================================
    print("\n" + "=" * 60)
    print("RINGKASAN QUANT MODEL")
    print("=" * 60)
    print(f"📊 Data Historis: {len(data)} records")
    print(f"🔧 Feature Engineering: {len(features.columns)} fitur")
    print(f"🤖 Model: {PREDICTION_METHOD}")
    
    if USE_CLASSIFICATION and 'signal' in result:
        print(f"📡 Signal: {result['signal']} (Prob: {result.get('buy_probability', 0):.1f}%)")
    else:
        predicted_price = result.get('prediction', current_price)
        print(f"📡 Prediksi Harga: ${predicted_price:,.2f}")
    
    if backtest_result:
        if 'accuracy' in backtest_result:
            print(f"📈 Accuracy: {backtest_result['accuracy']*100:.2f}%")
        if 'expected_value' in backtest_result:
            print(f"📈 Expected Value: {backtest_result['expected_value']:.2f}%")
        if 'sharpe_ratio' in backtest_result:
            print(f"📊 Sharpe Ratio: {backtest_result['sharpe_ratio']:.2f}")
    
    print("\n" + "=" * 60)
    print("CATATAN PENTING")
    print("=" * 60)
    print("⚠️  Prediksi ini hanya untuk referensi, bukan saran trading!")
    print("⚠️  Cryptocurrency sangat volatile, prediksi bisa meleset jauh")
    print("⚠️  Selalu gunakan risk management")
    print("⚠️  Pastikan data up-to-date untuk prediksi yang lebih akurat")

if __name__ == "__main__":
    main()

