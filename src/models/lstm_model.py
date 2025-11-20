"""
LSTM Model Implementation
Long Short-Term Memory networks for time series prediction
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout, GRU
    from tensorflow.keras.callbacks import EarlyStopping
    from sklearn.preprocessing import MinMaxScaler
    HAS_TENSORFLOW = True
except ImportError:
    HAS_TENSORFLOW = False
    print("⚠️  TensorFlow tidak terinstall. Install dengan: pip install tensorflow")


def create_sequences(data: np.ndarray, sequence_length: int) -> Tuple[np.ndarray, np.ndarray]:
    """
    Create sequences untuk LSTM
    
    Args:
        data: Array dengan data
        sequence_length: Length of sequences
    
    Returns:
        X, y arrays untuk training
    """
    X, y = [], []
    for i in range(len(data) - sequence_length):
        X.append(data[i:i+sequence_length])
        y.append(data[i+sequence_length])
    return np.array(X), np.array(y)


def create_lstm_model(sequence_length: int,
                     features_count: int,
                     lstm_units: int = 50,
                     dropout_rate: float = 0.2,
                     use_gru: bool = False) -> Optional:
    """
    Create LSTM/GRU model
    
    Args:
        sequence_length: Length of input sequences
        features_count: Number of features
        lstm_units: Number of LSTM units
        dropout_rate: Dropout rate
        use_gru: Use GRU instead of LSTM
    
    Returns:
        Compiled Keras model
    """
    if not HAS_TENSORFLOW:
        return None
    
    model = Sequential()
    
    if use_gru:
        model.add(GRU(lstm_units, return_sequences=True, input_shape=(sequence_length, features_count)))
    else:
        model.add(LSTM(lstm_units, return_sequences=True, input_shape=(sequence_length, features_count)))
    
    model.add(Dropout(dropout_rate))
    
    if use_gru:
        model.add(GRU(lstm_units, return_sequences=False))
    else:
        model.add(LSTM(lstm_units, return_sequences=False))
    
    model.add(Dropout(dropout_rate))
    model.add(Dense(1))
    
    model.compile(optimizer='adam', loss='mse', metrics=['mae'])
    
    return model


def predict_lstm_regression(features: pd.DataFrame,
                           df: pd.DataFrame,
                           sequence_length: int = 60,
                           test_size: float = 0.2,
                           epochs: int = 50,
                           batch_size: int = 32,
                           lstm_units: int = 50,
                           dropout_rate: float = 0.2,
                           use_gru: bool = False) -> Dict:
    """
    Prediksi menggunakan LSTM/GRU untuk regression
    
    Args:
        features: DataFrame dengan features
        df: DataFrame dengan data original
        sequence_length: Length of sequences
        test_size: Proportion of data untuk validation
        epochs: Number of training epochs
        batch_size: Batch size
        lstm_units: Number of LSTM units
        dropout_rate: Dropout rate
        use_gru: Use GRU instead of LSTM
    
    Returns:
        Dictionary dengan hasil prediksi
    """
    if not HAS_TENSORFLOW:
        raise ImportError("TensorFlow tidak tersedia. Install dengan: pip install tensorflow")
    
    current_price = df['Close'].iloc[-1]
    
    # Pilih features (exclude Close untuk features, tapi gunakan Close sebagai target)
    feature_cols = [col for col in features.columns if col != 'Close']
    
    if len(feature_cols) == 0:
        # Jika tidak ada features, gunakan Close saja
        feature_cols = ['Close']
        X_data = features[feature_cols].values
    else:
        X_data = features[feature_cols].values
    
    y_data = features['Close'].values if 'Close' in features.columns else df['Close'].values
    
    # Normalisasi
    scaler_X = MinMaxScaler()
    scaler_y = MinMaxScaler()
    
    X_scaled = scaler_X.fit_transform(X_data)
    y_scaled = scaler_y.fit_transform(y_data.reshape(-1, 1)).ravel()
    
    # Create sequences
    if len(X_scaled) < sequence_length + 10:
        raise ValueError(f"Data terlalu sedikit untuk LSTM (minimal {sequence_length + 10} data points)")
    
    X, y = create_sequences(X_scaled, sequence_length)
    y_target = y_scaled[sequence_length:]
    
    # Split data
    split_idx = int(len(X) * (1 - test_size))
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y_target[:split_idx], y_target[split_idx:]
    
    # Create model
    model = create_lstm_model(
        sequence_length=sequence_length,
        features_count=X.shape[2],
        lstm_units=lstm_units,
        dropout_rate=dropout_rate,
        use_gru=use_gru
    )
    
    if model is None:
        raise ValueError("Model tidak bisa dibuat")
    
    # Training dengan early stopping
    early_stopping = EarlyStopping(
        monitor='val_loss',
        patience=10,
        restore_best_weights=True
    )
    
    history = model.fit(
        X_train, y_train,
        validation_data=(X_test, y_test),
        epochs=epochs,
        batch_size=batch_size,
        callbacks=[early_stopping],
        verbose=0
    )
    
    # Prediksi validation
    y_pred_scaled = model.predict(X_test, verbose=0).ravel()
    y_pred = scaler_y.inverse_transform(y_pred_scaled.reshape(-1, 1)).ravel()
    y_test_actual = scaler_y.inverse_transform(y_test.reshape(-1, 1)).ravel()
    
    # Evaluasi
    from sklearn.metrics import mean_absolute_error, mean_squared_error
    mae = mean_absolute_error(y_test_actual, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test_actual, y_pred))
    
    # Prediksi untuk hari berikutnya
    # Ambil sequence terakhir
    X_last = X_scaled[-sequence_length:].reshape(1, sequence_length, -1)
    y_next_scaled = model.predict(X_last, verbose=0)[0][0]
    y_next = scaler_y.inverse_transform([[y_next_scaled]])[0][0]
    
    # Prediction interval (menggunakan std dari residuals)
    residuals = y_test_actual - y_pred
    prediction_std = residuals.std()
    prediction_lower = y_next - 1.96 * prediction_std
    prediction_upper = y_next + 1.96 * prediction_std
    
    return {
        'prediction': y_next,
        'prediction_lower': prediction_lower,
        'prediction_upper': prediction_upper,
        'mae': mae,
        'rmse': rmse,
        'model': model,
        'scaler_X': scaler_X,
        'scaler_y': scaler_y,
        'feature_cols': feature_cols,
        'current_price': current_price,
        'sequence_length': sequence_length,
        'model_type': 'GRU' if use_gru else 'LSTM'
    }


def predict_lstm_classification(features: pd.DataFrame,
                                df: pd.DataFrame,
                                sequence_length: int = 60,
                                test_size: float = 0.2,
                                epochs: int = 50,
                                batch_size: int = 32,
                                lstm_units: int = 50,
                                dropout_rate: float = 0.2,
                                use_gru: bool = False) -> Dict:
    """
    Prediksi menggunakan LSTM/GRU untuk classification
    
    Args:
        features: DataFrame dengan features
        df: DataFrame dengan data original
        sequence_length: Length of sequences
        test_size: Proportion of data untuk validation
        epochs: Number of training epochs
        batch_size: Batch size
        lstm_units: Number of LSTM units
        dropout_rate: Dropout rate
        use_gru: Use GRU instead of LSTM
    
    Returns:
        Dictionary dengan hasil prediksi
    """
    if not HAS_TENSORFLOW:
        raise ImportError("TensorFlow tidak tersedia. Install dengan: pip install tensorflow")
    
    current_price = df['Close'].iloc[-1]
    
    # Classification target: 1 jika harga naik, 0 jika turun
    target = (df['Close'].shift(-1) > df['Close']).astype(int)
    target = target[features.index]
    
    # Pilih features
    feature_cols = [col for col in features.columns if col != 'Close']
    
    if len(feature_cols) == 0:
        feature_cols = ['Close']
        X_data = features[feature_cols].values
    else:
        X_data = features[feature_cols].values
    
    y_data = target.values
    
    # Hapus NaN
    valid_idx = ~np.isnan(y_data)
    X_data = X_data[valid_idx]
    y_data = y_data[valid_idx]
    
    if len(X_data) < sequence_length + 10:
        raise ValueError(f"Data terlalu sedikit untuk LSTM (minimal {sequence_length + 10} data points)")
    
    # Normalisasi
    scaler_X = MinMaxScaler()
    X_scaled = scaler_X.fit_transform(X_data)
    
    # Create sequences
    X, y = create_sequences(X_scaled, sequence_length)
    y_target = y_data[sequence_length:]
    
    # Split data
    split_idx = int(len(X) * (1 - test_size))
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y_target[:split_idx], y_target[split_idx:]
    
    # Create model untuk classification
    model = Sequential()
    
    if use_gru:
        model.add(GRU(lstm_units, return_sequences=True, input_shape=(sequence_length, X.shape[2])))
    else:
        model.add(LSTM(lstm_units, return_sequences=True, input_shape=(sequence_length, X.shape[2])))
    
    model.add(Dropout(dropout_rate))
    
    if use_gru:
        model.add(GRU(lstm_units, return_sequences=False))
    else:
        model.add(LSTM(lstm_units, return_sequences=False))
    
    model.add(Dropout(dropout_rate))
    model.add(Dense(1, activation='sigmoid'))  # Binary classification
    
    model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
    
    # Training dengan early stopping
    early_stopping = EarlyStopping(
        monitor='val_loss',
        patience=10,
        restore_best_weights=True
    )
    
    history = model.fit(
        X_train, y_train,
        validation_data=(X_test, y_test),
        epochs=epochs,
        batch_size=batch_size,
        callbacks=[early_stopping],
        verbose=0
    )
    
    # Prediksi validation
    y_pred_proba = model.predict(X_test, verbose=0).ravel()
    y_pred = (y_pred_proba > 0.5).astype(int)
    
    # Evaluasi
    from sklearn.metrics import accuracy_score
    accuracy = accuracy_score(y_test, y_pred)
    
    # Prediksi untuk hari berikutnya
    X_last = X_scaled[-sequence_length:].reshape(1, sequence_length, -1)
    signal_proba = model.predict(X_last, verbose=0)[0][0]
    signal = 1 if signal_proba > 0.5 else 0
    
    signal_text = "BELI" if signal == 1 else "JUAL"
    buy_probability = signal_proba * 100
    
    return {
        'signal': signal_text,
        'buy_probability': buy_probability,
        'sell_probability': (1 - signal_proba) * 100,
        'accuracy': accuracy,
        'model': model,
        'scaler_X': scaler_X,
        'feature_cols': feature_cols,
        'current_price': current_price,
        'sequence_length': sequence_length,
        'model_type': 'GRU' if use_gru else 'LSTM'
    }

