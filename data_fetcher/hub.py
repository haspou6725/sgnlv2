import asyncio
import time
from collections import defaultdict, deque
from typing import Any, Deque, Dict, Tuple
from loguru import logger
from .symbols import load_symbols, universe_by_exchange
from .binance_ws import BinanceWS
from .bybit_ws import BybitWS
from .mexc_ws import MEXCWS
from .lbank_ws import LBankWS
from . import binance_rest, bybit_rest, mexc_rest, lbank_rest

Event = Dict[str, Any]

class DataHub:
    def __init__(self):
        self.allowed_symbols = set(load_symbols())
        # Raw per-exchange latest snapshots (kept internal; not emitted)
        self.orderbooks: Dict[Tuple[str, str], Any] = {}
        self.trades: Dict[Tuple[str, str], Deque[Any]] = defaultdict(lambda: deque(maxlen=4000))
        self.marks: Dict[Tuple[str, str], Any] = {}
        self.funding_rates: Dict[Tuple[str, str], Tuple[float, float]] = {}
        self.open_interest: Dict[Tuple[str, str], Deque[Tuple[float, float]]] = defaultdict(lambda: deque(maxlen=2880))
        # Per-exchange derived metrics cache per symbol
        # metrics[(ex, canon_sym)] = { 'price': float|None, 'spread': float|None, 'bid_total': float|None, 'ask_total': float|None, 'ts': float }
        self.metrics: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self.queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=10000)
        self._tasks = []
        self._ws_clients = []
        # Cache symbols that 4xx on Binance premiumIndex/OpenInterest to avoid repeated spam
        self._binance_skip: set[str] = set()
        self._binance_idx: int = 0
        # Track symbols actually observed on Binance WS before querying REST
        self._binance_observed: set[str] = set()

    def _canon(self, ex: str, sym: str) -> str:
        if ex == "lbank":
            return sym.replace("_usdt", "").replace("_", "").upper() + "USDT"
        return sym.upper()

    def _validate_symbol(self, ex: str, sym: str) -> bool:
        return self._canon(ex, sym) in self.allowed_symbols

    def _validate_timestamp(self, ts: float) -> bool:
        if not ts or ts <= 0:
            return False
        now = time.time()
        return abs(now - ts) < 300

    async def _emit(self, event: Event):
        try:
            self.queue.put_nowait(event)
        except asyncio.QueueFull:
            _ = await self.queue.get()
            await self.queue.put(event)

    def _avg(self, vals):
        xs = [float(v) for v in vals if v is not None]
        if not xs:
            return None
        return sum(xs) / len(xs)

    async def _emit_unified(self, canon_sym: str):
        # Collect latest metrics for all exchanges for this symbol
        now = time.time()
        per_ex = [v for (ex, s), v in self.metrics.items() if s == canon_sym and (now - v.get('ts', 0)) <= 180]
        if not per_ex:
            return
        price = self._avg([m.get('price') for m in per_ex])
        spread = self._avg([m.get('spread') for m in per_ex])
        bid_total = self._avg([m.get('bid_total') for m in per_ex])
        ask_total = self._avg([m.get('ask_total') for m in per_ex])
        # imbalance per-ex then averaged
        imbs = []
        for m in per_ex:
            bt = m.get('bid_total')
            at = m.get('ask_total')
            if bt is not None and at is not None and (bt + at) > 0:
                imbs.append((at - bt) / (at + bt))
        imbalance = self._avg(imbs)
        # funding average
        fr_vals = []
        for (ex, s), (ts, rate) in list(self.funding_rates.items()):
            if s == canon_sym and (now - ts) <= 7200:
                fr_vals.append(rate)
        funding = self._avg(fr_vals)
        # oi average (take latest per ex)
        oi_vals = []
        for (ex, s), dq in list(self.open_interest.items()):
            if s == canon_sym and dq:
                ts, val = dq[-1]
                if (now - ts) <= 7200:
                    oi_vals.append(val)
        oi = self._avg(oi_vals)
        # volume not consistently extracted; skip if unavailable
        volume = None
        # mark: use price if no specific mark
        mark = price
        unified = {
            "symbol": canon_sym,
            "price": float(price) if price is not None else None,
            "mark": float(mark) if mark is not None else None,
            "funding": float(funding) if funding is not None else None,
            "oi": float(oi) if oi is not None else None,
            "spread": float(spread) if spread is not None else None,
            "volume": float(volume) if volume is not None else None,
            "depth": {
                "bid_total": float(bid_total) if bid_total is not None else None,
                "ask_total": float(ask_total) if ask_total is not None else None,
                "imbalance": float(imbalance) if imbalance is not None else None,
            },
            "timestamp": int(now),
        }
        await self._emit({"type": "unified", "data": unified})

    async def _on_ob(self, ex, sym, payload):
        if not self._validate_symbol(ex, sym):
            return
        if not isinstance(payload, dict):
            return
        key = (ex, sym)
        self.orderbooks[key] = payload
        # derive spread and depth totals
        bids = []
        asks = []
        try:
            if payload.get("e") == "depthUpdate":
                for it in payload.get("b", []) or []:
                    bids.append((float(it[0]), float(it[1])))
                for it in payload.get("a", []) or []:
                    asks.append((float(it[0]), float(it[1])))
            else:
                d = payload.get("data") or payload.get("depth") or payload.get("data", {})
                bl = d.get("b") or d.get("bid") or d.get("bids") or []
                al = d.get("a") or d.get("ask") or d.get("asks") or []
                for it in bl:
                    if isinstance(it, dict):
                        bids.append((float(it.get("price")), float(it.get("size"))))
                    else:
                        bids.append((float(it[0]), float(it[1])))
                for it in al:
                    if isinstance(it, dict):
                        asks.append((float(it.get("price")), float(it.get("size"))))
                    else:
                        asks.append((float(it[0]), float(it[1])))
        except Exception:
            pass
        bid_total = sum(v for _, v in bids) if bids else None
        ask_total = sum(v for _, v in asks) if asks else None
        spread = None
        try:
            if bids and asks:
                best_bid = max(bids, key=lambda x: x[0])[0]
                best_ask = min(asks, key=lambda x: x[0])[0]
                if best_ask >= best_bid and best_bid > 0 and best_ask > 0:
                    spread = best_ask - best_bid
                    price = (best_bid + best_ask) / 2.0
                else:
                    price = None
            else:
                price = None
        except Exception:
            price = None
        canon = self._canon(ex, sym)
        self.metrics[(ex, canon)] = {
            "price": price,
            "spread": spread,
            "bid_total": bid_total,
            "ask_total": ask_total,
            "ts": time.time(),
        }
        await self._emit_unified(canon)

    async def _on_trade(self, ex, sym, payload):
        if not self._validate_symbol(ex, sym):
            return
        if not isinstance(payload, dict):
            return
        key = (ex, sym)
        self.trades[key].append(payload)
        if ex == "binance":
            self._binance_observed.add(sym)
        # extract price if available
        price = None
        try:
            if payload.get("e") == "aggTrade":
                price = float(payload.get("p", 0) or 0)
            elif payload.get("topic", "").startswith("publicTrade."):
                arr = payload.get("data", [])
                if arr:
                    price = float(arr[-1].get("p", 0) or 0)
            elif payload.get("method") in ("rs.deal", "push.deal"):
                arr = payload.get("data", [])
                if arr:
                    price = float(arr[-1].get("p", 0) or 0)
            elif payload.get("subscribe") == "trade.update":
                arr = payload.get("trades", [])
                if arr:
                    price = float(arr[-1].get("price", 0) or 0)
        except Exception:
            price = None
        canon = self._canon(ex, sym)
        if price and price > 0:
            prev = self.metrics.get((ex, canon), {})
            prev.update({"price": float(price), "ts": time.time()})
            self.metrics[(ex, canon)] = prev
        await self._emit_unified(canon)

    async def _on_mark(self, ex, sym, payload):
        if not self._validate_symbol(ex, sym):
            return
        if not isinstance(payload, dict):
            return
        key = (ex, sym)
        self.marks[key] = payload
        if ex == "binance":
            self._binance_observed.add(sym)
        # extract mark/price
        price = None
        try:
            price = payload.get("p") or payload.get("markPrice") or payload.get("price") or payload.get("last") or payload.get("c")
            if isinstance(price, str):
                price = float(price)
        except Exception:
            price = None
        canon = self._canon(ex, sym)
        if price and price > 0:
            prev = self.metrics.get((ex, canon), {})
            prev.update({"price": float(price), "ts": time.time()})
            self.metrics[(ex, canon)] = prev
        await self._emit_unified(canon)

    async def _funding_oi_loop(self, uni: Dict[str, list[str]]):
        while True:
            try:
                ts = time.time()
                # Only query Binance REST for symbols we have actually seen on WS
                observed = sorted(self._binance_observed)
                bin_syms = observed if observed else []
                # process a limited window per cycle to avoid flooding
                if bin_syms:
                    start = self._binance_idx
                    end = min(len(bin_syms), start + 50)
                    window = bin_syms[start:end]
                    self._binance_idx = 0 if end >= len(bin_syms) else end
                else:
                    window = []
                for sym in window:
                    if sym in self._binance_skip:
                        continue
                    try:
                        fund, oi = await binance_rest.funding_oi(sym)
                        rate = float(fund.get("lastFundingRate", 0) or 0)
                        self.funding_rates[("binance", sym)] = (ts, rate)
                        if isinstance(oi, list) and oi:
                            last = oi[-1]
                            val = float(last.get("sumOpenInterestValue") or last.get("sumOpenInterest", 0) or 0)
                            self.open_interest[("binance", sym)].append((ts, val))
                        await self._emit_unified(sym)
                    except Exception as e:
                        logger.debug(f"binance funding/oi for {sym} failed: {e}")
                        # On repeated 4xx, skip further attempts this session
                        self._binance_skip.add(sym)
                for sym in uni.get("bybit", []):
                    try:
                        data = await bybit_rest.oi(sym)
                        lst = data.get("result", {}).get("list", [])
                        if lst:
                            last = lst[-1]
                            val = float(last.get("openInterest", 0))
                            self.open_interest[("bybit", sym)].append((ts, val))
                        await self._emit_unified(sym)
                    except Exception as e:
                        logger.debug(f"bybit oi for {sym} failed: {e}")
                for sym in uni.get("mexc", []):
                    try:
                        data = await mexc_rest.funding(sym)
                        rate = float(data.get("data", {}).get("lastFundingRate", 0)) if isinstance(data.get("data"), dict) else 0.0
                        self.funding_rates[("mexc", sym)] = (ts, rate)
                        await self._emit_unified(sym)
                    except Exception as e:
                        logger.debug(f"mexc funding for {sym} failed: {e}")
                for sym in uni.get("lbank", []):
                    try:
                        data = await lbank_rest.funding(sym)
                        rate = 0.0
                        if isinstance(data, dict) and data.get("result", False):
                            arr = data.get("data") or []
                            if arr:
                                rate = float(arr[-1].get("rate", 0))
                        self.funding_rates[("lbank", sym)] = (ts, rate)
                        await self._emit_unified(sym)
                    except Exception as e:
                        logger.debug(f"lbank funding for {sym} failed: {e}")
            except Exception as e:
                logger.warning(f"Funding/OI loop error: {e}")
            await asyncio.sleep(60)

    async def _staleness_check_loop(self):
        while True:
            await asyncio.sleep(60)
            for ws in self._ws_clients:
                if hasattr(ws, "staleness_check"):
                    stale = ws.staleness_check()
                    if stale:
                        logger.warning(f"{ws.__class__.__name__} stale streams: {stale}")

    async def start(self):
        uni = universe_by_exchange()
        if not any(len(v) for v in uni.values()):
            logger.warning("Empty universe; using fallback")
            uni = {"binance": ["BTCUSDT"], "bybit": ["BTCUSDT"], "mexc": ["BTCUSDT"], "lbank": ["btc_usdt"]}
        tasks = []
        if uni.get("binance"):
            ws_b = BinanceWS(uni["binance"], self._on_ob, self._on_trade, self._on_mark)
            self._ws_clients.append(ws_b)
            tasks.append(asyncio.create_task(ws_b.run()))
        if uni.get("bybit"):
            ws_y = BybitWS(uni["bybit"], self._on_ob, self._on_trade, self._on_trade)
            self._ws_clients.append(ws_y)
            tasks.append(asyncio.create_task(ws_y.run()))
        if uni.get("mexc"):
            ws_m = MEXCWS(uni["mexc"], self._on_ob, self._on_trade, self._on_mark)
            self._ws_clients.append(ws_m)
            tasks.append(asyncio.create_task(ws_m.run()))
        if uni.get("lbank"):
            ws_l = LBankWS(uni["lbank"], self._on_ob, self._on_trade)
            self._ws_clients.append(ws_l)
            tasks.append(asyncio.create_task(ws_l.run()))
        tasks.append(asyncio.create_task(self._funding_oi_loop(uni)))
        tasks.append(asyncio.create_task(self._staleness_check_loop()))
        self._tasks = tasks
        # Don't await tasks here - let orchestrator manage them
        # Returning immediately allows orchestrator to run all components concurrently
