from config import RISK_PER_TRADE
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

def check_signals(df):
    """
    IMPROVED Signal Detection with STRICT Multiple Confirmations.
    
    Key Improvements:
    - Higher minimum score (5.5+) for entries
    - Stronger trend alignment requirements
    - Better volatility filtering
    - Avoid choppy markets (low ADX)
    - Better RSI timing for entries
    
    BUY Signal Requirements (need 5.5+ score):
    1. TREND ALIGNMENT: Price > EMA_50 > EMA_200 (strong uptrend)
    2. RSI TIMING: Coming out of oversold (30-45) with upward momentum
    3. MACD: Histogram positive AND increasing
    4. STOCHASTIC: Bullish cross in oversold zone
    5. ADX: > 25 (confirmed trending market)
    6. VOLUME: Confirms the move (above average)
    7. BOLLINGER: Price bouncing from lower half
    8. PRICE ACTION: Not extended too far from EMA
    """
    if df is None or df.empty:
        return None

    try:
        current = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else current
        prev2 = df.iloc[-3] if len(df) > 2 else prev
        
        # Check for required columns
        required_cols = ['EMA_50', 'EMA_200', 'RSI', 'MACD_Histogram', 
                        'ADX', 'Stoch_K', 'Stoch_D', 'BB_Position', 'OBV_Trend', 'ATR']
        for col in required_cols:
            if col not in df.columns or pd.isna(current[col]):
                logger.warning(f"Missing indicator: {col}")
                return None
        
        # === PRE-FILTERS (Skip low-quality setups) ===
        
        # 1. Skip ranging/choppy markets
        if current['ADX'] < 20:
            logger.debug("Skipped: Market is ranging (ADX < 20)")
            return None
            
        # 2. Skip extreme RSI (wait for pullback)
        if current['RSI'] > 75 or current['RSI'] < 25:
            logger.debug("Skipped: RSI at extreme levels")
            return None
            
        # 3. Skip if price extended too far from EMA50 (mean reversion risk)
        price = current['Close']
        ema50 = current['EMA_50']
        atr = current['ATR']
        extension = abs(price - ema50) / atr
        if extension > 3.0:  # More than 3 ATR from EMA50
            logger.debug(f"Skipped: Price too extended from EMA50 ({extension:.1f} ATR)")
            return None
        
        # === CALCULATE CONFIRMATIONS ===
        buy_score = 0
        sell_score = 0
        confirmations = {'buy': [], 'sell': []}
        
        # 1. STRONG TREND ALIGNMENT (Price action + EMAs)
        ema20 = current.get('EMA_20', current['EMA_50'])
        
        # Bullish: Price > EMA20 > EMA50 > EMA200
        if price > ema20 > current['EMA_50'] > current['EMA_200']:
            buy_score += 2.5
            confirmations['buy'].append("Perfect Bullish Alignment")
        elif current['EMA_50'] > current['EMA_200'] and price > current['EMA_200']:
            buy_score += 1.5
            confirmations['buy'].append("Uptrend (EMA50>200)")
        elif current['EMA_50'] < current['EMA_200']:
            # Don't fight the trend
            buy_score -= 2
            
        # Bearish: Price < EMA20 < EMA50 < EMA200    
        if price < ema20 < current['EMA_50'] < current['EMA_200']:
            sell_score += 2.5
            confirmations['sell'].append("Perfect Bearish Alignment")
        elif current['EMA_50'] < current['EMA_200'] and price < current['EMA_200']:
            sell_score += 1.5
            confirmations['sell'].append("Downtrend (EMA50<200)")
        elif current['EMA_50'] > current['EMA_200']:
            sell_score -= 2
            
        # 2. RSI TIMING (Buy on rising from oversold, Sell on falling from overbought)
        rsi = current['RSI']
        rsi_prev = prev['RSI']
        rsi_prev2 = prev2['RSI']
        
        # BUY: RSI was oversold and now recovering
        if rsi > rsi_prev > rsi_prev2 and rsi < 50 and rsi_prev < 40:
            buy_score += 1.5
            confirmations['buy'].append(f"RSI Recovering ({rsi:.1f})")
        elif 35 < rsi < 50 and rsi > rsi_prev:
            buy_score += 0.5
            
        # SELL: RSI was overbought and now falling
        if rsi < rsi_prev < rsi_prev2 and rsi > 50 and rsi_prev > 60:
            sell_score += 1.5
            confirmations['sell'].append(f"RSI Falling ({rsi:.1f})")
        elif 50 < rsi < 65 and rsi < rsi_prev:
            sell_score += 0.5
            
        # 3. MACD MOMENTUM (Not just positive, but increasing)
        macd_hist = current['MACD_Histogram']
        macd_prev = prev['MACD_Histogram']
        macd_prev2 = prev2['MACD_Histogram']
        
        if macd_hist > 0 and macd_hist > macd_prev:
            buy_score += 1.5
            if macd_prev < 0:  # Fresh bullish cross
                buy_score += 0.5
                confirmations['buy'].append("Fresh MACD Bull Cross")
            else:
                confirmations['buy'].append("MACD Bullish & Rising")
        elif macd_hist > 0:
            buy_score += 0.3
                
        if macd_hist < 0 and macd_hist < macd_prev:
            sell_score += 1.5
            if macd_prev > 0:  # Fresh bearish cross
                sell_score += 0.5
                confirmations['sell'].append("Fresh MACD Bear Cross")
            else:
                confirmations['sell'].append("MACD Bearish & Falling")
        elif macd_hist < 0:
            sell_score += 0.3
                
        # 4. STOCHASTIC CROSS IN OVERSOLD/OVERBOUGHT
        stoch_k = current['Stoch_K']
        stoch_d = current['Stoch_D']
        stoch_k_prev = prev['Stoch_K']
        stoch_d_prev = prev['Stoch_D']
        
        # Bullish: K crosses above D in oversold zone
        if stoch_k > stoch_d and stoch_k_prev <= stoch_d_prev and stoch_k < 30:
            buy_score += 1.5
            confirmations['buy'].append(f"Stoch Bull Cross ({stoch_k:.0f})")
        elif stoch_k < 40 and stoch_k > stoch_k_prev:
            buy_score += 0.5
            
        # Bearish: K crosses below D in overbought zone
        if stoch_k < stoch_d and stoch_k_prev >= stoch_d_prev and stoch_k > 70:
            sell_score += 1.5
            confirmations['sell'].append(f"Stoch Bear Cross ({stoch_k:.0f})")
        elif stoch_k > 60 and stoch_k < stoch_k_prev:
            sell_score += 0.5
            
        # 5. ADX TREND STRENGTH (Only trade strong trends)
        adx = current['ADX']
        plus_di = current.get('+DI', 25)
        minus_di = current.get('-DI', 25)
        
        if adx > 30:
            # Strong trend - add confirmation based on DI direction
            if plus_di > minus_di:
                buy_score += 1.0
                confirmations['buy'].append(f"Strong Bullish ADX ({adx:.0f})")
            else:
                sell_score += 1.0
                confirmations['sell'].append(f"Strong Bearish ADX ({adx:.0f})")
        elif adx > 25:
            if plus_di > minus_di:
                buy_score += 0.5
            else:
                sell_score += 0.5
                
        # 6. VOLUME CONFIRMATION (Must confirm the move)
        volume_ratio = current.get('Volume_Ratio', 1)
        obv_trend = current.get('OBV_Trend', 0)
        vpt_trend = current.get('VPT_Trend', 0)
        
        if obv_trend == 1 and volume_ratio > 1.2:
            buy_score += 1.0
            confirmations['buy'].append(f"Volume Confirms ({volume_ratio:.1f}x)")
        elif obv_trend == 1:
            buy_score += 0.3
            
        if obv_trend == -1 and volume_ratio > 1.2:
            sell_score += 1.0
            confirmations['sell'].append(f"Volume Confirms ({volume_ratio:.1f}x)")
        elif obv_trend == -1:
            sell_score += 0.3
            
        # Penalize divergence (price up but volume down)
        if obv_trend == -1 and rsi > rsi_prev:
            buy_score -= 0.5
        if obv_trend == 1 and rsi < rsi_prev:
            sell_score -= 0.5
                
        # 7. BOLLINGER BANDS POSITION (Entry timing)
        bb_pos = current['BB_Position']
        bb_pos_prev = prev['BB_Position']
        
        # Buy when price bouncing from lower band
        if bb_pos < 0.3 and bb_pos > bb_pos_prev:
            buy_score += 1.0
            confirmations['buy'].append(f"BB Bounce Lower ({bb_pos:.2f})")
        elif bb_pos < 0.4:
            buy_score += 0.3
            
        # Sell when price falling from upper band
        if bb_pos > 0.7 and bb_pos < bb_pos_prev:
            sell_score += 1.0
            confirmations['sell'].append(f"BB Rejection Upper ({bb_pos:.2f})")
        elif bb_pos > 0.6:
            sell_score += 0.3
            
        # 8. MOMENTUM SCORE (Composite momentum)
        mom_score = current.get('Momentum_Score', 0)
        if mom_score > 40:
            buy_score += 0.5
        elif mom_score < -40:
            sell_score += 0.5
            
        # === FINAL DECISION ===
        MIN_SCORE = 6.0  # Raised further for higher quality trades
        MIN_CONFIRMATIONS = 4  # Need at least 4 named confirmations
        
        logger.info(f"Signal Scores - BUY: {buy_score:.1f}, SELL: {sell_score:.1f}")
        logger.info(f"Buy Confirmations ({len(confirmations['buy'])}): {confirmations['buy']}")
        logger.info(f"Sell Confirmations ({len(confirmations['sell'])}): {confirmations['sell']}")
        
        if buy_score >= MIN_SCORE and len(confirmations['buy']) >= MIN_CONFIRMATIONS:
            if buy_score > sell_score + 2.0:  # Clear directional bias (stronger)
                # Final safety checks
                if current['EMA_50'] < current['EMA_200']:
                    logger.info("BUY rejected: Not in uptrend")
                    return None
                if rsi > 65:
                    logger.info("BUY rejected: RSI too high")
                    return None
                if adx < 22:
                    logger.info("BUY rejected: Trend too weak")
                    return None
                return "BUY"
                
        if sell_score >= MIN_SCORE and len(confirmations['sell']) >= MIN_CONFIRMATIONS:
            if sell_score > buy_score + 2.0:  # Clear directional bias (stronger)
                # Final safety checks
                if current['EMA_50'] > current['EMA_200']:
                    logger.info("SELL rejected: Not in downtrend")
                    return None
                if rsi < 35:
                    logger.info("SELL rejected: RSI too low")
                    return None
                if adx < 22:
                    logger.info("SELL rejected: Trend too weak")
                    return None
                return "SELL"
            
        return None
        
    except Exception as e:
        logger.error(f"Error in check_signals: {e}")
        return None


