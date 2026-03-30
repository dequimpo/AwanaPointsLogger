#!/bin/bash

# Awana Points Logger - Setup Normalized Schema
# This script activates the virtualenv and runs the migration
# Usage: ./setup-normalizedschema.sh

set -e

PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$PROJECT_DIR"

echo "🚀 Awana Points Logger - Schema Migration Setup"
echo ""

# Check if backend directory exists
if [ ! -d "backend" ]; then
    echo "❌ Error: backend directory not found!"
    exit 1
fi

# Navigate to backend
cd backend

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found in backend directory!"
    echo "   Please create backend/.env with your Azure credentials"
    exit 1
fi

# Create virtual environment if needed
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install -q -r requirements.txt

# Run migration
echo ""
echo "🔄 Running migration script..."
echo ""
python migrate_sheets.py

MIGRATION_EXIT=$?

echo ""
if [ $MIGRATION_EXIT -eq 0 ]; then
    echo "✅ Migration completed successfully!"
    echo ""
    echo "📊 Next steps:"
    echo "   1. Verify the new sheets in your SharePoint Excel file"
    echo "   2. Run: ./run-servers.sh"
    echo "   3. Test the app with existing and new dates"
    echo "   4. (Optional) Add auto-populate UI from FRONTEND_ENHANCEMENT.md"
    echo ""
    echo "📖 For more details, see:"
    echo "   • IMPLEMENTATION_GUIDE.md"
    echo "   • MIGRATION_GUIDE.md"
    echo "   • FRONTEND_ENHANCEMENT.md"
else
    echo "❌ Migration failed. Please check the errors above."
    exit 1
fi

echo ""
