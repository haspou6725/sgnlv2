"""
Telegram Message Templates
Formats messages for different notification types
"""


def format_signal_message(signal: dict) -> str:
    """Format a SHORT signal message"""
    reasons_text = "\n".join([f"  • {r}" for r in signal.get("reasons", [])])
    
    message = f"""
🔥 <b>SGNL-V2 SHORT SIGNAL</b> 🔥

<b>Symbol:</b> {signal.get('symbol', 'N/A')}
<b>Exchange:</b> {signal.get('exchange', 'N/A').upper()}

<b>Entry:</b> ${signal.get('entry', 0):.8f}
<b>Take Profit:</b> ${signal.get('tp', 0):.8f} (+{((signal.get('entry', 0) - signal.get('tp', 0)) / signal.get('entry', 1)) * 100:.2f}%)
<b>Stop Loss:</b> ${signal.get('sl', 0):.8f} (-{((signal.get('sl', 0) - signal.get('entry', 0)) / signal.get('entry', 1)) * 100:.2f}%)

<b>Score:</b> {signal.get('score', 0):.1f}/100

<b>Reasons:</b>
{reasons_text}

⏰ {signal.get('datetime', 'N/A')}
"""
    return message.strip()


def format_exit_message(exit_data: dict) -> str:
    """Format an exit notification message"""
    pnl = exit_data.get('pnl_pct', 0)
    emoji = "✅" if pnl > 0 else "❌"
    
    duration_min = exit_data.get('duration_seconds', 0) / 60
    
    message = f"""
{emoji} <b>POSITION CLOSED</b> {emoji}

<b>Symbol:</b> {exit_data.get('symbol', 'N/A')}
<b>Reason:</b> {exit_data.get('reason', 'N/A')}

<b>Entry:</b> ${exit_data.get('entry', 0):.8f}
<b>Exit:</b> ${exit_data.get('exit', 0):.8f}

<b>P&L:</b> {pnl:+.2f}%

<b>Duration:</b> {duration_min:.1f} minutes

⏰ {exit_data.get('exit_time', 'N/A')}
"""
    return message.strip()


def format_health_message(status: str, details: str = "") -> str:
    """Format a health status message"""
    if status == "online":
        emoji = "✅"
        title = "BOT ONLINE"
    elif status == "warning":
        emoji = "⚠️"
        title = "WARNING"
    else:
        emoji = "🔴"
        title = "ERROR"
    
    message = f"""
{emoji} <b>{title}</b> {emoji}

<b>Status:</b> SGNL-V2 Engine
<b>Details:</b> {details}

⏰ Time: {details}
"""
    return message.strip()


def format_daily_summary(summary: dict) -> str:
    """Format daily performance summary"""
    message = f"""
📊 <b>DAILY SUMMARY</b> 📊

<b>Signals Generated:</b> {summary.get('total_signals', 0)}
<b>Positions Closed:</b> {summary.get('closed_positions', 0)}

<b>Win Rate:</b> {summary.get('win_rate', 0):.1f}%
<b>Average P&L:</b> {summary.get('avg_pnl', 0):+.2f}%
<b>Total P&L:</b> {summary.get('total_pnl', 0):+.2f}%

<b>Best Trade:</b> {summary.get('best_trade', 'N/A')} ({summary.get('best_pnl', 0):+.2f}%)
<b>Worst Trade:</b> {summary.get('worst_trade', 'N/A')} ({summary.get('worst_pnl', 0):+.2f}%)

🕐 {summary.get('date', 'N/A')}
"""
    return message.strip()
