#!/usr/bin/env python3
"""
Deep Strategy Optimizer for EUR/USD
Tests multiple configurations to find optimal parameters
"""
import yfinance as yf
import pandas as pd
import numpy as np
from indicators import calculate_indicators
import warnings
warnings.filterwarnings('ignore')

# Configuration
SYMBOL = "EURUSD=X"
PERIOD = "2y"
INTERVAL = "1h"
INITIAL_CAPITAL = 20000
RISK_PER_TRADE = 50

def fetch_data():
    """Fetch and prepare data"""
    df = yf.download(SYMBOL, period=PERIOD, interval=INTERVAL, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = calculate_indicators(df)
    return df

def run_strategy_test(df, params, name="Test"):
    """
    Run a strategy with given parameters
    """
    balance = INITIAL_CAPITAL
    peak_balance = INITIAL_CAPITAL
    max_drawdown = 0
    trades = []
    active_trade = None
    
    adx_threshold = params.get('adx_threshold', 20)
    rsi_oversold = params.get('rsi_oversold', 35)
    rsi_overbought = params.get('rsi_overbought', 65)
    atr_mult = params.get('atr_mult', 1.5)
    rr_ratio = params.get('rr_ratio', 2.0)
    min_score = params.get('min_score', 4.0)
    trend_filter = params.get('trend_filter', True)
    use_macd_cross = params.get('use_macd_cross', True)
    use_rsi_zones = params.get('use_rsi_zones', True)
    use_stoch_cross = params.get('use_stoch_cross', True)
    use_bb_bounce = params.get('use_bb_bounce', True)
    allow_counter_trend = params.get('allow_counter_trend', False)
    
    for i in range(250, len(df)):
        current = df.iloc[i]
        prev = df.iloc[i-1]
        prev2 = df.iloc[i-2]
        current_date = df.index[i]
        current_price = current['Close']
        atr = current['ATR']
        
        # Manage active trade
        if active_trade:
            entry_price = active_trade['entry_price']
            risk_dist = abs(entry_price - active_trade['sl'])
            
            if active_trade['type'] == 'BUY':
                # Trailing stop
                if current['High'] >= entry_price + (1.5 * risk_dist):
                    new_sl = entry_price + (0.2 * risk_dist)
                    if new_sl > active_trade['sl']:
                        active_trade['sl'] = new_sl
                        
                if current['Low'] <= active_trade['sl']:
                    pnl_ratio = (active_trade['sl'] - entry_price) / risk_dist
                    pnl = pnl_ratio * active_trade['risk']
                    balance += pnl
                    active_trade['pnl'] = pnl
                    active_trade['result'] = 'WIN' if pnl > 0 else 'LOSS'
                    trades.append(active_trade)
                    active_trade = None
                elif current['High'] >= active_trade['tp']:
                    pnl = active_trade['risk'] * rr_ratio
                    balance += pnl
                    active_trade['pnl'] = pnl
                    active_trade['result'] = 'WIN'
                    trades.append(active_trade)
                    active_trade = None
                    
            elif active_trade['type'] == 'SELL':
                if current['Low'] <= entry_price - (1.5 * risk_dist):
                    new_sl = entry_price - (0.2 * risk_dist)
                    if new_sl < active_trade['sl']:
                        active_trade['sl'] = new_sl
                        
                if current['High'] >= active_trade['sl']:
                    pnl_ratio = (entry_price - active_trade['sl']) / risk_dist
                    pnl = pnl_ratio * active_trade['risk']
                    balance += pnl
                    active_trade['pnl'] = pnl
                    active_trade['result'] = 'WIN' if pnl > 0 else 'LOSS'
                    trades.append(active_trade)
                    active_trade = None
                elif current['Low'] <= active_trade['tp']:
                    pnl = active_trade['risk'] * rr_ratio
                    balance += pnl
                    active_trade['pnl'] = pnl
                    active_trade['result'] = 'WIN'
                    trades.append(active_trade)
                    active_trade = None
        
        # Update drawdown
        if balance > peak_balance:
            peak_balance = balance
        current_dd = (peak_balance - balance) / peak_balance * 100
        if current_dd > max_drawdown:
            max_drawdown = current_dd
            
        # Skip if trade active or ADX too low
        if active_trade:
            continue
        if current['ADX'] < adx_threshold:
            continue
            
        # Calculate signal
        buy_score = 0
        sell_score = 0
        price = current['Close']
        ema20 = current.get('EMA_20', current['EMA_50'])
        ema50 = current['EMA_50']
        ema200 = current['EMA_200']
        
        # Trend analysis
        major_trend = "UP" if ema50 > ema200 else "DOWN"
        minor_trend = "UP" if price > ema50 else "DOWN"
        
        # 1. EMA Alignment
        if price > ema20 > ema50 > ema200:
            buy_score += 2
        elif ema50 > ema200 and price > ema200:
            buy_score += 1
            
        if price < ema20 < ema50 < ema200:
            sell_score += 2
        elif ema50 < ema200 and price < ema200:
            sell_score += 1
        
        # 2. RSI
        rsi = current['RSI']
        rsi_prev = prev['RSI']
        
        if use_rsi_zones:
            if rsi_oversold < rsi < 50 and rsi > rsi_prev:
                buy_score += 1.5
            elif rsi < rsi_oversold and rsi > rsi_prev:
                buy_score += 1  # Recovery from oversold
                
            if rsi_overbought > rsi > 50 and rsi < rsi_prev:
                sell_score += 1.5
            elif rsi > rsi_overbought and rsi < rsi_prev:
                sell_score += 1  # Falling from overbought
        
        # 3. MACD
        macd_hist = current['MACD_Histogram']
        macd_prev = prev['MACD_Histogram']
        
        if use_macd_cross:
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
        
        # 4. Stochastic
        stoch_k = current['Stoch_K']
        stoch_d = current['Stoch_D']
        stoch_k_prev = prev['Stoch_K']
        stoch_d_prev = prev['Stoch_D']
        
        if use_stoch_cross:
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
        
        # 5. Bollinger Bands
        bb_pos = current['BB_Position']
        bb_prev = prev['BB_Position']
        
        if use_bb_bounce:
            if bb_pos < 0.3 and bb_pos > bb_prev:
                buy_score += 1
            if bb_pos > 0.7 and bb_pos < bb_prev:
                sell_score += 1
        
        # 6. ADX strength bonus
        adx = current['ADX']
        if adx > 30:
            if major_trend == "UP":
                buy_score += 0.5
            else:
                sell_score += 0.5
        
        # Final decision
        signal = None
        
        if trend_filter:
            # Only trade with trend
            if major_trend == "UP" and buy_score >= min_score and buy_score > sell_score + 1:
                if rsi < rsi_overbought:
                    signal = "BUY"
            elif major_trend == "DOWN" and sell_score >= min_score and sell_score > buy_score + 1:
                if rsi > rsi_oversold:
                    signal = "SELL"
        else:
            # Trade any direction
            if buy_score >= min_score and buy_score > sell_score + 1.5:
                if rsi < rsi_overbought:
                    signal = "BUY"
            elif sell_score >= min_score and sell_score > buy_score + 1.5:
                if rsi > rsi_oversold:
                    signal = "SELL"
        
        # Allow counter-trend with higher threshold
        if allow_counter_trend and signal is None:
            counter_min = min_score + 1.5
            if major_trend == "DOWN" and buy_score >= counter_min:
                if rsi < 45 and bb_pos < 0.3:
                    signal = "BUY"
            elif major_trend == "UP" and sell_score >= counter_min:
                if rsi > 55 and bb_pos > 0.7:
                    signal = "SELL"
        
        # Open trade
        if signal:
            if signal == "BUY":
                sl = current_price - (atr_mult * atr)
                risk_dist = current_price - sl
                tp = current_price + (rr_ratio * risk_dist)
            else:
                sl = current_price + (atr_mult * atr)
                risk_dist = sl - current_price
                tp = current_price - (rr_ratio * risk_dist)
                
            active_trade = {
                'entry_time': current_date,
                'entry_price': current_price,
                'type': signal,
                'sl': sl,
                'tp': tp,
                'risk': RISK_PER_TRADE,
            }
    
    # Calculate results
    total_trades = len(trades)
    if total_trades == 0:
        return {
            'name': name,
            'trades': 0,
            'win_rate': 0,
            'pnl': 0,
            'max_dd': 0,
            'profit_factor': 0,
            'score': 0
        }
    
    wins = [t for t in trades if t['result'] == 'WIN']
    win_rate = (len(wins) / total_trades) * 100
    total_pnl = balance - INITIAL_CAPITAL
    
    gross_profit = sum(t['pnl'] for t in wins)
    gross_loss = abs(sum(t['pnl'] for t in trades if t['result'] == 'LOSS'))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    buy_trades = len([t for t in trades if t['type'] == 'BUY'])
    sell_trades = len([t for t in trades if t['type'] == 'SELL'])
    
    # Calculate quality score
    score = 0
    if win_rate >= 45: score += 1
    if win_rate >= 50: score += 1
    if profit_factor >= 1.2: score += 1
    if profit_factor >= 1.5: score += 2
    if max_drawdown < 15: score += 1
    if max_drawdown < 10: score += 1
    if total_pnl > 0: score += 2
    if total_trades >= 30: score += 1
    if 0.3 < buy_trades / max(total_trades, 1) < 0.7: score += 1  # Balanced trades
    
    return {
        'name': name,
        'trades': total_trades,
        'buy_trades': buy_trades,
        'sell_trades': sell_trades,
        'wins': len(wins),
        'win_rate': win_rate,
        'pnl': total_pnl,
        'max_dd': max_drawdown,
        'profit_factor': profit_factor,
        'score': score,
        'balance': balance
    }


def main():
    print("\n" + "="*70)
    print("  EUR/USD STRATEGY OPTIMIZER")
    print("  Finding optimal parameters for consistent profitability")
    print("="*70 + "\n")
    
    print("📥 Loading data...")
    df = fetch_data()
    print(f"   ✓ Loaded {len(df)} candles\n")
    
    # Define strategies to test
    strategies = [
        # Strategy 1: Original (baseline)
        {
            'name': '1. Current Strategy (Baseline)',
            'params': {
                'adx_threshold': 18,
                'rsi_oversold': 28,
                'rsi_overbought': 72,
                'atr_mult': 1.5,
                'rr_ratio': 2.5,
                'min_score': 6.0,
                'trend_filter': True,
            }
        },
        # Strategy 2: Lower thresholds for more trades
        {
            'name': '2. Lower Score Threshold',
            'params': {
                'adx_threshold': 18,
                'rsi_oversold': 30,
                'rsi_overbought': 70,
                'atr_mult': 1.5,
                'rr_ratio': 2.0,
                'min_score': 4.0,
                'trend_filter': True,
            }
        },
        # Strategy 3: Aggressive RSI zones
        {
            'name': '3. Wider RSI Zones',
            'params': {
                'adx_threshold': 20,
                'rsi_oversold': 35,
                'rsi_overbought': 65,
                'atr_mult': 1.5,
                'rr_ratio': 2.0,
                'min_score': 4.5,
                'trend_filter': True,
            }
        },
        # Strategy 4: Allow counter-trend
        {
            'name': '4. With Counter-Trend Trades',
            'params': {
                'adx_threshold': 20,
                'rsi_oversold': 35,
                'rsi_overbought': 65,
                'atr_mult': 1.5,
                'rr_ratio': 2.0,
                'min_score': 4.5,
                'trend_filter': True,
                'allow_counter_trend': True,
            }
        },
        # Strategy 5: Tighter stops, 1.5:1 RR
        {
            'name': '5. Tighter Stops (1.5 RR)',
            'params': {
                'adx_threshold': 18,
                'rsi_oversold': 35,
                'rsi_overbought': 65,
                'atr_mult': 1.2,
                'rr_ratio': 1.5,
                'min_score': 4.0,
                'trend_filter': True,
            }
        },
        # Strategy 6: No trend filter (both directions)
        {
            'name': '6. No Trend Filter',
            'params': {
                'adx_threshold': 22,
                'rsi_oversold': 35,
                'rsi_overbought': 65,
                'atr_mult': 1.5,
                'rr_ratio': 2.0,
                'min_score': 5.0,
                'trend_filter': False,
            }
        },
        # Strategy 7: MACD + RSI Focus
        {
            'name': '7. MACD + RSI Focus',
            'params': {
                'adx_threshold': 18,
                'rsi_oversold': 40,
                'rsi_overbought': 60,
                'atr_mult': 1.5,
                'rr_ratio': 2.0,
                'min_score': 3.5,
                'trend_filter': True,
                'use_stoch_cross': False,
                'use_bb_bounce': False,
            }
        },
        # Strategy 8: Higher ADX requirement
        {
            'name': '8. Strong Trends Only (ADX>25)',
            'params': {
                'adx_threshold': 25,
                'rsi_oversold': 35,
                'rsi_overbought': 65,
                'atr_mult': 1.8,
                'rr_ratio': 2.5,
                'min_score': 4.0,
                'trend_filter': True,
            }
        },
        # Strategy 9: Conservative with wider stops
        {
            'name': '9. Wider Stops (2.0 ATR)',
            'params': {
                'adx_threshold': 20,
                'rsi_oversold': 35,
                'rsi_overbought': 65,
                'atr_mult': 2.0,
                'rr_ratio': 2.0,
                'min_score': 4.0,
                'trend_filter': True,
            }
        },
        # Strategy 10: Balanced approach
        {
            'name': '10. Balanced Optimal',
            'params': {
                'adx_threshold': 20,
                'rsi_oversold': 38,
                'rsi_overbought': 62,
                'atr_mult': 1.5,
                'rr_ratio': 2.0,
                'min_score': 4.0,
                'trend_filter': True,
                'allow_counter_trend': True,
            }
        },
    ]
    
    results = []
    
    print("🧪 Testing strategies...\n")
    
    for s in strategies:
        result = run_strategy_test(df, s['params'], s['name'])
        results.append(result)
        
        emoji = "✅" if result['pnl'] > 0 else "❌"
        print(f"{emoji} {result['name']}")
        print(f"   Trades: {result['trades']} (Buy: {result.get('buy_trades', 0)}, Sell: {result.get('sell_trades', 0)})")
        print(f"   Win Rate: {result['win_rate']:.1f}% | P/L: ${result['pnl']:+,.2f}")
        print(f"   Profit Factor: {result['profit_factor']:.2f} | Max DD: {result['max_dd']:.1f}%")
        print(f"   Score: {result['score']}/11\n")
    
    # Sort by score and P/L
    results.sort(key=lambda x: (x['score'], x['pnl']), reverse=True)
    
    print("="*70)
    print("  📊 RANKED RESULTS (Best to Worst)")
    print("="*70 + "\n")
    
    for i, r in enumerate(results, 1):
        stars = "⭐" * min(r['score'], 5)
        print(f"{i}. {r['name']}")
        print(f"   {stars} Score: {r['score']}/11")
        print(f"   P/L: ${r['pnl']:+,.2f} | Win Rate: {r['win_rate']:.1f}% | PF: {r['profit_factor']:.2f}")
        print()
    
    # Best strategy
    best = results[0]
    print("="*70)
    print(f"  🏆 BEST STRATEGY: {best['name']}")
    print("="*70)
    print(f"\n   Final Balance: ${best['balance']:,.2f}")
    print(f"   Total P/L: ${best['pnl']:+,.2f}")
    print(f"   Win Rate: {best['win_rate']:.1f}%")
    print(f"   Profit Factor: {best['profit_factor']:.2f}")
    print(f"   Max Drawdown: {best['max_dd']:.1f}%")
    print(f"   Total Trades: {best['trades']}")


if __name__ == "__main__":
    main()
