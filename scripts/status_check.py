#!/usr/bin/env python3
import os
import sqlite3
import json
import time
from datetime import datetime
from collections import defaultdict
import argparse
from zoneinfo import ZoneInfo

parser = argparse.ArgumentParser(description="SGNLV2 system status (recent window)")
parser.add_argument("--lookback-sec", type=int, default=int(os.getenv("LOOKBACK_SEC", "600")), help="Lookback window in seconds (default: 600)")
parser.add_argument("--limit", type=int, default=int(os.getenv("FEATURE_LIMIT", "5000")), help="Max feature rows to scan (default: 5000)")
parser.add_argument("--top", type=int, default=int(os.getenv("TOP_N", "5")), help="Top N symbols to display (default: 5)")
args = parser.parse_args()

conn = sqlite3.connect("/app/state/data.db")
cursor = conn.cursor()

# Get data freshness (unified)
try:
    cursor.execute("SELECT MAX(ts) FROM unified_ticks")
    latest_tick = cursor.fetchone()[0]
except Exception:
    latest_tick = None
tick_age = datetime.now().timestamp() - latest_tick if latest_tick else 9999

cursor.execute("SELECT MAX(ts) FROM features")  
latest_feat = cursor.fetchone()[0]
feat_age = datetime.now().timestamp() - latest_feat if latest_feat else 9999

# Get counts (unified)
try:
    cursor.execute("SELECT COUNT(*) FROM unified_ticks")
    tick_count = cursor.fetchone()[0]
except Exception:
    tick_count = 0
cursor.execute("SELECT COUNT(*) FROM features")
feat_count = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM signals")
sig_count = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM positions")
pos_count = cursor.fetchone()[0]

# Get recent features within window
now_ts = time.time()
window_start = now_ts - args.lookback_sec
cursor.execute(
    "SELECT sym, ts, data FROM features WHERE ts > ? ORDER BY ts DESC LIMIT ?",
    (window_start, args.limit),
)
scores = []
for sym, ts, data_raw in cursor.fetchall():
    try:
        data = json.loads(data_raw)
        score_val = float(data.get("score", 0))
    except Exception:
        score_val = 0.0
    scores.append((sym, score_val))

# Group by symbol and calculate average
symbol_scores = defaultdict(list)
for sym, score in scores:
    symbol_scores[sym].append(score)

# Calculate averages and sort
avg_scores = []
for sym, score_list in symbol_scores.items():
    avg_score = sum(score_list) / len(score_list)
    avg_scores.append((sym, avg_score))
avg_scores.sort(key=lambda x: x[1], reverse=True)

print("=" * 60)
print("SYSTEM STATUS CHECK")
print("=" * 60)
try:
    tehran = ZoneInfo("Asia/Tehran")
    now_teh = datetime.fromtimestamp(time.time(), tehran).strftime("%Y-%m-%d %H:%M:%S %Z")
    print(f"Now (Tehran): {now_teh}")
except Exception:
    pass
print(f"\nData Freshness:")
print(f"  Latest tick:    {tick_age:.1f}s ago")
print(f"  Latest feature: {feat_age:.1f}s ago")
print(f"\nRecord Counts:")
print(f"  Unified:   {tick_count:,}")
print(f"  Features:  {feat_count:,}")
print(f"  Signals:   {sig_count}")
print(f"  Positions: {pos_count}")
print(f"\nTop 5 Symbols (Average Scores):")
top_syms = [sym for sym, _ in avg_scores[: args.top]]

def unified_latest_price(symbol: str) -> float:
    try:
        row = cursor.execute(
            "SELECT price, mark FROM unified_ticks WHERE sym=? AND ts>? ORDER BY ts DESC LIMIT 1",
            (symbol, window_start),
        ).fetchone()
        if not row:
            return float('nan')
        price, mark = row
        val = price if price is not None else mark
        return float(val) if val is not None else float('nan')
    except Exception:
        return float('nan')

print(f"\nTop {args.top} Symbols (Avg Score | Unified Price in last {args.lookback_sec}s):")
for sym, avg_score in avg_scores[: args.top]:
    count = len(symbol_scores[sym])
    p = unified_latest_price(sym)
    p_str = f"${p:.6f}" if p == p else "n/a"  # NaN check
    print(f"  {sym:15} {avg_score:5.2f} (avg of {count} samp) | {p_str}")
score_min = float(os.getenv("SCORE_MIN", "45"))
print(f"\nEntry Threshold: SCORE_MIN >= {int(score_min)}")
best_score = avg_scores[0][1] if avg_scores else 0.0
print(f"Max Avg Score: {best_score:.2f}")
status = "WAITING FOR ENTRY CONDITIONS" if best_score < score_min else "CHECK ENTRY LOGIC"
print(f"Status: {status}")
print("=" * 60)

conn.close()
