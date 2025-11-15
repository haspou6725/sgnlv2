import os
import asyncio
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from telegram_bot.notifier import TelegramNotifier

# Simple .env reader (avoid extra deps)
ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
if os.path.exists(ENV_PATH):
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

token = os.getenv('TELEGRAM_TOKEN', '')
chat_id = int(os.getenv('TELEGRAM_CHAT_ID', '0'))

async def main():
    tg = TelegramNotifier(token, chat_id)
    sym = os.getenv('TEST_SYM', 'TESTUSDT')
    reason = os.getenv('TEST_REASON', 'trailing_giveback')
    price = float(os.getenv('TEST_PRICE', '0.12000'))
    pnl = float(os.getenv('TEST_PNL', '1.05'))
    ok = await tg.send_exit(sym, reason, price, pnl)
    print('sent:', ok)

if __name__ == '__main__':
    asyncio.run(main())
