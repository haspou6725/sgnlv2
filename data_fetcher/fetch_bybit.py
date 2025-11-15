"""
Bybit Futures Data Fetcher
Fetches orderbook, funding, OI, and trades via REST
"""
import aiohttp
from typing import Dict, List, Optional
from loguru import logger
from datetime import datetime


class BybitFetcher:
    """Bybit Futures data fetcher"""
    
    BASE_URL = "https://api.bybit.com"
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def init_session(self):
        """Initialize HTTP session"""
        if not self.session:
            self.session = aiohttp.ClientSession()
            logger.info("Bybit session initialized")
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            logger.info("Bybit session closed")
    
    async def fetch_ticker(self, symbol: str) -> Optional[Dict]:
        """Fetch ticker data"""
        await self.init_session()
        try:
            url = f"{self.BASE_URL}/v5/market/tickers"
            params = {"category": "linear", "symbol": symbol.upper()}
            
            async with self.session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("retCode") == 0:
                        result = data.get("result", {})
                        tickers = result.get("list", [])
                        if tickers:
                            ticker = tickers[0]
                            return {
                                "symbol": symbol,
                                "price": float(ticker.get("lastPrice", 0)),
                                "volume_24h": float(ticker.get("volume24h", 0)),
                                "high_24h": float(ticker.get("highPrice24h", 0)),
                                "low_24h": float(ticker.get("lowPrice24h", 0)),
                                "change_24h": float(ticker.get("price24hPcnt", 0)) * 100,
                                "timestamp": datetime.now().timestamp()
                            }
        except Exception as e:
            logger.error(f"Bybit fetch_ticker error for {symbol}: {e}")
        return None
    
    async def fetch_orderbook(self, symbol: str, depth: int = 20) -> Optional[Dict]:
        """Fetch orderbook depth"""
        await self.init_session()
        try:
            url = f"{self.BASE_URL}/v5/market/orderbook"
            params = {"category": "linear", "symbol": symbol.upper(), "limit": min(depth, 50)}
            
            async with self.session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("retCode") == 0:
                        result = data.get("result", {})
                        return {
                            "symbol": symbol,
                            "bids": [[float(p), float(q)] for p, q in result.get("b", [])[:depth]],
                            "asks": [[float(p), float(q)] for p, q in result.get("a", [])[:depth]],
                            "timestamp": datetime.now().timestamp()
                        }
        except Exception as e:
            logger.error(f"Bybit fetch_orderbook error for {symbol}: {e}")
        return None
    
    async def fetch_trades(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Fetch recent trades"""
        await self.init_session()
        try:
            url = f"{self.BASE_URL}/v5/market/recent-trade"
            params = {"category": "linear", "symbol": symbol.upper(), "limit": min(limit, 1000)}
            
            async with self.session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("retCode") == 0:
                        result = data.get("result", {})
                        trades = result.get("list", [])
                        return [{
                            "price": float(t.get("price", 0)),
                            "amount": float(t.get("size", 0)),
                            "side": t.get("side", "").lower(),
                            "timestamp": float(t.get("time", 0)) / 1000
                        } for t in trades]
        except Exception as e:
            logger.error(f"Bybit fetch_trades error for {symbol}: {e}")
        return []
    
    async def fetch_funding_rate(self, symbol: str) -> Optional[float]:
        """Fetch current funding rate"""
        await self.init_session()
        try:
            url = f"{self.BASE_URL}/v5/market/funding/history"
            params = {"category": "linear", "symbol": symbol.upper(), "limit": 1}
            
            async with self.session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("retCode") == 0:
                        result = data.get("result", {})
                        funding_list = result.get("list", [])
                        if funding_list:
                            return float(funding_list[0].get("fundingRate", 0))
        except Exception as e:
            logger.error(f"Bybit fetch_funding_rate error for {symbol}: {e}")
        return 0.0
    
    async def fetch_open_interest(self, symbol: str) -> Optional[float]:
        """Fetch open interest"""
        await self.init_session()
        try:
            url = f"{self.BASE_URL}/v5/market/open-interest"
            params = {"category": "linear", "symbol": symbol.upper(), "intervalTime": "5min", "limit": 1}
            
            async with self.session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("retCode") == 0:
                        result = data.get("result", {})
                        oi_list = result.get("list", [])
                        if oi_list:
                            return float(oi_list[0].get("openInterest", 0))
        except Exception as e:
            logger.error(f"Bybit fetch_open_interest error for {symbol}: {e}")
        return 0.0
    
    async def get_tradable_symbols(self, max_price: float = 5.0) -> List[str]:
        """Get list of tradable perpetual USDT contracts under specified price"""
        await self.init_session()
        try:
            url = f"{self.BASE_URL}/v5/market/instruments-info"
            params = {"category": "linear"}
            
            async with self.session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("retCode") == 0:
                        result = data.get("result", {})
                        instruments = result.get("list", [])
                        symbols = [
                            i.get("symbol") for i in instruments 
                            if i.get("quoteCoin") == "USDT" and i.get("status") == "Trading"
                        ]
                        
                        # Filter by price
                        filtered = []
                        for symbol in symbols[:50]:
                            ticker = await self.fetch_ticker(symbol)
                            if ticker and ticker.get("price", 999) < max_price:
                                filtered.append(symbol)
                        
                        logger.info(f"Bybit: Found {len(filtered)} symbols under ${max_price}")
                        return filtered[:30]
        except Exception as e:
            logger.error(f"Bybit get_tradable_symbols error: {e}")
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
            "exchange": "bybit",
            "price": ticker.get("price", 0) if ticker else 0,
            "volume_24h": ticker.get("volume_24h", 0) if ticker else 0,
            "orderbook": orderbook,
            "trades": trades,
            "funding_rate": funding,
            "open_interest": oi,
            "timestamp": datetime.now().timestamp()
        }
