#!/usr/bin/env python3
"""
Test the Kalshi demo API
"""

import requests

def test_demo_api():
    """Test the Kalshi demo API"""
    print("🔍 Testing Kalshi Demo API...")
    
    # Get the first open market (no auth required for public market data)
    response = requests.get('https://demo-api.kalshi.co/trade-api/v2/markets?limit=1&status=open')
    
    if response.status_code == 200:
        market = response.json()['markets'][0]
        
        print(f"✅ Found market: {market['ticker']}")
        print(f"   Title: {market['title']}")
        print(f"   Status: {market['status']}")
        
        # Get more markets to look for basketball
        response = requests.get('https://demo-api.kalshi.co/trade-api/v2/markets?limit=50&status=open')
        
        if response.status_code == 200:
            markets = response.json()['markets']
            print(f"\n📊 Found {len(markets)} open markets")
            
            # Look for basketball markets
            basketball_markets = []
            for market in markets:
                title = market.get('title', '').lower()
                if any(keyword in title for keyword in ['basketball', 'ncaa', 'march madness', 'college', 'tournament']):
                    basketball_markets.append(market)
            
            print(f"🏀 Found {len(basketball_markets)} basketball markets:")
            
            for i, market in enumerate(basketball_markets[:10]):
                print(f"   {i+1}. {market['ticker']}")
                print(f"      Title: {market['title']}")
                print(f"      Yes Price: ${market.get('yes_ask', 0)/100:.2f}")
                print(f"      No Price: ${market.get('no_ask', 0)/100:.2f}")
                print()
                
        else:
            print(f"❌ Failed to get markets: {response.status_code}")
            
    else:
        print(f"❌ Failed to get demo market: {response.status_code}")
        print(f"   Response: {response.text}")

if __name__ == "__main__":
    test_demo_api()
