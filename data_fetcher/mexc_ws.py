import asyncio, json, time
import websockets
from loguru import logger

class MEXCWS:
    def __init__(self, symbols, on_ob, on_trade, on_mark):
        self.symbols = [s.upper() for s in symbols if s.endswith("USDT")]
        self.on_ob = on_ob
        self.on_trade = on_trade
        self.on_mark = on_mark
        self._stop = False
        self._last_msg = {}

    async def run(self):
        endpoints = [
            "wss://contract.mexc.com/ws",
            "wss://contract.mexc.com/edge",
        ]
        backoff = 1
        while not self._stop:
            try:
                # Try endpoints in order
                last_err = None
                ws = None
                for url in endpoints:
                    try:
                        logger.debug(f"MEXCWS connecting to {url}")
                        ws = await websockets.connect(url, ping_interval=20, ping_timeout=10)
                        break
                    except Exception as e:
                        last_err = e
                        logger.debug(f"MEXCWS endpoint failed {url}: {e}")
                        continue
                if ws is None:
                    raise last_err or RuntimeError("MEXCWS no endpoint available")
                async with ws:
                    for s in self.symbols:
                        sym_lower = s.replace("USDT", "_USDT")
                        await ws.send(json.dumps({"method":"sub.deal","param":{"symbol":sym_lower}}))
                        await ws.send(json.dumps({"method":"sub.depth","param":{"symbol":sym_lower}}))
                        await ws.send(json.dumps({"method":"sub.ticker","param":{"symbol":sym_lower}}))
                    backoff = 1
                    async for msg in ws:
                        data = json.loads(msg)
                        method = data.get("method", "")
                        ch = data.get("channel", "")
                        ts = data.get("ts", 0) / 1000.0 if data.get("ts") else time.time()
                        sym_raw = (data.get("symbol") or "").replace("_USDT", "USDT").upper()
                        if "deal" in method or "deal" in ch:
                            self._last_msg[f"tr:{sym_raw}"] = ts
                            await self.on_trade("mexc", sym_raw, data)
                        elif "depth" in method or "depth" in ch:
                            self._last_msg[f"ob:{sym_raw}"] = ts
                            await self.on_ob("mexc", sym_raw, data)
                        elif "ticker" in method or "ticker" in ch:
                            self._last_msg[f"mk:{sym_raw}"] = ts
                            await self.on_mark("mexc", sym_raw, data)
            except Exception as e:
                logger.warning(f"MEXCWS reconnect in {backoff}s: {e}")
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
