import time
import logging
import datetime
import os
import threading
from config import SYMBOLS, COOLDOWN_MINUTES, RISK_PER_TRADE
from data_fetcher import fetch_data
from indicators import calculate_indicators
from strategy_optimized import check_signals, calculate_trade_params
from ai_manager import validate_with_ai
from notifier import send_telegram_alert
from trade_monitor import trade_monitor

# Optional: MT5 Integration (set USE_MT5=true in .env to enable)
USE_MT5 = os.getenv("USE_MT5", "false").lower() == "true"
mt5_executor = None
telegram_bot = None

if USE_MT5:
    try:
        from mt5_executor import MT5Executor
        from telegram_bot import TelegramTradeBot
    except ImportError:
        USE_MT5 = False

# Setup Logging
logging.basicConfig(
    filename="bot.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger()
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# State tracking for cooldowns
last_alert_time = {symbol: None for symbol in SYMBOLS}

def check_market_hours():
    """
    Check if the market is open.
    Forex Market Hours (approx):
    - Closes: Friday 22:00 UTC
    - Opens: Sunday 22:00 UTC
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    weekday = now.weekday()
    hour = now.hour

    # Saturday is always closed
    if weekday == 5:
        logger.info("Weekend detected (Saturday). Market closed.")
        return False

    # Friday after 22:00 UTC is closed
    if weekday == 4 and hour >= 22:
        logger.info("Weekend detected (Friday Night). Market closed.")
        return False

    # Sunday before 22:00 UTC is closed
    if weekday == 6 and hour < 22:
        logger.info("Weekend detected (Sunday Morning). Market closed.")
        return False

    return True

def run_telegram_bot():
    """Run Telegram bot in background thread"""
    global telegram_bot
    if telegram_bot:
        telegram_bot.run()

def run_bot():
    global mt5_executor, telegram_bot
    
    logger.info("Starting AI-Augmented Signal Bot (Modular + Gemini)...")
    logger.info("⚡ Trailing Stop Monitor: ACTIVE")
    
    # Initialize MT5 if enabled
    if USE_MT5:
        logger.info("🔌 MT5 Integration: ENABLED")
        mt5_executor = MT5Executor(
            login=int(os.getenv("MT5_LOGIN", 0)),
            password=os.getenv("MT5_PASSWORD", ""),
            server=os.getenv("MT5_SERVER", "")
        )
        if mt5_executor.connect():
            logger.info("✅ MT5 Connected to 5ers account")
            
            # Start Telegram bot with MT5 executor
            telegram_bot = TelegramTradeBot()
            telegram_bot.set_mt5_executor(mt5_executor)
            
            # Run Telegram bot in background
            bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
            bot_thread.start()
            logger.info("🤖 Telegram bot with trade buttons: ACTIVE")
        else:
            logger.error("❌ MT5 connection failed - running in signal-only mode")
    else:
        logger.info("📱 Running in SIGNAL-ONLY mode (no MT5)")
    
    while True:
        try:
            if not check_market_hours():
                time.sleep(900)
                continue
                
            for symbol in SYMBOLS:
                # Update existing trades with current price
                df = fetch_data(symbol)
                if df is None:
                    continue
                    
                df = calculate_indicators(df)
                if df is None:
                    continue
                
                # Monitor active trades
                current_row = df.iloc[-1]
                trade_monitor.update_price(
                    symbol,
                    current_high=current_row['High'],
                    current_low=current_row['Low'],
                    current_close=current_row['Close']
                )
                
                # Cooldown check
                last_time = last_alert_time.get(symbol)
                if last_time:
                    elapsed = (datetime.datetime.now() - last_time).total_seconds() / 60
                    if elapsed < COOLDOWN_MINUTES:
                        continue

                logger.info(f"Analyzing {symbol}...")
                    
                signal = check_signals(df)
                
                if signal:
                    logger.info(f"Signal found for {symbol}: {signal}")
                    
                    row = df.iloc[-1]
                    params = calculate_trade_params(signal, row, symbol)
                    
                    # AI Validation
                    approved, reasoning = validate_with_ai(symbol, signal, params)
                    
                    if approved:
                        logger.info(f"AI Approved {symbol}. Sending alert.")
                        
                        # Send alert first
                        alert_sent = False
                        
                        # Send alert with buttons if MT5 enabled
                        if USE_MT5 and telegram_bot:
                            import asyncio
                            signal_data = {
                                'symbol': symbol,
                                'direction': signal,
                                'entry': params['price'],
                                'sl': params['sl'],
                                'tp': params['tp'],
                                'risk': RISK_PER_TRADE,
                                'ai_analysis': reasoning
                            }
                            alert_sent = asyncio.run(telegram_bot.send_signal(signal_data))
                        else:
                            alert_sent = send_telegram_alert(symbol, signal, params, reasoning)
                        
                        if alert_sent:
                            logger.info(f"Alert sent successfully. Tracking trade for {symbol}.")
                            
                            # Track the trade
                            trade_monitor.open_trade(
                                symbol=symbol,
                                signal=signal,
                                entry_price=params['price'],
                                sl_price=params['sl'],
                                tp_price=params['tp'],
                                lot_size=params['lot_size']
                            )
                            
                            last_alert_time[symbol] = datetime.datetime.now()
                        else:
                            logger.error(f"Failed to send alert for {symbol}. Trade NOT tracked to prevent phantom signals.")
                    else:
                        logger.info(f"AI Rejected {symbol}: {reasoning}")
                else:
                    logger.info(f"No signal for {symbol}")
            
            logger.info("Cycle complete. Sleeping 15 minutes...")
            time.sleep(900)
            
        except KeyboardInterrupt:
            logger.info("Bot stopped by user.")
            logger.info(trade_monitor.get_stats())
            if mt5_executor:
                mt5_executor.disconnect()
            break
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
            time.sleep(60)

if __name__ == "__main__":
    run_bot()
