import time

class StalenessGuard:
    def __init__(self, max_age_sec: float = 5.0):
        self.max_age = max_age_sec
        self.last = {}
    def touch(self, key: str):
        self.last[key] = time.time()
    def stale(self, key: str) -> bool:
        t = self.last.get(key, 0)
        return (time.time() - t) > self.max_age
