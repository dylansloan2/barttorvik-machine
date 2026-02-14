#!/bin/bash
# Production Setup Script for Kalshi Best Bets Bot

echo "🔧 Kalshi Best Bets - Production Setup"
echo "=================================="
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cat > .env << EOF
# Kalshi Production API Credentials
# Get these from your Kalshi account settings

# Your API Key ID (UUID)
KALSHI_KEY_ID=your-key-id-here

# Path to your private key file
KALSHI_PRIVATE_KEY_PATH=./kalshi_private.key

# Production API URL
KALSHI_BASE_URL=https://api.elections.kalshi.com/trade-api/v2

# Optional: Add your key ID here for easy reference
# KALSHI_KEY_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
EOF
    echo "✅ Created .env file"
    echo ""
    echo "📋 Next steps:"
    echo "1. Open your Kalshi account settings"
    echo "2. Create a new API key"
    echo "3. Download the private key file and save it as 'kalshi_private.key'"
    echo "4. Edit .env and add your actual KALSHI_KEY_ID"
    echo "5. Run: source .env"
    echo "6. Run: python3 test_production.py"
    echo ""
else
    echo "ℹ️  .env file already exists"
    echo ""
    echo "🔍 Checking .env contents..."
    if grep -q "your-key-id-here" .env; then
        echo "❌ Please edit .env and add your actual KALSHI_KEY_ID"
    else
        echo "✅ .env appears to be configured"
    fi
    echo ""
fi

echo "📋 Current environment variables:"
echo "   KALSHI_KEY_ID: ${KALSHI_KEY_ID:-'Not set'}"
echo "   KALSHI_PRIVATE_KEY_PATH: ${KALSHI_PRIVATE_KEY_PATH:-'Not set'}"
echo "   KALSHI_BASE_URL: ${KALSHI_BASE_URL:-'Not set'}"
echo ""

# Load .env if it exists
if [ -f .env ]; then
    echo "🔗 Loading .env file..."
    export $(cat .env | grep -v '^#' | xargs)
    echo "✅ Environment variables loaded"
    echo ""
    
    echo "📋 Updated environment variables:"
    echo "   KALSHI_KEY_ID: ${KALSHI_KEY_ID:-'Not set'}"
    echo "   KALSHI_PRIVATE_KEY_PATH: ${KALSHI_PRIVATE_KEY_PATH:-'Not set'}"
    echo "   KALSHI_BASE_URL: ${KALSHI_BASE_URL:-'Not set'}"
    echo ""
    
    # Check if private key file exists
    if [ -n "$KALSHI_PRIVATE_KEY_PATH" ] && [ -f "$KALSHI_PRIVATE_KEY_PATH" ]; then
        echo "✅ Private key file found: $KALSHI_PRIVATE_KEY_PATH"
        
        # Test the setup
        echo "🧪 Testing production setup..."
        python3 test_production.py
    else
        echo "❌ Private key file not found: $KALSHI_PRIVATE_KEY_PATH"
        echo ""
        echo "📋 To fix:"
        echo "1. Make sure you have your Kalshi private key file"
        echo "2. Save it as: $KALSHI_PRIVATE_KEY_PATH"
        echo "3. Or update KALSHI_PRIVATE_KEY_PATH in .env"
    fi
else
    echo "❌ No .env file found"
    echo "Please run this script again after creating .env"
fi
