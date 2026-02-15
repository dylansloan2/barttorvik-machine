import logging
from typing import List, Dict

from selenium.webdriver.common.by import By

from browser import BrowserClient

CONODDS_URL = "https://barttorvik.com/conodds.php?conf={conf_code}"


class ConCastScraper:
    def __init__(self, browser: BrowserClient):
        self.browser = browser
        self.logger = logging.getLogger(__name__)

    def scrape_conference_odds(self, conf_code: str) -> List[Dict]:
        url = CONODDS_URL.format(conf_code=conf_code)
        self.logger.info("Scraping conference odds from %s", url)

        if not self.browser.get_page(url, wait_time=5):
            self.logger.error("Failed to load conference odds page for %s", conf_code)
            return []

        teams: List[Dict] = []
        try:
            rows = self.browser.find_elements(By.CSS_SELECTOR, "table tr")
            if not rows:
                rows = self.browser.find_elements(By.TAG_NAME, "tr")

            self.logger.info("Found %d table rows for %s", len(rows), conf_code)

            header_idx = self._find_header_indices(rows)
            if header_idx is None:
                self.logger.error("Could not find header row for %s", conf_code)
                return []

            team_col, share_col, sole_col = header_idx

            for row in rows[1:]:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) <= max(team_col, share_col, sole_col):
                    continue

                team_name = cells[team_col].text.strip()
                share_text = cells[share_col].text.strip()
                sole_text = cells[sole_col].text.strip()

                if not team_name or not share_text:
                    continue

                share_prob = self._parse_percentage(share_text)
                sole_prob = self._parse_percentage(sole_text)

                if share_prob is None and sole_prob is None:
                    continue

                team_data: Dict = {
                    "team": team_name,
                    "conference": conf_code,
                    "share_probability": (share_prob or 0.0) / 100.0,
                    "sole_probability": (sole_prob or 0.0) / 100.0,
                }
                teams.append(team_data)

        except Exception as exc:
            self.logger.error("Error scraping conference odds for %s: %s", conf_code, exc)

        self.logger.info("Scraped %d teams for conference %s", len(teams), conf_code)
        return teams

    def _find_header_indices(self, rows):
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "th")
            if not cells:
                cells = row.find_elements(By.TAG_NAME, "td")

            headers = [c.text.strip().lower() for c in cells]

            team_col = None
            share_col = None
            sole_col = None

            for i, h in enumerate(headers):
                if "team" in h:
                    team_col = i
                if h == "share":
                    share_col = i
                if h == "sole":
                    sole_col = i

            if team_col is not None and share_col is not None and sole_col is not None:
                return (team_col, share_col, sole_col)

        return None

    def _parse_percentage(self, text: str):
        text = text.replace("%", "").strip()
        try:
            return float(text)
        except ValueError:
            return None
