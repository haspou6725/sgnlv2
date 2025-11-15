from typing import List, Tuple

def _asks_from_payload(payload) -> List[Tuple[float, float]]:
    if not payload:
        return []
    if isinstance(payload, dict) and payload.get("e") == "depthUpdate":
        out = []
        for it in payload.get("a", []) or []:
            try:
                out.append((float(it[0]), float(it[1])))
            except Exception:
                continue
        return out
    if isinstance(payload, dict) and payload.get("topic", "").startswith("orderbook."):
        asks = []
        data = payload.get("data") or {}
        for it in data.get("a", []) or data.get("ask", []):
            if isinstance(it, dict):
                asks.append((float(it.get("price")), float(it.get("size"))))
            else:
                asks.append((float(it[0]), float(it[1])))
        return asks
    if isinstance(payload, dict) and (payload.get("method") in ("rs.depth", "push.depth") or payload.get("channel") == "push.depth"):
        d = payload.get("data", {})
        out = []
        for it in d.get("asks", []) or []:
            if isinstance(it, dict):
                out.append((float(it.get("price")), float(it.get("size"))))
            else:
                try:
                    out.append((float(it[0]), float(it[1])))
                except Exception:
                    continue
        return out
    if isinstance(payload, dict) and payload.get("subscribe") in ("depth.depth20", "depth"):
        d = payload.get("depth", {})
        out = []
        for it in d.get("asks", []) or []:
            if isinstance(it, dict):
                out.append((float(it.get("price")), float(it.get("size"))))
            else:
                try:
                    out.append((float(it[0]), float(it[1])))
                except Exception:
                    continue
        return out
    return []

class Liquidity:
    def void_above(self, ob_payload) -> float:
        from .microstructure import _parse_prices_sizes_from_payload
        _, asks = _parse_prices_sizes_from_payload(ob_payload)
        if len(asks) < 2:
            return 0.0
        asks_sorted = sorted(asks, key=lambda x: x[0])
        gaps = []
        for i in range(1, min(20, len(asks_sorted))):
            p0, _ = asks_sorted[i-1]
            p1, _ = asks_sorted[i]
            if p0 > 0:
                gaps.append((p1 - p0) / p0)
        return max(gaps) if gaps else 0.0

    def void_above_from_unified(self) -> float:
        """Unified metrics lack price ladder; return 0.0 as conservative default."""
        return 0.0
