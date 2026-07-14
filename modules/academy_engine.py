"""FinsageAI — Finsage Academy Gamified Learning Engine"""
import streamlit as st

BADGES = [
    ("Novice Trader", 100, "🌱"),
    ("Chart Reader", 250, "📊"),
    ("Pattern Guru", 500, "🕯️"),
    ("Risk Master", 750, "🛡️"),
    ("Market Sage", 1000, "🏆"),
]

CURRICULUM = {
    1: [
        {
            "id": "L1_1", "title": "What is a Stock Market?", "xp": 50,
            "content": """## 📈 What is a Stock Market?

A **stock market** is a marketplace where buyers and sellers trade shares of publicly listed companies.

**Key concepts:**
- **Share/Stock** — A unit of ownership in a company
- **Bull Market** — Prices rising (optimism) 🐂
- **Bear Market** — Prices falling (pessimism) 🐻
- **Sensex** — India's top 30 companies index (BSE)
- **Nifty 50** — India's top 50 companies index (NSE)

**Why do stock prices move?**
- Earnings reports (profits/losses)
- Economic data (GDP, inflation)
- News events (mergers, scandals)
- Supply & demand from buyers/sellers

> 💡 Think of buying a stock as buying a small piece of a business.""",
            "quiz": [
                {"q": "What does a Bull Market indicate?",
                 "opts": ["A) Prices falling", "B) Prices rising", "C) Market closed", "D) High volatility"],
                 "ans": "B", "exp": "Bull Market = prices going UP. Investors are optimistic about future growth. 🐂"},
                {"q": "Nifty 50 represents how many companies?",
                 "opts": ["A) 30", "B) 100", "C) 50", "D) 500"],
                 "ans": "C", "exp": "Nifty 50 tracks the performance of 50 large-cap companies on NSE India."},
                {"q": "Which exchange hosts the Sensex index?",
                 "opts": ["A) NSE", "B) BSE", "C) MCX", "D) SEBI"],
                 "ans": "B", "exp": "Sensex (Sensitive Index) is the benchmark index of Bombay Stock Exchange (BSE)."},
            ]
        },
        {
            "id": "L1_2", "title": "Candlestick Anatomy", "xp": 50,
            "content": """## 🕯️ Reading Candlestick Charts

Each candle represents price action over a time period.

**Anatomy:**
- **Body** — Distance between Open and Close
- **Upper Wick** — High above the body
- **Lower Wick** — Low below the body

**🟢 Green candle** = Close > Open (Bullish — buyers won)
**🔴 Red candle** = Close < Open (Bearish — sellers won)

**Key interpretation:**
- Long lower wick = buyers pushed price back up ✅
- Long upper wick = sellers pushed price back down ❌
- Small body + long wicks = market indecision (Doji)

> 💡 Patterns on daily/weekly charts are stronger than on 1-minute charts.""",
            "quiz": [
                {"q": "A green candlestick means:",
                 "opts": ["A) Close < Open", "B) Close > Open", "C) High = Low", "D) Market paused"],
                 "ans": "B", "exp": "Green (bullish) candle: Close price is HIGHER than Open price. Buyers dominated."},
                {"q": "The 'wick' on a candle represents:",
                 "opts": ["A) Average price", "B) Volume", "C) High/Low extremes", "D) Opening price"],
                 "ans": "C", "exp": "Wicks show the highest and lowest prices reached during the period."},
                {"q": "A long lower wick suggests:",
                 "opts": ["A) Bears are strong", "B) Buyers pushed price back up", "C) No trading happened", "D) Price is stable"],
                 "ans": "B", "exp": "Long lower wick = price fell but buyers stepped in and recovered it. Bullish sign!"},
            ]
        },
    ],
    2: [
        {
            "id": "L2_1", "title": "RSI — Relative Strength Index", "xp": 100,
            "content": """## 📊 RSI Deep Dive

RSI measures **momentum** — how fast prices move up or down.

**Scale: 0 to 100**
- **Below 30** → Oversold 🟢 (potential buying opportunity)
- **Above 70** → Overbought 🔴 (potential selling zone)
- **50** → Neutral

**RSI Divergence (powerful signal):**
- **Bullish**: Price makes lower low, RSI makes higher low → reversal up
- **Bearish**: Price makes higher high, RSI makes lower high → reversal down

**Best practices:**
- Default 14-period RSI
- Confirm with MACD + volume
- In strong trends, RSI can stay overbought for weeks

> ⚖️ Educational only. Not SEBI advice.""",
            "quiz": [
                {"q": "RSI below 30 indicates:",
                 "opts": ["A) Strong uptrend", "B) Overbought", "C) Oversold", "D) High volume"],
                 "ans": "C", "exp": "RSI < 30 = Oversold zone. Watch for reversal candles before acting."},
                {"q": "Bullish RSI Divergence occurs when:",
                 "opts": ["A) RSI and price both fall", "B) Price makes lower low but RSI makes higher low", "C) RSI exceeds 70", "D) Both make new highs"],
                 "ans": "B", "exp": "Bullish divergence: price weakness not confirmed by RSI momentum. Strong reversal signal!"},
                {"q": "Default RSI period is:",
                 "opts": ["A) 7", "B) 21", "C) 9", "D) 14"],
                 "ans": "D", "exp": "14-period RSI is the industry standard across most timeframes."},
            ]
        },
        {
            "id": "L2_2", "title": "MACD Explained", "xp": 100,
            "content": """## 📈 MACD (Moving Average Convergence Divergence)

**Components:**
- **MACD Line** = 12 EMA − 26 EMA
- **Signal Line** = 9 EMA of MACD Line
- **Histogram** = MACD − Signal

**Signals:**
| Signal | Meaning |
|--------|---------|
| MACD crosses ABOVE Signal | 🟢 Bullish |
| MACD crosses BELOW Signal | 🔴 Bearish |
| Histogram growing | Momentum increasing |
| Histogram shrinking | Momentum weakening |

**Zero line:** MACD above 0 = bullish territory.

> 💡 MACD is a lagging indicator — confirms trends rather than predicting reversals. Best on 4H/Daily charts.

> ⚖️ Educational only. Not SEBI advice.""",
            "quiz": [
                {"q": "MACD Line is calculated as:",
                 "opts": ["A) 26 EMA − 12 EMA", "B) 12 EMA − 26 EMA", "C) 9 EMA of price", "D) RSI × Volume"],
                 "ans": "B", "exp": "MACD Line = 12-period EMA minus 26-period EMA. Positive = fast EMA > slow EMA (bullish)."},
                {"q": "A bullish MACD crossover happens when:",
                 "opts": ["A) Price crosses 200 MA", "B) MACD crosses below Signal", "C) MACD crosses above Signal", "D) Histogram turns negative"],
                 "ans": "C", "exp": "MACD crossing above Signal line = bullish momentum shift. Buy trigger in trend systems."},
                {"q": "MACD is primarily a:",
                 "opts": ["A) Volume indicator", "B) Trend-following momentum indicator", "C) Volatility indicator", "D) Support/Resistance tool"],
                 "ans": "B", "exp": "MACD combines trend (moving averages) and momentum. It's a lagging trend-following indicator."},
            ]
        },
    ],
    3: [
        {
            "id": "L3_1", "title": "Risk Management & Position Sizing", "xp": 150,
            "content": """## 🛡️ Risk Management — The Most Important Skill

**The 1% Rule:** Never risk more than 1-2% of total capital per trade.

**Position Sizing:**
```
Position Size = (Account × Risk%) / (Entry − Stop Loss)

Example:
Account = ₹1,00,000 | Risk = 1% = ₹1,000
Entry = ₹500, SL = ₹480
Position = ₹1,000 / ₹20 = 50 shares
```

**Risk:Reward Ratio:**
- Minimum **1:2** (risk ₹1 to potentially make ₹2)
- With 50% win rate + 1:2 R:R → you're profitable

**Stop Loss Types:**
- Fixed % (5-8% below entry)
- Support-based (just below key support)
- ATR-based (Entry − 1.5 × ATR)

> 🚫 The #1 mistake: no stop loss. A 50% loss needs 100% gain to recover.""",
            "quiz": [
                {"q": "The 1% Rule means:",
                 "opts": ["A) Only trade 1% of stocks", "B) Never risk more than 1-2% capital per trade", "C) Take 1% profit and exit", "D) Use 1% position always"],
                 "ans": "B", "exp": "Risk max 1-2% of total capital per trade. On ₹1L account = ₹1,000-2,000 max loss."},
                {"q": "Minimum recommended Risk:Reward ratio is:",
                 "opts": ["A) 1:1", "B) 2:1", "C) 1:2", "D) 3:1"],
                 "ans": "C", "exp": "1:2 R:R = risking ₹1 to make ₹2. Even with 40% win rate, you can be profitable."},
                {"q": "A 50% loss requires what % gain to recover?",
                 "opts": ["A) 50%", "B) 75%", "C) 100%", "D) 25%"],
                 "ans": "C", "exp": "₹1L drops 50% to ₹50K → needs 100% gain (₹50K) to get back to ₹1L. Avoid large losses!"},
            ]
        },
        {
            "id": "L3_2", "title": "Trading Psychology", "xp": 150,
            "content": """## 🧠 Trading Psychology

**The biggest enemy in trading is YOU.**

| Trap | Description | Fix |
|------|-------------|-----|
| **FOMO** | Fear Of Missing Out — buying at peaks | Wait for pullbacks |
| **Loss Aversion** | Holding losers, selling winners early | Use stop losses always |
| **Overconfidence** | After winning streak, risk too much | Stick to 1% rule |
| **Revenge Trading** | Big loss → recover fast → bigger loss | Take break after 2 losses |
| **Anchoring** | Attached to your buy price | Market doesn't know your cost |

**3 Rules of Discipline:**
1. Plan the trade, trade the plan
2. Journal every trade (reason, emotion)
3. Review weekly — what worked?

> 💡 The market rewards patience and punishes impatience.""",
            "quiz": [
                {"q": "FOMO in trading means:",
                 "opts": ["A) Fear Of Market Opening", "B) Fear Of Missing Out on a trade", "C) Follow Other Market Orders", "D) Full Order Market Operations"],
                 "ans": "B", "exp": "FOMO leads traders to chase pumped stocks at the top. Solution: stick to your entry criteria."},
                {"q": "'Revenge trading' refers to:",
                 "opts": ["A) Trading against market makers", "B) Reporting fraudulent brokers", "C) Making reckless trades after a loss to recover", "D) Using algorithmic strategies"],
                 "ans": "C", "exp": "After a loss, anger drives traders to take bigger, riskier trades to 'get even' — causing larger losses."},
                {"q": "Best practice after 2 consecutive losses is:",
                 "opts": ["A) Double your position size", "B) Switch strategies immediately", "C) Take a break and review your trades", "D) Trade more to average out"],
                 "ans": "C", "exp": "After 2 losses, step away. Review what went wrong. Emotional trading is your worst enemy."},
            ]
        },
    ]
}


