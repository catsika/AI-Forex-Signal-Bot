# EUR/USD Forex Trading Bot 🤖📈A professional-grade, automated trading signal generator optimized for **EUR/USD** trading with prop firm rules in mind.## 🎯 Strategy Performance (Backtested)| Metric | Value ||--------|-------|| **Win Rate** | 56% (stable markets) || **Profit Factor** | 1.7 - 2.3 || **Risk:Reward** | 1:2.5 || **Max Drawdown** | 2.3% || **Trades/Month** | ~5 |## 💰 Prop Firm Challenge Timeline### Conservative ($50 risk/trade = 0.25%)| Phase | Target | Time ||-------|--------|------|| Phase 1 | 8% ($1,600) | ~7 months || Phase 2 | 5% ($1,000) | ~4 months || **Total to Funded** | | **~11 months** |### Aggressive ($100 risk/trade = 0.5%) ⚡ RECOMMENDED| Phase | Target | Time ||-------|--------|------|| Phase 1 | 8% ($1,600) | ~3-4 months || Phase 2 | 5% ($1,000) | ~2-3 months || **Total to Funded** | | **~5-7 months** |### Once Funded ($20k account, $100 risk)- **Monthly Profit:** ~$480- **Yearly Profit:** ~$5,760 (29% ROI)- **You Keep (80%):** ~$4,600/year## 🚀 Features- **Multi-Indicator Strategy**: EMA, RSI, MACD, ADX, Bollinger Bands, Stochastic- **AI Risk Filter**: Google Gemini 2.0 blocks trades during high-impact news- **Dynamic Risk Management**: ATR-based stop loss, trailing stops- **Telegram Alerts**: Real-time signals with entry, SL, TP, and reasoning- **Prop Firm Safe**: Low drawdown, consistent returns## 📦 Installation```bash# Clone and installgit clone https://github.com/YOUR_USERNAME/forex-trading-bot.gitcd forex-trading-botpip install -r requirements.txt# Configurecp .env.example .env# Edit .env with your API keys# Run backtest firstpython3 backtest.py# Run livepython3 main.py```## ⚙️ ConfigurationEdit `config.py`:```pythonSYMBOL = "EURUSD=X"       # Trading pairRISK_PER_TRADE = 100      # USD risk per tradeTIMEFRAME = "1h"          # Hourly candles```## 📊 Strategy Logic**Entry Conditions (Score-based system):**- Trend alignment (EMA 20/50/200)- RSI in range (30-70, not extreme)
- ADX > 25 (strong trend)
- MACD confirmation
- Bollinger Band position
- Volume confirmation

**Risk Management:**
- Stop Loss: 2.0x ATR
- Take Profit: 2.5x risk distance
- Trailing Stop: Moves to breakeven + 20% at 1.5R profit

## 🏦 Prop Firm Compatibility

| Rule | Strategy | Status |
|------|----------|--------|
| Max Daily DD 5% | 2.3% max observed | ✅ |
| Max Total DD 10% | Never exceeded 3% | ✅ |
| Consistent style | Same strategy always | ✅ |
| No martingale | Fixed risk per trade | ✅ |

## 📁 Files

| File | Purpose |
|------|---------|
| `main.py` | Live trading loop |
| `strategy_optimized.py` | Signal generation |
| `indicators.py` | Technical indicators |
| `backtest.py` | Strategy testing |
| `notifier.py` | Telegram alerts |
| `ai_manager.py` | AI news filter |
| `config.py` | Settings |

## ⚠️ Disclaimer

This software is for educational purposes only. Forex trading involves significant risk. Past backtest performance does not guarantee future results. Use at your own risk.
