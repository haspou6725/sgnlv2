"""
SGNL-V2 Orchestrator
Main loop that coordinates all components
"""
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger

from data_fetcher.fetch_lbank import LBankFetcher
from data_fetcher.fetch_binance import BinanceFetcher
from data_fetcher.fetch_mexc import MEXCFetcher
from data_fetcher.fetch_bybit import BybitFetcher
from features.orderflow import OrderflowAnalyzer
from features.liquidity import LiquidityAnalyzer
from features.funding_oi import FundingOIAnalyzer
from features.volatility import VolatilityAnalyzer
from scalp_engine.scorer import ScalpScorer
from scalp_engine.entry_trigger import EntryTrigger
from scalp_engine.exit_manager import ExitManager
from storage.db import get_sqlite_cache, get_mysql_history
from telegram_bot.notifier import TelegramNotifier


class Orchestrator:
    """Main orchestrator for SGNL-V2 engine"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.running = False
        
        # Initialize fetchers
        self.fetchers = {
            "lbank": LBankFetcher(),
            "binance": BinanceFetcher(),
            "mexc": MEXCFetcher(),
            "bybit": BybitFetcher()
        }
        
        # Initialize feature analyzers
        self.orderflow = OrderflowAnalyzer()
        self.liquidity = LiquidityAnalyzer()
        self.funding_oi = FundingOIAnalyzer()
        self.volatility = VolatilityAnalyzer()
        
        # Initialize scalp engine
        self.scorer = ScalpScorer()
        self.entry_trigger = EntryTrigger(
            min_score=config.get("min_score_threshold", 72),
            min_ask_imbalance=config.get("min_ask_imbalance", 0.60),
            max_daily_signals=config.get("max_daily_trades", 8),
            cooldown_seconds=config.get("cooldown_seconds", 60)
        )
        self.exit_manager = ExitManager()
        
        # Initialize storage
        self.sqlite_cache = get_sqlite_cache()
        self.mysql_history = None  # Will be initialized async
        
        # Initialize notifier
        telegram_token = config.get("telegram_bot_token")
        telegram_chat = config.get("telegram_chat_id")
        self.notifier = TelegramNotifier(telegram_token, telegram_chat)
        
        # Symbol tracking
        self.active_symbols = []
        self.symbol_scores = {}
        
        logger.info("Orchestrator initialized")
    
    async def initialize(self):
        """Async initialization"""
        # Initialize MySQL
        mysql_config = self.config.get("mysql", {})
        if mysql_config.get("host"):
            from storage.db import get_mysql_history
            self.mysql_history = get_mysql_history(
                host=mysql_config.get("host"),
                port=mysql_config.get("port", 3306),
                user=mysql_config.get("user"),
                password=mysql_config.get("password"),
                database=mysql_config.get("database")
            )
            if self.mysql_history:
                await self.mysql_history.connect()
        
        # Test Telegram connection
        await self.notifier.test_connection()
        
        logger.info("Orchestrator async initialization complete")
    
    async def discover_symbols(self, max_price: float = 5.0):
        """Discover tradable symbols across all exchanges"""
        logger.info(f"Discovering symbols under ${max_price}...")
        
        all_symbols = []
        
        for exchange_name, fetcher in self.fetchers.items():
            try:
                symbols = await fetcher.get_tradable_symbols(max_price)
                for symbol in symbols:
                    all_symbols.append({
                        "symbol": symbol,
                        "exchange": exchange_name
                    })
                logger.info(f"{exchange_name}: {len(symbols)} symbols discovered")
            except Exception as e:
                logger.error(f"Failed to discover symbols from {exchange_name}: {e}")
        
        self.active_symbols = all_symbols[:50]  # Limit to 50 symbols total
        logger.info(f"Total active symbols: {len(self.active_symbols)}")
        
        return self.active_symbols
    
    async def process_symbol(self, symbol_info: Dict) -> Optional[Dict]:
        """Process a single symbol through the entire pipeline"""
        symbol = symbol_info["symbol"]
        exchange = symbol_info["exchange"]
        
        try:
            # 1. Fetch data
            fetcher = self.fetchers.get(exchange)
            if not fetcher:
                return None
            
            data = await fetcher.fetch_unified_data(symbol)
            
            if not data or data.get("price", 0) == 0:
                return None
            
            # 2. Extract features
            features = {}
            features.update(self.orderflow.calculate_features(data))
            features.update(self.liquidity.calculate_features(data))
            features.update(self.funding_oi.calculate_features(data))
            features.update(self.volatility.calculate_features(data))
            
            # 3. Calculate score
            score_data = self.scorer.calculate_score(features, data)
            score = score_data["score"]
            
            # Store in cache
            self.sqlite_cache.save_score(symbol, score, features)
            self.sqlite_cache.save_depth(
                symbol, exchange,
                data.get("orderbook", {}).get("bids", []),
                data.get("orderbook", {}).get("asks", [])
            )
            
            # Track for dashboard
            self.symbol_scores[symbol] = {
                "exchange": exchange,
                "score": score,
                "price": data.get("price"),
                "features": features,
                "timestamp": datetime.now().timestamp()
            }
            
            # 4. Check entry conditions
            should_enter, reason = self.entry_trigger.should_enter(score_data, features, data)
            
            if should_enter:
                signal = self.entry_trigger.generate_signal(
                    score_data, data,
                    tp_pct=self.config.get("tp_percent", 1.7),
                    sl_pct_min=self.config.get("sl_percent_min", 0.7),
                    sl_pct_max=self.config.get("sl_percent_max", 1.1)
                )
                
                if signal:
                    # Save to storage
                    self.sqlite_cache.save_signal(signal)
                    if self.mysql_history:
                        await self.mysql_history.save_signal(signal)
                    
                    # Send notification
                    await self.notifier.send_signal(signal)
                    
                    # Track position
                    self.exit_manager.add_position(signal)
                    
                    logger.success(f"✅ Signal generated: {symbol} @ {signal['entry']} | Score: {score:.1f}")
                    
                    return signal
            
            # 5. Check exits for active positions
            exit_signal = self.exit_manager.check_exits(data)
            if exit_signal:
                await self.notifier.send_exit(exit_signal)
                logger.info(f"Position exited: {symbol}")
            
            return None
            
        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}")
            return None
    
    async def main_loop(self):
        """Main processing loop"""
        logger.info("Starting main loop...")
        
        # Discover symbols on startup
        await self.discover_symbols(max_price=5.0)
        
        iteration = 0
        
        while self.running:
            try:
                iteration += 1
                logger.debug(f"Loop iteration {iteration}")
                
                # Process all symbols
                tasks = [self.process_symbol(s) for s in self.active_symbols]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Count signals
                signals_generated = sum([1 for r in results if r and not isinstance(r, Exception)])
                if signals_generated > 0:
                    logger.info(f"Generated {signals_generated} signals this iteration")
                
                # Wait before next iteration
                await asyncio.sleep(self.config.get("refresh_interval", 5))
                
                # Rediscover symbols periodically (every hour)
                if iteration % 720 == 0:  # 720 * 5s = 1 hour
                    await self.discover_symbols()
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(10)
    
    async def start(self):
        """Start the orchestrator"""
        self.running = True
        await self.initialize()
        
        # Send startup notification
        await self.notifier.send_health("online", f"SGNL-V2 started at {datetime.now().isoformat()}")
        
        logger.info("🚀 SGNL-V2 Engine started")
        await self.main_loop()
    
    async def stop(self):
        """Stop the orchestrator"""
        self.running = False
        
        # Close all fetcher sessions
        for fetcher in self.fetchers.values():
            await fetcher.close()
        
        # Close MySQL connection
        if self.mysql_history:
            await self.mysql_history.close()
        
        logger.info("Orchestrator stopped")
    
    def get_top_candidates(self, limit: int = 10) -> List[Dict]:
        """Get top scoring symbols"""
        sorted_symbols = sorted(
            self.symbol_scores.items(),
            key=lambda x: x[1]["score"],
            reverse=True
        )
        return [{"symbol": k, **v} for k, v in sorted_symbols[:limit]]
