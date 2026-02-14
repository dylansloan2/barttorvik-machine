import logging
from datetime import datetime
from typing import List, Dict

from selenium.webdriver.common.by import By

from browser import BrowserClient

SCHEDULE_URL = "https://barttorvik.com/schedule.php?date={date_str}"


class ScheduleScraper:
    def __init__(self, browser: BrowserClient):
        self.browser = browser
        self.logger = logging.getLogger(__name__)

    def scrape_games(self, target_date: datetime) -> List[Dict]:
        date_str = target_date.strftime("%Y%m%d")
        url = SCHEDULE_URL.format(date_str=date_str)
        self.logger.info("Scraping schedule from %s", url)

        if not self.browser.get_page(url, wait_time=5):
            self.logger.error("Failed to load schedule page")
            return []

        games: List[Dict] = []
        try:
            rows = self.browser.find_elements(By.CSS_SELECTOR, "table tr")
            if not rows:
                rows = self.browser.find_elements(By.TAG_NAME, "tr")

            self.logger.info("Found %d table rows", len(rows))

            for row in rows[1:]:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) < 2:
                    continue

                game = self._parse_game_row(cells)
                if game:
                    games.append(game)

        except Exception as exc:
            self.logger.error("Error scraping schedule: %s", exc)

        self.logger.info("Scraped %d games for %s", len(games), date_str)
        return games

    def _parse_game_row(self, cells) -> Dict:
        try:
            matchup_text = ""
            for cell in cells:
                text = cell.text.strip()
                if "@" in text or " at " in text.lower() or " vs " in text.lower():
                    matchup_text = text
                    break

            if not matchup_text:
                if len(cells) >= 2:
                    away_team = cells[0].text.strip()
                    home_team = cells[1].text.strip()
                    if away_team and home_team:
                        return {
                            "away_team": away_team,
                            "home_team": home_team,
                        }
                return {}

            if " at " in matchup_text.lower():
                parts = matchup_text.lower().split(" at ")
            elif " @ " in matchup_text:
                parts = matchup_text.split(" @ ")
            elif " vs " in matchup_text.lower():
                parts = matchup_text.lower().split(" vs ")
            else:
                return {}

            if len(parts) == 2:
                return {
                    "away_team": parts[0].strip(),
                    "home_team": parts[1].strip(),
                }

        except Exception as exc:
            self.logger.debug("Error parsing game row: %s", exc)

        return {}
