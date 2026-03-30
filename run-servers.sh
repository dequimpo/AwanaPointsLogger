#!/bin/bash

# Awana Points Logger - Run Backend & Frontend Together
# This script starts both the FastAPI backend and Expo frontend
# cd /Users/deq/Documents/DBDNJ_Dev/AwanaPointsLogger ./run-servers.sh

PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$PROJECT_DIR"

echo "🚀 Awana Points Logger - Starting Servers..."
echo ""

# Setup NVM and Node
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
nvm use 18.20.8

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down servers..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit
}

# Trap Ctrl+C to cleanup
trap cleanup EXIT INT TERM

# Start Backend (FastAPI)
echo "📦 Starting Backend Server (FastAPI)..."
if [ ! -d "venv" ]; then
    echo "   Creating Python virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

# Check if requirements need to be installed
if ! python3 -c "import msal" 2>/dev/null; then
    echo "   Installing Python dependencies..."
    pip install -q -r requirements.txt
fi

cd backend
python3 main.py &
BACKEND_PID=$!
cd ..
echo "   Backend running with PID $BACKEND_PID"
echo "   📍 http://localhost:8000/health"
echo "   📍 http://localhost:8000/docs"
echo ""

# Wait for backend to start
sleep 3

# Start Frontend (Expo)
echo "⚛️  Starting Frontend Server (Expo)..."
npm start &
FRONTEND_PID=$!
echo "   Frontend running with PID $FRONTEND_PID"
echo "   📍 http://localhost:8081"
echo ""

echo "✅ Both servers are running!"
echo ""
echo "🌐 Access the app at: http://localhost:8081"
echo "📊 API docs at: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all servers"
echo ""

# Keep the script running
wait
