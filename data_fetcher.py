import yfinance as yf
import logging
from config import TIMEFRAME

logger = logging.getLogger(__name__)

def fetch_data(symbol):
    """
    Fetch historical data with enough candles for indicator calculation.
    Need at least 250+ candles for 200 EMA to stabilize.
    """
    try:
        ticker = yf.Ticker(symbol)
        
        # Map timeframe to appropriate period
        period_map = {
            "1m": "7d",      # Max for 1m
            "5m": "60d",     
            "15m": "60d",    # 60 days = ~5760 candles
            "30m": "60d",
            "1h": "730d",    # 2 years
            "1d": "5y",
        }
        
        period = period_map.get(TIMEFRAME, "60d")
        
        df = ticker.history(period=period, interval=TIMEFRAME)
        
        if df.empty:
            logger.warning(f"No data fetched for {symbol}")
            return None
        
        # Flatten MultiIndex columns if present (newer yfinance versions)
        if hasattr(df.columns, 'levels'):
            df.columns = df.columns.get_level_values(0)
            
        logger.info(f"Fetched {len(df)} candles for {symbol} ({TIMEFRAME})")
        
        # Validate minimum data requirement
        if len(df) < 250:
            logger.warning(f"Insufficient data for {symbol}: {len(df)} candles (need 250+)")
            return None
            
        return df
        
    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {e}")
        return None
