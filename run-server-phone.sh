#!/bin/bash

# Awana Points Logger - Run for Physical Phone Testing 
# Usage: ./run-server-phone.sh
# Requires: Expo Go installed on phone, phone on same Wi-Fi as this Mac

PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$PROJECT_DIR"

echo "📱 Awana Points Logger - Phone Testing Mode"
echo ""

# Detect Mac's local Wi-Fi IP
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null)
if [ -z "$LOCAL_IP" ]; then
    echo "❌ Could not detect local IP address."
    echo "   Make sure you're connected to Wi-Fi."
    echo "   You can find your IP in System Settings > Wi-Fi > Details."
    exit 1
fi

echo "🌐 Detected local IP: $LOCAL_IP"
echo ""

# Patch EXPO_PUBLIC_API_BASE_URL in .env.development to use local IP
ENV_DEV="$PROJECT_DIR/.env.development"
OLD_API_URL="EXPO_PUBLIC_API_BASE_URL=http://localhost:8000"
NEW_API_URL="EXPO_PUBLIC_API_BASE_URL=http://$LOCAL_IP:8000"

if [ ! -f "$ENV_DEV" ]; then
    echo "❌ .env.development not found at $ENV_DEV"
    echo "   Copy .env.development.example and fill in your credentials first."
    exit 1
fi

if grep -q "^$OLD_API_URL" "$ENV_DEV"; then
    sed -i '' "s|^$OLD_API_URL|$NEW_API_URL|" "$ENV_DEV"
    echo "✅ Updated .env.development: EXPO_PUBLIC_API_BASE_URL → http://$LOCAL_IP:8000"
elif grep -q "^$NEW_API_URL" "$ENV_DEV"; then
    echo "✅ .env.development already pointing to $LOCAL_IP:8000"
else
    echo "⚠️  Could not auto-patch EXPO_PUBLIC_API_BASE_URL in .env.development."
    echo "   Please manually set: EXPO_PUBLIC_API_BASE_URL=http://$LOCAL_IP:8000"
fi

# Patch backend/.env ALLOWED_ORIGINS to include the LAN IP (for browser-based testing)
BACKEND_ENV="$PROJECT_DIR/backend/.env"
if [ -f "$BACKEND_ENV" ]; then
    if ! grep -q "$LOCAL_IP:8081" "$BACKEND_ENV"; then
        sed -i '' "s|ALLOWED_ORIGINS=\(.*\)|ALLOWED_ORIGINS=\1,http://$LOCAL_IP:8081|" "$BACKEND_ENV"
        echo "✅ Added http://$LOCAL_IP:8081 to backend/.env ALLOWED_ORIGINS"
    else
        echo "✅ backend/.env ALLOWED_ORIGINS already includes $LOCAL_IP:8081"
    fi
fi
echo ""

# Restore EXPO_PUBLIC_API_BASE_URL in .env.development to localhost on exit
restore_env_dev() {
    echo ""
    echo "🔄 Restoring .env.development EXPO_PUBLIC_API_BASE_URL to localhost..."
    sed -i '' "s|^EXPO_PUBLIC_API_BASE_URL=http://$LOCAL_IP:8000|EXPO_PUBLIC_API_BASE_URL=http://localhost:8000|" "$ENV_DEV"
    # Also clean up the LAN IP from backend/.env ALLOWED_ORIGINS
    if [ -f "$BACKEND_ENV" ]; then
        sed -i '' "s|,http://$LOCAL_IP:8081||g" "$BACKEND_ENV"
    fi
    echo "✅ Restored. .env.development is back to localhost:8000"
}

# Cleanup all processes on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down servers..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    restore_env_dev
    exit
}

trap cleanup EXIT INT TERM

# Setup NVM and Node
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
nvm use 18.20.8

# Start Backend (FastAPI) — bind to 0.0.0.0 so phone can reach it
echo "📦 Starting Backend (FastAPI) on $LOCAL_IP:8000..."
if [ ! -d "venv" ]; then
    echo "   Creating Python virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

if ! python3 -c "import msal" 2>/dev/null; then
    echo "   Installing Python dependencies..."
    pip install -q -r requirements.txt
fi

cd backend
python3 main.py &
BACKEND_PID=$!
cd ..
echo "   Backend PID: $BACKEND_PID"
echo ""

# Wait for backend to start
sleep 3

# Start Frontend (Expo) in tunnel or LAN mode so phone can connect
echo "⚛️  Starting Frontend (Expo) in LAN mode..."
npx expo start --lan &
FRONTEND_PID=$!
echo "   Frontend PID: $FRONTEND_PID"
echo ""

echo "✅ Servers running!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📱 TO TEST ON YOUR PHONE:"
echo "   1. Install 'Expo Go' from the App Store or Play Store"
echo "   2. Make sure your phone is on the SAME Wi-Fi network"
echo "   3. Scan the QR code that appears below with:"
echo "      • Android: Expo Go app → Scan QR"
echo "      • iPhone:  Native Camera app (opens Expo Go)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🔗 Backend API: http://$LOCAL_IP:8000"
echo "📊 API Docs:    http://$LOCAL_IP:8000/docs"
echo ""
echo "Press Ctrl+C to stop all servers and restore App.js"
echo ""

wait
