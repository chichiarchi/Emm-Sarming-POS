#!/bin/bash
# Emma Sarming Store - Development Runner
# Runs the app directly via Python (fastest for development)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check for virtual environment
if [ ! -f "venv/bin/python" ]; then
    echo "[ERROR] Virtual environment not found."
    echo "Run setup_linux.sh first to set up the environment."
    exit 1
fi

echo "Starting Emma Sarming Store (Development Mode)..."
venv/bin/python app.py
