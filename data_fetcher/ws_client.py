"""
WebSocket Client Base for Exchange Connections
Handles reconnection, error handling, and message processing
"""
import asyncio
import json
from typing import Callable, Optional, Dict, Any
from loguru import logger
import websockets
from websockets.exceptions import ConnectionClosed


class WSClient:
    """Base WebSocket client with reconnection logic"""
    
    def __init__(self, url: str, on_message: Callable, ping_interval: int = 30):
        self.url = url
        self.on_message = on_message
        self.ping_interval = ping_interval
        self.ws = None
        self.running = False
        self.reconnect_delay = 5
        self.max_reconnect_delay = 60
    
    async def connect(self):
        """Establish WebSocket connection"""
        try:
            self.ws = await websockets.connect(
                self.url,
                ping_interval=self.ping_interval,
                ping_timeout=10
            )
            logger.info(f"WebSocket connected: {self.url}")
            return True
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            return False
    
    async def subscribe(self, subscription: Dict[str, Any]):
        """Send subscription message"""
        if self.ws:
            try:
                await self.ws.send(json.dumps(subscription))
                logger.debug(f"Subscribed: {subscription}")
            except Exception as e:
                logger.error(f"Subscription failed: {e}")
    
    async def start(self):
        """Start WebSocket client with auto-reconnect"""
        self.running = True
        while self.running:
            connected = await self.connect()
            if not connected:
                await asyncio.sleep(self.reconnect_delay)
                self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
                continue
            
            # Reset reconnect delay on successful connection
            self.reconnect_delay = 5
            
            try:
                await self._listen()
            except ConnectionClosed:
                logger.warning("WebSocket connection closed, reconnecting...")
                await asyncio.sleep(self.reconnect_delay)
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                await asyncio.sleep(self.reconnect_delay)
    
    async def _listen(self):
        """Listen for messages"""
        async for message in self.ws:
            try:
                data = json.loads(message)
                await self.on_message(data)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode message: {e}")
            except Exception as e:
                logger.error(f"Message handler error: {e}")
    
    async def stop(self):
        """Stop WebSocket client"""
        self.running = False
        if self.ws:
            await self.ws.close()
            logger.info("WebSocket closed")
    
    async def send(self, message: Dict[str, Any]):
        """Send message to WebSocket"""
        if self.ws:
            try:
                await self.ws.send(json.dumps(message))
            except Exception as e:
                logger.error(f"Failed to send message: {e}")


class OrderbookWSManager:
    """Manages multiple WebSocket connections for orderbook streams"""
    
    def __init__(self):
        self.clients: Dict[str, WSClient] = {}
        self.orderbooks: Dict[str, Dict[str, Any]] = {}
        self.callbacks: Dict[str, Callable] = {}
    
    def register_callback(self, exchange: str, callback: Callable):
        """Register callback for orderbook updates"""
        self.callbacks[exchange] = callback
    
    async def add_stream(self, exchange: str, url: str, symbols: list):
        """Add WebSocket stream for exchange"""
        async def on_message(data):
            # Process and store orderbook update
            await self._process_orderbook(exchange, data)
            
            # Call registered callback if exists
            if exchange in self.callbacks:
                await self.callbacks[exchange](data)
        
        client = WSClient(url, on_message)
        self.clients[exchange] = client
        
        # Start client
        asyncio.create_task(client.start())
        
        # Subscribe to symbols (exchange-specific logic needed)
        await asyncio.sleep(1)  # Wait for connection
        # Subscription will be handled by exchange-specific implementations
    
    async def _process_orderbook(self, exchange: str, data: Dict):
        """Process orderbook update (to be overridden by exchange-specific logic)"""
        pass
    
    def get_orderbook(self, exchange: str, symbol: str) -> Optional[Dict]:
        """Get latest orderbook for symbol"""
        key = f"{exchange}:{symbol}"
        return self.orderbooks.get(key)
    
    async def stop_all(self):
        """Stop all WebSocket clients"""
        for client in self.clients.values():
            await client.stop()
