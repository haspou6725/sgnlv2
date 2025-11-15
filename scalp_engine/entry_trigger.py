"""
Entry Trigger Engine
Decides when to enter SHORT positions based on scoring and conditions
"""
from typing import Dict, Optional
from datetime import datetime
from loguru import logger


class EntryTrigger:
    """Manages entry logic for short scalp signals"""
    
    def __init__(self, 
                 min_score: float = 72,
                 min_ask_imbalance: float = 0.60,
                 max_daily_signals: int = 8,
                 cooldown_seconds: int = 60):
        self.min_score = min_score
        self.min_ask_imbalance = min_ask_imbalance
        self.max_daily_signals = max_daily_signals
        self.cooldown_seconds = cooldown_seconds
        
        # Track signals
        self.recent_signals = {}  # symbol -> last_signal_time
        self.daily_signal_count = 0
        self.last_reset = datetime.now().date()
    
    def should_enter(self, score_data: Dict, features: Dict, data: Dict) -> tuple[bool, str]:
        """
        Determine if entry conditions are met
        
        Returns:
            (should_enter: bool, reason: str)
        """
        symbol = data.get("symbol", "unknown")
        score = score_data.get("score", 0)
        
        # Reset daily counter if new day
        self._check_daily_reset()
        
        # 1. Check minimum score
        if score < self.min_score:
            return False, f"Score {score} below threshold {self.min_score}"
        
        # 2. Check ask imbalance
        ask_dominance = features.get("ask_dominance", 50) / 100
        if ask_dominance < self.min_ask_imbalance:
            return False, f"Ask dominance {ask_dominance:.2%} below {self.min_ask_imbalance:.2%}"
        
        # 3. Check sweep detection
        if not features.get("sweep_detected", False):
            return False, "No sweep detected"
        
        # 4. Check OI divergence
        oi_div = features.get("oi_divergence", 0)
        if oi_div < 30:
            return False, f"OI divergence {oi_div} too weak"
        
        # 5. Check BTC microtrend (if available)
        # For now, we'll skip this as BTC data needs separate fetching
        
        # 6. Check daily limit
        if self.daily_signal_count >= self.max_daily_signals:
            return False, f"Daily signal limit reached ({self.max_daily_signals})"
        
        # 7. Check cooldown
        if not self._check_cooldown(symbol):
            return False, f"Symbol in cooldown ({self.cooldown_seconds}s)"
        
        # 8. Check spread risk
        spread_risk = features.get("spread_risk", 1.0)
        if spread_risk > 0.5:  # 0.5% max spread
            return False, f"Spread too wide: {spread_risk:.4f}%"
        
        # All conditions met!
        return True, "All entry conditions satisfied"
    
    def generate_signal(self, score_data: Dict, data: Dict, tp_pct: float = 1.7, 
                       sl_pct_min: float = 0.7, sl_pct_max: float = 1.1) -> Optional[Dict]:
        """
        Generate a SHORT signal with entry, TP, and SL
        
        Args:
            score_data: Scoring data
            data: Market data
            tp_pct: Take profit percentage
            sl_pct_min: Minimum stop loss percentage
            sl_pct_max: Maximum stop loss percentage
        
        Returns:
            Signal dict or None
        """
        symbol = data.get("symbol", "unknown")
        exchange = data.get("exchange", "unknown")
        entry_price = data.get("price", 0)
        
        if entry_price == 0:
            logger.error(f"Invalid entry price for {symbol}")
            return None
        
        # Calculate TP and SL
        tp_price = entry_price * (1 - tp_pct / 100)  # SHORT: profit when price falls
        
        # Adjust SL based on volatility
        volatility = data.get("volatility", 0)
        if volatility > 2:  # High volatility
            sl_price = entry_price * (1 + sl_pct_max / 100)
        else:
            sl_price = entry_price * (1 + sl_pct_min / 100)
        
        signal = {
            "symbol": symbol,
            "exchange": exchange,
            "side": "SHORT",
            "entry": round(entry_price, 8),
            "tp": round(tp_price, 8),
            "sl": round(sl_price, 8),
            "score": score_data.get("score", 0),
            "reasons": score_data.get("reasons", []),
            "timestamp": datetime.now().timestamp(),
            "datetime": datetime.now().isoformat()
        }
        
        # Update tracking
        self.recent_signals[symbol] = datetime.now()
        self.daily_signal_count += 1
        
        logger.info(f"Signal generated: {symbol} SHORT @ {entry_price} | TP: {tp_price} | SL: {sl_price} | Score: {signal['score']}")
        
        return signal
    
    def _check_cooldown(self, symbol: str) -> bool:
        """Check if symbol is in cooldown period"""
        if symbol not in self.recent_signals:
            return True
        
        last_signal = self.recent_signals[symbol]
        elapsed = (datetime.now() - last_signal).total_seconds()
        
        return elapsed >= self.cooldown_seconds
    
    def _check_daily_reset(self):
        """Reset daily counter if new day"""
        today = datetime.now().date()
        if today != self.last_reset:
            self.daily_signal_count = 0
            self.last_reset = today
            logger.info("Daily signal counter reset")
