# SGNL-V2 🔥

**Autonomous Short-Scalp Trading Engine for Crypto Futures**

SGNL-V2 is a real-time, AI-powered short-scalp signal generator optimized for low-cap crypto futures on LBank, Binance, MEXC, and Bybit. It detects microstructure inefficiencies and generates high-conviction SHORT signals with precise TP/SL levels.

## 🎯 Key Features

- **Multi-Exchange Support**: LBank, Binance, MEXC, Bybit Futures
- **Ultra-Fast Microstructure Detection**: Analyzes orderbook depth, funding rates, open interest, and trades
- **Smart Scoring Engine (UPS)**: 0-100 score based on 10+ features
- **Automated Signal Generation**: 4-8 high-quality SHORT signals per day
- **Telegram Notifications**: Real-time alerts with entry, TP, SL
- **Live Dashboard**: Streamlit-based real-time monitoring
- **MySQL History**: Persistent signal storage and analytics
- **Docker Ready**: Complete containerized deployment

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      SGNL-V2 Engine                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐    ┌─────────────────┐   ┌─────────────┐ │
│  │   Fetchers   │───▶│ Feature Engine  │──▶│   Scorer    │ │
│  │ (4 Exchanges)│    │ (10 Features)   │   │  (UPS 0-100)│ │
│  └──────────────┘    └─────────────────┘   └──────┬──────┘ │
│                                                     │         │
│                                                     ▼         │
│  ┌──────────────┐    ┌─────────────────┐   ┌─────────────┐ │
│  │   Telegram   │◀───│ Entry Trigger   │◀──│Exit Manager │ │
│  │   Notifier   │    │  (Signal Gen)   │   │  (TP/SL)    │ │
│  └──────────────┘    └─────────────────┘   └─────────────┘ │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Storage: SQLite Cache + MySQL History        │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 📊 Signal Generation Logic

### Entry Conditions (SHORT)
- **Score ≥ 72/100** (minimum threshold)
- **Ask Imbalance ≥ 60%** (ask-heavy orderbook)
- **Sweep Detected** (large aggressive order)
- **OI Divergence ≥ 30** (OI rising + price falling)
- **Spread Risk < 0.5%** (tight spread)
- **Cooldown: 60s** between signals per symbol
- **Max 8 signals/day** (quality over quantity)

### Exit Logic
- **Take Profit: +1.7%** (SHORT position)
- **Stop Loss: -0.7% to -1.1%** (adjusts based on volatility)
- **Emergency Exit**: BTC pump, liquidity flip, timeout (1h)
- **Optional Trailing**: Lock profits on favorable moves

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/haspou6725/sgnlv2.git
cd sgnlv2
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your Telegram credentials
nano .env
```

**Required Environment Variables:**
```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
```

### 3. Run with Docker (Recommended)
```bash
docker-compose up -d
```

This starts:
- **SGNL-V2 Engine** (main.py)
- **MySQL Database** (signals history)
- **Streamlit Dashboard** (http://localhost:8501)

### 4. Access Dashboard
Open browser: **http://localhost:8501**

## 🛠️ Manual Setup (Without Docker)

### Prerequisites
- Python 3.10+
- MySQL 8.0+ (optional, for history)

### Installation
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run engine
python app/main.py

# Run dashboard (separate terminal)
streamlit run ui/dashboard.py
```

## 📁 Project Structure

```
sgnlv2/
├── app/
│   ├── main.py              # Entry point
│   └── orchestrator.py      # Main loop coordinator
├── data_fetcher/
│   ├── fetch_lbank.py       # LBank data fetcher
│   ├── fetch_binance.py     # Binance data fetcher
│   ├── fetch_mexc.py        # MEXC data fetcher
│   ├── fetch_bybit.py       # Bybit data fetcher
│   └── ws_client.py         # WebSocket base client
├── features/
│   ├── orderflow.py         # Orderbook imbalance, sweep detection
│   ├── liquidity.py         # Sell walls, buy exhaustion
│   ├── funding_oi.py        # Funding rate & OI divergence
│   └── volatility.py        # VWAP distance, momentum
├── scalp_engine/
│   ├── scorer.py            # UPS scoring (0-100)
│   ├── entry_trigger.py     # Entry condition checker
│   └── exit_manager.py      # TP/SL/emergency exits
├── telegram_bot/
│   ├── notifier.py          # Telegram notification sender
│   └── templates.py         # Message templates
├── ui/
│   └── dashboard.py         # Streamlit dashboard
├── storage/
│   ├── db.py                # SQLite + MySQL storage
│   └── sqlite_cache.db      # Local cache (auto-created)
├── tests/                   # Unit tests
├── Dockerfile               # Docker container definition
├── docker-compose.yml       # Multi-container orchestration
├── requirements.txt         # Python dependencies
└── .env.example             # Environment template
```

