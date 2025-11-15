import os


class ExitManager:
    TP_PCT = 1.7
    SL_PCT_MIN = 0.7
    SL_PCT_MAX = 1.1

    def __init__(self):
        # Trailing config (percent thresholds)
        self.TRAIL_ACTIVATE_PCT = float(os.getenv("TRAIL_ACTIVATE_PCT", "0.6"))
        self.TRAIL_GIVEBACK_PCT = float(os.getenv("TRAIL_GIVEBACK_PCT", "0.4"))
        self.HARD_STOP_LOSS_PCT = float(os.getenv("HARD_STOP_LOSS_PCT", "1.2"))

    def check_exit(self, entry_price: float, current_price: float, features: dict, elapsed_sec: float) -> tuple:
        """
        Returns (should_exit: bool, reason: str, pnl_pct: float).
        TP = 1.7%, SL = 0.7-1.1%. Trailing is available via trailing_for_short.
        """
        if not (isinstance(entry_price, (int, float)) and isinstance(current_price, (int, float))):
            return False, "invalid_price", 0.0
        if entry_price <= 0 or current_price <= 0:
            return False, "zero_price", 0.0

        pnl_pct = ((entry_price - current_price) / entry_price) * 100.0  # short pnl

        # TP hit
        if pnl_pct >= self.TP_PCT:
            return True, "tp_hit", pnl_pct

        # SL hit (hard stop)
        if pnl_pct <= -self.SL_PCT_MAX:
            return True, "sl_hit", pnl_pct

        # Emergency exits
        btc_flip = features.get("btc_alignment", 0.0) > 0.7  # BTC pumping hard
        buy_wall = features.get("bid_dom", 0.5) > 0.65  # strong buy pressure
        vol_burst = features.get("volatility_burst", 0.0) > 0.8
        oi_collapse = features.get("oi_divergence", 0.0) < -0.3

        if btc_flip:
            return True, "btc_flip", pnl_pct
        if buy_wall:
            return True, "buy_wall", pnl_pct
        if vol_burst:
            return True, "vol_burst", pnl_pct
        if oi_collapse:
            return True, "oi_collapse", pnl_pct

        # Time stop (optional: exit after 15 min if no TP)
        if elapsed_sec > 900 and pnl_pct < 0.5:
            return True, "time_stop", pnl_pct

        return False, "hold", pnl_pct

    def trailing_for_short(self, entry_price: float, current_price: float, best_low: float | None) -> tuple:
        """
        Short trailing logic. Maintains and returns updated best_low.
        Returns (should_exit: bool, reason: str, pnl_pct: float, updated_best_low: float, trail_active: bool)
        """
        if not (isinstance(entry_price, (int, float)) and isinstance(current_price, (int, float))):
            return False, "invalid_price", 0.0, best_low, False
        if entry_price <= 0 or current_price <= 0:
            return False, "zero_price", 0.0, best_low, False

        if best_low is None or best_low <= 0:
            best_low = entry_price

        updated_best_low = best_low
        if current_price < best_low:
            updated_best_low = current_price

        pnl_pct = ((entry_price - current_price) / entry_price) * 100.0
        peak_pnl_pct = ((entry_price - updated_best_low) / entry_price) * 100.0

        # hard stop if loss exceeds threshold
        if pnl_pct <= -self.HARD_STOP_LOSS_PCT:
            return True, "hard_stop", pnl_pct, updated_best_low, False

        trail_active = pnl_pct >= self.TRAIL_ACTIVATE_PCT
        if trail_active:
            giveback = peak_pnl_pct - pnl_pct
            if giveback >= self.TRAIL_GIVEBACK_PCT and peak_pnl_pct >= self.TRAIL_ACTIVATE_PCT:
                return True, "trailing_giveback", pnl_pct, updated_best_low, True

        return False, "hold", pnl_pct, updated_best_low, trail_active
