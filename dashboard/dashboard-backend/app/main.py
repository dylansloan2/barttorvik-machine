import os
import time
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.hash import pbkdf2_sha256
from pydantic import BaseModel
import jwt
import requests

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

KALSHI_BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"
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

logger = logging.getLogger(__name__)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class Token(BaseModel):
    access_token: str
    token_type: str


def create_access_token(data: dict, expires_delta: timedelta = None):
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


def kalshi_get(path: str, params: dict = None) -> Optional[dict]:
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
    while True:
        params = {"series_ticker": series_ticker, "status": "open", "limit": "200"}
        if cursor:
            params["cursor"] = cursor
        data = kalshi_get("/markets", params=params)
        if data is None:
            break
        markets = data.get("markets", [])
        all_markets.extend(markets)
        cursor = data.get("cursor", "")
        if not cursor or not markets:
            break
    return all_markets


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
    }


_cache: dict = {}
CACHE_TTL = 300


def get_cached_bets() -> list:
    now = time.time()
    if "bets" in _cache and now - _cache["bets_time"] < CACHE_TTL:
        return _cache["bets"]

    all_bets: list = []

    raw = fetch_markets_by_series(MAKE_TOURNAMENT_SERIES)
    for m in raw:
        parsed = parse_market(m, "Make Tournament", "March Madness")
        if parsed:
            all_bets.append(parsed)

    for conf, series in CONFERENCE_SERIES_MAP.items():
        time.sleep(0.3)
        raw = fetch_markets_by_series(series)
        for m in raw:
            parsed = parse_market(m, "Conference Champion", conf)
            if parsed:
                all_bets.append(parsed)

    all_bets.sort(key=lambda x: x["implied_prob"], reverse=True)

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

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_markets": len(bets),
        "make_tournament": make_tourney,
        "conference_markets": conf_grouped,
    }


@app.get("/api/summary")
async def get_summary(user: str = Depends(get_current_user)):
    bets = get_cached_bets()
    make_tourney = [b for b in bets if b["market_type"] == "Make Tournament"]
    conference = [b for b in bets if b["market_type"] == "Conference Champion"]

    top_favorites = sorted(make_tourney, key=lambda x: x["implied_prob"], reverse=True)[:10]
    top_underdogs = sorted(
        [b for b in make_tourney if b["implied_prob"] > 0],
        key=lambda x: x["implied_prob"],
    )[:10]

    conf_counts: dict = {}
    for b in conference:
        conf_counts[b["conference"]] = conf_counts.get(b["conference"], 0) + 1

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_make_tournament": len(make_tourney),
        "total_conference": len(conference),
        "conferences_tracked": list(conf_counts.keys()),
        "conference_counts": conf_counts,
        "top_favorites": top_favorites,
        "top_underdogs": top_underdogs,
    }
