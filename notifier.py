import requests
import logging
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)

def get_readable_name(symbol):
    names = {
        "EURUSD=X": "EUR/USD"
    }
    return names.get(symbol, symbol)

def escape_markdown(text):
    """Escape special characters for Telegram MarkdownV2"""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

def get_signal_strength(params):
    """Calculate signal strength from indicators"""
    quality = params.get('signal_quality', {})
    
    adx = quality.get('adx', 0)
    momentum = quality.get('momentum_score', 0)
    volume_ratio = quality.get('volume_ratio', 1)
    
    # Strength categories
    if adx > 30 and abs(momentum) > 40 and volume_ratio > 1.3:
        return "STRONG"
    elif adx > 25 and abs(momentum) > 25:
        return "MODERATE"
    else:
        return "WEAK"

def send_telegram_alert(symbol, signal, params, reasoning):
    """
    Send formatted message to Telegram with enhanced metrics.
    Uses HTML parse mode to avoid Markdown escaping issues.
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
    
    # Clean up reasoning - remove special characters that might break HTML
    clean_reasoning = reasoning[:200].replace('<', '').replace('>', '').replace('&', 'and')
    
    # Use HTML format instead of Markdown
    message = f"""{emoji} <b>{signal} {readable_name}</b> {emoji}
━━━━━━━━━━━━━━━━━━━━━

📍 <b>COPY THESE VALUES:</b>

Entry: <code>{entry:.5f}</code>
SL: <code>{params['sl']:.5f}</code> - {sl_pips:.0f} pips
TP: <code>{params['tp']:.5f}</code> - {tp_pips:.0f} pips
Lot: <code>{params['lot_size']}</code>

━━━━━━━━━━━━━━━━━━━━━

💰 Risk: ${params['risk_amount']:.0f} | Reward: ${params['potential_profit']:.0f}
📊 Strength: {signal_strength}
📈 ADX: {quality.get('adx', 0):.0f} | RSI: {quality.get('rsi', 0):.0f}

🤖 <b>AI:</b> {clean_reasoning}

━━━━━━━━━━━━━━━━━━━━━
⚡ Tap values above to copy!
"""

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        resp = requests.post(url, json=payload)
        if resp.status_code != 200:
            logger.error(f"Failed to send Telegram message: {resp.text}")
            # Fallback: try without formatting
            payload["text"] = message.replace('<b>', '').replace('</b>', '').replace('<code>', '').replace('</code>', '')
            payload["parse_mode"] = None
            resp = requests.post(url, json=payload)
            if resp.status_code == 200:
                logger.info(f"Alert sent for {symbol} (plain text fallback)")
        else:
            logger.info(f"Alert sent for {symbol}")
    except Exception as e:
        logger.error(f"Telegram error: {e}")


def send_trailing_stop_alert(symbol, trade_type, old_sl, new_sl, entry_price, current_price):
    """
    Send Telegram alert when trailing stop is moved to breakeven.
    Uses HTML to avoid Markdown escaping issues.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram credentials missing. Log only.")
        return

    readable_name = get_readable_name(symbol)
    emoji = "🟢" if trade_type == "BUY" else "🔴"
    
    # Calculate profit locked
    if trade_type == "BUY":
        locked_pips = (new_sl - entry_price) * 10000
    else:
        locked_pips = (entry_price - new_sl) * 10000
    
    message = f"""🔄 <b>TRAILING STOP UPDATE: {readable_name}</b>
━━━━━━━━━━━━━━━━━━━━━

⚡ <b>ACTION REQUIRED:</b>
Update your Stop Loss in your broker NOW!

{emoji} <b>Trade:</b> {trade_type}
Entry: {entry_price:.5f}
Current: {current_price:.5f}

🛡️ <b>Stop Loss Change:</b>
OLD SL: <code>{old_sl:.5f}</code> ❌
NEW SL: <code>{new_sl:.5f}</code> ✅
Profit Locked: {locked_pips:.1f} pips

💰 Trade is now RISK-FREE!

━━━━━━━━━━━━━━━━━━━━━
⏰ Update your broker immediately!
"""

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
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
    Uses HTML to avoid Markdown escaping issues.
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
    
    message = f"""{emoji} <b>TRADE CLOSED: {readable_name}</b>
━━━━━━━━━━━━━━━━━━━━━

📊 <b>Result:</b> {result}

💵 <b>Trade Details:</b>
Type: {trade_type}
Entry: {entry_price:.5f}
Exit: {exit_price:.5f}
Reason: {reason}

💰 <b>P/L:</b> ${pnl:+.2f}

━━━━━━━━━━━━━━━━━━━━━
"""

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        resp = requests.post(url, json=payload)
        if resp.status_code != 200:
            logger.error(f"Failed to send trade closed alert: {resp.text}")
        else:
            logger.info(f"Trade closed alert sent for {symbol}")
    except Exception as e:
        logger.error(f"Telegram error: {e}")