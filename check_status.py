#!/usr/bin/env python3
import sqlite3, os, sys
from datetime import datetime

db_path = os.path.join(os.path.dirname(__file__), "data.db")
if not os.path.exists(db_path):
    print("DB not found")
    sys.exit(1)

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Count total unified ticks
cur.execute("SELECT COUNT(*) FROM unified_ticks")
total = cur.fetchone()[0]

# No per-exchange breakdown in unified table; show recent per-symbol counts instead
cur.execute("SELECT sym, COUNT(*) FROM unified_ticks GROUP BY sym ORDER BY COUNT(*) DESC LIMIT 10")
sym_counts = cur.fetchall()

# Latest unified ticks
cur.execute("SELECT sym, COALESCE(price, mark) as price, ts FROM unified_ticks ORDER BY ts DESC LIMIT 30")
latest = cur.fetchall()

print(f"Total ticks: {total:,}")
print("\nTop symbols by rows:")
for sym, cnt in sym_counts:
    print(f"  {sym}: {cnt:,}")

print("\nLatest 30 unified ticks:")
for sym, price, ts in latest:
    dt = datetime.fromtimestamp(ts).strftime("%H:%M:%S")
    print(f"  {dt} {sym:12s} {price:.6f}")

conn.close()
