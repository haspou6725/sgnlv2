import asyncio, json, time
import websockets
from loguru import logger

class BinanceWS:
    def __init__(self, symbols, on_ob, on_trade, on_mark):
        self.symbols = [s.lower() for s in symbols if s.endswith("USDT")]
        self.on_ob = on_ob
        self.on_trade = on_trade
        self.on_mark = on_mark
        self._stop = False
        self._last_msg = {}

    async def run(self):
        MAX_SYM_PER_CONN = 30
        tasks = []
        for i in range(0, len(self.symbols), MAX_SYM_PER_CONN):
            chunk = self.symbols[i:i+MAX_SYM_PER_CONN]
            tasks.append(asyncio.create_task(self._conn(chunk)))
        await asyncio.gather(*tasks)

    async def _conn(self, symbols_chunk):
        streams = []
        for s in symbols_chunk:
            streams += [f"{s}@depth20@100ms", f"{s}@aggTrade", f"{s}@markPrice@1s"]
        url = "wss://fstream.binance.com/stream?streams=" + "/".join(streams)
        backoff = 1
        while not self._stop:
            try:
                async with websockets.connect(url, ping_interval=15, ping_timeout=10) as ws:
                    backoff = 1
                    async for msg in ws:
                        data = json.loads(msg)
                        p = data.get("data", {})
                        st = p.get("e")
                        sym = p.get("s", "").upper()
                        ts = p.get("E", 0) / 1000.0 if p.get("E") else time.time()
                        if st == "depthUpdate":
                            self._last_msg[f"ob:{sym}"] = ts
                            await self.on_ob("binance", sym, p)
                        elif st == "aggTrade":
                            self._last_msg[f"tr:{sym}"] = ts
                            await self.on_trade("binance", sym, p)
                        elif st == "markPriceUpdate":
                            self._last_msg[f"mk:{sym}"] = ts
                            await self.on_mark("binance", sym, p)
            except Exception as e:
                logger.warning(f"BinanceWS reconnect in {backoff}s: {e}")
                await asyncio.sleep(backoff)
                backoff = min(30, backoff * 2)

    def stop(self):
        self._stop = True

    def staleness_check(self) -> dict:
        now = time.time()
        stale = {}
        for k, ts in self._last_msg.items():
            if now - ts > 60:
                stale[k] = now - ts
        return stale
