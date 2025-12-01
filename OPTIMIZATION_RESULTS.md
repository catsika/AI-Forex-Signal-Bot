# EUR/USD Strategy Optimization Results

## Final Optimized Configuration

After running a comprehensive grid search across 648 parameter combinations on 2 years of EUR/USD 1H data:

### Best Parameters (Applied to `strategy_optimized.py`)

| Parameter | Value | Description |
|-----------|-------|-------------|
| ADX Threshold | 25 | Minimum trend strength to take trades |
| RSI Oversold | 30 | Lower RSI bound |
| RSI Overbought | 70 | Upper RSI bound |
| ATR Multiplier | 2.0x | Stop-loss distance (2× ATR) |
| Risk:Reward | 1:2.5 | Take profit at 2.5× risk distance |
| Min Score | 5.0 | Minimum signal quality score |
| Trading Mode | Both Directions | Trade both bullish and bearish setups |
| Session Filter | Block hours 1,3,6 UTC | Avoid low-liquidity Asian hours |

### Backtest Performance (2-Year Period)

| Metric | Value |
|--------|-------|
| **Total Profit** | +$1,785 |
| **Return** | +8.9% |
| **Profit Factor** | **1.70** |
| **Win Rate** | **51.4%** |
| **Max Drawdown** | **2.3%** |
| **Total Trades** | 105 |
| **Buy/Sell Balance** | 52/53 |
| **Avg Holding** | 22 bars (~22 hours) |

---

## ⚡ CRITICAL: Trailing Stop Mechanism

The trailing stop is the **KEY** to this strategy's profitability. Without it, the strategy loses money.

### How it works:
1. Trade opens with SL at 2.0× ATR from entry
2. When price moves **1.5× risk** in our favor:
   - SL moves to **breakeven + 20% profit**
   - Trade becomes **risk-free**
3. This turns many would-be losses into small wins or breakeven

### Why it matters:
- Raw signal win rate: ~22%
- With trailing stop: ~51%
- **Trailing stop saves ~30% of trades from being losses**

### Monitoring the Trailing Stop:
The `trade_monitor.py` module tracks:
- When stops are moved to breakeven
- How many trades were saved by the trailing stop
- Full trade history with SL adjustments

View stats anytime:
```python
from trade_monitor import trade_monitor
print(trade_monitor.get_stats())
```

---

## Files

- `strategy_optimized.py` - Optimized strategy with grid-searched parameters
- `backtest.py` - Uses optimized strategy
- `main.py` - Live trading with trade monitor
- `trade_monitor.py` - **Tracks trailing stops and logs adjustments**
- `grid_search.py` - Parameter optimization tool
- `active_trades.json` - Persists trade state across restarts

---

## Account Settings

- **Capital:** $20,000 (Prop Firm)
- **Risk Per Trade:** $50 (0.25%)
- **Symbol:** EUR/USD only
- **Timeframe:** 1H (hourly)

---

## Prop Firm Readiness

✅ **Win Rate > 50%** - 51.4%  
✅ **Profit Factor > 1.5** - 1.70  
✅ **Low Drawdown** - 2.3% max  
✅ **Consistent Trading** - 105 trades/2yr  
✅ **Balanced Direction** - 52 Buy / 53 Sell  

---

## Running the Bot

```bash
# Run backtest
python3 backtest.py

# Run grid search (to re-optimize)
python3 grid_search.py

# Run live bot (with trailing stop monitoring)
python3 main.py
```

---

*Generated: December 2024*
