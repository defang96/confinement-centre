#!/bin/bash
# ─────────────────────────────────────────────────────────────
#  Confinement Centre — Start Script
#  Run this once to set up and launch the app.
#  Usage:  bash start.sh
# ─────────────────────────────────────────────────────────────

echo "🌸 Confinement Centre — Starting up..."
echo ""

# Move into backend folder
cd "$(dirname "$0")/backend"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.9+ and try again."
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt --quiet

echo ""
echo "✅ Ready! Starting server..."
echo ""
echo "  🌐 API:      http://localhost:8000"
echo "  📖 API Docs: http://localhost:8000/docs"
echo ""
echo "  Open frontend/index.html in your browser to use the app."
echo "  Press Ctrl+C to stop the server."
echo ""

python3 main.py
