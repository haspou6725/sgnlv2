import streamlit as st
import sqlite3
import time
import json
import sys
from zoneinfo import ZoneInfo
sys.path.insert(0, "/app")
from data_fetcher.symbols import load_symbols

st.set_page_config(page_title="SGNLV2 Real-Time", layout="wide")
st.title("🚀 SGNLV2 Real-Time Dashboard")

DB_PATH = "/app/state/data.db"

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


# Auto-refresh fully removed; dashboard only updates on browser refresh or manual button

def fetch_recent_ticks(n=100):
    conn = get_conn()
    rows = conn.execute("SELECT ts, sym, COALESCE(price, mark) as price, spread, bid_total, ask_total FROM unified_ticks ORDER BY ts DESC LIMIT ?", (n,)).fetchall()
    conn.close()
    return rows

def fetch_recent_signals(n=20):
    conn = get_conn()
    rows = conn.execute("SELECT ts, sym, score, entry_price, reason FROM signals ORDER BY ts DESC LIMIT ?", (n,)).fetchall()
    conn.close()
    return rows

def fetch_freshness_and_counts():
    conn = get_conn()
    cur = conn.cursor()
    now = time.time()
    cur.execute("SELECT MAX(ts) FROM unified_ticks")
    latest_tick = cur.fetchone()[0] or 0
    cur.execute("SELECT MAX(ts) FROM features")
    latest_feat = cur.fetchone()[0] or 0
    cur.execute("SELECT COUNT(*) FROM unified_ticks")
    tick_count = cur.fetchone()[0] or 0
    cur.execute("SELECT COUNT(*) FROM features")
    feat_count = cur.fetchone()[0] or 0
    conn.close()
    return max(0.0, now - latest_tick), max(0.0, now - latest_feat), tick_count, feat_count

def fetch_symbol_stats():
    conn = get_conn()
    rows = conn.execute("""
        SELECT sym, COUNT(*) as cnt, MIN(COALESCE(price, mark)) as lo, MAX(COALESCE(price, mark)) as hi, AVG(COALESCE(price, mark)) as avg
        FROM unified_ticks
        WHERE ts > ?
        GROUP BY sym
        ORDER BY cnt DESC
    """, (time.time() - 3600,)).fetchall()
    conn.close()
    return rows

def fetch_symbol_ticks(sym: str, lookback_sec: int = 3600):
    conn = get_conn()
    rows = conn.execute(
        "SELECT ts, COALESCE(price, mark) as price FROM unified_ticks WHERE sym=? AND ts>? ORDER BY ts ASC",
        (sym, time.time() - lookback_sec),
    ).fetchall()
    conn.close()
    return rows

def fetch_symbol_scores(sym: str, lookback_sec: int = 3600):
    conn = get_conn()
    rows = conn.execute(
        "SELECT ts, data FROM features WHERE sym=? AND ts>? ORDER BY ts ASC",
        (sym, time.time() - lookback_sec),
    ).fetchall()
    conn.close()
    out = []
    for ts, data in rows:
        try:
            d = json.loads(data)
            sc = float(d.get("score", 0))
            out.append((ts, sc))
        except Exception:
            continue
    return out

def fetch_top_ranks(lookback_sec: int = 3600, limit: int = 20):
    conn = get_conn()
    rows = conn.execute(
        "SELECT sym, score, ts FROM ranks WHERE ts>? ORDER BY ts DESC LIMIT 2000",
        (time.time() - lookback_sec,),
    ).fetchall()
    conn.close()
    latest = {}
    for sym, score, ts in rows:
        if sym not in latest or ts > latest[sym][1]:
            latest[sym] = (float(score), ts)
    sorted_syms = sorted(latest.items(), key=lambda kv: kv[1][0], reverse=True)[:limit]
    return [(sym, sc_ts[0]) for sym, sc_ts in sorted_syms]

# Sidebar
st.sidebar.header("Controls")
# 'Refresh now' button removed; dashboard only updates on browser refresh

