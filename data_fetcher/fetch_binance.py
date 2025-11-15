"""
Binance Futures Data Fetcher
Fetches orderbook, funding, OI, and trades via REST + WebSocket
"""
import aiohttp
from typing import Dict, List, Optional
from loguru import logger
from datetime import datetime


class BinanceFetcher:
    """Binance Futures data fetcher"""
    
    BASE_URL = "https://fapi.binance.com"
    WS_URL = "wss://fstream.binance.com/ws"
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.orderbooks: Dict[str, Dict] = {}
    
    async def init_session(self):
        """Initialize HTTP session"""
        if not self.session:
            self.session = aiohttp.ClientSession()
            logger.info("Binance session initialized")
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            logger.info("Binance session closed")
    
    async def fetch_ticker(self, symbol: str) -> Optional[Dict]:
        """Fetch ticker data"""
        await self.init_session()
        try:
            url = f"{self.BASE_URL}/fapi/v1/ticker/24hr"
            params = {"symbol": symbol.upper()}
            
            async with self.session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        "symbol": symbol,
                        "price": float(data.get("lastPrice", 0)),
                        "volume_24h": float(data.get("volume", 0)),
                        "high_24h": float(data.get("highPrice", 0)),
                        "low_24h": float(data.get("lowPrice", 0)),
                        "change_24h": float(data.get("priceChangePercent", 0)),
                        "timestamp": datetime.now().timestamp()
                    }
        except Exception as e:
            logger.error(f"Binance fetch_ticker error for {symbol}: {e}")
        return None
    
    async def fetch_orderbook(self, symbol: str, depth: int = 20) -> Optional[Dict]:
        """Fetch orderbook depth"""
        await self.init_session()
        try:
            url = f"{self.BASE_URL}/fapi/v1/depth"
            params = {"symbol": symbol.upper(), "limit": depth}
            
            async with self.session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        "symbol": symbol,
                        "bids": [[float(p), float(q)] for p, q in data.get("bids", [])[:depth]],
                        "asks": [[float(p), float(q)] for p, q in data.get("asks", [])[:depth]],
                        "timestamp": datetime.now().timestamp()
                    }
        except Exception as e:
            logger.error(f"Binance fetch_orderbook error for {symbol}: {e}")
        return None
    
    async def fetch_trades(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Fetch recent trades"""
        await self.init_session()
        try:
            url = f"{self.BASE_URL}/fapi/v1/trades"
            params = {"symbol": symbol.upper(), "limit": limit}
            
            async with self.session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return [{
                        "price": float(t.get("price", 0)),
                        "amount": float(t.get("qty", 0)),
                        "side": "sell" if t.get("isBuyerMaker") else "buy",
                        "timestamp": float(t.get("time", 0)) / 1000
                    } for t in data]
        except Exception as e:
            logger.error(f"Binance fetch_trades error for {symbol}: {e}")
        return []
    
    async def fetch_funding_rate(self, symbol: str) -> Optional[float]:
        """Fetch current funding rate"""
        await self.init_session()
        try:
            url = f"{self.BASE_URL}/fapi/v1/fundingRate"
            params = {"symbol": symbol.upper(), "limit": 1}
            
            async with self.session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data:
                        return float(data[0].get("fundingRate", 0))
        except Exception as e:
            logger.error(f"Binance fetch_funding_rate error for {symbol}: {e}")
        return 0.0
    
    async def fetch_open_interest(self, symbol: str) -> Optional[float]:
        """Fetch open interest"""
        await self.init_session()
        try:
            url = f"{self.BASE_URL}/fapi/v1/openInterest"
            params = {"symbol": symbol.upper()}
            
            async with self.session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return float(data.get("openInterest", 0))
        except Exception as e:
            logger.error(f"Binance fetch_open_interest error for {symbol}: {e}")
        return 0.0
    
    async def get_tradable_symbols(self, max_price: float = 5.0) -> List[str]:
        """Get list of tradable USDT futures under specified price"""
        await self.init_session()
        try:
            url = f"{self.BASE_URL}/fapi/v1/exchangeInfo"
            
            async with self.session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    symbols = []
                    
                    for symbol_info in data.get("symbols", []):
                        if (symbol_info.get("quoteAsset") == "USDT" and 
                            symbol_info.get("status") == "TRADING" and
                            symbol_info.get("contractType") == "PERPETUAL"):
                            symbols.append(symbol_info.get("symbol"))
                    
                    # Filter by price
                    filtered = []
                    for symbol in symbols[:50]:  # Limit API calls
                        ticker = await self.fetch_ticker(symbol)
                        if ticker and ticker.get("price", 999) < max_price:
                            filtered.append(symbol)
                    
                    logger.info(f"Binance: Found {len(filtered)} symbols under ${max_price}")
                    return filtered[:30]
        except Exception as e:
            logger.error(f"Binance get_tradable_symbols error: {e}")
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
            "exchange": "binance",
            "price": ticker.get("price", 0) if ticker else 0,
            "volume_24h": ticker.get("volume_24h", 0) if ticker else 0,
            "orderbook": orderbook,
            "trades": trades,
            "funding_rate": funding,
            "open_interest": oi,
            "timestamp": datetime.now().timestamp()
        }
