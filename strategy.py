from config import RISK_PER_TRADE
import pandas as pd

def check_signals(df):
    """
    Long: Close > 200 EMA AND RSI < 33
    Short: Close < 200 EMA AND RSI > 67
    """
    if df is None or df.empty:
        return None

    current = df.iloc[-1]
    
    if pd.isna(current['EMA_200']) or pd.isna(current['RSI']):
        return None

    signal = None
    
    # Long Condition
    if current['Close'] > current['EMA_200'] and current['RSI'] < 33:
        signal = "BUY"
    
    # Short Condition
    elif current['Close'] < current['EMA_200'] and current['RSI'] > 67:
        signal = "SELL"
        
    return signal

def calculate_lot_size(symbol, entry_price, sl_price):
    """
    Calculate lot size based on fixed risk amount.
    """
    risk_amount = RISK_PER_TRADE
    distance = abs(entry_price - sl_price)
    
    if distance == 0:
        return 0.0

    lot_size = 0.0
    
    # Gold (GC=F or XAUUSD)
    if "GC=F" in symbol or "XAU" in symbol:
        # 1 Lot = 100 oz. $1 move = $100 PnL per lot.
        # Risk = Lot * 100 * Distance
        # Lot = Risk / (100 * Distance)
        lot_size = risk_amount / (100 * distance)
        
    # Forex (EURUSD)
    elif "EURUSD" in symbol:
        # Standard Lot (1.0) = 100,000 units.
        # $10 per pip (0.0001).
        # Risk = Lot * 100,000 * Distance
        # Lot = Risk / (100,000 * Distance)
        lot_size = risk_amount / (100000 * distance)
        
    # Crypto (BTC-USD)
    elif "BTC" in symbol:
        # 1 Lot = 1 BTC.
        # Risk = Lot * Distance
        # Lot = Risk / Distance
        lot_size = risk_amount / distance
        
    return round(lot_size, 2)

def calculate_trade_params(signal, row, symbol):
    """
    SL: Current Low - (1.5 * ATR) for Buy; Current High + (1.5 * ATR) for Sell.
    Entry Buffer: 0.05% movement.
    TP: 1:2 Risk-to-Reward.
    """
    price = row['Close']
    atr = row['ATR']
    
    if signal == "BUY":
        sl_price = row['Low'] - (1.5 * atr)
        risk = price - sl_price
        tp_price = price + (2 * risk)
        
        buffer_amount = price * 0.0005
        entry_min = price
        entry_max = price + buffer_amount
        
    elif signal == "SELL":
        sl_price = row['High'] + (1.5 * atr)
        risk = sl_price - price
        tp_price = price - (2 * risk)
        
        buffer_amount = price * 0.0005
        entry_max = price
        entry_min = price - buffer_amount
    
    # Calculate Lot Size
    # Use 'price' as approximate entry for calculation
    lot_size = calculate_lot_size(symbol, price, sl_price)
    
    # Calculate Potential Profit (based on Lot Size rounding)
    potential_profit = 0.0
    tp_dist = abs(tp_price - price)
    
    if "GC=F" in symbol or "XAU" in symbol:
        potential_profit = lot_size * 100 * tp_dist
    elif "EURUSD" in symbol:
        potential_profit = lot_size * 100000 * tp_dist
    elif "BTC" in symbol:
        potential_profit = lot_size * tp_dist
        
    return {
        "price": price,
        "sl": sl_price,
        "tp": tp_price,
        "entry_min": entry_min,
        "entry_max": entry_max,
        "atr": atr,
        "rsi": row['RSI'],
        "ema_200": row['EMA_200'],
        "lot_size": lot_size,
        "risk_amount": RISK_PER_TRADE,
        "potential_profit": round(potential_profit, 2)
    }
