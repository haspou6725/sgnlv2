from data_fetcher.symbols import load_symbols

class SymbolSelector:
    def eligible(self, latest_prices: dict, max_price: float = 5.0) -> list:
        """Return symbols from load_symbols() with price <= max_price."""
        syms = load_symbols()
        valid = []
        for s in syms:
            p = latest_prices.get(s)
            if p is not None and isinstance(p, (int, float)) and 0 < p <= max_price:
                valid.append(s)
        return valid
    
    def top(self, symbols: list, scores: dict, n: int = 10) -> list:
        """Sort symbols by score descending, return top n."""
        ranked = sorted(symbols, key=lambda s: scores.get(s, 0.0), reverse=True)
        return ranked[:n]
