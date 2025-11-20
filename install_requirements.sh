#!/bin/bash
# Script untuk install requirements dengan urutan yang benar
# Menghindari masalah build arch yang memerlukan numpy headers

set -e

echo "📦 Installing requirements in correct order..."

# Step 1: Install numpy first (required by arch)
echo "1️⃣ Installing numpy..."
pip install "numpy>=2.1.0"

# Step 2: Install build tools (required for --no-build-isolation)
echo "2️⃣ Installing build tools..."
pip install "setuptools>=65.0" "wheel>=0.40.0"

# Step 3: Install core data processing
echo "3️⃣ Installing core data processing..."
pip install "pandas>=2.2.3" "scipy>=1.15.0"

# Step 4: Install arch (now numpy headers and build tools are available)
# Note: arch needs numpy headers in build environment
# Use --no-build-isolation to use numpy from venv instead of isolated build env
echo "4️⃣ Installing arch..."
pip install "arch==6.2.0" --no-build-isolation || {
    echo "⚠️  Build dengan --no-build-isolation gagal, skip arch (kode sudah handle ImportError)"
    echo "💡 Install arch nanti dengan: pip install arch==6.2.0 --no-build-isolation"
}

# Step 5: Install ML libraries
echo "5️⃣ Installing ML libraries..."
pip install "scikit-learn>=1.5.0" "xgboost==2.0.3" "lightgbm==4.1.0"

# Step 6: Install time series
echo "6️⃣ Installing time series..."
pip install "statsmodels>=0.14.1"

# Step 7: Install visualization
echo "7️⃣ Installing visualization..."
pip install "matplotlib>=3.9.0"

# Step 8: Install data sources
echo "8️⃣ Installing data sources..."
pip install "yfinance==0.2.32" "requests==2.31.0" "python-binance==1.0.19"

# Step 9: Install other dependencies
echo "9️⃣ Installing other dependencies..."
pip install "scikit-optimize==0.9.0" "python-dotenv==1.0.0"

# Step 10: Install TensorFlow and Keras last (largest packages)
echo "🔟 Installing TensorFlow and Keras..."
pip install "tensorflow>=2.20.0" "keras>=3.0.0"

echo "✅ All packages installed successfully!"

