import re
import logging
import time
from typing import List, Dict

from selenium.webdriver.common.by import By

from browser import BrowserClient

TOURNEYCAST_URL = "https://barttorvik.com/tourneycast.php"


class TourneyCastScraper:
    def __init__(self, browser: BrowserClient):
        self.browser = browser
        self.logger = logging.getLogger(__name__)

    def scrape_tourney_probabilities(self) -> List[Dict]:
        self.logger.info("Scraping TourneyCast from %s", TOURNEYCAST_URL)

        if not self.browser.get_page(TOURNEYCAST_URL, wait_time=5):
            self.logger.error("Failed to load TourneyCast page")
            return []

        teams: List[Dict] = []
        try:
            rows = self.browser.find_elements(By.CSS_SELECTOR, "table tr")
            if not rows:
                rows = self.browser.find_elements(By.TAG_NAME, "tr")

            self.logger.info("Found %d table rows", len(rows))

            header_idx = self._find_header_indices(rows)
            if header_idx is None:
                self.logger.error("Could not find TourneyCast header row")
                return []

            team_col, conf_col, in_col = header_idx

            for row in rows[1:]:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) <= max(team_col, conf_col, in_col):
                    continue

                team_name = cells[team_col].text.strip()
                conference = cells[conf_col].text.strip()
                in_pct_text = cells[in_col].text.strip()

                if not team_name or not in_pct_text:
                    continue

                in_prob = self._parse_percentage(in_pct_text)
                if in_prob is None:
                    continue

                team_data: Dict = {
                    "team": team_name,
                    "conference": conference,
                    "in_probability": in_prob / 100.0,
                }

                teams.append(team_data)

        except Exception as exc:
            self.logger.error("Error scraping TourneyCast: %s", exc)

        self.logger.info("Scraped %d teams from TourneyCast", len(teams))
        return teams

    def _find_header_indices(self, rows):
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "th")
            if not cells:
                cells = row.find_elements(By.TAG_NAME, "td")

            headers = [c.text.strip().lower() for c in cells]

            team_col = None
            conf_col = None
            in_col = None

            for i, h in enumerate(headers):
                if h == "team" or h == "":
                    if team_col is None and i == 0:
                        team_col = i
                if "team" in h:
                    team_col = i
                if h in ("conf", "conference"):
                    conf_col = i
                if h in ("in %", "in%", "in"):
                    in_col = i

            if team_col is not None and conf_col is not None and in_col is not None:
                return (team_col, conf_col, in_col)

        return None

    def _parse_percentage(self, text: str):
        text = text.replace("%", "").strip()
        try:
            return float(text)
        except ValueError:
            return None
