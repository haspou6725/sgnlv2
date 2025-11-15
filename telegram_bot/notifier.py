import aiohttp
import asyncio
import time
from typing import Dict, Tuple

class TelegramNotifier:
    COOLDOWN_SEC = 300  # 5 minutes per symbol
    EXIT_COOLDOWN_SEC = 120  # 2 minutes per symbol for exits
    
    def __init__(self, token: str, chat_id: int):
        self.token = token
        self.chat_id = chat_id
        self._last_signal_ts: Dict[str, float] = {}  # sym -> timestamp
        self._last_exit_ts: Dict[str, float] = {}  # sym -> timestamp
    
    def _should_send(self, sym: str) -> bool:
        """Check if cooldown allows new signal for symbol."""
        now = time.time()
        last = self._last_signal_ts.get(sym, 0.0)
        return (now - last) >= self.COOLDOWN_SEC
    
    def _format_signal(self, sym: str, score: float, entry_price: float, features: dict) -> str:
        """Format signal message with real metrics."""
        oi_div = features.get("oi_divergence", 0.0)
        liq_gap = features.get("liquidity_gap_above", 0.0)
        sweep = features.get("sweep_rejection", 0.0)
        funding = features.get("funding_impulse", 0.0)
        btc = features.get("btc_alignment", 0.0)
        
        msg = f"""🔻 SHORT SIGNAL: {sym}
Score: {score:.1f}/100
Entry: ${entry_price:.6f}
TP: +1.7% | SL: -1.1%

📊 Metrics:
• OI Divergence: {oi_div:.2f}
• Liq Gap Above: {liq_gap:.2%}
• Sweep Rejection: {sweep:.2f}
• Funding: {funding:.3f}
• BTC Alignment: {btc:.2f}

⏱ {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}"""
        return msg
    
    async def send_signal(self, sym: str, score: float, entry_price: float, features: dict) -> bool:
        """Send signal with cooldown and formatting. Returns True if sent."""
        if not self._should_send(sym):
            return False
        
        text = self._format_signal(sym, score, entry_price, features)
        success = await self._send(text)
        if success:
            self._last_signal_ts[sym] = time.time()
        return success

    def _should_send_exit(self, sym: str) -> bool:
        now = time.time()
        last = self._last_exit_ts.get(sym, 0.0)
        return (now - last) >= self.EXIT_COOLDOWN_SEC

    def _format_exit(self, sym: str, reason: str, price: float, pnl_pct: float) -> str:
        icon = "✅" if pnl_pct >= 0 else "⛔"
        reason_map = {
            "tp_hit": "Take Profit",
            "sl_hit": "Stop Loss",
            "hard_stop": "Hard Stop",
            "trailing_giveback": "Trailing Exit",
            "time_stop": "Time-based Exit",
        }
        label = reason_map.get(reason, reason)
        msg = f"""{icon} EXIT: {sym}
Reason: {label}
Exit: ${price:.6f}
PnL: {pnl_pct:.2f}%

⏱ {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}"""
        return msg

    async def send_exit(self, sym: str, reason: str, price: float, pnl_pct: float) -> bool:
        """Send exit notification with a shorter cooldown. Returns True if sent."""
        if not self._should_send_exit(sym):
            return False
        text = self._format_exit(sym, reason, price, pnl_pct)
        success = await self._send(text)
        if success:
            self._last_exit_ts[sym] = time.time()
        return success
    
    async def _send(self, text: str) -> bool:
        """Low-level send to Telegram API."""
        if not self.token or not self.chat_id:
            return False
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(url, json={"chat_id": self.chat_id, "text": text, "parse_mode": "Markdown"}, timeout=10) as r:
                    return r.status == 200
        except Exception:
            return False
