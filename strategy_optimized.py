"""
EUR/USD Optimized Strategy - Based on Grid Search Results

Best Configuration Found (Fast Grid Search v2):
- ADX Threshold: 25
- RSI Range: 30-70
- ATR Multiplier: 2.0x
- Risk:Reward: 1:2.5
- Min Score: 5.0
- Mode: Both Directions

Results: +$2,095 profit, 47.9% WR, 1.67 PF, 2.1% max DD, 121 trades
"""

from config import RISK_PER_TRADE
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

# === OPTIMIZED PARAMETERS (from fast grid search v2) ===
ADX_THRESHOLD = 25
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
ATR_MULTIPLIER = 2.0
RISK_REWARD = 2.5
MIN_SCORE = 5.0


def check_signals(df):
    """
    EUR/USD Optimized Signal Detection.
    
    Grid-search optimized for:
    - $20k prop firm account
    - $50 risk per trade
    - 1H timeframe
    - Balanced buy/sell signals
    """
    if df is None or df.empty:
        return None

    try:
        current = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else current
        prev2 = df.iloc[-3] if len(df) > 2 else prev
        
        # Check for required columns
        required_cols = ['EMA_50', 'EMA_200', 'RSI', 'MACD_Histogram', 
                        'ADX', 'Stoch_K', 'Stoch_D', 'BB_Position', 'ATR']
        for col in required_cols:
            if col not in df.columns or pd.isna(current[col]):
                logger.warning(f"Missing indicator: {col}")
                return None
        
        # === PRE-FILTERS ===
        
        # Skip ranging markets
        if current['ADX'] < ADX_THRESHOLD:
            logger.debug(f"Skipped: ADX {current['ADX']:.1f} < {ADX_THRESHOLD}")
            return None
        
        price = current['Close']
        ema20 = current.get('EMA_20', current['EMA_50'])
        ema50 = current['EMA_50']
        ema200 = current['EMA_200']
        rsi = current['RSI']
        rsi_prev = prev['RSI']
        macd_hist = current['MACD_Histogram']
        macd_prev = prev['MACD_Histogram']
        stoch_k = current['Stoch_K']
        stoch_d = current['Stoch_D']
        stoch_k_prev = prev['Stoch_K']
        stoch_d_prev = prev['Stoch_D']
        bb_pos = current['BB_Position']
        bb_prev = prev['BB_Position']
        adx = current['ADX']
        
        # Determine trend
        major_trend = "UP" if ema50 > ema200 else "DOWN"
        
        # === CALCULATE SCORES ===
        buy_score = 0
        sell_score = 0
        
        # 1. EMA ALIGNMENT (up to 2 points)
        if price > ema20 > ema50 > ema200:
            buy_score += 2
        elif ema50 > ema200 and price > ema200:
            buy_score += 1
            
        if price < ema20 < ema50 < ema200:
            sell_score += 2
        elif ema50 < ema200 and price < ema200:
            sell_score += 1
        
        # 2. RSI (up to 1.5 points)
        if RSI_OVERSOLD < rsi < 50 and rsi > rsi_prev:
            buy_score += 1.5
        elif rsi < RSI_OVERSOLD and rsi > rsi_prev:
            buy_score += 1
            
        if RSI_OVERBOUGHT > rsi > 50 and rsi < rsi_prev:
            sell_score += 1.5
        elif rsi > RSI_OVERBOUGHT and rsi < rsi_prev:
            sell_score += 1
        
        # 3. MACD (up to 1.5 points)
        if macd_hist > 0:
            buy_score += 0.5
            if macd_prev <= 0:  # Fresh cross
                buy_score += 1
            elif macd_hist > macd_prev:  # Rising
                buy_score += 0.5
                
        if macd_hist < 0:
            sell_score += 0.5
            if macd_prev >= 0:  # Fresh cross
                sell_score += 1
            elif macd_hist < macd_prev:  # Falling
                sell_score += 0.5
        
        # 4. STOCHASTIC (up to 1.5 points)
        if stoch_k > stoch_d and stoch_k_prev <= stoch_d_prev:
            if stoch_k < 30:
                buy_score += 1.5
            elif stoch_k < 50:
                buy_score += 0.5
                
        if stoch_k < stoch_d and stoch_k_prev >= stoch_d_prev:
            if stoch_k > 70:
                sell_score += 1.5
            elif stoch_k > 50:
                sell_score += 0.5
        
        # 5. BOLLINGER BANDS (up to 1 point)
        if bb_pos < 0.3 and bb_pos > bb_prev:
            buy_score += 1
        if bb_pos > 0.7 and bb_pos < bb_prev:
            sell_score += 1
        
        # 6. ADX BONUS (up to 0.5 points)
        if adx > 30:
            if major_trend == "UP":
                buy_score += 0.5
            else:
                sell_score += 0.5
        
        # === FINAL DECISION (Both directions allowed) ===
        logger.info(f"Scores - BUY: {buy_score:.1f}, SELL: {sell_score:.1f} | Trend: {major_trend}")
        
        signal = None
        
        # BUY Signal
        if buy_score >= MIN_SCORE and buy_score > sell_score + 1:
            if rsi < RSI_OVERBOUGHT:
                signal = "BUY"
                logger.info(f"BUY Signal: Score {buy_score:.1f}")
        
        # SELL Signal  
        elif sell_score >= MIN_SCORE and sell_score > buy_score + 1:
            if rsi > RSI_OVERSOLD:
                signal = "SELL"
                logger.info(f"SELL Signal: Score {sell_score:.1f}")
        
        return signal
        
    except Exception as e:
        logger.error(f"Error in check_signals: {e}")
        return None


