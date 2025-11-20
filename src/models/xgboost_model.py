"""
XGBoost Model Implementation
Advanced gradient boosting for classification and regression
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

try:
    from xgboost import XGBRegressor, XGBClassifier
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False
    print("⚠️  xgboost tidak terinstall. Install dengan: pip install xgboost")


def predict_xgboost_classification(features: pd.DataFrame, 
                                   df: pd.DataFrame,
                                   test_size: float = 0.2,
                                   n_estimators: int = 200,
                                   max_depth: int = 6,
                                   learning_rate: float = 0.1,
                                   subsample: float = 0.8,
                                   colsample_bytree: float = 0.8,
                                   random_state: int = 42) -> Dict:
    """
    Prediksi menggunakan XGBoost Classifier
    
    Args:
        features: DataFrame dengan features
        df: DataFrame dengan data original
        test_size: Proportion of data untuk validation
        n_estimators: Number of boosting rounds
        max_depth: Maximum tree depth
        learning_rate: Learning rate
        subsample: Subsample ratio
        colsample_bytree: Column subsample ratio
        random_state: Random seed
    
    Returns:
        Dictionary dengan hasil prediksi
    """
    if not HAS_XGBOOST:
        raise ImportError("XGBoost tidak tersedia. Install dengan: pip install xgboost")
    
    current_price = df['Close'].iloc[-1]
    
    # Classification: Prediksi Beli (1) atau Jual (0)
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
        raise ValueError("Data terlalu sedikit untuk XGBoost (minimal 50 data points)")
    
    # Split data
    split_idx = int(len(X) * (1 - test_size))
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    # Training dengan early stopping
    model = XGBClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        learning_rate=learning_rate,
        subsample=subsample,
        colsample_bytree=colsample_bytree,
        random_state=random_state,
        eval_metric='logloss',
        use_label_encoder=False
    )
    
    # Early stopping jika validation set cukup besar
    if len(X_test) > 10:
        model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            early_stopping_rounds=20,
            verbose=False
        )
    else:
        model.fit(X_train, y_train)
    
    # Prediksi validation
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)
    
    # Evaluasi
    from sklearn.metrics import accuracy_score
    accuracy = accuracy_score(y_test, y_pred)
    
    # Prediksi untuk hari berikutnya
    X_last = X[-1:].reshape(1, -1)
    signal_proba = model.predict_proba(X_last)[0]
    signal = model.predict(X_last)[0]
    
    signal_text = "BELI" if signal == 1 else "JUAL"
    buy_probability = signal_proba[1] * 100
    
    # Feature importance
    feature_importance = pd.DataFrame({
        'feature': feature_cols,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    return {
        'signal': signal_text,
        'buy_probability': buy_probability,
        'sell_probability': signal_proba[0] * 100,
        'accuracy': accuracy,
        'model': model,
        'feature_cols': feature_cols,
        'current_price': current_price,
        'feature_importance': feature_importance
    }


def predict_xgboost_regression(features: pd.DataFrame,
                               df: pd.DataFrame,
                               test_size: float = 0.2,
                               n_estimators: int = 200,
                               max_depth: int = 6,
                               learning_rate: float = 0.1,
                               subsample: float = 0.8,
                               colsample_bytree: float = 0.8,
                               random_state: int = 42) -> Dict:
    """
    Prediksi menggunakan XGBoost Regressor
    
    Args:
        features: DataFrame dengan features
        df: DataFrame dengan data original
        test_size: Proportion of data untuk validation
        n_estimators: Number of boosting rounds
        max_depth: Maximum tree depth
        learning_rate: Learning rate
        subsample: Subsample ratio
        colsample_bytree: Column subsample ratio
        random_state: Random seed
    
    Returns:
        Dictionary dengan hasil prediksi
    """
    if not HAS_XGBOOST:
        raise ImportError("XGBoost tidak tersedia. Install dengan: pip install xgboost")
    
    current_price = df['Close'].iloc[-1]
    
    feature_cols = [col for col in features.columns if col != 'Close']
    X = features[feature_cols].values
    y = features['Close'].values
    
    # Hapus NaN
    valid_idx = ~np.isnan(y)
    X = X[valid_idx]
    y = y[valid_idx]
    
    if len(X) < 50:
        raise ValueError("Data terlalu sedikit untuk XGBoost (minimal 50 data points)")
    
    # Split data
    split_idx = int(len(X) * (1 - test_size))
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    # Training dengan early stopping
    model = XGBRegressor(
        n_estimators=n_estimators,
        max_depth=max_depth,
        learning_rate=learning_rate,
        subsample=subsample,
        colsample_bytree=colsample_bytree,
        random_state=random_state,
        eval_metric='rmse'
    )
    
    # Early stopping jika validation set cukup besar
    if len(X_test) > 10:
        model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            early_stopping_rounds=20,
            verbose=False
        )
    else:
        model.fit(X_train, y_train)
    
    # Prediksi validation
    y_pred = model.predict(X_test)
    
    # Evaluasi
    from sklearn.metrics import mean_absolute_error, mean_squared_error
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    
    # Prediksi untuk hari berikutnya
    X_last = X[-1:].reshape(1, -1)
    prediction = model.predict(X_last)[0]
    
    # Prediction intervals (menggunakan quantile regression atau std dari residuals)
    residuals = y_test - y_pred
    prediction_std = residuals.std()
    prediction_lower = prediction - 1.96 * prediction_std  # 95% CI
    prediction_upper = prediction + 1.96 * prediction_std
    
    # Feature importance
    feature_importance = pd.DataFrame({
        'feature': feature_cols,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    return {
        'prediction': prediction,
        'prediction_lower': prediction_lower,
        'prediction_upper': prediction_upper,
        'mae': mae,
        'rmse': rmse,
        'model': model,
        'feature_cols': feature_cols,
        'current_price': current_price,
        'feature_importance': feature_importance
    }

