"""
Unit tests untuk signal quality module
"""

import unittest
import pandas as pd
import numpy as np
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.utils.signal_quality import (
    calculate_signal_confidence,
    filter_signals_by_confidence,
    validate_signal_with_volume,
    calculate_signal_quality_score
)


class TestSignalQuality(unittest.TestCase):
    """Test cases untuk signal quality"""
    
    def setUp(self):
        """Setup test data"""
        self.signals = pd.Series([1, -1, 0, 1, -1])
        self.confidence_scores = pd.Series([0.8, 0.6, 0.0, 0.4, 0.9])
    
    def test_calculate_signal_confidence(self):
        """Test signal confidence calculation"""
        indicators = {
            'rsi': 30.0,
            'macd': 0.5,
            'zscore': -2.0
        }
        confidence = calculate_signal_confidence(1, indicators)
        self.assertIsInstance(confidence, float)
        self.assertGreaterEqual(confidence, 0.0)
        self.assertLessEqual(confidence, 1.0)
    
    def test_calculate_signal_confidence_neutral(self):
        """Test confidence untuk neutral signal"""
        indicators = {'rsi': 50.0}
        confidence = calculate_signal_confidence(0, indicators)
        self.assertEqual(confidence, 0.0)
    
    def test_filter_signals_by_confidence(self):
        """Test signal filtering berdasarkan confidence"""
        filtered = filter_signals_by_confidence(
            self.signals, self.confidence_scores, min_confidence=0.5
        )
        self.assertIsInstance(filtered, pd.Series)
        self.assertEqual(len(filtered), len(self.signals))
        # Signals dengan confidence < 0.5 should be 0
        self.assertEqual(filtered.iloc[2], 0)  # Signal 0
        self.assertEqual(filtered.iloc[3], 0)  # Confidence 0.4
    
    def test_validate_signal_with_volume(self):
        """Test signal validation dengan volume"""
        # Valid: volume > avg_volume * min_ratio
        valid = validate_signal_with_volume(1, 1000, 500, min_volume_ratio=0.8)
        self.assertTrue(valid)
        
        # Invalid: volume < avg_volume * min_ratio
        invalid = validate_signal_with_volume(1, 300, 500, min_volume_ratio=0.8)
        self.assertFalse(invalid)
    
    def test_calculate_signal_quality_score(self):
        """Test signal quality score calculation"""
        score = calculate_signal_quality_score(
            signal=1,
            confidence=0.8,
            volume_confirmed=True,
            market_aligned=True
        )
        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)
        
        # Lower quality dengan volume not confirmed
        score_low = calculate_signal_quality_score(
            signal=1,
            confidence=0.8,
            volume_confirmed=False,
            market_aligned=False
        )
        self.assertLess(score_low, score)


if __name__ == '__main__':
    unittest.main()

