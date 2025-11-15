import time
from typing import List, Dict, Any

class Sweeps:
    def detect(self, trades: List[Dict[str, Any]], lookback_sec: int = 20) -> float:
        if not trades:
            return 0.0
        now = time.time()
        buy_vol = 0.0
        sell_vol = 0.0
        cnt = 0
        for tr in trades[-500:]:
            ts = tr.get("T") or tr.get("ts") or tr.get("time") or tr.get("E") or 0
            ts = float(ts) / 1000.0 if ts and ts > 1e12 else float(ts)
            if ts and ts < now - lookback_sec:
                continue
            qty = 0.0
            side = None
            # Binance aggTrade: p price q qty m is buyer is maker -> True means sell taker
            if tr.get("e") == "aggTrade":
                qty = float(tr.get("q", 0))
                side = "sell" if tr.get("m") else "buy"
            # Bybit publicTrade: data list with side and qty
            elif tr.get("topic", "").startswith("publicTrade."):
                for d in tr.get("data", []):
                    qty += float(d.get("v", 0))
                    side = d.get("S", "Buy").lower()
            # MEXC deal: data list with side
            elif tr.get("method") in ("rs.deal", "push.deal"):
                for d in tr.get("data", []):
                    qty += float(d.get("v", 0))
                    side = (d.get("T") or "buy").lower()
            # LBank trade.update
            elif tr.get("subscribe") == "trade.update":
                for d in tr.get("trades", []):
                    qty += float(d.get("amount", 0))
                    side = (d.get("type") or "buy").lower()

            cnt += 1
            if side and "sell" in side:
                sell_vol += qty
            else:
                buy_vol += qty
        total = buy_vol + sell_vol
        if total <= 0 or cnt < 3:
            return 0.0
        dom = max(buy_vol, sell_vol) / total
        # stronger sweep if dominance high and trade count reasonable
        return max(0.0, min(2.0, dom * (cnt / 20.0)))
