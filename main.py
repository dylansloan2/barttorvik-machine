#!/usr/bin/env python3

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from config import Config
from browser import BrowserClient
from scrapers.schedule_scraper import ScheduleScraper
from scrapers.tourneycast_scraper import TourneyCastScraper
from scrapers.concast_scraper import ConCastScraper
from kalshi.kalshi_client import KalshiClient
from matcher import TeamMatcher
from ev import EVCalculator
from output import OutputManager

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Kalshi Best Bets Bot')
    
    parser.add_argument('--date', type=str, help='Date in YYYY-MM-DD format (default: today)')
    parser.add_argument('--top', type=int, default=20, help='Number of top bets to display (default: 20)')
    parser.add_argument('--min-ev', type=float, default=0.02, help='Minimum EV threshold (default: 0.02)')
    parser.add_argument('--share-factor', type=float, default=0.5, help='Share factor for conference championships (default: 0.5)')
    parser.add_argument('--dry-run', action='store_true', help='Run without placing trades (default)')
    parser.add_argument('--screenshots', action='store_true', help='Save screenshots when parsing fails')
    
    return parser.parse_args()

def parse_date(date_str: str) -> datetime:
    """Parse date string and return datetime object"""
    if date_str:
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            print(f"Invalid date format: {date_str}. Use YYYY-MM-DD")
            sys.exit(1)
    else:
        # Default to today in America/Chicago timezone
        return datetime.now()

def scrape_tourneycast(browser_client: BrowserClient) -> list:
    """Scrape TourneyCast data"""
    scraper = TourneyCastScraper(browser_client)
    return scraper.scrape_tourney_probabilities()

def scrape_conference_odds(browser_client: BrowserClient, config: Config) -> dict:
    """Scrape conference championship odds"""
    scraper = ConCastScraper(browser_client)
    conference_data = {}
    
    for conference in config.conferences:
        conf_code = config.get_conference_code(conference)
        teams = scraper.scrape_conference_odds(conf_code)
        if teams:
            conference_data[conference] = teams
    
    return conference_data

def scrape_games(browser_client: BrowserClient, target_date: datetime) -> list:
    """Scrape game schedule"""
    scraper = ScheduleScraper(browser_client)
    return scraper.scrape_games(target_date)

def get_kalshi_markets(config: Config, kalshi_client: KalshiClient) -> tuple:
    """Get Kalshi markets and contracts using production API"""
    
    # Get Make Tournament markets with new method
    make_tournament_markets = kalshi_client.get_make_tournament_markets()
    
    # Convert markets to contract format for compatibility
    make_tournament_contracts = []
    for market in make_tournament_markets:
        # Get prices for this market
        prices = kalshi_client.get_market_prices(market['ticker'])
        
        contract = {
            'ticker': market['ticker'],
            'title': market.get('title', ''),
            'team_name': market['team_name'],
            'yes_price': prices.get('yes_buy_price', 0.5),
            'no_price': prices.get('no_buy_price', 0.5)
        }
        make_tournament_contracts.append(contract)
    
    # For now, conference markets are not implemented in production API
    # This would need to be added based on available market titles
    conference_markets = {}
    
    return make_tournament_contracts, conference_markets

