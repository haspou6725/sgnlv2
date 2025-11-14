"""
Exit Manager
Manages exit logic for active positions (TP/SL/Emergency)
"""
from typing import Dict, Optional, List
from datetime import datetime
from loguru import logger


class ExitManager:
    """Manages exits for short scalp positions"""
    
    def __init__(self):
        self.active_positions = {}  # symbol -> position data
        self.closed_positions = []
    
    def add_position(self, signal: Dict):
        """Add a new position to track"""
        symbol = signal.get("symbol")
        if not symbol:
            return
        
        position = {
            "symbol": symbol,
            "side": signal.get("side", "SHORT"),
            "entry": signal.get("entry"),
            "tp": signal.get("tp"),
            "sl": signal.get("sl"),
            "score": signal.get("score"),
            "entry_time": datetime.now(),
            "trailing_enabled": False,
            "highest_profit": 0
        }
        
        self.active_positions[symbol] = position
        logger.info(f"Position added: {symbol} SHORT @ {position['entry']}")
    
    def check_exits(self, market_data: Dict) -> Optional[Dict]:
        """
        Check if any positions should be exited
        
        Returns:
            Exit signal dict or None
        """
        symbol = market_data.get("symbol")
        current_price = market_data.get("price", 0)
        
        if symbol not in self.active_positions or current_price == 0:
            return None
        
        position = self.active_positions[symbol]
        entry = position["entry"]
        tp = position["tp"]
        sl = position["sl"]
        
        # Calculate current P&L %
        pnl_pct = ((entry - current_price) / entry) * 100  # SHORT: profit when price falls
        
        # Update highest profit for trailing
        if pnl_pct > position["highest_profit"]:
            position["highest_profit"] = pnl_pct
        
        # 1. Check Take Profit
        if current_price <= tp:
            return self._exit_position(symbol, current_price, "TP_HIT", pnl_pct)
        
        # 2. Check Stop Loss
        if current_price >= sl:
            return self._exit_position(symbol, current_price, "SL_HIT", pnl_pct)
        
        # 3. Check emergency exits
        emergency_reason = self._check_emergency_exit(market_data, position)
        if emergency_reason:
            return self._exit_position(symbol, current_price, emergency_reason, pnl_pct)
        
        # 4. Check trailing stop (optional)
        if position.get("trailing_enabled") and pnl_pct > 1.0:
            # If profit > 1% and price retraces 0.3%, exit
            if pnl_pct < position["highest_profit"] - 0.3:
                return self._exit_position(symbol, current_price, "TRAILING_STOP", pnl_pct)
        
        return None
    
    def _exit_position(self, symbol: str, exit_price: float, reason: str, pnl_pct: float) -> Dict:
        """Exit a position and return exit signal"""
        if symbol not in self.active_positions:
            return None
        
        position = self.active_positions.pop(symbol)
        
        exit_signal = {
            "symbol": symbol,
            "action": "EXIT",
            "reason": reason,
            "entry": position["entry"],
            "exit": exit_price,
            "pnl_pct": round(pnl_pct, 2),
            "entry_time": position["entry_time"].isoformat(),
            "exit_time": datetime.now().isoformat(),
            "duration_seconds": (datetime.now() - position["entry_time"]).total_seconds()
        }
        
        self.closed_positions.append(exit_signal)
        
        logger.info(f"Position exited: {symbol} @ {exit_price} | Reason: {reason} | P&L: {pnl_pct:.2f}%")
        
        return exit_signal
    
    def _check_emergency_exit(self, market_data: Dict, position: Dict) -> Optional[str]:
        """
        Check for emergency exit conditions
        
        Returns:
            Reason string or None
        """
        # 1. Check if BTC suddenly pumps (would need BTC data)
        # For now, skip this
        
        # 2. Check if liquidity pressure collapses
        features = market_data.get("features", {})
        if features:
            # If orderbook flips bullish suddenly
            obi = features.get("orderbook_imbalance", 0)
            if obi < -30:  # Bid-heavy = bullish
                return "LIQUIDITY_FLIP"
            
            # If sweep on bid side (bullish)
            sweep = features.get("sweep_detected", False)
            aggressive_sells = features.get("aggressive_sell_ratio", 50)
            if sweep and aggressive_sells < 30:  # More buys than sells
                return "BUY_SWEEP"
        
        # 3. Check for extended time without profit
        entry_time = position.get("entry_time")
        if entry_time:
            duration = (datetime.now() - entry_time).total_seconds()
            if duration > 3600:  # 1 hour without hitting TP
                return "TIMEOUT"
        
        return None
    
    def get_active_positions(self) -> List[Dict]:
        """Get all active positions"""
        return list(self.active_positions.values())
    
    def get_closed_positions(self, limit: int = 100) -> List[Dict]:
        """Get recent closed positions"""
        return self.closed_positions[-limit:]
    
    def enable_trailing(self, symbol: str):
        """Enable trailing stop for a position"""
        if symbol in self.active_positions:
            self.active_positions[symbol]["trailing_enabled"] = True
            logger.info(f"Trailing stop enabled for {symbol}")
