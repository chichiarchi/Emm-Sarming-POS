#!/bin/bash
# Emma Sarming Store - Linux Setup & Build Script
# Run this once to set up the environment and build the production app.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================"
echo "  Emma Sarming Store - Linux Setup Script"
echo "============================================"

# 1. Install system dependencies
echo ""
echo "[1/5] Installing system dependencies..."
sudo apt-get update -qq
sudo apt-get install -y \
    python3-full \
    python3.12-venv \
    libxcb-cursor0 \
    libxcb-xinerama0 \
    libxcb-randr0 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-render-util0 \
    libdbus-1-3 \
    libegl1 \
    libgl1 \
    libfontconfig1 \
    curl

echo "[1/5] System dependencies installed."

# 2. Create virtual environment
echo ""
echo "[2/5] Creating Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv --without-pip venv
    curl -sS https://bootstrap.pypa.io/get-pip.py | venv/bin/python3
    echo "[2/5] Virtual environment created."
else
    echo "[2/5] Virtual environment already exists, skipping."
fi

# 3. Install Python packages
echo ""
echo "[3/5] Installing Python packages (this may take a few minutes)..."
venv/bin/pip install --quiet -r requirements.txt
echo "[3/5] Python packages installed."

# 4. Initialize database
echo ""
echo "[4/5] Initializing database..."
venv/bin/python -c "import database; database.init_db(); print('Database initialized.')"

# 5. Build production executable
echo ""
echo "[5/5] Building production executable..."
venv/bin/pyinstaller EmmaSarmingStore.spec --clean --noconfirm
echo "[5/5] Build complete!"

echo ""
echo "============================================"
echo "  Setup Complete!"
echo "============================================"
echo ""
echo "  Production build: dist/EmmaSarmingStore/EmmaSarmingStore"
echo ""
echo "  To run the app:"
echo "    Production:  ./dist/EmmaSarmingStore/EmmaSarmingStore"
echo "    Development: ./run.sh"
echo ""
echo "  Default login: admin / admin"
echo ""
