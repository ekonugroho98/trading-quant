#!/bin/bash
# Script untuk menjalankan aplikasi trading quant di virtual environment

# Warna untuk output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Trading Quant - Setup & Run${NC}"
echo "=================================="
echo ""

# Cek apakah venv sudah ada
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment tidak ditemukan. Membuat venv baru...${NC}"
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Gagal membuat virtual environment${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Virtual environment berhasil dibuat${NC}"
fi

# Aktifkan venv
echo -e "${GREEN}📦 Mengaktifkan virtual environment...${NC}"
source venv/bin/activate

# Upgrade pip
echo -e "${GREEN}⬆️  Memperbarui pip...${NC}"
pip install --upgrade pip --quiet

# Install dependencies jika requirements.txt ada
if [ -f "requirements.txt" ]; then
    echo -e "${GREEN}📥 Menginstall dependencies dari requirements.txt...${NC}"
    pip install -r requirements.txt --quiet
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Gagal menginstall dependencies${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Dependencies berhasil diinstall${NC}"
else
    echo -e "${YELLOW}⚠️  requirements.txt tidak ditemukan${NC}"
fi

echo ""
echo -e "${GREEN}✅ Setup selesai!${NC}"
echo ""
echo "Untuk menjalankan aplikasi:"
echo "  1. Aktifkan venv: source venv/bin/activate"
echo "  2. Jalankan script: python run_all_analysis.py"
echo ""
echo "Atau jalankan langsung:"
echo "  ./run.sh --run"
echo ""

# Jika ada flag --run, langsung jalankan aplikasi
if [ "$1" == "--run" ]; then
    echo -e "${GREEN}🚀 Menjalankan aplikasi...${NC}"
    echo ""
    python run_all_analysis.py
fi

