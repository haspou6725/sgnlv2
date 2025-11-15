"""
SGNL-V2 Scoring Engine
Combines features into UPS (Unified Prediction Score) 0-100
"""
from typing import Dict
from loguru import logger


class ScalpScorer:
    """Calculate unified prediction score for short scalp signals"""
    
    # Feature weights (must sum to 100)
    WEIGHTS = {
        "oi_divergence": 20,
        "liquidity_pressure": 20,
        "orderflow_imbalance": 15,
        "sweep": 15,
        "btc_microtrend": 10,
        "short_momentum": 10,
        "funding": 10
    }
    
    def __init__(self):
        self.btc_trend = 0.0  # -1 (down) to +1 (up)
    
    def calculate_score(self, features: Dict, data: Dict) -> Dict:
        """
        Calculate UPS (Unified Prediction Score) 0-100
        
        Args:
            features: Dict with all extracted features
            data: Market data
        
        Returns:
            Dict with score, sub-scores, and reasons
        """
        try:
            # Extract features
            oi_div = features.get("oi_divergence", 0)
            sell_wall = features.get("sell_wall_pressure", 50)
            buy_exhaustion = features.get("buy_wall_exhaustion", 50)
            obi = features.get("orderbook_imbalance", 0)
            sweep = features.get("sweep_detected", False)
            momentum = features.get("micro_momentum", 0)
            funding_pressure = features.get("funding_pressure", 0)
            ask_dominance = features.get("ask_dominance", 50)
            
            # Calculate sub-scores (0-100 each)
            sub_scores = {}
            
            # 1. OI Divergence Score (20 points)
            sub_scores["oi_divergence"] = min(100, oi_div)
            
            # 2. Liquidity Pressure Score (20 points)
            # Combination of sell walls and buy exhaustion
            liquidity_score = (sell_wall + buy_exhaustion) / 2
            sub_scores["liquidity_pressure"] = min(100, liquidity_score)
            
            # 3. Orderflow Imbalance Score (15 points)
            # Positive OBI = ask heavy = bearish
            obi_score = max(0, obi) if obi > 0 else 0
            obi_score += (ask_dominance - 50)  # Boost if asks dominate
            sub_scores["orderflow_imbalance"] = min(100, obi_score)
            
            # 4. Sweep Score (15 points)
            sub_scores["sweep"] = 100 if sweep else 0
            
            # 5. BTC Microtrend Score (10 points)
            # Negative trend is good for shorts
            btc_score = 50 + (-self.btc_trend * 50)
            sub_scores["btc_microtrend"] = max(0, min(100, btc_score))
            
            # 6. Short Momentum Score (10 points)
            # Negative momentum is good for shorts
            momentum_score = 50 + (-momentum / 2)
            sub_scores["short_momentum"] = max(0, min(100, momentum_score))
            
            # 7. Funding Score (10 points)
            # High positive funding = overleveraged longs = good for shorts
            sub_scores["funding"] = min(100, funding_pressure)
            
            # Calculate weighted total score
            total_score = 0
            for key, weight in self.WEIGHTS.items():
                score = sub_scores.get(key, 0)
                total_score += (score * weight / 100)
            
            # Generate reasons
            reasons = self._generate_reasons(sub_scores, features)
            
            return {
                "score": round(total_score, 2),
                "sub_scores": sub_scores,
                "reasons": reasons,
                "features": features
            }
            
        except Exception as e:
            logger.error(f"Error calculating score: {e}")
            return {
                "score": 0,
                "sub_scores": {},
                "reasons": ["Error in calculation"],
                "features": features
            }
    
    def _generate_reasons(self, sub_scores: Dict, features: Dict) -> list:
        """Generate human-readable reasons for the score"""
        reasons = []
        
        # OI Divergence
        if sub_scores.get("oi_divergence", 0) > 50:
            reasons.append("Strong OI divergence detected (OI rising, price falling)")
        
        # Liquidity
        if sub_scores.get("liquidity_pressure", 0) > 60:
            reasons.append("High liquidity pressure (sell walls + buy exhaustion)")
        
        # Orderflow
        if sub_scores.get("orderflow_imbalance", 0) > 50:
            reasons.append("Ask-heavy orderbook (bearish imbalance)")
        
        # Sweep
        if sub_scores.get("sweep", 0) == 100:
            reasons.append("Large sweep order detected")
        
        # BTC
        if sub_scores.get("btc_microtrend", 0) > 60:
            reasons.append("BTC microtrend favorable (not pumping)")
        
        # Momentum
        if sub_scores.get("short_momentum", 0) > 60:
            reasons.append("Negative price momentum")
        
        # Funding
        if sub_scores.get("funding", 0) > 50:
            reasons.append("Positive funding rate (longs overleveraged)")
        
        if not reasons:
            reasons.append("Weak signal - insufficient conviction")
        
        return reasons
    
    def update_btc_trend(self, trend: float):
        """Update BTC microtrend (-1 to +1)"""
        self.btc_trend = max(-1, min(1, trend))
