#!/bin/bash
# ============================================
# Meeting Notes — One-Click Launcher for macOS
# ============================================

cd "$(dirname "$0")"

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo ""
    echo "Python 3 is not installed."
    echo ""
    echo "To install it:"
    echo "  1. Open Safari and go to: https://www.python.org/downloads/"
    echo "  2. Click the big yellow 'Download Python' button"
    echo "  3. Open the downloaded file and follow the installer"
    echo "  4. After installing, run this script again"
    echo ""
    read -p "Press Enter to close..."
    exit 1
fi

# Check if dependencies are installed
if ! python3 -c "import sounddevice" 2>/dev/null; then
    echo ""
    echo "Installing required packages (first time only, may take a few minutes)..."
    echo ""
    python3 -m pip install --user -q sounddevice numpy openai-whisper anthropic certifi 2>&1
    echo ""
    echo "Installation complete!"
    echo ""
fi

# Check for BlackHole
if ! system_profiler SPAudioDataType 2>/dev/null | grep -qi "blackhole"; then
    echo ""
    echo "========================================="
    echo "  IMPORTANT: BlackHole is not detected"
    echo "========================================="
    echo ""
    echo "BlackHole is needed to capture your conference call audio."
    echo "Without it, you can only record from your microphone."
    echo ""
    echo "To install BlackHole (free):"
    echo "  1. Open Safari and go to: https://existential.audio/blackhole/"
    echo "  2. Enter your email, click 'Download BlackHole 2ch (Free)'"
    echo "  3. Open the downloaded file and follow the installer"
    echo "  4. After installing, see the README for setup instructions"
    echo ""
    echo "Continuing anyway — you can set up BlackHole later."
    echo ""
fi

# Fix SSL certificates on macOS (needed for Whisper model download)
export SSL_CERT_FILE=$(python3 -c "import certifi; print(certifi.where())" 2>/dev/null)

echo "Starting Meeting Notes..."
python3 -m meeting_notes.gui 2>&1

if [ $? -ne 0 ]; then
    echo ""
    echo "========================================="
    echo "  The app exited with an error."
    echo "========================================="
    echo ""
    echo "Please copy everything above and share it."
    echo ""
    read -p "Press Enter to close..."
fi
