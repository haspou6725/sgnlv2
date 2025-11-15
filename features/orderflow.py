"""
Orderflow Feature Extraction
Analyzes orderbook imbalances, sweep detection, and aggressive orders
"""
from typing import Dict, List, Optional
import numpy as np
from loguru import logger


class OrderflowAnalyzer:
    """Extract orderflow microstructure features"""
    
    def __init__(self):
        self.prev_trades = {}
    
    def calculate_features(self, data: Dict) -> Dict:
        """
        Calculate orderflow features from market data
        
        Returns dict with:
        - ask_dominance: % of liquidity on ask side
        - bid_weakness: % deterioration of bid side
        - orderbook_imbalance: bid-ask imbalance ratio
        - sweep_detected: large aggressive order detected
        - aggressive_sell_ratio: ratio of aggressive sells
        """
        features = {}
        
        orderbook = data.get("orderbook")
        trades = data.get("trades", [])
        
        if not orderbook:
            return self._default_features()
        
        # Extract orderbook data
        bids = orderbook.get("bids", [])
        asks = orderbook.get("asks", [])
        
        if not bids or not asks:
            return self._default_features()
        
        # 1. Ask Dominance
        features["ask_dominance"] = self._calculate_ask_dominance(bids, asks)
        
        # 2. Bid Weakness
        features["bid_weakness"] = self._calculate_bid_weakness(bids)
        
        # 3. Orderbook Imbalance (OBI)
        features["orderbook_imbalance"] = self._calculate_obi(bids, asks)
        
        # 4. Sweep Detection
        features["sweep_detected"] = self._detect_sweep(trades, orderbook)
        
        # 5. Aggressive Sell Ratio
        features["aggressive_sell_ratio"] = self._calculate_aggressive_sells(trades)
        
        # Store trades for next iteration
        symbol = data.get("symbol", "unknown")
        self.prev_trades[symbol] = trades
        
        return features
    
    def _calculate_ask_dominance(self, bids: List, asks: List) -> float:
        """Calculate ask side liquidity dominance (0-100%)"""
        try:
            # Sum top 10 levels
            bid_volume = sum([float(q) for p, q in bids[:10]])
            ask_volume = sum([float(q) for p, q in asks[:10]])
            
            total = bid_volume + ask_volume
            if total == 0:
                return 50.0
            
            ask_dominance = (ask_volume / total) * 100
            return round(ask_dominance, 2)
        except Exception as e:
            logger.error(f"Error calculating ask dominance: {e}")
            return 50.0
    
    def _calculate_bid_weakness(self, bids: List) -> float:
        """Calculate bid side weakness based on thin liquidity (0-100%)"""
        try:
            if len(bids) < 5:
                return 100.0
            
            # Compare top 5 vs next 5 levels
            top_5_vol = sum([float(q) for p, q in bids[:5]])
            next_5_vol = sum([float(q) for p, q in bids[5:10]]) if len(bids) >= 10 else 0
            
            if top_5_vol == 0:
                return 100.0
            
            ratio = next_5_vol / top_5_vol
            # Lower ratio = weaker bids = higher weakness score
            weakness = max(0, min(100, (1 - ratio) * 100))
            return round(weakness, 2)
        except Exception as e:
            logger.error(f"Error calculating bid weakness: {e}")
            return 50.0
    
    def _calculate_obi(self, bids: List, asks: List) -> float:
        """
        Calculate Orderbook Imbalance (OBI)
        Returns: -100 (bid heavy) to +100 (ask heavy)
        Positive = short signal
        """
        try:
            bid_volume = sum([float(q) for p, q in bids[:10]])
            ask_volume = sum([float(q) for p, q in asks[:10]])
            
            total = bid_volume + ask_volume
            if total == 0:
                return 0.0
            
            obi = ((ask_volume - bid_volume) / total) * 100
            return round(obi, 2)
        except Exception as e:
            logger.error(f"Error calculating OBI: {e}")
            return 0.0
    
    def _detect_sweep(self, trades: List, orderbook: Dict) -> bool:
        """
        Detect if a large sweep order occurred
        Sweep = large aggressive order that cleared multiple levels
        """
        try:
            if not trades or len(trades) < 5:
                return False
            
            # Look at last 10 trades
            recent = trades[:10]
            
            # Calculate average trade size
            avg_size = np.mean([float(t.get("amount", 0)) for t in recent])
            
            # Check if any recent trade is 3x+ average (sweep indicator)
            for trade in recent[:3]:
                size = float(trade.get("amount", 0))
                if size >= avg_size * 3:
                    return True
            
            return False
        except Exception as e:
            logger.error(f"Error detecting sweep: {e}")
            return False
    
    def _calculate_aggressive_sells(self, trades: List) -> float:
        """
        Calculate ratio of aggressive sell orders (0-100%)
        Higher = more selling pressure
        """
        try:
            if not trades:
                return 50.0
            
            recent = trades[:20]
            sell_count = sum([1 for t in recent if t.get("side") == "sell"])
            
            ratio = (sell_count / len(recent)) * 100
            return round(ratio, 2)
        except Exception as e:
            logger.error(f"Error calculating aggressive sells: {e}")
            return 50.0
    
    def _default_features(self) -> Dict:
        """Return default features when data is insufficient"""
        return {
            "ask_dominance": 50.0,
            "bid_weakness": 50.0,
            "orderbook_imbalance": 0.0,
            "sweep_detected": False,
            "aggressive_sell_ratio": 50.0
        }
