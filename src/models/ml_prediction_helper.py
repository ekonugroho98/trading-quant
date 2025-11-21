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


def get_ml_prediction_from_file(symbol: Optional[str] = None) -> Optional[Dict]:
    """
    Ambil hasil ML prediction dari file JSON jika ada
    
    Args:
        symbol: Symbol untuk mencari file spesifik (format: BTC-USD atau BTCUSD)
                Jika None, akan coba cari dari config atau gunakan file default
    
    Returns:
        Dictionary dengan hasil ML prediction atau None
    """
    # Cari file di project root (bukan di src/)
    import sys
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    
    # Normalize symbol untuk nama file
    if symbol:
        symbol_normalized = symbol.replace('-USD', '').replace('-', '').upper()
        json_filename = f"ml_prediction_result_{symbol_normalized}.json"
    else:
        # Coba ambil dari config
        try:
            from src.utils.config import SYMBOL
            if SYMBOL:
                symbol_normalized = SYMBOL.replace('-USD', '').replace('-', '').upper()
                json_filename = f"ml_prediction_result_{symbol_normalized}.json"
            else:
                json_filename = "ml_prediction_result.json"  # Fallback ke default
        except:
            json_filename = "ml_prediction_result.json"  # Fallback ke default
    
    json_file = os.path.join(project_root, json_filename)
    
    print(f"🔍 [ML_HELPER] Looking for JSON file at: {json_file}")
    print(f"   Project root: {project_root}")
    print(f"   Current directory: {os.getcwd()}")
    print(f"   Symbol: {symbol_normalized if 'symbol_normalized' in locals() else 'default'}")
    
    # Juga cek di current directory sebagai fallback
    json_file_current = json_filename
    
    # Cek juga file default (untuk backward compatibility)
    json_file_default = os.path.join(project_root, "ml_prediction_result.json")
    json_file_current_default = "ml_prediction_result.json"
    
    if os.path.exists(json_file):
        json_file_to_use = json_file
    elif os.path.exists(json_file_current):
        json_file_to_use = json_file_current
    elif os.path.exists(json_file_default):
        json_file_to_use = json_file_default
        print(f"   ⚠️  Using default file (backward compatibility): {json_file_default}")
    elif os.path.exists(json_file_current_default):
        json_file_to_use = json_file_current_default
        print(f"   ⚠️  Using default file (backward compatibility): {json_file_current_default}")
    else:
        print(f"⚠️  [ML_HELPER] File tidak ditemukan di {json_file} atau {json_file_current}")
        return None
    
    print(f"✅ [ML_HELPER] Using file: {json_file_to_use}")
    
    if os.path.exists(json_file_to_use):
        try:
            with open(json_file_to_use, 'r') as f:
                data = json.load(f)
                # Debug logging
                print(f"🔍 [ML_HELPER] File JSON ditemukan, membaca data...")
                print(f"   File path: {json_file_to_use}")
                print(f"   File size: {os.path.getsize(json_file_to_use)} bytes")
                print(f"   Type: {type(data)}")
                if isinstance(data, dict):
                    print(f"   Keys: {list(data.keys())}")
                    print(f"   accuracy: {data.get('accuracy')} (type: {type(data.get('accuracy'))})")
                    print(f"   sharpe_ratio: {data.get('sharpe_ratio')} (type: {type(data.get('sharpe_ratio'))})")
                    print(f"   expected_value: {data.get('expected_value')} (type: {type(data.get('expected_value'))})")
                return data
        except Exception as e:
            print(f"⚠️  [ML_HELPER] Error reading JSON file: {e}")
            import traceback
            traceback.print_exc()
            return None
    else:
        print(f"⚠️  [ML_HELPER] File {json_file} tidak ditemukan")
    return None

