import os
import sys

# Add project root to Python path to enable src imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Change working directory to project root to ensure CSV files are found
# CSV files are created in project root, not in src/ directory
if os.getcwd() != project_root:
    os.chdir(project_root)
    print(f"🔍 [DEBUG] Changed working directory to project root: {project_root}")

import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, accuracy_score, classification_report
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import glob

# ============================================
# QUANT MODEL: PREDICTIVE MACHINE LEARNING
# Sesuai dengan komponen Quant Trading:
# 1. Data Historis (Historical Data)
# 2. Feature Engineering
# 3. Model Statistik/ML
# 4. Signal Generator (Beli/Jual dengan probabilitas)
# 5. Backtesting (Evaluasi matematis)
# ============================================

# Import konfigurasi dari config.py
try:
    from src.utils.config import (
        PREDICTION_METHOD, USE_CLASSIFICATION, ML_MODELS_CONFIG,
        USE_CSV_DATA, CSV_FILE
    )
except ImportError:
    # Fallback jika config.py tidak ada
    print("⚠️  config.py tidak ditemukan, menggunakan konfigurasi default")
    PREDICTION_METHOD = "ensemble"
    USE_CLASSIFICATION = True
    ML_MODELS_CONFIG = [
        {"model": "random_forest", "weight": 0.5, "enabled": True},
        {"model": "linear", "weight": 0.3, "enabled": True},
        {"model": "moving_avg", "weight": 0.2, "enabled": True}
    ]
    USE_CSV_DATA = True
    CSV_FILE = None
except Exception as e:
    print(f"⚠️  Error loading config: {e}, menggunakan default")
    PREDICTION_METHOD = "ensemble"
    USE_CLASSIFICATION = True
    ML_MODELS_CONFIG = [
        {"model": "random_forest", "weight": 0.5, "enabled": True},
        {"model": "linear", "weight": 0.3, "enabled": True},
        {"model": "moving_avg", "weight": 0.2, "enabled": True}
    ]
    USE_CSV_DATA = True
    CSV_FILE = None

# Global variable untuk menyimpan nama file CSV yang digunakan
used_csv_file_prediction = None

def load_data(csv_file=None):
    """Load data untuk prediksi"""
    global used_csv_file_prediction
    
    if csv_file is None:
        # Cari file CSV terbaru (prioritas: historical, lalu data real-time)
        # Pattern lebih fleksibel: btc_*.csv, btcusd_*.csv, atau *_historical_*.csv
        csv_files = []
        
        print(f"🔍 [DEBUG] Searching for CSV files...")
        print(f"   Current directory: {os.getcwd()}")
        print(f"   Project root: {project_root}")
        
        # Pastikan kita mencari di project root
        # Change to project root directory untuk mencari CSV files
        original_cwd = os.getcwd()
        search_dir = project_root if project_root else os.getcwd()
        
        if os.getcwd() != search_dir:
            os.chdir(search_dir)
            print(f"   Changed to search directory: {search_dir}")
        
        print(f"   Searching in: {os.getcwd()}")
        
        # Cari file historical dulu (prioritas)
        historical_files = glob.glob("*_historical_*.csv")
        csv_files.extend(historical_files)
        print(f"   Found {len(historical_files)} historical CSV files: {historical_files}")
        
        # Cari file dengan pattern umum (tanpa underscore requirement)
        if not csv_files:
            all_csv = glob.glob("*.csv")
            # Filter out common non-data files
            all_csv = [f for f in all_csv if not f.startswith('.') and 'test' not in f.lower()]
            csv_files.extend(all_csv)
            print(f"   Found {len(all_csv)} CSV files (all): {all_csv}")
        
        # Restore original directory jika berbeda
        if original_cwd != os.getcwd():
            os.chdir(original_cwd)
        
        if not csv_files:
            # List all files in current directory for debugging
            all_files = os.listdir('.')
            csv_in_dir = [f for f in all_files if f.endswith('.csv')]
            print(f"   ⚠️  No CSV files found with patterns!")
            print(f"   All CSV files in directory: {csv_in_dir}")
            raise FileNotFoundError("Tidak ada file CSV ditemukan. Jalankan get_data.py atau get_historical_data.py terlebih dahulu.")
        
        csv_file = max(csv_files, key=os.path.getctime)
        print(f"✅ Menggunakan file CSV terbaru: {csv_file}")
        print(f"   File size: {os.path.getsize(csv_file):,} bytes")
        print(f"   Modified time: {datetime.fromtimestamp(os.path.getmtime(csv_file))}")
    
    # Simpan nama file untuk dihapus nanti
    used_csv_file_prediction = csv_file
    
    df = pd.read_csv(csv_file)
    
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        
        if 'Close' in df.columns:
            # Pastikan Volume, High, Low juga diambil jika tersedia (untuk VWAP dan features lainnya)
            cols_to_use = ['Close']
            if 'Volume' in df.columns:
                cols_to_use.append('Volume')
            if 'High' in df.columns:
                cols_to_use.append('High')
            if 'Low' in df.columns:
                cols_to_use.append('Low')
            
            data = df[cols_to_use].copy()
            
            # Tambahkan Volume = 0 jika tidak ada
            if 'Volume' not in data.columns:
                data['Volume'] = 0
                print(f"⚠️  Volume tidak tersedia, akan menggunakan Volume = 0")
            else:
                print(f"✅ Data dengan Volume: {len(data)} records")
            
            # Tambahkan High/Low = Close jika tidak ada (untuk VWAP)
            if 'High' not in data.columns:
                data['High'] = data['Close']
            if 'Low' not in data.columns:
                data['Low'] = data['Close']
        elif 'price' in df.columns:
            # Resample tick data
            data = pd.DataFrame()
            data['Close'] = df['price'].resample('1h').last()
            # Cek apakah ada amount/volume
            if 'amount' in df.columns:
                data['Volume'] = df['amount'].resample('1h').sum()
            else:
                data['Volume'] = 0
        else:
            raise ValueError("Kolom 'Close' atau 'price' tidak ditemukan")
    else:
        raise ValueError("Kolom 'date' tidak ditemukan")
    
    data = data.dropna()
    return data

