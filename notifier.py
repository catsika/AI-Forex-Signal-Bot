import requests
import logging
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)

def get_readable_name(symbol):
    names = {
        "GC=F": "GOLD FUTURES",
        "XAUUSD=X": "GOLD SPOT",
        "EURUSD=X": "EUR/USD",
        "BTC-USD": "BITCOIN"
    }
    return names.get(symbol, symbol)

def send_telegram_alert(symbol, signal, params, reasoning):
    """
    Send formatted message to Telegram.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram credentials missing. Log only.")
        return

    readable_name = get_readable_name(symbol)
    emoji = "🚨" if signal == "BUY" else "🔻"
    
    message = f"""{emoji} {signal} SIGNAL: {readable_name} ({symbol})

✅ Entry Zone: {params['entry_min']:.2f} - {params['entry_max']:.2f}
🛑 Stop Loss: {params['sl']:.2f}
💰 Take Profit: {params['tp']:.2f}

⚖️ **Risk:** ${params['risk_amount']:.2f}
💰 **Potential Profit:** ${params['potential_profit']:.2f}
📦 **Lot Size:** {params['lot_size']}

🤖 AI Reasoning: "{reasoning}"
"""

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    
    try:
        resp = requests.post(url, json=payload)
        if resp.status_code != 200:
            logger.error(f"Failed to send Telegram message: {resp.text}")
        else:
            logger.info(f"Alert sent for {symbol}")
    except Exception as e:
        logger.error(f"Telegram error: {e}")
