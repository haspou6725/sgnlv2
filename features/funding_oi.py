"""
Funding Rate and Open Interest Analysis
Tracks funding impulse and OI divergence
"""
from typing import Dict, Optional
from collections import deque
from loguru import logger


class FundingOIAnalyzer:
    """Analyze funding rate and open interest for divergence signals"""
    
    def __init__(self, history_size: int = 10):
        self.funding_history = {}
        self.oi_history = {}
        self.price_history = {}
        self.history_size = history_size
    
    def calculate_features(self, data: Dict) -> Dict:
        """
        Calculate funding and OI features
        
        Returns:
        - funding_impulse: recent funding rate change
        - oi_divergence: OI rising while price falling (bearish)
        - funding_pressure: overall funding pressure score
        """
        features = {}
        
        symbol = data.get("symbol", "unknown")
        funding_rate = data.get("funding_rate", 0)
        open_interest = data.get("open_interest", 0)
        price = data.get("price", 0)
        
        # Initialize history for this symbol
        if symbol not in self.funding_history:
            self.funding_history[symbol] = deque(maxlen=self.history_size)
            self.oi_history[symbol] = deque(maxlen=self.history_size)
            self.price_history[symbol] = deque(maxlen=self.history_size)
        
        # Add current values to history
        self.funding_history[symbol].append(funding_rate)
        self.oi_history[symbol].append(open_interest)
        self.price_history[symbol].append(price)
        
        # 1. Funding Impulse
        features["funding_impulse"] = self._calculate_funding_impulse(symbol)
        
        # 2. OI Divergence
        features["oi_divergence"] = self._calculate_oi_divergence(symbol)
        
        # 3. Funding Pressure
        features["funding_pressure"] = self._calculate_funding_pressure(symbol)
        
        return features
    
    def _calculate_funding_impulse(self, symbol: str) -> float:
        """
        Calculate funding rate impulse (-100 to +100)
        Positive funding = longs paying shorts = bullish sentiment
        We want negative/neutral for shorts
        """
        try:
            history = list(self.funding_history[symbol])
            
            if len(history) < 2:
                return 0.0
            
            # Current vs average
            current = history[-1]
            avg = sum(history[:-1]) / len(history[:-1]) if len(history) > 1 else 0
            
            # Scale to -100 to +100
            # Positive funding is bearish for our short strategy
            impulse = (current - avg) * 10000  # Funding rates are small decimals
            impulse = max(-100, min(100, impulse))
            
            return round(impulse, 2)
        except Exception as e:
            logger.error(f"Error calculating funding impulse: {e}")
            return 0.0
    
    def _calculate_oi_divergence(self, symbol: str) -> float:
        """
        Calculate OI divergence score (0-100)
        High score = OI rising + price falling = bearish divergence
        """
        try:
            oi_hist = list(self.oi_history[symbol])
            price_hist = list(self.price_history[symbol])
            
            if len(oi_hist) < 3 or len(price_hist) < 3:
                return 0.0
            
            # Check if OI is rising
            oi_change = (oi_hist[-1] - oi_hist[0]) / oi_hist[0] if oi_hist[0] != 0 else 0
            
            # Check if price is falling
            price_change = (price_hist[-1] - price_hist[0]) / price_hist[0] if price_hist[0] != 0 else 0
            
            # Divergence: OI up + price down = bearish
            if oi_change > 0.02 and price_change < -0.01:  # 2% OI increase, 1% price decrease
                divergence_score = min(100, abs(oi_change) * 100 + abs(price_change) * 100)
                return round(divergence_score, 2)
            
            return 0.0
        except Exception as e:
            logger.error(f"Error calculating OI divergence: {e}")
            return 0.0
    
    def _calculate_funding_pressure(self, symbol: str) -> float:
        """
        Calculate overall funding pressure (0-100)
        High score = high positive funding = overleveraged longs = good for shorts
        """
        try:
            history = list(self.funding_history[symbol])
            
            if not history:
                return 0.0
            
            avg_funding = sum(history) / len(history)
            
            # Positive funding (longs paying shorts) is good for short strategy
            # Scale to 0-100
            pressure = avg_funding * 10000  # Funding rates are small decimals
            pressure = max(0, min(100, pressure * 2))  # Scale and cap
            
            return round(pressure, 2)
        except Exception as e:
            logger.error(f"Error calculating funding pressure: {e}")
            return 0.0