def create_features(df, lookback=20, use_enhanced=True):
    """
    Buat fitur untuk prediksi dengan enhanced features
    
    Args:
        df: DataFrame dengan price data
        lookback: Lookback window untuk beberapa indicators
        use_enhanced: Gunakan enhanced feature engineering
    """
    features = pd.DataFrame(index=df.index)
    
    # Harga historis
    features['Close'] = df['Close']
    features['Return'] = df['Close'].pct_change()
    
    # Moving Averages (multiple windows)
    for window in [5, 10, 20, 50, 100]:
        if len(df) >= window:
            features[f'MA_{window}'] = df['Close'].rolling(window=window).mean()
            features[f'EMA_{window}'] = df['Close'].ewm(span=window, adjust=False).mean()
    
    # Volatilitas (multiple windows)
    for window in [10, 20, 50]:
        if len(df) >= window:
            features[f'Volatility_{window}'] = df['Close'].rolling(window=window).std()
            if f'MA_{window}' in features.columns:
                features[f'Volatility_Ratio_{window}'] = features[f'Volatility_{window}'] / features[f'MA_{window}']
    
    # Momentum (multiple periods)
    for period in [1, 3, 5, 10, 20]:
        features[f'Momentum_{period}'] = df['Close'].pct_change(period)
    
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
    features['BB_Position'] = (df['Close'] - features['BB_Lower']) / (features['BB_Upper'] - features['BB_Lower'])
    
    # Harga relatif terhadap MA
    for ma_col in ['MA_5', 'MA_10', 'MA_20', 'MA_50']:
        if ma_col in features.columns:
            features[f'Price_{ma_col}_Ratio'] = df['Close'] / features[ma_col]
    
    # Lag features (harga kemarin, 2 hari lalu, dll)
    for lag in [1, 2, 3, 5, 10]:
        features[f'Close_Lag_{lag}'] = df['Close'].shift(lag)
        features[f'Return_Lag_{lag}'] = features['Return'].shift(lag)
    
    # Volume-based features (PENTING untuk akurasi!)
    if 'Volume' in df.columns and df['Volume'].sum() > 0:
        # Volume Moving Averages
        for window in [5, 10, 20, 50]:
            if len(df) >= window:
                features[f'Volume_MA_{window}'] = df['Volume'].rolling(window=window).mean()
        
        # Volume Ratio (volume hari ini vs rata-rata)
        if 'Volume_MA_20' in features.columns:
            features['Volume_Ratio'] = df['Volume'] / features['Volume_MA_20']
            features['Volume_Ratio'] = features['Volume_Ratio'].replace([np.inf, -np.inf], 0).fillna(0)
        
        # Volume Change (momentum volume)
        features['Volume_Change'] = df['Volume'].pct_change()
        features['Volume_Change'] = features['Volume_Change'].fillna(0)
        
        # Volume Spikes (volume > 2x rata-rata)
        if 'Volume_MA_20' in features.columns:
            features['Volume_Spike'] = (df['Volume'] > (features['Volume_MA_20'] * 2)).astype(int)
        
        # VWAP (Volume Weighted Average Price) - rolling
        for window in [10, 20, 50]:
            if len(df) >= window:
                # Calculate typical price (High + Low + Close) / 3, fallback ke Close jika High/Low tidak ada
                if 'High' in df.columns and 'Low' in df.columns:
                    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
                else:
                    typical_price = df['Close']  # Fallback ke Close jika High/Low tidak ada
                
                vwap = (typical_price * df['Volume']).rolling(window=window).sum() / df['Volume'].rolling(window=window).sum()
                features[f'VWAP_{window}'] = vwap
                features[f'Price_VWAP_{window}_Ratio'] = df['Close'] / features[f'VWAP_{window}']
                features[f'Price_VWAP_{window}_Ratio'] = features[f'Price_VWAP_{window}_Ratio'].replace([np.inf, -np.inf], 1).fillna(1)
        
        # Volume-Price Trend (VPT)
        features['VPT'] = (features['Return'] * df['Volume']).cumsum()
        
        # On-Balance Volume (OBV)
        obv = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
        features['OBV'] = obv
        features['OBV_MA_20'] = features['OBV'].rolling(window=20).mean() if len(df) >= 20 else 0
        
        print(f"✅ Volume features ditambahkan: {len([col for col in features.columns if 'Volume' in col or 'VWAP' in col or 'OBV' in col or 'VPT' in col])} features")
    else:
        print(f"⚠️  Volume tidak tersedia atau semua 0, skip volume features")
    
    # Enhanced features jika enabled
    if use_enhanced:
        try:
            from src.utils.enhanced_feature_engineering import (
                add_time_based_features,
                add_rolling_window_features,
                add_garch_volatility_features
            )
            
            # Time-based features
            features = add_time_based_features(features)
            
            # Additional rolling windows
            features = add_rolling_window_features(features, windows=[5, 10, 20, 50, 100])
            
            # GARCH volatility (jika data cukup)
            if len(df) > 100:
                try:
                    features = add_garch_volatility_features(features)
                except:
                    pass  # Skip jika error
            
        except ImportError:
            print("⚠️  Enhanced features tidak tersedia, menggunakan basic features saja")
        except Exception as e:
            print(f"⚠️  Error dalam enhanced features: {e}")
    
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

