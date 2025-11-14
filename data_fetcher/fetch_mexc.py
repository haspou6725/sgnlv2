"""
MEXC Futures Data Fetcher
Fetches orderbook, funding, OI, and trades via REST
"""
import asyncio
import aiohttp
from typing import Dict, List, Optional
from loguru import logger
from datetime import datetime


class MEXCFetcher:
    """MEXC Futures data fetcher"""
    
    BASE_URL = "https://contract.mexc.com"
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def init_session(self):
        """Initialize HTTP session"""
        if not self.session:
            self.session = aiohttp.ClientSession()
            logger.info("MEXC session initialized")
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            logger.info("MEXC session closed")
    
    async def fetch_ticker(self, symbol: str) -> Optional[Dict]:
        """Fetch ticker data"""
        await self.init_session()
        try:
            url = f"{self.BASE_URL}/api/v1/contract/ticker"
            params = {"symbol": symbol.upper()}
            
            async with self.session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("success"):
                        ticker = data.get("data", {})
                        return {
                            "symbol": symbol,
                            "price": float(ticker.get("lastPrice", 0)),
                            "volume_24h": float(ticker.get("volume24", 0)),
                            "high_24h": float(ticker.get("high24Price", 0)),
                            "low_24h": float(ticker.get("low24Price", 0)),
                            "change_24h": float(ticker.get("riseFallRate", 0)),
                            "timestamp": datetime.now().timestamp()
                        }
        except Exception as e:
            logger.error(f"MEXC fetch_ticker error for {symbol}: {e}")
        return None
    
    async def fetch_orderbook(self, symbol: str, depth: int = 20) -> Optional[Dict]:
        """Fetch orderbook depth"""
        await self.init_session()
        try:
            url = f"{self.BASE_URL}/api/v1/contract/depth/{symbol}"
            
            async with self.session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("success"):
                        book = data.get("data", {})
                        return {
                            "symbol": symbol,
                            "bids": [[float(p), float(q)] for p, q in book.get("bids", [])[:depth]],
                            "asks": [[float(p), float(q)] for p, q in book.get("asks", [])[:depth]],
                            "timestamp": datetime.now().timestamp()
                        }
        except Exception as e:
            logger.error(f"MEXC fetch_orderbook error for {symbol}: {e}")
        return None
    
    async def fetch_trades(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Fetch recent trades"""
        await self.init_session()
        try:
            url = f"{self.BASE_URL}/api/v1/contract/deals/{symbol}"
            params = {"limit": min(limit, 100)}
            
            async with self.session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("success"):
                        trades = data.get("data", [])
                        return [{
                            "price": float(t.get("p", 0)),
                            "amount": float(t.get("v", 0)),
                            "side": "sell" if t.get("T") == 2 else "buy",
                            "timestamp": float(t.get("t", 0)) / 1000
                        } for t in trades]
        except Exception as e:
            logger.error(f"MEXC fetch_trades error for {symbol}: {e}")
        return []
    
    async def fetch_funding_rate(self, symbol: str) -> Optional[float]:
        """Fetch funding rate"""
        await self.init_session()
        try:
            url = f"{self.BASE_URL}/api/v1/contract/funding_rate/{symbol}"
            
            async with self.session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("success"):
                        return float(data.get("data", {}).get("fundingRate", 0))
        except Exception as e:
            logger.debug(f"MEXC funding rate not available for {symbol}: {e}")
        return 0.0
    
    async def fetch_open_interest(self, symbol: str) -> Optional[float]:
        """Fetch open interest"""
        await self.init_session()
        try:
            url = f"{self.BASE_URL}/api/v1/contract/detail"
            params = {"symbol": symbol.upper()}
            
            async with self.session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("success"):
                        return float(data.get("data", {}).get("holdVol", 0))
        except Exception as e:
            logger.debug(f"MEXC open interest not available for {symbol}: {e}")
        return 0.0
    
    async def get_tradable_symbols(self, max_price: float = 5.0) -> List[str]:
        """Get list of tradable perpetual contracts under specified price"""
        await self.init_session()
        try:
            url = f"{self.BASE_URL}/api/v1/contract/detail"
            
            async with self.session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("success"):
                        contracts = data.get("data", [])
                        symbols = [c.get("symbol") for c in contracts if c.get("symbol", "").endswith("_USDT")]
                        
                        # Filter by price
                        filtered = []
                        for symbol in symbols[:50]:
                            ticker = await self.fetch_ticker(symbol)
                            if ticker and ticker.get("price", 999) < max_price:
                                filtered.append(symbol)
                        
                        logger.info(f"MEXC: Found {len(filtered)} symbols under ${max_price}")
                        return filtered[:30]
        except Exception as e:
            logger.error(f"MEXC get_tradable_symbols error: {e}")
        return []
    
    async def fetch_unified_data(self, symbol: str) -> Dict:
        """Fetch all data for a symbol in unified format"""
        ticker = await self.fetch_ticker(symbol)
        orderbook = await self.fetch_orderbook(symbol)
        trades = await self.fetch_trades(symbol, limit=50)
        funding = await self.fetch_funding_rate(symbol)
        oi = await self.fetch_open_interest(symbol)
        
        return {
            "symbol": symbol,
            "exchange": "mexc",
            "price": ticker.get("price", 0) if ticker else 0,
            "volume_24h": ticker.get("volume_24h", 0) if ticker else 0,
            "orderbook": orderbook,
            "trades": trades,
            "funding_rate": funding,
            "open_interest": oi,
            "timestamp": datetime.now().timestamp()
        }
