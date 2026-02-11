#!/bin/bash
#
# Start the Allocation POC web interface.
#
# Usage:
#   ./start.sh
#
# Then open http://localhost:5000 in Safari.
# Default password: allocation2024
#

set -e

echo ""
echo "============================================"
echo "  Allocation POC - Setup & Launch"
echo "============================================"
echo ""

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is required but not installed."
    echo "Install it from https://www.python.org/downloads/"
    exit 1
fi

# Install dependencies
echo "Installing dependencies..."
pip3 install -r requirements.txt --quiet 2>/dev/null || pip install -r requirements.txt --quiet

echo ""
echo "Starting the application..."
echo ""
echo "  Open this URL in Safari:"
echo "  --> http://localhost:5000"
echo ""
echo "  Password: allocation2024"
echo ""
echo "  Press Ctrl+C to stop the server."
echo ""

python3 app.py