def calculate_lot_size(symbol, entry_price, sl_price):
    """
    Calculate lot size based on fixed risk amount.
    """
    risk_amount = RISK_PER_TRADE
    distance = abs(entry_price - sl_price)
    
    if distance == 0:
        return 0.01  # Minimum lot size

    lot_size = 0.0
    
    # Gold (GC=F or XAUUSD)
    if "GC=F" in symbol or "XAU" in symbol:
        lot_size = risk_amount / (100 * distance)
        
    # Forex (EURUSD)
    elif "EURUSD" in symbol or "USD" in symbol:
        lot_size = risk_amount / (100000 * distance)
        
    # Crypto (BTC-USD)
    elif "BTC" in symbol:
        lot_size = risk_amount / distance
        
    else:
        # Default Forex calculation
        lot_size = risk_amount / (100000 * distance)
        
    return max(0.01, round(lot_size, 2))


def calculate_trade_params(signal, row, symbol):
    """
    Enhanced trade parameters with dynamic SL/TP based on volatility.
    
    SL: Based on ATR multiplier (adaptive to volatility)
    TP: 1:2 Risk-to-Reward ratio
    """
    price = row['Close']
    atr = row['ATR']
    adx = row.get('ADX', 25)
    
    # Dynamic ATR multiplier based on trend strength
    if adx > 35:
        atr_mult = 2.0  # Strong trend = wider stops
    elif adx > 25:
        atr_mult = 1.5  # Normal trend
    else:
        atr_mult = 1.2  # Ranging market = tighter stops
    
    if signal == "BUY":
        # SL below recent swing low
        sl_price = row['Low'] - (atr_mult * atr)
        risk = price - sl_price
        tp_price = price + (2 * risk)  # 1:2 RR
        
        # Entry zone (small buffer for limit order)
        buffer_amount = price * 0.0003  # 0.03%
        entry_min = price - buffer_amount
        entry_max = price + buffer_amount
        
    elif signal == "SELL":
        # SL above recent swing high
        sl_price = row['High'] + (atr_mult * atr)
        risk = sl_price - price
        tp_price = price - (2 * risk)  # 1:2 RR
        
        buffer_amount = price * 0.0003
        entry_max = price + buffer_amount
        entry_min = price - buffer_amount
    
    # Calculate Lot Size
    lot_size = calculate_lot_size(symbol, price, sl_price)
    
    # Calculate Potential Profit
    tp_dist = abs(tp_price - price)
    
    if "GC=F" in symbol or "XAU" in symbol:
        potential_profit = lot_size * 100 * tp_dist
    elif "EURUSD" in symbol or "USD" in symbol:
        potential_profit = lot_size * 100000 * tp_dist
    elif "BTC" in symbol:
        potential_profit = lot_size * tp_dist
    else:
        potential_profit = lot_size * 100000 * tp_dist
    
    # Gather signal quality indicators
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
        "atr_multiplier": atr_mult,
        "rsi": row['RSI'],
        "ema_200": row['EMA_200'],
        "ema_50": row['EMA_50'],
        "lot_size": lot_size,
        "risk_amount": RISK_PER_TRADE,
        "potential_profit": round(potential_profit, 2),
        "signal_quality": signal_quality
    }
