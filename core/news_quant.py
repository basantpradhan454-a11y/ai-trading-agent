"""
Lightweight social/news sentiment (Google News RSS — no API key required)
plus basic quant risk metrics for the selected symbol.
"""
import feedparser
import pandas as pd

POSITIVE_WORDS = {
    "surge", "rally", "bullish", "gain", "soar", "upgrade", "breakout", "record",
    "adoption", "growth", "strong", "beat", "rebound", "recovery", "inflow",
}
NEGATIVE_WORDS = {
    "crash", "plunge", "bearish", "loss", "dump", "downgrade", "selloff", "hack",
    "ban", "fear", "weak", "miss", "outflow", "lawsuit", "collapse",
}


def fetch_news(symbol_query: str = "bitcoin", limit: int = 8) -> list:
    query = symbol_query.replace("/", " ").replace("USDT", "").replace("USD", "").strip()
    url = f"https://news.google.com/rss/search?q={query}%20crypto&hl=en-IN&gl=IN&ceid=IN:en"
    feed = feedparser.parse(url)
    items = []
    for entry in feed.entries[:limit]:
        title = entry.title
        words = set(title.lower().replace(",", " ").replace(".", " ").split())
        score = len(words & POSITIVE_WORDS) - len(words & NEGATIVE_WORDS)
        sentiment = "Positive" if score > 0 else "Negative" if score < 0 else "Neutral"
        items.append({"title": title, "link": entry.link, "sentiment": sentiment})
    return items


def quant_metrics(df: pd.DataFrame) -> dict:
    returns = df["close"].pct_change().dropna()
    if returns.empty or returns.std() == 0:
        return {"annualized_volatility_pct": 0.0, "sharpe_estimate": 0.0, "max_drawdown_pct": 0.0}
    volatility = returns.std() * (365 ** 0.5) * 100
    sharpe = (returns.mean() / returns.std()) * (365 ** 0.5)
    max_drawdown = ((df["close"] / df["close"].cummax()) - 1).min() * 100
    return {
        "annualized_volatility_pct": round(float(volatility), 2),
        "sharpe_estimate": round(float(sharpe), 2),
        "max_drawdown_pct": round(float(max_drawdown), 2),
    }
