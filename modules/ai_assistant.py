"""FinsageAI — AI Trading Chat Assistant Backend"""
import os
from datetime import datetime

KNOWLEDGE_BASE = {
    "rsi": """**📊 RSI (Relative Strength Index)**

Momentum oscillator measuring speed and change of price movements.

**Scale: 0–100**
- **Below 30** → Oversold 🟢 (potential buy opportunity)
- **Above 70** → Overbought 🔴 (potential sell zone)
- **30–70** → Neutral zone

**RSI Divergence:**
- Bullish: Price lower low, RSI higher low → reversal up likely
- Bearish: Price higher high, RSI lower high → reversal down likely

**Best practices:** 14-period default. Confirm with MACD + volume. In strong trends RSI can stay overbought for weeks.

> ⚖️ Educational only. Not SEBI investment advice.""",

    "macd": """**📈 MACD (Moving Average Convergence Divergence)**

Shows relationship between two moving averages.

**Components:**
- MACD Line = 12 EMA − 26 EMA
- Signal Line = 9 EMA of MACD
- Histogram = MACD − Signal

**Signals:**
- 🟢 MACD crosses above Signal → Bullish
- 🔴 MACD crosses below Signal → Bearish
- Histogram growing → momentum increasing

MACD is a **lagging** indicator — best for trend confirmation on 4H/Daily charts.

> ⚖️ Educational only. Not SEBI advice.""",

    "candlestick": """**🕯️ Candlestick Patterns**

**Bullish Reversals:**
- 🟢 Hammer — Long lower shadow, buyers rejected lower prices
- 🟢 Morning Star — 3 candles: red → doji → large green
- 🟢 Bullish Engulfing — Green fully covers previous red

**Bearish Reversals:**
- 🔴 Shooting Star — Long upper shadow after uptrend
- 🔴 Evening Star — 3 candles: green → doji → large red
- 🔴 Bearish Engulfing — Red covers previous green

**Neutral:**
- ⚪ Doji — Open ≈ Close → market indecision

**Pro Tip:** Always confirm with volume. High volume = stronger signal.

> ⚖️ Educational only. Not SEBI advice.""",

    "risk management": """**🛡️ Risk Management — The Most Important Skill**

**The 1% Rule:** Never risk more than 1-2% of total capital per trade.

**Position Sizing:**
`Position Size = (Account × Risk%) / (Entry − Stop Loss)`

**Risk:Reward Ratio:**
- Minimum 1:2 (risk ₹1 to make ₹2)
- Ideal: 1:3 or better

**Portfolio rules:** Max 5-10 positions, diversify sectors, keep 20-30% cash.

**Biggest mistake:** No stop loss. A 50% loss requires 100% gain to recover.

> ⚖️ Educational only. Not SEBI advice.""",

    "moving average": """**📉 Moving Averages**

- **SMA** = Equal weight to all periods
- **EMA** = More weight to recent prices (faster signals)

**Key levels:** 20 MA (short), 50 MA (medium), 200 MA (long-term)

**Golden Cross** 🟢 → 50 MA crosses above 200 MA → Strong bullish signal
**Death Cross** 🔴 → 50 MA crosses below 200 MA → Strong bearish signal

Price above 200 MA = bullish territory. Below = bearish.

> ⚖️ Educational only. Not SEBI advice.""",

    "fundamental analysis": """**📋 Fundamental Analysis**

| Metric | Good Range |
|--------|-----------|
| P/E Ratio | 10-25x typical |
| EPS Growth | >15% strong |
| Debt/Equity | <1.5x healthy |
| ROE | >15% strong |
| Revenue Growth | >10% good |

**Steps:** Read quarterly earnings → compare P/E to sector → check debt trend → verify management guidance accuracy.

> ⚖️ Educational only. Not SEBI advice.""",

    "crypto": """**₿ Cryptocurrency Guide**

**Risks:** 24/7 market, extreme volatility (50%+ swings), smart contract bugs, regulatory risk, rug pulls in meme coins.

**Key indicators for crypto:**
- RSI on daily charts
- Bitcoin dominance as macro signal
- Fear & Greed Index (alternative.me)

**Market Cap** is more reliable than price. Only invest what you can afford to lose completely.

> ⚖️ Educational only. Not SEBI advice.""",

    "ipo": """**🏦 IPO Analysis Guide**

**✅ Green flags:** Revenue growth >20%, clear profitability path, dominant market position, quality underwriters.

**🔴 Red flags:** Negative revenue growth, extreme valuation (P/S >20x), heavy insider selling at IPO.

**India IPO:** Apply via UPI/ASBA. Allotment is lottery if oversubscribed. Wait 3-6 months post-listing for price discovery.

> ⚖️ Educational only. Not SEBI advice.""",

    "portfolio": """**📁 Portfolio Building**

**Moderate allocation:** 60% stocks, 10% crypto, 25% bonds/FD, 5% cash.

**Stock split:** 50% large-cap (stability), 30% mid-cap (growth), 10% small-cap (risk/reward), 10% international.

**Rebalance quarterly.** SIP strategy = rupee cost averaging. "Time in market > timing the market."

> ⚖️ Educational only. Not SEBI advice.""",

    "options": """**⚙️ Options Trading Basics**

**Call** = right to BUY at strike price. **Put** = right to SELL.

**Greeks:**
- Delta — price sensitivity (0 to 1)
- Theta — time decay (options lose value daily)
- Vega — volatility sensitivity
- Gamma — rate of delta change

**Basic strategies:** Buy Call (bullish), Buy Put (bearish), Covered Call (income), Iron Condor (range-bound).

**⚠️ Warning:** 80%+ retail options traders lose money. Learn before trading.

> ⚖️ Educational only. Not SEBI advice.""",

    "support resistance": """**📐 Support & Resistance**

**Support** = price floor where buyers step in. **Resistance** = price ceiling where sellers dominate.

**How to identify:** Price bouncing 2+ times from same level. Previous highs become support after breakout. Round numbers act as psychological levels.

**Breakout:** Price closes above resistance with high volume → new support level.

The more times a level is tested, the stronger it is.

> ⚖️ Educational only. Not SEBI advice.""",

    "volume": """**📊 Volume Analysis**

Volume **confirms** price moves. High volume breakout = strong signal. Low volume = weak/false move.

- Volume declining in uptrend = weakening momentum
- Spike in volume = institutional activity
- High volume on reversal candle = strong signal

Always check volume when evaluating any chart pattern.

> ⚖️ Educational only. Not SEBI advice.""",

    "fibonacci": """**🌀 Fibonacci Retracements**

Key levels: **23.6%, 38.2%, 50%, 61.8%** (Golden Ratio), 78.6%.

**61.8%** retracement = strongest support in uptrend. Draw from swing low to swing high.

Combine with RSI and volume for confirmation. Fibonacci works best in trending markets.

> ⚖️ Educational only. Not SEBI advice.""",

    "bollinger": """**📊 Bollinger Bands**

3 bands: Upper (SMA + 2σ), Middle (20 SMA), Lower (SMA − 2σ).

- Price touching lower band = oversold zone
- Price touching upper band = overbought zone
- **Band squeeze** = low volatility → explosive move coming

Walking the bands in strong trends = momentum signal. Always confirm with other indicators.

> ⚖️ Educational only. Not SEBI advice.""",

    "psychology": """**🧠 Trading Psychology**

**Common traps:**
- FOMO — chasing pumped stocks at peaks
- Loss Aversion — holding losers, selling winners early
- Revenge Trading — reckless trades after a loss
- Overconfidence — risking too much after a winning streak

**Fixes:** Plan trade before entering. Journal every trade. Take break after 2 losses. Focus on process, not P&L.

The market rewards patience and punishes impatience.

> ⚖️ Educational only. Not SEBI advice.""",
}


