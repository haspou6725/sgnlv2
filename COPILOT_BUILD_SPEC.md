# SGNL-V2 — Autonomous Build Specification  
### (Full Self-Generating Copilot Build System)

You are GitHub Copilot.  
Your task is to fully generate, implement, and structure a production-grade crypto short-scalp engine called SGNL-V2 across the entire repository.

Copilot must generate ALL code, ALL modules, ALL files, and ALL logic according to this specification.  
No TODOs.  
No placeholders.  
No mock data.  
Only real logic.

------------------------------------------------------------
1) OVERVIEW / VISION
------------------------------------------------------------

SGNL-V2 is a real-time short-scalp trading engine optimized for:
- LBank Futures (primary)
- Binance Futures
- MEXC Futures
- Bybit Futures

Targets:
- ultra-fast microstructure detection
- tokens under 5 USDT
- short-only scalping
- 1.7% TP / 0.7–1.1% SL
- 4–8 trades per day max
- high-confidence entries only

Outputs:
- Live scalp-short signals
- TP/SL calculation
- Score 0–100
- Telegram Alerts
- Streamlit Dashboard
- Historical logs in MySQL

End Users:
- Quant traders
- Automated trading systems
- Professional scalpers

------------------------------------------------------------
2) HIGH-LEVEL SYSTEM ARCHITECTURE
------------------------------------------------------------

Layers:
- Data Fetch Layer (REST + WebSocket)
- Feature Engine
- Scoring Engine
- Entry Trigger Engine
- Exit Manager
- Orchestrator Loop
- Telegram Notification Layer
- Streamlit Dashboard UI
- Storage Layer (SQLite cache + MySQL history)

Data Flow:
Exchange APIs → Fetchers → Feature Engine → Scorer → Entry Trigger → Telegram + Dashboard → DB Logging

Architecture:
Async, modular, multicomponent, high-throughput.

------------------------------------------------------------
3) COMPONENTS BREAKDOWN
------------------------------------------------------------

FETCHERS:
Inputs:
- Live orderbook depth 20 (WS)
- Funding, OI, price (REST)
- 1m trades
- BTC microtrend feed

Outputs:
- Unified DataFrame-like dict per symbol

Failure Modes:
- WS reconnect
- REST backoff
- Timeout protection

FEATURE ENGINE:
Extract 10 microstructure features:
- ask dominance
- bid weakness
- sell-wall pressure
- buy-wall exhaustion
- sweep detection
- OI divergence
- funding impulse
- micro momentum
- VWAP distance
- spread risk

SCORING ENGINE:
Score = 0–100 based on weights:
- OI Divergence: 20
- Liquidity Pressure: 20
- Orderflow Imbalance: 15
- Sweep: 15
- BTC Microtrend: 10
- Short Momentum: 10
- Funding: 10

ENTRY TRIGGER:
Enter SHORT only if:
- score ≥ 72
- ask imbalance > 60%
- sweep = true
- OI rising + price declining
- funding impulse aligns
- BTC microtrend NOT pumping

EXIT MANAGER:
- TP = +1.7%
- SL = −0.7% to −1.1%
- emergency exit on BTC flip
- exit on pressure collapse
- optional trailing

TELEGRAM LAYER:
- Deduplication
- Cooldown 45–90s
- No spamming
- Health alerts (bot alive, WS disconnected, etc.)

UI DASHBOARD:
Real-time:
- signals
- depth
- score table
- BTC trend
- top candidates
Auto-refresh 1–5s

------------------------------------------------------------
4) DATA SPECIFICATION
------------------------------------------------------------

REST:
- fundingRate
- openInterest
- markPrice
- 24h volume
- trades

WS:
- orderbook (20 levels)
- incremental updates
- timestamps

Validation:
- sorted bids/asks
- numeric
- non-null

------------------------------------------------------------
5) DATABASE SPECIFICATION
------------------------------------------------------------

SQLite (/storage/sqlite_cache.db):
- last_depth
- last_scores
- last_signals

MySQL (signals_history):
Fields:
- id
- timestamp
- symbol
- entry
- tp
- sl
- score
- exchange
- reasons (JSON)

Indexes:
- (timestamp)
- (symbol)

------------------------------------------------------------
6) ALGORITHM SPECIFICATION
------------------------------------------------------------

