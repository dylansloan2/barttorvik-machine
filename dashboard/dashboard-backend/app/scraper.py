import logging
import time
import os
from datetime import datetime
from typing import Dict, List
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)

TOURNEYCAST_URL = "https://barttorvik.com/tourneycast.php"
CONCAST_URL = "https://barttorvik.com/concast.php?conlimit={conf}&date={date}"
SCHEDULE_URL = "https://barttorvik.com/schedule.php"

BARTTORVIK_CONF_CODES = {
    "SEC": "SEC",
    "Big 12": "B12",
    "ACC": "ACC",
    "Big Ten": "B10",
    "Big East": "BE",
    "West Coast Conference": "WCC",
    "Mountain West Conference": "MWC",
    "Atlantic 10 Conference": "A10",
    "American Athletic Conference": "Amer",
}


def _resolve_chromedriver_path() -> str:
    """
    Resolve a stable chromedriver binary path to avoid Selenium Manager
    downloading a fresh (and often Gatekeeper-blocked) executable.
    """
    env_path = os.getenv("CHROMEDRIVER_PATH", "").strip()
    if env_path and Path(env_path).exists():
        return env_path

    cache_root = Path.home() / ".cache" / "selenium" / "chromedriver" / "mac-arm64"
    if cache_root.exists():
        drivers = sorted(cache_root.glob("*/chromedriver"), reverse=True)
        for driver in drivers:
            if driver.exists():
                return str(driver)

    auto_root = (
        Path.home()
        / "Library"
        / "Python"
        / "3.9"
        / "lib"
        / "python"
        / "site-packages"
        / "chromedriver_autoinstaller"
    )
    if auto_root.exists():
        drivers = sorted(auto_root.glob("*/chromedriver"), reverse=True)
        for driver in drivers:
            if driver.exists():
                return str(driver)

    return ""


def _create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")

    driver_path = _resolve_chromedriver_path()
    if driver_path:
        logger.info("Using chromedriver at %s", driver_path)
        service = Service(executable_path=driver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
    else:
        logger.warning("No fixed chromedriver path found; falling back to Selenium Manager")
        driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(30)
    return driver


def _parse_pct(text: str) -> float:
    text = text.replace("%", "").replace(",", "").strip()
    if not text or text == "-" or text == "N/A":
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def scrape_tourneycast() -> Dict[str, Dict]:
    logger.info("Scraping tourneycast.php")
    driver = _create_driver()
    teams: Dict[str, Dict] = {}
    try:
        driver.get(TOURNEYCAST_URL)
        time.sleep(8)

        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "table"))
        )

        table = driver.find_element(By.TAG_NAME, "table")

        first_header_row = table.find_element(By.CSS_SELECTOR, "tr")
        header_cells = first_header_row.find_elements(By.TAG_NAME, "th")
        if not header_cells:
            header_cells = first_header_row.find_elements(By.TAG_NAME, "td")
        header_names = [h.text.strip().upper() for h in header_cells]
        logger.info("Tourneycast first header row: %s", header_names)
        num_cols = len(header_names)

        team_col = None
        conf_col = None
        in_col = None
        for i, h in enumerate(header_names):
            if h == "TEAM" and team_col is None:
                team_col = i
            elif h == "CONF" and conf_col is None:
                conf_col = i
            elif (h == "IN %" or h == "IN%") and in_col is None:
                in_col = i

        if team_col is None or in_col is None:
            logger.error("Could not find required columns. Headers: %s", header_names)
            return teams

        rows = table.find_elements(By.TAG_NAME, "tr")
        logger.info("Found %d rows in tourneycast", len(rows))

        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) < num_cols:
                continue

            team_name = cells[team_col].text.strip()
            in_pct = _parse_pct(cells[in_col].text)
            conference = cells[conf_col].text.strip() if conf_col is not None and len(cells) > conf_col else ""

            if not team_name:
                continue

            teams[team_name] = {
                "team": team_name,
                "conference": conference,
                "in_probability": in_pct / 100.0,
            }

        logger.info("Scraped %d teams from tourneycast", len(teams))

    except Exception as e:
        logger.error("Error scraping tourneycast: %s", e)
    finally:
        driver.quit()

    return teams


def scrape_concast(conf_code: str, date_str: str) -> List[Dict]:
    url = CONCAST_URL.format(conf=conf_code, date=date_str)
    logger.info("Scraping concast: %s", url)
    driver = _create_driver()
    teams: List[Dict] = []
    try:
        driver.get(url)
        time.sleep(5)

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "table"))
        )

        tables = driver.find_elements(By.TAG_NAME, "table")
        if not tables:
            logger.error("No tables found for %s", conf_code)
            return teams

        table = tables[0]
        headers = table.find_elements(By.TAG_NAME, "th")
        header_names = [h.text.strip().upper() for h in headers]
        logger.info("Concast %s headers: %s", conf_code, header_names)

        team_col = None
        share_col = None
        sole_col = None
        for i, h in enumerate(header_names):
            if h == "TEAM":
                team_col = i
            elif h == "SHARE":
                share_col = i
            elif h == "SOLE":
                sole_col = i

        if team_col is None or share_col is None:
            logger.error("Could not find required columns for %s. Headers: %s", conf_code, header_names)
            return teams

        rows = table.find_elements(By.TAG_NAME, "tr")
        for row in rows[1:]:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) <= max(team_col, share_col):
                continue

            team_name = cells[team_col].text.strip()
            share_pct = _parse_pct(cells[share_col].text)
            sole_pct = _parse_pct(cells[sole_col].text) if sole_col is not None and len(cells) > sole_col else 0.0

            if not team_name:
                continue

            teams.append({
                "team": team_name,
                "conference": conf_code,
                "share_probability": share_pct / 100.0,
                "sole_probability": sole_pct / 100.0,
            })

        logger.info("Scraped %d teams for conference %s", len(teams), conf_code)

    except Exception as e:
        logger.error("Error scraping concast for %s: %s", conf_code, e)
    finally:
        driver.quit()

    return teams


def scrape_all_conferences(date_str: str) -> Dict[str, List[Dict]]:
    all_conf_data: Dict[str, List[Dict]] = {}
    for kalshi_name, bt_code in BARTTORVIK_CONF_CODES.items():
        teams = scrape_concast(bt_code, date_str)
        if teams:
            all_conf_data[kalshi_name] = teams
        time.sleep(1)
    return all_conf_data


def scrape_schedule() -> List[Dict]:
    logger.info("Scraping schedule.php")
    driver = _create_driver()
    games: List[Dict] = []
    try:
        driver.get(SCHEDULE_URL)
        time.sleep(5)

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "table"))
        )

        table = driver.find_element(By.TAG_NAME, "table")
        headers = table.find_elements(By.TAG_NAME, "th")
        header_names = [h.text.strip().upper() for h in headers]
        logger.info("Schedule headers: %s", header_names)

        rows = table.find_elements(By.TAG_NAME, "tr")
        for row in rows[1:]:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) < 2:
                continue

            time_text = cells[0].text.strip() if len(cells) > 0 else ""
            matchup_text = cells[1].text.strip() if len(cells) > 1 else ""
            line_text = cells[2].text.strip() if len(cells) > 2 else ""

            if not matchup_text:
                continue

            games.append({
                "time": time_text,
                "matchup": matchup_text,
                "line": line_text,
            })

        logger.info("Scraped %d games from schedule", len(games))

    except Exception as e:
        logger.error("Error scraping schedule: %s", e)
    finally:
        driver.quit()

    return games
