#!/bin/bash
# EFA Juxtaposition Analysis - Quick Setup Script for Unix/Linux/macOS
# Copyright (C) 2025 John-Are Hansen
# Licensed under GPL v3.0

echo "========================================="
echo "EFA Juxtaposition Analysis Setup"
echo "========================================="
echo

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ Error: uv is not installed"
    echo
    echo "Please install uv first:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "  source $HOME/.cargo/env"
    echo
    exit 1
fi

echo "✅ uv is installed: $(uv --version)"

# Install dependencies
echo "📦 Installing dependencies..."
uv sync

# Install Windows dependencies if on Windows (via WSL)
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]] || grep -qi microsoft /proc/version 2>/dev/null; then
    echo "🪟 Detected Windows environment, installing Windows-specific dependencies..."
    uv add --optional windows
fi

echo
echo "✅ Setup complete!"
echo
echo "To run the application:"
echo "  uv run python efa_juxtaposition_app/EFA_juxtaposition_v0p9p6.py"
echo
echo "Or create a launcher script:"
echo "  uv run --script efa-juxtaposition"