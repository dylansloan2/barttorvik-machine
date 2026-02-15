#!/usr/bin/env python3
"""
Test to find March Madness markets using the elections API
"""

from kalshi.kalshi_client import KalshiClient

def test_march_madness_markets():
    """Test to find March Madness markets"""
    print("🏀 Searching for March Madness Markets...")
    
    client = KalshiClient()
    
    # Test different search terms based on the screenshot
    search_terms = [
        "march",
        "madness", 
        "ncaa",
        "tournament",
        "basketball",
        "college",
        "championship",
        "round of 64",
        "bracket"
    ]
    
    all_markets = []
    
    for term in search_terms:
        print(f"\n🔍 Searching for: '{term}'")
        markets = client.get_markets_by_title(term)
        
        if markets:
            print(f"   Found {len(markets)} markets")
            
            # Filter for basketball-related markets
            basketball_markets = []
            for market in markets:
                title = market.get('title', '').lower()
                # Look for basketball indicators
                if any(keyword in title for keyword in ['basketball', 'ncaa', 'march madness', 'college', 'bracket']):
                    basketball_markets.append(market)
            
            if basketball_markets:
                print(f"   🏀 Found {len(basketball_markets)} basketball markets:")
                for i, market in enumerate(basketball_markets[:3]):
                    print(f"      {i+1}. {market.get('ticker', 'N/A')}")
                    print(f"         Title: {market.get('title', 'N/A')}")
                    print(f"         Status: {market.get('status', 'N/A')}")
                    
                    # Try to get price
                    ticker = market.get('ticker')
                    if ticker:
                        try:
                            yes_price = client._get_yes_price(ticker)
                            print(f"         YES Price: ${yes_price:.3f}")
                        except Exception as e:
                            print(f"         Price: Error - {e}")
                    print()
                
                all_markets.extend(basketball_markets)
            else:
                # Show first non-basketball market for reference
                if markets:
                    print(f"   Sample market: {markets[0].get('title', 'N/A')}")
        else:
            print("   No markets found")
    
    # Summary
    print(f"\n📊 SUMMARY:")
    print(f"   Total basketball markets found: {len(all_markets)}")
    
    if all_markets:
        print(f"\n🏀 ALL BASKETBALL MARKETS:")
        for i, market in enumerate(all_markets):
            print(f"   {i+1}. {market.get('ticker', 'N/A')} - {market.get('title', 'N/A')}")
    
    return all_markets

if __name__ == "__main__":
    test_march_madness_markets()
