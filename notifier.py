import requests
import logging
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)

def get_readable_name(symbol):
    names = {
        "EURUSD=X": "EUR/USD"
    }
    return names.get(symbol, symbol)

def get_signal_strength(params):
    """Calculate signal strength from indicators"""
    quality = params.get('signal_quality', {})
    
    adx = quality.get('adx', 0)
    momentum = quality.get('momentum_score', 0)
    volume_ratio = quality.get('volume_ratio', 1)
    
    # Strength categories
    if adx > 30 and abs(momentum) > 40 and volume_ratio > 1.3:
        return "🔥 STRONG"
    elif adx > 25 and abs(momentum) > 25:
        return "✅ MODERATE"
    else:
        return "⚠️ WEAK"

def send_telegram_alert(symbol, signal, params, reasoning):
    """
    Send formatted message to Telegram with enhanced metrics.
    Formatted for easy manual execution on MT5 mobile app.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram credentials missing. Log only.")
        return

    readable_name = get_readable_name(symbol)
    emoji = "🟢" if signal == "BUY" else "🔴"
    signal_strength = get_signal_strength(params)
    
    # Get signal quality metrics
    quality = params.get('signal_quality', {})
    
    # Calculate pips for easy reference
    entry = (params['entry_min'] + params['entry_max']) / 2
    sl_pips = abs(entry - params['sl']) * 10000
    tp_pips = abs(entry - params['tp']) * 10000
    
    message = f"""{emoji} **{signal} {readable_name}** {emoji}
━━━━━━━━━━━━━━━━━━━━━

� **COPY THESE VALUES:**

Entry: `{entry:.5f}`
SL: `{params['sl']:.5f}` ({sl_pips:.0f} pips)
TP: `{params['tp']:.5f}` ({tp_pips:.0f} pips)
Lot: `{params['lot_size']}`

━━━━━━━━━━━━━━━━━━━━━

💰 Risk: ${params['risk_amount']:.0f} → Reward: ${params['potential_profit']:.0f}
� Strength: {signal_strength}
� ADX: {quality.get('adx', 0):.0f} | RSI: {quality.get('rsi', 0):.0f}

🤖 **AI:** {reasoning[:200]}...

━━━━━━━━━━━━━━━━━━━━━
⚡ Tap values above to copy!
"""

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        resp = requests.post(url, json=payload)
        if resp.status_code != 200:
            logger.error(f"Failed to send Telegram message: {resp.text}")
        else:
            logger.info(f"Alert sent for {symbol}")
    except Exception as e:
        logger.error(f"Telegram error: {e}")


def send_trailing_stop_alert(symbol, trade_type, old_sl, new_sl, entry_price, current_price):
    """
    Send Telegram alert when trailing stop is moved to breakeven.
    
    This is CRITICAL - user needs to update their broker's SL!
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram credentials missing. Log only.")
        return

    readable_name = get_readable_name(symbol)
    emoji = "🟢" if trade_type == "BUY" else "🔴"
    
    # Calculate profit locked
    if trade_type == "BUY":
        locked_pips = (new_sl - entry_price) * 10000  # For EUR/USD
    else:
        locked_pips = (entry_price - new_sl) * 10000
    
    message = f"""🔄 **TRAILING STOP UPDATE: {readable_name}**
━━━━━━━━━━━━━━━━━━━━━

⚡ **ACTION REQUIRED:**
Update your Stop Loss in your broker NOW!

{emoji} **Trade:** {trade_type}
├ Entry: {entry_price:.5f}
├ Current: {current_price:.5f}

🛡️ **Stop Loss Change:**
├ OLD SL: {old_sl:.5f} ❌
├ NEW SL: {new_sl:.5f} ✅
└ Profit Locked: {locked_pips:.1f} pips

💰 **Trade is now RISK-FREE!**
Your stop is at breakeven + small profit.

━━━━━━━━━━━━━━━━━━━━━
⏰ Update your broker immediately!
"""

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        resp = requests.post(url, json=payload)
        if resp.status_code != 200:
            logger.error(f"Failed to send trailing stop alert: {resp.text}")
        else:
            logger.info(f"Trailing stop alert sent for {symbol}")
    except Exception as e:
        logger.error(f"Telegram error: {e}")


def send_trade_closed_alert(symbol, trade_type, entry_price, exit_price, pnl, reason):
    """
    Send Telegram alert when a trade closes.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram credentials missing. Log only.")
        return

    readable_name = get_readable_name(symbol)
    
    if pnl > 0:
        emoji = "✅"
        result = "WIN"
    elif pnl < -5:
        emoji = "❌"
        result = "LOSS"
    else:
        emoji = "⚖️"
        result = "BREAKEVEN"
    
    message = f"""{emoji} **TRADE CLOSED: {readable_name}**
━━━━━━━━━━━━━━━━━━━━━

📊 **Result:** {result}

💵 **Trade Details:**
├ Type: {trade_type}
├ Entry: {entry_price:.5f}
├ Exit: {exit_price:.5f}
└ Reason: {reason}

💰 **P/L:** ${pnl:+.2f}

━━━━━━━━━━━━━━━━━━━━━
"""

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        resp = requests.post(url, json=payload)
        if resp.status_code != 200:
            logger.error(f"Failed to send trade closed alert: {resp.text}")
        else:
            logger.info(f"Trade closed alert sent for {symbol}")
    except Exception as e:
        logger.error(f"Telegram error: {e}")