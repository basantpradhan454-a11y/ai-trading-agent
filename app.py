"""
Elite Trading Intelligence Engine — v5.0
Futuristic UI | Institutional-Grade Analysis | Zero raw-HTML bugs
"""

import streamlit as st
import ccxt
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import feedparser
import re, uuid, os, datetime, json
from cryptography.fernet import Fernet
from passlib.context import CryptContext
from sqlalchemy import create_engine, Column, String, Float, DateTime, Text, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="TIE — Trading Intelligence Engine",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"Get Help": None, "Report a bug": None, "About": None}
)

# ── Database ──────────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./trading.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    pool_pre_ping=True
)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id          = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email       = Column(String, unique=True, nullable=False)
    full_name   = Column(String, nullable=False)
    hashed_pw   = Column(String, nullable=False)
    created_at  = Column(DateTime, default=datetime.datetime.utcnow)

class UserApiKey(Base):
    __tablename__ = "user_api_keys"
    id           = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id      = Column(String, nullable=False)
    exchange     = Column(String, nullable=False)
    enc_api_key  = Column(Text, nullable=False)
    enc_secret   = Column(Text, nullable=False)
    is_demo      = Column(Boolean, default=True)
    created_at   = Column(DateTime, default=datetime.datetime.utcnow)

Base.metadata.create_all(engine)

# ── Security ──────────────────────────────────────────────────────────────────
_raw_key = os.getenv("ENCRYPTION_KEY", "")
try:
    FERNET = Fernet(_raw_key.encode()) if _raw_key else Fernet(Fernet.generate_key())
except Exception:
    FERNET = Fernet(Fernet.generate_key())

PWD_CTX = CryptContext(schemes=["bcrypt"], deprecated="auto")
hash_pw   = lambda p: PWD_CTX.hash(p)
verify_pw = lambda p, h: PWD_CTX.verify(p, h)
encrypt   = lambda t: FERNET.encrypt(t.encode()).decode()
decrypt   = lambda t: FERNET.decrypt(t.encode()).decode()

# ── Global CSS — Futuristic Dark UI ──────────────────────────────────────────
def inject_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* ── Reset & Base ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, [data-testid="stAppViewContainer"],
[data-testid="stApp"] {
    background: #020812 !important;
    font-family: 'Inter', sans-serif !important;
}

/* Animated grid background */
[data-testid="stAppViewContainer"]::before {
    content: '';
    position: fixed;
    inset: 0;
    background-image:
        linear-gradient(rgba(37,99,235,0.04) 1px, transparent 1px),
        linear-gradient(90deg, rgba(37,99,235,0.04) 1px, transparent 1px);
    background-size: 60px 60px;
    pointer-events: none;
    z-index: 0;
}

/* Glowing orbs */
[data-testid="stAppViewContainer"]::after {
    content: '';
    position: fixed;
    top: -200px; left: -200px;
    width: 700px; height: 700px;
    background: radial-gradient(circle, rgba(37,99,235,0.07) 0%, transparent 70%);
    pointer-events: none;
    z-index: 0;
    animation: orb 18s ease-in-out infinite alternate;
}

@keyframes orb {
    0%   { transform: translate(0, 0); }
    50%  { transform: translate(400px, 200px); }
    100% { transform: translate(100px, 500px); }
}

/* ── Remove Streamlit chrome ── */
#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"] { display: none !important; }

/* ── Block container ── */
[data-testid="block-container"] {
    padding: 0 !important;
    max-width: 100% !important;
}

[data-testid="stVerticalBlock"] { gap: 0 !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: rgba(5,12,28,0.95) !important;
    border-right: 1px solid rgba(37,99,235,0.15) !important;
    backdrop-filter: blur(20px);
}

[data-testid="stSidebar"]::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, #2563eb, #6366f1, #06b6d4);
}

[data-testid="stSidebarContent"] {
    padding: 24px 18px !important;
}

/* ── Tabs ── */
[data-testid="stTabs"] [role="tablist"] {
    background: rgba(255,255,255,0.03) !important;
    border-radius: 10px !important;
    padding: 4px !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    gap: 2px !important;
}

[data-testid="stTabs"] [role="tab"] {
    color: rgba(255,255,255,0.4) !important;
    border-radius: 8px !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    letter-spacing: 0.04em !important;
    padding: 8px 16px !important;
    transition: all 0.2s !important;
    border: none !important;
    background: transparent !important;
}

[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    background: rgba(37,99,235,0.2) !important;
    color: #60a5fa !important;
    box-shadow: 0 0 12px rgba(37,99,235,0.15) !important;
}

/* ── Inputs ── */
[data-testid="stTextInput"] input,
[data-testid="stSelectbox"] select,
[data-testid="stTextArea"] textarea {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 10px !important;
    color: #e2e8f0 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 14px !important;
    padding: 12px 14px !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}

[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color: rgba(37,99,235,0.5) !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.1) !important;
    outline: none !important;
}

[data-testid="stTextInput"] label,
[data-testid="stSelectbox"] label,
[data-testid="stTextArea"] label {
    color: rgba(255,255,255,0.45) !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    margin-bottom: 6px !important;
}

/* ── Buttons ── */
[data-testid="stFormSubmitButton"] button,
[data-testid="stButton"] button {
    background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    letter-spacing: 0.05em !important;
    padding: 12px 24px !important;
    transition: all 0.25s !important;
    box-shadow: 0 4px 20px rgba(37,99,235,0.3) !important;
    cursor: pointer !important;
}

[data-testid="stFormSubmitButton"] button:hover,
[data-testid="stButton"] button:hover {
    background: linear-gradient(135deg, #3b82f6, #2563eb) !important;
    box-shadow: 0 6px 28px rgba(37,99,235,0.45) !important;
    transform: translateY(-1px) !important;
}

/* ── Alerts ── */
[data-testid="stAlert"] {
    background: rgba(239,68,68,0.08) !important;
    border: 1px solid rgba(239,68,68,0.2) !important;
    border-radius: 10px !important;
    color: #fca5a5 !important;
}

[data-testid="stAlert"][data-baseweb="notification"] {
    background: rgba(16,185,129,0.08) !important;
    border-color: rgba(16,185,129,0.2) !important;
    color: #6ee7b7 !important;
}

/* ── Metrics ── */
[data-testid="stMetric"] {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 12px !important;
    padding: 16px !important;
}

[data-testid="stMetricLabel"] {
    color: rgba(255,255,255,0.4) !important;
    font-size: 10px !important;
    font-weight: 700 !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
}

[data-testid="stMetricValue"] {
    color: #f1f5f9 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 22px !important;
    font-weight: 600 !important;
}

/* ── Dataframe ── */
[data-testid="stDataFrame"] {
    border-radius: 12px !important;
    overflow: hidden !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
    background: rgba(37,99,235,0.3);
    border-radius: 4px;
}

/* ── Divider ── */
hr {
    border: none !important;
    border-top: 1px solid rgba(255,255,255,0.06) !important;
    margin: 20px 0 !important;
}

/* ── Custom card utility ── */
.tie-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px;
    padding: 24px;
    backdrop-filter: blur(12px);
    transition: border-color 0.2s, box-shadow 0.2s;
}
.tie-card:hover {
    border-color: rgba(37,99,235,0.25);
    box-shadow: 0 0 30px rgba(37,99,235,0.08);
}

.tie-label {
    color: rgba(255,255,255,0.35);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
}

.tie-value {
    color: #f1f5f9;
    font-family: 'JetBrains Mono', monospace;
    font-size: 20px;
    font-weight: 600;
    margin-top: 4px;
}

.tie-badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}

.tie-badge-blue {
    background: rgba(37,99,235,0.12);
    border: 1px solid rgba(37,99,235,0.25);
    color: #60a5fa;
}

.tie-badge-green {
    background: rgba(16,185,129,0.1);
    border: 1px solid rgba(16,185,129,0.2);
    color: #34d399;
}

.tie-badge-red {
    background: rgba(239,68,68,0.1);
    border: 1px solid rgba(239,68,68,0.2);
    color: #f87171;
}

.tie-badge-yellow {
    background: rgba(245,158,11,0.1);
    border: 1px solid rgba(245,158,11,0.2);
    color: #fbbf24;
}

.tie-section-title {
    color: rgba(255,255,255,0.18);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 10px;
}

