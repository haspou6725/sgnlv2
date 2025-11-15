import os
from typing import List, Set, Dict
from loguru import logger

_SYMBOLS_CACHE: List[str] = []

def load_symbols() -> List[str]:
    global _SYMBOLS_CACHE
    if _SYMBOLS_CACHE:
        return _SYMBOLS_CACHE
    path = os.path.join(os.path.dirname(__file__), "..", "state", "symbols.txt")
    if not os.path.exists(path):
        logger.error(f"Symbol file not found: {path}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    seen = set()
    out = []
    for ln in lines:
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        # Normalize formats like "ACE/USDT" -> "ACEUSDT" and keep existing symbols as-is
        ln = ln.replace("/", "").upper()
        if ln and ln not in seen:
            seen.add(ln)
            out.append(ln)
    _SYMBOLS_CACHE = out
    logger.info(f"Loaded {len(out)} symbols from {path}")
    return out

def canon_to_lbank(sym: str) -> str:
    return f"{sym[:-4].lower()}_usdt" if sym.endswith("USDT") else f"{sym.lower()}_usdt"

def universe_by_exchange() -> Dict[str, List[str]]:
    syms = load_symbols()
    # Filter out symbols that are known invalid for certain exchanges to reduce noise
    # Keep conservative: Binance futures often excludes stocks/wrappers like AAPLX etc.
    blacklist_prefix = {"AAPL", "AAPLX", "2Z", "4"}
    binance_syms = [s for s in syms if not any(s.startswith(p) for p in blacklist_prefix)]
    return {
        "binance": binance_syms,
        "bybit": syms,
        "mexc": syms,
        "lbank": [canon_to_lbank(s) for s in syms],
    }
