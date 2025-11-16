"""
ML Prediction Helper Module
Helper untuk menjalankan ML prediction dan mendapatkan hasilnya
"""

import subprocess
import sys
import json
import os
from typing import Dict, Optional


def run_ml_prediction_and_get_results() -> Optional[Dict]:
    """
    Jalankan prediksi_next_day.py dan ambil hasilnya
    
    Returns:
        Dictionary dengan hasil ML prediction atau None jika error
    """
    try:
        # Jalankan prediksi_next_day.py dan capture output
        result = subprocess.run(
            [sys.executable, "prediksi_next_day.py"],
            capture_output=True,
            text=True,
            check=False
        )
        
        # Parse output untuk mendapatkan informasi
        output = result.stdout
        
        # Extract informasi dari output
        ml_result = {}
        
        # Model info
        if "Model: Ensemble" in output:
            ml_result['model'] = "Ensemble (RandomForestClassifier)"
        elif "Model: RandomForestClassifier" in output:
            ml_result['model'] = "RandomForestClassifier"
        elif "Model: LinearRegression" in output:
            ml_result['model'] = "LinearRegression"
        else:
            ml_result['model'] = "Unknown"
        
        # Signal
        if "Signal: BELI" in output:
            ml_result['signal'] = "BELI"
        elif "Signal: JUAL" in output:
            ml_result['signal'] = "JUAL"
        else:
            ml_result['signal'] = "HOLD"
        
        # Probabilitas
        import re
        buy_prob_match = re.search(r'Probabilitas BELI: ([\d.]+)%', output)
        sell_prob_match = re.search(r'Probabilitas JUAL: ([\d.]+)%', output)
        
        if buy_prob_match:
            ml_result['buy_prob'] = float(buy_prob_match.group(1))
        if sell_prob_match:
            ml_result['sell_prob'] = float(sell_prob_match.group(1))
        
        # Accuracy
        accuracy_match = re.search(r'Accuracy Score: ([\d.]+)%', output)
        if accuracy_match:
            ml_result['accuracy'] = float(accuracy_match.group(1))
        
        # Expected Value
        expected_match = re.search(r'Expected Value: ([\d.+-]+)%', output)
        if expected_match:
            ml_result['expected_value'] = float(expected_match.group(1))
        
        # Sharpe Ratio
        sharpe_match = re.search(r'Sharpe Ratio: ([\d.+-]+)', output)
        if sharpe_match:
            ml_result['sharpe_ratio'] = float(sharpe_match.group(1))
        
        # Data info
        data_match = re.search(r'Data Historis: (\d+) records', output)
        if data_match:
            ml_result['data_records'] = int(data_match.group(1))
        
        # Features
        features_match = re.search(r'Feature Engineering: (\d+) fitur', output)
        if features_match:
            ml_result['features_count'] = int(features_match.group(1))
        
        return ml_result if ml_result else None
        
    except Exception as e:
        print(f"⚠️  Error mendapatkan hasil ML prediction: {e}")
        return None


def get_ml_prediction_from_file() -> Optional[Dict]:
    """
    Ambil hasil ML prediction dari file JSON jika ada
    
    Returns:
        Dictionary dengan hasil ML prediction atau None
    """
    json_file = "ml_prediction_result.json"
    if os.path.exists(json_file):
        try:
            with open(json_file, 'r') as f:
                return json.load(f)
        except:
            pass
    return None

