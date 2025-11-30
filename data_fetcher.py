import yfinance as yf
import logging
from config import TIMEFRAME

logger = logging.getLogger(__name__)

def fetch_data(symbol):
    """Fetch last candles of data."""
    try:
        ticker = yf.Ticker(symbol)
        # Fetch 5 days to ensure enough data for indicators
        df = ticker.history(period="5d", interval=TIMEFRAME) 
        
        if df.empty:
            logger.warning(f"No data fetched for {symbol}")
            return None
            
        return df
    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {e}")
        return None
