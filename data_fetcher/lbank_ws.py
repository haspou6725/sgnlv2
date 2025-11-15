import asyncio, json, time
import websockets
from loguru import logger

class LBankWS:
    def __init__(self, symbols, on_ob, on_trade):
        self.symbols = [s.lower() for s in symbols]
        self.on_ob = on_ob
        self.on_trade = on_trade
        self._stop = False
        self._last_msg = {}

    async def run(self):
        # Try common LBank WS endpoints
        endpoints = [
            "wss://www.lbkex.net/ws/V3/",
            "wss://www.lbkex.net/ws/V3",
            "wss://www.lbkex.net/ws/V2/",
            "wss://www.lbank.com/ws/V3/",
        ]
        backoff = 1
        while not self._stop:
            try:
                ws = None
                last_err = None
                for url in endpoints:
                    try:
                        logger.debug(f"LBankWS connecting to {url}")
                        ws = await websockets.connect(url, ping_interval=15, ping_timeout=10)
                        break
                    except Exception as e:
                        last_err = e
                        logger.debug(f"LBankWS endpoint failed {url}: {e}")
                        continue
                if ws is None:
                    raise last_err or RuntimeError("LBankWS no endpoint available")
                async with ws:
                    for s in self.symbols:
                        # Try V3-style topics
                        try:
                            await ws.send(json.dumps({"action":"subscribe", "subscribe":"depth.depth20", "pair":s}))
                        except Exception:
                            pass
                        try:
                            await ws.send(json.dumps({"action":"subscribe", "subscribe":"trade.update", "pair":s}))
                        except Exception:
                            pass
                        # Try V2-style topics (depth/trade)
                        try:
                            await ws.send(json.dumps({
                                "action":"subscribe", "subscribe":"depth", "pair":s, "depth":20
                            }))
                        except Exception:
                            pass
                        try:
                            await ws.send(json.dumps({
                                "action":"subscribe", "subscribe":"trade", "pair":s
                            }))
                        except Exception:
                            pass
                    backoff = 1
                    async for msg in ws:
                        d = json.loads(msg)
                        sub = d.get("subscribe") or d.get("type") or ""
                        pair = (d.get("pair") or d.get("symbol") or "").lower()
                        ts_raw = d.get("TS")
                        try:
                            ts = float(ts_raw) / 1000.0 if ts_raw is not None else time.time()
                        except Exception:
                            ts = time.time()
                        if sub in ("depth.depth20", "depth", "depth.update"):
                            self._last_msg[f"ob:{pair}"] = ts
                            await self.on_ob("lbank", pair, d)
                        elif sub in ("trade.update", "trade"):
                            self._last_msg[f"tr:{pair}"] = ts
                            await self.on_trade("lbank", pair, d)
            except Exception as e:
                logger.warning(f"LBankWS reconnect in {backoff}s: {e}")
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
