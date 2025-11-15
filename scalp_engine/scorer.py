class Scorer:
    WEIGHTS = {
        "oi_divergence": 20,
        "liquidity_pressure": 20,
        "orderflow_imbalance": 15,
        "sweep_rejection": 15,
        "short_momentum": 10,
        "funding_impulse": 10,
        "btc_alignment": 10,
    }
    
    def score(self, feats: dict) -> float:
        """Compute 0-100 score from real feature dict. All features normalized 0..1."""
        if not isinstance(feats, dict):
            return 0.0
        total = 0.0
        for k, w in self.WEIGHTS.items():
            val = feats.get(k, 0.0)
            if not isinstance(val, (int, float)):
                val = 0.0
            val = max(0.0, min(1.0, float(val)))
            total += w * val
        max_score = sum(self.WEIGHTS.values())
        return max(0.0, min(100.0, (total / max_score) * 100.0)) if max_score > 0 else 0.0
