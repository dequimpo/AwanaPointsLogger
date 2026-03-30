#!/bin/bash

# Awana Points Logger - Setup Script
# This script automates the backend setup process

set -e

echo "=========================================="
echo "Awana Points Logger - Setup Script"
echo "=========================================="
echo

# Navigate to backend directory
cd "$(dirname "$0")/backend"
echo "Setting up backend in: $(pwd)"
echo

# Check Python version
echo "Checking Python version..."
python3 --version
echo

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
echo "✓ Virtual environment created"
echo

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"
echo

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip
echo "✓ Pip upgraded"
echo

# Install requirements
echo "Installing dependencies..."
pip install -r requirements.txt
echo "✓ Dependencies installed"
echo

# Verify .env file exists
if [ -f ".env" ]; then
    echo "✓ .env file found"
else
    echo "✗ .env file not found"
    exit 1
fi
echo

echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo
echo "To run the backend server:"
echo "  1. Activate the virtual environment:"
echo "     source backend/venv/bin/activate"
echo "  2. Run the server:"
echo "     python main.py"
echo
echo "The server will run on http://localhost:8000"
echo "API docs will be available at http://localhost:8000/docs"
echo
