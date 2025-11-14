"""
LBank Exchange Data Fetcher
Fetches orderbook, funding, OI, and trades via REST + WebSocket
"""
import asyncio
import aiohttp
from typing import Dict, List, Optional
from loguru import logger
from datetime import datetime


class LBankFetcher:
    """LBank Futures data fetcher"""
    
    BASE_URL = "https://www.lbkex.net"
    WS_URL = "wss://www.lbkex.net/ws/V2/"
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.orderbooks: Dict[str, Dict] = {}
    
    async def init_session(self):
        """Initialize HTTP session"""
        if not self.session:
            self.session = aiohttp.ClientSession()
            logger.info("LBank session initialized")
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            logger.info("LBank session closed")
    
    async def fetch_ticker(self, symbol: str) -> Optional[Dict]:
        """Fetch ticker data (price, volume, etc.)"""
        await self.init_session()
        try:
            url = f"{self.BASE_URL}/v2/ticker/24hr.do"
            params = {"symbol": symbol.lower()}
            
            async with self.session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("result") == "true":
                        ticker = data.get("data", [{}])[0] if data.get("data") else {}
                        return {
                            "symbol": symbol,
                            "price": float(ticker.get("latest", 0)),
                            "volume_24h": float(ticker.get("vol", 0)),
                            "high_24h": float(ticker.get("high", 0)),
                            "low_24h": float(ticker.get("low", 0)),
                            "change_24h": float(ticker.get("change", 0)),
                            "timestamp": datetime.now().timestamp()
                        }
        except Exception as e:
            logger.error(f"LBank fetch_ticker error for {symbol}: {e}")
        return None
    
    async def fetch_orderbook(self, symbol: str, depth: int = 20) -> Optional[Dict]:
        """Fetch orderbook depth"""
        await self.init_session()
        try:
            url = f"{self.BASE_URL}/v2/depth.do"
            params = {"symbol": symbol.lower(), "size": depth}
            
            async with self.session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("result") == "true":
                        book = data.get("data", {})
                        return {
                            "symbol": symbol,
                            "bids": [[float(p), float(q)] for p, q in book.get("bids", [])[:depth]],
                            "asks": [[float(p), float(q)] for p, q in book.get("asks", [])[:depth]],
                            "timestamp": datetime.now().timestamp()
                        }
        except Exception as e:
            logger.error(f"LBank fetch_orderbook error for {symbol}: {e}")
        return None
    
    async def fetch_trades(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Fetch recent trades"""
        await self.init_session()
        try:
            url = f"{self.BASE_URL}/v2/trades.do"
            params = {"symbol": symbol.lower(), "size": limit}
            
            async with self.session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("result") == "true":
                        trades = data.get("data", [])
                        return [{
                            "price": float(t.get("price", 0)),
                            "amount": float(t.get("amount", 0)),
                            "side": t.get("type"),  # buy/sell
                            "timestamp": float(t.get("date_ms", 0)) / 1000
                        } for t in trades]
        except Exception as e:
            logger.error(f"LBank fetch_trades error for {symbol}: {e}")
        return []
    
    async def fetch_funding_rate(self, symbol: str) -> Optional[float]:
        """
        Fetch funding rate for futures
        Note: LBank API may vary - adjust endpoint as needed
        """
        await self.init_session()
        try:
            # This is a placeholder - actual LBank futures API may differ
            # Check LBank documentation for correct endpoint
            url = f"{self.BASE_URL}/v2/supplement/funding_rate.do"
            params = {"symbol": symbol.lower()}
            
            async with self.session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Parse funding rate from response
                    # Structure depends on actual API
                    return data.get("funding_rate", 0.0)
        except Exception as e:
            logger.debug(f"LBank funding rate not available for {symbol}: {e}")
        return 0.0  # Default if not available
    
    async def fetch_open_interest(self, symbol: str) -> Optional[float]:
        """
        Fetch open interest for futures
        Note: LBank API may vary - adjust endpoint as needed
        """
        await self.init_session()
        try:
            # Placeholder - check LBank docs for actual endpoint
            url = f"{self.BASE_URL}/v2/supplement/open_interest.do"
            params = {"symbol": symbol.lower()}
            
            async with self.session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("open_interest", 0.0)
        except Exception as e:
            logger.debug(f"LBank open interest not available for {symbol}: {e}")
        return 0.0  # Default if not available
    
    async def get_tradable_symbols(self, max_price: float = 5.0) -> List[str]:
        """Get list of tradable symbols under specified price"""
        await self.init_session()
        try:
            url = f"{self.BASE_URL}/v2/currencyPairs.do"
            
            async with self.session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("result") == "true":
                        pairs = data.get("data", [])
                        symbols = [p for p in pairs if p.endswith("_usdt")]
                        
                        # Filter by price
                        filtered = []
                        for symbol in symbols[:50]:  # Limit API calls
                            ticker = await self.fetch_ticker(symbol)
                            if ticker and ticker.get("price", 999) < max_price:
                                filtered.append(symbol)
                        
                        logger.info(f"LBank: Found {len(filtered)} symbols under ${max_price}")
                        return filtered[:30]  # Limit to 30 symbols
        except Exception as e:
            logger.error(f"LBank get_tradable_symbols error: {e}")
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
            "exchange": "lbank",
            "price": ticker.get("price", 0) if ticker else 0,
            "volume_24h": ticker.get("volume_24h", 0) if ticker else 0,
            "orderbook": orderbook,
            "trades": trades,
            "funding_rate": funding,
            "open_interest": oi,
            "timestamp": datetime.now().timestamp()
        }
