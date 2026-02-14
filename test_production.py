#!/usr/bin/env python3
"""
Test the production Kalshi API setup
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.kalshi.kalshi_client import KalshiClient

def test_production_setup():
    """Test the production Kalshi API setup"""
    print("🔧 Testing Production Kalshi API Setup...")
    print("=" * 50)
    
    # Check environment variables
    print("📋 Checking environment variables:")
    
    key_id = os.getenv('KALSHI_KEY_ID')
    private_key_path = os.getenv('KALSHI_PRIVATE_KEY_PATH')
    base_url = os.getenv('KALSHI_BASE_URL')
    
    print(f"   KALSHI_KEY_ID: {'✅ Set' if key_id else '❌ Missing'}")
    print(f"   KALSHI_PRIVATE_KEY_PATH: {'✅ Set' if private_key_path else '❌ Missing'}")
    print(f"   KALSHI_BASE_URL: {'✅ Set' if base_url else '❌ Missing (will use config)'}")
    
    if not key_id or not private_key_path:
        print("\n❌ Missing required environment variables!")
        print("\nTo set up production credentials:")
        print("1. Create a Kalshi API key in Kalshi settings")
        print("2. Save the private key file (.key)")
        print("3. Set environment variables:")
        print("   export KALSHI_KEY_ID='your-key-id'")
        print("   export KALSHI_PRIVATE_KEY_PATH='/path/to/your.key'")
        print("   export KALSHI_BASE_URL='https://api.elections.kalshi.com/trade-api/v2'")
        return False
    
    # Check if private key file exists
    if not os.path.exists(private_key_path):
        print(f"\n❌ Private key file not found: {private_key_path}")
        return False
    
    print(f"✅ Private key file exists: {private_key_path}")
    
    # Initialize client and test preflight
    print("\n🔍 Testing Kalshi client initialization...")
    try:
        client = KalshiClient()
        print("✅ Kalshi client initialized successfully")
        
        print("\n🚀 Testing preflight check...")
        if client.preflight_check():
            print("✅ Preflight check passed!")
            
            print("\n📊 Testing Make Tournament markets fetch...")
            markets = client.get_make_tournament_markets()
            
            if markets:
                print(f"✅ Found {len(markets)} Make Tournament markets")
                
                # Show sample markets
                print("\n🏀 Sample Make Tournament Markets:")
                for i, market in enumerate(markets[:5]):
                    ticker = market.get('ticker', 'N/A')
                    team_name = market.get('team_name', 'N/A')
                    print(f"   {i+1}. {ticker}")
                    print(f"      Team: {team_name}")
                    
                    # Test price fetching
                    prices = client.get_market_prices(ticker)
                    yes_buy = prices.get('yes_buy_price')
                    no_buy = prices.get('no_buy_price')
                    
                    print(f"      YES Buy: ${yes_buy:.3f}" if yes_buy else "      YES Buy: None")
                    print(f"      NO Buy: ${no_buy:.3f}" if no_buy else "      NO Buy: None")
                    print()
                
                return True
            else:
                print("❌ No Make Tournament markets found")
                print("   This might be expected if March Madness markets are not yet available")
                return True
        else:
            print("❌ Preflight check failed")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_production_setup()
    
    if success:
        print("\n🎉 Production setup test completed successfully!")
        print("🚀 Ready to run: python3 src/main.py")
    else:
        print("\n❌ Production setup test failed!")
        print("🔧 Please fix the issues above before running the bot")
