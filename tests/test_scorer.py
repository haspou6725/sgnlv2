"""
Tests for scoring engine
"""
import pytest
from scalp_engine.scorer import ScalpScorer


def test_scorer_initialization():
    """Test scorer initialization"""
    scorer = ScalpScorer()
    assert scorer is not None
    assert scorer.btc_trend == 0.0
    assert sum(scorer.WEIGHTS.values()) == 100  # Weights must sum to 100


def test_calculate_score_basic():
    """Test basic score calculation"""
    scorer = ScalpScorer()
    
    features = {
        "oi_divergence": 50,
        "sell_wall_pressure": 60,
        "buy_wall_exhaustion": 70,
        "orderbook_imbalance": 30,
        "sweep_detected": True,
        "micro_momentum": -10,
        "funding_pressure": 40,
        "ask_dominance": 65
    }
    
    data = {"price": 1.0}
    
    result = scorer.calculate_score(features, data)
    
    assert "score" in result
    assert "sub_scores" in result
    assert "reasons" in result
    assert 0 <= result["score"] <= 100


def test_score_with_perfect_features():
    """Test score with perfect bearish features"""
    scorer = ScalpScorer()
    
    features = {
        "oi_divergence": 100,
        "sell_wall_pressure": 100,
        "buy_wall_exhaustion": 100,
        "orderbook_imbalance": 100,
        "sweep_detected": True,
        "micro_momentum": -100,
        "funding_pressure": 100,
        "ask_dominance": 100
    }
    
    data = {"price": 1.0}
    
    result = scorer.calculate_score(features, data)
    
    # With perfect features, score should be very high
    assert result["score"] > 80


def test_score_with_weak_features():
    """Test score with weak features"""
    scorer = ScalpScorer()
    
    features = {
        "oi_divergence": 0,
        "sell_wall_pressure": 0,
        "buy_wall_exhaustion": 0,
        "orderbook_imbalance": -50,  # Bid-heavy (bullish)
        "sweep_detected": False,
        "micro_momentum": 50,  # Positive (bullish)
        "funding_pressure": 0,
        "ask_dominance": 30  # Bid-heavy
    }
    
    data = {"price": 1.0}
    
    result = scorer.calculate_score(features, data)
    
    # With weak features, score should be low
    assert result["score"] < 50


def test_btc_trend_update():
    """Test BTC trend update"""
    scorer = ScalpScorer()
    
    scorer.update_btc_trend(0.5)
    assert scorer.btc_trend == 0.5
    
    scorer.update_btc_trend(-0.8)
    assert scorer.btc_trend == -0.8
    
    # Test clamping
    scorer.update_btc_trend(2.0)
    assert scorer.btc_trend == 1.0
    
    scorer.update_btc_trend(-2.0)
    assert scorer.btc_trend == -1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