def calculate_lot_size(symbol, entry_price, sl_price):
    """Calculate lot size for EUR/USD"""
    risk_amount = RISK_PER_TRADE
    distance = abs(entry_price - sl_price)
    
    if distance == 0:
        return 0.01
    
    # EUR/USD: 1 standard lot = 100,000 units
    lot_size = risk_amount / (100000 * distance)
    return max(0.01, round(lot_size, 2))


def calculate_trade_params(signal, row, symbol):
    """
    Calculate trade parameters with optimized settings.
    
    Uses grid-search optimized values:
    - ATR Multiplier: 2.0x
    - Risk:Reward: 1:2.5
    """
    price = row['Close']
    atr = row['ATR']
    
    if signal == "BUY":
        sl_price = row['Low'] - (ATR_MULTIPLIER * atr)
        risk = price - sl_price
        tp_price = price + (RISK_REWARD * risk)
        
        buffer_amount = price * 0.0003
        entry_min = price - buffer_amount
        entry_max = price + buffer_amount
        
    elif signal == "SELL":
        sl_price = row['High'] + (ATR_MULTIPLIER * atr)
        risk = sl_price - price
        tp_price = price - (RISK_REWARD * risk)
        
        buffer_amount = price * 0.0003
        entry_max = price + buffer_amount
        entry_min = price - buffer_amount
    
    lot_size = calculate_lot_size(symbol, price, sl_price)
    tp_dist = abs(tp_price - price)
    potential_profit = lot_size * 100000 * tp_dist
    
    signal_quality = {
        'adx': row.get('ADX', 0),
        'rsi': row.get('RSI', 50),
        'macd_hist': row.get('MACD_Histogram', 0),
        'volume_ratio': row.get('Volume_Ratio', 1),
        'obv_trend': row.get('OBV_Trend', 0),
        'momentum_score': row.get('Momentum_Score', 0),
        'bb_position': row.get('BB_Position', 0.5),
        'stoch_k': row.get('Stoch_K', 50),
    }
        
    return {
        "price": price,
        "sl": sl_price,
        "tp": tp_price,
        "entry_min": entry_min,
        "entry_max": entry_max,
        "atr": atr,
        "atr_multiplier": ATR_MULTIPLIER,
        "rsi": row['RSI'],
        "ema_200": row['EMA_200'],
        "ema_50": row['EMA_50'],
        "lot_size": lot_size,
        "risk_amount": RISK_PER_TRADE,
        "potential_profit": round(potential_profit, 2),
        "signal_quality": signal_quality
    }
