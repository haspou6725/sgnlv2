from loguru import logger

class EntryTrigger:
    def should_short(self, features: dict, microstructure: dict, symbol: str = "") -> bool:
        """Check real conditions for short entry. All values must be real."""
        if not (isinstance(features, dict) and isinstance(microstructure, dict)):
            return False
        
        # Core microstructure signals
        sweep_rej = features.get("sweep_rejection", 0.0)
        ask_dom = microstructure.get("ask_dom", 0.5)
        liq_gap = features.get("liquidity_gap_above", 0.0)
        spread_pct = microstructure.get("spread_pct", 0.0)
        spread_ok = spread_pct < 0.002  # spread <0.2%
        
        # OI + price divergence
        oi_div = features.get("oi_divergence", 0.0)
        
        # Funding negative (shorts paid)
        funding_impulse = features.get("funding_impulse", 0.0)
        funding_neg = funding_impulse < 0
        
        # BTC not pumping
        btc_align = features.get("btc_alignment", 1.0)
        btc_ok = btc_align < 0.5
        
        # Near resistance (optional tight check)
        near_res = features.get("near_resistance", 1.0) < 0.0025
        
        conditions = [
            sweep_rej >= 0.7,
            ask_dom > 0.6,
            liq_gap > 0.005,
            spread_ok,
            oi_div > 0.0,
            funding_neg,
            btc_ok,
        ]
        met = sum(conditions)
        
        # Log for high-scoring symbols that don't meet entry criteria
        score = features.get("final_score", 0)
        if score >= 60 and met < 6:
            logger.warning(
                f"Entry check failed for {symbol} (score={score:.1f}): "
                f"sweep={sweep_rej:.2f}≥0.7? {conditions[0]} | "
                f"ask_dom={ask_dom:.2f}>0.6? {conditions[1]} | "
                f"liq_gap={liq_gap:.4f}>0.005? {conditions[2]} | "
                f"spread={spread_pct:.4f}<0.002? {conditions[3]} | "
                f"oi_div={oi_div:.2f}>0? {conditions[4]} | "
                f"funding={funding_impulse:.3f}<0? {conditions[5]} | "
                f"btc={btc_align:.2f}<0.5? {conditions[6]} | "
                f"met={met}/7"
            )
        
        return met >= 6
