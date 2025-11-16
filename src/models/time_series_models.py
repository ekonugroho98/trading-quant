"""
Time Series Models Module
Implementasi ARIMA dan GARCH untuk analisis dan prediksi
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')


def fit_arima_model(data: pd.Series, order: Tuple[int, int, int] = (1, 1, 1)) -> Dict:
    """
    Fit ARIMA model to time series data
    
    Args:
        data: Time series data
        order: ARIMA order (p, d, q)
    
    Returns:
        Dictionary dengan model results dan predictions
    """
    try:
        from statsmodels.tsa.arima.model import ARIMA
    except ImportError:
        print("⚠️  statsmodels tidak terinstall. Install dengan: pip install statsmodels")
        return {}
    
    try:
        # Remove NaN values
        data_clean = data.dropna()
        
        if len(data_clean) < 50:
            print("⚠️  Data terlalu sedikit untuk ARIMA (minimal 50 data points)")
            return {}
        
        # Fit ARIMA model
        model = ARIMA(data_clean, order=order)
        fitted_model = model.fit()
        
        # Get predictions
        predictions = fitted_model.fittedvalues
        
        # Forecast next period
        forecast = fitted_model.forecast(steps=1)
        
        # Calculate residuals
        residuals = fitted_model.resid
        
        # Model statistics
        aic = fitted_model.aic
        bic = fitted_model.bic
        
        return {
            'model': fitted_model,
            'predictions': predictions,
            'forecast': forecast.iloc[0] if hasattr(forecast, 'iloc') else forecast[0],
            'residuals': residuals,
            'aic': aic,
            'bic': bic,
            'order': order
        }
    except Exception as e:
        print(f"⚠️  Error fitting ARIMA model: {e}")
        return {}


def fit_garch_model(returns: pd.Series, p: int = 1, q: int = 1) -> Dict:
    """
    Fit GARCH model to returns data for volatility forecasting
    
    Args:
        returns: Returns data
        p: GARCH p parameter
        q: GARCH q parameter
    
    Returns:
        Dictionary dengan model results dan volatility forecast
    """
    try:
        from arch import arch_model
    except ImportError:
        print("⚠️  arch tidak terinstall. Install dengan: pip install arch")
        return {}
    
    try:
        # Remove NaN values and convert to percentage
        returns_clean = returns.dropna() * 100
        
        if len(returns_clean) < 50:
            print("⚠️  Data terlalu sedikit untuk GARCH (minimal 50 data points)")
            return {}
        
        # Fit GARCH model
        model = arch_model(returns_clean, vol='Garch', p=p, q=q)
        fitted_model = model.fit(disp='off')
        
        # Get conditional volatility
        conditional_vol = fitted_model.conditional_volatility
        
        # Forecast volatility
        forecast = fitted_model.forecast(horizon=1)
        forecast_variance = forecast.variance.iloc[-1, 0]
        forecast_vol = np.sqrt(forecast_variance)
        
        return {
            'model': fitted_model,
            'conditional_volatility': conditional_vol,
            'forecast_volatility': forecast_vol / 100,  # Convert back to decimal
            'params': fitted_model.params,
            'aic': fitted_model.aic,
            'bic': fitted_model.bic
        }
    except Exception as e:
        print(f"⚠️  Error fitting GARCH model: {e}")
        return {}


def auto_arima(data: pd.Series, max_p: int = 3, max_d: int = 2, max_q: int = 3) -> Dict:
    """
    Automatically find best ARIMA parameters using AIC
    
    Args:
        data: Time series data
        max_p: Maximum p value to test
        max_d: Maximum d value to test
        max_q: Maximum q value to test
    
    Returns:
        Dictionary dengan best model
    """
    try:
        from statsmodels.tsa.arima.model import ARIMA
    except ImportError:
        return {}
    
    best_aic = np.inf
    best_order = None
    best_model = None
    
    # Remove NaN
    data_clean = data.dropna()
    
    if len(data_clean) < 50:
        return {}
    
    # Grid search
    for p in range(max_p + 1):
        for d in range(max_d + 1):
            for q in range(max_q + 1):
                try:
                    model = ARIMA(data_clean, order=(p, d, q))
                    fitted = model.fit()
                    
                    if fitted.aic < best_aic:
                        best_aic = fitted.aic
                        best_order = (p, d, q)
                        best_model = fitted
                except:
                    continue
    
    if best_model is None:
        return {}
    
    # Get forecast
    forecast = best_model.forecast(steps=1)
    
    return {
        'model': best_model,
        'order': best_order,
        'aic': best_aic,
        'forecast': forecast.iloc[0] if hasattr(forecast, 'iloc') else forecast[0],
        'predictions': best_model.fittedvalues
    }


def analyze_time_series(df: pd.DataFrame) -> Dict:
    """
    Comprehensive time series analysis with ARIMA and GARCH
    
    Args:
        df: DataFrame dengan Close prices dan Returns
    
    Returns:
        Dictionary dengan analysis results
    """
    results = {}
    
    # ARIMA for price prediction
    if 'Close' in df.columns:
        print("📈 Fitting ARIMA model for price prediction...")
        arima_results = auto_arima(df['Close'], max_p=2, max_d=1, max_q=2)
        if arima_results:
            results['arima'] = arima_results
            print(f"   ✅ Best ARIMA order: {arima_results.get('order')}")
            print(f"   📊 AIC: {arima_results.get('aic', 0):.2f}")
            print(f"   🔮 Next period forecast: {arima_results.get('forecast', 0):.2f}")
    
    # GARCH for volatility prediction
    if 'Return' in df.columns:
        print("📊 Fitting GARCH model for volatility prediction...")
        garch_results = fit_garch_model(df['Return'], p=1, q=1)
        if garch_results:
            results['garch'] = garch_results
            print(f"   ✅ GARCH(1,1) fitted")
            print(f"   📊 AIC: {garch_results.get('aic', 0):.2f}")
            print(f"   🔮 Forecast volatility: {garch_results.get('forecast_volatility', 0)*100:.2f}%")
    
    return results


def print_time_series_results(results: Dict):
    """Print time series analysis results"""
    if not results:
        return
    
    print("\n" + "=" * 70)
    print("📈 TIME SERIES ANALYSIS (ARIMA & GARCH)")
    print("=" * 70)
    
    # ARIMA results
    if 'arima' in results:
        arima = results['arima']
        print(f"\n📊 ARIMA Model:")
        print(f"   Order: {arima.get('order', 'N/A')}")
        print(f"   AIC: {arima.get('aic', 0):.2f}")
        print(f"   Next Period Forecast: {arima.get('forecast', 0):.2f}")
    
    # GARCH results
    if 'garch' in results:
        garch = results['garch']
        print(f"\n📊 GARCH Model:")
        print(f"   AIC: {garch.get('aic', 0):.2f}")
        print(f"   Forecast Volatility: {garch.get('forecast_volatility', 0)*100:.2f}%")
        
        # Current vs forecast volatility
        if 'conditional_volatility' in garch:
            current_vol = garch['conditional_volatility'].iloc[-1] / 100
            forecast_vol = garch.get('forecast_volatility', 0)
            vol_change = ((forecast_vol - current_vol) / current_vol * 100) if current_vol != 0 else 0
            print(f"   Current Volatility: {current_vol*100:.2f}%")
            print(f"   Volatility Change: {vol_change:+.2f}%")
    
    print("\n" + "=" * 70)
