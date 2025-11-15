class OpenInterest:
    def divergence(self, now: float, prev: float) -> float:
        if not (isinstance(now, (int, float)) and isinstance(prev, (int, float))):
            return 0.0
        if prev <= 0 or now <= 0:
            return 0.0
        # Positive divergence (OI up while price down elsewhere) handled in orchestrator logic
        return max(-1.0, min(1.0, (now - prev) / prev))
