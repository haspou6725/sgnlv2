# Changelog

All notable changes to SGNL-V2 will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-01-15

### Added
- Initial release of SGNL-V2 short-scalp trading engine
- Multi-exchange support (LBank, Binance, MEXC, Bybit)
- Real-time orderbook analysis with 10+ microstructure features
- Unified Prediction Score (UPS) algorithm (0-100)
- Smart entry trigger with 7 condition checks
- TP/SL exit manager with emergency exits
- Telegram notification system with rate limiting
- Streamlit real-time dashboard
- SQLite caching layer
- MySQL historical storage
- Docker deployment configuration
- Comprehensive test suite (16 unit tests)
- Full documentation (README, QUICKSTART, CHANGELOG)

### Features

#### Data Layer
- Async REST API fetchers for 4 exchanges
- WebSocket client base with reconnection logic
- Unified data format across exchanges
- Symbol discovery (tokens under $5 USDT)

#### Feature Engine
- Orderflow analysis (ask dominance, bid weakness, sweep detection)
- Liquidity analysis (sell walls, buy exhaustion)
- Funding rate & open interest tracking
- Volatility & momentum calculations
- VWAP distance tracking

#### Scoring & Entry
- UPS scoring with weighted features
- Entry conditions: score ≥72, sweep, OI divergence
- Daily signal limits (max 8/day)
- Per-symbol cooldown (60s)
- Spread risk checks

#### Exit Management
- Configurable TP (+1.7%) and SL (-0.7% to -1.1%)
- Emergency exits (liquidity flip, BTC pump)
- Optional trailing stops
- Position tracking

#### Notifications
- Telegram signal alerts with formatting
- Exit notifications
- Health status messages
- Daily summary reports
- Deduplication and rate limiting

#### UI Dashboard
- Real-time metrics (active symbols, signals, scores)
- Top scoring symbols table
- Recent signals display
- Score distribution histogram
- Feature breakdown for top symbol
- Auto-refresh (1-30s configurable)

#### Storage
- SQLite for real-time caching
- MySQL for historical signals
- Async database operations
- Auto-retry on failures

#### Deployment
- Docker containerization
- Docker Compose multi-service setup
- Non-root user security
- Health checks
- Volume persistence
- Environment-based configuration

### Documentation
- Comprehensive README with architecture diagrams
- Quick start guide (5-minute setup)
- Configuration guide
- Troubleshooting section
- Security best practices
- API documentation

### Testing
- Unit tests for fetchers
- Scorer validation tests
- Entry trigger logic tests
- 100% test pass rate

### Configuration
- Environment-based config (.env)
- 15+ configurable parameters
- Exchange enable/disable
- Threshold tuning
- Performance settings

## [Unreleased]

### Planned Features
- WebSocket live orderbook streaming
- Advanced BTC microtrend analysis
- Long position support
- Risk management module
- Performance analytics dashboard
- Backtesting framework
- Additional exchanges (Kraken, OKX)
- Machine learning score optimizer
- Mobile app notifications
- API endpoints for external systems

### Known Issues
- LBank futures API endpoints may need adjustment (varies by region)
- MEXC funding rate endpoint may be unavailable for some symbols
- High-frequency updates can trigger exchange rate limits (mitigated by 5s interval)

---

## Version History

- **1.0.0** (2024-01-15): Initial public release
- **0.9.0** (2024-01-10): Beta testing phase
- **0.1.0** (2024-01-01): Alpha development

---

## Migration Guide

### From v0.x to v1.0
No migration needed - this is the first production release.

---

## Contributors

- **Hassan (haspou6725)** - Project creator and lead developer

---

## License

MIT License - See [LICENSE](LICENSE) file for details

---

*Built with ❤️ by Hassan | Powered by GitHub Copilot*
