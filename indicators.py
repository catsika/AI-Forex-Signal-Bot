import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

def calculate_indicators(df):
    """
    Calculate comprehensive technical indicators:
    - EMA (20, 50, 200)
    - RSI (14) with Wilder's smoothing
    - MACD (12, 26, 9)
    - Bollinger Bands (20, 2)
    - ATR (14)
    - ADX (14) - Trend Strength
    - Stochastic (14, 3, 3)
    - Volume Analysis (SMA, Ratio, Trend)
    """
    try:
        if df is None or len(df) < 200:
            logger.warning("Insufficient data for indicator calculation")
            return None
            
        # === MOVING AVERAGES ===
        df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
        df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
        df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
        
        # === RSI (14) - Wilder's Smoothing ===
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
        
        rs = avg_gain / avg_loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # === MACD (12, 26, 9) ===
        ema_12 = df['Close'].ewm(span=12, adjust=False).mean()
        ema_26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = ema_12 - ema_26
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Histogram'] = df['MACD'] - df['MACD_Signal']
        
        # === Bollinger Bands (20, 2) ===
        df['BB_Middle'] = df['Close'].rolling(window=20).mean()
        bb_std = df['Close'].rolling(window=20).std()
        df['BB_Upper'] = df['BB_Middle'] + (2 * bb_std)
        df['BB_Lower'] = df['BB_Middle'] - (2 * bb_std)
        df['BB_Width'] = (df['BB_Upper'] - df['BB_Lower']) / df['BB_Middle']
        df['BB_Position'] = (df['Close'] - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower'])
        
        # === ATR (14) ===
        high_low = df['High'] - df['Low']
        high_close = (df['High'] - df['Close'].shift()).abs()
        low_close = (df['Low'] - df['Close'].shift()).abs()
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        df['ATR'] = true_range.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
        
        # === ADX (14) - Average Directional Index ===
        df['ADX'], df['Plus_DI'], df['Minus_DI'] = calculate_adx(df, period=14)
        
        # === Stochastic Oscillator (14, 3, 3) ===
        low_14 = df['Low'].rolling(window=14).min()
        high_14 = df['High'].rolling(window=14).max()
        df['Stoch_K'] = 100 * (df['Close'] - low_14) / (high_14 - low_14)
        df['Stoch_D'] = df['Stoch_K'].rolling(window=3).mean()
        
        # === VOLUME ANALYSIS ===
        df = calculate_volume_indicators(df)
        
        # === TREND DETECTION ===
        df['Trend'] = np.where(df['EMA_50'] > df['EMA_200'], 1, 
                              np.where(df['EMA_50'] < df['EMA_200'], -1, 0))
        
        # === MOMENTUM SCORE ===
        df['Momentum_Score'] = calculate_momentum_score(df)
        
        return df
        
    except Exception as e:
        logger.error(f"Error calculating indicators: {e}")
        return None


def calculate_adx(df, period=14):
    """Calculate ADX, +DI, and -DI"""
    try:
        # Calculate +DM and -DM
        high_diff = df['High'].diff()
        low_diff = -df['Low'].diff()
        
        plus_dm = pd.Series(np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0), index=df.index)
        minus_dm = pd.Series(np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0), index=df.index)
        
        # True Range
        high_low = df['High'] - df['Low']
        high_close = (df['High'] - df['Close'].shift()).abs()
        low_close = (df['Low'] - df['Close'].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        
        # Smoothed values using Wilder's smoothing (simple rolling mean for stability)
        atr = tr.rolling(window=period).mean()
        plus_dm_smooth = plus_dm.rolling(window=period).mean()
        minus_dm_smooth = minus_dm.rolling(window=period).mean()
        
        # +DI and -DI
        plus_di = 100 * (plus_dm_smooth / atr)
        minus_di = 100 * (minus_dm_smooth / atr)
        
        # DX and ADX
        di_sum = plus_di + minus_di
        di_sum = di_sum.replace(0, np.nan)  # Avoid division by zero
        dx = 100 * (abs(plus_di - minus_di) / di_sum)
        adx = dx.rolling(window=period).mean()
        
        # Fill NaN with default values (25 = neutral trend strength)
        adx = adx.fillna(25)
        plus_di = plus_di.fillna(25)
        minus_di = minus_di.fillna(25)
        
        return adx, plus_di, minus_di
        
    except Exception as e:
        logger.error(f"Error calculating ADX: {e}")
        return pd.Series([25] * len(df), index=df.index), pd.Series([25] * len(df), index=df.index), pd.Series([25] * len(df), index=df.index)


def calculate_volume_indicators(df):
    """
    Calculate volume-based indicators.
    Note: Yahoo Finance Forex data has limited volume data,
    but this works well for Gold (GC=F) and Crypto (BTC-USD).
    For Forex pairs, we use tick volume as a proxy.
    """
    try:
        # Check if Volume column exists and has meaningful data
        if 'Volume' not in df.columns:
            df['Volume'] = 0
            
        # Replace 0 volumes with NaN for calculation, then forward fill
        vol = df['Volume'].replace(0, np.nan)
        
        # If all volume is NaN/0, create synthetic volume based on range
        if vol.isna().all() or (df['Volume'] == 0).all():
            # Use price range as a proxy for activity (tick volume proxy)
            df['Volume_Proxy'] = (df['High'] - df['Low']) * 1000000
            vol = df['Volume_Proxy']
            logger.info("Using price range as volume proxy for Forex pair")
        else:
            df['Volume_Proxy'] = df['Volume']
            vol = df['Volume']
        
        # Volume Moving Averages
        df['Volume_SMA_20'] = vol.rolling(window=20).mean()
        df['Volume_SMA_50'] = vol.rolling(window=50).mean()
        
        # Volume Ratio (current vs average)
        df['Volume_Ratio'] = vol / df['Volume_SMA_20']
        
        # Volume Trend (is volume increasing?)
        df['Volume_Trend'] = np.where(df['Volume_SMA_20'] > df['Volume_SMA_50'], 1, -1)
        
        # High Volume Detection (> 1.5x average)
        df['High_Volume'] = vol > (df['Volume_SMA_20'] * 1.5)
        
        # Volume Price Trend (VPT)
        df['VPT'] = (vol * ((df['Close'] - df['Close'].shift(1)) / df['Close'].shift(1))).cumsum()
        df['VPT_Signal'] = df['VPT'].ewm(span=21, adjust=False).mean()
        
        # On-Balance Volume (OBV)
        obv = [0]
        for i in range(1, len(df)):
            if df['Close'].iloc[i] > df['Close'].iloc[i-1]:
                obv.append(obv[-1] + vol.iloc[i] if not pd.isna(vol.iloc[i]) else obv[-1])
            elif df['Close'].iloc[i] < df['Close'].iloc[i-1]:
                obv.append(obv[-1] - vol.iloc[i] if not pd.isna(vol.iloc[i]) else obv[-1])
            else:
                obv.append(obv[-1])
        df['OBV'] = obv
        df['OBV_EMA'] = df['OBV'].ewm(span=21, adjust=False).mean()
        
        # OBV Trend (bullish if OBV > OBV_EMA)
        df['OBV_Trend'] = np.where(df['OBV'] > df['OBV_EMA'], 1, -1)
        
        # Volume Momentum
        df['Volume_Momentum'] = vol.pct_change(periods=5) * 100
        
        return df
        
    except Exception as e:
        logger.error(f"Error calculating volume indicators: {e}")
        return df


def calculate_momentum_score(df):
    """
    Calculate a composite momentum score (-100 to +100).
    Positive = Bullish momentum, Negative = Bearish momentum.
    """
    try:
        score = pd.Series(index=df.index, dtype=float)
        score[:] = 0
        
        # RSI contribution (-25 to +25)
        rsi_score = np.where(df['RSI'] > 70, -25,
                    np.where(df['RSI'] > 60, -10,
                    np.where(df['RSI'] < 30, 25,
                    np.where(df['RSI'] < 40, 10, 0))))
        score += rsi_score
        
        # MACD contribution (-25 to +25)
        macd_score = np.where(df['MACD_Histogram'] > 0, 
                             np.minimum(25, df['MACD_Histogram'] * 1000),
                             np.maximum(-25, df['MACD_Histogram'] * 1000))
        score += macd_score
        
        # Trend contribution (-25 to +25)
        trend_score = np.where(df['Trend'] == 1, 25,
                      np.where(df['Trend'] == -1, -25, 0))
        score += trend_score
        
        # Volume contribution (-25 to +25)
        volume_score = np.where((df['OBV_Trend'] == 1) & (df['Volume_Ratio'] > 1.2), 25,
                       np.where((df['OBV_Trend'] == -1) & (df['Volume_Ratio'] > 1.2), -25,
                       np.where(df['OBV_Trend'] == 1, 10,
                       np.where(df['OBV_Trend'] == -1, -10, 0))))
        score += volume_score
        
        return score
        
    except Exception as e:
        logger.error(f"Error calculating momentum score: {e}")
        return pd.Series([0] * len(df))
