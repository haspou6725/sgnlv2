import asyncio
import time
from collections import deque
from data_fetcher.rest_client import RESTClient

class BTCRegime:
    def __init__(self, maxlen: int = 360):
        self.klines = deque(maxlen=maxlen)  # (ts, close)

    async def poll(self):
        """Fetch last 60 minutes of BTCUSDT 1m klines and update buffer."""
        rc = RESTClient("https://api.binance.com")
        data = await rc.get("/api/v3/klines", params={"symbol": "BTCUSDT", "interval": "1m", "limit": 60})
        await rc.close()
        now = time.time()
        self.klines.clear()
        for k in data:
            # [ openTime, open, high, low, close, volume, closeTime, ... ]
            ct = k[6] / 1000.0
            close = float(k[4])
            self.klines.append((ct, close))

    def alignment(self) -> float:
        if len(self.klines) < 5:
            return 0.0
        now = time.time()
        recent = [(t, c) for t, c in self.klines if abs(t - now) < 3900]
        if len(recent) < 5:
            return 0.0
        closes = [c for _, c in recent]
        # 5m trend vs 60m trend blend
        c60 = closes[-1]
        c5 = closes[-5]
        c60b = closes[0]
        r5 = (c60 - c5) / c5 if c5 > 0 else 0
        r60 = (c60 - c60b) / c60b if c60b > 0 else 0
        # For short entries, we prefer non-pump regime; map uptrend to higher alignment (worse for shorts)
        pump = max(r5, r60)
        # Convert to 0..1 where 1 = strong pump; cap at +3% per hour scale
        return max(0.0, min(1.0, pump / 0.03))