def predict_ensemble_enhanced(features, df, use_classification=True, models_config=None, 
                              use_dynamic_weighting=True, use_arima_garch=True):
    """
    Enhanced ensemble dengan support untuk XGBoost, LSTM, ARIMA/GARCH, dan dynamic weighting
    
    Args:
        features: DataFrame dengan features
        df: DataFrame dengan data original
        use_classification: True untuk classification, False untuk regression
        models_config: List of dict dengan konfigurasi model
        use_dynamic_weighting: Gunakan dynamic weighting berdasarkan performance
        use_arima_garch: Include ARIMA/GARCH predictions
    
    Returns:
        Dictionary dengan hasil ensemble
    """
    # Import enhanced utilities
    try:
        from src.utils.ensemble_improvements import (
            calculate_dynamic_weights,
            dynamic_weighted_ensemble
        )
        from src.models.xgboost_model import (
            predict_xgboost_classification,
            predict_xgboost_regression
        )
        from src.models.lstm_model import (
            predict_lstm_classification,
            predict_lstm_regression
        )
        from src.models.time_series_models import auto_arima, fit_garch_model
        HAS_ENHANCED = True
    except ImportError as e:
        print(f"⚠️  Enhanced models tidak tersedia: {e}")
        HAS_ENHANCED = False
    
    # Default models config
    if models_config is None:
        models_config = ML_MODELS_CONFIG if 'ML_MODELS_CONFIG' in globals() else [
            {"model": "random_forest", "weight": 0.3, "enabled": True},
            {"model": "xgboost", "weight": 0.3, "enabled": True},
            {"model": "linear", "weight": 0.2, "enabled": True},
            {"model": "moving_avg", "weight": 0.2, "enabled": True}
        ]
    
    enabled_models = [m for m in models_config if m.get('enabled', True)]
    if not enabled_models:
        raise ValueError("Tidak ada model yang enabled")
    
    results = {}
    model_results = {}
    model_performances = []
    
    # Run semua models
    for model_config in enabled_models:
        model_name = model_config['model']
        
        try:
            if model_name == "random_forest":
                result = predict_random_forest(features, df, use_classification=use_classification)
                model_results['random_forest'] = result
                results['rf'] = result
                if 'accuracy' in result:
                    model_performances.append(result['accuracy'])
                else:
                    model_performances.append(0.5)  # Default
                    
            elif model_name == "xgboost" and HAS_ENHANCED:
                if use_classification:
                    result = predict_xgboost_classification(features, df)
                else:
                    result = predict_xgboost_regression(features, df)
                model_results['xgboost'] = result
                results['xgb'] = result
                if 'accuracy' in result:
                    model_performances.append(result['accuracy'])
                else:
                    model_performances.append(0.5)
                    
            elif model_name == "lstm" and HAS_ENHANCED:
                # Load LSTM config dari config.py
                try:
                    from src.utils.config import (
                        LSTM_SEQUENCE_LENGTH, LSTM_UNITS, LSTM_DROPOUT_RATE,
                        LSTM_EPOCHS, LSTM_BATCH_SIZE, LSTM_USE_GRU, ENABLE_LSTM
                    )
                    if not ENABLE_LSTM:
                        print("⚠️  LSTM disabled di config, skip")
                        continue
                except ImportError:
                    # Default values jika config tidak ada
                    LSTM_SEQUENCE_LENGTH = 60
                    LSTM_UNITS = 50
                    LSTM_DROPOUT_RATE = 0.2
                    LSTM_EPOCHS = 50
                    LSTM_BATCH_SIZE = 32
                    LSTM_USE_GRU = False
                
                if use_classification:
                    result = predict_lstm_classification(
                        features, df,
                        sequence_length=LSTM_SEQUENCE_LENGTH,
                        epochs=LSTM_EPOCHS,
                        batch_size=LSTM_BATCH_SIZE,
                        lstm_units=LSTM_UNITS,
                        dropout_rate=LSTM_DROPOUT_RATE,
                        use_gru=LSTM_USE_GRU
                    )
                else:
                    result = predict_lstm_regression(
                        features, df,
                        sequence_length=LSTM_SEQUENCE_LENGTH,
                        epochs=LSTM_EPOCHS,
                        batch_size=LSTM_BATCH_SIZE,
                        lstm_units=LSTM_UNITS,
                        dropout_rate=LSTM_DROPOUT_RATE,
                        use_gru=LSTM_USE_GRU
                    )
                model_results['lstm'] = result
                results['lstm'] = result
                if 'accuracy' in result:
                    model_performances.append(result['accuracy'])
                else:
                    model_performances.append(0.5)
                    
            elif model_name == "linear":
                result = predict_linear_regression(features)
                model_results['linear'] = result
                results['lr'] = result
                model_performances.append(0.5)  # Linear regression tidak punya accuracy
                
            elif model_name == "moving_avg":
                result = predict_moving_average(df)
                model_results['moving_avg'] = result
                results['ma'] = result
                model_performances.append(0.5)
                
        except Exception as e:
            print(f"⚠️  {model_name} error: {e}, skip model ini")
            continue
    
    # ARIMA/GARCH jika enabled
    arima_pred = None
    if use_arima_garch and HAS_ENHANCED:
        try:
            arima_result = auto_arima(df['Close'], max_p=2, max_d=1, max_q=2)
            if arima_result:
                arima_pred = arima_result.get('forecast', None)
                if arima_pred:
                    results['arima'] = {'prediction': arima_pred}
        except:
            pass
    
    if not results:
        raise ValueError("Semua model gagal")
    
    # Dynamic weighting jika enabled
    if use_dynamic_weighting and HAS_ENHANCED and len(model_performances) > 1:
        weights = calculate_dynamic_weights(model_performances, method='inverse_error')
    else:
        # Static weights dari config
        weights = [m.get('weight', 1.0/len(enabled_models)) for m in enabled_models]
        total_w = sum(weights)
        if total_w > 0:
            weights = [w / total_w for w in weights]
    
    # Combine predictions
    if use_classification:
        # Classification: combine probabilities
        buy_probs = []
        sell_probs = []
        valid_weights = []
        
        for i, (model_config, weight) in enumerate(zip(enabled_models, weights)):
            model_name = model_config['model']
            if model_name == 'random_forest' and 'rf' in results:
                buy_probs.append(results['rf']['buy_probability'])
                sell_probs.append(results['rf']['sell_probability'])
                valid_weights.append(weight)
            elif model_name == 'xgboost' and 'xgb' in results:
                buy_probs.append(results['xgb']['buy_probability'])
                sell_probs.append(results['xgb']['sell_probability'])
                valid_weights.append(weight)
            elif model_name == 'lstm' and 'lstm' in results:
                buy_probs.append(results['lstm']['buy_probability'])
                sell_probs.append(results['lstm']['sell_probability'])
                valid_weights.append(weight)
        
        if not buy_probs:
            # Fallback ke random_forest jika ada
            if 'rf' in results:
                return {
                    'signal': results['rf']['signal'],
                    'buy_probability': results['rf']['buy_probability'],
                    'sell_probability': results['rf']['sell_probability'],
                    'accuracy': results['rf'].get('accuracy', 0),
                    'current_price': results['rf']['current_price'],
                    'model_type': 'Ensemble (Enhanced)',
                    'ensemble_models': list(model_results.keys())
                }
            else:
                raise ValueError("Tidak ada model classification yang berhasil")
        
        # Normalize weights
        total_w = sum(valid_weights)
        if total_w > 0:
            valid_weights = [w / total_w for w in valid_weights]
        
        # Weighted average
        combined_buy_prob = sum(bp * w for bp, w in zip(buy_probs, valid_weights))
        combined_sell_prob = sum(sp * w for sp, w in zip(sell_probs, valid_weights))
        
        # Determine signal
        prob_margin = abs(combined_buy_prob - combined_sell_prob)
        min_threshold_strong = 55.0
        min_margin_strong = 10.0
        
        if combined_buy_prob >= min_threshold_strong and prob_margin >= min_margin_strong:
            signal = "BELI"
            signal_strength = "STRONG"
        elif combined_sell_prob >= min_threshold_strong and prob_margin >= min_margin_strong:
            signal = "JUAL"
            signal_strength = "STRONG"
        elif combined_buy_prob > 50:
            signal = "BELI"
            signal_strength = "WEAK"
        elif combined_sell_prob > 50:
            signal = "JUAL"
            signal_strength = "WEAK"
        else:
            signal = "HOLD"
            signal_strength = "NEUTRAL"
        
        # Get accuracy dari best model
        best_accuracy = max([r.get('accuracy', 0) for r in results.values() if 'accuracy' in r], default=0)
        current_price = results[list(results.keys())[0]].get('current_price', df['Close'].iloc[-1])
        
        return {
            'signal': signal,
            'buy_probability': combined_buy_prob,
            'sell_probability': combined_sell_prob,
            'signal_strength': signal_strength,
            'prob_margin': prob_margin,
            'accuracy': best_accuracy,
            'current_price': current_price,
            'model_type': 'Ensemble (Enhanced)',
            'ensemble_models': list(model_results.keys()),
            'model_weights': dict(zip([m['model'] for m in enabled_models], weights))
        }
    else:
        # Regression: weighted average predictions
        predictions = []
        valid_weights = []
        
        for i, (model_config, weight) in enumerate(zip(enabled_models, weights)):
            model_name = model_config['model']
            if model_name == 'linear' and 'lr' in results:
                predictions.append(results['lr']['prediction'])
                valid_weights.append(weight)
            elif model_name == 'moving_avg' and 'ma' in results:
                predictions.append(results['ma']['prediction'])
                valid_weights.append(weight)
            elif model_name == 'xgboost' and 'xgb' in results:
                predictions.append(results['xgb']['prediction'])
                valid_weights.append(weight)
            elif model_name == 'lstm' and 'lstm' in results:
                predictions.append(results['lstm']['prediction'])
                valid_weights.append(weight)
        
        # Include ARIMA jika ada
        if arima_pred:
            predictions.append(arima_pred)
            valid_weights.append(0.1)  # Small weight untuk ARIMA
        
        if not predictions:
            raise ValueError("Tidak ada model regression yang berhasil")
        
        # Normalize weights
        total_w = sum(valid_weights)
        if total_w > 0:
            valid_weights = [w / total_w for w in valid_weights]
        
        # Weighted average
        ensemble_pred = sum(p * w for p, w in zip(predictions, valid_weights))
        
        # Get metrics dari best model
        current_price = results[list(results.keys())[0]].get('current_price', df['Close'].iloc[-1])
        
        return {
            'prediction': ensemble_pred,
            'current_price': current_price,
            'model_type': 'Ensemble (Enhanced)',
            'ensemble_models': list(model_results.keys()),
            'model_weights': dict(zip([m['model'] for m in enabled_models], weights))
        }


