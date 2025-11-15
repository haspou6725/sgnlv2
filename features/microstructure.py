from typing import Dict, List, Tuple
import time

def _parse_prices_sizes_from_payload(payload) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]:
    """
    Attempt to extract top-of-book price levels from various exchange payloads.
    Returns (bids, asks) as lists of (price, size).
    """
    bids: List[Tuple[float, float]] = []
    asks: List[Tuple[float, float]] = []
    if not payload:
        return bids, asks
    # Binance depthUpdate
    if isinstance(payload, dict) and payload.get("e") == "depthUpdate":
        for pr, sz in payload.get("b", []):
            bids.append((float(pr), float(sz)))
        for pr, sz in payload.get("a", []):
            asks.append((float(pr), float(sz)))
        return bids, asks
    # Bybit orderbook
    if isinstance(payload, dict) and payload.get("topic", "").startswith("orderbook."):
        data = payload.get("data") or {}
        for it in data.get("b", []) or data.get("bid", []):
            # bybit may send dicts with price/size
            if isinstance(it, dict):
                bids.append((float(it.get("price")), float(it.get("size"))))
            else:
                # [price, size]
                bids.append((float(it[0]), float(it[1])))
        for it in data.get("a", []) or data.get("ask", []):
            if isinstance(it, dict):
                asks.append((float(it.get("price")), float(it.get("size"))))
            else:
                asks.append((float(it[0]), float(it[1])))
        return bids, asks
    # MEXC depth
    if isinstance(payload, dict) and (payload.get("method") in ("rs.depth", "push.depth") or payload.get("channel") == "push.depth"):
        d = payload.get("data", {})
        for it in d.get("bids", []) or []:
            if isinstance(it, dict):
                bids.append((float(it.get("price")), float(it.get("size"))))
            else:
                try:
                    bids.append((float(it[0]), float(it[1])))
                except Exception:
                    continue
        for it in d.get("asks", []) or []:
            if isinstance(it, dict):
                asks.append((float(it.get("price")), float(it.get("size"))))
            else:
                try:
                    asks.append((float(it[0]), float(it[1])))
                except Exception:
                    continue
        return bids, asks
    # LBank depth
    if isinstance(payload, dict) and payload.get("subscribe") in ("depth.depth20", "depth"):
        d = payload.get("depth", {})
        for it in d.get("bids", []) or []:
            if isinstance(it, dict):
                bids.append((float(it.get("price")), float(it.get("size"))))
            else:
                try:
                    bids.append((float(it[0]), float(it[1])))
                except Exception:
                    continue
        for it in d.get("asks", []) or []:
            if isinstance(it, dict):
                asks.append((float(it.get("price")), float(it.get("size"))))
            else:
                try:
                    asks.append((float(it[0]), float(it[1])))
                except Exception:
                    continue
        return bids, asks
    return bids, asks


class Microstructure:
    def orderbook_features(self, ob_payload) -> Dict[str, float]:
        bids, asks = _parse_prices_sizes_from_payload(ob_payload)
        if not bids or not asks:
            return {"ask_dom": 0.0, "spread": 0.0, "gap_above": 0.0, "spread_pct": 0.0}
        # Compute spread and dominance
        best_bid = max(bids, key=lambda x: x[0])
        best_ask = min(asks, key=lambda x: x[0])
        spread = (best_ask[0] - best_bid[0]) / best_ask[0] if best_ask[0] > 0 else 0.0
        sum_b = sum(sz for _, sz in bids[:20])
        sum_a = sum(sz for _, sz in asks[:20])
        denom = (sum_b + sum_a) or 1.0
        ask_dom = sum_a / denom
        # Liquidity gap above: max relative gap between consecutive ask prices
        asks_sorted = sorted(asks[:20], key=lambda x: x[0])
        gaps = []
        for i in range(1, len(asks_sorted)):
            p0, _ = asks_sorted[i-1]
            p1, _ = asks_sorted[i]
            if p0 > 0:
                gaps.append((p1 - p0) / p0)
        gap_above = max(gaps) if gaps else 0.0
        return {"ask_dom": ask_dom, "spread": spread, "gap_above": gap_above, "spread_pct": spread}

    def features_from_unified(self, price: float | None, spread: float | None, bid_total: float | None, ask_total: float | None) -> Dict[str, float]:
        """Compute microstructure-like features from unified averaged metrics.
        - ask_dom: ask_total / (bid_total + ask_total)
        - spread_pct: spread / price
        - gap_above: not available without levels; approximate 0.0
        """
        denom = 0.0
        try:
            denom = float((bid_total or 0.0) + (ask_total or 0.0))
        except Exception:
            denom = 0.0
        ask_dom = float(ask_total or 0.0) / (denom if denom > 0 else 1.0)
        sp_pct = 0.0
        try:
            if spread and price and price > 0:
                sp_pct = float(spread) / float(price)
        except Exception:
            sp_pct = 0.0
        return {"ask_dom": max(0.0, min(1.0, ask_dom)), "spread_pct": max(0.0, sp_pct), "gap_above": 0.0}
