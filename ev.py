from typing import Dict, List, Optional
import logging
from dataclasses import dataclass

@dataclass
class Bet:
    market_type: str
    league_conf: str
    description: str
    model_prob_or_exp_payout: float
    yes_price: float
    ev: float
    edge: float
    contract_ticker: str
    team_name: str

class EVCalculator:
    def __init__(self, min_ev: float = 0.02, share_factor: float = 0.5):
        self.min_ev = min_ev
        self.share_factor = share_factor
        self.logger = logging.getLogger(__name__)
    
    def calculate_make_tournament_ev(self, team_data: Dict, contract: Dict) -> Optional[Bet]:
        """Calculate EV for Make Tournament markets"""
        try:
            model_prob = team_data['in_probability']
            market_price = contract['yes_price']
            
            # EV = model_prob - market_price
            ev = model_prob - market_price
            
            # Edge is same as EV for binary markets
            edge = ev
            
            if ev >= self.min_ev:
                return Bet(
                    market_type="Make Tournament",
                    league_conf="March Madness",
                    description=f"{team_data['team']} to Make Tournament",
                    model_prob_or_exp_payout=model_prob,
                    yes_price=market_price,
                    ev=ev,
                    edge=edge,
                    contract_ticker=contract.get('ticker', ''),
                    team_name=team_data['team']
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error calculating make tournament EV: {e}")
            return None
    
    def calculate_conference_champ_ev(self, team_data: Dict, contract: Dict, 
                                    conference: str) -> Optional[Bet]:
        """Calculate EV for Conference Champion markets"""
        try:
            p_sole = team_data['sole_probability']
            p_share = team_data['share_probability']
            market_price = contract['yes_price']
            
            # Expected payout = p_sole * 1.0 + p_share * share_factor
            exp_payout = p_sole * 1.0 + p_share * self.share_factor
            
            # EV = exp_payout - market_price
            ev = exp_payout - market_price
            
            # Edge is same as EV for these markets
            edge = ev
            
            if ev >= self.min_ev:
                return Bet(
                    market_type="Conference Champion",
                    league_conf=conference,
                    description=f"{team_data['team']} to Win {conference}",
                    model_prob_or_exp_payout=exp_payout,
                    yes_price=market_price,
                    ev=ev,
                    edge=edge,
                    contract_ticker=contract.get('ticker', ''),
                    team_name=team_data['team']
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error calculating conference champ EV: {e}")
            return None
    
    def calculate_game_winner_ev(self, game_data: Dict, contract: Dict, 
                               favored_team: str) -> Optional[Bet]:
        """Calculate EV for Game Winner markets"""
        try:
            # Determine which team we're betting on
            if contract['team_name'].lower() == favored_team.lower():
                model_prob = game_data['win_probability']
            else:
                # Underdog probability
                model_prob = 1.0 - game_data['win_probability']
            
            market_price = contract['yes_price']
            
            # EV = model_prob - market_price
            ev = model_prob - market_price
            
            # Edge is same as EV for binary markets
            edge = ev
            
            if ev >= self.min_ev:
                return Bet(
                    market_type="Game Winner",
                    league_conf="NCAA",
                    description=f"{contract['team_name']} vs {game_data['away_team'] if game_data['away_team'] != contract['team_name'] else game_data['home_team']}",
                    model_prob_or_exp_payout=model_prob,
                    yes_price=market_price,
                    ev=ev,
                    edge=edge,
                    contract_ticker=contract.get('ticker', ''),
                    team_name=contract['team_name']
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error calculating game winner EV: {e}")
            return None
    
    def calculate_all_bets(self, matched_data: List[Dict], market_type: str, 
                         conference: str = None) -> List[Bet]:
        """Calculate EV for all matched bets"""
        bets = []
        
        for match in matched_data:
            team_data = match['model_data']
            contract = match['contract']
            
            if market_type == "make_tournament":
                bet = self.calculate_make_tournament_ev(team_data, contract)
            elif market_type == "conference_champ":
                bet = self.calculate_conference_champ_ev(team_data, contract, conference)
            elif market_type == "game_winner":
                # For games, we need the game data and favored team
                game_data = match.get('game_data')
                favored_team = match.get('favored_team')
                if game_data and favored_team:
                    bet = self.calculate_game_winner_ev(game_data, contract, favored_team)
                else:
                    self.logger.warning(f"Missing game data for {contract['team_name']}")
                    bet = None
            else:
                self.logger.warning(f"Unknown market type: {market_type}")
                bet = None
            
            if bet:
                bets.append(bet)
        
        # Sort by EV descending
        bets.sort(key=lambda x: x.ev, reverse=True)
        
        self.logger.info(f"Calculated {len(bets)} qualifying bets for {market_type}")
        return bets
