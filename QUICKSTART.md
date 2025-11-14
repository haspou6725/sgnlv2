# SGNL-V2 Quick Start Guide

Get SGNL-V2 up and running in 5 minutes! 🚀

## Prerequisites
- Docker & Docker Compose (recommended)
- **OR** Python 3.10+ (for manual setup)
- Telegram Bot Token (get from [@BotFather](https://t.me/botfather))

## Method 1: Docker (Recommended) ⭐

### Step 1: Clone & Configure
```bash
git clone https://github.com/haspou6725/sgnlv2.git
cd sgnlv2

# Copy environment template
cp .env.example .env
```

### Step 2: Edit `.env`
```bash
nano .env  # or use your favorite editor
```

**Set these required values:**
```env
TELEGRAM_BOT_TOKEN=123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ
TELEGRAM_CHAT_ID=987654321
```

**How to get Telegram credentials:**
1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Create a new bot with `/newbot`
3. Copy the token
4. Message [@userinfobot](https://t.me/userinfobot) to get your Chat ID

### Step 3: Launch!
```bash
docker-compose up -d
```

That's it! 🎉

**Access:**
- Dashboard: http://localhost:8501
- Logs: `docker logs -f sgnlv2_app`

### Stop
```bash
docker-compose down
```

---

## Method 2: Manual Setup (Without Docker)

### Step 1: Install Dependencies
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install packages
pip install -r requirements.txt
```

### Step 2: Configure
```bash
cp .env.example .env
nano .env  # Edit with your Telegram credentials
```

### Step 3: Run Engine
```bash
python app/main.py
```

### Step 4: Run Dashboard (Separate Terminal)
```bash
streamlit run ui/dashboard.py
```

**Access Dashboard:** http://localhost:8501

---

## Verify It's Working

1. **Check Dashboard:** Visit http://localhost:8501
   - You should see "Active Symbols" count increasing
   - "Top Scoring Symbols" table populates in ~1-2 minutes

2. **Check Logs:**
   ```bash
   # Docker
   docker logs -f sgnlv2_app
   
   # Manual
   tail -f logs/sgnlv2_*.log
   ```

3. **Wait for Signals:**
   - Engine scans markets every 5 seconds
   - High-quality signals (score ≥72) are rare by design
   - Expect 4-8 signals per day max
   - You'll receive Telegram notifications when signals are found

---

## Test the System

Run unit tests to verify everything works:
```bash
pytest tests/ -v
```

All 16 tests should pass ✅

---

## Configuration Tips

### Adjust Signal Thresholds
Edit `.env` to fine-tune:

```env
MIN_SCORE_THRESHOLD=72     # Lower = more signals (less quality)
MIN_ASK_IMBALANCE=0.60     # Minimum ask dominance
TP_PERCENT=1.7             # Take profit %
SL_PERCENT_MAX=1.1         # Stop loss %
MAX_DAILY_TRADES=8         # Max signals per day
```

### Change Monitored Exchanges
Edit `app/orchestrator.py`:
```python
# Disable an exchange
# self.fetchers["mexc"] = MEXCFetcher()  # Commented out
```

---

## Troubleshooting

### "No signals generated"
- **Normal!** High-quality SHORT signals are rare
- Lower `MIN_SCORE_THRESHOLD` in `.env` to 65 for more signals
- Check logs to see symbol scanning activity

### "Dashboard shows no data"
- Wait 1-2 minutes after starting engine
- Verify engine is running: `docker ps` or check process
- Check SQLite cache exists: `ls -la storage/sqlite_cache.db`

### "Telegram not working"
- Verify bot token in `.env` is correct
- Check chat ID (numeric, no spaces)
- Test: Message your bot on Telegram

### "Docker build fails"
- Update Docker: `docker --version` (need 20.10+)
- Clear cache: `docker system prune -a`
- Check disk space: `df -h`

### "MySQL connection error"
- MySQL is optional - engine works without it
- For history logging, wait for MySQL container: `docker logs sgnlv2_mysql`

---

## What Happens Next?

1. **Engine scans** 4 exchanges for low-cap tokens under $5
2. **Features extracted** from orderbook, trades, funding, OI
3. **Scores calculated** (0-100) for each symbol
4. **When score ≥72** + other conditions met → Signal generated
5. **Telegram notification** sent with entry, TP, SL
6. **Dashboard updates** in real-time

---

## Advanced Usage

### Run in Background (Docker)
```bash
docker-compose up -d
```

### View Logs
```bash
docker logs -f sgnlv2_app
```

### Access MySQL Database
```bash
docker exec -it sgnlv2_mysql mysql -u sgnlv2_user -p
# Password: sgnlv2_secure_password
```

### Custom Symbol List
Edit `app/orchestrator.py`:
```python
async def discover_symbols(self, max_price: float = 5.0):
    # Add manual symbols
    self.active_symbols = [
        {"symbol": "BTCUSDT", "exchange": "binance"},
        {"symbol": "ETHUSDT", "exchange": "binance"}
    ]
```

---

## Production Deployment

### Security Checklist
- [ ] Change default MySQL password in `.env`
- [ ] Never commit `.env` to Git
- [ ] Use firewall to restrict port access
- [ ] Run as non-root user (Docker already does this)
- [ ] Enable UFW firewall: `sudo ufw allow 22,8501/tcp`

### Server Setup (Ubuntu 22.04)
```bash
# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Clone and run
git clone https://github.com/haspou6725/sgnlv2.git
cd sgnlv2
cp .env.example .env
nano .env  # Configure
docker-compose up -d
```

### Auto-restart on Boot
Docker Compose with `restart: unless-stopped` (already configured) will auto-start on reboot.

---

## Need Help?

- 📖 Full docs: [README.md](README.md)
- 🐛 Issues: [GitHub Issues](https://github.com/haspou6725/sgnlv2/issues)
- 💬 Contact: [@haspou6725](https://github.com/haspou6725)

---

**Happy Trading! 🔥📈**

*Remember: This is for research/education. Always do your own due diligence.*
