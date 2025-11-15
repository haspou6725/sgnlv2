class Funding:
    def impulse(self, latest_rate: float) -> float:
        # Negative funding (shorts paid) increases short incentive; normalize around +/-0.01 baseline
        if latest_rate is None or not isinstance(latest_rate, (int, float)):
            return 0.0
        return max(-1.0, min(1.0, -latest_rate / 0.01))
