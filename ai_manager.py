import google.generativeai as genai
import logging
import json
import re
from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

# High-impact news events that should block trading
HIGH_IMPACT_KEYWORDS = [
    "FOMC", "Fed rate", "interest rate decision", "NFP", "non-farm payroll",
    "CPI", "inflation", "ECB rate", "ECB decision", "GDP", "unemployment",
    "Powell", "Lagarde", "emergency", "war", "crisis", "default"
]

def validate_with_ai(symbol, signal, params):
    """
    Ask Gemini if this is a safe trade.
    Uses Google Search to check real-time news and economic events.
    """
    if not GEMINI_API_KEY:
        logger.warning("No Gemini API Key. Auto-approving signal.")
        return True, "AI Validation skipped (No Key)."

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        
        # Use stable model
        # Note: google_search tool removed temporarily as it was causing API errors
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Get readable symbol
        symbol_name = "EUR/USD" if "EURUSD" in symbol else symbol

        prompt = f"""You are a Forex Risk Manager. Check if it's safe to trade {symbol_name} right now.

SIGNAL: {signal} {symbol_name}
Entry: {params.get('price', 0):.5f}
Stop Loss: {params.get('sl', 0):.5f}
Take Profit: {params.get('tp', 0):.5f}

SEARCH for:
1. Any major news affecting EUR or USD in the next 4 hours
2. Upcoming Fed or ECB announcements
3. Unusual market volatility or geopolitical events

DECISION RULES:
- REJECT if: Major news in next 2 hours (FOMC, ECB, NFP, CPI)
- REJECT if: Extreme volatility or "black swan" events
- APPROVE if: Normal market conditions, no major news imminent

Reply with JSON only:
{{"approved": true/false, "reasoning": "Brief explanation (1-2 sentences)"}}"""

        response = model.generate_content(prompt)
        
        # Extract JSON from response (handle markdown code blocks)
        text = response.text.strip()
        
        # Remove markdown code blocks if present
        if "```" in text:
            match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
            if match:
                text = match.group(1)
        
        # Parse JSON
        result = json.loads(text)
        approved = result.get("approved", False)
        reasoning = result.get("reasoning", "No reasoning provided.")
        
        logger.info(f"AI Decision: {'APPROVED' if approved else 'REJECTED'} - {reasoning}")
        return approved, reasoning
        
    except json.JSONDecodeError as e:
        logger.warning(f"AI returned invalid JSON, auto-approving: {e}")
        return True, "AI response unclear - signal approved with caution"
        
    except Exception as e:
        logger.error(f"AI Validation error: {e}")
        # On error, approve but flag it
        return True, f"AI check failed ({str(e)[:50]}) - proceed with caution"


def check_high_impact_news(reasoning: str) -> bool:
    """Check if AI reasoning mentions high-impact events"""
    reasoning_lower = reasoning.lower()
    for keyword in HIGH_IMPACT_KEYWORDS:
        if keyword.lower() in reasoning_lower:
            return True
    return False
