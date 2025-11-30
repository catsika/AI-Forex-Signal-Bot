import google.generativeai as genai
import logging
import json
from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

def validate_with_ai(symbol, signal, params):
    """
    Ask Gemini if this is a safe trade.
    """
    if not GEMINI_API_KEY:
        logger.warning("No Gemini API Key provided. Skipping AI validation.")
        return True, "AI Validation skipped (No Key)."

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        # Enable Google Search tool
        tools = [
            {"google_search_retrieval": {
                "dynamic_retrieval_config": {
                    "mode": "dynamic",
                    "dynamic_threshold": 0.6,
                }
            }}
        ]
        model = genai.GenerativeModel('gemini-2.0-flash-exp', tools=tools)

        prompt = f"""
        You are a professional Forex Risk Manager. 
        I have a technical signal for {symbol}.
        
        Signal: {signal}
        Current Price: {params['price']:.2f}
        RSI (14): {params['rsi']:.2f}
        EMA (200): {params['ema_200']:.2f}
        ATR (14): {params['atr']:.4f}
        
        Proposed Trade:
        Entry Zone: {params['entry_min']:.2f} - {params['entry_max']:.2f}
        Stop Loss: {params['sl']:.2f}
        Take Profit: {params['tp']:.2f}
        
        Market Context:
        The strategy is a mean reversion / trend pullback strategy.
        - Buy when price is ABOVE 200 EMA (Trend Up) but RSI is Oversold (<33).
        - Sell when price is BELOW 200 EMA (Trend Down) but RSI is Overbought (>67).
        
        Task:
        1. SEARCH for the latest news, economic events, or sentiment affecting {symbol} right now.
        2. Analyze the technical levels provided.
        3. Decide if this is a high-probability setup considering BOTH technicals and current market sentiment/news.
        
        Reply with a JSON object:
        {{
            "approved": true/false,
            "reasoning": "Concise reason including any relevant news found (max 2 sentences)."
        }}
        """
        
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        
        result = json.loads(response.text)
        
        return result.get("approved", False), result.get("reasoning", "No reasoning provided.")
        
    except Exception as e:
        logger.error(f"AI Validation failed: {e}")
        return False, f"AI Error: {e}"