def init_user():
    if "academy_profile" not in st.session_state:
        st.session_state["academy_profile"] = {"xp": 0, "level": 1, "badges": [], "completed": []}

def get_profile():
    init_user()
    return st.session_state["academy_profile"]

def check_answer(lesson_id, q_idx, user_ans):
    profile = get_profile()
    lesson = None
    for lv in CURRICULUM.values():
        for l in lv:
            if l["id"] == lesson_id:
                lesson = l; break
    if not lesson:
        return {"correct": False, "exp": "Lesson not found", "xp": 0, "badge": None}
    q = lesson["quiz"][q_idx]
    correct = user_ans == q["ans"]
    xp_gain = lesson["xp"] // len(lesson["quiz"]) if correct else 0
    profile["xp"] += xp_gain
    if correct and lesson_id not in profile["completed"]:
        profile["completed"].append(lesson_id)
    new_badge = None
    for name, threshold, icon in BADGES:
        badge_str = f"{icon} {name}"
        if profile["xp"] >= threshold and badge_str not in profile["badges"]:
            profile["badges"].append(badge_str)
            new_badge = badge_str; break
    if profile["xp"] >= 200 and profile["level"] < 2: profile["level"] = 2
    if profile["xp"] >= 500 and profile["level"] < 3: profile["level"] = 3
    return {"correct": correct, "exp": q["exp"], "xp": xp_gain,
            "total_xp": profile["xp"], "level": profile["level"], "badge": new_badge}
