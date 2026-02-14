#!/usr/bin/env python3
"""
Test to find Make Tournament markets using the correct method
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.kalshi.kalshi_client import KalshiClient

def test_make_tournament_markets():
    """Test to find Make Tournament markets"""
    print("🏀 Testing Make Tournament Markets Search...")
    
    client = KalshiClient()
    
    # Get Make Tournament markets
    markets = client.get_make_tournament_markets()
    
    if markets:
        print(f"✅ Found {len(markets)} Make Tournament markets")
        
        # Show first few markets
        print("\n🏀 Sample Make Tournament Markets:")
        for i, market in enumerate(markets[:10]):
            ticker = market.get('ticker', 'N/A')
            team_name = market.get('team_name', 'N/A')
            print(f"   {i+1}. {ticker}")
            print(f"      Team: {team_name}")
            print(f"      Title: {market.get('title', 'N/A')}")
            
            # Get prices
            prices = client.get_market_prices(ticker)
            yes_buy = prices.get('yes_buy_price')
            no_buy = prices.get('no_buy_price')
            
            print(f"      YES Buy: ${yes_buy:.3f}" if yes_buy else "      YES Buy: None")
            print(f"      NO Buy: ${no_buy:.3f}" if no_buy else "      NO Buy: None")
            print()
    else:
        print("❌ No Make Tournament markets found")
        
        # Debug: show some sample markets to see what's available
        print("\n🔍 Debug: Showing sample available markets...")
        try:
            import requests
            response = requests.get('https://demo-api.kalshi.co/trade-api/v2/markets?status=open&limit=10')
            if response.status_code == 200:
                markets = response.json()['markets']
                for i, market in enumerate(markets[:5]):
                    ticker = market.get('ticker', 'N/A')
                    print(f"   {i+1}. {ticker} - {market.get('title', 'N/A')}")
        except Exception as e:
            print(f"   Error: {e}")

if __name__ == "__main__":
    test_make_tournament_markets()