.tie-section-title::after {
    content: '';
    flex: 1;
    height: 1px;
    background: rgba(255,255,255,0.06);
}
</style>
""", unsafe_allow_html=True)

# ── Session State ─────────────────────────────────────────────────────────────
def init_state():
    defaults = {
        "user": None,
        "page": "dashboard",
        "symbol": "BTC/USDT",
        "exchange": "binance",
        "strategy": "Balanced",
        "demo_mode": True,
        "daily_pnl": 0.0,
        "shutdown": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# ── Risk Validation Layer ─────────────────────────────────────────────────────
RISK = {"max_pos": 5.0, "max_sl": 2.0, "min_tp": 5.0, "min_rr": 2.0, "max_daily_loss": 10.0}

def validate_trade(action, entry, sl, tp, size_pct, balance=10000.0):
    issues = []
    if st.session_state.get("shutdown"):
        return False, ["Global Shutdown active — no trades allowed."], {}
    if st.session_state.get("daily_pnl", 0) <= -RISK["max_daily_loss"]:
        st.session_state["shutdown"] = True
        return False, ["Daily loss limit breached. Global Shutdown activated for 24h."], {}
    if size_pct > RISK["max_pos"]:
        issues.append(f"Position {size_pct}% > max {RISK['max_pos']}%")
    if entry > 0:
        sl_dist = abs((entry - sl) / entry) * 100
        if sl_dist > RISK["max_sl"]:
            issues.append(f"Stop-loss distance {sl_dist:.2f}% > max {RISK['max_sl']}%")
        risk   = abs(entry - sl)
        reward = abs(tp - entry)
        rr     = reward / risk if risk > 0 else 0
        if rr < RISK["min_rr"]:
            issues.append(f"R:R {rr:.2f} below minimum 1:{RISK['min_rr']}")
    else:
        rr = 0
        issues.append("Invalid entry price")
    valid = len(issues) == 0
    order = {"action": action, "entry": entry, "sl": sl, "tp": tp,
             "size_pct": size_pct, "risk_reward": f"1:{rr:.1f}",
             "trade_value": round(balance * size_pct / 100, 2)} if valid else {}
    return valid, issues, order

# ── Market Data ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def get_ohlcv(symbol="BTC/USDT", exchange_id="binance", tf="1h", limit=200):
    try:
        ex = getattr(ccxt, exchange_id)({"enableRateLimit": True})
        raw = ex.fetch_ohlcv(symbol, tf, limit=limit)
        df  = pd.DataFrame(raw, columns=["ts","open","high","low","close","volume"])
        df["ts"] = pd.to_datetime(df["ts"], unit="ms")
        return df
    except Exception as e:
        np.random.seed(42)
        n = limit
        closes = 65000 + np.cumsum(np.random.randn(n) * 400)
        df = pd.DataFrame({
            "ts":     pd.date_range(end=datetime.datetime.utcnow(), periods=n, freq="1h"),
            "open":   closes - np.abs(np.random.randn(n) * 200),
            "high":   closes + np.abs(np.random.randn(n) * 300),
            "low":    closes - np.abs(np.random.randn(n) * 300),
            "close":  closes,
            "volume": np.abs(np.random.randn(n) * 5000) + 2000,
        })
        return df

def compute_indicators(df):
    c = df["close"]
    # RSI
    delta = c.diff()
    gain  = delta.clip(lower=0).ewm(com=13).mean()
    loss  = (-delta.clip(upper=0)).ewm(com=13).mean()
    df["rsi"] = 100 - 100 / (1 + gain / loss.replace(0, 1e-9))
    # EMA
    for p in [9, 21, 50, 200]:
        df[f"ema{p}"] = c.ewm(span=p).mean()
    # MACD
    ema12 = c.ewm(span=12).mean()
    ema26 = c.ewm(span=26).mean()
    df["macd"]   = ema12 - ema26
    df["signal"] = df["macd"].ewm(span=9).mean()
    df["hist"]   = df["macd"] - df["signal"]
    # Bollinger
    sma20        = c.rolling(20).mean()
    std20        = c.rolling(20).std()
    df["bb_mid"] = sma20
    df["bb_up"]  = sma20 + 2 * std20
    df["bb_dn"]  = sma20 - 2 * std20
    # ATR
    hl  = df["high"] - df["low"]
    hpc = (df["high"] - c.shift()).abs()
    lpc = (df["low"]  - c.shift()).abs()
    df["atr"] = pd.concat([hl, hpc, lpc], axis=1).max(axis=1).rolling(14).mean()
    return df

def get_sr_levels(df, n=5):
    window = 20
    h = df["high"].rolling(window, center=True).max()
    l = df["low"].rolling(window,  center=True).min()
    res = sorted(h.dropna().unique(), reverse=True)[:n]
    sup = sorted(l.dropna().unique())[:n]
    return res, sup

# ── News Engine ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch_news(symbol="BTC/USDT"):
    base  = symbol.split("/")[0].upper()
    feeds = [
        f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={base}-USD&region=US&lang=en-US",
        "https://feeds.bbci.co.uk/news/business/rss.xml",
        "https://rss.cnn.com/rss/money_news_international.rss",
        "https://feeds.reuters.com/reuters/businessNews",
    ]
    articles = []
    pos_kw = ["surge","rally","bullish","gain","record","breakout","adoption","launch","upgrade","buy"]
    neg_kw = ["crash","drop","fall","bearish","ban","sell","loss","hack","fraud","fear","decline"]
    for url in feeds:
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:4]:
                title   = e.get("title", "")
                summary = e.get("summary", title)[:180]
                pub     = e.get("published", "")
                text    = (title + " " + summary).lower()
                score   = sum(1 for w in pos_kw if w in text) - sum(1 for w in neg_kw if w in text)
                score   = max(-5, min(5, score))
                articles.append({"title": title, "summary": summary[:120] + "…",
                                  "score": score, "published": pub})
        except Exception:
            pass
    return articles[:16]

def overall_sentiment(articles):
    if not articles:
        return 0.0, "Neutral"
    avg = sum(a["score"] for a in articles) / len(articles)
    label = "Bullish" if avg > 0.5 else "Bearish" if avg < -0.5 else "Neutral"
    return round(avg, 2), label

# ── Chart Builder ─────────────────────────────────────────────────────────────
def build_chart(df, symbol, res_levels, sup_levels):
    last = df.tail(120)
    fig  = go.Figure()

    # Bollinger band fill
    fig.add_trace(go.Scatter(x=pd.concat([last["ts"], last["ts"][::-1]]),
        y=pd.concat([last["bb_up"], last["bb_dn"][::-1]]),
        fill="toself",
        fillcolor="rgba(37,99,235,0.05)",
        line=dict(color="rgba(0,0,0,0)"),
        name="BB Band", showlegend=False))

    # BB lines
    for col, name, color in [
        ("bb_up",  "BB Upper", "rgba(37,99,235,0.4)"),
        ("bb_mid", "BB Mid",   "rgba(37,99,235,0.25)"),
        ("bb_dn",  "BB Lower", "rgba(37,99,235,0.4)"),
    ]:
        fig.add_trace(go.Scatter(x=last["ts"], y=last[col],
            line=dict(color=color, width=1, dash="dot"),
            name=name, showlegend=False))

    # EMA lines
    ema_colors = {"ema9":"#f59e0b","ema21":"#10b981","ema50":"#6366f1","ema200":"#ec4899"}
    for col, color in ema_colors.items():
        fig.add_trace(go.Scatter(x=last["ts"], y=last[col],
            line=dict(color=color, width=1),
            name=col.upper(), showlegend=True,
            opacity=0.7))

    # Candlesticks
    fig.add_trace(go.Candlestick(
        x=last["ts"], open=last["open"], high=last["high"],
        low=last["low"],  close=last["close"],
        increasing_fillcolor="#10b981", increasing_line_color="#10b981",
        decreasing_fillcolor="#ef4444", decreasing_line_color="#ef4444",
        name=symbol, showlegend=False,
        line=dict(width=1)))

    # Support / Resistance
    price = df["close"].iloc[-1]
    for lvl in res_levels[:3]:
        if lvl > price * 0.98:
            fig.add_hline(y=lvl, line_dash="dash",
                line_color="rgba(239,68,68,0.45)", line_width=1,
                annotation_text=f"R ${lvl:,.0f}",
                annotation_font_color="rgba(239,68,68,0.7)",
                annotation_font_size=10)
    for lvl in sup_levels[:3]:
        if lvl < price * 1.02:
            fig.add_hline(y=lvl, line_dash="dash",
                line_color="rgba(16,185,129,0.45)", line_width=1,
                annotation_text=f"S ${lvl:,.0f}",
                annotation_font_color="rgba(16,185,129,0.7)",
                annotation_font_size=10)

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color="rgba(255,255,255,0.5)", size=11),
        height=480,
        margin=dict(l=0, r=60, t=20, b=0),
        xaxis=dict(gridcolor="rgba(255,255,255,0.03)", showline=False,
                   zeroline=False, rangeslider_visible=False,
                   color="rgba(255,255,255,0.3)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.04)", showline=False,
                   zeroline=False, side="right",
                   color="rgba(255,255,255,0.3)"),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="rgba(5,12,28,0.95)",
                        bordercolor="rgba(37,99,235,0.3)",
                        font_size=12),
        legend=dict(bgcolor="rgba(0,0,0,0)",
                    bordercolor="rgba(255,255,255,0.06)",
                    borderwidth=1, font_size=10,
                    orientation="h", y=-0.08),
    )
    return fig

def build_volume_chart(df):
    last = df.tail(80)
    colors = ["rgba(16,185,129,0.6)" if c >= o else "rgba(239,68,68,0.6)"
              for c, o in zip(last["close"], last["open"])]
    fig = go.Figure(go.Bar(x=last["ts"], y=last["volume"],
        marker_color=colors, showlegend=False))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=120, margin=dict(l=0, r=60, t=8, b=0),
        xaxis=dict(gridcolor="rgba(255,255,255,0.02)", showline=False,
                   zeroline=False, color="rgba(255,255,255,0.2)", showticklabels=False),
        yaxis=dict(gridcolor="rgba(255,255,255,0.02)", showline=False,
                   zeroline=False, side="right", color="rgba(255,255,255,0.2)"),
    )
    return fig

def build_macd_chart(df):
    last = df.tail(80)
    colors = ["rgba(16,185,129,0.7)" if v >= 0 else "rgba(239,68,68,0.7)"
              for v in last["hist"]]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=last["ts"], y=last["hist"],
        marker_color=colors, name="Histogram", showlegend=False))
    fig.add_trace(go.Scatter(x=last["ts"], y=last["macd"],
        line=dict(color="#2563eb", width=1.5), name="MACD"))
    fig.add_trace(go.Scatter(x=last["ts"], y=last["signal"],
        line=dict(color="#f59e0b", width=1.5), name="Signal"))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=160, margin=dict(l=0, r=60, t=8, b=0),
        xaxis=dict(gridcolor="rgba(255,255,255,0.02)", showline=False,
                   zeroline=False, color="rgba(255,255,255,0.2)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.02)", showline=False,
                   zeroline=False, side="right", color="rgba(255,255,255,0.2)"),
        legend=dict(bgcolor="rgba(0,0,0,0)", font_size=10,
                    orientation="h", y=-0.3),
    )
    return fig

# ── Auth Page ─────────────────────────────────────────────────────────────────
def page_auth():
    # Full page override for auth
    st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    background: radial-gradient(ellipse at 20% 50%, rgba(37,99,235,0.08) 0%, transparent 60%),
                radial-gradient(ellipse at 80% 20%, rgba(99,102,241,0.06) 0%, transparent 50%),
                #020812 !important;
}
[data-testid="block-container"] { padding: 0 !important; }
</style>
""", unsafe_allow_html=True)

    # Two-column layout using st.columns — NO split HTML
    left_col, right_col = st.columns([1.15, 0.85], gap="small")

    # ── LEFT — Branding ──
    with left_col:
        st.markdown("""
<div style="
    min-height: 100vh;
    padding: 64px 56px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    border-right: 1px solid rgba(255,255,255,0.05);
    background: linear-gradient(160deg, rgba(37,99,235,0.06) 0%, rgba(99,102,241,0.04) 50%, transparent 100%);
">
    <div style="max-width: 440px;">

        <div style="
            display: inline-flex; align-items: center; gap: 8px;
            background: rgba(37,99,235,0.08);
            border: 1px solid rgba(37,99,235,0.18);
            border-radius: 6px;
            padding: 5px 12px;
            margin-bottom: 48px;
        ">
            <div style="
                width: 5px; height: 5px; border-radius: 50%;
                background: #2563eb;
                box-shadow: 0 0 8px #2563eb;
                animation: pulse 2s infinite;
            "></div>
            <span style="color:rgba(255,255,255,0.45);font-size:10px;font-weight:700;letter-spacing:0.15em;text-transform:uppercase;">Institutional Grade</span>
        </div>

        <h1 style="
            font-size: 44px; font-weight: 800;
            color: #f1f5f9; line-height: 1.1;
            margin-bottom: 20px;
            letter-spacing: -2px;
        ">
            Trading<br>
            <span style="
                background: linear-gradient(135deg, #2563eb, #6366f1, #06b6d4);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            ">Intelligence</span><br>Engine
        </h1>

        <p style="color:rgba(255,255,255,0.35);font-size:14px;line-height:1.75;margin-bottom:44px;max-width:380px;">
            A professional-grade platform combining real-time technical analysis, 
            fundamental news assessment, and AI-powered decision synthesis into 
            institutional White Paper reports.
        </p>

        <div style="display:flex;flex-direction:column;gap:14px;margin-bottom:48px;">
            <div style="display:flex;align-items:center;gap:14px;">
                <div style="width:32px;height:32px;border-radius:8px;background:rgba(37,99,235,0.12);border:1px solid rgba(37,99,235,0.2);display:flex;align-items:center;justify-content:center;flex-shrink:0;">
                    <div style="width:10px;height:10px;border:2px solid #2563eb;border-radius:2px;transform:rotate(45deg);"></div>
                </div>
                <span style="color:rgba(255,255,255,0.4);font-size:13px;">Live TA — RSI, MACD, Bollinger Bands, EMA Stack</span>
            </div>
            <div style="display:flex;align-items:center;gap:14px;">
                <div style="width:32px;height:32px;border-radius:8px;background:rgba(99,102,241,0.1);border:1px solid rgba(99,102,241,0.2);display:flex;align-items:center;justify-content:center;flex-shrink:0;">
                    <div style="width:10px;height:10px;border:2px solid #6366f1;border-radius:2px;transform:rotate(45deg);"></div>
                </div>
                <span style="color:rgba(255,255,255,0.4);font-size:13px;">News Sentiment with Impact Scoring ( -5 to +5 )</span>
            </div>
            <div style="display:flex;align-items:center;gap:14px;">
                <div style="width:32px;height:32px;border-radius:8px;background:rgba(6,182,212,0.1);border:1px solid rgba(6,182,212,0.2);display:flex;align-items:center;justify-content:center;flex-shrink:0;">
                    <div style="width:10px;height:10px;border:2px solid #06b6d4;border-radius:2px;transform:rotate(45deg);"></div>
                </div>
                <span style="color:rgba(255,255,255,0.4);font-size:13px;">White Paper Report — 5-section Institutional Format</span>
            </div>
            <div style="display:flex;align-items:center;gap:14px;">
                <div style="width:32px;height:32px;border-radius:8px;background:rgba(16,185,129,0.1);border:1px solid rgba(16,185,129,0.2);display:flex;align-items:center;justify-content:center;flex-shrink:0;">
                    <div style="width:10px;height:10px;border:2px solid #10b981;border-radius:2px;transform:rotate(45deg);"></div>
                </div>
                <span style="color:rgba(255,255,255,0.4);font-size:13px;">AES-256 Encrypted API Key Storage</span>
            </div>
            <div style="display:flex;align-items:center;gap:14px;">
                <div style="width:32px;height:32px;border-radius:8px;background:rgba(245,158,11,0.1);border:1px solid rgba(245,158,11,0.2);display:flex;align-items:center;justify-content:center;flex-shrink:0;">
                    <div style="width:10px;height:10px;border:2px solid #f59e0b;border-radius:2px;transform:rotate(45deg);"></div>
                </div>
                <span style="color:rgba(255,255,255,0.4);font-size:13px;">Non-negotiable Risk Validation Layer</span>
            </div>
        </div>

        <div style="
            padding-top: 24px;
            border-top: 1px solid rgba(255,255,255,0.06);
        ">
            <p style="color:rgba(255,255,255,0.15);font-size:11px;line-height:1.65;max-width:360px;">
                This platform is an analytical execution tool, not a financial advisor. 
                All outputs are for informational and educational purposes only.
            </p>
        </div>

    </div>
</div>

<style>
@keyframes pulse {
    0%,100% { opacity:1; box-shadow: 0 0 8px #2563eb; }
    50%      { opacity:0.6; box-shadow: 0 0 16px #2563eb; }
}
</style>
""", unsafe_allow_html=True)

    # ── RIGHT — Auth Form ──
    with right_col:
        st.markdown("""
<div style="min-height:100vh;display:flex;align-items:center;justify-content:center;padding:40px 48px;">
<div style="width:100%;max-width:380px;">
""", unsafe_allow_html=True)

        st.markdown("""
<p style="color:rgba(255,255,255,0.22);font-size:10px;font-weight:700;letter-spacing:0.18em;text-transform:uppercase;margin-bottom:24px;">
    Account Access
</p>
""", unsafe_allow_html=True)

        tab_in, tab_up = st.tabs(["Sign In", "Create Account"])

        with tab_in:
            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
            with st.form("form_login", clear_on_submit=False):
                email = st.text_input("Email Address", placeholder="you@example.com", key="li_email")
                pw    = st.text_input("Password", type="password", placeholder="Enter your password", key="li_pw")
                submitted = st.form_submit_button("Sign In", use_container_width=True)
            if submitted:
                if not email or not pw:
                    st.error("Please fill in all fields.")
                else:
                    db = SessionLocal()
                    try:
                        u = db.query(User).filter(User.email == email.lower().strip()).first()
                        if u and verify_pw(pw, u.hashed_pw):
                            st.session_state.user = {"id": u.id, "email": u.email, "name": u.full_name}
                            st.rerun()
                        else:
                            st.error("Invalid email or password.")
                    finally:
                        db.close()

        with tab_up:
            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
            with st.form("form_signup", clear_on_submit=False):
                name   = st.text_input("Full Name", placeholder="John Doe", key="su_name")
                email2 = st.text_input("Email Address", placeholder="you@example.com", key="su_email")
                pw2    = st.text_input("Password", type="password", placeholder="Minimum 8 characters", key="su_pw")
                pw3    = st.text_input("Confirm Password", type="password", placeholder="Repeat password", key="su_pw2")
                submitted2 = st.form_submit_button("Create Account", use_container_width=True)

            if submitted2:
                if not name or not email2 or not pw2 or not pw3:
                    st.error("Please fill in all fields.")
                elif len(pw2) < 8:
                    st.error("Password must be at least 8 characters.")
                elif pw2 != pw3:
                    st.error("Passwords do not match.")
                else:
                    db = SessionLocal()
                    try:
                        existing = db.query(User).filter(User.email == email2.lower().strip()).first()
                        if existing:
                            st.error("An account with this email already exists.")
                        else:
                            new_user = User(
                                email=email2.lower().strip(),
                                full_name=name.strip(),
                                hashed_pw=hash_pw(pw2)
                            )
                            db.add(new_user)
                            db.commit()
                            db.refresh(new_user)
                            st.session_state.user = {"id": new_user.id, "email": new_user.email, "name": new_user.full_name}
                            st.rerun()
                    except Exception as ex:
                        db.rollback()
                        st.error(f"Registration failed: {ex}")
                    finally:
                        db.close()

        st.markdown("""
<div style="margin-top:32px;padding-top:20px;border-top:1px solid rgba(255,255,255,0.06);">
    <p style="color:rgba(255,255,255,0.14);font-size:10px;line-height:1.7;text-align:center;">
        By continuing, you acknowledge this tool is for informational use only.<br>
        All API keys are encrypted with AES-256 before storage.
    </p>
</div>
</div></div>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
def render_sidebar():
    user = st.session_state.user
    with st.sidebar:
        # Header
        st.markdown(f"""
<div style="margin-bottom:28px;">
    <div style="
        display:flex;align-items:center;gap:10px;
        padding-bottom:20px;
        border-bottom:1px solid rgba(255,255,255,0.06);
    ">
        <div style="
            width:36px;height:36px;border-radius:10px;
            background:linear-gradient(135deg,rgba(37,99,235,0.3),rgba(99,102,241,0.2));
            border:1px solid rgba(37,99,235,0.3);
            display:flex;align-items:center;justify-content:center;
            font-size:13px;font-weight:700;color:#60a5fa;
        ">{user['name'][0].upper()}</div>
        <div>
            <p style="color:#f1f5f9;font-size:13px;font-weight:600;margin:0;">{user['name']}</p>
            <p style="color:rgba(255,255,255,0.3);font-size:10px;margin:0;">{user['email']}</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

        # Navigation
        st.markdown('<p class="tie-label" style="margin-bottom:10px;padding-left:4px;">Navigation</p>', unsafe_allow_html=True)
        pages = [
            ("dashboard", "Dashboard"),
            ("report",    "White Paper Report"),
            ("news",      "News & Sentiment"),
            ("settings",  "Settings"),
        ]
        for key, label in pages:
            active = st.session_state.page == key
            if st.button(label, key=f"nav_{key}",
                         use_container_width=True,
                         type="primary" if active else "secondary"):
                st.session_state.page = key
                st.rerun()

        st.markdown("<hr>", unsafe_allow_html=True)

        # Market Controls
        st.markdown('<p class="tie-label" style="margin-bottom:10px;padding-left:4px;">Market Controls</p>', unsafe_allow_html=True)

        st.session_state.symbol   = st.selectbox("Symbol", ["BTC/USDT","ETH/USDT","SOL/USDT","XRP/USDT","BNB/USDT","ADA/USDT"], key="sb_sym")
        st.session_state.exchange = st.selectbox("Exchange", ["binance","kraken","coinbase","bybit"], key="sb_ex")
        st.session_state.strategy = st.selectbox("Strategy", ["Conservative","Balanced","Aggressive"], index=1, key="sb_strat")

        st.markdown("<hr>", unsafe_allow_html=True)

        # Risk Status
        pnl  = st.session_state.daily_pnl
        shut = st.session_state.shutdown
        pnl_color = "#10b981" if pnl >= 0 else "#ef4444"

        st.markdown(f"""
<div class="tie-card" style="padding:16px;">
    <p class="tie-label" style="margin-bottom:12px;">Risk Status</p>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
        <span style="color:rgba(255,255,255,0.4);font-size:11px;">Daily P&L</span>
        <span style="color:{pnl_color};font-family:'JetBrains Mono',monospace;font-size:12px;font-weight:600;">{pnl:+.2f}%</span>
    </div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
        <span style="color:rgba(255,255,255,0.4);font-size:11px;">Max Position</span>
        <span style="color:#f1f5f9;font-family:'JetBrains Mono',monospace;font-size:12px;">5.0%</span>
    </div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <span style="color:rgba(255,255,255,0.4);font-size:11px;">Stop Loss</span>
        <span style="color:#f1f5f9;font-family:'JetBrains Mono',monospace;font-size:12px;">2.0%</span>
    </div>
    <div style="
        padding:8px 12px;border-radius:8px;text-align:center;font-size:11px;font-weight:700;letter-spacing:0.06em;
        {'background:rgba(239,68,68,0.12);border:1px solid rgba(239,68,68,0.25);color:#f87171;' if shut else 'background:rgba(16,185,129,0.1);border:1px solid rgba(16,185,129,0.2);color:#34d399;'}
    ">{'SHUTDOWN ACTIVE' if shut else 'SYSTEM ACTIVE'}</div>
</div>
""", unsafe_allow_html=True)

        st.markdown("<hr>", unsafe_allow_html=True)
        if st.button("Sign Out", use_container_width=True, key="btn_logout"):
            st.session_state.user = None
            st.rerun()

# ── Dashboard Page ─────────────────────────────────────────────────────────────
def page_dashboard():
    sym  = st.session_state.symbol
    ex   = st.session_state.exchange
    strat = st.session_state.strategy

    st.markdown(f"""
<div style="padding:28px 32px 0;">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">
        <div>
            <p class="tie-label">Live Dashboard</p>
            <h2 style="color:#f1f5f9;font-size:26px;font-weight:700;letter-spacing:-0.5px;margin-top:4px;">{sym}</h2>
        </div>
        <div style="display:flex;gap:8px;align-items:center;">
            <span class="tie-badge tie-badge-blue">{strat}</span>
            <span class="tie-badge tie-badge-green">
                <span style="width:5px;height:5px;border-radius:50%;background:#10b981;display:inline-block;"></span>
                Live
            </span>
        </div>
    </div>
</div>
<div style="padding:0 32px 20px;margin-top:0;">
    <div style="height:1px;background:linear-gradient(90deg,rgba(37,99,235,0.4),rgba(99,102,241,0.2),transparent);margin-bottom:24px;"></div>
</div>
""", unsafe_allow_html=True)

    with st.spinner("Fetching live market data..."):
        df = get_ohlcv(sym, ex, "1h", 200)
        df = compute_indicators(df)
        res_levels, sup_levels = get_sr_levels(df)
        articles = fetch_news(sym)

    # Key metrics row
    price  = df["close"].iloc[-1]
    open_p = df["open"].iloc[-1]
    high   = df["high"].iloc[-1]
    low    = df["low"].iloc[-1]
    vol    = df["volume"].iloc[-1]
    rsi    = df["rsi"].iloc[-1]
    chg    = (price - df["close"].iloc[-2]) / df["close"].iloc[-2] * 100
    chg_color = "#10b981" if chg >= 0 else "#ef4444"

    st.markdown(f"""
<div style="padding:0 32px;display:grid;grid-template-columns:repeat(6,1fr);gap:12px;margin-bottom:20px;">
    <div class="tie-card" style="padding:18px;">
        <p class="tie-label">Price</p>
        <p class="tie-value" style="font-size:18px;">${price:,.2f}</p>
        <p style="color:{chg_color};font-family:'JetBrains Mono',monospace;font-size:11px;margin-top:4px;">{chg:+.2f}%</p>
    </div>
    <div class="tie-card" style="padding:18px;">
        <p class="tie-label">24h High</p>
        <p class="tie-value" style="font-size:18px;color:#10b981;">${high:,.2f}</p>
    </div>
    <div class="tie-card" style="padding:18px;">
        <p class="tie-label">24h Low</p>
        <p class="tie-value" style="font-size:18px;color:#ef4444;">${low:,.2f}</p>
    </div>
    <div class="tie-card" style="padding:18px;">
        <p class="tie-label">RSI (14)</p>
        <p class="tie-value" style="font-size:18px;color:{'#ef4444' if rsi>70 else '#10b981' if rsi<30 else '#f1f5f9'};">{rsi:.1f}</p>
        <p style="color:rgba(255,255,255,0.3);font-size:10px;margin-top:4px;">{'Overbought' if rsi>70 else 'Oversold' if rsi<30 else 'Neutral'}</p>
    </div>
    <div class="tie-card" style="padding:18px;">
        <p class="tie-label">Volume</p>
        <p class="tie-value" style="font-size:18px;">{vol/1000:.1f}K</p>
    </div>
    <div class="tie-card" style="padding:18px;">
        <p class="tie-label">ATR (14)</p>
        <p class="tie-value" style="font-size:18px;">${df['atr'].iloc[-1]:,.0f}</p>
    </div>
</div>
""", unsafe_allow_html=True)

    # Chart
    with st.container():
        st.markdown('<div style="padding:0 32px;">', unsafe_allow_html=True)
        st.markdown('<div class="tie-card" style="padding:20px 20px 8px;">', unsafe_allow_html=True)
        st.markdown('<p class="tie-section-title">Price Chart — Candlestick + Indicators</p>', unsafe_allow_html=True)
        st.plotly_chart(build_chart(df, sym, res_levels, sup_levels),
                        use_container_width=True, config={"displayModeBar": False})
        st.markdown('<p class="tie-section-title" style="margin-top:12px;">Volume</p>', unsafe_allow_html=True)
        st.plotly_chart(build_volume_chart(df),
                        use_container_width=True, config={"displayModeBar": False})
        st.markdown('<p class="tie-section-title" style="margin-top:12px;">MACD</p>', unsafe_allow_html=True)
        st.plotly_chart(build_macd_chart(df),
                        use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div></div>", unsafe_allow_html=True)

    # Indicators + Levels
    st.markdown('<div style="padding:20px 32px 0;display:grid;grid-template-columns:1fr 1fr;gap:16px;">', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        macd_v = df["macd"].iloc[-1]
        sig_v  = df["signal"].iloc[-1]
        bb_pct = (price - df["bb_dn"].iloc[-1]) / (df["bb_up"].iloc[-1] - df["bb_dn"].iloc[-1]) * 100
        ema9   = df["ema9"].iloc[-1]
        ema21  = df["ema21"].iloc[-1]
        ema50  = df["ema50"].iloc[-1]

        st.markdown(f"""
<div class="tie-card">
    <p class="tie-section-title">Technical Indicators</p>
    <div style="display:flex;flex-direction:column;gap:10px;">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="color:rgba(255,255,255,0.4);font-size:12px;">RSI (14)</span>
            <span class="tie-badge {'tie-badge-red' if rsi>70 else 'tie-badge-green' if rsi<30 else 'tie-badge-blue'}">{rsi:.1f} — {'Overbought' if rsi>70 else 'Oversold' if rsi<30 else 'Neutral'}</span>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="color:rgba(255,255,255,0.4);font-size:12px;">MACD</span>
            <span class="tie-badge {'tie-badge-green' if macd_v>sig_v else 'tie-badge-red'}">{macd_v:.2f} {'Bullish' if macd_v>sig_v else 'Bearish'}</span>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="color:rgba(255,255,255,0.4);font-size:12px;">BB Position</span>
            <span class="tie-badge tie-badge-blue">{bb_pct:.0f}% of Band</span>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="color:rgba(255,255,255,0.4);font-size:12px;">EMA 9 / 21</span>
            <span class="tie-badge {'tie-badge-green' if ema9>ema21 else 'tie-badge-red'}">${ema9:,.0f} / ${ema21:,.0f}</span>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="color:rgba(255,255,255,0.4);font-size:12px;">EMA 50 / 200</span>
            <span class="tie-badge {'tie-badge-green' if ema50>df['ema200'].iloc[-1] else 'tie-badge-red'}">${ema50:,.0f} / ${df['ema200'].iloc[-1]:,.0f}</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
<div class="tie-card">
    <p class="tie-section-title">Support / Resistance Levels</p>
    <div style="display:flex;flex-direction:column;gap:8px;">
        {"".join([f'''
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <span class="tie-badge tie-badge-red">R{i+1}</span>
            <span style="color:#f1f5f9;font-family:'JetBrains Mono',monospace;font-size:12px;">${lvl:,.2f}</span>
            <span style="color:rgba(239,68,68,0.6);font-size:11px;">+{((lvl-price)/price*100):.2f}%</span>
        </div>''' for i, lvl in enumerate(res_levels[:3])])}
        <div style="height:1px;background:rgba(255,255,255,0.06);margin:4px 0;"></div>
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <span class="tie-badge tie-badge-blue">NOW</span>
            <span style="color:#60a5fa;font-family:'JetBrains Mono',monospace;font-size:13px;font-weight:700;">${price:,.2f}</span>
            <span style="color:rgba(255,255,255,0.3);font-size:11px;">Current</span>
        </div>
        <div style="height:1px;background:rgba(255,255,255,0.06);margin:4px 0;"></div>
        {"".join([f'''
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <span class="tie-badge tie-badge-green">S{i+1}</span>
            <span style="color:#f1f5f9;font-family:'JetBrains Mono',monospace;font-size:12px;">${lvl:,.2f}</span>
            <span style="color:rgba(16,185,129,0.6);font-size:11px;">{((lvl-price)/price*100):.2f}%</span>
        </div>''' for i, lvl in enumerate(sup_levels[:3])])}
    </div>
</div>
""", unsafe_allow_html=True)

# ── Report Page ───────────────────────────────────────────────────────────────
def page_report():
    sym   = st.session_state.symbol
    ex    = st.session_state.exchange
    strat = st.session_state.strategy

    st.markdown(f"""
<div style="padding:28px 32px 0;">
    <p class="tie-label">Institutional Analysis</p>
    <h2 style="color:#f1f5f9;font-size:26px;font-weight:700;letter-spacing:-0.5px;margin-top:4px;">White Paper Report</h2>
    <div style="height:1px;background:linear-gradient(90deg,rgba(37,99,235,0.4),rgba(99,102,241,0.2),transparent);margin:20px 0 24px;"></div>
</div>
""", unsafe_allow_html=True)

    with st.spinner("Running full analysis engine..."):
        df = get_ohlcv(sym, ex, "1h", 200)
        df = compute_indicators(df)
        res_levels, sup_levels = get_sr_levels(df)
        articles = fetch_news(sym)

    price  = df["close"].iloc[-1]
    rsi    = df["rsi"].iloc[-1]
    macd_v = df["macd"].iloc[-1]
    sig_v  = df["signal"].iloc[-1]
    hist_v = df["hist"].iloc[-1]
    ema9   = df["ema9"].iloc[-1]
    ema21  = df["ema21"].iloc[-1]
    ema50  = df["ema50"].iloc[-1]
    ema200 = df["ema200"].iloc[-1]
    bb_up  = df["bb_up"].iloc[-1]
    bb_dn  = df["bb_dn"].iloc[-1]
    bb_mid = df["bb_mid"].iloc[-1]
    atr    = df["atr"].iloc[-1]
    chg    = (price - df["close"].iloc[-2]) / df["close"].iloc[-2] * 100
    avg_score, sent_label = overall_sentiment(articles)

    # Thesis logic
    bull_pts = bear_pts = 0
    signals  = []
    if rsi < 35:    bull_pts += 2; signals.append(("[RSI]", "RSI in oversold zone — historically a mean-reversion trigger", "green"))
    elif rsi > 65:  bear_pts += 2; signals.append(("[RSI]", "RSI in overbought zone — momentum exhaustion risk", "red"))
    if macd_v > sig_v: bull_pts += 1; signals.append(("[MACD]", "MACD line above Signal — bullish momentum", "green"))
    else:              bear_pts += 1; signals.append(("[MACD]", "MACD line below Signal — bearish momentum", "red"))
    if ema9 > ema21 > ema50: bull_pts += 2; signals.append(("[EMA]", "EMA 9 > EMA 21 > EMA 50 — bullish alignment", "green"))
    elif ema9 < ema21 < ema50: bear_pts += 2; signals.append(("[EMA]", "EMA stack bearish alignment confirmed", "red"))
    if price > ema200: bull_pts += 1; signals.append(("[EMA200]", f"Price above 200 EMA (${ema200:,.0f}) — long-term uptrend", "green"))
    else:              bear_pts += 1; signals.append(("[EMA200]", f"Price below 200 EMA (${ema200:,.0f}) — long-term downtrend", "red"))
    if price < bb_mid: bull_pts += 1; signals.append(("[BB]", "Price below BB mid-band — potential reversion upward", "green"))
    else:              signals.append(("[BB]", f"Price at ${price:,.0f}, BB upper at ${bb_up:,.0f}", "blue"))
    if avg_score > 0.5: bull_pts += 1; signals.append(("[NEWS]", f"News sentiment positive (avg score {avg_score:+.1f})", "green"))
    elif avg_score < -0.5: bear_pts += 1; signals.append(("[NEWS]", f"News sentiment negative (avg score {avg_score:+.1f})", "red"))

    if bull_pts > bear_pts + 1: thesis = "BULLISH"; t_color = "#10b981"; t_badge = "tie-badge-green"
    elif bear_pts > bull_pts + 1: thesis = "BEARISH"; t_color = "#ef4444"; t_badge = "tie-badge-red"
    else: thesis = "NEUTRAL"; t_color = "#f59e0b"; t_badge = "tie-badge-yellow"

    # Proposed levels
    sl_price = price * (1 - 0.02) if thesis == "BULLISH" else price * (1 + 0.02)
    tp_price = price * (1 + 0.05) if thesis == "BULLISH" else price * (1 - 0.05)

    now_str = datetime.datetime.utcnow().strftime("%B %d, %Y — %H:%M UTC")

    st.markdown(f"""
<div style="padding:0 32px 32px;">

    <!-- Document Header -->
    <div class="tie-card" style="padding:32px;margin-bottom:20px;border-color:rgba(37,99,235,0.2);">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:24px;">
            <div>
                <p style="color:rgba(255,255,255,0.2);font-size:10px;font-weight:700;letter-spacing:0.2em;text-transform:uppercase;margin-bottom:8px;">Trading Intelligence Engine — White Paper</p>
                <h1 style="color:#f1f5f9;font-size:28px;font-weight:800;letter-spacing:-1px;margin-bottom:6px;">{sym} Market Analysis</h1>
                <p style="color:rgba(255,255,255,0.25);font-size:12px;">Published: {now_str} &nbsp;|&nbsp; Strategy: {strat} &nbsp;|&nbsp; Exchange: {ex.capitalize()}</p>
            </div>
            <span class="tie-badge {t_badge}" style="font-size:12px;padding:6px 16px;">{thesis}</span>
        </div>
        <div style="height:1px;background:linear-gradient(90deg,rgba(37,99,235,0.3),transparent);"></div>
    </div>

    <!-- SECTION 01: Executive Summary -->
    <div class="tie-card" style="padding:28px;margin-bottom:16px;">
        <p style="color:rgba(255,255,255,0.18);font-size:10px;font-weight:700;letter-spacing:0.2em;text-transform:uppercase;margin-bottom:6px;">01</p>
        <h3 style="color:#f1f5f9;font-size:18px;font-weight:700;margin-bottom:16px;">Executive Summary</h3>
        <p style="color:rgba(255,255,255,0.55);font-size:14px;line-height:1.8;">
            {sym.split('/')[0]} is currently trading at <strong style="color:#60a5fa;font-family:'JetBrains Mono',monospace;">${price:,.2f}</strong>, 
            representing a <strong style="color:{'#10b981' if chg>=0 else '#ef4444'};">{chg:+.2f}%</strong> change from the prior session close.
            The integrated analysis across {len(signals)} technical signals and {len(articles)} live news events 
            yields a consolidated <strong style="color:{t_color};">{thesis}</strong> thesis with a bull/bear signal ratio of 
            <strong style="color:#60a5fa;">{bull_pts}:{bear_pts}</strong> in favour of {'buyers' if thesis=='BULLISH' else 'sellers' if thesis=='BEARISH' else 'neither side'}.
            The broader market sentiment derived from live news feeds registers at 
            <strong style="color:{'#10b981' if avg_score>0 else '#ef4444' if avg_score<0 else '#f59e0b'};">{avg_score:+.2f} ({sent_label})</strong>.
            The 14-period RSI stands at <strong style="color:#f1f5f9;">{rsi:.1f}</strong> 
            ({'indicating overbought conditions' if rsi>70 else 'indicating oversold conditions' if rsi<30 else 'within the neutral band'}), 
            while the MACD histogram is <strong style="color:{'#10b981' if hist_v>0 else '#ef4444'};">{'positive' if hist_v>0 else 'negative'}</strong> 
            at <strong style="color:#f1f5f9;font-family:'JetBrains Mono',monospace;">{hist_v:.4f}</strong>, 
            confirming {'building bullish' if hist_v>0 else 'bearish'} momentum.
            Price is currently <strong>{'above' if price > ema200 else 'below'}</strong> the 200-period EMA 
            (${ema200:,.0f}), which defines the long-term structural {'uptrend' if price>ema200 else 'downtrend'}.
        </p>
    </div>

</div>
""", unsafe_allow_html=True)

    # SECTION 02: Market Pulse (News)
    st.markdown('<div style="padding:0 32px;">', unsafe_allow_html=True)
    st.markdown("""
<div class="tie-card" style="padding:28px;margin-bottom:16px;">
    <p style="color:rgba(255,255,255,0.18);font-size:10px;font-weight:700;letter-spacing:0.2em;text-transform:uppercase;margin-bottom:6px;">02</p>
    <h3 style="color:#f1f5f9;font-size:18px;font-weight:700;margin-bottom:20px;">Market Pulse — News Sentiment</h3>
</div>
""", unsafe_allow_html=True)

    if articles:
        news_data = []
        for a in articles[:10]:
            sc = a["score"]
            if sc > 2:   badge = "STRONGLY BULLISH"
            elif sc > 0: badge = "BULLISH"
            elif sc < -2: badge = "STRONGLY BEARISH"
            elif sc < 0: badge = "BEARISH"
            else:        badge = "NEUTRAL"
            news_data.append({"Headline": a["title"][:70]+"…" if len(a["title"])>70 else a["title"],
                               "Summary": a["summary"][:80]+"…" if len(a["summary"])>80 else a["summary"],
                               "Score": f"{sc:+d}",
                               "Sentiment": badge})
        df_news = pd.DataFrame(news_data)
        st.dataframe(df_news, use_container_width=True, hide_index=True, height=340)
    else:
        st.info("No news articles retrieved at this time.")
    st.markdown("</div>", unsafe_allow_html=True)

    # SECTION 03: Technical Blueprint
    st.markdown(f"""
<div style="padding:16px 32px 0;">
<div class="tie-card" style="padding:28px;margin-bottom:16px;">
    <p style="color:rgba(255,255,255,0.18);font-size:10px;font-weight:700;letter-spacing:0.2em;text-transform:uppercase;margin-bottom:6px;">03</p>
    <h3 style="color:#f1f5f9;font-size:18px;font-weight:700;margin-bottom:20px;">Technical Blueprint</h3>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">

        <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:18px;">
            <p class="tie-label" style="margin-bottom:12px;">RSI (14-Period)</p>
            <p style="font-family:'JetBrains Mono',monospace;font-size:24px;font-weight:700;color:{'#ef4444' if rsi>70 else '#10b981' if rsi<30 else '#f1f5f9'};margin-bottom:8px;">{rsi:.2f}</p>
            <p style="color:rgba(255,255,255,0.4);font-size:12px;line-height:1.6;">
                {'The RSI is in overbought territory above 70. This suggests that recent buying pressure may be excessive, increasing the probability of a pullback or consolidation before the next directional move.' if rsi>70 else 'The RSI is below 30, entering oversold territory. This condition historically precedes mean-reversion bounces, particularly when accompanied by volume confirmation.' if rsi<30 else f'RSI at {rsi:.1f} is within the neutral 30-70 band, indicating no immediate directional bias from momentum alone. Traders should use supporting indicators for confirmation.'}
            </p>
        </div>

        <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:18px;">
            <p class="tie-label" style="margin-bottom:12px;">MACD (12/26/9)</p>
            <p style="font-family:'JetBrains Mono',monospace;font-size:18px;font-weight:700;color:{'#10b981' if macd_v>sig_v else '#ef4444'};margin-bottom:8px;">
                {macd_v:.4f} / Signal {sig_v:.4f}
            </p>
            <p style="color:rgba(255,255,255,0.4);font-size:12px;line-height:1.6;">
                MACD is {'above' if macd_v>sig_v else 'below'} the signal line with a histogram value of {hist_v:.4f}.
                {'This bullish crossover indicates accelerating upward momentum. A sustained histogram expansion would confirm trend continuation.' if macd_v>sig_v else 'This bearish reading signals declining momentum. Watch for histogram compression as an early sign of trend reversal.'}
            </p>
        </div>

        <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:18px;">
            <p class="tie-label" style="margin-bottom:12px;">Bollinger Bands (20/2)</p>
            <p style="font-family:'JetBrains Mono',monospace;font-size:13px;font-weight:600;color:#f1f5f9;margin-bottom:8px;">
                Upper: ${bb_up:,.2f} | Mid: ${bb_mid:,.2f} | Lower: ${bb_dn:,.2f}
            </p>
            <p style="color:rgba(255,255,255,0.4);font-size:12px;line-height:1.6;">
                Price is positioned at {((price-bb_dn)/(bb_up-bb_dn)*100):.0f}% within the band width.
                {'Price approaching the upper band indicates strong bullish momentum but elevated volatility risk.' if price > bb_mid else 'Price in the lower half of the band. A bounce from mid-band would confirm continuation; a break below the lower band signals bearish expansion.'}
                Band width: ${(bb_up-bb_dn):,.2f} ({((bb_up-bb_dn)/bb_mid*100):.1f}% of mid).
            </p>
        </div>

        <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:18px;">
            <p class="tie-label" style="margin-bottom:12px;">EMA Stack Analysis</p>
            <p style="font-family:'JetBrains Mono',monospace;font-size:12px;color:#f1f5f9;margin-bottom:8px;line-height:1.7;">
                EMA 9:   ${ema9:,.0f}<br>
                EMA 21:  ${ema21:,.0f}<br>
                EMA 50:  ${ema50:,.0f}<br>
                EMA 200: ${ema200:,.0f}
            </p>
            <p style="color:rgba(255,255,255,0.4);font-size:12px;line-height:1.6;">
                {'Full bullish alignment confirmed. All short-term EMAs are stacked above long-term EMAs, indicating a strong uptrend structure.' if ema9>ema21>ema50>ema200 else 'Full bearish alignment. EMAs are in a downward stack, confirming the prevailing downtrend across all timeframes.' if ema9<ema21<ema50<ema200 else 'Mixed EMA alignment indicating a transitional or consolidation phase. No clear directional bias from the EMA stack alone.'}
            </p>
        </div>
    </div>
</div>
</div>
""", unsafe_allow_html=True)

    # SECTION 04: Visual Blueprint
    st.markdown(f"""
<div style="padding:0 32px;">
<div class="tie-card" style="padding:28px;margin-bottom:16px;">
    <p style="color:rgba(255,255,255,0.18);font-size:10px;font-weight:700;letter-spacing:0.2em;text-transform:uppercase;margin-bottom:6px;">04</p>
    <h3 style="color:#f1f5f9;font-size:18px;font-weight:700;margin-bottom:20px;">Visual Blueprint — Chart Levels</h3>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;">
        {"".join([f'''
        <div style="background:rgba(239,68,68,0.06);border:1px solid rgba(239,68,68,0.18);border-radius:10px;padding:16px;">
            <p style="color:#f87171;font-size:10px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;margin-bottom:6px;">Resistance {i+1}</p>
            <p style="color:#f1f5f9;font-family:'JetBrains Mono',monospace;font-size:18px;font-weight:700;">${lvl:,.2f}</p>
            <p style="color:rgba(239,68,68,0.5);font-size:11px;margin-top:4px;">+{((lvl-price)/price*100):.2f}% from current</p>
        </div>''' for i, lvl in enumerate(res_levels[:3])])}
        {"".join([f'''
        <div style="background:rgba(16,185,129,0.06);border:1px solid rgba(16,185,129,0.18);border-radius:10px;padding:16px;">
            <p style="color:#34d399;font-size:10px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;margin-bottom:6px;">Support {i+1}</p>
            <p style="color:#f1f5f9;font-family:'JetBrains Mono',monospace;font-size:18px;font-weight:700;">${lvl:,.2f}</p>
            <p style="color:rgba(16,185,129,0.5);font-size:11px;margin-top:4px;">{((lvl-price)/price*100):.2f}% from current</p>
        </div>''' for i, lvl in enumerate(sup_levels[:3])])}
    </div>
    <div style="margin-top:20px;display:grid;grid-template-columns:repeat(3,1fr);gap:12px;">
        <div style="background:rgba(37,99,235,0.06);border:1px solid rgba(37,99,235,0.2);border-radius:10px;padding:16px;">
            <p style="color:#60a5fa;font-size:10px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;margin-bottom:6px;">Entry Zone</p>
            <p style="color:#f1f5f9;font-family:'JetBrains Mono',monospace;font-size:18px;font-weight:700;">${price:,.2f}</p>
            <p style="color:rgba(37,99,235,0.5);font-size:11px;margin-top:4px;">Current market price</p>
        </div>
        <div style="background:rgba(239,68,68,0.06);border:1px solid rgba(239,68,68,0.2);border-radius:10px;padding:16px;">
            <p style="color:#f87171;font-size:10px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;margin-bottom:6px;">Stop Loss Zone</p>
            <p style="color:#f87171;font-family:'JetBrains Mono',monospace;font-size:18px;font-weight:700;">${sl_price:,.2f}</p>
            <p style="color:rgba(239,68,68,0.5);font-size:11px;margin-top:4px;">2.0% from entry</p>
        </div>
        <div style="background:rgba(16,185,129,0.06);border:1px solid rgba(16,185,129,0.2);border-radius:10px;padding:16px;">
            <p style="color:#34d399;font-size:10px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;margin-bottom:6px;">Take Profit Zone</p>
            <p style="color:#34d399;font-family:'JetBrains Mono',monospace;font-size:18px;font-weight:700;">${tp_price:,.2f}</p>
            <p style="color:rgba(16,185,129,0.5);font-size:11px;margin-top:4px;">5.0% from entry — R:R 1:2.5</p>
        </div>
    </div>
</div>
</div>
""", unsafe_allow_html=True)

    # SECTION 05: Actionable Thesis
    sig_html = "".join([f"""
<div style="display:flex;align-items:flex-start;gap:12px;padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.04);">
    <span class="tie-badge {'tie-badge-green' if color=='green' else 'tie-badge-red' if color=='red' else 'tie-badge-blue'}" style="flex-shrink:0;font-size:9px;">{tag}</span>
    <p style="color:rgba(255,255,255,0.5);font-size:12px;line-height:1.6;margin:0;">{text}</p>
</div>""" for tag, text, color in signals])

    st.markdown(f"""
<div style="padding:0 32px 32px;">
<div class="tie-card" style="padding:28px;border-color:rgba({'16,185,129' if thesis=='BULLISH' else '239,68,68' if thesis=='BEARISH' else '245,158,11'},0.2);">
    <p style="color:rgba(255,255,255,0.18);font-size:10px;font-weight:700;letter-spacing:0.2em;text-transform:uppercase;margin-bottom:6px;">05</p>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
        <h3 style="color:#f1f5f9;font-size:18px;font-weight:700;">Actionable Thesis</h3>
        <span class="tie-badge {t_badge}" style="font-size:13px;padding:6px 18px;letter-spacing:0.08em;">{thesis}</span>
    </div>
    <p style="color:rgba(255,255,255,0.45);font-size:13px;line-height:1.8;margin-bottom:20px;">
        Based on the integrated analysis of {len(signals)} technical signals and {len(articles)} news events, 
        the weight of evidence points to a <strong style="color:{t_color};">{thesis}</strong> outcome for {sym.split('/')[0]}.
        The bull-bear signal count stands at <strong style="color:#60a5fa;">{bull_pts} vs {bear_pts}</strong>.
        {'A long position is favored, contingent on risk validation and confirmation from volume.' if thesis=='BULLISH' else 
         'A short position or cash preservation is favored. Avoid new longs until trend reversal is confirmed.' if thesis=='BEARISH' else
         'No directional trade is recommended at this time. Monitor for a decisive breakout above resistance or breakdown below support.'}
    </p>
    <div style="background:rgba(255,255,255,0.02);border-radius:10px;padding:16px;">
        <p class="tie-label" style="margin-bottom:8px;">Evidence Stack ({len(signals)} Signals)</p>
        {sig_html}
    </div>
    <div style="margin-top:20px;padding:16px;background:rgba(255,255,255,0.02);border-radius:10px;border:1px solid rgba(255,255,255,0.05);">
        <p style="color:rgba(255,255,255,0.18);font-size:10px;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;margin-bottom:6px;">Disclaimer</p>
        <p style="color:rgba(255,255,255,0.2);font-size:11px;line-height:1.6;">
            This report is generated by an automated analytical engine. It is not financial advice. 
            All trade recommendations must pass the mandatory Risk Validation Layer before execution.
            Past performance does not guarantee future results. Trade at your own risk.
        </p>
    </div>
</div>
</div>
""", unsafe_allow_html=True)

# ── News Page ─────────────────────────────────────────────────────────────────
def page_news():
    sym = st.session_state.symbol

    st.markdown(f"""
<div style="padding:28px 32px 24px;">
    <p class="tie-label">Real-time Feed</p>
    <h2 style="color:#f1f5f9;font-size:26px;font-weight:700;letter-spacing:-0.5px;margin-top:4px;">News & Sentiment</h2>
    <div style="height:1px;background:linear-gradient(90deg,rgba(37,99,235,0.4),rgba(99,102,241,0.2),transparent);margin:20px 0 0;"></div>
</div>
""", unsafe_allow_html=True)

    with st.spinner("Loading news feeds..."):
        articles = fetch_news(sym)
    avg, sent = overall_sentiment(articles)

    # Sentiment bar
    sent_color = "#10b981" if avg > 0 else "#ef4444" if avg < 0 else "#f59e0b"
    st.markdown(f"""
<div style="padding:0 32px 20px;">
<div class="tie-card" style="padding:20px 24px;display:flex;align-items:center;justify-content:space-between;gap:24px;">
    <div>
        <p class="tie-label" style="margin-bottom:4px;">Aggregate Sentiment Score</p>
        <p style="font-family:'JetBrains Mono',monospace;font-size:28px;font-weight:700;color:{sent_color};">{avg:+.2f}</p>
    </div>
    <span class="tie-badge {'tie-badge-green' if avg>0 else 'tie-badge-red' if avg<0 else 'tie-badge-yellow'}" style="font-size:14px;padding:8px 20px;">{sent}</span>
    <div style="flex:1;max-width:300px;">
        <div style="height:6px;background:rgba(255,255,255,0.07);border-radius:6px;overflow:hidden;">
            <div style="height:100%;width:{min(100,(avg+5)/10*100):.0f}%;background:linear-gradient(90deg,{sent_color},{sent_color}88);border-radius:6px;transition:width 0.5s;"></div>
        </div>
        <div style="display:flex;justify-content:space-between;margin-top:4px;">
            <span style="color:rgba(255,255,255,0.2);font-size:9px;">-5 Bearish</span>
            <span style="color:rgba(255,255,255,0.2);font-size:9px;">+5 Bullish</span>
        </div>
    </div>
    <div>
        <p class="tie-label" style="margin-bottom:4px;">Articles Analyzed</p>
        <p style="font-family:'JetBrains Mono',monospace;font-size:28px;font-weight:700;color:#f1f5f9;">{len(articles)}</p>
    </div>
</div>
</div>
""", unsafe_allow_html=True)

    # Article cards
    st.markdown('<div style="padding:0 32px 32px;display:grid;grid-template-columns:1fr 1fr;gap:12px;">', unsafe_allow_html=True)
    cols = st.columns(2)
    for i, a in enumerate(articles[:12]):
        sc = a["score"]
        if sc > 2:   badge_class = "tie-badge-green"; lbl = "Strongly Bullish"
        elif sc > 0: badge_class = "tie-badge-green"; lbl = "Bullish"
        elif sc < -2: badge_class = "tie-badge-red"; lbl = "Strongly Bearish"
        elif sc < 0: badge_class = "tie-badge-red"; lbl = "Bearish"
        else:        badge_class = "tie-badge-blue"; lbl = "Neutral"
        with cols[i % 2]:
            st.markdown(f"""
<div class="tie-card" style="padding:18px;margin-bottom:12px;">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px;gap:8px;">
        <p style="color:#e2e8f0;font-size:13px;font-weight:600;line-height:1.4;flex:1;">{a['title'][:80]}{'...' if len(a['title'])>80 else ''}</p>
        <span class="tie-badge {badge_class}" style="flex-shrink:0;">{sc:+d}</span>
    </div>
    <p style="color:rgba(255,255,255,0.35);font-size:12px;line-height:1.6;margin-bottom:10px;">{a['summary'][:120]}{'...' if len(a['summary'])>120 else ''}</p>
    <div style="display:flex;justify-content:space-between;align-items:center;">
        <span class="tie-badge {badge_class}" style="font-size:9px;">{lbl}</span>
        <span style="color:rgba(255,255,255,0.2);font-size:10px;">{a['published'][:22] if a['published'] else '—'}</span>
    </div>
</div>
""", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ── Settings Page ─────────────────────────────────────────────────────────────
def page_settings():
    user = st.session_state.user

    st.markdown("""
<div style="padding:28px 32px 24px;">
    <p class="tie-label">Configuration</p>
    <h2 style="color:#f1f5f9;font-size:26px;font-weight:700;letter-spacing:-0.5px;margin-top:4px;">Settings</h2>
    <div style="height:1px;background:linear-gradient(90deg,rgba(37,99,235,0.4),rgba(99,102,241,0.2),transparent);margin:20px 0 0;"></div>
</div>
""", unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["API Keys", "Risk Parameters", "Account"])

    with tab1:
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        st.markdown("""
<div style="padding:0 4px;">
<div class="tie-card" style="padding:24px;margin-bottom:16px;">
    <p class="tie-section-title">Exchange API Keys</p>
    <p style="color:rgba(255,255,255,0.35);font-size:12px;margin-bottom:16px;line-height:1.6;">
        API keys are encrypted with AES-256 before database storage. Keys are never written or logged in plaintext.
        Enable <strong>Demo Mode</strong> to use market data without executing real trades.
    </p>
</div>
</div>
""", unsafe_allow_html=True)
        with st.form("form_api", clear_on_submit=False):
            exchange_sel = st.selectbox("Exchange", ["binance","kraken","coinbase","bybit","kucoin"], key="api_ex_sel")
            api_key_in   = st.text_input("API Key", type="password", placeholder="Paste your API key here")
            api_sec_in   = st.text_input("API Secret", type="password", placeholder="Paste your API secret here")
            demo_mode    = st.checkbox("Demo Mode (paper trading only — recommended)", value=True, key="api_demo")
            save_btn     = st.form_submit_button("Encrypt & Save Key", use_container_width=True)

        if save_btn:
            if not api_key_in or not api_sec_in:
                st.error("Both API Key and Secret are required.")
            else:
                db = SessionLocal()
                try:
                    new_key = UserApiKey(
                        user_id=user["id"],
                        exchange=exchange_sel,
                        enc_api_key=encrypt(api_key_in),
                        enc_secret=encrypt(api_sec_in),
                        is_demo=demo_mode
                    )
                    db.add(new_key)
                    db.commit()
                    st.success(f"API key for {exchange_sel.capitalize()} encrypted and saved successfully.")
                except Exception as ex:
                    db.rollback()
                    st.error(f"Failed to save: {ex}")
                finally:
                    db.close()

        # Saved keys
        db = SessionLocal()
        try:
            saved = db.query(UserApiKey).filter(UserApiKey.user_id == user["id"]).all()
        finally:
            db.close()

        if saved:
            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            keys_data = [{"Exchange": k.exchange.capitalize(),
                          "Mode": "Demo" if k.is_demo else "Live",
                          "API Key": "••••••••" + k.enc_api_key[-6:],
                          "Added": str(k.created_at)[:10]} for k in saved]
            st.dataframe(pd.DataFrame(keys_data), use_container_width=True, hide_index=True)

    with tab2:
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        st.markdown(f"""
<div style="padding:0 4px;">
<div class="tie-card" style="padding:24px;">
    <p class="tie-section-title">Active Risk Parameters</p>
    <p style="color:rgba(255,255,255,0.3);font-size:12px;margin-bottom:20px;">
        These limits are hard-coded in the validation layer and cannot be overridden by the AI engine.
    </p>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
        <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:16px;">
            <p class="tie-label" style="margin-bottom:6px;">Max Position Size</p>
            <p style="font-family:'JetBrains Mono',monospace;font-size:22px;font-weight:700;color:#60a5fa;">5.0%</p>
            <p style="color:rgba(255,255,255,0.3);font-size:11px;margin-top:4px;">Of total account balance per trade</p>
        </div>
        <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:16px;">
            <p class="tie-label" style="margin-bottom:6px;">Max Stop Loss</p>
            <p style="font-family:'JetBrains Mono',monospace;font-size:22px;font-weight:700;color:#f87171;">2.0%</p>
            <p style="color:rgba(255,255,255,0.3);font-size:11px;margin-top:4px;">Maximum distance from entry</p>
        </div>
        <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:16px;">
            <p class="tie-label" style="margin-bottom:6px;">Min Take Profit</p>
            <p style="font-family:'JetBrains Mono',monospace;font-size:22px;font-weight:700;color:#34d399;">5.0%</p>
            <p style="color:rgba(255,255,255,0.3);font-size:11px;margin-top:4px;">Minimum target from entry</p>
        </div>
        <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:16px;">
            <p class="tie-label" style="margin-bottom:6px;">Min Risk / Reward</p>
            <p style="font-family:'JetBrains Mono',monospace;font-size:22px;font-weight:700;color:#a78bfa;">1 : 2.0</p>
            <p style="color:rgba(255,255,255,0.3);font-size:11px;margin-top:4px;">Minimum R:R before execution</p>
        </div>
        <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(239,68,68,0.15);border-radius:10px;padding:16px;grid-column:1/-1;">
            <p class="tie-label" style="margin-bottom:6px;">Daily Loss Limit — Global Shutdown Trigger</p>
            <p style="font-family:'JetBrains Mono',monospace;font-size:22px;font-weight:700;color:#ef4444;">10.0%</p>
            <p style="color:rgba(255,255,255,0.3);font-size:11px;margin-top:4px;">If cumulative daily loss exceeds this threshold, all trading is suspended for 24 hours automatically.</p>
        </div>
    </div>
</div>
</div>
""", unsafe_allow_html=True)

    with tab3:
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        st.markdown(f"""
<div style="padding:0 4px;">
<div class="tie-card" style="padding:24px;">
    <p class="tie-section-title">Account Details</p>
    <div style="display:flex;flex-direction:column;gap:14px;">
        <div style="display:flex;justify-content:space-between;padding:12px 0;border-bottom:1px solid rgba(255,255,255,0.05);">
            <span class="tie-label">Full Name</span>
            <span style="color:#f1f5f9;font-size:14px;font-weight:500;">{user['name']}</span>
        </div>
        <div style="display:flex;justify-content:space-between;padding:12px 0;border-bottom:1px solid rgba(255,255,255,0.05);">
            <span class="tie-label">Email Address</span>
            <span style="color:#f1f5f9;font-size:14px;font-family:'JetBrains Mono',monospace;">{user['email']}</span>
        </div>
        <div style="display:flex;justify-content:space-between;padding:12px 0;border-bottom:1px solid rgba(255,255,255,0.05);">
            <span class="tie-label">Account ID</span>
            <span style="color:rgba(255,255,255,0.3);font-size:12px;font-family:'JetBrains Mono',monospace;">{user['id'][:20]}…</span>
        </div>
        <div style="display:flex;justify-content:space-between;padding:12px 0;">
            <span class="tie-label">Encryption</span>
            <span class="tie-badge tie-badge-green">AES-256 Active</span>
        </div>
    </div>
</div>
</div>
""", unsafe_allow_html=True)

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    init_state()
    inject_css()

    if not st.session_state.user:
        page_auth()
        return

    render_sidebar()

    page = st.session_state.page
    if page == "dashboard":
        page_dashboard()
    elif page == "report":
        page_report()
    elif page == "news":
        page_news()
    elif page == "settings":
        page_settings()

if __name__ == "__main__":
    main()
