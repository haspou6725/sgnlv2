import os
import asyncio
import time
import json
import hashlib
from collections import defaultdict, deque
from loguru import logger
from data_fetcher.hub import DataHub
from data_fetcher.symbols import load_symbols
from features.microstructure import Microstructure
from features.btc_regime import BTCRegime
from features.liquidity import Liquidity
from features.sweeps import Sweeps
from features.volatility import Volatility
from features.funding import Funding
from features.oi import OpenInterest
from scalp_engine.symbol_selector import SymbolSelector
from scalp_engine.scorer import Scorer
from scalp_engine.entry_trigger import EntryTrigger
from scalp_engine.exit_manager import ExitManager
from storage.sqlite_cache import SQLiteCache
from telegram_bot.notifier import TelegramNotifier

class Orchestrator:
    def __init__(self):
        self.hub = DataHub()
        self.selector = SymbolSelector()
        self.ms = Microstructure()
        self.liq = Liquidity()
        self.sweeps = Sweeps()
        self.vol_idx: dict[str, Volatility] = defaultdict(lambda: Volatility())
        self.funding = Funding()
        self.oi = OpenInterest()
        self.btc = BTCRegime()
        self.scorer = Scorer()
        self.entry = EntryTrigger()
        self.exit = ExitManager()
        self.db = SQLiteCache("/app/state/data.db")
        
        token = os.getenv("TELEGRAM_TOKEN", "")
        chat_id_str = os.getenv("TELEGRAM_CHAT_ID", "0")
        chat_id = int(chat_id_str) if chat_id_str.isdigit() else 0
        self.tg = TelegramNotifier(token, chat_id)
        
        # rolling state per symbol (normalize to single sym key)
        self.last_price: dict[str, float] = {}
        self.price_window: dict[str, deque] = defaultdict(lambda: deque(maxlen=120))
        self.last_oi_val: dict[str, float] = {}
        self.features_cache: dict[str, dict] = {}
        self.in_position: set[str] = set()
        # trailing state managed via DB (best_low) and in-memory activation flags
        self._trail_active: set[str] = set()
        # latest per-exchange prices per symbol: {sym: {ex: (ts, price)}}
        self._ex_latest: dict[str, dict[str, tuple[float, float]]] = defaultdict(dict)
        
        # allowed symbols from load_symbols()
        self._allowed = set(load_symbols())

        # thresholds (env configurable)
        self.SCORE_MIN = int(os.getenv("SCORE_MIN", "60"))
        self.MAX_PRICE = float(os.getenv("MAX_PRICE", "5.0"))

        # anti-spam / cooldowns
        self.ENTRY_COOLDOWN_SEC = int(os.getenv("ENTRY_COOLDOWN_SEC", "300"))  # prevent multiple signals for same sym in short time
        self._last_entry_ts: dict[str, float] = {}

        # trailing configuration (percent values)
        self.TRAIL_ACTIVATE_PCT = float(os.getenv("TRAIL_ACTIVATE_PCT", "0.6"))  # activate after >=0.6% unrealized
        self.TRAIL_GIVEBACK_PCT = float(os.getenv("TRAIL_GIVEBACK_PCT", "0.4")) # exit if giveback from peak >=0.4%
        self.HARD_STOP_LOSS_PCT = float(os.getenv("HARD_STOP_LOSS_PCT", "1.2"))  # cut if loss >=1.2%

    def _update_ex_price(self, ex: str, sym: str, ts: float, price: float):
        self._ex_latest[sym][ex] = (ts, float(price))

    def _cross_ex_avg(self, sym: str, max_age_sec: int = 120) -> float | None:
        now = time.time()
        entries = self._ex_latest.get(sym, {})
        vals = [p for (t, p) in entries.values() if (now - t) <= max_age_sec and p > 0]
        if not vals:
            return None
        return sum(vals) / len(vals)

    async def _btc_loop(self):
        while True:
            try:
                await self.btc.poll()
            except Exception as e:
                logger.debug(f"BTC regime poll failed: {e}")
            await asyncio.sleep(30)

    def _compute_near_resistance(self, sym: str) -> float:
        win = self.price_window.get(sym)
        if not win or len(win) < 5:
            return 1.0
        last_ts, last_p = win[-1]
        cutoff = last_ts - 60
        highs = [p for ts, p in win if ts >= cutoff]
        if not highs:
            return 1.0
        mx = max(highs)
        if last_p <= 0:
            return 1.0
        return max(0.0, (mx - last_p) / last_p)

    def _recent_return(self, sym: str) -> float:
        win = self.price_window.get(sym)
        if not win or len(win) < 2:
            return 0.0
        p0 = win[-2][1]
        p1 = win[-1][1]
        if p0 <= 0:
            return 0.0
        return (p1 - p0) / p0

    def _dedup_hash(self, sym: str, price: float, score: float, feats: dict) -> str:
        keys = [
            "sweep_rejection", "liquidity_gap_above", "orderflow_imbalance",
            "volatility_burst", "short_momentum", "btc_not_pumping"
        ]
        snap = {k: round(float(feats.get(k, 0.0) or 0.0), 4) for k in keys}
        snap["sym"] = sym
        snap["price"] = round(float(price), 5)
        snap["score"] = int(score)
        s = json.dumps(snap, sort_keys=True)
        return hashlib.sha1(s.encode()).hexdigest()

    def _check_trailing(self, sym: str, price: float):
        pos = self.db.get_open_position(sym)
        if not pos:
            self._trail_active.discard(sym)
            return
        entry = float(pos["entry_price"])
        best_low = float(pos.get("best_low") or entry)
        should_exit, reason, pnl_pct, updated_best_low, trail_active = self.exit.trailing_for_short(entry, price, best_low)
        if updated_best_low != best_low:
            self.db.update_best_low(sym, updated_best_low)
        if trail_active:
            self._trail_active.add(sym)
        else:
            self._trail_active.discard(sym)
        if should_exit:
            self.db.close_position(sym, price, reason)
            if sym in self.in_position:
                self.in_position.discard(sym)
            self._trail_active.discard(sym)
            self.db.store_signal(sym, pnl_pct, price, f"exit_{reason}", time.time(), None, "exit")
            # Notify Telegram about exit (non-blocking)
            try:
                asyncio.create_task(self.tg.send_exit(sym, reason, price, pnl_pct))
            except Exception:
                pass
            logger.info(f"EXIT ({reason.upper()}): {sym} @ ${price:.6f} pnl={pnl_pct:.2f}%")

    async def _consume(self):
        while True:
            ev = await self.hub.queue.get()
            et = ev.get("type")
            if et != "unified":
                continue
            data = ev.get("data") or {}
            sym = data.get("symbol") or data.get("sym")
            if not sym or sym not in self._allowed:
                continue
            try:
                ts = float(data.get("timestamp") or time.time())
                price = data.get("price") or data.get("mark")
                price = float(price) if price is not None else None
                spread = data.get("spread")
                depth = data.get("depth") or {}
                bid_total = depth.get("bid_total")
                ask_total = depth.get("ask_total")
                funding_rate = data.get("funding")
                oi_val = data.get("oi")

                # Persist unified row
                try:
                    self.db.store_unified(data)
                except Exception:
                    pass

                # Update price state and trailing
                if price and price > 0:
                    self.last_price[sym] = float(price)
                    self.price_window[sym].append((ts, float(price)))
                    self.vol_idx[sym].ingest_mark(ts, float(price))
                    self._check_trailing(sym, float(price))

                # Build features from unified metrics
                feats_ms = self.ms.features_from_unified(price, spread, bid_total, ask_total)
                feats_ms["gap_above"] = self.liq.void_above_from_unified()
                base = self.features_cache.get(sym, {})
                base.update(feats_ms)

                # Funding impulse
                base["funding_impulse"] = self.funding.impulse(funding_rate)

                # OI divergence
                if oi_val is not None:
                    prev_oi = self.last_oi_val.get(sym)
                    div = self.oi.divergence(float(oi_val), prev_oi) if prev_oi is not None else 0.0
                    self.last_oi_val[sym] = float(oi_val)
                    base["oi_divergence"] = max(0.0, div)
                    base["oi_rising"] = div > 0

                # Decision pass
                last_p = self.last_price.get(sym)
                if last_p is None or last_p <= 0:
                    self.features_cache[sym] = base
                    continue

                eligible = self.selector.eligible({sym: last_p}, max_price=self.MAX_PRICE)
                if sym not in eligible:
                    self.features_cache[sym] = base
                    continue

                # No per-ex trades available in unified path; set sweep metric conservative
                base["sweep_rejection"] = 0.0

                burst = self.vol_idx[sym].burst(60)
                base["volatility_burst"] = burst

                r = self._recent_return(sym)
                short_mom = max(0.0, -r) / 0.003
                short_mom = max(0.0, min(1.0, short_mom))
                base["short_momentum"] = short_mom

                btc_pump = self.btc.alignment()
                base["btc_alignment"] = max(0.0, min(1.0, 1.0 - btc_pump))
                base["btc_not_pumping"] = btc_pump < 0.4

                base["price_falling"] = r < 0
                base["liquidity_gap_above"] = base.get("gap_above", 0.0)
                base["spread_not_collapsing"] = base.get("spread_pct", 0.0) > 0.00005
                base["near_resistance"] = self._compute_near_resistance(sym)

                # Normalized features for scorer
                base["liquidity_pressure"] = max(0.0, min(1.0, base.get("gap_above", 0.0) / 0.002))
                base["orderflow_imbalance"] = max(0.0, min(1.0, base.get("ask_dom", 0.5)))

                score = self.scorer.score(base)
                base["score"] = score
                self.features_cache[sym] = base

                # Store features and rank
                now_ts = time.time()
                self.db.store_features(sym, json.dumps(base), now_ts)
                try:
                    self.db.store_rank(sym, float(score), now_ts)
                except Exception:
                    pass

                # Entry check
                microstructure_dict = {k: v for k, v in base.items() if k in ["ask_dom", "bid_dom", "spread_pct"]}
                if self.entry.should_short(base, microstructure_dict, sym):
                    if sym not in self.in_position and score >= self.SCORE_MIN:
                        now_ts = time.time()
                        last_ts = self._last_entry_ts.get(sym, 0)
                        if (now_ts - last_ts) < self.ENTRY_COOLDOWN_SEC or self.db.seen_recent_symbol_signal(sym, self.ENTRY_COOLDOWN_SEC, 'entry'):
                            logger.info(f"COOLDOWN: skip entry for {sym} (cooldown {self.ENTRY_COOLDOWN_SEC}s)")
                            continue
                        dh = self._dedup_hash(sym, last_p, score, base)
                        if not self.db.seen_recent_signal(sym, dh, window_sec=900):
                            self.in_position.add(sym)
                            self.db.open_position(sym, float(last_p))
                            self.db.store_signal(sym, float(score), float(last_p), "entry", time.time(), dh, "entry")
                            self._last_entry_ts[sym] = now_ts
                            asyncio.create_task(self.tg.send_signal(sym, score, last_p, base))
                            logger.info(f"SHORT SIGNAL: {sym} @ ${last_p:.6f} score={score:.1f}")
                        else:
                            logger.info(f"DEDUP: skipped duplicate signal for {sym}")
            except Exception as e:
                logger.debug(f"Orchestrator consume error on unified {sym}: {e}")

    async def run(self):
        # Start hub (non-blocking now - just creates tasks)
        await self.hub.start()
        
        # Now gather all tasks: hub's WebSocket tasks + our pipeline tasks
        all_tasks = self.hub._tasks + [
            asyncio.create_task(self._btc_loop()),
            asyncio.create_task(self._consume()),
        ]
        await asyncio.gather(*all_tasks)
