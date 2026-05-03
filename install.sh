#!/bin/bash
set -e

echo "📦 Installing Pluck..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required. Please install from https://www.python.org/"
    exit 1
fi

PY_VERSION=$(python3 --version | cut -d' ' -f2)
echo "✓ Python $PY_VERSION found"

# Create venv
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate venv
source .venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip setuptools wheel > /dev/null 2>&1

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt > /dev/null 2>&1

# Install Playwright browsers
echo "📦 Installing Playwright Chromium (this may take a minute)..."
playwright install chromium > /dev/null 2>&1

# Create .env template if not present
if [ ! -f ".env" ]; then
    cat > .env << 'EOF'
# Optional: Add API keys for cloud engines
# ANTHROPIC_API_KEY=sk-ant-...
# OPENAI_API_KEY=sk-...
# GEMINI_API_KEY=...
EOF
    echo "✓ Created .env template — add API keys if needed"
fi

echo ""
echo "✅ Pluck installed successfully!"
echo ""
echo "🚀 Quick start:"
echo "   .venv/bin/python main.py --gui"
echo ""
echo "📚 Learn more:"
echo "   cat README.md"
echo ""
