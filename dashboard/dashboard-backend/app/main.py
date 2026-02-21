import os
import time
import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.hash import pbkdf2_sha256
from pydantic import BaseModel
import jwt
import requests

from app.scraper import (
    scrape_tourneycast,
    scrape_all_conferences,
    scrape_schedule,
    BARTTORVIK_CONF_CODES,
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = os.getenv("JWT_SECRET", "barttorvik-dashboard-secret-key-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 720

USERS_DB = {
    "dylan": pbkdf2_sha256.hash("bart123#")
}

KALSHI_BASE_URL = os.getenv("KALSHI_BASE_URL", "https://demo-api.kalshi.co/trade-api/v2")
MAKE_TOURNAMENT_SERIES = "KXMAKEMARMAD"
CONFERENCE_SERIES_MAP = {
    "SEC": "KXSECREG",
    "Big 12": "KXBIG12REG",
    "ACC": "KXACCREG",
    "Big Ten": "KXBIG10REG",
    "Big East": "KXBIGEASTREG",
    "West Coast Conference": "KXWCCREG",
    "Mountain West Conference": "KXMWREG",
    "Atlantic 10 Conference": "KXA10REG",
    "American Athletic Conference": "KXAACREG",
}

TEAM_NAME_MAP = {
    "N.C. State": "NC State",
    "Mississippi": "Ole Miss",
    "Miami FL": "Miami",
    "St. John's": "St Johns",
    "Saint Mary's": "Saint Marys",
    "Loyola Chicago": "Loyola-Chicago",
    "UConn": "Connecticut",
    "UCONN": "Connecticut",
    "USC": "Southern California",
    "UCF": "Central Florida",
    "SMU": "Southern Methodist",
    "VCU": "Virginia Commonwealth",
    "BYU": "Brigham Young",
    "LSU": "Louisiana State",
    "UNLV": "Nevada-Las Vegas",
    "UNC": "North Carolina",
    "TCU": "Texas Christian",
}

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class Token(BaseModel):
    access_token: str
    token_type: str


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None or username not in USERS_DB:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def kalshi_get(path: str, params: Optional[dict] = None) -> Optional[dict]:
    url = KALSHI_BASE_URL + path
    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            return None
    return None


def fetch_markets_by_series(series_ticker: str) -> list:
    all_markets = []
    cursor = None
    seen_cursors = set()
    max_pages = 200
    page_count = 0
    while True:
        page_count += 1
        if page_count > max_pages:
            logger.warning("Stopped pagination for %s after %d pages", series_ticker, max_pages)
            break
        params = {"series_ticker": series_ticker, "status": "open", "limit": "200"}
        if cursor:
            params["cursor"] = cursor
        data = kalshi_get("/markets", params=params)
        if data is None:
            break
        markets = data.get("markets", [])
        all_markets.extend(markets)
        next_cursor = data.get("cursor", "")
        if not next_cursor or not markets:
            break
        if next_cursor in seen_cursors:
            logger.warning("Detected repeated cursor for %s, stopping pagination", series_ticker)
            break
        seen_cursors.add(next_cursor)
        cursor = next_cursor
    return all_markets


def normalize_team_name(name: str) -> str:
    name = name.strip()
    name = name.replace(".", "").replace("'", "").replace("\u2019", "")
    name = name.replace("-", " ").replace("  ", " ")
    return name.lower().strip()


def match_team_name(kalshi_name: str, bt_teams: dict) -> Optional[str]:
    if kalshi_name in bt_teams:
        return kalshi_name

    mapped = TEAM_NAME_MAP.get(kalshi_name)
    if mapped and mapped in bt_teams:
        return mapped

    for bt_name in bt_teams:
        mapped_bt = TEAM_NAME_MAP.get(bt_name)
        if mapped_bt and mapped_bt == kalshi_name:
            return bt_name

    kalshi_norm = normalize_team_name(kalshi_name)
    for bt_name in bt_teams:
        bt_norm = normalize_team_name(bt_name)
        if kalshi_norm == bt_norm:
            return bt_name
        if kalshi_norm in bt_norm or bt_norm in kalshi_norm:
            return bt_name

    return None


def match_conf_team(kalshi_name: str, conf_teams: list) -> Optional[dict]:
    for t in conf_teams:
        if t["team"] == kalshi_name:
            return t

    mapped = TEAM_NAME_MAP.get(kalshi_name)
    if mapped:
        for t in conf_teams:
            if t["team"] == mapped:
                return t

    kalshi_norm = normalize_team_name(kalshi_name)
    for t in conf_teams:
        bt_norm = normalize_team_name(t["team"])
        if kalshi_norm == bt_norm:
            return t
        if kalshi_norm in bt_norm or bt_norm in kalshi_norm:
            return t

    for t in conf_teams:
        mapped_bt = TEAM_NAME_MAP.get(t["team"])
        if mapped_bt and normalize_team_name(mapped_bt) == kalshi_norm:
            return t

    return None


def parse_market(m: dict, market_type: str, conference: str) -> Optional[dict]:
    team_name = m.get("yes_sub_title", "")
    if not team_name:
        parts = m.get("ticker", "").rsplit("-", 1)
        if len(parts) == 2:
            team_name = parts[1]
    if not team_name:
        return None

    yes_bid = m.get("yes_bid", 0) / 100.0
    yes_ask = m.get("yes_ask", 0) / 100.0
    no_bid = m.get("no_bid", 0) / 100.0
    no_ask = m.get("no_ask", 0) / 100.0
    last_price = m.get("last_price", 0) / 100.0
    volume = m.get("volume", 0)

    mid_price = (yes_bid + yes_ask) / 2 if (yes_bid + yes_ask) > 0 else last_price

    return {
        "team_name": team_name,
        "ticker": m["ticker"],
        "market_type": market_type,
        "conference": conference,
        "yes_price": yes_bid,
        "no_price": no_bid,
        "yes_ask": yes_ask,
        "no_ask": no_ask,
        "last_price": last_price,
        "volume": volume,
        "implied_prob": round(mid_price, 4),
        "bt_probability": 0.0,
        "ev": 0.0,
        "bt_source": "",
        "share_prob": 0.0,
        "sole_prob": 0.0,
    }


def get_market_cost(parsed_market: dict) -> float:
    """Choose the best available market cost for EV calculations."""
    for key in ("yes_ask", "yes_price", "last_price"):
        value = parsed_market.get(key, 0.0) or 0.0
        if value > 0:
            return float(value)
    return 0.0


_cache: dict = {}
CACHE_TTL = 300
BT_CACHE_TTL = 1800
_scrape_lock = threading.Lock()


def _scrape_barttorvik():
    now = time.time()
    if "bt_tourney" in _cache and now - _cache.get("bt_time", 0) < BT_CACHE_TTL:
        return

    logger.info("Starting BartTorvik scrape...")
    try:
        tourney_data = scrape_tourneycast()
        _cache["bt_tourney"] = tourney_data
        logger.info("Scraped %d teams from tourneycast", len(tourney_data))
    except Exception as e:
        logger.error("Failed to scrape tourneycast: %s", e)
        if "bt_tourney" not in _cache:
            _cache["bt_tourney"] = {}

    try:
        date_str = datetime.now().strftime("%Y%m%d")
        conf_data = scrape_all_conferences(date_str)
        _cache["bt_conferences"] = conf_data
        logger.info("Scraped %d conferences from concast", len(conf_data))
    except Exception as e:
        logger.error("Failed to scrape conferences: %s", e)
        if "bt_conferences" not in _cache:
            _cache["bt_conferences"] = {}

    try:
        schedule_data = scrape_schedule()
        _cache["bt_schedule"] = schedule_data
        logger.info("Scraped %d games from schedule", len(schedule_data))
    except Exception as e:
        logger.error("Failed to scrape schedule: %s", e)
        if "bt_schedule" not in _cache:
            _cache["bt_schedule"] = []

    _cache["bt_time"] = time.time()
    logger.info("BartTorvik scrape complete")


def get_cached_bets() -> list:
    now = time.time()
    if "bets" in _cache and now - _cache.get("bets_time", 0) < CACHE_TTL:
        return _cache["bets"]

    with _scrape_lock:
        _scrape_barttorvik()

    bt_tourney = _cache.get("bt_tourney", {})
    bt_conferences = _cache.get("bt_conferences", {})

    all_bets: list = []

    raw = fetch_markets_by_series(MAKE_TOURNAMENT_SERIES)
    for m in raw:
        parsed = parse_market(m, "Make Tournament", "March Madness")
        if not parsed:
            continue

        bt_match = match_team_name(parsed["team_name"], bt_tourney)
        if bt_match and bt_match in bt_tourney:
            bt_data = bt_tourney[bt_match]
            bt_prob = bt_data["in_probability"]
            parsed["bt_probability"] = round(bt_prob, 4)
            parsed["bt_source"] = f"BT: {bt_data['team']} ({bt_data['conference']})"

            cost = get_market_cost(parsed)
            if cost > 0:
                parsed["ev"] = round(bt_prob * 1.0 - cost, 4)

        all_bets.append(parsed)

    for conf, series in CONFERENCE_SERIES_MAP.items():
        time.sleep(0.3)
        raw = fetch_markets_by_series(series)
        bt_conf_teams = bt_conferences.get(conf, [])

        for m in raw:
            parsed = parse_market(m, "Conference Champion", conf)
            if not parsed:
                continue

            bt_match = match_conf_team(parsed["team_name"], bt_conf_teams)
            if bt_match:
                sole_prob = bt_match["sole_probability"]
                share_prob = bt_match["share_probability"]
                share_only_prob = share_prob - sole_prob

                effective_prob = sole_prob * 1.0 + share_only_prob * 0.5
                parsed["bt_probability"] = round(share_prob, 4)
                parsed["bt_source"] = (
                    f"BT: {bt_match['team']} "
                    f"(Share: {share_prob*100:.1f}%, Sole: {sole_prob*100:.1f}%)"
                )
                parsed["share_prob"] = round(share_prob, 4)
                parsed["sole_prob"] = round(sole_prob, 4)

                cost = get_market_cost(parsed)
                if cost > 0:
                    parsed["ev"] = round(effective_prob - cost, 4)

            all_bets.append(parsed)

    all_bets.sort(key=lambda x: x["ev"], reverse=True)

    _cache["bets"] = all_bets
    _cache["bets_time"] = now
    return all_bets


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    password_hash = USERS_DB.get(form_data.username)
    if not password_hash or not pbkdf2_sha256.verify(form_data.password, password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": form_data.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/api/bets")
async def get_bets(user: str = Depends(get_current_user)):
    bets = get_cached_bets()
    make_tourney = [b for b in bets if b["market_type"] == "Make Tournament"]
    conference = [b for b in bets if b["market_type"] == "Conference Champion"]

    conf_grouped: dict = {}
    for b in conference:
        conf_grouped.setdefault(b["conference"], []).append(b)

    best_ev = sorted(
        [b for b in bets if b["ev"] > 0],
        key=lambda x: x["ev"],
        reverse=True,
    )[:20]

    bt_status = {
        "tourney_teams": len(_cache.get("bt_tourney", {})),
        "conferences_scraped": list(_cache.get("bt_conferences", {}).keys()),
        "schedule_games": len(_cache.get("bt_schedule", [])),
        "last_scrape": _cache.get("bt_time", 0),
    }

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_markets": len(bets),
        "make_tournament": make_tourney,
        "conference_markets": conf_grouped,
        "best_ev_bets": best_ev,
        "bt_status": bt_status,
        "schedule": _cache.get("bt_schedule", []),
    }


@app.get("/api/summary")
async def get_summary(user: str = Depends(get_current_user)):
    bets = get_cached_bets()
    make_tourney = [b for b in bets if b["market_type"] == "Make Tournament"]
    conference = [b for b in bets if b["market_type"] == "Conference Champion"]

    best_ev = sorted(
        [b for b in bets if b["ev"] > 0],
        key=lambda x: x["ev"],
        reverse=True,
    )[:10]

    worst_ev = sorted(
        [b for b in bets if b["ev"] < 0 and b["bt_probability"] > 0],
        key=lambda x: x["ev"],
    )[:10]

    conf_counts: dict = {}
    for b in conference:
        conf_counts[b["conference"]] = conf_counts.get(b["conference"], 0) + 1

    matched_count = sum(1 for b in bets if b["bt_probability"] > 0)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_make_tournament": len(make_tourney),
        "total_conference": len(conference),
        "conferences_tracked": list(conf_counts.keys()),
        "conference_counts": conf_counts,
        "best_ev_bets": best_ev,
        "worst_ev_bets": worst_ev,
        "matched_teams": matched_count,
        "total_markets": len(bets),
    }
