"""
Unit tests untuk validation metrics
"""

import unittest
import pandas as pd
import numpy as np
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.utils.validation_metrics import (
    calculate_var,
    calculate_cvar,
    calculate_expected_shortfall,
    calculate_maximum_drawdown,
    calculate_win_rate
)


class TestValidationMetrics(unittest.TestCase):
    """Test cases untuk validation metrics"""
    
    def setUp(self):
        """Setup test data"""
        # Generate sample returns
        np.random.seed(42)
        self.returns = pd.Series(np.random.normal(0.001, 0.02, 100))
        self.equity_curve = (1 + self.returns).cumprod()
    
    def test_calculate_var(self):
        """Test VaR calculation"""
        var = calculate_var(self.returns, confidence_level=0.95)
        self.assertIsInstance(var, float)
        self.assertGreaterEqual(var, 0)
    
    def test_calculate_cvar(self):
        """Test CVaR calculation"""
        cvar = calculate_cvar(self.returns, confidence_level=0.95)
        self.assertIsInstance(cvar, float)
        self.assertGreaterEqual(cvar, 0)
        # CVaR should be >= VaR
        var = calculate_var(self.returns, confidence_level=0.95)
        self.assertGreaterEqual(cvar, var)
    
    def test_calculate_expected_shortfall(self):
        """Test Expected Shortfall calculation"""
        es = calculate_expected_shortfall(self.returns, confidence_level=0.95)
        self.assertIsInstance(es, float)
        self.assertGreaterEqual(es, 0)
        # ES should equal CVaR
        cvar = calculate_cvar(self.returns, confidence_level=0.95)
        self.assertAlmostEqual(es, cvar, places=5)
    
    def test_calculate_maximum_drawdown(self):
        """Test maximum drawdown calculation"""
        result = calculate_maximum_drawdown(self.equity_curve)
        self.assertIsInstance(result, dict)
        self.assertIn('max_drawdown', result)
        self.assertLessEqual(result['max_drawdown'], 0)
    
    def test_calculate_win_rate(self):
        """Test win rate calculation"""
        trades = pd.DataFrame({
            'profit': [10, -5, 15, -3, 20, -8, 12]
        })
        result = calculate_win_rate(trades)
        self.assertIsInstance(result, dict)
        self.assertIn('win_rate', result)
        self.assertGreaterEqual(result['win_rate'], 0)
        self.assertLessEqual(result['win_rate'], 100)
    
    def test_empty_returns(self):
        """Test dengan empty returns"""
        empty_returns = pd.Series([], dtype=float)
        var = calculate_var(empty_returns)
        self.assertEqual(var, 0.0)


if __name__ == '__main__':
    unittest.main()

