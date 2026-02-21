import os
import time
import logging
import base64
import datetime
from typing import Dict, List, Optional

import requests
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import padding


BASE_URL = "https://demo-api.kalshi.co/trade-api/v2"

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


class KalshiClient:
    def __init__(self, base_url: str = None):
        self.logger = logging.getLogger(__name__)
        self.base_url = base_url or os.getenv("KALSHI_BASE_URL", BASE_URL)
        self.session = requests.Session()
        self.private_key = None
        self.api_key_id = os.getenv("KALSHI_KEY_ID", "")

        key_path = os.getenv("KALSHI_PRIVATE_KEY_PATH", "")
        if key_path and os.path.exists(key_path):
            self._load_private_key(key_path)

    def _load_private_key(self, key_path: str) -> None:
        with open(key_path, "rb") as f:
            self.private_key = serialization.load_pem_private_key(
                f.read(), password=None, backend=default_backend()
            )
        self.logger.info("Loaded private key from %s", key_path)

    def _sign_request(self, timestamp: str, method: str, path: str) -> str:
        path_without_query = path.split("?")[0]
        message = f"{timestamp}{method}{path_without_query}".encode("utf-8")
        signature = self.private_key.sign(
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.DIGEST_LENGTH,
            ),
            hashes.SHA256(),
        )
        return base64.b64encode(signature).decode("utf-8")

    def _get_auth_headers(self, method: str, path: str) -> Dict[str, str]:
        if not self.private_key or not self.api_key_id:
            return {}
        timestamp = str(int(datetime.datetime.now().timestamp() * 1000))
        signature = self._sign_request(timestamp, method, path)
        return {
            "KALSHI-ACCESS-KEY": self.api_key_id,
            "KALSHI-ACCESS-SIGNATURE": signature,
            "KALSHI-ACCESS-TIMESTAMP": timestamp,
        }

    def _get(self, path: str, params: Optional[Dict] = None, auth: bool = False) -> Optional[Dict]:
        url = self.base_url + path
        headers = {}
        if auth:
            headers = self._get_auth_headers("GET", path)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = self.session.get(url, params=params, headers=headers, timeout=30)
                if resp.status_code == 429:
                    wait = 2 ** attempt
                    self.logger.warning("Rate limited, retrying in %ds...", wait)
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp.json()
            except requests.RequestException as exc:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                self.logger.error("GET %s failed: %s", url, exc)
                return None
        return None

    def preflight_check(self) -> bool:
        data = self._get("/markets", params={"limit": "1", "status": "open"})
        if data is None:
            return False
        markets = data.get("markets", [])
        if not markets:
            self.logger.warning("Preflight: no open markets returned")
            return False
        self.logger.info("Preflight: API reachable, got %d market(s)", len(markets))
        return True

    def _fetch_all_markets(self, params: Dict) -> List[Dict]:
        all_markets: List[Dict] = []
        cursor = None
        while True:
            req_params = dict(params)
            req_params["limit"] = "200"
            if cursor:
                req_params["cursor"] = cursor
            data = self._get("/markets", params=req_params)
            if data is None:
                break
            markets = data.get("markets", [])
            all_markets.extend(markets)
            cursor = data.get("cursor", "")
            if not cursor or not markets:
                break
        return all_markets

    def get_markets_by_series(self, series_ticker: str, status: str = "open") -> List[Dict]:
        params = {"series_ticker": series_ticker, "status": status}
        return self._fetch_all_markets(params)

    def get_markets_by_event(self, event_ticker: str, status: str = "open") -> List[Dict]:
        params = {"event_ticker": event_ticker, "status": status}
        return self._fetch_all_markets(params)

    def get_make_tournament_markets(self) -> List[Dict]:
        raw_markets = self.get_markets_by_series(MAKE_TOURNAMENT_SERIES)
        self.logger.info("Fetched %d raw Make Tournament markets", len(raw_markets))

        results: List[Dict] = []
        for m in raw_markets:
            team_name = m.get("yes_sub_title", "")
            if not team_name:
                team_name = self._extract_team_from_ticker(m.get("ticker", ""))
            if not team_name:
                continue

            results.append({
                "ticker": m["ticker"],
                "title": m.get("title", ""),
                "team_name": team_name,
                "yes_price": m.get("yes_bid", 0) / 100.0,
                "no_price": m.get("no_bid", 0) / 100.0,
                "yes_ask": m.get("yes_ask", 0) / 100.0,
                "no_ask": m.get("no_ask", 0) / 100.0,
                "last_price": m.get("last_price", 0) / 100.0,
                "volume": m.get("volume", 0),
                "status": m.get("status", ""),
                "event_ticker": m.get("event_ticker", ""),
            })

        self.logger.info("Parsed %d Make Tournament markets with team names", len(results))
        return results

    def get_conference_markets(self, conference: str) -> List[Dict]:
        series_ticker = CONFERENCE_SERIES_MAP.get(conference)
        if not series_ticker:
            self.logger.warning("No series ticker mapped for conference: %s", conference)
            return []

        raw_markets = self.get_markets_by_series(series_ticker)
        self.logger.info("Fetched %d raw %s conference markets", len(raw_markets), conference)

        results: List[Dict] = []
        for m in raw_markets:
            team_name = m.get("yes_sub_title", "")
            if not team_name:
                team_name = self._extract_team_from_ticker(m.get("ticker", ""))
            if not team_name:
                continue

            results.append({
                "ticker": m["ticker"],
                "title": m.get("title", ""),
                "team_name": team_name,
                "yes_price": m.get("yes_bid", 0) / 100.0,
                "no_price": m.get("no_bid", 0) / 100.0,
                "yes_ask": m.get("yes_ask", 0) / 100.0,
                "no_ask": m.get("no_ask", 0) / 100.0,
                "last_price": m.get("last_price", 0) / 100.0,
                "volume": m.get("volume", 0),
                "status": m.get("status", ""),
                "event_ticker": m.get("event_ticker", ""),
            })

        return results

    def get_market_prices(self, ticker: str) -> Dict:
        data = self._get(f"/markets/{ticker}")
        if data is None:
            return {}
        market = data.get("market", {})
        return {
            "yes_buy_price": market.get("yes_ask", 0) / 100.0,
            "no_buy_price": market.get("no_ask", 0) / 100.0,
            "yes_bid_price": market.get("yes_bid", 0) / 100.0,
            "no_bid_price": market.get("no_bid", 0) / 100.0,
            "last_price": market.get("last_price", 0) / 100.0,
        }

    def _get_yes_price(self, ticker: str) -> float:
        """
        Backward-compatible helper used by older test scripts.
        Returns the best YES ask as a dollar price.
        """
        prices = self.get_market_prices(ticker)
        return float(prices.get("yes_buy_price", 0.0))

    def get_market_orderbook(self, ticker: str) -> Dict:
        data = self._get(f"/markets/{ticker}/orderbook")
        if data is None:
            return {}
        return data.get("orderbook", {})

    def get_markets_by_title(self, search_term: str, status: str = "open") -> List[Dict]:
        all_markets = self._fetch_all_markets({"status": status})
        term_lower = search_term.lower()
        return [
            m for m in all_markets
            if term_lower in m.get("title", "").lower()
            or term_lower in m.get("yes_sub_title", "").lower()
        ]

    def _extract_team_from_ticker(self, ticker: str) -> str:
        parts = ticker.rsplit("-", 1)
        if len(parts) == 2:
            return parts[1]
        return ""
