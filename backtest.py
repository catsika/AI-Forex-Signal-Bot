import yfinance as yf
import pandas as pd
import numpy as np
from indicators import calculate_indicators
from strategy import check_signals

# --- Configuration ---
SYMBOL = "EURUSD=X"  # Yahoo Finance symbol for EUR/USD
PERIOD = "2y"        # 2 Years of data for better testing
INTERVAL = "1h"      # 1 Hour candles
INITIAL_CAPITAL = 10000
RISK_PER_TRADE = 100 # $100 risk per trade

def run_backtest():
    print(f"\n{'='*60}")
    print(f"  ENHANCED BACKTEST: {SYMBOL}")
    print(f"  Period: {PERIOD} | Interval: {INTERVAL}")
    print(f"{'='*60}\n")
    
    # 1. Fetch Data
    print("📥 Fetching historical data...")
    df = yf.download(SYMBOL, period=PERIOD, interval=INTERVAL, progress=False)
    
    if df.empty:
        print("❌ Error: No data found.")
        return

    # Flatten MultiIndex columns if needed
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    print(f"   Loaded {len(df)} candles from {df.index[0]} to {df.index[-1]}")

    # 2. Calculate Indicators
    print("📊 Calculating enhanced indicators...")
    df = calculate_indicators(df)
    
    if df is None:
        print("❌ Error: Could not calculate indicators")
        return
    
    print(f"   ✓ EMA (20, 50, 200)")
    print(f"   ✓ RSI (14)")
    print(f"   ✓ MACD (12, 26, 9)")
    print(f"   ✓ Bollinger Bands (20, 2)")
    print(f"   ✓ ADX (14)")
    print(f"   ✓ Stochastic (14, 3, 3)")
    print(f"   ✓ Volume Analysis (OBV, VPT, Ratios)")

    # 3. Simulate Trades
    print("\n🎯 Simulating trades...")
    balance = INITIAL_CAPITAL
    peak_balance = INITIAL_CAPITAL
    max_drawdown = 0
    trades = []
    active_trade = None
    
    # Iterate through the data (skip first 250 rows for indicators to settle)
    for i in range(250, len(df)):
        current_slice = df.iloc[:i+1] 
        
        # Check for Signal
        signal = check_signals(current_slice)
        current_row = df.iloc[i]
        current_price = current_row['Close']
        current_date = df.index[i]
        atr = current_row['ATR']
        adx = current_row.get('ADX', 25)
        
        # Dynamic ATR multiplier based on trend strength
        if adx > 35:
            atr_mult = 2.0
        elif adx > 25:
            atr_mult = 1.5
        else:
            atr_mult = 1.2
        
        # --- Manage Active Trade with Trailing Stop ---
        if active_trade:
            entry_price = active_trade['entry_price']
            risk_dist = abs(entry_price - active_trade['original_sl'])
            
            if active_trade['type'] == 'BUY':
                # Check for breakeven move (when price hits 1.5x risk)
                if current_row['High'] >= entry_price + (1.5 * risk_dist):
                    # Move SL to breakeven + small profit
                    new_sl = entry_price + (0.3 * risk_dist)
                    if new_sl > active_trade['sl']:
                        active_trade['sl'] = new_sl
                
                # Trailing stop: if price moves 2x risk, trail by 1 ATR
                if current_row['High'] >= entry_price + (2 * risk_dist):
                    trailing_sl = current_row['High'] - (1.2 * atr)
                    if trailing_sl > active_trade['sl']:
                        active_trade['sl'] = trailing_sl
                
                if current_row['Low'] <= active_trade['sl']:
                    # Stopped Out (could be profit if trailing)
                    actual_exit = active_trade['sl']
                    pnl_pips = actual_exit - entry_price
                    pnl = (pnl_pips / risk_dist) * active_trade['risk']
                    balance += pnl
                    active_trade['exit_price'] = actual_exit
                    active_trade['exit_time'] = current_date
                    active_trade['pnl'] = pnl
                    active_trade['result'] = 'WIN' if pnl > 0 else 'LOSS'
                    active_trade['holding_bars'] = i - active_trade['entry_bar']
                    trades.append(active_trade)
                    active_trade = None
                elif current_row['High'] >= active_trade['tp']:
                    # Take Profit (2.5x reward)
                    pnl = active_trade['risk'] * 2.5
                    balance += pnl
                    active_trade['exit_price'] = active_trade['tp']
                    active_trade['exit_time'] = current_date
                    active_trade['pnl'] = pnl
                    active_trade['result'] = 'WIN'
                    active_trade['holding_bars'] = i - active_trade['entry_bar']
                    trades.append(active_trade)
                    active_trade = None
                    
            elif active_trade['type'] == 'SELL':
                # Check for breakeven move
                if current_row['Low'] <= entry_price - (1.5 * risk_dist):
                    new_sl = entry_price - (0.3 * risk_dist)
                    if new_sl < active_trade['sl']:
                        active_trade['sl'] = new_sl
                
                # Trailing stop
                if current_row['Low'] <= entry_price - (2 * risk_dist):
                    trailing_sl = current_row['Low'] + (1.2 * atr)
                    if trailing_sl < active_trade['sl']:
                        active_trade['sl'] = trailing_sl
                
                if current_row['High'] >= active_trade['sl']:
                    # Stopped Out
                    actual_exit = active_trade['sl']
                    pnl_pips = entry_price - actual_exit
                    pnl = (pnl_pips / risk_dist) * active_trade['risk']
                    balance += pnl
                    active_trade['exit_price'] = actual_exit
                    active_trade['exit_time'] = current_date
                    active_trade['pnl'] = pnl
                    active_trade['result'] = 'WIN' if pnl > 0 else 'LOSS'
                    active_trade['holding_bars'] = i - active_trade['entry_bar']
                    trades.append(active_trade)
                    active_trade = None
                elif current_row['Low'] <= active_trade['tp']:
                    # Take Profit (2.5x reward)
                    pnl = active_trade['risk'] * 2.5
                    balance += pnl
                    active_trade['exit_price'] = active_trade['tp']
                    active_trade['exit_time'] = current_date
                    active_trade['pnl'] = pnl
                    active_trade['result'] = 'WIN'
                    active_trade['holding_bars'] = i - active_trade['entry_bar']
                    trades.append(active_trade)
                    active_trade = None
        
        # Update peak and drawdown
        if balance > peak_balance:
            peak_balance = balance
        current_drawdown = (peak_balance - balance) / peak_balance * 100
        if current_drawdown > max_drawdown:
            max_drawdown = current_drawdown
                    
        # --- Open New Trade ---
        if signal and active_trade is None:
            if signal == "BUY":
                sl = current_price - (atr_mult * atr)
                risk_dist = current_price - sl
                tp = current_price + (2.5 * risk_dist)  # 2.5:1 R:R
                
                active_trade = {
                    'entry_time': current_date,
                    'entry_bar': i,
                    'entry_price': current_price,
                    'type': 'BUY',
                    'sl': sl,
                    'original_sl': sl,  # Keep track for trailing
                    'tp': tp,
                    'risk': RISK_PER_TRADE,
                    'rsi': current_row['RSI'],
                    'adx': current_row['ADX'],
                    'volume_ratio': current_row.get('Volume_Ratio', 1)
                }
                
            elif signal == "SELL":
                sl = current_price + (atr_mult * atr)
                risk_dist = sl - current_price
                tp = current_price - (2.5 * risk_dist)  # 2.5:1 R:R
                
                active_trade = {
                    'entry_time': current_date,
                    'entry_bar': i,
                    'entry_price': current_price,
                    'type': 'SELL',
                    'sl': sl,
                    'original_sl': sl,  # Keep track for trailing
                    'tp': tp,
                    'risk': RISK_PER_TRADE,
                    'rsi': current_row['RSI'],
                    'adx': current_row['ADX'],
                    'volume_ratio': current_row.get('Volume_Ratio', 1)
                }

    # 4. Generate Report
    print(f"\n{'='*60}")
    print("  📈 BACKTEST RESULTS")
    print(f"{'='*60}\n")
    
    total_trades = len(trades)
    if total_trades == 0:
        print("❌ No trades taken. Strategy may be too restrictive.")
        return

    wins = [t for t in trades if t['result'] == 'WIN']
    losses = [t for t in trades if t['result'] == 'LOSS']
    win_rate = (len(wins) / total_trades) * 100
    
    total_pnl = balance - INITIAL_CAPITAL
    avg_win = sum(t['pnl'] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t['pnl'] for t in losses) / len(losses) if losses else 0
    
    # Profit Factor
    gross_profit = sum(t['pnl'] for t in wins)
    gross_loss = abs(sum(t['pnl'] for t in losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    # Average holding time
    avg_holding = sum(t['holding_bars'] for t in trades) / total_trades
    
    # Trade breakdown
    buy_trades = [t for t in trades if t['type'] == 'BUY']
    sell_trades = [t for t in trades if t['type'] == 'SELL']
    buy_wins = len([t for t in buy_trades if t['result'] == 'WIN'])
    sell_wins = len([t for t in sell_trades if t['result'] == 'WIN'])
    
    print(f"  💰 Final Balance:    ${balance:,.2f}")
    print(f"  📊 Total P/L:        ${total_pnl:+,.2f} ({total_pnl/INITIAL_CAPITAL*100:+.1f}%)")
    print(f"  📉 Max Drawdown:     {max_drawdown:.1f}%")
    print()
    print(f"  🎯 Total Trades:     {total_trades}")
    print(f"  ✅ Wins:             {len(wins)} ({win_rate:.1f}%)")
    print(f"  ❌ Losses:           {len(losses)} ({100-win_rate:.1f}%)")
    print()
    print(f"  📈 Avg Win:          ${avg_win:+,.2f}")
    print(f"  📉 Avg Loss:         ${avg_loss:,.2f}")
    print(f"  ⚖️  Profit Factor:   {profit_factor:.2f}")
    print()
    print(f"  🟢 BUY Trades:       {len(buy_trades)} ({buy_wins} wins)")
    print(f"  🔴 SELL Trades:      {len(sell_trades)} ({sell_wins} wins)")
    print(f"  ⏱️  Avg Holding:     {avg_holding:.0f} bars")
    
    # Performance Rating
    print(f"\n{'='*60}")
    print("  📊 STRATEGY RATING")
    print(f"{'='*60}\n")
    
    score = 0
    if win_rate >= 50: score += 1
    if profit_factor >= 1.5: score += 1
    if max_drawdown < 20: score += 1
    if total_pnl > 0: score += 1
    if total_trades >= 20: score += 1
    
    ratings = {
        5: "⭐⭐⭐⭐⭐ EXCELLENT - Ready for live testing",
        4: "⭐⭐⭐⭐ GOOD - Minor refinements needed",
        3: "⭐⭐⭐ MODERATE - Some improvements needed",
        2: "⭐⭐ WEAK - Significant changes required",
        1: "⭐ POOR - Strategy needs rework",
        0: "❌ FAILING - Do not use"
    }
    
    print(f"  Rating: {ratings.get(score, 'Unknown')}")
    print(f"\n  Breakdown:")
    print(f"    Win Rate >= 50%:     {'✓' if win_rate >= 50 else '✗'}")
    print(f"    Profit Factor >= 1.5: {'✓' if profit_factor >= 1.5 else '✗'}")
    print(f"    Max DD < 20%:        {'✓' if max_drawdown < 20 else '✗'}")
    print(f"    Profitable:          {'✓' if total_pnl > 0 else '✗'}")
    print(f"    Enough Trades (20+): {'✓' if total_trades >= 20 else '✗'}")
    
    # Print some sample trades
    if trades:
        print(f"\n{'='*60}")
        print("  📋 SAMPLE TRADES (Last 5)")
        print(f"{'='*60}\n")
        
        for t in trades[-5:]:
            emoji = "✅" if t['result'] == 'WIN' else "❌"
            print(f"  {emoji} {t['type']} @ {t['entry_price']:.5f}")
            print(f"     Entry: {t['entry_time']}")
            print(f"     Exit:  {t['exit_time']} | P/L: ${t['pnl']:+.2f}")
            print(f"     RSI: {t['rsi']:.1f} | ADX: {t['adx']:.1f}")
            print()

if __name__ == "__main__":
    run_backtest()
