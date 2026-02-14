import json
import csv
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import logging
from tabulate import tabulate

from ev import Bet

class OutputManager:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.logger = logging.getLogger(__name__)
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def print_bets_table(self, bets: List[Bet], top_n: int = 20):
        """Print formatted table of top bets"""
        if not bets:
            print("No qualifying bets found.")
            return
        
        # Limit to top N bets
        top_bets = bets[:top_n]
        
        # Prepare table data
        table_data = []
        for bet in top_bets:
            table_data.append([
                bet.market_type,
                bet.league_conf,
                bet.description[:50] + "..." if len(bet.description) > 50 else bet.description,
                f"{bet.model_prob_or_exp_payout:.3f}",
                f"${bet.yes_price:.2f}",
                f"${bet.ev:.3f}"
            ])
        
        headers = [
            "Market Type",
            "League/Conf", 
            "Description",
            "Model Prob/Exp Payout",
            "Yes Price",
            "EV"
        ]
        
        print(f"\n🏀 TOP {len(top_bets)} KALSHI BEST BETS 🏀")
        print("=" * 80)
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
        print(f"\nTotal qualifying bets: {len(bets)}")
        print(f"Showing top {len(top_bets)} bets")
    
    def save_bets_csv(self, bets: List[Bet], filename: str = "best_bets.csv"):
        """Save bets to CSV file"""
        if not bets:
            self.logger.warning("No bets to save to CSV")
            return
        
        csv_path = self.output_dir / filename
        
        # Prepare data for CSV
        csv_data = []
        for bet in bets:
            csv_data.append({
                'market_type': bet.market_type,
                'league_conf': bet.league_conf,
                'description': bet.description,
                'model_prob_or_exp_payout': bet.model_prob_or_exp_payout,
                'yes_price': bet.yes_price,
                'ev': bet.ev,
                'edge': bet.edge,
                'contract_ticker': bet.contract_ticker,
                'team_name': bet.team_name,
                'timestamp': datetime.now().isoformat()
            })
        
        df = pd.DataFrame(csv_data)
        df.to_csv(csv_path, index=False)
        
        self.logger.info(f"Saved {len(bets)} bets to {csv_path}")
    
    def save_bets_json(self, bets: List[Bet], filename: str = "best_bets.json"):
        """Save bets to JSON file"""
        if not bets:
            self.logger.warning("No bets to save to JSON")
            return
        
        json_path = self.output_dir / filename
        
        # Convert bets to dict format
        bets_data = []
        for bet in bets:
            bets_data.append({
                'market_type': bet.market_type,
                'league_conf': bet.league_conf,
                'description': bet.description,
                'model_prob_or_exp_payout': bet.model_prob_or_exp_payout,
                'yes_price': bet.yes_price,
                'ev': bet.ev,
                'edge': bet.edge,
                'contract_ticker': bet.contract_ticker,
                'team_name': bet.team_name
            })
        
        # Add metadata
        output_data = {
            'timestamp': datetime.now().isoformat(),
            'total_bets': len(bets),
            'min_ev': min(bet.ev for bet in bets) if bets else 0,
            'max_ev': max(bet.ev for bet in bets) if bets else 0,
            'avg_ev': sum(bet.ev for bet in bets) / len(bets) if bets else 0,
            'bets': bets_data
        }
        
        with open(json_path, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        self.logger.info(f"Saved {len(bets)} bets to {json_path}")
    
    def save_log(self, log_messages: List[str], filename: str = "log.txt"):
        """Save log messages to file"""
        log_path = self.output_dir / filename
        
        with open(log_path, 'w') as f:
            f.write(f"Kalshi Best Bets Log - {datetime.now().isoformat()}\n")
            f.write("=" * 50 + "\n\n")
            
            for message in log_messages:
                f.write(f"{message}\n")
        
        self.logger.info(f"Saved log to {log_path}")
    
    def save_summary_stats(self, bets: List[Bet]):
        """Save summary statistics"""
        if not bets:
            return
        
        # Group by market type
        market_stats = {}
        for bet in bets:
            market_type = bet.market_type
            if market_type not in market_stats:
                market_stats[market_type] = {
                    'count': 0,
                    'total_ev': 0,
                    'avg_ev': 0,
                    'max_ev': 0,
                    'min_ev': float('inf')
                }
            
            stats = market_stats[market_type]
            stats['count'] += 1
            stats['total_ev'] += bet.ev
            stats['max_ev'] = max(stats['max_ev'], bet.ev)
            stats['min_ev'] = min(stats['min_ev'], bet.ev)
        
        # Calculate averages
        for market_type, stats in market_stats.items():
            stats['avg_ev'] = stats['total_ev'] / stats['count']
            if stats['min_ev'] == float('inf'):
                stats['min_ev'] = 0
        
        # Save summary
        summary_path = self.output_dir / "summary.json"
        summary_data = {
            'timestamp': datetime.now().isoformat(),
            'total_bets': len(bets),
            'overall_avg_ev': sum(bet.ev for bet in bets) / len(bets),
            'market_breakdown': market_stats
        }
        
        with open(summary_path, 'w') as f:
            json.dump(summary_data, f, indent=2)
        
        self.logger.info(f"Saved summary statistics to {summary_path}")
    
    def generate_report(self, bets: List[Bet], log_messages: List[str] = None):
        """Generate complete report"""
        self.print_bets_table(bets)
        self.save_bets_csv(bets)
        self.save_bets_json(bets)
        self.save_summary_stats(bets)
        
        if log_messages:
            self.save_log(log_messages)
        
        print(f"\n📁 Reports saved to: {self.output_dir}")
        print(f"📊 Files created: best_bets.csv, best_bets.json, summary.json")
        if log_messages:
            print("📝 Log file: log.txt")
