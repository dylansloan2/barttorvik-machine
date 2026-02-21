import os
import time
import logging
import base64
import datetime
import uuid
from typing import Dict, List, Optional, Any

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
        return self._request("GET", path, params=params, auth=auth)

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict] = None,
        json_body: Optional[Dict] = None,
        auth: bool = False,
    ) -> Optional[Dict]:
        url = self.base_url + path
        headers: Dict[str, str] = {}
        if auth:
            headers = self._get_auth_headers(method.upper(), path)

        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = self.session.request(
                    method=method.upper(),
                    url=url,
                    params=params,
                    json=json_body,
                    headers=headers,
                    timeout=30,
                )
                if resp.status_code == 429:
                    wait = 2 ** attempt
                    self.logger.warning("Rate limited, retrying in %ds...", wait)
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                if not resp.text:
                    return {}
                return resp.json()
            except requests.RequestException as exc:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                self.logger.error("%s %s failed: %s", method.upper(), url, exc)
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
                "yes_price": self._read_price(m, "yes_bid"),
                "no_price": self._read_price(m, "no_bid"),
                "yes_ask": self._read_price(m, "yes_ask"),
                "no_ask": self._read_price(m, "no_ask"),
                "last_price": self._read_price(m, "last_price"),
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
                "yes_price": self._read_price(m, "yes_bid"),
                "no_price": self._read_price(m, "no_bid"),
                "yes_ask": self._read_price(m, "yes_ask"),
                "no_ask": self._read_price(m, "no_ask"),
                "last_price": self._read_price(m, "last_price"),
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
            "yes_buy_price": self._read_price(market, "yes_ask"),
            "no_buy_price": self._read_price(market, "no_ask"),
            "yes_bid_price": self._read_price(market, "yes_bid"),
            "no_bid_price": self._read_price(market, "no_bid"),
            "last_price": self._read_price(market, "last_price"),
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

    def _read_price(self, market: Dict[str, Any], base_field: str) -> float:
        dollars_field = f"{base_field}_dollars"
        if dollars_field in market and market[dollars_field] not in (None, ""):
            try:
                value = float(market[dollars_field])
                return max(0.0, min(1.0, value))
            except (TypeError, ValueError):
                pass

        raw = market.get(base_field, 0)
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return 0.0
        if value > 1.0:
            return max(0.0, min(1.0, value / 100.0))
        return max(0.0, min(1.0, value))

    def can_auth_trade(self) -> bool:
        return bool(self.private_key and self.api_key_id)

    def auth_preflight_check(self) -> bool:
        """Validate authenticated portfolio access before live trading."""
        if not self.can_auth_trade():
            self.logger.error("Auth preflight failed: missing key id or private key")
            return False
        data = self._request(
            "GET",
            "/portfolio/orders",
            params={"limit": "1"},
            auth=True,
        )
        if data is None:
            self.logger.error("Auth preflight failed: could not query portfolio orders")
            return False
        self.logger.info("Auth preflight passed: portfolio API reachable")
        return True

    def place_order(
        self,
        ticker: str,
        side: str,
        action: str,
        count: int,
        yes_price_cents: int,
        post_only: bool = False,
        client_order_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        if not self.can_auth_trade():
            self.logger.error("Trading auth not configured (KALSHI_KEY_ID / KALSHI_PRIVATE_KEY_PATH)")
            return None

        if count <= 0:
            self.logger.warning("Skipping order with non-positive count: %s", count)
            return None

        order_id = client_order_id or str(uuid.uuid4())
        payload = {
            "ticker": ticker,
            "client_order_id": order_id,
            "type": "limit",
            "action": action.upper(),
            "side": side.upper(),
            "count": int(count),
            "yes_price": int(yes_price_cents),
            "post_only": bool(post_only),
        }
        return self._request("POST", "/portfolio/orders", json_body=payload, auth=True)

    def get_open_orders(self) -> List[Dict[str, Any]]:
        if not self.can_auth_trade():
            return []
        data = self._request(
            "GET",
            "/portfolio/orders",
            params={"status": "resting", "limit": "200"},
            auth=True,
        )
        if data is None:
            return []
        return data.get("orders", [])

    def cancel_order(self, order_id: str) -> bool:
        if not self.can_auth_trade():
            return False
        data = self._request("DELETE", f"/portfolio/orders/{order_id}", auth=True)
        return data is not None
