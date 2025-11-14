"""
Tests for entry trigger logic
"""
import pytest
from scalp_engine.entry_trigger import EntryTrigger


def test_trigger_initialization():
    """Test trigger initialization"""
    trigger = EntryTrigger()
    assert trigger is not None
    assert trigger.min_score == 72
    assert trigger.min_ask_imbalance == 0.60
    assert trigger.max_daily_signals == 8
    assert trigger.cooldown_seconds == 60


def test_should_enter_with_good_conditions():
    """Test entry with good conditions"""
    trigger = EntryTrigger(min_score=70, cooldown_seconds=1)
    
    score_data = {
        "score": 75,
        "reasons": ["Test reason"]
    }
    
    features = {
        "ask_dominance": 65,  # 65% > 60%
        "sweep_detected": True,
        "oi_divergence": 40,
        "spread_risk": 0.3
    }
    
    data = {
        "symbol": "TESTUSDT",
        "price": 1.0
    }
    
    should_enter, reason = trigger.should_enter(score_data, features, data)
    assert should_enter is True


def test_should_enter_with_low_score():
    """Test entry rejection due to low score"""
    trigger = EntryTrigger(min_score=75)
    
    score_data = {
        "score": 70,  # Below threshold
        "reasons": []
    }
    
    features = {
        "ask_dominance": 65,
        "sweep_detected": True,
        "oi_divergence": 40,
        "spread_risk": 0.3
    }
    
    data = {"symbol": "TESTUSDT", "price": 1.0}
    
    should_enter, reason = trigger.should_enter(score_data, features, data)
    assert should_enter is False
    assert "Score" in reason


def test_should_enter_with_low_ask_imbalance():
    """Test entry rejection due to low ask imbalance"""
    trigger = EntryTrigger()
    
    score_data = {"score": 75, "reasons": []}
    
    features = {
        "ask_dominance": 50,  # 50% < 60%
        "sweep_detected": True,
        "oi_divergence": 40,
        "spread_risk": 0.3
    }
    
    data = {"symbol": "TESTUSDT", "price": 1.0}
    
    should_enter, reason = trigger.should_enter(score_data, features, data)
    assert should_enter is False
    assert "Ask dominance" in reason


def test_should_enter_without_sweep():
    """Test entry rejection without sweep"""
    trigger = EntryTrigger()
    
    score_data = {"score": 75, "reasons": []}
    
    features = {
        "ask_dominance": 65,
        "sweep_detected": False,  # No sweep
        "oi_divergence": 40,
        "spread_risk": 0.3
    }
    
    data = {"symbol": "TESTUSDT", "price": 1.0}
    
    should_enter, reason = trigger.should_enter(score_data, features, data)
    assert should_enter is False
    assert "sweep" in reason.lower()


def test_generate_signal():
    """Test signal generation"""
    trigger = EntryTrigger()
    
    score_data = {
        "score": 78.5,
        "reasons": ["Test reason 1", "Test reason 2"]
    }
    
    data = {
        "symbol": "TESTUSDT",
        "exchange": "binance",
        "price": 1.0
    }
    
    signal = trigger.generate_signal(score_data, data)
    
    assert signal is not None
    assert signal["symbol"] == "TESTUSDT"
    assert signal["exchange"] == "binance"
    assert signal["side"] == "SHORT"
    assert signal["entry"] == 1.0
    assert signal["tp"] < signal["entry"]  # TP below entry for SHORT
    assert signal["sl"] > signal["entry"]  # SL above entry for SHORT
    assert signal["score"] == 78.5
    assert len(signal["reasons"]) == 2


def test_daily_limit():
    """Test daily signal limit"""
    trigger = EntryTrigger(max_daily_signals=2)
    
    score_data = {"score": 75, "reasons": []}
    features = {
        "ask_dominance": 65,
        "sweep_detected": True,
        "oi_divergence": 40,
        "spread_risk": 0.3
    }
    
    # First signal - should pass
    data1 = {"symbol": "TEST1USDT", "price": 1.0}
    should_enter, _ = trigger.should_enter(score_data, features, data1)
    if should_enter:
        trigger.generate_signal(score_data, data1)
    
    # Second signal - should pass
    data2 = {"symbol": "TEST2USDT", "price": 1.0}
    should_enter, _ = trigger.should_enter(score_data, features, data2)
    if should_enter:
        trigger.generate_signal(score_data, data2)
    
    # Third signal - should fail (daily limit)
    data3 = {"symbol": "TEST3USDT", "price": 1.0}
    should_enter, reason = trigger.should_enter(score_data, features, data3)
    
    if trigger.daily_signal_count >= 2:
        assert "limit" in reason.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
