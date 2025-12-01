import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SYMBOLS = ["EURUSD=X"]  # EUR/USD only - optimized for forex
TIMEFRAME = "1h"       # 1-hour timeframe for better signals
LOOKBACK = 100
COOLDOWN_MINUTES = 60

# ═══════════════════════════════════════════════════════════════════
# PROP FIRM SETTINGS - $20k Account
# ═══════════════════════════════════════════════════════════════════
ACCOUNT_SIZE = 20000
RISK_PER_TRADE = 100.0  # USD - 0.5% risk for faster challenge completion
                        # Use $50 (0.25%) for more conservative approach
