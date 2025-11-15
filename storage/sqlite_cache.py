import sqlite3
import time
from data_fetcher.symbols import load_symbols

class SQLiteCache:
    def __init__(self, path: str):
        self.conn = sqlite3.connect(path, check_same_thread=False, timeout=10.0)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self._init_schema()
        self._allowed = set(load_symbols())
    
    def _init_schema(self):
        # Ticks table
        self.conn.execute("""CREATE TABLE IF NOT EXISTS ticks(
            ts REAL NOT NULL,
            ex TEXT NOT NULL,
            sym TEXT NOT NULL,
            price REAL NOT NULL
        )""")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_ticks_ts ON ticks(ts)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_ticks_sym ON ticks(sym)")
        
        # Features table
        self.conn.execute("""CREATE TABLE IF NOT EXISTS features(
            ts REAL NOT NULL,
            sym TEXT NOT NULL,
            data TEXT NOT NULL
        )""")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_features_sym ON features(sym)")
        
        # Signals table (extended with dedup_hash and type)
        self.conn.execute("""CREATE TABLE IF NOT EXISTS signals(
            ts REAL NOT NULL,
            sym TEXT NOT NULL,
            score REAL NOT NULL,
            entry_price REAL NOT NULL,
            reason TEXT,
            dedup_hash TEXT,
            signal_type TEXT DEFAULT 'entry'
        )""")
        # Add columns if upgrading existing DB
        try:
            self.conn.execute("ALTER TABLE signals ADD COLUMN dedup_hash TEXT")
        except Exception:
            pass
        try:
            self.conn.execute("ALTER TABLE signals ADD COLUMN signal_type TEXT DEFAULT 'entry'")
        except Exception:
            pass
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_signals_ts ON signals(ts)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_signals_sym_ts ON signals(sym, ts)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_signals_dedup ON signals(sym, dedup_hash)")

        # Positions table
        self.conn.execute("""CREATE TABLE IF NOT EXISTS positions(
            sym TEXT NOT NULL,
            entry_ts REAL NOT NULL,
            entry_price REAL NOT NULL,
            status TEXT NOT NULL,
            best_low REAL,
            exit_ts REAL,
            exit_price REAL,
            exit_reason TEXT,
            pnl_pct REAL
        )""")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_positions_sym ON positions(sym)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status)")

        # Ranks table
        self.conn.execute("""CREATE TABLE IF NOT EXISTS ranks(
            ts REAL NOT NULL,
            sym TEXT NOT NULL,
            score REAL NOT NULL
        )""")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_ranks_ts ON ranks(ts)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_ranks_sym ON ranks(sym)")
        
        # Unified averaged ticks table (one row per symbol per tick)
        self.conn.execute("""CREATE TABLE IF NOT EXISTS unified_ticks(
            ts REAL NOT NULL,
            sym TEXT NOT NULL,
            price REAL,
            mark REAL,
            funding REAL,
            oi REAL,
            spread REAL,
            volume REAL,
            bid_total REAL,
            ask_total REAL,
            imbalance REAL,
            UNIQUE(sym, ts)
        )""")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_unified_ts ON unified_ticks(ts)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_unified_sym ON unified_ticks(sym)")
        self.conn.commit()
    
    def _validate_symbol(self, sym: str) -> bool:
        return sym in self._allowed
    
    def _validate_timestamp(self, ts: float) -> bool:
        return abs(ts - time.time()) < 300
    
    def store_tick(self, ex: str, sym: str, price: float, ts: float = None):
        if ts is None:
            ts = time.time()
        if not self._validate_symbol(sym):
            return
        if not self._validate_timestamp(ts):
            return
        if not (isinstance(price, (int, float)) and price > 0):
            return
        self.conn.execute("INSERT INTO ticks VALUES (?,?,?,?)", (ts, ex, sym, price))
        self.conn.commit()
    
    def store_features(self, sym: str, data_json: str, ts: float = None):
        if ts is None:
            ts = time.time()
        if not self._validate_symbol(sym):
            return
        if not self._validate_timestamp(ts):
            return
        self.conn.execute("INSERT INTO features VALUES (?,?,?)", (ts, sym, data_json))
        self.conn.commit()

    def store_unified(self, unified: dict):
        """Store a single averaged row per symbol per tick, replacing if same (sym, ts)."""
        if not isinstance(unified, dict):
            return
        sym = unified.get("symbol") or unified.get("sym")
        ts = unified.get("timestamp") or unified.get("ts") or time.time()
        if not self._validate_symbol(sym):
            return
        if not self._validate_timestamp(float(ts)):
            return
        price = unified.get("price")
        mark = unified.get("mark")
        funding = unified.get("funding")
        oi = unified.get("oi")
        spread = unified.get("spread")
        volume = unified.get("volume")
        depth = unified.get("depth") or {}
        bid_total = depth.get("bid_total") if isinstance(depth, dict) else None
        ask_total = depth.get("ask_total") if isinstance(depth, dict) else None
        imbalance = depth.get("imbalance") if isinstance(depth, dict) else None
        self.conn.execute(
            "INSERT OR REPLACE INTO unified_ticks (ts, sym, price, mark, funding, oi, spread, volume, bid_total, ask_total, imbalance) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (float(ts), sym, _float_or_none(price), _float_or_none(mark), _float_or_none(funding), _float_or_none(oi), _float_or_none(spread), _float_or_none(volume), _float_or_none(bid_total), _float_or_none(ask_total), _float_or_none(imbalance)),
        )
        self.conn.commit()
    
    def store_signal(self, sym: str, score: float, entry_price: float, reason: str = "", ts: float = None, dedup_hash: str | None = None, signal_type: str = "entry"):
        if ts is None:
            ts = time.time()
        if not self._validate_symbol(sym):
            return
        self.conn.execute("INSERT INTO signals (ts, sym, score, entry_price, reason, dedup_hash, signal_type) VALUES (?,?,?,?,?,?,?)", (ts, sym, score, entry_price, reason, dedup_hash, signal_type))
        self.conn.commit()

    def seen_recent_signal(self, sym: str, dedup_hash: str, window_sec: int = 900) -> bool:
        cutoff = time.time() - window_sec
        row = self.conn.execute("SELECT 1 FROM signals WHERE sym=? AND dedup_hash=? AND ts>? LIMIT 1", (sym, dedup_hash, cutoff)).fetchone()
        return bool(row)

    def seen_recent_symbol_signal(self, sym: str, window_sec: int = 300, signal_type: str = 'entry') -> bool:
        """Return True if there is any signal for symbol within the cooldown window, optionally filtered by type."""
        cutoff = time.time() - window_sec
        if signal_type:
            row = self.conn.execute(
                "SELECT 1 FROM signals WHERE sym=? AND signal_type=? AND ts>? LIMIT 1",
                (sym, signal_type, cutoff),
            ).fetchone()
        else:
            row = self.conn.execute(
                "SELECT 1 FROM signals WHERE sym=? AND ts>? LIMIT 1",
                (sym, cutoff),
            ).fetchone()
        return bool(row)

    def open_position(self, sym: str, entry_price: float, entry_ts: float | None = None, best_low: float | None = None):
        if entry_ts is None:
            entry_ts = time.time()
        if not self._validate_symbol(sym):
            return
        self.conn.execute("INSERT INTO positions (sym, entry_ts, entry_price, status, best_low) VALUES (?,?,?,?,?)",
                          (sym, entry_ts, entry_price, 'OPEN', best_low if best_low is not None else entry_price))
        self.conn.commit()

    def close_position(self, sym: str, exit_price: float, reason: str, exit_ts: float | None = None):
        if exit_ts is None:
            exit_ts = time.time()
        row = self.conn.execute("SELECT entry_price FROM positions WHERE sym=? AND status='OPEN' ORDER BY entry_ts DESC LIMIT 1", (sym,)).fetchone()
        if not row:
            return
        entry_price = float(row[0])
        pnl_pct = ((entry_price - exit_price) / entry_price) * 100.0
        self.conn.execute("UPDATE positions SET status='CLOSED', exit_ts=?, exit_price=?, exit_reason=?, pnl_pct=? WHERE sym=? AND status='OPEN'",
                          (exit_ts, exit_price, reason, pnl_pct, sym))
        self.conn.commit()

    def update_best_low(self, sym: str, best_low: float):
        self.conn.execute("UPDATE positions SET best_low=? WHERE sym=? AND status='OPEN'", (best_low, sym))
        self.conn.commit()

    def get_open_position(self, sym: str):
        row = self.conn.execute("SELECT entry_ts, entry_price, best_low FROM positions WHERE sym=? AND status='OPEN' ORDER BY entry_ts DESC LIMIT 1", (sym,)).fetchone()
        if not row:
            return None
        return {"entry_ts": row[0], "entry_price": float(row[1]), "best_low": float(row[2]) if row[2] is not None else None}

    def store_rank(self, sym: str, score: float, ts: float | None = None):
        if ts is None:
            ts = time.time()
        if not self._validate_symbol(sym):
            return
        self.conn.execute("INSERT INTO ranks (ts, sym, score) VALUES (?,?,?)", (ts, sym, score))
        self.conn.commit()
    
    def latest_tick(self, sym: str) -> dict:
        if not self._validate_symbol(sym):
            return None
        row = self.conn.execute("SELECT ts, ex, price FROM ticks WHERE sym=? ORDER BY ts DESC LIMIT 1", (sym,)).fetchone()
        if not row:
            return None
        return {"ts": row[0], "ex": row[1], "sym": sym, "price": row[2]}

    def latest_unified(self, sym: str) -> dict | None:
        if not self._validate_symbol(sym):
            return None
        row = self.conn.execute("""
            SELECT ts, price, mark, funding, oi, spread, volume, bid_total, ask_total, imbalance
            FROM unified_ticks WHERE sym=? ORDER BY ts DESC LIMIT 1
        """, (sym,)).fetchone()
        if not row:
            return None
        ts, price, mark, funding, oi, spread, volume, bt, at, imb = row
        return {
            "timestamp": ts,
            "symbol": sym,
            "price": price,
            "mark": mark,
            "funding": funding,
            "oi": oi,
            "spread": spread,
            "volume": volume,
            "depth": {"bid_total": bt, "ask_total": at, "imbalance": imb},
        }

def _float_or_none(x):
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None
    
    def latest_price(self, sym: str) -> float:
        tick = self.latest_tick(sym)
        return tick["price"] if tick else None
    
    def latest_features(self, sym: str) -> str:
        if not self._validate_symbol(sym):
            return None
        row = self.conn.execute("SELECT data FROM features WHERE sym=? ORDER BY ts DESC LIMIT 1", (sym,)).fetchone()
        return row[0] if row else None
    
    def prune_old(self, days: int = 7):
        cutoff = time.time() - (days * 86400)
        self.conn.execute("DELETE FROM ticks WHERE ts < ?", (cutoff,))
        try:
            self.conn.execute("DELETE FROM unified_ticks WHERE ts < ?", (cutoff,))
        except Exception:
            pass
        self.conn.execute("DELETE FROM features WHERE ts < ?", (cutoff,))
        self.conn.commit()
    
    def close(self):
        self.conn.close()