def main():
    """Main function"""
    args = parse_arguments()
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Parse target date
    target_date = parse_date(args.date)
    
    # Load configuration
    config = Config()
    
    # Override config with CLI arguments
    config.config['ev']['min_ev'] = args.min_ev
    config.config['ev']['share_factor'] = args.share_factor
    config.config['ev']['top_bets'] = args.top
    config.config['scraping']['screenshot_on_error'] = args.screenshots
    
    # Setup output directory
    output_dir = config.get_output_dir(target_date)
    
    # Setup screenshot directory if needed
    screenshot_dir = output_dir / "screenshots" if args.screenshots else None
    
    logger.info(f"Starting Kalshi Best Bets for {target_date.strftime('%Y-%m-%d')}")
    logger.info(f"Output directory: {output_dir}")
    
    # Initialize components
    ev_calculator = EVCalculator(
        min_ev=config.ev['min_ev'],
        share_factor=config.ev['share_factor']
    )
    matcher = TeamMatcher()
    output_manager = OutputManager(output_dir)
    
    # Initialize Kalshi client and do preflight check
    kalshi_client = KalshiClient()
    logger.info("Performing Kalshi API preflight check...")
    if not kalshi_client.preflight_check():
        logger.error("Kalshi API preflight check failed - aborting")
        sys.exit(1)
    logger.info("Kalshi API preflight check passed")
    
    log_messages = []
    
    try:
        # Scrape data from BartTorvik
        logger.info("Scraping BartTorvik data...")
        
        with BrowserClient(
            headless=config.scraping['headless'],
            timeout=config.scraping['timeout'],
            screenshot_dir=screenshot_dir
        ) as browser:
            
            # Scrape TourneyCast
            logger.info("Scraping TourneyCast...")
            tourney_teams = scrape_tourneycast(browser)
            log_messages.append(f"TourneyCast: Found {len(tourney_teams)} teams")
            
            # Scrape conference odds
            logger.info("Scraping conference championship odds...")
            conference_data = scrape_conference_odds(browser, config)
            total_conf_teams = sum(len(teams) for teams in conference_data.values())
            log_messages.append(f"Conference odds: Found {total_conf_teams} teams across {len(conference_data)} conferences")
            
            # Scrape games
            logger.info("Scraping game schedule...")
            games = scrape_games(browser, target_date)
            log_messages.append(f"Games: Found {len(games)} games for {target_date.strftime('%Y-%m-%d')}")
        
        # Get Kalshi markets
        logger.info("Fetching Kalshi markets...")
        make_tournament_contracts, conference_markets = get_kalshi_markets(config, kalshi_client)
        
        log_messages.append(f"Kalshi make tournament: {len(make_tournament_contracts)} contracts")
        log_messages.append(f"Kalshi conference champs: {sum(len(contracts) for contracts in conference_markets.values())} contracts")
        
        # Calculate EV for make tournament markets
        all_bets = []
        if tourney_teams and make_tournament_contracts:
            logger.info("Matching make tournament teams to contracts...")
            matched_tourney = matcher.match_teams_to_contracts(
                tourney_teams, make_tournament_contracts, output_dir
            )
            tourney_bets = ev_calculator.calculate_all_bets(matched_tourney, "make_tournament")
            all_bets.extend(tourney_bets)
            log_messages.append(f"Make tournament bets: {len(tourney_bets)} qualifying")
        
        # Calculate EV for conference championship markets
        for conference, teams in conference_data.items():
            if conference in conference_markets:
                logger.info(f"Matching {conference} teams to contracts...")
                contracts = conference_markets[conference]
                matched_conf = matcher.match_teams_to_contracts(teams, contracts, output_dir)
                conf_bets = ev_calculator.calculate_all_bets(
                    matched_conf, "conference_champ", conference
                )
                all_bets.extend(conf_bets)
                log_messages.append(f"{conference} bets: {len(conf_bets)} qualifying")
        
        # Sort all bets by EV
        all_bets.sort(key=lambda x: x.ev, reverse=True)
        
        # Generate output
        logger.info("Generating reports...")
        output_manager.generate_report(all_bets, log_messages)
        
        # Print summary
        print(f"\n✅ Analysis complete!")
        print(f"📊 Total qualifying bets: {len(all_bets)}")
        if all_bets:
            print(f"💰 Best EV: ${all_bets[0].ev:.3f}")
            print(f"📈 Average EV: ${sum(bet.ev for bet in all_bets) / len(all_bets):.3f}")
        
        logger.info("Kalshi Best Bets completed successfully")
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        log_messages.append(f"ERROR: {e}")
        
        # Try to save error log
        try:
            output_manager.save_log(log_messages)
        except:
            pass
        
        sys.exit(1)

if __name__ == "__main__":
    main()
