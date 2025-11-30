import pandas as pd
import logging

logger = logging.getLogger(__name__)

def calculate_indicators(df):
    """Calculate RSI, EMA, ATR using pure pandas."""
    try:
        # EMA (50, 200)
        df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
        df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()

        # RSI (14)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        
        # Use exponential moving average for RSI to match standard RSI
        # Standard RSI uses Wilder's Smoothing which is alpha = 1/n
        # Pandas ewm alpha=1/14 is roughly com=13.
        # Let's use a simple approximation or the proper Wilder's smoothing if possible.
        # For simplicity and robustness, standard rolling mean is often used in simple bots, 
        # but let's try to be accurate.
        # Wilder's Smoothing:
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
        
        rs = avg_gain / avg_loss
        df['RSI'] = 100 - (100 / (1 + rs))

        # ATR (14)
        high_low = df['High'] - df['Low']
        high_close = (df['High'] - df['Close'].shift()).abs()
        low_close = (df['Low'] - df['Close'].shift()).abs()
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        
        # ATR is usually SMA of TR or Wilder's. Let's use Wilder's (EWM)
        df['ATR'] = true_range.ewm(alpha=1/14, min_periods=14, adjust=False).mean()

        return df
    except Exception as e:
        logger.error(f"Error calculating indicators: {e}")
        return None
