# AI-Augmented Forex Signal Bot 🤖📈

A professional-grade, automated trading signal generator for **Gold (XAUUSD)**, **EURUSD**, and **Bitcoin**. 

This bot combines classic **Trend Following** strategies with **AI-Powered Risk Management** (Google Gemini 2.0) to filter out bad trades during high-impact news events.

## 🚀 Features

*   **Smart Strategy**: 
    *   **Trend Filter**: 200 EMA (Exponential Moving Average).
    *   **Entry Signal**: RSI (Relative Strength Index) Pullbacks (Oversold/Overbought).
    *   **Volatility Adjustment**: Dynamic Stop Loss based on ATR (Average True Range).
*   **AI Risk Manager**: 
    *   Uses **Google Gemini 2.0 Flash** to analyze real-time market news and sentiment.
    *   Prevents trading during "Black Swan" events or conflicting fundamental data.
*   **Money Management**:
    *   **Auto-Lot Calculation**: Automatically calculates lot size to risk a fixed amount (e.g., $50) per trade.
    *   **Risk/Reward**: Targets a strict 1:2 Risk-to-Reward ratio.
*   **Instant Alerts**: Sends detailed signals to **Telegram** with Entry, Stop Loss, Take Profit, and AI Reasoning.

## 🛠️ Tech Stack

*   **Python 3.10+**
*   **yfinance** (Real-time Data)
*   **pandas** (Technical Analysis)
*   **Google Gemini API** (AI Analysis)
*   **Telegram Bot API** (Notifications)

## 📦 Installation

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/YOUR_USERNAME/AI-Forex-Signal-Bot.git
    cd AI-Forex-Signal-Bot
    ```

2.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment**
    Create a `.env` file in the root directory:
    ```env
    GEMINI_API_KEY=your_google_gemini_key
    TELEGRAM_BOT_TOKEN=your_telegram_bot_token
    TELEGRAM_CHAT_ID=your_telegram_chat_id
    ```

4.  **Run the Bot**
    ```bash
    python3 main.py
    ```

## ⚙️ Configuration

You can adjust settings in `config.py`:
*   `RISK_PER_TRADE`: Amount in USD to risk per trade (Default: $50).
*   `SYMBOLS`: List of assets to trade (Default: GC=F, EURUSD=X, BTC-USD).
*   `TIMEFRAME`: Candle size (Default: 15m).

## 📊 Strategy Logic

1.  **Long Setup**:
    *   Price > 200 EMA (Uptrend)
    *   RSI < 33 (Oversold Pullback)
    *   **AI Confirmation**: "Is there any negative news affecting this asset right now?"

2.  **Short Setup**:
    *   Price < 200 EMA (Downtrend)
    *   RSI > 67 (Overbought Pullback)
    *   **AI Confirmation**: "Is there any positive news affecting this asset right now?"

## ⚠️ Disclaimer

This software is for educational purposes only. Forex and Crypto trading involve significant risk. The authors are not responsible for any financial losses incurred while using this bot. Use at your own risk.
