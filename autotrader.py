import json
import logging
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Optional, Set
from zoneinfo import ZoneInfo

from ev import Bet
from kalshi.kalshi_client import KalshiClient


@dataclass
class AutotradeConfig:
    bankroll: float
    min_edge: float = 0.15
    kelly_fraction: float = 0.25
    maker_discount: float = 0.02
    min_price: float = 0.01
    max_price: float = 0.99
    poll_seconds: int = 30
    max_daily_exposure: float = 300.0
    max_per_market_exposure: float = 75.0
    max_orders_per_run: int = 40
    order_retries: int = 3
    state_file: str = "out/autotrader_state.json"
    kill_switch_file: str = "autotrader.stop"
    schedule_timezone: str = "America/Chicago"


@dataclass
class PlacedOrder:
    ticker: str
    team_name: str
    side: str
    action: str
    count: int
    yes_price: float
    post_only: bool
    client_order_id: str
    order_id: str
    notional: float


class AutoTrader:
    def __init__(self, client: KalshiClient, config: AutotradeConfig, timezone_name: str = "America/Chicago"):
        self.client = client
        self.config = config
        self.tz = ZoneInfo(timezone_name)
        self.schedule_tz = ZoneInfo(config.schedule_timezone)
        self.logger = logging.getLogger(__name__)
        self.state_path = Path(config.state_file)
        self.kill_switch_path = Path(config.kill_switch_file)
        self.state = self._load_state()

    def validate_live_trading_readiness(self) -> bool:
        if self._kill_switch_enabled():
            self.logger.error("Kill switch enabled; refusing live trading")
            return False
        if not self.client.auth_preflight_check():
            return False
        return True

    def _kill_switch_enabled(self) -> bool:
        env_value = os.getenv("AUTOTRADER_KILL_SWITCH", "").strip().lower()
        if env_value in {"1", "true", "on", "yes"}:
            return True
        return self.kill_switch_path.exists()

    def _today_key(self) -> str:
        return datetime.now(self.tz).date().isoformat()

    def _load_state(self) -> Dict:
        if not self.state_path.exists():
            return {"by_date": {}}
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"by_date": {}}

    def _save_state(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2)

    def _daily_bucket(self) -> Dict:
        today = self._today_key()
        by_date = self.state.setdefault("by_date", {})
        return by_date.setdefault(today, {"submitted_ids": [], "orders": []})

    def _submitted_ids(self) -> Set[str]:
        return set(self._daily_bucket().get("submitted_ids", []))

    def _record_order(self, order: PlacedOrder) -> None:
        bucket = self._daily_bucket()
        bucket.setdefault("submitted_ids", []).append(order.client_order_id)
        bucket.setdefault("orders", []).append(
            {
                "ticker": order.ticker,
                "team_name": order.team_name,
                "side": order.side,
                "action": order.action,
                "count": order.count,
                "yes_price": order.yes_price,
                "post_only": order.post_only,
                "client_order_id": order.client_order_id,
                "order_id": order.order_id,
                "notional": order.notional,
                "ts": int(time.time()),
            }
        )
        self._save_state()

    def _daily_notional(self) -> float:
        return sum(float(o.get("notional", 0.0)) for o in self._daily_bucket().get("orders", []))

    def _market_notional(self, ticker: str) -> float:
        total = 0.0
        for o in self._daily_bucket().get("orders", []):
            if o.get("ticker") == ticker:
                total += float(o.get("notional", 0.0))
        return total

    def _quarter_kelly_contracts(self, model_prob: float, price: float) -> int:
        if price <= 0 or price >= 1:
            return 0
        full_kelly = (model_prob - price) / (1.0 - price)
        frac = max(0.0, full_kelly) * self.config.kelly_fraction
        dollars = self.config.bankroll * frac
        if dollars <= 0:
            return 0
        return int(dollars / price)

    def _maker_price(self, fair_prob: float) -> float:
        p = fair_prob - self.config.maker_discount
        p = max(self.config.min_price, min(self.config.max_price, p))
        return round(p, 2)

    def _taker_price(self, ticker: str) -> float:
        prices = self.client.get_market_prices(ticker)
        yes_ask = float(prices.get("yes_buy_price", 0.0) or 0.0)
        if yes_ask > 0:
            return yes_ask
        last_price = float(prices.get("last_price", 0.0) or 0.0)
        return last_price

    def _idempotency_id(self, ticker: str, side: str, action: str, yes_price_cents: int, post_only: bool) -> str:
        mode = "mm" if post_only else "tk"
        return f"{mode}-{self._today_key()}-{ticker}-{side}-{action}-{yes_price_cents}"

    def _can_allocate_notional(self, ticker: str, notional: float) -> bool:
        if self._daily_notional() + notional > self.config.max_daily_exposure:
            return False
        if self._market_notional(ticker) + notional > self.config.max_per_market_exposure:
            return False
        return True

    def trade_best_edges(self, bets: List[Bet], live_orders: bool = False) -> Dict[str, List[PlacedOrder]]:
        if self._kill_switch_enabled():
            self.logger.warning("Kill switch is on; skipping autotrader execution")
            return {"taker": [], "maker": []}

        candidates = [b for b in bets if b.ev >= self.config.min_edge and b.contract_ticker]
        candidates.sort(key=lambda b: b.ev, reverse=True)
        self.logger.info(
            "Autotrader: %d candidates with edge >= %.1f%%",
            len(candidates),
            self.config.min_edge * 100.0,
        )

        existing_ids = self._submitted_ids()
        open_ids = set()
        if live_orders:
            for o in self.client.get_open_orders():
                cid = o.get("client_order_id")
                if cid:
                    open_ids.add(cid)

        taker_orders: List[PlacedOrder] = []
        maker_orders: List[PlacedOrder] = []
        placed_count = 0

        for bet in candidates:
            if placed_count >= self.config.max_orders_per_run:
                break

            taker_price = self._taker_price(bet.contract_ticker)
            model_prob = float(bet.model_prob_or_exp_payout)

            post_only = False
            price = taker_price
            if price <= 0:
                post_only = True
                price = self._maker_price(model_prob)

            count = self._quarter_kelly_contracts(model_prob, price)
            if count <= 0:
                continue

            notional = count * price
            if not self._can_allocate_notional(bet.contract_ticker, notional):
                self.logger.info("Risk cap hit for %s, skipping", bet.contract_ticker)
                continue

            yes_price_cents = int(round(price * 100))
            order_id = self._idempotency_id(
                ticker=bet.contract_ticker,
                side="YES",
                action="BUY",
                yes_price_cents=yes_price_cents,
                post_only=post_only,
            )
            if order_id in existing_ids or order_id in open_ids:
                self.logger.info("Skipping duplicate order id %s", order_id)
                continue

            order = self._place(
                ticker=bet.contract_ticker,
                team_name=bet.team_name,
                side="YES",
                action="BUY",
                count=count,
                yes_price=price,
                post_only=post_only,
                order_id=order_id,
                notional=notional,
                live_orders=live_orders,
            )
            if not order:
                continue
            if post_only:
                maker_orders.append(order)
            else:
                taker_orders.append(order)
            placed_count += 1

        self.logger.info(
            "Autotrader summary: taker=%d maker=%d live=%s daily_notional=%.2f",
            len(taker_orders),
            len(maker_orders),
            live_orders,
            self._daily_notional(),
        )
        return {"taker": taker_orders, "maker": maker_orders}

    def _place(
        self,
        ticker: str,
        team_name: str,
        side: str,
        action: str,
        count: int,
        yes_price: float,
        post_only: bool,
        order_id: str,
        notional: float,
        live_orders: bool,
    ) -> Optional[PlacedOrder]:
        yes_price_cents = int(round(yes_price * 100))

        final_order_id = order_id
        if live_orders:
            success = False
            for attempt in range(self.config.order_retries):
                response = self.client.place_order(
                    ticker=ticker,
                    side=side,
                    action=action,
                    count=count,
                    yes_price_cents=yes_price_cents,
                    post_only=post_only,
                    client_order_id=order_id,
                )
                if response is not None:
                    response_order_id = self._extract_order_id(response)
                    if response_order_id:
                        final_order_id = response_order_id
                    success = True
                    break
                sleep_for = 2 ** attempt
                time.sleep(sleep_for)
            if not success:
                self.logger.error("Order failed after retries: %s %s x%d @ %.2f", ticker, side, count, yes_price)
                return None

        order = PlacedOrder(
            ticker=ticker,
            team_name=team_name,
            side=side,
            action=action,
            count=count,
            yes_price=yes_price,
            post_only=post_only,
            client_order_id=order_id,
            order_id=final_order_id,
            notional=notional,
        )
        self._record_order(order)
        self.logger.info(
            "%s order %s x%d @ %.2f (%s) notional=%.2f",
            "LIVE" if live_orders else "SIM",
            ticker,
            count,
            yes_price,
            "maker" if post_only else "taker",
            notional,
        )
        return order

    def cancel_maker_orders_at_first_tipoff(
        self,
        games: List[Dict],
        maker_orders: List[PlacedOrder],
        target_date: date,
        live_orders: bool,
    ) -> int:
        first_tipoff = self._first_tipoff_datetime(games, target_date)
        if first_tipoff is None:
            self.logger.warning("Could not determine first tipoff time; skipping maker cancel automation")
            return 0

        now = datetime.now(self.tz)
        if now < first_tipoff:
            wait_seconds = int((first_tipoff - now).total_seconds())
            self.logger.info(
                "Waiting %d seconds until first tipoff (%s) to cancel maker orders",
                wait_seconds,
                first_tipoff.isoformat(),
            )
            while wait_seconds > 0:
                sleep_for = min(wait_seconds, self.config.poll_seconds)
                time.sleep(sleep_for)
                wait_seconds -= sleep_for

        order_ids: List[str] = [o.order_id for o in maker_orders if o.order_id]
        if live_orders and not order_ids:
            # Fallback: cancel any live maker orders opened earlier today by this strategy.
            for o in self.client.get_open_orders():
                cid = o.get("client_order_id", "")
                oid = o.get("order_id")
                if cid.startswith("mm-") and self._today_key() in cid and oid:
                    order_ids.append(oid)

        canceled = 0
        for order_id in order_ids:
            if not live_orders:
                canceled += 1
                self.logger.info("SIM cancel maker order: %s", order_id)
                continue
            if self.client.cancel_order(order_id):
                canceled += 1
                self.logger.info("Canceled maker order: %s", order_id)
        return canceled

    def _parse_tipoff_text(self, text: str) -> Optional[datetime]:
        cleaned = text.strip().upper()
        cleaned = re.sub(r"\b(ET|CT|MT|PT|EST|CST|MST|PST)\b", "", cleaned).strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        for fmt in ("%I:%M %p", "%I %p"):
            try:
                t = datetime.strptime(cleaned, fmt).time()
                return datetime.combine(datetime.now(self.schedule_tz).date(), t, self.schedule_tz)
            except ValueError:
                continue
        return None

    def _first_tipoff_datetime(self, games: List[Dict], target_date: date) -> Optional[datetime]:
        parsed: List[datetime] = []
        for game in games:
            time_text = (game.get("time") or "").strip()
            if not time_text:
                continue
            parsed_dt = self._parse_tipoff_text(time_text)
            if parsed_dt is None:
                continue
            parsed_dt = parsed_dt.replace(year=target_date.year, month=target_date.month, day=target_date.day)
            parsed.append(parsed_dt.astimezone(self.tz))
        if not parsed:
            return None
        return min(parsed)

    def _extract_order_id(self, response: Dict) -> Optional[str]:
        if "order_id" in response:
            return response.get("order_id")
        if "order" in response and isinstance(response["order"], dict):
            return response["order"].get("order_id")
        return None