def predict_ensemble(features, df, use_classification=True, models_config=None, use_enhanced=True):
    """
    Prediksi menggunakan ensemble method (gabungan beberapa metode)
    Support untuk enhanced models jika use_enhanced=True
    
    Args:
        features: DataFrame dengan features
        df: DataFrame dengan data original
        use_classification: True untuk classification, False untuk regression
        models_config: List of dict dengan konfigurasi model dari config.py
        use_enhanced: Gunakan enhanced ensemble dengan XGBoost, LSTM, dll
    
    Returns:
        Dictionary dengan hasil ensemble
    """
    # Gunakan enhanced ensemble jika enabled
    if use_enhanced:
        try:
            return predict_ensemble_enhanced(
                features, df, 
                use_classification=use_classification,
                models_config=models_config,
                use_dynamic_weighting=True,
                use_arima_garch=True
            )
        except Exception as e:
            print(f"⚠️  Enhanced ensemble error: {e}, fallback ke basic ensemble")
            # Fallback ke basic ensemble
    # Gunakan config dari parameter atau global config
    if models_config is None:
        models_config = ML_MODELS_CONFIG if 'ML_MODELS_CONFIG' in globals() else [
            {"model": "random_forest", "weight": 0.5, "enabled": True},
            {"model": "linear", "weight": 0.3, "enabled": True},
            {"model": "moving_avg", "weight": 0.2, "enabled": True}
        ]
    
    # Filter hanya model yang enabled
    enabled_models = [m for m in models_config if m.get('enabled', True)]
    
    if not enabled_models:
        raise ValueError("Tidak ada model yang enabled dalam ML_MODELS_CONFIG")
    
    # Normalize weights (pastikan total = 1.0)
    total_weight = sum(m.get('weight', 0) for m in enabled_models)
    if total_weight > 0:
        # Normalize weights
        for m in enabled_models:
            m['weight'] = m.get('weight', 0) / total_weight
    else:
        # Jika semua weight = 0, set equal weights
        equal_weight = 1.0 / len(enabled_models)
        for m in enabled_models:
            m['weight'] = equal_weight
    
    results = {}
    model_results = {}
    
    # Jalankan setiap model yang enabled
    for model_config in enabled_models:
        model_name = model_config['model']
        weight = model_config['weight']
        
        try:
            if model_name == "random_forest":
                rf_result = predict_random_forest(features, df, use_classification=use_classification)
                model_results['random_forest'] = rf_result
                results['rf'] = rf_result
                
            elif model_name == "linear":
                lr_result = predict_linear_regression(features)
                model_results['linear'] = lr_result
                results['lr'] = lr_result
                
            elif model_name == "moving_avg":
                ma_result = predict_moving_average(df)
                model_results['moving_avg'] = ma_result
                results['ma'] = ma_result
                
        except Exception as e:
            print(f"⚠️  {model_name} error: {e}, skip model ini")
            # Kurangi weight model yang error, redistribute ke model lain
            continue
    
    if not results:
        raise ValueError("Semua model gagal, tidak bisa membuat ensemble")
    
    # Untuk classification: gunakan RandomForest jika ada, atau weighted voting
    if use_classification:
        if 'rf' in results:
            # Jika ada RandomForest, gunakan sebagai base, tapi bisa combine dengan yang lain
            rf_result = results['rf']
            rf_weight = next((m['weight'] for m in enabled_models if m['model'] == 'random_forest'), 0.5)
            
            # Debug: cek apakah accuracy ada
            if 'accuracy' not in rf_result:
                print(f"⚠️  [DEBUG] rf_result tidak memiliki 'accuracy' key!")
                print(f"   rf_result keys: {list(rf_result.keys())}")
                print(f"   rf_result content: {rf_result}")
                # Set default accuracy = 0
                rf_result['accuracy'] = 0
            
            # Jika hanya RandomForest, return langsung
            if len(results) == 1:
                result = {
                    'signal': rf_result['signal'],
                    'buy_probability': rf_result['buy_probability'],
                    'sell_probability': rf_result['sell_probability'],
                    'accuracy': rf_result['accuracy'],
                    'current_price': rf_result['current_price'],
                    'model_type': 'RandomForestClassifier',
                    'ensemble_models': ['random_forest']
                }
                print(f"🔍 [DEBUG] predict_ensemble returning (single RF): accuracy={result.get('accuracy')}")
                return result
            
            # Jika ada multiple models, combine probabilities
            # Untuk classification, kita bisa combine buy_probability
            buy_probs = []
            sell_probs = []
            weights = []
            
            if 'rf' in results:
                buy_probs.append(rf_result['buy_probability'])
                sell_probs.append(rf_result['sell_probability'])
                weights.append(next((m['weight'] for m in enabled_models if m['model'] == 'random_forest'), 0.5))
            
            # Normalize weights
            total_w = sum(weights)
            if total_w > 0:
                weights = [w / total_w for w in weights]
            
            # Weighted average probabilities
            combined_buy_prob = sum(bp * w for bp, w in zip(buy_probs, weights))
            combined_sell_prob = sum(sp * w for sp, w in zip(sell_probs, weights))
            
            # Determine signal dengan threshold yang lebih ketat
            # Threshold untuk signal kuat: minimal 55% dengan margin minimal 10%
            # Signal lemah (50-55% atau margin < 10%) akan menghasilkan HOLD
            prob_margin = abs(combined_buy_prob - combined_sell_prob)
            min_threshold_strong = 55.0  # Minimal 55% untuk signal kuat
            min_margin_strong = 10.0    # Minimal 10% margin untuk signal kuat
            
            signal_strength = "WEAK"  # Default: weak signal
            if combined_buy_prob >= min_threshold_strong and prob_margin >= min_margin_strong:
                signal = "BELI"
                signal_strength = "STRONG"
            elif combined_sell_prob >= min_threshold_strong and prob_margin >= min_margin_strong:
                signal = "JUAL"
                signal_strength = "STRONG"
            elif combined_buy_prob > 50:
                # Signal lemah untuk LONG - tetap signal BELI tapi akan di-warning
                signal = "BELI"
                signal_strength = "WEAK"
            elif combined_sell_prob > 50:
                # Signal lemah untuk SHORT - tetap signal JUAL tapi akan di-warning
                signal = "JUAL"
                signal_strength = "WEAK"
            else:
                # Tidak ada sinyal jelas
                signal = "HOLD"
                signal_strength = "NEUTRAL"
            
            # Debug: cek accuracy
            accuracy_val = rf_result.get('accuracy', 0) if 'rf' in results else 0
            if accuracy_val == 0 and 'rf' in results:
                print(f"⚠️  [DEBUG] rf_result accuracy = 0 atau tidak ada!")
                print(f"   rf_result keys: {list(rf_result.keys()) if isinstance(rf_result, dict) else 'N/A'}")
                if isinstance(rf_result, dict):
                    print(f"   rf_result['accuracy']: {rf_result.get('accuracy', 'KEY NOT FOUND')}")
            
            result = {
                'signal': signal,
                'buy_probability': combined_buy_prob,
                'sell_probability': combined_sell_prob,
                'signal_strength': signal_strength,  # STRONG, WEAK, atau NEUTRAL
                'prob_margin': prob_margin,  # Margin antara buy dan sell prob
                'accuracy': accuracy_val,
                'current_price': rf_result['current_price'],
                'model_type': 'Ensemble (Weighted)',
                'ensemble_models': [m['model'] for m in enabled_models if m['model'] in model_results],
                'model_weights': {m['model']: m['weight'] for m in enabled_models if m['model'] in model_results}
            }
            print(f"🔍 [DEBUG] predict_ensemble returning (multiple models): accuracy={result.get('accuracy')}")
            return result
        else:
            # Jika tidak ada RandomForest, tidak bisa classification
            raise ValueError("RandomForest diperlukan untuk classification mode")
    
    else:
        # Untuk regression: weighted average predictions
        predictions = []
        weights = []
        
        if 'lr' in results:
            predictions.append(results['lr']['prediction'])
            weights.append(next((m['weight'] for m in enabled_models if m['model'] == 'linear'), 0.5))
        
        if 'ma' in results:
            predictions.append(results['ma']['prediction'])
            weights.append(next((m['weight'] for m in enabled_models if m['model'] == 'moving_avg'), 0.5))
        
        if not predictions:
            raise ValueError("Tidak ada model regression yang berhasil")
        
        # Normalize weights
        total_w = sum(weights)
        if total_w > 0:
            weights = [w / total_w for w in weights]
        
        # Weighted average prediction
        ensemble_pred = sum(p * w for p, w in zip(predictions, weights))
        
        # Calculate confidence interval (gunakan RMSE dari Linear Regression jika ada)
        confidence_interval = None
        if 'lr' in results:
            confidence_interval = results['lr'].get('rmse', ensemble_pred * 0.02)
        else:
            confidence_interval = ensemble_pred * 0.02
        
        return {
            'prediction': ensemble_pred,
            'lr_prediction': results['lr']['prediction'] if 'lr' in results else None,
            'ma_prediction': results['ma']['prediction'] if 'ma' in results else None,
            'confidence_interval': confidence_interval,
            'lr_mae': results['lr'].get('mae') if 'lr' in results else None,
            'lr_rmse': results['lr'].get('rmse') if 'lr' in results else None,
            'current_price': results['ma']['current_price'] if 'ma' in results else results['lr'].get('current_price', df['Close'].iloc[-1]),
            'model_type': 'Ensemble (Weighted)',
            'ensemble_models': [m['model'] for m in enabled_models if m['model'] in model_results],
            'model_weights': {m['model']: m['weight'] for m in enabled_models if m['model'] in model_results}
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
    
    # Default values (akan di-overwrite jika perhitungan berhasil)
    accuracy_val = 0
    expected_val = 0
    sharpe_val = 0
    
    if use_classification and 'accuracy' in model_result:
        # Classification backtesting
        accuracy = model_result['accuracy']
        accuracy_val = accuracy  # Simpan untuk return
        print(f"✅ Accuracy Score: {accuracy*100:.2f}%")
        print(f"   (Menggunakan accuracy_score dari sklearn)")
        
        # Hitung expected value dari probabilitas
        buy_prob = model_result.get('buy_probability', 50) / 100
        sell_prob = model_result.get('sell_probability', 50) / 100
        
        # Simulasi return jika ikuti sinyal berdasarkan probabilitas
        returns = df['Close'].pct_change().dropna()
        
        print(f"   📊 Data returns: {len(returns)} records")
        
        if len(returns) > 10:
            # Hitung expected return berdasarkan probabilitas
            # Expected return = (buy_prob * avg_positive_return) - (sell_prob * avg_negative_return)
            positive_returns = returns[returns > 0]
            negative_returns = returns[returns < 0]
            
            print(f"   📊 Positive returns: {len(positive_returns)}, Negative returns: {len(negative_returns)}")
            
            if len(positive_returns) > 0 and len(negative_returns) > 0:
                avg_positive = positive_returns.mean()
                avg_negative = abs(negative_returns.mean())
                
                expected_return = (buy_prob * avg_positive) - (sell_prob * avg_negative)
                expected_val = expected_return * 100
                
                # Sharpe Ratio
                strategy_returns = []
                for ret in returns[-50:]:  # Ambil 50 data terakhir
                    if buy_prob > 0.5:
                        strategy_returns.append(ret)  # Ikuti sinyal BELI
                    else:
                        strategy_returns.append(-ret)  # Ikuti sinyal JUAL
                
                if len(strategy_returns) > 0 and np.std(strategy_returns) > 0:
                    sharpe_val = (np.mean(strategy_returns) / np.std(strategy_returns)) * np.sqrt(252)
                else:
                    sharpe_val = 0
                
                print(f"📈 Expected Value: {expected_val:.2f}%")
                print(f"   (Berdasarkan probabilitas dan historical returns)")
                print(f"📊 Sharpe Ratio: {sharpe_val:.2f}")
                print(f"   (Sharpe > 1 = bagus, > 2 = sangat bagus)")
            else:
                print(f"⚠️  Tidak cukup positive/negative returns untuk menghitung expected value")
                print(f"   Menggunakan default values: expected_value=0, sharpe_ratio=0")
        else:
            print(f"⚠️  Tidak cukup data returns (perlu >10, dapat {len(returns)})")
            print(f"   Menggunakan default values: expected_value=0, sharpe_ratio=0")
    else:
        # Regression backtesting
        if 'lr_mae' in model_result and model_result['lr_mae']:
            print(f"✅ MAE (Mean Absolute Error): ${model_result['lr_mae']:,.2f}")
            print(f"✅ RMSE (Root Mean Squared Error): ${model_result['lr_rmse']:,.2f}")
            
            # Hitung expected value dari prediksi
            current_price = model_result['current_price']
            predicted_price = model_result['prediction']
            expected_return = ((predicted_price - current_price) / current_price) * 100
            expected_val = expected_return  # Untuk regression, expected_value = expected_return
            
            print(f"📈 Expected Return: {expected_return:.2f}%")
            print(f"   (Berdasarkan prediksi harga)")
            
            # Bisa tambah perhitungan return (seperti di gambar)
            returns = df['Close'].pct_change().dropna()
            if len(returns) > 0:
                avg_return = returns.mean() * 100
                print(f"📊 Average Historical Return: {avg_return:.2f}%")
            
            # Untuk regression, return dengan key yang berbeda
            return {
                'mae': model_result['lr_mae'],
                'rmse': model_result['lr_rmse'],
                'expected_value': expected_val,  # Tambahkan expected_value untuk konsistensi
                'expected_return': expected_return,
                'accuracy': 0,  # Regression tidak punya accuracy
                'sharpe_ratio': 0  # Belum dihitung untuk regression
            }
        else:
            print("⚠️  Regression backtesting tidak bisa dilakukan (tidak ada lr_mae)")
            # Tetap set expected_val = 0 untuk konsistensi
            expected_val = 0
    
    # SELALU return dict dengan key yang konsisten, bahkan jika nilainya 0
    result = {
        'accuracy': accuracy_val,
        'expected_value': expected_val,
        'sharpe_ratio': sharpe_val
    }
    
    print(f"✅ Backtest result: accuracy={result['accuracy']}, expected_value={result['expected_value']}, sharpe_ratio={result['sharpe_ratio']}")
    
    # Debug: cek kenapa nilai 0
    if result['accuracy'] == 0 and result['expected_value'] == 0 and result['sharpe_ratio'] == 0:
        print(f"⚠️  [DEBUG] Semua metrics = 0, cek kondisi:")
        print(f"   - use_classification: {use_classification}")
        print(f"   - 'accuracy' in model_result: {'accuracy' in model_result if isinstance(model_result, dict) else 'model_result bukan dict'}")
        if isinstance(model_result, dict):
            print(f"   - model_result keys: {list(model_result.keys())}")
            print(f"   - model_result content: {model_result}")
        print(f"   - len(df): {len(df) if df is not None else 'df is None'}")
        if df is not None and len(df) > 0:
            returns = df['Close'].pct_change().dropna()
            print(f"   - len(returns): {len(returns)}")
            if len(returns) > 0:
                positive_returns = returns[returns > 0]
                negative_returns = returns[returns < 0]
                print(f"   - len(positive_returns): {len(positive_returns)}")
                print(f"   - len(negative_returns): {len(negative_returns)}")
    
    return result

def main():
    print("=" * 60)
    print("⚙️  QUANT MODEL: PREDICTIVE MACHINE LEARNING")
    print("=" * 60)
    
    # Debug: Log environment info
    print(f"🔍 [DEBUG] Environment check:")
    print(f"   - Python version: {sys.version}")
    print(f"   - Working directory: {os.getcwd()}")
    print(f"   - Script location: {__file__}")
    print()
    
    # ============================================
    # 1. DATA HISTORIS (Historical Data)
    # ============================================
    print("📊 [1] DATA HISTORIS")
    print("-" * 60)
    
    # Debug: Validasi data sebelum diproses
    print(f"🔍 [DEBUG] Checking data source...")
    try:
        if USE_CSV_DATA and CSV_FILE:
            print(f"   - Using CSV file: {CSV_FILE}")
            if not os.path.exists(CSV_FILE):
                print(f"   ❌ ERROR: CSV file not found: {CSV_FILE}")
        else:
            print(f"   - Using data from get_historical_data.py")
    except Exception as e:
        print(f"   ⚠️  Error checking data source: {e}")
    
    try:
        data = load_data(CSV_FILE)
        print(f"✅ Data dimuat: {len(data)} records")
        print(f"   Periode: {data.index.min()} sampai {data.index.max()}")
        print(f"   Sumber: {'CSV' if USE_CSV_DATA else 'yfinance'}")
        
        # Debug: Validasi data yang dimuat
        print(f"   🔍 [DEBUG] Data validation after load:")
        print(f"      - Data shape: {data.shape}")
        print(f"      - Data columns: {list(data.columns)}")
        print(f"      - Index type: {type(data.index)}")
        print(f"      - Index name: {data.index.name}")
        print(f"      - Data types: {data.dtypes.to_dict()}")
        print(f"      - Null values: {data.isnull().sum().to_dict()}")
        if 'Close' in data.columns:
            print(f"      - Close price stats: min={data['Close'].min():.8f}, max={data['Close'].max():.8f}, mean={data['Close'].mean():.8f}")
            print(f"      - Close price sample (first 5): {data['Close'].head(5).tolist()}")
        else:
            print(f"      ⚠️  WARNING: 'Close' column not found in data!")
            print(f"      - Available columns: {list(data.columns)}")
        
        # Validasi: pastikan data tidak kosong
        if len(data) == 0:
            print(f"   ❌ ERROR: Data is empty after loading!")
            return
        
        # Validasi: pastikan ada kolom Close
        if 'Close' not in data.columns:
            print(f"   ❌ ERROR: 'Close' column is required but not found!")
            return
        
        # Validasi: pastikan tidak ada null values di Close
        if data['Close'].isnull().any():
            print(f"   ⚠️  WARNING: Found null values in Close column, dropping...")
            data = data.dropna(subset=['Close'])
            print(f"      After dropna: {len(data)} rows")
            if len(data) == 0:
                print(f"   ❌ ERROR: Data is empty after dropping null values!")
                return
        
        print(f"   ✅ Data validation passed: {len(data)} valid rows ready for processing")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # ============================================
    # 1.5. DATA QUALITY SCORING
    # ============================================
    print("\n📊 [1.5] DATA QUALITY SCORING")
    print("-" * 60)
    try:
        from src.utils.data_quality import calculate_data_quality_score
        
        quality_result = calculate_data_quality_score(data)
        quality_score = quality_result['score']
        quality_grade = quality_result['grade']
        quality_recommendation = quality_result['recommendation']
        
        print(f"✅ Data Quality Score: {quality_score*100:.1f}% (Grade: {quality_grade})")
        print(f"   Recommendation: {quality_recommendation}")
        
        if quality_score < 0.6:
            print(f"⚠️  PERINGATAN: Data quality rendah! Disarankan cleaning data sebelum prediksi")
            # Auto-clean jika quality terlalu rendah
            if quality_score < 0.4:
                print(f"   🔧 Auto-cleaning data...")
                from src.utils.data_quality import clean_trading_data
                data = clean_trading_data(data, handle_outliers=True, impute_missing=True, remove_invalid_ohlc=True)
                print(f"   ✅ Data cleaned")
        
        # Show quality details
        if quality_result['details']['warnings']:
            print(f"   ⚠️  Warnings: {len(quality_result['details']['warnings'])}")
        if quality_result['details']['errors']:
            print(f"   ❌ Errors: {len(quality_result['details']['errors'])}")
    except Exception as e:
        print(f"⚠️  Data quality scoring error: {e}")
    
    # ============================================
    # 2. FEATURE ENGINEERING (ENHANCED)
    # ============================================
    print("\n🔧 [2] FEATURE ENGINEERING (ENHANCED)")
    print("-" * 60)
    print("Menyusun pola matematis dari harga dengan enhanced features...")
    
    # Get current interval untuk multi-timeframe features
    try:
        from src.utils.config import get_interval
        current_interval = get_interval()
    except:
        current_interval = None
    
    # Gunakan enhanced features
    features = create_features(data, use_enhanced=True)
    
    # Add multi-timeframe features jika enabled
    try:
        from src.utils.enhanced_feature_engineering import add_multi_timeframe_features, add_seasonal_features
        from src.utils.pullback_detection import add_pullback_features, get_current_pullback_status
        
        # Multi-timeframe features
        features = add_multi_timeframe_features(features, current_interval=current_interval)
        
        # Seasonal features
        features = add_seasonal_features(features, column='Close')
        
        # Pullback detection features
        features = add_pullback_features(features)
        
        # Get current pullback & reversal status untuk coin (misalnya XAN)
        pullback_status = get_current_pullback_status(data)
        
        # Display Reversal (prioritas tertinggi)
        if pullback_status.get('has_reversal', False):
            print(f"\n🔄 REVERSAL DETECTION:")
            print(f"   ✅ Reversal Detected: {pullback_status['reversal_type']}")
            print(f"   Signal: {'LONG (Bullish Reversal)' if pullback_status['reversal_signal'] == 1 else 'SHORT (Bearish Reversal)' if pullback_status['reversal_signal'] == -1 else 'NONE'}")
            print(f"   Confidence: {pullback_status['reversal_confidence']*100:.1f}%")
            print(f"   ⚠️  WARNING: Trend berubah! Ini bukan pullback, tapi reversal sebenarnya")
            print(f"   Recommendation: {pullback_status['recommendation']}")
        
        # Display Breakout (prioritas kedua)
        elif pullback_status.get('has_breakout', False):
            print(f"\n🚀 BREAKOUT DETECTION:")
            print(f"   ✅ Breakout Detected: {pullback_status['breakout_type']}")
            print(f"   Signal: {'LONG (Bullish Breakout)' if pullback_status['breakout_signal'] == 1 else 'SHORT (Bearish Breakout)' if pullback_status['breakout_signal'] == -1 else 'NONE'}")
            print(f"   Level: ${pullback_status.get('breakout_level', 0):.6f}")
            print(f"   Confidence: {pullback_status['breakout_confidence']*100:.1f}%")
            print(f"   Recommendation: {pullback_status['recommendation']}")
        
        # Display Impulse Move (prioritas ketiga)
        elif pullback_status.get('has_impulse', False):
            print(f"\n⚡ IMPULSE MOVE DETECTION:")
            print(f"   ✅ Impulse Detected: {pullback_status['impulse_type']}")
            print(f"   Signal: {'LONG (Bullish Impulse)' if pullback_status['impulse_signal'] == 1 else 'SHORT (Bearish Impulse)' if pullback_status['impulse_signal'] == -1 else 'NONE'}")
            print(f"   Strength: {pullback_status['impulse_strength']*100:.1f}%")
            print(f"   Confidence: {pullback_status['impulse_confidence']*100:.1f}%")
            print(f"   Recommendation: {pullback_status['recommendation']}")
        
        # Display Pullback (prioritas terendah)
        elif pullback_status.get('has_pullback', False):
            print(f"\n📊 PULLBACK DETECTION:")
            print(f"   ✅ Pullback Detected: {pullback_status['pullback_type']} ({pullback_status['pullback_depth']*100:.1f}% retracement)")
            print(f"   Signal: {'LONG' if pullback_status['pullback_signal'] == 1 else 'SHORT' if pullback_status['pullback_signal'] == -1 else 'NONE'}")
            print(f"   Confidence: {pullback_status['pullback_confidence']*100:.1f}%")
            print(f"   Recommendation: {pullback_status['recommendation']}")
            if pullback_status['entry_levels']['pullback_entry_1']:
                print(f"   Entry Levels:")
                if pullback_status['entry_levels']['pullback_entry_1']:
                    print(f"      Entry 1 (Shallow): ${pullback_status['entry_levels']['pullback_entry_1']:.6f}")
                if pullback_status['entry_levels']['pullback_entry_2']:
                    print(f"      Entry 2 (Medium): ${pullback_status['entry_levels']['pullback_entry_2']:.6f}")
                if pullback_status['entry_levels']['pullback_entry_3']:
                    print(f"      Entry 3 (Deep): ${pullback_status['entry_levels']['pullback_entry_3']:.6f}")
    except Exception as e:
        print(f"⚠️  Error adding multi-timeframe/seasonal/pullback features: {e}")
    print(f"✅ Fitur dibuat: {len(features.columns)} fitur")
    
    # Feature selection jika terlalu banyak features
    if len(features.columns) > 100:
        print(f"⚠️  Terlalu banyak features ({len(features.columns)}), melakukan feature selection...")
        try:
            from src.utils.feature_selection import comprehensive_feature_selection
            from sklearn.ensemble import RandomForestClassifier
            
            # Feature selection
            target = (data['Close'].shift(-1) > data['Close']).astype(int)
            target = target[features.index]
            target = target.dropna()
            features_aligned = features.loc[target.index]
            
            selection_result = comprehensive_feature_selection(
                features_aligned,
                target,
                RandomForestClassifier,
                n_features_to_select=50,
                min_importance=0.01
            )
            
            selected_features = selection_result['selected_features']
            features = features[selected_features + ['Close']]  # Keep Close
            print(f"✅ Feature selection: {len(selected_features)} features selected")
        except Exception as e:
            print(f"⚠️  Feature selection error: {e}, menggunakan semua features")
    
    feature_examples = ['Return', 'MA_5', 'RSI', 'Volatility_10', 'Momentum_5']
    available_features = [f for f in feature_examples if f in features.columns]
    print(f"   Contoh fitur: {', '.join(available_features)}")
    
    # Show enhanced features jika ada
    enhanced_features = [f for f in features.columns if any(x in f.lower() for x in ['hour', 'day', 'month', 'garch', 'seasonal'])]
    if enhanced_features:
        print(f"   Enhanced features: {len(enhanced_features)} (time-based, GARCH, dll)")
    
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
        # Gunakan enhanced ensemble dengan semua improvements
        result = predict_ensemble(
            features, data, 
            use_classification=USE_CLASSIFICATION, 
            models_config=ML_MODELS_CONFIG,
            use_enhanced=True  # Enable enhanced models (XGBoost, LSTM, ARIMA/GARCH)
        )
        
        # Add confidence intervals jika regression
        if not USE_CLASSIFICATION and 'prediction' in result:
            try:
                # Calculate confidence interval dari model predictions
                predictions_list = []
                if 'lr' in result or 'lr_prediction' in result:
                    predictions_list.append(result.get('lr_prediction', result.get('prediction')))
                if 'xgb' in result and 'prediction' in result.get('xgb', {}):
                    predictions_list.append(result['xgb']['prediction'])
                if 'lstm' in result and 'prediction' in result.get('lstm', {}):
                    predictions_list.append(result['lstm']['prediction'])
                
                if predictions_list:
                    pred_array = np.array(predictions_list)
                    pred_std = np.std(pred_array)
                    result['prediction_lower'] = result['prediction'] - 1.96 * pred_std
                    result['prediction_upper'] = result['prediction'] + 1.96 * pred_std
                    result['confidence_interval_95'] = {
                        'lower': result['prediction_lower'],
                        'upper': result['prediction_upper'],
                        'width': 2 * 1.96 * pred_std
                    }
            except:
                pass
        if USE_CLASSIFICATION and 'signal' in result:
            model_type = result.get('model_type', 'Ensemble')
            print(f"✅ Model: {model_type}")
            print(f"   Signal: {result['signal']}")
            print(f"   Probabilitas BELI: {result['buy_probability']:.2f}%")
            print(f"   Probabilitas JUAL: {result['sell_probability']:.2f}%")
            if 'signal_strength' in result:
                print(f"   Signal Strength: {result['signal_strength']}")
            if 'ensemble_models' in result:
                print(f"   Models: {', '.join(result['ensemble_models'])}")
        else:
            # Regression
            if 'prediction' in result:
                print(f"✅ Model: {result.get('model_type', 'Ensemble')}")
                print(f"   Prediksi harga: ${result['prediction']:,.2f}")
                if 'prediction_lower' in result and 'prediction_upper' in result:
                    print(f"   Confidence Interval (95%): ${result['prediction_lower']:,.2f} - ${result['prediction_upper']:,.2f}")
    
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
        signal_strength = result.get('signal_strength', 'UNKNOWN')
        prob_margin = result.get('prob_margin', 0)
        
        print(f"   Prediksi besok: {signal}")
        print(f"   Probabilitas BELI: {buy_prob:.2f}%")
        print(f"   Probabilitas JUAL: {sell_prob:.2f}%")
        print(f"   Margin Probabilitas: {prob_margin:.2f}%")
        
        if signal_strength == "STRONG":
            print(f"   💪 Signal Kuat: {signal} (Probabilitas tinggi, margin {prob_margin:.1f}%)")
        elif signal_strength == "WEAK":
            print(f"   ⚠️  Signal Lemah: {signal} (Probabilitas {buy_prob:.1f}%, margin hanya {prob_margin:.1f}%)")
            print(f"   💡 Peringatan: Signal ini lemah! Pertimbangkan konfirmasi dari AI Strategy atau market context")
        elif signal_strength == "NEUTRAL":
            print(f"   🟡 Signal Netral: {signal} (Tidak ada sinyal jelas)")
        else:
            # Fallback untuk backward compatibility
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
    
    # Simpan hasil ke file JSON untuk digunakan oleh analisis_quant.py
    try:
        import json
        
        # Extract metrics dari backtest_result (pastikan selalu ada nilai, bahkan jika 0)
        # backtest_result sekarang SELALU return dict dengan key yang konsisten
        if backtest_result and isinstance(backtest_result, dict):
            accuracy_val = backtest_result.get('accuracy', 0)
            expected_val = backtest_result.get('expected_value', 0)
            sharpe_val = backtest_result.get('sharpe_ratio', 0)
            # Pastikan semua nilai adalah number, bukan None
            if accuracy_val is None:
                accuracy_val = 0
            if expected_val is None:
                expected_val = 0
            if sharpe_val is None:
                sharpe_val = 0
        else:
            accuracy_val = 0
            expected_val = 0
            sharpe_val = 0
        
        print(f"🔍 [DEBUG] Extracting metrics from backtest_result:")
        print(f"   backtest_result type: {type(backtest_result)}")
        print(f"   backtest_result content: {backtest_result}")
        print(f"   accuracy_val (before conversion): {accuracy_val}")
        print(f"   expected_val: {expected_val}")
        print(f"   sharpe_val: {sharpe_val}")
        
        # Convert accuracy dari decimal ke persen jika perlu (0.49 -> 49)
        if isinstance(accuracy_val, (int, float)) and 0 < accuracy_val < 1:
            accuracy_val = accuracy_val * 100
            print(f"   accuracy_val (after conversion): {accuracy_val}")
        
        print(f"✅ Final metrics: accuracy={accuracy_val}, expected_value={expected_val}, sharpe_ratio={sharpe_val}")
        
        ml_result = {
            'model': PREDICTION_METHOD,
            'model_type': result.get('model_type', 'Unknown'),
            'signal': result.get('signal', 'HOLD'),
            'buy_probability': result.get('buy_probability', 0),
            'sell_probability': result.get('sell_probability', 0),
            'accuracy': accuracy_val,  # Sudah dalam format persen jika perlu
            'expected_value': expected_val,
            'sharpe_ratio': sharpe_val,
            'data_records': len(data),
            'features_count': len(features.columns),
            'current_price': result.get('current_price', data['Close'].iloc[-1])
        }
        
        # Pastikan file disimpan di project root (bukan di src/)
        json_file_path = os.path.join(project_root, 'ml_prediction_result.json')
        print(f"🔍 [DEBUG] Saving ml_prediction_result.json to: {json_file_path}")
        print(f"   Current directory: {os.getcwd()}")
        print(f"   Project root: {project_root}")
        
        with open(json_file_path, 'w') as f:
            json.dump(ml_result, f, indent=2)
        
        # Verifikasi file terbuat
        if os.path.exists(json_file_path):
            file_size = os.path.getsize(json_file_path)
            print(f"✅ ML prediction results disimpan ke {json_file_path}")
            print(f"   File size: {file_size} bytes")
            print(f"   📊 Saved metrics: accuracy={ml_result.get('accuracy')}, sharpe={ml_result.get('sharpe_ratio')}, expected_value={ml_result.get('expected_value')}")
            
            # Debug: baca kembali untuk verifikasi
            try:
                with open(json_file_path, 'r') as f:
                    verify_data = json.load(f)
                    print(f"   ✅ Verification: File dapat dibaca, keys: {list(verify_data.keys())}")
            except Exception as e:
                print(f"   ⚠️  Verification failed: {e}")
        else:
            print(f"❌ ERROR: File tidak terbuat di {json_file_path}")
    except Exception as e:
        # Log error untuk debugging
        print(f"⚠️  Error saving ML prediction results: {e}")
        import traceback
        traceback.print_exc()
    
    # JANGAN hapus file CSV di sini - biarkan analisis_quant.py yang menghapusnya
    # setelah semua proses selesai (termasuk prediksi dan DeepSeek)
    # Ini memastikan file CSV tetap tersedia untuk semua proses yang membutuhkannya

if __name__ == "__main__":
    main()

