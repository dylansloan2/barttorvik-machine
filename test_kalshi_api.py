#!/usr/bin/env python3
"""
Test the Kalshi elections API
"""

import requests
import json

def test_kalshi_api():
    """Test the Kalshi elections API"""
    print("🔍 Testing Kalshi Elections API...")
    
    base_url = "https://api.elections.kalshi.com/trade-api/v2"
    
    # Test markets endpoint
    markets_url = f"{base_url}/markets"
    print(f"📡 Requesting: {markets_url}")
    
    try:
        response = requests.get(markets_url)
        print(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            markets = data.get('markets', [])
            print(f"✅ Found {len(markets)} markets")
            
            if markets:
                print("\n🏀 First 5 markets:")
                for i, market in enumerate(markets[:5]):
                    print(f"   {i+1}. {market.get('ticker', 'N/A')} - {market.get('title', 'N/A')}")
                
                # Test orderbook for first market
                first_market = markets[0]
                ticker = first_market['ticker']
                orderbook_url = f"{base_url}/markets/{ticker}/orderbook"
                
                print(f"\n📈 Testing orderbook for {ticker}...")
                orderbook_response = requests.get(orderbook_url)
                
                if orderbook_response.status_code == 200:
                    orderbook = orderbook_response.json()
                    yes_bids = orderbook.get('orderbook', {}).get('yes', [])
                    no_bids = orderbook.get('orderbook', {}).get('no', [])
                    
                    print(f"✅ Orderbook found:")
                    if yes_bids:
                        print(f"   YES bids: {len(yes_bids) if yes_bids else 0}")
                        print(f"   Best YES bid: {yes_bids[0][0]}¢, Quantity: {yes_bids[0][1]}")
                    else:
                        print(f"   YES bids: 0")
                    
                    if no_bids:
                        print(f"   NO bids: {len(no_bids) if no_bids else 0}")
                        print(f"   Best NO bid: {no_bids[0][0]}¢, Quantity: {no_bids[0][1]}")
                    else:
                        print(f"   NO bids: 0")
                        
                    # Look for basketball markets
                    print(f"\n🏀 Searching for basketball markets...")
                    basketball_markets = []
                    for market in markets:
                        title = market.get('title', '').lower()
                        if any(keyword in title for keyword in ['basketball', 'tournament', 'march madness', 'ncaa']):
                            basketball_markets.append(market)
                    
                    print(f"   Found {len(basketball_markets)} basketball-related markets")
                    if basketball_markets:
                        print("\n🏀 Basketball markets:")
                        for i, market in enumerate(basketball_markets[:5]):
                            print(f"   {i+1}. {market.get('ticker', 'N/A')} - {market.get('title', 'N/A')}")
                else:
                    print(f"❌ Orderbook failed: {orderbook_response.status_code}")
                    print(f"   Response: {orderbook_response.text}")
            else:
                print("❌ No markets found")
        else:
            print(f"❌ API request failed: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_kalshi_api()
