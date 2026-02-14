#!/usr/bin/env python3
"""
Test the regular Kalshi API
"""

import requests
import json

def test_regular_kalshi_api():
    """Test the regular Kalshi API"""
    print("🔍 Testing Regular Kalshi API...")
    
    base_url = "https://api.kalshi.com/v1"
    
    # Test different endpoints
    endpoints = [
        "/markets",
        "/markets?status=open",
        "/markets?series=tournament",
        "/markets?limit=10",
        "/events",
        "/series"
    ]
    
    for endpoint in endpoints:
        url = f"{base_url}{endpoint}"
        print(f"\n📡 Requesting: {url}")
        
        try:
            response = requests.get(url, timeout=10)
            print(f"📊 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if 'markets' in data:
                    markets = data.get('markets', [])
                    print(f"✅ Found {len(markets)} markets")
                    
                    # Look for basketball/tournament markets
                    basketball_markets = []
                    for market in markets[:10]:  # Check first 10
                        title = market.get('title', '').lower()
                        if any(keyword in title for keyword in ['basketball', 'tournament', 'march madness', 'ncaa', 'make tournament']):
                            basketball_markets.append(market)
                    
                    if basketball_markets:
                        print(f"🏀 Found {len(basketball_markets)} basketball markets:")
                        for i, market in enumerate(basketball_markets[:3]):
                            print(f"   {i+1}. {market.get('ticker', 'N/A')} - {market.get('title', 'N/A')}")
                            
                            # Get price info
                            ticker = market.get('ticker')
                            if ticker:
                                price_url = f"{base_url}/markets/{ticker}/price"
                                price_response = requests.get(price_url)
                                if price_response.status_code == 200:
                                    price_data = price_response.json()
                                    print(f"      Price: {price_data}")
                    else:
                        print("   No basketball markets found in first 10")
                        # Show first market for reference
                        if markets:
                            print(f"   Sample market: {markets[0].get('title', 'N/A')}")
                            
                elif 'events' in data:
                    events = data.get('events', [])
                    print(f"✅ Found {len(events)} events")
                elif 'series' in data:
                    series = data.get('series', [])
                    print(f"✅ Found {len(series)} series")
                    # Look for tournament series
                    tournament_series = [s for s in series if 'tournament' in s.get('title', '').lower()]
                    if tournament_series:
                        print(f"🏀 Tournament series: {tournament_series}")
                else:
                    print(f"✅ Response: {list(data.keys())}")
                    
            elif response.status_code == 401:
                print("❌ Authentication required - need API credentials")
            elif response.status_code == 403:
                print("❌ Access forbidden - may need API credentials")
            elif response.status_code == 404:
                print("❌ Endpoint not found")
            else:
                print(f"❌ Error: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                
        except requests.exceptions.Timeout:
            print("❌ Request timeout")
        except requests.exceptions.ConnectionError as e:
            print(f"❌ Connection error: {e}")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_regular_kalshi_api()
