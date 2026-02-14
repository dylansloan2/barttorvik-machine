import re
from rapidfuzz import fuzz, process
from typing import List, Dict, Tuple, Optional
import logging
import pandas as pd
from pathlib import Path

class TeamMatcher:
    def __init__(self, min_score: int = 90):
        self.min_score = min_score
        self.logger = logging.getLogger(__name__)
        self.unmatched_teams = []
        self.unmatched_contracts = []
        
        # Team name normalization mappings
        self.team_normalizations = {
            'St.': 'State',
            'St ': 'State ',
            'UConn': 'Connecticut',
            'Ole Miss': 'Mississippi',
            'USC': 'Southern California',
            'UCLA': 'California Los Angeles',
            'UCF': 'Central Florida',
            'USF': 'South Florida',
            'UTSA': 'Texas San Antonio',
            'UTEP': 'Texas El Paso',
            'SMU': 'Southern Methodist',
            'TCU': 'Texas Christian',
            'UT': 'Texas',
            'UK': 'Kentucky',
            'UNC': 'North Carolina',
            'UVA': 'Virginia',
            'Ga.': 'Georgia',
            'Fla.': 'Florida',
            'Miss.': 'Mississippi',
            'Ala.': 'Alabama',
            'Ark.': 'Arkansas',
            'La.': 'Louisiana',
            'Tenn.': 'Tennessee',
            'S.C.': 'South Carolina',
            'N.C.': 'North Carolina',
            'W.Va.': 'West Virginia',
            'Purdue Fort Wayne': 'Purdue Fort Wayne',
            'UC Davis': 'California Davis',
            'UC Irvine': 'California Irvine',
            'UC Riverside': 'California Riverside',
            'UC Santa Barbara': 'California Santa Barbara',
            'CSU Bakersfield': 'Cal State Bakersfield',
            'CSU Fullerton': 'Cal State Fullerton',
            'CSU Northridge': 'Cal State Northridge',
            'LIU Brooklyn': 'LIU',
            'UMBC': 'Maryland Baltimore County',
            'UMass Lowell': 'Massachusetts Lowell',
            'SIU Edwardsville': 'Southern Illinois Edwardsville',
            'UTRGV': 'Texas Rio Grande Valley',
            'UAB': 'Alabama Birmingham',
            'UT Martin': 'Tennessee Martin',
            'FGCU': 'Florida Gulf Coast',
            'UNC Wilmington': 'Wilmington',
            'College of Charleston': 'Charleston',
            'William & Mary': 'William and Mary',
        }
    
    def normalize_team_name(self, name: str) -> str:
        """Normalize team name for matching"""
        if not name:
            return ""
        
        # Convert to lowercase and strip
        name = name.lower().strip()
        
        # Apply normalizations
        for old, new in self.team_normalizations.items():
            name = name.replace(old.lower(), new.lower())
        
        # Remove common punctuation and extra spaces
        name = re.sub(r'[^\w\s]', ' ', name)
        name = re.sub(r'\s+', ' ', name)
        
        return name.strip()
    
    def match_teams_to_contracts(self, teams: List[Dict], contracts: List[Dict], 
                                output_dir: Path) -> List[Dict]:
        """Match teams to Kalshi contracts"""
        matched_bets = []
        
        # Create list of team names for fuzzy matching
        team_names = [self.normalize_team_name(team['team']) for team in teams]
        contract_names = [self.normalize_team_name(contract['team_name']) for contract in contracts]
        
        # Match each team to best contract
        for i, team in enumerate(teams):
            team_name_norm = self.normalize_team_name(team['team'])
            
            # Find best match using rapidfuzz
            result = process.extractOne(
                team_name_norm, 
                contract_names,
                scorer=fuzz.token_set_ratio,
                score_cutoff=self.min_score
            )
            
            if result:
                matched_name, score, best_match_idx = result
                # Ensure best_match_idx is an integer
                if isinstance(best_match_idx, str):
                    # Find the actual index by searching contract names
                    try:
                        best_match_idx = contract_names.index(matched_name)
                    except ValueError:
                        self.logger.warning(f"Could not find index for matched name: {matched_name}")
                        continue
                
                contract = contracts[best_match_idx]
                
                # Log low-scoring matches
                if score < 95:
                    self.logger.warning(f"Low score match: {team['team']} -> {contract['team_name']} (score: {score})")
                
                matched_bet = {
                    'team': team['team'],
                    'contract': contract,
                    'match_score': score,
                    'model_data': team
                }
                matched_bets.append(matched_bet)
            else:
                # No match found
                self.unmatched_teams.append({
                    'team': team['team'],
                    'normalized': team_name_norm,
                    'reason': 'No contract match found'
                })
        
        # Find contracts that weren't matched
        matched_contract_names = {self.normalize_team_name(bet['contract']['team_name']) for bet in matched_bets}
        
        for contract in contracts:
            contract_name_norm = self.normalize_team_name(contract['team_name'])
            if contract_name_norm not in matched_contract_names:
                self.unmatched_contracts.append({
                    'contract': contract['team_name'],
                    'normalized': contract_name_norm,
                    'ticker': contract.get('ticker', ''),
                    'reason': 'No team match found'
                })
        
        # Save unmatched data
        self._save_unmatched_data(output_dir)
        
        self.logger.info(f"Matched {len(matched_bets)} teams to contracts")
        self.logger.info(f"Unmatched teams: {len(self.unmatched_teams)}")
        self.logger.info(f"Unmatched contracts: {len(self.unmatched_contracts)}")
        
        return matched_bets
    
    def match_game_markets(self, games: List[Dict], markets: List[Dict], 
                          output_dir: Path) -> List[Dict]:
        """Match games to Kalshi game winner markets"""
        matched_games = []
        
        for game in games:
            away_team = game['away_team']
            home_team = game['home_team']
            
            # Search for markets containing both team names
            matching_markets = []
            
            for market in markets:
                market_title = market.get('title', '').lower()
                market_subtitle = market.get('subtitle', '').lower()
                
                away_norm = self.normalize_team_name(away_team)
                home_norm = self.normalize_team_name(home_team)
                
                # Check if both team names are in market
                if (away_norm in market_title and home_norm in market_title) or \
                   (away_norm in market_subtitle and home_norm in market_subtitle):
                    matching_markets.append(market)
            
            if len(matching_markets) == 1:
                # Unique match found
                matched_games.append({
                    'game': game,
                    'market': matching_markets[0],
                    'match_type': 'unique'
                })
            elif len(matching_markets) > 1:
                # Multiple matches - ambiguous
                self.unmatched_teams.append({
                    'game': f"{away_team} vs {home_team}",
                    'reason': f'Multiple markets found: {len(matching_markets)}'
                })
            else:
                # No matches
                self.unmatched_teams.append({
                    'game': f"{away_team} vs {home_team}",
                    'reason': 'No market found'
                })
        
        self._save_unmatched_data(output_dir)
        
        self.logger.info(f"Matched {len(matched_games)} games to markets")
        return matched_games
    
    def _save_unmatched_data(self, output_dir: Path):
        """Save unmatched teams and contracts to CSV files"""
        if self.unmatched_teams:
            teams_df = pd.DataFrame(self.unmatched_teams)
            teams_df.to_csv(output_dir / "unmatched_teams.csv", index=False)
        
        if self.unmatched_contracts:
            contracts_df = pd.DataFrame(self.unmatched_contracts)
            contracts_df.to_csv(output_dir / "unmatched_contracts.csv", index=False)
