"""
SGNL-V2 Main Entry Point
Starts the trading engine orchestrator
"""
import asyncio
import os
import sys
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.orchestrator import Orchestrator


def load_config() -> dict:
    """Load configuration from environment"""
    load_dotenv()
    
    config = {
        # Telegram
        "telegram_bot_token": os.getenv("TELEGRAM_BOT_TOKEN", ""),
        "telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID", ""),
        
        # MySQL
        "mysql": {
            "host": os.getenv("MYSQL_HOST", "mysql"),
            "port": int(os.getenv("MYSQL_PORT", "3306")),
            "user": os.getenv("MYSQL_USER", "sgnlv2_user"),
            "password": os.getenv("MYSQL_PASSWORD", "sgnlv2_secure_password"),
            "database": os.getenv("MYSQL_DATABASE", "sgnlv2_db")
        },
        
        # Application
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
        "refresh_interval": int(os.getenv("REFRESH_INTERVAL", "5")),
        "max_daily_trades": int(os.getenv("MAX_DAILY_TRADES", "8")),
        "cooldown_seconds": int(os.getenv("COOLDOWN_SECONDS", "60")),
        
        # Trading
        "min_score_threshold": float(os.getenv("MIN_SCORE_THRESHOLD", "72")),
        "min_ask_imbalance": float(os.getenv("MIN_ASK_IMBALANCE", "0.60")),
        "tp_percent": float(os.getenv("TP_PERCENT", "1.7")),
        "sl_percent_min": float(os.getenv("SL_PERCENT_MIN", "0.7")),
        "sl_percent_max": float(os.getenv("SL_PERCENT_MAX", "1.1")),
    }
    
    return config


def setup_logging(log_level: str = "INFO"):
    """Configure logging"""
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> | <level>{message}</level>",
        level=log_level
    )
    logger.add(
        "/home/runner/work/sgnlv2/sgnlv2/logs/sgnlv2_{time}.log",
        rotation="1 day",
        retention="7 days",
        level=log_level
    )


async def main():
    """Main entry point"""
    # Load configuration
    config = load_config()
    setup_logging(config["log_level"])
    
    logger.info("=" * 60)
    logger.info("SGNL-V2 Crypto Short-Scalp Engine")
    logger.info("=" * 60)
    
    # Create orchestrator
    orchestrator = Orchestrator(config)
    
    try:
        # Start the engine
        await orchestrator.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        await orchestrator.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        await orchestrator.stop()
        raise


if __name__ == "__main__":
    # Create logs directory
    os.makedirs("/home/runner/work/sgnlv2/sgnlv2/logs", exist_ok=True)
    
    # Run the engine
    asyncio.run(main())