st.sidebar.header("Universe")
symbols = load_symbols()
st.sidebar.metric("Total Symbols", len(symbols))
st.sidebar.text_area("Loaded Symbols (first 50)", "\n".join(symbols[:50]), height=200)

# Live metrics
tick_age, feat_age, tick_cnt, feat_cnt = fetch_freshness_and_counts()
m1, m2, m3, m4 = st.columns(4)
m1.metric("Tick Freshness", f"{tick_age:.1f}s")
m2.metric("Feature Freshness", f"{feat_age:.1f}s")
m3.metric("Total Ticks", f"{tick_cnt:,}")
m4.metric("Total Features", f"{feat_cnt:,}")

# Main
tab1, tab2, tab3, tab4 = st.tabs(["📊 Live Ticks", "🔻 Signals", "📈 Symbol Stats", "🖼️ Charts + Ranks"])

TEHRAN = ZoneInfo("Asia/Tehran")

def fmt_dt(ts: float, show_date: bool = False):
    if not ts:
        return "-"
    t = time.localtime(ts)  # fallback if ZoneInfo fails
    try:
        from datetime import datetime
        return datetime.fromtimestamp(ts, TEHRAN).strftime("%Y-%m-%d %H:%M:%S") if show_date else datetime.fromtimestamp(ts, TEHRAN).strftime("%H:%M:%S")
    except Exception:
        return time.strftime("%Y-%m-%d %H:%M:%S" if show_date else "%H:%M:%S", t)

with tab1:
    st.subheader("Recent Ticks (Last 100)")
    ticks = fetch_recent_ticks(100)
    if ticks:
        for ts, sym, price, spread, bt, at in ticks[:20]:
            extra = []
            if spread is not None:
                extra.append(f"spread={spread:.6f}")
            if bt is not None and at is not None:
                extra.append(f"depth(b={bt:.2f}, a={at:.2f})")
            suffix = " | " + ", ".join(extra) if extra else ""
            st.write(f"{fmt_dt(ts)} | {sym:10} | ${price:.6f}{suffix}")
    else:
        st.info("No ticks yet...")

with tab2:
    st.subheader("Recent Signals")
    signals = fetch_recent_signals(20)
    if signals:
        for ts, sym, score, ep, reason in signals:
            st.write(f"{fmt_dt(ts, show_date=True)} | {sym:10} | Score: {score:.1f} | Entry: ${ep:.6f} | {reason}")
    else:
        st.info("No signals yet...")

with tab3:
    st.subheader("Symbol Stats (Last 1h)")
    stats = fetch_symbol_stats()
    if stats:
        for sym, cnt, lo, hi, avg in stats[:30]:
            st.write(f"{sym:10} | Ticks: {cnt:5} | Lo: ${lo:.6f} | Hi: ${hi:.6f} | Avg: ${avg:.6f}")
    else:
        st.info("No stats yet...")

with tab4:
    st.subheader("Symbol Charts (Last 1h)")
    sel = st.selectbox("Select symbol", options=symbols)
    col1, col2 = st.columns(2)
    with col1:
        st.caption(f"Price: {sel}")
        pts = fetch_symbol_ticks(sel, 3600)
        if pts:
            st.line_chart({"ts": [p[0] for p in pts], "price": [p[1] for p in pts]}, x="ts", y="price")
        else:
            st.info("No price data in window.")
    with col2:
        st.caption(f"Score: {sel}")
        scs = fetch_symbol_scores(sel, 3600)
        if scs:
            st.line_chart({"ts": [s[0] for s in scs], "score": [s[1] for s in scs]}, x="ts", y="score")
        else:
            st.info("No score data in window.")

    st.divider()
    st.subheader("Top Symbols by Latest Score (1h)")
    ranks = fetch_top_ranks(3600, 20)
    if ranks:
        for sym, score in ranks:
            st.write(f"{sym:10} | Score: {score:.1f}")
    else:
        st.info("No ranks yet...")

st.caption(f"Last updated (Tehran): {fmt_dt(time.time(), show_date=True)}")
