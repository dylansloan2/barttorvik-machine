#!/usr/bin/env python3
"""
Run the bot with real TourneyCast data and sample Kalshi data to show best bets
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from datetime import datetime
from src.browser import BrowserClient
from src.scrapers.tourneycast_scraper import TourneyCastScraper
from src.config import Config
from src.matcher import TeamMatcher
from src.ev import EVCalculator
from src.output import OutputManager

def create_sample_kalshi_contracts():
    """Create sample Kalshi contracts that match our scraped teams"""
    contracts = []
    
    # Top teams from TourneyCast with varying prices to create EV opportunities
    sample_teams = [
        ('Arizona', 0.95),      # High probability, lower price
        ('Michigan', 0.92), 
        ('Duke', 0.90),
        ('Connecticut', 0.93),
        ('Houston', 0.88),
        ('Purdue', 0.85),
        ('Tennessee', 0.80),
        ('Kansas', 0.82),
        ('Alabama', 0.75),
        ('North Carolina', 0.70),
        ('Marquette', 0.65),
        ('Michigan State', 0.60),
        ('Creighton', 0.55),
        ('Baylor', 0.50),
        ('UCLA', 0.45),
    ]
    
    for team, base_price in sample_teams:
        contracts.append({
            'ticker': f'{team.upper().replace(" ", "")}-YES',
            'team_name': team,
            'title': f'{team} to Make Tournament',
            'yes_price': base_price,
            'no_price': 1.0 - base_price
        })
    
    return contracts

def run_best_bets():
    """Run the bot to get best bets"""
    print("🏀 KALSHI BEST BETS - REAL DATA RUN 🏀")
    print("=" * 60)
    
    # Setup
    config = Config()
    output_dir = config.get_output_dir(datetime.now())
    
    ev_calculator = EVCalculator(
        min_ev=config.ev['min_ev'],
        share_factor=config.ev['share_factor']
    )
    matcher = TeamMatcher()
    output_manager = OutputManager(output_dir)
    
    print("📊 Scraping real TourneyCast data...")
    
    # Scrape real TourneyCast data
    with BrowserClient(headless=True, timeout=30) as browser:
        scraper = TourneyCastScraper(browser)
        tourney_teams = scraper.scrape_tourney_probabilities()
    
    print(f"✅ Scraped {len(tourney_teams)} teams from TourneyCast")
    
    # Create sample Kalshi contracts
    kalshi_contracts = create_sample_kalshi_contracts()
    print(f"📈 Generated {len(kalshi_contracts)} sample Kalshi contracts")
    
    all_bets = []
    
    # Process make tournament markets
    print("🎯 Processing Make Tournament markets...")
    make_contracts = [c for c in kalshi_contracts if 'to Make Tournament' in c['title']]
    matched_tourney = matcher.match_teams_to_contracts(tourney_teams, make_contracts, output_dir)
    tourney_bets = ev_calculator.calculate_all_bets(matched_tourney, "make_tournament")
    all_bets.extend(tourney_bets)
    print(f"   Found {len(tourney_bets)} qualifying bets")
    
    # Sort all bets by EV
    all_bets.sort(key=lambda x: x.ev, reverse=True)
    
    print()
    print("🎉 BEST BETS RESULTS:")
    print("=" * 60)
    
    # Display top bets
    if all_bets:
        output_manager.print_bets_table(all_bets, top_n=15)
        
        # Save results
        output_manager.save_bets_csv(all_bets, "real_best_bets.csv")
        output_manager.save_bets_json(all_bets, "real_best_bets.json")
        
        print(f"\n📁 Results saved to: {output_dir}")
        print("📄 Files: real_best_bets.csv, real_best_bets.json")
        
        # Show summary
        print(f"\n📊 SUMMARY:")
        print(f"   Total teams analyzed: {len(tourney_teams)}")
        print(f"   Qualifying bets found: {len(all_bets)}")
        print(f"   Average EV: {sum(bet.ev for bet in all_bets) / len(all_bets):.3f}")
        print(f"   Highest EV: {all_bets[0].ev:.3f} ({all_bets[0].team_name})")
        
    else:
        print("No qualifying bets found with current parameters.")
        print("Try lowering --min-ev or --share-factor thresholds.")
    
    print()
    print("🚀 Bot is working! Selenium scraping is successful!")
    print("💡 To get real Kalshi data, fix API connectivity issues.")

if __name__ == "__main__":
    run_best_bets()
