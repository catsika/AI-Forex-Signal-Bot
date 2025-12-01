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
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram credentials missing. Log only.")
        return

    readable_name = get_readable_name(symbol)
    emoji = "🟢" if signal == "BUY" else "🔴"
    signal_strength = get_signal_strength(params)
    
    # Get signal quality metrics
    quality = params.get('signal_quality', {})
    
    message = f"""{emoji} **{signal} SIGNAL: {readable_name}**
━━━━━━━━━━━━━━━━━━━━━

📊 **Signal Strength:** {signal_strength}

💵 **Trade Setup:**
├ Entry Zone: {params['entry_min']:.4f} - {params['entry_max']:.4f}
├ Stop Loss: {params['sl']:.4f}
├ Take Profit: {params['tp']:.4f}
└ ATR Mult: {params.get('atr_multiplier', 1.5):.1f}x

⚖️ **Risk Management:**
├ Risk: ${params['risk_amount']:.2f}
├ Potential: ${params['potential_profit']:.2f}
└ Lot Size: {params['lot_size']}

📈 **Technical Indicators:**
├ RSI: {quality.get('rsi', 0):.1f}
├ ADX (Trend): {quality.get('adx', 0):.1f}
├ MACD Hist: {quality.get('macd_hist', 0):.4f}
├ Stoch %K: {quality.get('stoch_k', 0):.1f}
└ BB Position: {quality.get('bb_position', 0.5):.2f}

📊 **Volume Analysis:**
├ Volume Ratio: {quality.get('volume_ratio', 1):.2f}x
└ OBV Trend: {"📈 Bullish" if quality.get('obv_trend', 0) == 1 else "📉 Bearish"}

🎯 **Momentum Score:** {quality.get('momentum_score', 0):.0f}/100

🤖 **AI Analysis:**
{reasoning}

━━━━━━━━━━━━━━━━━━━━━
⏰ Trade at your own risk!
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
