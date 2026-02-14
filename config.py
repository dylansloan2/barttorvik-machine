import yaml
import os
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime, timezone

class Config:
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "config.yaml"
        
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Load conference map
        conference_map_path = Path(__file__).parent.parent / "config" / "conference_map.yaml"
        with open(conference_map_path, 'r') as f:
            self.conference_map = yaml.safe_load(f)['conferences']
    
    @property
    def scraping(self) -> Dict[str, Any]:
        return self.config.get('scraping', {})
    
    @property
    def ev(self) -> Dict[str, Any]:
        return self.config.get('ev', {})
    
    @property
    def kalshi(self) -> Dict[str, Any]:
        return self.config.get('kalshi', {})
    
    @property
    def output(self) -> Dict[str, Any]:
        return self.config.get('output', {})
    
    @property
    def conferences(self) -> List[str]:
        return self.config.get('conferences', [])
    
    @property
    def market_titles(self) -> Dict[str, Any]:
        return self.config.get('market_titles', {})
    
    def get_conference_code(self, conference_name: str) -> str:
        """Get BartTorvik conference code from full name"""
        return self.conference_map.get(conference_name, conference_name)
    
    def get_output_dir(self, date: datetime = None) -> Path:
        """Get output directory for a specific date"""
        if date is None:
            date = datetime.now(timezone.utc)
        
        date_str = date.strftime(self.output['date_format'])
        base_dir = Path(__file__).parent.parent / "out"
        output_dir = base_dir / date_str
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir
