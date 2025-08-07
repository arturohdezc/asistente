#!/bin/bash

echo "🔧 Installing missing dependencies for Replit..."
echo "================================================"

# Install python-telegram-bot which is not available in Nix
echo "📦 Installing python-telegram-bot..."
python -m pip install --break-system-packages "python-telegram-bot>=21.0,<22.0"

echo "✅ Installation complete!"
echo "🚀 You can now run: python run_simple.py"