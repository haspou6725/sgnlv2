"""
Volatility and Momentum Analysis
Calculates VWAP distance, momentum, and spread metrics
"""
from typing import Dict, List
from collections import deque
import numpy as np
from loguru import logger


class VolatilityAnalyzer:
    """Analyze price volatility and momentum features"""
    
    def __init__(self, history_size: int = 50):
        self.price_history = {}
        self.volume_history = {}
        self.history_size = history_size
    
    def calculate_features(self, data: Dict) -> Dict:
        """
        Calculate volatility features
        
        Returns:
        - vwap_distance: % distance from VWAP
        - micro_momentum: 1m momentum score
        - price_velocity: rate of price change
        """
        features = {}
        
        symbol = data.get("symbol", "unknown")
        price = data.get("price", 0)
        volume = data.get("volume_24h", 0)
        trades = data.get("trades", [])
        
        # Initialize history
        if symbol not in self.price_history:
            self.price_history[symbol] = deque(maxlen=self.history_size)
            self.volume_history[symbol] = deque(maxlen=self.history_size)
        
        # Add current data
        self.price_history[symbol].append(price)
        self.volume_history[symbol].append(volume)
        
        # 1. VWAP Distance
        features["vwap_distance"] = self._calculate_vwap_distance(symbol, trades)
        
        # 2. Micro Momentum
        features["micro_momentum"] = self._calculate_micro_momentum(symbol)
        
        # 3. Price Velocity
        features["price_velocity"] = self._calculate_price_velocity(symbol)
        
        return features
    
    def _calculate_vwap_distance(self, symbol: str, trades: List) -> float:
        """
        Calculate distance from VWAP as percentage
        Positive = above VWAP (resistance), negative = below VWAP
        """
        try:
            if not trades:
                return 0.0
            
            # Calculate VWAP from recent trades
            total_pv = sum([float(t.get("price", 0)) * float(t.get("amount", 0)) for t in trades])
            total_v = sum([float(t.get("amount", 0)) for t in trades])
            
            if total_v == 0:
                return 0.0
            
            vwap = total_pv / total_v
            
            # Current price
            current_price = list(self.price_history[symbol])[-1] if self.price_history[symbol] else 0
            
            if current_price == 0:
                return 0.0
            
            # Distance as percentage
            distance = ((current_price - vwap) / vwap) * 100
            
            return round(distance, 4)
        except Exception as e:
            logger.error(f"Error calculating VWAP distance: {e}")
            return 0.0
    
    def _calculate_micro_momentum(self, symbol: str) -> float:
        """
        Calculate 1-minute momentum score (-100 to +100)
        Negative = falling = good for shorts
        """
        try:
            prices = list(self.price_history[symbol])
            
            if len(prices) < 2:
                return 0.0
            
            # Compare recent vs earlier
            recent_avg = np.mean(prices[-5:]) if len(prices) >= 5 else prices[-1]
            earlier_avg = np.mean(prices[-10:-5]) if len(prices) >= 10 else prices[0]
            
            if earlier_avg == 0:
                return 0.0
            
            momentum = ((recent_avg - earlier_avg) / earlier_avg) * 100
            momentum = max(-100, min(100, momentum * 10))  # Scale up
            
            return round(momentum, 2)
        except Exception as e:
            logger.error(f"Error calculating micro momentum: {e}")
            return 0.0
    
    def _calculate_price_velocity(self, symbol: str) -> float:
        """
        Calculate rate of price change (velocity)
        High velocity = rapid movement
        """
        try:
            prices = list(self.price_history[symbol])
            
            if len(prices) < 2:
                return 0.0
            
            # Calculate differences
            diffs = [prices[i] - prices[i-1] for i in range(1, len(prices))]
            
            if not diffs:
                return 0.0
            
            # Average absolute change
            avg_velocity = np.mean(np.abs(diffs))
            
            # Normalize by price
            if prices[-1] != 0:
                velocity_pct = (avg_velocity / prices[-1]) * 100
                return round(velocity_pct, 4)
            
            return 0.0
        except Exception as e:
            logger.error(f"Error calculating price velocity: {e}")
            return 0.0
