from collections import deque
from typing import Deque, Tuple
import math
import time

class Volatility:
    def __init__(self, maxlen: int = 600):
        self.prices: Deque[Tuple[float, float]] = deque(maxlen=maxlen)  # (ts, price)

    def ingest_mark(self, ts: float, price: float):
        if price > 0 and abs(ts - time.time()) < 300:
            self.prices.append((ts, price))

    def burst(self, window_sec: int = 60) -> float:
        if len(self.prices) < 5:
            return 0.0
        now = self.prices[-1][0]
        wins = [p for t, p in self.prices if t >= now - window_sec]
        if len(wins) < 5:
            return 0.0
        rets = []
        for i in range(1, len(wins)):
            if wins[i-1] > 0:
                rets.append((wins[i] - wins[i-1]) / wins[i-1])
        if not rets:
            return 0.0
        mu = sum(rets) / len(rets)
        var = sum((r - mu) ** 2 for r in rets) / len(rets)
        vol = math.sqrt(var)
        # Normalize relative to a 0.2% baseline
        return max(0.0, min(1.0, vol / 0.002))
