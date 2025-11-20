"""
Data Quality Module
Data validation, outlier detection, dan missing data handling
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from scipy import stats
import logging

logger = logging.getLogger('data_quality')


def validate_dataframe(df: pd.DataFrame, 
                      required_columns: Optional[List[str]] = None,
                      min_rows: int = 1) -> Dict[str, Any]:
    """
    Validate DataFrame structure dan completeness
    
    Args:
        df: DataFrame to validate
        required_columns: List of required columns
        min_rows: Minimum number of rows required
    
    Returns:
        Dictionary dengan validation results
    """
    results = {
        'valid': True,
        'errors': [],
        'warnings': []
    }
    
    # Check if DataFrame is empty
    if df is None or df.empty:
        results['valid'] = False
        results['errors'].append("DataFrame is None or empty")
        return results
    
    # Check minimum rows
    if len(df) < min_rows:
        results['valid'] = False
        results['errors'].append(f"DataFrame has {len(df)} rows, minimum required: {min_rows}")
    
    # Check required columns
    if required_columns:
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            results['valid'] = False
            results['errors'].append(f"Missing required columns: {missing_columns}")
    
    # Check for completely empty columns
    empty_columns = df.columns[df.isnull().all()].tolist()
    if empty_columns:
        results['warnings'].append(f"Completely empty columns: {empty_columns}")
    
    return results


def detect_outliers_iqr(series: pd.Series, 
                       multiplier: float = 1.5) -> pd.Series:
    """
    Detect outliers menggunakan IQR (Interquartile Range) method
    
    Args:
        series: Series to analyze
        multiplier: IQR multiplier (default 1.5)
    
    Returns:
        Boolean Series indicating outliers
    """
    Q1 = series.quantile(0.25)
    Q3 = series.quantile(0.75)
    IQR = Q3 - Q1
    
    lower_bound = Q1 - multiplier * IQR
    upper_bound = Q3 + multiplier * IQR
    
    outliers = (series < lower_bound) | (series > upper_bound)
    return outliers


def detect_outliers_zscore(series: pd.Series, 
                          threshold: float = 3.0) -> pd.Series:
    """
    Detect outliers menggunakan Z-score method
    
    Args:
        series: Series to analyze
        threshold: Z-score threshold (default 3.0)
    
    Returns:
        Boolean Series indicating outliers
    """
    z_scores = np.abs(stats.zscore(series.dropna()))
    outliers = pd.Series(False, index=series.index)
    outliers[series.dropna().index] = z_scores > threshold
    return outliers


def handle_outliers(df: pd.DataFrame,
                   columns: Optional[List[str]] = None,
                   method: str = 'clip',
                   outlier_detection: str = 'iqr') -> pd.DataFrame:
    """
    Handle outliers dalam DataFrame
    
    Args:
        df: DataFrame to process
        columns: Columns to process (None = all numeric columns)
        method: Handling method ('clip', 'remove', 'winsorize')
        outlier_detection: Detection method ('iqr', 'zscore')
    
    Returns:
        DataFrame dengan outliers handled
    """
    df = df.copy()
    
    if columns is None:
        columns = df.select_dtypes(include=[np.number]).columns.tolist()
    
    for col in columns:
        if col not in df.columns:
            continue
        
        # Detect outliers
        if outlier_detection == 'iqr':
            outliers = detect_outliers_iqr(df[col])
        elif outlier_detection == 'zscore':
            outliers = detect_outliers_zscore(df[col])
        else:
            logger.warning(f"Unknown outlier detection method: {outlier_detection}")
            continue
        
        outlier_count = outliers.sum()
        if outlier_count > 0:
            logger.info(f"Found {outlier_count} outliers in column {col}")
            
            if method == 'clip':
                # Clip to IQR bounds
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                df[col] = df[col].clip(lower=lower_bound, upper=upper_bound)
            
            elif method == 'remove':
                # Remove outliers
                df = df[~outliers]
            
            elif method == 'winsorize':
                # Winsorize (cap at percentiles)
                lower_percentile = df[col].quantile(0.05)
                upper_percentile = df[col].quantile(0.95)
                df[col] = df[col].clip(lower=lower_percentile, upper=upper_percentile)
    
    return df


def impute_missing_data(df: pd.DataFrame,
                       method: str = 'forward_fill',
                       columns: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Impute missing data dalam DataFrame
    
    Args:
        df: DataFrame to process
        method: Imputation method ('forward_fill', 'backward_fill', 'mean', 'median', 'interpolate')
        columns: Columns to process (None = all columns)
    
    Returns:
        DataFrame dengan missing data imputed
    """
    df = df.copy()
    
    if columns is None:
        columns = df.columns.tolist()
    
    for col in columns:
        if col not in df.columns:
            continue
        
        missing_count = df[col].isnull().sum()
        if missing_count > 0:
            logger.info(f"Imputing {missing_count} missing values in column {col} using {method}")
            
            if method == 'forward_fill':
                df[col] = df[col].fillna(method='ffill')
            elif method == 'backward_fill':
                df[col] = df[col].fillna(method='bfill')
            elif method == 'mean':
                df[col] = df[col].fillna(df[col].mean())
            elif method == 'median':
                df[col] = df[col].fillna(df[col].median())
            elif method == 'interpolate':
                df[col] = df[col].interpolate()
            else:
                logger.warning(f"Unknown imputation method: {method}")
    
    return df


