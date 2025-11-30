import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SYMBOLS = ["GC=F", "EURUSD=X", "BTC-USD"]
TIMEFRAME = "15m"
LOOKBACK = 100
COOLDOWN_MINUTES = 60
RISK_PER_TRADE = 50.0  # USD
