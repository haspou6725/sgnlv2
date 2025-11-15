"""Send a test signal message via Telegram using TelegramNotifier"""
import asyncio
import os
from dotenv import load_dotenv
from telegram_bot.notifier import TelegramNotifier

async def main():
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    notifier = TelegramNotifier(token, chat_id, cooldown_seconds=5)

    test_signal = {
        "symbol": "TEST/USDT",
        "entry": 1.2345,
        "tp": 1.2555,
        "sl": 1.2280,
        "score": 89.7,
        "exchange": "binance",
        "reasons": ["Test harness", "Connectivity check"]
    }

    print("Sending test signal...")
    ok = await notifier.send_signal(test_signal)
    print("Result:", ok)

if __name__ == "__main__":
    asyncio.run(main())