def _gemini_response(query, history):
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        system = (
            "You are FinsageAI Trading Assistant — an expert educational trading guide. "
            "Help traders understand stocks, crypto, technical and fundamental analysis, risk management. "
            "Never give direct buy/sell recommendations for specific stocks. "
            "Always end with: 'For educational purposes only. Not SEBI investment advice.' "
            f"Respond in 150-300 words. Today: {datetime.now().strftime('%B %d, %Y')}."
        )
        model = genai.GenerativeModel("gemini-1.5-flash", system_instruction=system)
        resp = model.generate_content(query)
        return resp.text
    except Exception:
        return None


def _smart_response(query):
    q = query.lower()
    for key, ans in KNOWLEDGE_BASE.items():
        if key in q:
            return ans
    if any(g in q for g in ["hello", "hi ", "hey", "namaste", "start", "help"]):
        return """👋 **Welcome to FinsageAI Assistant!**

Ask me anything about trading:

📊 **Technical Analysis** — RSI, MACD, Bollinger, Moving Averages
🕯️ **Candlestick Patterns** — Hammer, Doji, Engulfing, and more
🛡️ **Risk Management** — Position sizing, Stop losses
₿ **Crypto** — Bitcoin, DeFi, Altcoins, Meme coins
📁 **Portfolio Building** — Diversification, Asset allocation
⚙️ **Options** — Basics, Greeks, Strategies
📈 **IPO Analysis** — How to evaluate new listings

**Try:** *"Explain RSI"* or *"What is MACD?"* or *"How to manage risk?"*

> ⚖️ Educational guide only. Not SEBI investment advice."""
    common = {
        "buy": "**When to Buy?**\n\n- 🟢 RSI not overbought (<65)\n- 🟢 Near support level\n- 🟢 MACD bullish crossover\n- 🟢 Strong fundamental story\n- 🟢 Volume confirming move\n\n**Never buy:** Just because price is falling, or on tips without research.\n\n> ⚖️ Educational only.",
        "sell": "**When to Sell?**\n\n- 🔴 Stop loss hit (non-negotiable)\n- 🔴 Fundamental story has changed\n- 🔴 RSI > 80 overbought\n- 🔴 Price hits your target\n\n**Avoid:** Panic selling on temporary dips or selling winners too early.\n\n> ⚖️ Educational only.",
        "beginner": "**Getting Started as a Trader**\n\n1. 📚 Learn first — paper trade before real money\n2. 💰 Start small — only invest what you can afford to lose\n3. 🛡️ Risk management — 1-2% max risk per trade\n4. 📊 Pick 2-3 indicators — don't overcomplicate\n5. 📝 Keep a trade journal\n6. 😌 Control emotions — FOMO is your enemy\n\n> ⚖️ Educational only.",
    }
    for kw, resp in common.items():
        if kw in q:
            return resp
    return """🤔 **I can help you with:**

📊 Technical Analysis — *"explain RSI"*, *"what is MACD"*, *"candlestick patterns"*
🛡️ Risk Management — *"risk management"*, *"position sizing"*
📁 Portfolio — *"how to build portfolio"*
₿ Crypto — *"crypto trading guide"*
⚙️ Options — *"options trading basics"*

*For real-time analysis, use the Backtesting or Stock Dashboard modules!*

> ⚖️ FinsageAI is educational only. Not SEBI investment advice."""


def get_response(query, history):
    gemini = _gemini_response(query, history)
    if gemini:
        return gemini, "gemini"
    return _smart_response(query), "local"
