"""
Telegram Notification Layer
Sends alerts with deduplication and rate limiting
"""
import asyncio
from typing import Optional
from datetime import datetime, timedelta
from loguru import logger
from telegram import Bot
from telegram.error import TelegramError
from telegram_bot.templates import (
    format_signal_message,
    format_exit_message,
    format_health_message,
    format_daily_summary
)


class TelegramNotifier:
    """Send notifications via Telegram with smart rate limiting"""
    
    def __init__(self, bot_token: str, chat_id: str, cooldown_seconds: int = 60):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.cooldown_seconds = cooldown_seconds
        self.bot: Optional[Bot] = None
        
        # Deduplication tracking
        self.sent_signals = {}  # symbol -> last_sent_time
        self.last_health_message = None
        
        # Initialize bot
        if bot_token and bot_token != "your_telegram_bot_token_here":
            try:
                self.bot = Bot(token=bot_token)
                logger.info("Telegram bot initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Telegram bot: {e}")
                self.bot = None
        else:
            logger.warning("Telegram bot token not configured - notifications disabled")
    
    async def send_signal(self, signal: dict) -> bool:
        """Send a signal notification with deduplication"""
        if not self.bot:
            logger.debug("Telegram bot not configured, skipping notification")
            return False
        
        symbol = signal.get("symbol", "unknown")
        
        # Check cooldown
        if not self._check_cooldown(symbol):
            logger.debug(f"Signal for {symbol} in cooldown, skipping")
            return False
        
        try:
            message = format_signal_message(signal)
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode="HTML"
            )
            
            # Update tracking
            self.sent_signals[symbol] = datetime.now()
            logger.info(f"Telegram signal sent for {symbol}")
            return True
            
        except TelegramError as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Telegram message: {e}")
            return False
    
    async def send_exit(self, exit_data: dict) -> bool:
        """Send an exit notification"""
        if not self.bot:
            return False
        
        try:
            message = format_exit_message(exit_data)
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode="HTML"
            )
            logger.info(f"Telegram exit notification sent for {exit_data.get('symbol')}")
            return True
        except Exception as e:
            logger.error(f"Failed to send exit notification: {e}")
            return False
    
    async def send_health(self, status: str, details: str = "") -> bool:
        """Send health status message with rate limiting"""
        if not self.bot:
            return False
        
        # Rate limit health messages (max 1 per 5 minutes)
        if self.last_health_message:
            elapsed = (datetime.now() - self.last_health_message).total_seconds()
            if elapsed < 300:  # 5 minutes
                return False
        
        try:
            message = format_health_message(status, details)
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode="HTML"
            )
            self.last_health_message = datetime.now()
            logger.info(f"Health message sent: {status}")
            return True
        except Exception as e:
            logger.error(f"Failed to send health message: {e}")
            return False
    
    async def send_daily_summary(self, summary: dict) -> bool:
        """Send daily performance summary"""
        if not self.bot:
            return False
        
        try:
            message = format_daily_summary(summary)
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode="HTML"
            )
            logger.info("Daily summary sent")
            return True
        except Exception as e:
            logger.error(f"Failed to send daily summary: {e}")
            return False
    
    def _check_cooldown(self, symbol: str) -> bool:
        """Check if symbol is in cooldown period"""
        if symbol not in self.sent_signals:
            return True
        
        last_sent = self.sent_signals[symbol]
        elapsed = (datetime.now() - last_sent).total_seconds()
        
        return elapsed >= self.cooldown_seconds
    
    async def test_connection(self) -> bool:
        """Test Telegram bot connection"""
        if not self.bot:
            logger.error("Telegram bot not initialized")
            return False
        
        try:
            await self.bot.get_me()
            logger.info("Telegram bot connection test successful")
            return True
        except Exception as e:
            logger.error(f"Telegram bot connection test failed: {e}")
            return False