def validate_ohlcv_data(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Validate OHLCV (Open, High, Low, Close, Volume) data
    
    Args:
        df: DataFrame dengan OHLCV data
    
    Returns:
        Dictionary dengan validation results
    """
    results = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'stats': {}
    }
    
    required_columns = ['Open', 'High', 'Low', 'Close']
    
    # Basic validation
    validation = validate_dataframe(df, required_columns=required_columns)
    results['valid'] = validation['valid']
    results['errors'].extend(validation['errors'])
    results['warnings'].extend(validation['warnings'])
    
    if not results['valid']:
        return results
    
    # Check OHLC relationships
    invalid_ohlc = (
        (df['High'] < df['Low']) |
        (df['High'] < df['Open']) |
        (df['High'] < df['Close']) |
        (df['Low'] > df['Open']) |
        (df['Low'] > df['Close'])
    )
    
    if invalid_ohlc.any():
        invalid_count = invalid_ohlc.sum()
        results['warnings'].append(f"Found {invalid_count} rows with invalid OHLC relationships")
        results['stats']['invalid_ohlc_count'] = invalid_count
    
    # Check for negative prices
    price_columns = ['Open', 'High', 'Low', 'Close']
    for col in price_columns:
        negative_count = (df[col] < 0).sum()
        if negative_count > 0:
            results['errors'].append(f"Found {negative_count} negative values in {col}")
            results['valid'] = False
    
    # Check for zero volume (warning, not error)
    if 'Volume' in df.columns:
        zero_volume_count = (df['Volume'] == 0).sum()
        if zero_volume_count > 0:
            results['warnings'].append(f"Found {zero_volume_count} rows with zero volume")
            results['stats']['zero_volume_count'] = zero_volume_count
    
    # Check for missing data
    for col in required_columns:
        missing_count = df[col].isnull().sum()
        if missing_count > 0:
            results['warnings'].append(f"Found {missing_count} missing values in {col}")
            results['stats'][f'{col}_missing'] = missing_count
    
    return results


def calculate_data_quality_score(df: pd.DataFrame,
                                required_columns: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Calculate comprehensive data quality score (0.0 - 1.0)
    
    Args:
        df: DataFrame untuk evaluate
        required_columns: List of required columns
    
    Returns:
        Dictionary dengan quality score dan details
    """
    if required_columns is None:
        required_columns = ['Open', 'High', 'Low', 'Close']
    
    score = 1.0
    details = {
        'checks': {},
        'warnings': [],
        'errors': []
    }
    
    # Check 1: Data completeness (30% weight)
    if df is None or df.empty:
        details['errors'].append("DataFrame is None or empty")
        return {
            'score': 0.0,
            'details': details,
            'grade': 'F',
            'recommendation': 'Data tidak valid'
        }
    
    completeness_score = 1.0
    if len(df) < 50:
        completeness_score = len(df) / 50.0
        details['warnings'].append(f"Data terlalu sedikit: {len(df)} rows (minimal 50)")
    
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        completeness_score = 0.0
        details['errors'].append(f"Missing required columns: {missing_cols}")
    
    details['checks']['completeness'] = completeness_score
    score *= completeness_score ** 0.3
    
    # Check 2: Missing data (20% weight)
    missing_data_score = 1.0
    if len(df) > 0:
        missing_pct = df[required_columns].isnull().sum().sum() / (len(df) * len(required_columns))
        missing_data_score = 1.0 - missing_pct
        if missing_pct > 0.1:
            details['warnings'].append(f"Missing data: {missing_pct*100:.1f}%")
    
    details['checks']['missing_data'] = missing_data_score
    score *= missing_data_score ** 0.2
    
    # Check 3: Data validity (20% weight)
    validity_score = 1.0
    if all(col in df.columns for col in ['Open', 'High', 'Low', 'Close']):
        invalid_ohlc = (
            (df['High'] < df['Low']) |
            (df['High'] < df['Open']) |
            (df['High'] < df['Close']) |
            (df['Low'] > df['Open']) |
            (df['Low'] > df['Close'])
        )
        invalid_count = invalid_ohlc.sum()
        if invalid_count > 0:
            invalid_pct = invalid_count / len(df)
            validity_score = 1.0 - invalid_pct
            details['warnings'].append(f"Invalid OHLC: {invalid_count} rows ({invalid_pct*100:.1f}%)")
        
        # Check for negative prices
        negative_prices = (df[required_columns] < 0).any().any()
        if negative_prices:
            validity_score = 0.0
            details['errors'].append("Found negative prices")
    
    details['checks']['validity'] = validity_score
    score *= validity_score ** 0.2
    
    # Check 4: Outliers (15% weight)
    outlier_score = 1.0
    if 'Close' in df.columns:
        outliers = detect_outliers_zscore(df['Close'], threshold=3.0)
        outlier_pct = outliers.sum() / len(df)
        if outlier_pct > 0.05:  # More than 5% outliers
            outlier_score = 1.0 - min(0.5, outlier_pct * 2)  # Max penalty 50%
            details['warnings'].append(f"High outlier rate: {outlier_pct*100:.1f}%")
    
    details['checks']['outliers'] = outlier_score
    score *= outlier_score ** 0.15
    
    # Check 5: Data consistency (15% weight)
    consistency_score = 1.0
    if 'Close' in df.columns and len(df) > 1:
        # Check for unrealistic price changes
        returns = df['Close'].pct_change().abs()
        extreme_changes = (returns > 0.5).sum()  # More than 50% change
        if extreme_changes > 0:
            extreme_pct = extreme_changes / len(df)
            consistency_score = 1.0 - min(0.3, extreme_pct * 3)
            details['warnings'].append(f"Extreme price changes: {extreme_changes} occurrences")
    
    details['checks']['consistency'] = consistency_score
    score *= consistency_score ** 0.15
    
    # Calculate final score
    score = max(0.0, min(1.0, score))
    
    # Grade
    if score >= 0.9:
        grade = 'A'
        recommendation = 'Data quality excellent, siap untuk prediksi'
    elif score >= 0.75:
        grade = 'B'
        recommendation = 'Data quality baik, beberapa warnings perlu diperhatikan'
    elif score >= 0.6:
        grade = 'C'
        recommendation = 'Data quality cukup, disarankan cleaning sebelum prediksi'
    elif score >= 0.4:
        grade = 'D'
        recommendation = 'Data quality buruk, perlu cleaning dan validation'
    else:
        grade = 'F'
        recommendation = 'Data quality sangat buruk, tidak disarankan untuk prediksi'
    
    return {
        'score': score,
        'grade': grade,
        'details': details,
        'recommendation': recommendation
    }


def clean_trading_data(df: pd.DataFrame,
                      handle_outliers: bool = True,
                      impute_missing: bool = True,
                      remove_invalid_ohlc: bool = True) -> pd.DataFrame:
    """
    Comprehensive data cleaning untuk trading data
    
    Args:
        df: DataFrame dengan trading data
        handle_outliers: Whether to handle outliers
        impute_missing: Whether to impute missing data
        remove_invalid_ohlc: Whether to remove invalid OHLC rows
    
    Returns:
        Cleaned DataFrame
    """
    df = df.copy()
    
    # Validate data
    validation = validate_ohlcv_data(df)
    if not validation['valid']:
        logger.error(f"Data validation failed: {validation['errors']}")
        raise ValueError(f"Invalid data: {validation['errors']}")
    
    # Remove invalid OHLC rows
    if remove_invalid_ohlc:
        invalid_ohlc = (
            (df['High'] < df['Low']) |
            (df['High'] < df['Open']) |
            (df['High'] < df['Close']) |
            (df['Low'] > df['Open']) |
            (df['Low'] > df['Close'])
        )
        if invalid_ohlc.any():
            logger.info(f"Removing {invalid_ohlc.sum()} rows with invalid OHLC")
            df = df[~invalid_ohlc]
    
    # Handle outliers
    if handle_outliers:
        price_columns = ['Open', 'High', 'Low', 'Close']
        df = handle_outliers(df, columns=price_columns, method='clip')
    
    # Impute missing data
    if impute_missing:
        df = impute_missing_data(df, method='forward_fill')
        # If still missing, use backward fill
        if df.isnull().any().any():
            df = impute_missing_data(df, method='backward_fill')
    
    return df

