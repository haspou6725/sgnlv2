"""
SGNL-V2 Database Layer
Handles SQLite caching and MySQL historical storage
"""
import os
import sqlite3
from typing import Dict, List
from datetime import datetime
import json
from loguru import logger
import aiomysql


class SQLiteCache:
    """Local SQLite cache for real-time data"""
    
    def __init__(self, db_path: str = "storage/sqlite_cache.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Last depth snapshot
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS last_depth (
                    symbol TEXT PRIMARY KEY,
                    exchange TEXT,
                    timestamp REAL,
                    bids TEXT,
                    asks TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Last scores
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS last_scores (
                    symbol TEXT PRIMARY KEY,
                    score REAL,
                    features TEXT,
                    timestamp REAL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Recent signals (cache)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS last_signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT,
                    entry REAL,
                    tp REAL,
                    sl REAL,
                    score REAL,
                    exchange TEXT,
                    timestamp REAL,
                    reasons TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
        logger.info(f"SQLite cache initialized at {self.db_path}")
    
    def save_depth(self, symbol: str, exchange: str, bids: List, asks: List):
        """Save orderbook depth snapshot"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO last_depth (symbol, exchange, timestamp, bids, asks, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                symbol,
                exchange,
                datetime.now().timestamp(),
                json.dumps(bids),
                json.dumps(asks),
                datetime.now()
            ))
            
            conn.commit()
    
    def save_score(self, symbol: str, score: float, features: Dict):
        """Save scoring data"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO last_scores (symbol, score, features, timestamp, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                symbol,
                score,
                json.dumps(features),
                datetime.now().timestamp(),
                datetime.now()
            ))
            
            conn.commit()
    
    def save_signal(self, signal: Dict):
        """Save signal to cache"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO last_signals (symbol, entry, tp, sl, score, exchange, timestamp, reasons)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                signal['symbol'],
                signal['entry'],
                signal['tp'],
                signal['sl'],
                signal['score'],
                signal['exchange'],
                datetime.now().timestamp(),
                json.dumps(signal.get('reasons', []))
            ))
            
            conn.commit()
    
    def get_last_signals(self, limit: int = 10) -> List[Dict]:
        """Retrieve recent signals"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM last_signals
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            
            rows = cursor.fetchall()
        
        return [dict(row) for row in rows]
    
    def get_scores(self) -> List[Dict]:
        """Get all cached scores"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM last_scores ORDER BY score DESC")
            rows = cursor.fetchall()
        
        return [dict(row) for row in rows]


class MySQLHistory:
    """MySQL storage for historical signals"""
    
    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.pool = None
    
    async def connect(self):
        """Initialize connection pool"""
        try:
            self.pool = await aiomysql.create_pool(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                db=self.database,
                minsize=1,
                maxsize=10,
                autocommit=True
            )
            logger.info(f"MySQL connection pool created for {self.database}")
            await self._init_tables()
        except Exception as e:
            logger.error(f"Failed to connect to MySQL: {e}")
            # Don't fail - app can run without MySQL
    
    async def _init_tables(self):
        """Initialize MySQL tables"""
        if not self.pool:
            return
        
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS signals_history (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        symbol VARCHAR(20) NOT NULL,
                        entry DECIMAL(20, 8) NOT NULL,
                        tp DECIMAL(20, 8) NOT NULL,
                        sl DECIMAL(20, 8) NOT NULL,
                        score DECIMAL(5, 2) NOT NULL,
                        exchange VARCHAR(20) NOT NULL,
                        reasons JSON,
                        INDEX idx_timestamp (timestamp),
                        INDEX idx_symbol (symbol),
                        INDEX idx_score (score)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
                logger.info("MySQL tables initialized")
    
    async def save_signal(self, signal: Dict):
        """Save signal to MySQL history"""
        if not self.pool:
            logger.warning("MySQL pool not available, skipping history save")
            return
        
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("""
                        INSERT INTO signals_history (symbol, entry, tp, sl, score, exchange, reasons)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        signal['symbol'],
                        signal['entry'],
                        signal['tp'],
                        signal['sl'],
                        signal['score'],
                        signal['exchange'],
                        json.dumps(signal.get('reasons', []))
                    ))
                    logger.debug(f"Signal saved to MySQL: {signal['symbol']}")
        except Exception as e:
            logger.error(f"Failed to save signal to MySQL: {e}")
    
    async def get_recent_signals(self, hours: int = 24, limit: int = 100) -> List[Dict]:
        """Retrieve recent signals from history"""
        if not self.pool:
            return []
        
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute("""
                        SELECT * FROM signals_history
                        WHERE timestamp >= DATE_SUB(NOW(), INTERVAL %s HOUR)
                        ORDER BY timestamp DESC
                        LIMIT %s
                    """, (hours, limit))
                    return await cursor.fetchall()
        except Exception as e:
            logger.error(f"Failed to fetch signals from MySQL: {e}")
            return []
    
    async def close(self):
        """Close connection pool"""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            logger.info("MySQL connection pool closed")


# Singleton instances
_sqlite_cache = None
_mysql_history = None


def get_sqlite_cache() -> SQLiteCache:
    """Get SQLite cache instance"""
    global _sqlite_cache
    if _sqlite_cache is None:
        _sqlite_cache = SQLiteCache()
    return _sqlite_cache


def get_mysql_history(host: str = None, port: int = None, user: str = None, 
                      password: str = None, database: str = None) -> MySQLHistory:
    """Get MySQL history instance"""
    global _mysql_history
    if _mysql_history is None and all([host, port, user, password, database]):
        _mysql_history = MySQLHistory(host, port, user, password, database)
    return _mysql_history
