import asyncio, json, time
import websockets
from loguru import logger

class BybitWS:
    def __init__(self, symbols, on_ob, on_trade, on_liq):
        self.symbols = [s.upper() for s in symbols if s.endswith("USDT")]
        self.on_ob = on_ob
        self.on_trade = on_trade
        self.on_liq = on_liq
        self._stop = False
        self._last_msg = {}

    async def run(self):
        url = "wss://stream.bybit.com/v5/public/linear"
        backoff = 1
        while not self._stop:
            try:
                async with websockets.connect(url, ping_interval=20, ping_timeout=10) as ws:
                    for s in self.symbols:
                        await ws.send(json.dumps({"op":"subscribe","args":[f"orderbook.50.{s}", f"publicTrade.{s}", f"liquidation.{s}"]}))
                    backoff = 1
                    async for msg in ws:
                        data = json.loads(msg)
                        if data.get("op") == "pong":
                            continue
                        topic = data.get("topic", "")
                        ts = data.get("ts", 0) / 1000.0 if data.get("ts") else time.time()
                        if "orderbook" in topic:
                            sym = topic.split(".")[-1].upper()
                            self._last_msg[f"ob:{sym}"] = ts
                            await self.on_ob("bybit", sym, data)
                        elif "publicTrade" in topic:
                            sym = topic.split(".")[-1].upper()
                            self._last_msg[f"tr:{sym}"] = ts
                            await self.on_trade("bybit", sym, data)
                        elif "liquidation" in topic:
                            sym = topic.split(".")[-1].upper()
                            self._last_msg[f"liq:{sym}"] = ts
                            await self.on_liq("bybit", sym, data)
            except Exception as e:
                logger.warning(f"BybitWS reconnect in {backoff}s: {e}")
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
