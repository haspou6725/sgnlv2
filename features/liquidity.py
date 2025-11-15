"""
Liquidity Feature Extraction
Analyzes sell walls, buy walls, and liquidity pressure
"""
from typing import Dict, List
import numpy as np
from loguru import logger


class LiquidityAnalyzer:
    """Extract liquidity microstructure features"""
    
    def calculate_features(self, data: Dict) -> Dict:
        """
        Calculate liquidity features
        
        Returns:
        - sell_wall_pressure: strength of resistance above price
        - buy_wall_exhaustion: weakness of support below price
        - spread_risk: bid-ask spread as % of price
        """
        features = {}
        
        orderbook = data.get("orderbook")
        price = data.get("price", 0)
        
        if not orderbook or price == 0:
            return self._default_features()
        
        bids = orderbook.get("bids", [])
        asks = orderbook.get("asks", [])
        
        if not bids or not asks:
            return self._default_features()
        
        # 1. Sell Wall Pressure
        features["sell_wall_pressure"] = self._calculate_sell_wall_pressure(asks, price)
        
        # 2. Buy Wall Exhaustion
        features["buy_wall_exhaustion"] = self._calculate_buy_wall_exhaustion(bids, price)
        
        # 3. Spread Risk
        features["spread_risk"] = self._calculate_spread_risk(bids, asks, price)
        
        return features
    
    def _calculate_sell_wall_pressure(self, asks: List, current_price: float) -> float:
        """
        Calculate sell wall pressure (0-100)
        Higher = stronger resistance above price = better for short
        """
        try:
            if not asks or current_price == 0:
                return 50.0
            
            # Look for large orders (walls) in top 10 levels
            volumes = [float(q) for p, q in asks[:10]]
            
            if not volumes:
                return 50.0
            
            # Calculate concentration - check if volume is clustered (wall)
            max_vol = max(volumes)
            avg_vol = np.mean(volumes)
            
            if avg_vol == 0:
                return 50.0
            
            # Wall strength = how much larger the max is vs average
            concentration = (max_vol / avg_vol - 1) * 50  # Scale to 0-100
            concentration = max(0, min(100, concentration))
            
            return round(concentration, 2)
        except Exception as e:
            logger.error(f"Error calculating sell wall pressure: {e}")
            return 50.0
    
    def _calculate_buy_wall_exhaustion(self, bids: List, current_price: float) -> float:
        """
        Calculate buy wall exhaustion (0-100)
        Higher = weaker support = better for short
        """
        try:
            if not bids or current_price == 0:
                return 50.0
            
            # Analyze bid side liquidity distribution
            volumes = [float(q) for p, q in bids[:10]]
            
            if not volumes:
                return 50.0
            
            # Check if bids are thin/weak
            top_3 = np.mean(volumes[:3]) if len(volumes) >= 3 else 0
            next_7 = np.mean(volumes[3:10]) if len(volumes) >= 10 else 0
            
            if top_3 == 0:
                return 100.0
            
            # Exhaustion = top bids much larger than deeper ones (thin support)
            ratio = next_7 / top_3
            exhaustion = max(0, min(100, (1 - ratio) * 100))
            
            return round(exhaustion, 2)
        except Exception as e:
            logger.error(f"Error calculating buy wall exhaustion: {e}")
            return 50.0
    
    def _calculate_spread_risk(self, bids: List, asks: List, current_price: float) -> float:
        """
        Calculate spread risk as percentage of price
        Higher spread = higher risk
        """
        try:
            if not bids or not asks or current_price == 0:
                return 1.0
            
            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
            
            spread = best_ask - best_bid
            spread_pct = (spread / current_price) * 100
            
            return round(spread_pct, 4)
        except Exception as e:
            logger.error(f"Error calculating spread risk: {e}")
            return 1.0
    
    def _default_features(self) -> Dict:
        """Return default features when data is insufficient"""
        return {
            "sell_wall_pressure": 50.0,
            "buy_wall_exhaustion": 50.0,
            "spread_risk": 1.0
        }
