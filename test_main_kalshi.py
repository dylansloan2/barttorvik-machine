#!/usr/bin/env python3
"""
Test the main Kalshi API with real credentials
"""

from kalshi.kalshi_client import KalshiClient

def test_main_kalshi_api():
    """Test the main Kalshi API with authentication"""
    print("🔐 Testing Main Kalshi API with Authentication...")
    
    client = KalshiClient()
    
    # Test markets endpoint
    print("📡 Testing /markets endpoint...")
    markets = client.get_markets_by_title("tournament")
    
    if markets:
        print(f"✅ Found {len(markets)} markets")
        
        # Look for basketball/tournament markets
        basketball_markets = []
        for market in markets:
            title = market.get('title', '').lower()
            if any(keyword in title for keyword in ['basketball', 'tournament', 'march madness', 'ncaa', 'make tournament']):
                basketball_markets.append(market)
        
        print(f"🏀 Found {len(basketball_markets)} basketball-related markets")
        
        if basketball_markets:
            print("\n🏀 Basketball markets:")
            for i, market in enumerate(basketball_markets[:5]):
                print(f"   {i+1}. {market.get('ticker', 'N/A')} - {market.get('title', 'N/A')}")
                
                # Get price info
                ticker = market.get('ticker')
                if ticker:
                    try:
                        # Try to get price using the client
                        yes_price = client._get_yes_price(ticker)
                        print(f"      YES Price: ${yes_price:.3f}")
                    except Exception as e:
                        print(f"      Price error: {e}")
        else:
            print("   No basketball markets found")
            print("   Showing first 5 markets instead:")
            for i, market in enumerate(markets[:5]):
                print(f"   {i+1}. {market.get('ticker', 'N/A')} - {market.get('title', 'N/A')}")
    else:
        print("❌ No markets found")
    
    print("\n🔍 Testing specific market titles...")
    
    # Test for specific titles we're looking for
    test_titles = [
        "Men's March Madness Round of 64 Qualifiers",
        "Make Tournament",
        "March Madness",
        "Big Ten",
        "SEC"
    ]
    
    for title in test_titles:
        markets = client.get_markets_by_title(title)
        print(f"   '{title}': {len(markets)} markets")
        if markets:
            print(f"      Example: {markets[0].get('title', 'N/A')}")

if __name__ == "__main__":
    test_main_kalshi_api()
