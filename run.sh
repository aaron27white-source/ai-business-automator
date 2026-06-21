#!/usr/bin/env bash
# AI Business Automator — Launch Script
set -euo pipefail

cd "$(dirname "$0")"

VENV_DIR=".venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "🔧 Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install -r requirements.txt
    echo "✅ Dependencies installed"
fi

if [ ! -f "$HOME/.hermes/.env" ]; then
    echo "⚠️  Warning: ~/.hermes/.env not found"
    echo "   Create it with: OPENROUTER_API_KEY=sk-..."
fi

echo "🚀 AI Business Automator — http://localhost:${PORT:-8770}"
exec "$VENV_DIR/bin/python3" server.py "$@"