## 🔧 Configuration

### Key Parameters (`.env`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `MIN_SCORE_THRESHOLD` | 72 | Minimum score to generate signal |
| `MIN_ASK_IMBALANCE` | 0.60 | Minimum ask dominance (60%) |
| `TP_PERCENT` | 1.7 | Take profit percentage |
| `SL_PERCENT_MIN` | 0.7 | Stop loss min % |
| `SL_PERCENT_MAX` | 1.1 | Stop loss max % |
| `MAX_DAILY_TRADES` | 8 | Max signals per day |
| `COOLDOWN_SECONDS` | 60 | Cooldown between signals |
| `REFRESH_INTERVAL` | 5 | Loop interval (seconds) |

## 📈 Dashboard Features

The Streamlit dashboard provides:
- **Real-time Metrics**: Active symbols, signals generated, average score
- **Top Scoring Symbols**: Live leaderboard of best opportunities
- **Signal History**: Recent SHORT signals with TP/SL
- **Score Distribution**: Histogram of symbol scores
- **Feature Breakdown**: Detailed analysis of top symbol
- **Auto-refresh**: Configurable refresh interval (1-30s)

## 🔔 Telegram Notifications

Signal format:
```
🔥 SGNL-V2 SHORT SIGNAL 🔥

Symbol: XLMUSDT
Exchange: BINANCE

Entry: $0.12345678
Take Profit: $0.12135802 (+1.70%)
Stop Loss: $0.12469234 (-1.00%)

Score: 78.5/100

Reasons:
  • Strong OI divergence detected
  • High liquidity pressure
  • Large sweep order detected

⏰ 2024-01-15 14:30:25
```

## 🧪 Testing

Run tests:
```bash
pytest tests/ -v
```

Run with coverage:
```bash
pytest tests/ --cov=. --cov-report=html
```

## 📊 Scoring Algorithm (UPS)

The Unified Prediction Score (0-100) combines:

| Feature | Weight | Description |
|---------|--------|-------------|
| **OI Divergence** | 20% | OI rising + price falling |
| **Liquidity Pressure** | 20% | Sell walls + buy exhaustion |
| **Orderflow Imbalance** | 15% | Ask-heavy orderbook |
| **Sweep Detection** | 15% | Large aggressive orders |
| **BTC Microtrend** | 10% | BTC not pumping |
| **Short Momentum** | 10% | Negative price momentum |
| **Funding Rate** | 10% | Positive funding (longs overleveraged) |

**Total: 100%**

## 🛡️ Security & Best Practices

- **Never commit `.env`** - Contains sensitive credentials
- **Use read-only API keys** - Signal generation only (no trading execution)
- **Run as non-root** - Docker container uses unprivileged user
- **Rate limiting** - Respects exchange API limits
- **Error handling** - Graceful degradation on exchange downtime

## 🔍 Monitoring

### Logs
```bash
tail -f logs/sgnlv2_*.log
```

### Database
```bash
# SQLite cache
sqlite3 storage/sqlite_cache.db "SELECT * FROM last_signals ORDER BY timestamp DESC LIMIT 10;"

# MySQL history
docker exec -it sgnlv2_mysql mysql -u sgnlv2_user -p sgnlv2_db
```

## 🐛 Troubleshooting

### Engine not starting
- Check `.env` configuration
- Verify MySQL connection (if using)
- Check logs: `logs/sgnlv2_*.log`

### No signals generated
- Verify exchange APIs are accessible
- Check minimum score threshold (default 72)
- Review cooldown/daily limits

### Dashboard shows no data
- Ensure engine is running first
- Wait 1-2 minutes for data collection
- Check SQLite cache exists: `storage/sqlite_cache.db`

## 📝 License

MIT License - See LICENSE file

## 👤 Author

**Hassan (haspou6725)**
- GitHub: [@haspou6725](https://github.com/haspou6725)

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## ⚠️ Disclaimer

**FOR EDUCATIONAL AND RESEARCH PURPOSES ONLY**

This software is provided "as is" without warranty. Trading cryptocurrencies carries risk. The authors are not responsible for any financial losses incurred while using this software. Always do your own research and never risk more than you can afford to lose.

---

**Built with ❤️ by Hassan | Powered by GitHub Copilot**
