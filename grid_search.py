#!/usr/bin/env python3
"""
Fast Grid Search for EUR/USD Strategy Optimization
Optimized for speed with reduced parameter space
"""
import yfinance as yf
import pandas as pd
import numpy as np
from indicators import calculate_indicators
from itertools import product
import warnings
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing
warnings.filterwarnings('ignore')

SYMBOL = "EURUSD=X"
PERIOD = "2y"
INTERVAL = "1h"
INITIAL_CAPITAL = 20000
RISK_PER_TRADE = 50

# Global dataframe for multiprocessing
_df = None

def fetch_data():
    df = yf.download(SYMBOL, period=PERIOD, interval=INTERVAL, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = calculate_indicators(df)
    return df

def run_backtest(params):
    """Run a single backtest with given parameters"""
    adx_th, rsi_os, rsi_ob, atr_m, rr, min_s, trend_f = params
    df = _df
    
    balance = INITIAL_CAPITAL
    peak_balance = INITIAL_CAPITAL
    max_drawdown = 0
    trades = []
    active_trade = None
    
    # Pre-compute arrays for speed
    closes = df['Close'].values
    highs = df['High'].values
    lows = df['Low'].values
    atrs = df['ATR'].values
    adxs = df['ADX'].values
    rsis = df['RSI'].values
    ema50s = df['EMA_50'].values
    ema200s = df['EMA_200'].values
    macd_hists = df['MACD_Histogram'].values
    stoch_ks = df['Stoch_K'].values
    stoch_ds = df['Stoch_D'].values
    bb_pos = df['BB_Position'].values
    
    # Use EMA_20 if available, else EMA_50
    if 'EMA_20' in df.columns:
        ema20s = df['EMA_20'].values
    else:
        ema20s = ema50s
    
    for i in range(250, len(df)):
        current_price = closes[i]
        atr = atrs[i]
        
        # Manage active trade
        if active_trade:
            entry_price = active_trade['entry_price']
            risk_dist = abs(entry_price - active_trade['sl'])
            
            if active_trade['type'] == 'BUY':
                if highs[i] >= entry_price + (1.5 * risk_dist):
                    new_sl = entry_price + (0.2 * risk_dist)
                    if new_sl > active_trade['sl']:
                        active_trade['sl'] = new_sl
                        
                if lows[i] <= active_trade['sl']:
                    pnl_ratio = (active_trade['sl'] - entry_price) / risk_dist
                    pnl = pnl_ratio * RISK_PER_TRADE
                    balance += pnl
                    trades.append({'type': 'BUY', 'result': 'WIN' if pnl > 0 else 'LOSS', 'pnl': pnl})
                    active_trade = None
                elif highs[i] >= active_trade['tp']:
                    pnl = RISK_PER_TRADE * rr
                    balance += pnl
                    trades.append({'type': 'BUY', 'result': 'WIN', 'pnl': pnl})
                    active_trade = None
                    
            elif active_trade['type'] == 'SELL':
                if lows[i] <= entry_price - (1.5 * risk_dist):
                    new_sl = entry_price - (0.2 * risk_dist)
                    if new_sl < active_trade['sl']:
                        active_trade['sl'] = new_sl
                        
                if highs[i] >= active_trade['sl']:
                    pnl_ratio = (entry_price - active_trade['sl']) / risk_dist
                    pnl = pnl_ratio * RISK_PER_TRADE
                    balance += pnl
                    trades.append({'type': 'SELL', 'result': 'WIN' if pnl > 0 else 'LOSS', 'pnl': pnl})
                    active_trade = None
                elif lows[i] <= active_trade['tp']:
                    pnl = RISK_PER_TRADE * rr
                    balance += pnl
                    trades.append({'type': 'SELL', 'result': 'WIN', 'pnl': pnl})
                    active_trade = None
        
        if balance > peak_balance:
            peak_balance = balance
        current_dd = (peak_balance - balance) / peak_balance * 100
        if current_dd > max_drawdown:
            max_drawdown = current_dd
            
        if active_trade:
            continue
        if adxs[i] < adx_th:
            continue
            
        # Calculate signal
        buy_score = 0
        sell_score = 0
        price = closes[i]
        ema20 = ema20s[i]
        ema50 = ema50s[i]
        ema200 = ema200s[i]
        rsi = rsis[i]
        rsi_prev = rsis[i-1]
        macd_hist = macd_hists[i]
        macd_prev = macd_hists[i-1]
        stoch_k = stoch_ks[i]
        stoch_d = stoch_ds[i]
        stoch_k_prev = stoch_ks[i-1]
        stoch_d_prev = stoch_ds[i-1]
        bb = bb_pos[i]
        bb_prev = bb_pos[i-1]
        
        major_trend = "UP" if ema50 > ema200 else "DOWN"
        
        # EMA Alignment
        if price > ema20 > ema50 > ema200:
            buy_score += 2
        elif ema50 > ema200 and price > ema200:
            buy_score += 1
            
        if price < ema20 < ema50 < ema200:
            sell_score += 2
        elif ema50 < ema200 and price < ema200:
            sell_score += 1
        
        # RSI
        if rsi_os < rsi < 50 and rsi > rsi_prev:
            buy_score += 1.5
        elif rsi < rsi_os and rsi > rsi_prev:
            buy_score += 1
            
        if rsi_ob > rsi > 50 and rsi < rsi_prev:
            sell_score += 1.5
        elif rsi > rsi_ob and rsi < rsi_prev:
            sell_score += 1
        
        # MACD
        if macd_hist > 0:
            buy_score += 0.5
            if macd_prev <= 0:
                buy_score += 1
            elif macd_hist > macd_prev:
                buy_score += 0.5
                
        if macd_hist < 0:
            sell_score += 0.5
            if macd_prev >= 0:
                sell_score += 1
            elif macd_hist < macd_prev:
                sell_score += 0.5
        
        # Stochastic
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
        
        # Bollinger Bands
        if bb < 0.3 and bb > bb_prev:
            buy_score += 1
        if bb > 0.7 and bb < bb_prev:
            sell_score += 1
        
        # ADX bonus
        if adxs[i] > 30:
            if major_trend == "UP":
                buy_score += 0.5
            else:
                sell_score += 0.5
        
        # Final decision
        signal = None
        
        if trend_f:
            if major_trend == "UP" and buy_score >= min_s and buy_score > sell_score + 1:
                if rsi < rsi_ob:
                    signal = "BUY"
            elif major_trend == "DOWN" and sell_score >= min_s and sell_score > buy_score + 1:
                if rsi > rsi_os:
                    signal = "SELL"
        else:
            if buy_score >= min_s and buy_score > sell_score + 1.5:
                if rsi < rsi_ob:
                    signal = "BUY"
            elif sell_score >= min_s and sell_score > buy_score + 1.5:
                if rsi > rsi_os:
                    signal = "SELL"
        
        if signal:
            if signal == "BUY":
                sl = current_price - (atr_m * atr)
                risk_dist = current_price - sl
                tp = current_price + (rr * risk_dist)
            else:
                sl = current_price + (atr_m * atr)
                risk_dist = sl - current_price
                tp = current_price - (rr * risk_dist)
                
            active_trade = {
                'entry_price': current_price,
                'type': signal,
                'sl': sl,
                'tp': tp,
            }
    
    total_trades = len(trades)
    if total_trades < 15:  # Reduced minimum
        return None
    
    wins = [t for t in trades if t['result'] == 'WIN']
    win_rate = (len(wins) / total_trades) * 100
    total_pnl = balance - INITIAL_CAPITAL
    
    gross_profit = sum(t['pnl'] for t in wins)
    gross_loss = abs(sum(t['pnl'] for t in trades if t['result'] == 'LOSS'))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
    
    buy_trades = len([t for t in trades if t['type'] == 'BUY'])
    sell_trades = len([t for t in trades if t['type'] == 'SELL'])
    
    return {
        'adx_th': adx_th,
        'rsi_os': rsi_os,
        'rsi_ob': rsi_ob,
        'atr_m': atr_m,
        'rr': rr,
        'min_s': min_s,
        'trend_f': trend_f,
        'trades': total_trades,
        'buy_trades': buy_trades,
        'sell_trades': sell_trades,
        'win_rate': win_rate,
        'pnl': total_pnl,
        'max_dd': max_drawdown,
        'profit_factor': profit_factor
    }


def main():
    global _df
    
    print("\n" + "="*70)
    print("  ⚡ FAST GRID SEARCH - EUR/USD")
    print("  Optimized parameter search...")
    print("="*70 + "\n")
    
    _df = fetch_data()
    print(f"📥 Loaded {len(_df)} candles\n")
    
    # Reduced parameter grid for speed
    adx_thresholds = [20, 25, 30]
    rsi_oversolds = [30, 35]
    rsi_overboughts = [65, 70]
    atr_mults = [1.5, 2.0, 2.5]
    rr_ratios = [2.0, 2.5, 3.0]
    min_scores = [4.0, 4.5, 5.0]
    trend_filters = [True, False]
    
    # Generate all combinations
    all_params = list(product(
        adx_thresholds, rsi_oversolds, rsi_overboughts,
        atr_mults, rr_ratios, min_scores, trend_filters
    ))
    
    total_combinations = len(all_params)
    print(f"🧪 Testing {total_combinations} parameter combinations...\n")
    
    results = []
    for idx, params in enumerate(all_params):
        result = run_backtest(params)
        if result:
            results.append(result)
        if (idx + 1) % 50 == 0:
            print(f"   Progress: {idx + 1}/{total_combinations} ({len(results)} valid)")
    
    print(f"\n✅ Completed! {len(results)} valid strategies found.\n")
    
    if not results:
        print("❌ No strategies met minimum criteria.")
        return
    
    # Sort by profit factor and profit
    profitable = [r for r in results if r['pnl'] > 0 and r['profit_factor'] > 1.1]
    profitable.sort(key=lambda x: (x['profit_factor'], x['pnl'], -x['max_dd']), reverse=True)
    
    print("="*70)
    print("  🏆 TOP 10 STRATEGIES")
    print("="*70 + "\n")
    
    for i, r in enumerate(profitable[:10], 1):
        tf_str = "Trend" if r['trend_f'] else "Both"
        print(f"{i}. ADX>{r['adx_th']} | RSI {r['rsi_os']}-{r['rsi_ob']} | ATR {r['atr_m']}x | RR {r['rr']} | Score>{r['min_s']} | {tf_str}")
        print(f"   P/L: ${r['pnl']:+,.2f} | WR: {r['win_rate']:.1f}% | PF: {r['profit_factor']:.2f} | DD: {r['max_dd']:.1f}% | Trades: {r['trades']}")
        print()
    
    # Best overall
    if profitable:
        best = profitable[0]
        print("="*70)
        print("  🥇 BEST CONFIGURATION")
        print("="*70)
        tf_str = "Trend-Following Only" if best['trend_f'] else "Both Directions"
        print(f"""
   Parameters:
   - ADX Threshold:     {best['adx_th']}
   - RSI Oversold:      {best['rsi_os']}
   - RSI Overbought:    {best['rsi_ob']}
   - ATR Multiplier:    {best['atr_m']}
   - Risk:Reward:       1:{best['rr']}
   - Min Score:         {best['min_s']}
   - Mode:              {tf_str}

   Results:
   - Total Trades:      {best['trades']}
   - Buy/Sell:          {best['buy_trades']}/{best['sell_trades']}
   - Win Rate:          {best['win_rate']:.1f}%
   - Profit/Loss:       ${best['pnl']:+,.2f}
   - Profit Factor:     {best['profit_factor']:.2f}
   - Max Drawdown:      {best['max_dd']:.1f}%
""")


if __name__ == "__main__":
    main()
