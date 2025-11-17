"""
Unit tests untuk data quality module
"""

import unittest
import pandas as pd
import numpy as np
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.utils.data_quality import (
    validate_dataframe,
    detect_outliers_iqr,
    detect_outliers_zscore,
    handle_outliers,
    impute_missing_data,
    validate_ohlcv_data,
    clean_trading_data
)


class TestDataQuality(unittest.TestCase):
    """Test cases untuk data quality"""
    
    def setUp(self):
        """Setup test data"""
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        self.df = pd.DataFrame({
            'date': dates,
            'Open': np.random.uniform(100, 200, 100),
            'High': np.random.uniform(200, 300, 100),
            'Low': np.random.uniform(50, 100, 100),
            'Close': np.random.uniform(100, 200, 100),
            'Volume': np.random.uniform(1000, 10000, 100)
        })
        # Ensure High >= Low, High >= Open, High >= Close, etc.
        self.df['High'] = self.df[['Open', 'Close', 'Low']].max(axis=1) * 1.1
        self.df['Low'] = self.df[['Open', 'Close', 'High']].min(axis=1) * 0.9
    
    def test_validate_dataframe(self):
        """Test DataFrame validation"""
        result = validate_dataframe(self.df, required_columns=['Open', 'Close'])
        self.assertIsInstance(result, dict)
        self.assertIn('valid', result)
        self.assertTrue(result['valid'])
    
    def test_validate_dataframe_missing_columns(self):
        """Test validation dengan missing columns"""
        result = validate_dataframe(self.df, required_columns=['MissingColumn'])
        self.assertFalse(result['valid'])
        self.assertGreater(len(result['errors']), 0)
    
    def test_detect_outliers_iqr(self):
        """Test IQR outlier detection"""
        outliers = detect_outliers_iqr(self.df['Close'])
        self.assertIsInstance(outliers, pd.Series)
        self.assertEqual(len(outliers), len(self.df))
    
    def test_detect_outliers_zscore(self):
        """Test Z-score outlier detection"""
        outliers = detect_outliers_zscore(self.df['Close'])
        self.assertIsInstance(outliers, pd.Series)
        self.assertEqual(len(outliers), len(self.df))
    
    def test_handle_outliers_clip(self):
        """Test outlier handling dengan clip method"""
        df_with_outliers = self.df.copy()
        df_with_outliers.loc[0, 'Close'] = 10000  # Add outlier
        result = handle_outliers(df_with_outliers, method='clip')
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), len(df_with_outliers))
    
    def test_impute_missing_data(self):
        """Test missing data imputation"""
        df_with_missing = self.df.copy()
        df_with_missing.loc[0:5, 'Close'] = np.nan
        result = impute_missing_data(df_with_missing, method='forward_fill')
        self.assertIsInstance(result, pd.DataFrame)
        self.assertFalse(result['Close'].isnull().any())
    
    def test_validate_ohlcv_data(self):
        """Test OHLCV data validation"""
        result = validate_ohlcv_data(self.df)
        self.assertIsInstance(result, dict)
        self.assertIn('valid', result)
        self.assertTrue(result['valid'])
    
    def test_clean_trading_data(self):
        """Test comprehensive data cleaning"""
        df_dirty = self.df.copy()
        df_dirty.loc[0, 'Close'] = np.nan  # Add missing
        df_dirty.loc[1, 'Close'] = 10000  # Add outlier
        result = clean_trading_data(df_dirty)
        self.assertIsInstance(result, pd.DataFrame)
        self.assertFalse(result['Close'].isnull().any())


if __name__ == '__main__':
    unittest.main()