Microstructure Features (10):
1. Ask Dominance %
2. Bid Weakness %
3. Sell-Wall Pressure
4. Buy-Wall Exhaustion
5. Sweep Detection
6. OI Divergence
7. Funding Impulse
8. 1m Momentum
9. VWAP Distance
10. Spread Risk

Entry Thresholds:
- score ≥ 72
- ask imbalance ≥ 60%
- sweep = true
- btc microtrend ok
- resistance proximity < 0.25%

------------------------------------------------------------
7) API SPEC (optional)
------------------------------------------------------------

GET /signals/latest  
GET /scores/{symbol}  
GET /health  

------------------------------------------------------------
8) DASHBOARD SPEC
------------------------------------------------------------

Pages:
- Overview
- Real-time Signals
- Depth Snapshot
- Scoreboard
- BTC Trend

Elements:
- tables
- KPIs
- mini-charts
- auto-refresh

------------------------------------------------------------
9) NOTIFICATION SPEC
------------------------------------------------------------

Message:
🔥 SGNL-V2 SHORT SIGNAL  
Symbol: {symbol}  
Entry: {entry}  
TP: {tp}  
SL: {sl}  
Score: {score}/100  
Exchange: {exchange}  
Reasons:  
- {reason1}  
- {reason2}  

Rules:
- dedup
- cooldown
- send health messages

------------------------------------------------------------
10) DEPLOYMENT SPEC
------------------------------------------------------------

docker-compose.yml:
Services:
- sgnlv2_app
- mysql
- streamlit
- redis (optional)

Dockerfile:
- python:3.10-slim
- non-root user
- poetry/pip

Volumes:
- logs
- sqlite
- config
- state

Healthchecks:
- WS status
- REST latency
- heartbeat file

------------------------------------------------------------
11) SERVER SPEC
------------------------------------------------------------

OS: Ubuntu 22.04

Folders:
/srv/sgnlv2  
/storage/sqlite  
/logs  
/state  

Cron:
- backup
- heartbeat

Firewall:
- 22 ssh
- 8501 ui
- rest closed

------------------------------------------------------------
12) SECURITY SPEC
------------------------------------------------------------

.env rules:
- NEVER commit .env
- no hardcoded API keys
- telegram token via env
- encryption optional

------------------------------------------------------------
13) MONITORING
------------------------------------------------------------

Health checks:
- ws_connected
- rest_latency
- heartbeat timestamp

------------------------------------------------------------
14) PERFORMANCE TARGET
------------------------------------------------------------

Latency: 50–150ms  
Async everywhere  
Batch depth updates  
Warm Cache  
Filtered symbols only  

------------------------------------------------------------
15) TESTING
------------------------------------------------------------

Unit tests:
- fetchers
- scorer
- trigger
- exit

Integration tests:
- loop cycle test
- replay WS test

------------------------------------------------------------
16) FAILURE MODES
------------------------------------------------------------

WS drop → reconnect  
Exchange down → skip  
BTC feed missing → pause  
DB locked → retry  

------------------------------------------------------------
17) MAINTENANCE
------------------------------------------------------------

Semantic versioning  
Schema migrations  
Add/remove exchanges  
Update scoring logic  

------------------------------------------------------------
18) GLOSSARY
------------------------------------------------------------

UPS — Unified Prediction Score  
Sweep — large aggressive market order  
OBI — Orderbook Imbalance  
Liquidity Wall — resting order cluster  
Regime — BTC trend classifier  
VWAP — volume-weighted average price  

------------------------------------------------------------
19) REQUIRED FILE STRUCTURE
------------------------------------------------------------

/sgnlv2
    /app
        main.py
        orchestrator.py
    /data_fetcher
        fetch_lbank.py
        fetch_binance.py
        fetch_mexc.py
        fetch_bybit.py
        ws_client.py
    /features
        orderflow.py
        liquidity.py
        funding_oi.py
        volatility.py
    /scalp_engine
        scorer.py
        entry_trigger.py
        exit_manager.py
    /telegram_bot
        notifier.py
        templates.py
    /ui
        dashboard.py
    /storage
        db.py
        sqlite_cache.db
    /tests
        test_fetchers.py
        test_scorer.py
        test_trigger.py
    docker-compose.yml
    Dockerfile
    requirements.txt
    .env.example
    README.md

Copilot must generate ALL CODE automatically according to this exact blueprint.
