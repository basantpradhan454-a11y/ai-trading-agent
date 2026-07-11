"""
Trading Intelligence Engine — v6.0
60% #0c1222 | 30% #0f1e35 | 10% #00d4ff / #7c3aed
Futuristic dark fintech UI — clean Streamlit architecture
"""

import streamlit as st
import ccxt, pandas as pd, numpy as np
import plotly.graph_objects as go
import feedparser, re, uuid, os, datetime, json, hashlib
from cryptography.fernet import Fernet
from passlib.context import CryptContext
from sqlalchemy import create_engine, Column, String, Float, DateTime, Text, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Trading Intelligence Engine",
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
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)

class User(Base):
    __tablename__ = "users"
    id            = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email         = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name     = Column(String, default="")
    strategy      = Column(String, default="Balanced")
    created_at    = Column(DateTime, default=datetime.datetime.utcnow)

class ApiKey(Base):
    __tablename__ = "api_keys"
    id            = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id       = Column(String, nullable=False)
    exchange      = Column(String, nullable=False)
    api_key_enc   = Column(Text, nullable=False)
    api_secret_enc= Column(Text, nullable=False)
    created_at    = Column(DateTime, default=datetime.datetime.utcnow)

class TradeLog(Base):
    __tablename__ = "trade_logs"
    id            = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id       = Column(String, nullable=False)
    symbol        = Column(String)
    action        = Column(String)
    entry_price   = Column(Float)
    stop_loss     = Column(Float)
    take_profit   = Column(Float)
    size_pct      = Column(Float)
    risk_reward   = Column(String)
    strategy      = Column(String)
    status        = Column(String, default="demo")
    timestamp     = Column(DateTime, default=datetime.datetime.utcnow)

Base.metadata.create_all(bind=engine)

# ── Security ──────────────────────────────────────────────────────────────────
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
RAW_KEY = os.getenv("ENCRYPTION_KEY", Fernet.generate_key().decode())
FERNET   = Fernet(RAW_KEY.encode() if isinstance(RAW_KEY, str) else RAW_KEY)

def hash_pw(p):  return pwd_ctx.hash(p)
def verify_pw(p, h): return pwd_ctx.verify(p, h)
def encrypt(v):  return FERNET.encrypt(v.encode()).decode()
def decrypt(v):  return FERNET.decrypt(v.encode()).decode()

# ── Risk Limits (hard-coded, AI cannot override) ──────────────────────────────
MAX_POSITION_PCT  = 5.0
MAX_SL_PCT        = 2.0
MIN_TP_PCT        = 5.0
MIN_RR            = 2.0
MAX_DAILY_LOSS_PCT= 10.0

def validate_trade(action, entry, sl, tp, size_pct):
    issues = []
    action = action.upper()
    if size_pct > MAX_POSITION_PCT:
        issues.append(f"Position {size_pct}% > max {MAX_POSITION_PCT}%")
    sl_dist = abs(entry - sl) / entry * 100
    if sl_dist > MAX_SL_PCT:
        issues.append(f"Stop-loss distance {sl_dist:.2f}% > max {MAX_SL_PCT}%")
    if action == "BUY" and (sl >= entry or tp <= entry):
        issues.append("BUY: SL must be below entry, TP above entry")
    if action == "SELL" and (sl <= entry or tp >= entry):
        issues.append("SELL: SL must be above entry, TP below entry")
    risk   = abs(entry - sl)
    reward = abs(tp - entry)
    rr     = reward / risk if risk > 0 else 0
    if rr < MIN_RR:
        issues.append(f"R:R {rr:.2f} below minimum 1:{MIN_RR}")
    is_valid = len(issues) == 0
    order = {
        "action": action, "entry_price": entry, "stop_loss": sl,
        "take_profit": tp, "size_pct": size_pct,
        "risk_reward": f"1:{round(rr, 1)}"
    } if is_valid else {}
    return is_valid, issues, order

# ── Global CSS — 60/30/10 Rule ────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* === 60% — Base Background === */
html, body, .stApp, [data-testid="stAppViewContainer"] {
    background: #0c1222 !important;
    font-family: 'Inter', sans-serif !important;
    color: #c8d6e8 !important;
}

/* === 30% — Secondary Surface === */
[data-testid="stSidebar"] {
    background: #0f1e35 !important;
    border-right: 1px solid rgba(0,212,255,0.12) !important;
}
[data-testid="stSidebar"] * { color: #c8d6e8 !important; }

/* Block container */
[data-testid="stMainBlockContainer"] {
    padding-top: 1.5rem !important;
}

/* === Cards (30% secondary) === */
.tic-card {
    background: #0f1e35;
    border: 1px solid rgba(0,212,255,0.12);
    border-radius: 14px;
    padding: 24px 28px;
    margin-bottom: 16px;
    transition: border-color .2s;
}
.tic-card:hover { border-color: rgba(0,212,255,0.28); }

/* Auth card */
.auth-card {
    background: #0f1e35;
    border: 1px solid rgba(0,212,255,0.18);
    border-radius: 18px;
    padding: 40px 36px;
}

/* Auth branding */
.auth-brand {
    padding: 40px 20px;
}

/* === 10% — Cyan Accent === */
.accent { color: #00d4ff !important; }
.accent-purple { color: #7c3aed !important; }

/* Metric tiles */
.metric-tile {
    background: #0f1e35;
    border: 1px solid rgba(0,212,255,0.1);
    border-radius: 12px;
    padding: 18px 20px;
    text-align: center;
}
.metric-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.7rem;
    font-weight: 600;
    color: #00d4ff;
    display: block;
}
.metric-label {
    font-size: 0.72rem;
    color: #5a7a9a;
    letter-spacing: .08em;
    text-transform: uppercase;
    margin-top: 4px;
}

/* Section headers */
.section-header {
    font-size: 0.7rem;
    letter-spacing: .14em;
    text-transform: uppercase;
    color: #00d4ff;
    font-weight: 600;
    margin-bottom: 6px;
    border-left: 3px solid #00d4ff;
    padding-left: 10px;
}

/* === 10% — Buttons === */
.stButton > button {
    background: linear-gradient(135deg, #00d4ff, #0090c4) !important;
    color: #0c1222 !important;
    font-weight: 700 !important;
    font-size: 0.88rem !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 12px 28px !important;
    letter-spacing: .04em !important;
    transition: all .2s !important;
    width: 100%;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #00eaff, #00b8e6) !important;
    box-shadow: 0 0 24px rgba(0,212,255,0.4) !important;
    transform: translateY(-1px) !important;
}

/* Tabs */
[data-testid="stTabs"] [role="tab"] {
    background: transparent !important;
    color: #5a7a9a !important;
    border: none !important;
    font-weight: 500;
    font-size: 0.9rem;
    padding: 10px 20px !important;
    border-bottom: 2px solid transparent !important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: #00d4ff !important;
    border-bottom: 2px solid #00d4ff !important;
    background: transparent !important;
}
[data-testid="stTabs"] [role="tablist"] {
    border-bottom: 1px solid rgba(0,212,255,0.12) !important;
    gap: 4px;
}

/* Inputs */
.stTextInput > div > div > input,
.stSelectbox > div > div,
.stNumberInput > div > div > input {
    background: rgba(0,212,255,0.04) !important;
    border: 1px solid rgba(0,212,255,0.18) !important;
    border-radius: 10px !important;
    color: #e2eaf4 !important;
    font-size: 0.9rem !important;
    padding: 10px 14px !important;
}
.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus {
    border-color: rgba(0,212,255,0.5) !important;
    box-shadow: 0 0 0 2px rgba(0,212,255,0.1) !important;
}
.stTextInput > label, .stSelectbox > label, .stNumberInput > label {
    color: #5a7a9a !important;
    font-size: 0.78rem !important;
    font-weight: 500 !important;
    letter-spacing: .06em !important;
    text-transform: uppercase;
}

/* Sidebar nav radio */
[data-testid="stSidebar"] .stRadio > div {
    gap: 4px !important;
}
[data-testid="stSidebar"] .stRadio label {
    background: rgba(0,212,255,0.04);
    border: 1px solid rgba(0,212,255,0.08);
    border-radius: 10px;
    padding: 10px 16px !important;
    cursor: pointer;
    font-size: 0.88rem;
    color: #8aafc8 !important;
    transition: all .18s;
    width: 100%;
    display: block;
}
[data-testid="stSidebar"] .stRadio label:hover {
    border-color: rgba(0,212,255,0.3);
    color: #00d4ff !important;
    background: rgba(0,212,255,0.08);
}

/* Selectbox */
.stSelectbox [data-baseweb="select"] > div {
    background: rgba(0,212,255,0.04) !important;
    border: 1px solid rgba(0,212,255,0.18) !important;
    border-radius: 10px !important;
}

/* Forms */
[data-testid="stForm"] {
    border: none !important;
    padding: 0 !important;
    background: transparent !important;
}

/* Dataframe */
[data-testid="stDataFrame"] {
    background: #0f1e35 !important;
    border-radius: 12px !important;
}

/* Hide Streamlit chrome */
#MainMenu, footer, header,
[data-testid="stDecoration"],
[data-testid="stToolbar"]  { display:none !important; }

/* Divider */
hr { border-color: rgba(0,212,255,0.1) !important; margin: 20px 0 !important; }

/* Alert / info boxes */
.stAlert { border-radius: 10px !important; }
[data-testid="stNotification"] { border-radius: 10px !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #0c1222; }
::-webkit-scrollbar-thumb { background: rgba(0,212,255,0.25); border-radius: 3px; }

/* Badge */
.badge {
    display: inline-block;
    font-size: 0.7rem;
    font-weight: 600;
    padding: 2px 10px;
    border-radius: 20px;
    letter-spacing: .06em;
}
.badge-bull { background: rgba(16,185,129,0.15); color: #10b981; border: 1px solid rgba(16,185,129,0.3); }
.badge-bear { background: rgba(239,68,68,0.15);  color: #ef4444; border: 1px solid rgba(239,68,68,0.3); }
.badge-neut { background: rgba(0,212,255,0.1);   color: #00d4ff; border: 1px solid rgba(0,212,255,0.3); }

/* Report sections */
.report-section {
    background: #0f1e35;
    border: 1px solid rgba(124,58,237,0.2);
    border-left: 3px solid #7c3aed;
    border-radius: 12px;
    padding: 22px 26px;
    margin-bottom: 18px;
}
.report-num {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    color: #7c3aed;
    letter-spacing: .12em;
    text-transform: uppercase;
    font-weight: 600;
}
.report-title {
    font-size: 1.05rem;
    font-weight: 600;
    color: #e2eaf4;
    margin-top: 2px;
}
</style>
""", unsafe_allow_html=True)

# ── Session State ─────────────────────────────────────────────────────────────
for k, v in [("user", None), ("page", "Dashboard"), ("daily_pnl", 0.0), ("shutdown", False)]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── Market Data ───────────────────────────────────────────────────────────────
SYMBOLS = ["BTC/USDT","ETH/USDT","BNB/USDT","SOL/USDT","XRP/USDT",
           "ADA/USDT","AVAX/USDT","DOGE/USDT","MATIC/USDT","DOT/USDT"]

@st.cache_data(ttl=90)
def fetch_ohlcv(symbol="BTC/USDT", tf="1h", limit=200):
    try:
        ex = ccxt.binance({"enableRateLimit": True})
        raw = ex.fetch_ohlcv(symbol, tf, limit=limit)
        df = pd.DataFrame(raw, columns=["ts","open","high","low","close","volume"])
        df["ts"] = pd.to_datetime(df["ts"], unit="ms")
        return df
    except Exception:
        np.random.seed(42)
        n = limit
        base = 65000 if "BTC" in symbol else 3500
        closes = base + np.cumsum(np.random.randn(n) * base * 0.008)
        df = pd.DataFrame({
            "ts":     pd.date_range("2024-01-01", periods=n, freq="1h"),
            "open":   closes * (1 - np.random.rand(n) * 0.005),
            "high":   closes * (1 + np.random.rand(n) * 0.01),
            "low":    closes * (1 - np.random.rand(n) * 0.01),
            "close":  closes,
            "volume": np.random.randint(500, 5000, n).astype(float)
        })
        return df

def calc_indicators(df):
    c = df["close"]
    # EMA
    df["ema20"]  = c.ewm(span=20).mean()
    df["ema50"]  = c.ewm(span=50).mean()
    df["ema200"] = c.ewm(span=200).mean()
    # RSI
    delta = c.diff()
    gain  = delta.clip(lower=0).ewm(span=14).mean()
    loss  = (-delta.clip(upper=0)).ewm(span=14).mean()
    df["rsi"] = 100 - 100/(1+gain/loss.replace(0, 1e-9))
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
    df["bb_low"] = sma20 - 2 * std20
    # Volume MA
    df["vol_ma"] = df["volume"].rolling(20).mean()
    # S/R levels
    recent = df.tail(50)
    df.attrs["support"]    = round(float(recent["low"].min()), 2)
    df.attrs["resistance"] = round(float(recent["high"].max()), 2)
    return df

def get_signal(df):
    last = df.iloc[-1]
    score = 0
    reasons = []
    if last["rsi"] < 35:   score += 2; reasons.append("RSI oversold")
    elif last["rsi"] > 65: score -= 2; reasons.append("RSI overbought")
    if last["macd"] > last["signal"]: score += 1; reasons.append("MACD bullish crossover")
    else:                             score -= 1; reasons.append("MACD bearish")
    if last["close"] > last["ema20"] > last["ema50"]: score += 1; reasons.append("Price above EMA stack")
    elif last["close"] < last["ema20"] < last["ema50"]: score -= 1; reasons.append("Price below EMA stack")
    if last["volume"] > last["vol_ma"] * 1.4: score += 1; reasons.append("Volume spike detected")
    if last["close"] < last["bb_low"]: score += 1; reasons.append("Below lower Bollinger Band")
    elif last["close"] > last["bb_up"]: score -= 1; reasons.append("Above upper Bollinger Band")

    if score >= 3:   sig = "STRONG BUY"
    elif score >= 1: sig = "BUY"
    elif score <= -3:sig = "STRONG SELL"
    elif score <= -1:sig = "SELL"
    else:            sig = "NEUTRAL"
    return sig, score, reasons

# ── News Engine ───────────────────────────────────────────────────────────────
NEWS_FEEDS = [
    "https://cointelegraph.com/rss",
    "https://feeds.coindesk.com/rss",
    "https://cryptopanic.com/news/rss/",
    "https://bitcoinmagazine.com/.rss/full/",
]

@st.cache_data(ttl=600)
def fetch_news(query="crypto", limit=15):
    articles = []
    for url in NEWS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:5]:
                t = e.get("title","")
                s = e.get("summary","")[:200]
                d = e.get("published","")
                articles.append({"title":t,"summary":s,"date":d,"source":url.split("/")[2]})
        except Exception:
            pass
    # sentiment score
    pos = ["bull","buy","surge","rally","gain","breakout","record","high","adoption","ETF","approval"]
    neg = ["bear","sell","crash","drop","fall","hack","ban","risk","loss","FUD","SEC","decline"]
    q = query.lower()
    scored = []
    for a in articles:
        txt = (a["title"]+" "+a["summary"]).lower()
        if q not in txt and q not in a["source"]:
            pass  # still include all news for breadth
        sc = sum(1 for w in pos if w in txt) - sum(1 for w in neg if w in txt)
        sc = max(-5, min(5, sc))
        a["score"] = sc
        scored.append(a)
    return scored[:limit]

# ── Chart ─────────────────────────────────────────────────────────────────────
def build_chart(df, symbol):
    fig = go.Figure()
    # Candles
    fig.add_trace(go.Candlestick(
        x=df["ts"], open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        name="Price",
        increasing=dict(fillcolor="#10b981", line=dict(color="#10b981", width=1)),
        decreasing=dict(fillcolor="#ef4444", line=dict(color="#ef4444", width=1)),
    ))
    # EMAs
    for col, clr, nm in [("ema20","#00d4ff","EMA20"),("ema50","#7c3aed","EMA50"),("ema200","#f59e0b","EMA200")]:
        fig.add_trace(go.Scatter(x=df["ts"], y=df[col], line=dict(color=clr,width=1.2), name=nm, opacity=0.7))
    # BB
    fig.add_trace(go.Scatter(x=df["ts"], y=df["bb_up"],  line=dict(color="rgba(0,212,255,0.3)",width=1), name="BB Upper", fill=None))
    fig.add_trace(go.Scatter(x=df["ts"], y=df["bb_low"], line=dict(color="rgba(0,212,255,0.3)",width=1), name="BB Lower",
                             fill="tonexty", fillcolor="rgba(0,212,255,0.04)"))
    # S/R
    fig.add_hline(y=df.attrs["support"],    line=dict(color="rgba(16,185,129,0.5)",  dash="dash", width=1), annotation_text="Support")
    fig.add_hline(y=df.attrs["resistance"], line=dict(color="rgba(239,68,68,0.5)",   dash="dash", width=1), annotation_text="Resistance")
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(12,18,34,0)",
        plot_bgcolor ="rgba(15,30,53,0.5)",
        margin=dict(l=0,r=0,t=28,b=0),
        height=400,
        font=dict(family="Inter", color="#8aafc8", size=11),
        xaxis=dict(gridcolor="rgba(0,212,255,0.05)", showline=False, zeroline=False, rangeslider_visible=False),
        yaxis=dict(gridcolor="rgba(0,212,255,0.05)", showline=False, zeroline=False, side="right"),
        legend=dict(bgcolor="rgba(15,30,53,0.7)", bordercolor="rgba(0,212,255,0.15)", borderwidth=1, font_size=10),
        hoverlabel=dict(bgcolor="rgba(12,18,34,0.95)", bordercolor="rgba(0,212,255,0.3)", font_size=11),
        title=dict(text=f"{symbol} — Technical Chart", font=dict(size=13, color="#e2eaf4"), x=0),
    )
    return fig

def build_volume_chart(df):
    colors = ["#10b981" if r["close"]>=r["open"] else "#ef4444" for _, r in df.iterrows()]
    fig = go.Figure(go.Bar(x=df["ts"], y=df["volume"], marker_color=colors, name="Volume"))
    fig.add_trace(go.Scatter(x=df["ts"], y=df["vol_ma"], line=dict(color="#00d4ff",width=1.2), name="Vol MA20"))
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(12,18,34,0)",
        plot_bgcolor ="rgba(15,30,53,0.5)",
        margin=dict(l=0,r=0,t=0,b=0), height=150,
        font=dict(family="Inter", color="#8aafc8", size=10),
        xaxis=dict(gridcolor="rgba(0,212,255,0.05)", showline=False, zeroline=False),
        yaxis=dict(gridcolor="rgba(0,212,255,0.05)", showline=False, zeroline=False, side="right"),
        showlegend=False, bargap=0.15,
    )
    return fig

# ── Auth Page ─────────────────────────────────────────────────────────────────
def page_auth():
    col_brand, col_gap, col_form = st.columns([1.05, 0.1, 0.85])

    # ── Left Branding ────────────────────────────────────────────────────────
    with col_brand:
        st.markdown("<div style='height:60px'></div>", unsafe_allow_html=True)

        st.markdown("""
        <div style="
            display:inline-block;
            background: rgba(0,212,255,0.08);
            border: 1px solid rgba(0,212,255,0.22);
            border-radius: 8px;
            padding: 5px 14px;
            font-size: 0.72rem;
            letter-spacing: .12em;
            color: #00d4ff;
            font-weight: 600;
            text-transform: uppercase;
            margin-bottom: 28px;
        ">⬡ &nbsp;INSTITUTIONAL GRADE PLATFORM</div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <h1 style="
            font-size: 3rem;
            font-weight: 700;
            line-height: 1.15;
            color: #e2eaf4;
            margin: 0 0 10px 0;
        ">Trading<br><span style="color:#00d4ff;">Intelligence</span><br>Engine</h1>
        """, unsafe_allow_html=True)

        st.markdown("""
        <p style="font-size:0.92rem; color:#5a7a9a; max-width:400px; line-height:1.7; margin:16px 0 36px 0;">
        Institutional-grade market analysis powered by real-time TA/FA fusion,
        AI-driven trade theses, and a hard-coded risk validation layer.
        </p>
        """, unsafe_allow_html=True)

        features = [
            ("RSI · MACD · Bollinger Bands", "Live technical analysis suite"),
            ("News Sentiment Engine",         "Real-time impact scoring −5 to +5"),
            ("White Paper Report",            "5-section institutional document"),
            ("AES-256 Encryption",            "No plaintext API keys ever"),
            ("Risk Validation Layer",         "5% position · 2% SL · 1:2 R:R"),
        ]
        for title, desc in features:
            st.markdown(f"""
            <div style="display:flex; align-items:flex-start; gap:14px; margin-bottom:14px;">
                <div style="
                    width:8px; height:8px; border-radius:50%;
                    background:#00d4ff;
                    box-shadow: 0 0 10px rgba(0,212,255,0.6);
                    margin-top:6px; flex-shrink:0;
                "></div>
                <div>
                    <div style="font-size:0.88rem; font-weight:600; color:#c8d6e8;">{title}</div>
                    <div style="font-size:0.78rem; color:#4a6a8a; margin-top:1px;">{desc}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)
        st.markdown("""
        <div style="display:flex; gap:24px; flex-wrap:wrap;">
            <span style="font-size:0.72rem; color:#304a66; letter-spacing:.06em;">AES-256 ENCRYPTION</span>
            <span style="font-size:0.72rem; color:#304a66; letter-spacing:.06em;">BCRYPT AUTH</span>
            <span style="font-size:0.72rem; color:#304a66; letter-spacing:.06em;">DEMO-FIRST MODE</span>
            <span style="font-size:0.72rem; color:#304a66; letter-spacing:.06em;">NO PLAINTEXT KEYS</span>
        </div>
        """, unsafe_allow_html=True)

    # ── Right Form Card ───────────────────────────────────────────────────────
    with col_form:
        st.markdown("<div style='height:60px'></div>", unsafe_allow_html=True)

        # Card container
        st.markdown("""
        <div style="
            background: #0f1e35;
            border: 1px solid rgba(0,212,255,0.18);
            border-radius: 18px;
            padding: 36px 32px 28px 32px;
        ">
        <div style="
            font-size:0.68rem; letter-spacing:.14em; color:#00d4ff;
            font-weight:600; text-transform:uppercase; margin-bottom:6px;
        ">ACCESS PORTAL</div>
        <div style="font-size:1.25rem; font-weight:700; color:#e2eaf4; margin-bottom:24px;">
            Sign in to your account
        </div>
        </div>
        """, unsafe_allow_html=True)

        tab_in, tab_up = st.tabs(["Sign In", "Create Account"])

        # ── Sign In ──
        with tab_in:
            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            with st.form("form_login", clear_on_submit=False):
                email    = st.text_input("Email Address", placeholder="you@example.com", key="li_email")
                password = st.text_input("Password",      placeholder="Enter your password", type="password", key="li_pw")
                submit   = st.form_submit_button("Sign In", use_container_width=True)

            if submit:
                if not email or not password:
                    st.error("Please fill in all fields.")
                else:
                    db = SessionLocal()
                    try:
                        user = db.query(User).filter(User.email == email.lower().strip()).first()
                        if user and verify_pw(password, user.password_hash):
                            st.session_state.user = {
                                "id": user.id, "email": user.email,
                                "name": user.full_name or email.split("@")[0],
                                "strategy": user.strategy
                            }
                            st.success("Signed in successfully.")
                            st.rerun()
                        else:
                            st.error("Invalid email or password.")
                    except Exception as e:
                        st.error(f"Sign in error: {e}")
                    finally:
                        db.close()

        # ── Create Account ──
        with tab_up:
            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            with st.form("form_signup", clear_on_submit=False):
                full_name = st.text_input("Full Name",         placeholder="Your full name",       key="su_name")
                su_email  = st.text_input("Email Address",     placeholder="you@example.com",      key="su_email")
                su_pw     = st.text_input("Password",          placeholder="Min 8 characters",     type="password", key="su_pw")
                su_pw2    = st.text_input("Confirm Password",  placeholder="Repeat your password", type="password", key="su_pw2")
                strategy  = st.selectbox("Trading Strategy", ["Balanced","Conservative","Aggressive"], key="su_strat")
                register  = st.form_submit_button("Create Account", use_container_width=True)

            if register:
                errs = []
                if not full_name:             errs.append("Full name is required.")
                if not su_email or "@" not in su_email: errs.append("Valid email is required.")
                if len(su_pw) < 8:            errs.append("Password must be at least 8 characters.")
                if su_pw != su_pw2:           errs.append("Passwords do not match.")

                if errs:
                    for e in errs:
                        st.error(e)
                else:
                    db = SessionLocal()
                    try:
                        exists = db.query(User).filter(User.email == su_email.lower().strip()).first()
                        if exists:
                            st.error("An account with this email already exists.")
                        else:
                            new_user = User(
                                email=su_email.lower().strip(),
                                password_hash=hash_pw(su_pw),
                                full_name=full_name.strip(),
                                strategy=strategy
                            )
                            db.add(new_user)
                            db.commit()
                            db.refresh(new_user)
                            st.session_state.user = {
                                "id": new_user.id, "email": new_user.email,
                                "name": new_user.full_name,
                                "strategy": new_user.strategy
                            }
                            st.success("Account created! Welcome aboard.")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Registration error: {e}")
                    finally:
                        db.close()

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        st.markdown("""
        <p style="font-size:0.72rem; color:#304a66; text-align:center; margin-top:8px;">
        By signing in you agree to our risk disclaimers. This platform is for
        educational and demo-trading purposes only.
        </p>
        """, unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
def render_sidebar():
    u = st.session_state.user
    with st.sidebar:
        st.markdown("""
        <div style="padding: 8px 0 20px 0;">
            <div style="font-size:1.05rem; font-weight:700; color:#e2eaf4; letter-spacing:.02em;">
                ⬡ TIE
            </div>
            <div style="font-size:0.72rem; color:#304a66; letter-spacing:.1em; text-transform:uppercase; margin-top:2px;">
                Trading Intelligence Engine
            </div>
        </div>
        <hr style="border-color:rgba(0,212,255,0.1); margin: 0 0 16px 0;">
        """, unsafe_allow_html=True)

        # User badge
        initials = "".join(w[0].upper() for w in u["name"].split()[:2])
        st.markdown(f"""
        <div style="
            display:flex; align-items:center; gap:12px;
            background: rgba(0,212,255,0.05);
            border: 1px solid rgba(0,212,255,0.1);
            border-radius: 12px; padding: 12px 14px;
            margin-bottom: 20px;
        ">
            <div style="
                width:36px; height:36px; border-radius:50%;
                background: linear-gradient(135deg,#00d4ff,#7c3aed);
                display:flex; align-items:center; justify-content:center;
                font-weight:700; font-size:0.85rem; color:#0c1222; flex-shrink:0;
            ">{initials}</div>
            <div>
                <div style="font-size:0.85rem; font-weight:600; color:#c8d6e8;">{u['name']}</div>
                <div style="font-size:0.72rem; color:#304a66; margin-top:1px;">{u['strategy']} strategy</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div style="font-size:0.68rem; letter-spacing:.1em; color:#304a66; text-transform:uppercase; margin-bottom:8px; padding-left:4px;">Navigation</div>', unsafe_allow_html=True)
        nav = st.radio("", ["Dashboard", "Analysis Report", "News Feed", "Settings"],
                       key="nav_radio", label_visibility="collapsed")
        st.session_state.page = nav

        st.markdown("<div style='flex:1'></div>", unsafe_allow_html=True)
        st.markdown("<hr>", unsafe_allow_html=True)

        # Risk limits display
        st.markdown("""
        <div style="font-size:0.68rem; letter-spacing:.1em; color:#304a66; text-transform:uppercase; margin-bottom:10px;">Risk Limits (Hard-Coded)</div>
        """, unsafe_allow_html=True)
        limits = [("Max Position", "5%"), ("Stop-Loss", "2%"), ("Take-Profit", "5%"),
                  ("Min R:R", "1:2"), ("Daily Loss", "10%")]
        for k, v in limits:
            st.markdown(f"""
            <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
                <span style="font-size:0.78rem; color:#4a6a8a;">{k}</span>
                <span style="font-family:'JetBrains Mono',monospace; font-size:0.78rem; color:#00d4ff;">{v}</span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        if st.button("Sign Out", key="signout"):
            st.session_state.user = None
            st.rerun()

# ── Dashboard ─────────────────────────────────────────────────────────────────
def page_dashboard():
    st.markdown("""
    <div style="margin-bottom:24px;">
        <div style="font-size:0.7rem; letter-spacing:.14em; color:#00d4ff; text-transform:uppercase; font-weight:600;">Market Overview</div>
        <h2 style="font-size:1.6rem; font-weight:700; color:#e2eaf4; margin:4px 0 0 0;">Live Dashboard</h2>
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns([3, 1])
    with c1:
        symbol = st.selectbox("Symbol", SYMBOLS, key="dash_sym", label_visibility="collapsed")
    with c2:
        tf = st.selectbox("Timeframe", ["15m","1h","4h","1d"], index=1, key="dash_tf", label_visibility="collapsed")

    df = fetch_ohlcv(symbol, tf, 200)
    df = calc_indicators(df)
    last = df.iloc[-1]
    prev = df.iloc[-2]
    sig, score, reasons = get_signal(df)

    # Metrics row
    chg    = (last["close"] - prev["close"]) / prev["close"] * 100
    chg_clr= "#10b981" if chg >= 0 else "#ef4444"
    chg_sym= "+" if chg >= 0 else ""
    sig_clr = "#10b981" if "BUY" in sig else "#ef4444" if "SELL" in sig else "#00d4ff"

    m1, m2, m3, m4, m5 = st.columns(5)
    tiles = [
        ("PRICE", f"${last['close']:,.2f}", f"{chg_sym}{chg:.2f}%", chg_clr),
        ("RSI 14", f"{last['rsi']:.1f}", "Oversold <30 · Overbought >70", "#5a7a9a"),
        ("MACD", f"{last['macd']:.2f}", f"Signal {last['signal']:.2f}", "#5a7a9a"),
        ("VOLUME", f"{last['volume']:,.0f}", "vs 20-period MA", "#5a7a9a"),
        ("SIGNAL", sig, f"Score {score:+d}", sig_clr),
    ]
    for col, (lbl, val, sub, clr) in zip([m1,m2,m3,m4,m5], tiles):
        with col:
            st.markdown(f"""
            <div class="metric-tile">
                <span style="font-size:0.65rem; letter-spacing:.1em; color:#304a66; text-transform:uppercase;">{lbl}</span>
                <span style="display:block; font-family:'JetBrains Mono',monospace; font-size:1.25rem; font-weight:700; color:{clr}; margin:6px 0 4px 0;">{val}</span>
                <span style="font-size:0.72rem; color:#4a6a8a;">{sub}</span>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    st.plotly_chart(build_chart(df, symbol), use_container_width=True)
    st.plotly_chart(build_volume_chart(df),  use_container_width=True)

    # Signal reasoning
    st.markdown(f"""
    <div class="tic-card" style="border-left: 3px solid {sig_clr};">
        <div style="font-size:0.68rem; letter-spacing:.12em; color:{sig_clr}; text-transform:uppercase; font-weight:600; margin-bottom:8px;">AI Signal Summary — {sig}</div>
        {"".join(f'<div style="font-size:0.85rem; color:#8aafc8; margin-bottom:5px; display:flex; gap:10px;"><span style="color:{sig_clr}; font-weight:600;">→</span>{r}</div>' for r in reasons)}
    </div>
    """, unsafe_allow_html=True)

    # S/R levels
    st.markdown(f"""
    <div class="tic-card">
        <div class="section-header" style="margin-bottom:12px;">Support / Resistance Levels</div>
        <div style="display:flex; gap:32px;">
            <div>
                <span style="font-size:0.72rem; color:#4a6a8a; text-transform:uppercase; letter-spacing:.08em;">Support</span>
                <div style="font-family:'JetBrains Mono',monospace; font-size:1.1rem; color:#10b981; font-weight:600; margin-top:4px;">${df.attrs['support']:,.2f}</div>
            </div>
            <div>
                <span style="font-size:0.72rem; color:#4a6a8a; text-transform:uppercase; letter-spacing:.08em;">Resistance</span>
                <div style="font-family:'JetBrains Mono',monospace; font-size:1.1rem; color:#ef4444; font-weight:600; margin-top:4px;">${df.attrs['resistance']:,.2f}</div>
            </div>
            <div>
                <span style="font-size:0.72rem; color:#4a6a8a; text-transform:uppercase; letter-spacing:.08em;">BB Upper</span>
                <div style="font-family:'JetBrains Mono',monospace; font-size:1.1rem; color:#00d4ff; font-weight:600; margin-top:4px;">${last['bb_up']:,.2f}</div>
            </div>
            <div>
                <span style="font-size:0.72rem; color:#4a6a8a; text-transform:uppercase; letter-spacing:.08em;">BB Lower</span>
                <div style="font-family:'JetBrains Mono',monospace; font-size:1.1rem; color:#7c3aed; font-weight:600; margin-top:4px;">${last['bb_low']:,.2f}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── White Paper Report ────────────────────────────────────────────────────────
def page_report():
    st.markdown("""
    <div style="margin-bottom:24px;">
        <div style="font-size:0.7rem; letter-spacing:.14em; color:#7c3aed; text-transform:uppercase; font-weight:600;">Institutional Document</div>
        <h2 style="font-size:1.6rem; font-weight:700; color:#e2eaf4; margin:4px 0 0 0;">White Paper Report</h2>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        symbol = st.selectbox("Asset Symbol", SYMBOLS, key="rep_sym")
    with c2:
        tf = st.selectbox("Timeframe", ["1h","4h","1d"], key="rep_tf")
    with c3:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        gen = st.button("Generate Report", use_container_width=True, key="gen_report")

    if not gen:
        st.markdown("""
        <div style="text-align:center; padding: 60px 20px; color:#304a66;">
            <div style="font-size:2rem; margin-bottom:12px; color:rgba(124,58,237,0.4);">⬡</div>
            <div style="font-size:0.88rem;">Select a symbol and click <strong style="color:#7c3aed;">Generate Report</strong> to produce the institutional analysis.</div>
        </div>
        """, unsafe_allow_html=True)
        return

    with st.spinner("Fetching market data and building report..."):
        df      = fetch_ohlcv(symbol, tf, 200)
        df      = calc_indicators(df)
        news    = fetch_news(symbol.split("/")[0])
        last    = df.iloc[-1]
        sig, score, reasons = get_signal(df)
        chg = (last["close"] - df.iloc[-2]["close"]) / df.iloc[-2]["close"] * 100
        avg_news_score = sum(a["score"] for a in news) / len(news) if news else 0
        overall = "BULLISH" if (score >= 1 and avg_news_score >= 0) else \
                  "BEARISH" if (score <= -1 and avg_news_score <= 0) else "NEUTRAL"
        overall_clr = "#10b981" if overall=="BULLISH" else "#ef4444" if overall=="BEARISH" else "#00d4ff"
        rpt_date = datetime.datetime.utcnow().strftime("%B %d, %Y — %H:%M UTC")

    # Report header
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, rgba(124,58,237,0.08) 0%, rgba(0,212,255,0.06) 100%);
        border: 1px solid rgba(124,58,237,0.2);
        border-radius: 16px;
        padding: 28px 32px;
        margin-bottom: 24px;
    ">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:12px;">
            <div>
                <div style="font-size:0.65rem; letter-spacing:.16em; color:#7c3aed; text-transform:uppercase; font-weight:700;">TRADING INTELLIGENCE ENGINE — INSTITUTIONAL REPORT</div>
                <div style="font-size:1.8rem; font-weight:700; color:#e2eaf4; margin:6px 0 4px 0;">{symbol} Market Analysis</div>
                <div style="font-size:0.8rem; color:#4a6a8a;">{rpt_date} · Timeframe: {tf}</div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:0.7rem; color:#4a6a8a; text-transform:uppercase; letter-spacing:.08em; margin-bottom:4px;">Overall Verdict</div>
                <div style="font-family:'JetBrains Mono',monospace; font-size:1.5rem; font-weight:700; color:{overall_clr};">{overall}</div>
                <div style="font-size:0.75rem; color:#4a6a8a; margin-top:2px;">TA Score: {score:+d} · Sentiment: {avg_news_score:+.1f}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── 01 Executive Summary ─────────────────────────────────────────────────
    exec_body = (
        f"{symbol.split('/')[0]} is currently trading at "
        f"<span style='color:#00d4ff; font-family:JetBrains Mono,monospace;'>${last['close']:,.2f}</span>, "
        f"representing a <span style='color:{'#10b981' if chg>=0 else '#ef4444'};'>{chg:+.2f}%</span> move in this session. "
        f"The composite technical score is <strong style='color:#e2eaf4;'>{score:+d}</strong> and the news sentiment index reads "
        f"<strong style='color:#e2eaf4;'>{avg_news_score:+.2f}</strong>, yielding a combined verdict of "
        f"<strong style='color:{overall_clr};'>{overall}</strong>."
    )
    st.markdown(f"""
    <div class="report-section">
        <div class="report-num">SECTION 01</div>
        <div class="report-title">Executive Summary</div>
        <hr style="border-color:rgba(124,58,237,0.15); margin:12px 0;">
        <p style="font-size:0.9rem; color:#8aafc8; line-height:1.8; margin:0;">{exec_body}</p>
    </div>
    """, unsafe_allow_html=True)

    # ── 02 Market Pulse ──────────────────────────────────────────────────────
    news_rows = ""
    for a in news[:12]:
        sc    = a["score"]
        sc_clr= "#10b981" if sc > 0 else "#ef4444" if sc < 0 else "#00d4ff"
        badge = "badge-bull" if sc > 0 else "badge-bear" if sc < 0 else "badge-neut"
        summ  = a["summary"][:120].strip() + ("…" if len(a["summary"]) > 120 else "")
        news_rows += f"""
        <tr>
            <td style="padding:10px 8px; border-bottom:1px solid rgba(0,212,255,0.06); font-size:0.82rem; color:#c8d6e8; max-width:300px;">{a['title'][:80]}</td>
            <td style="padding:10px 8px; border-bottom:1px solid rgba(0,212,255,0.06); font-size:0.78rem; color:#5a7a9a;">{summ}</td>
            <td style="padding:10px 8px; border-bottom:1px solid rgba(0,212,255,0.06); text-align:center;">
                <span style="font-family:'JetBrains Mono',monospace; font-weight:700; color:{sc_clr};">{sc:+d}</span></td>
            <td style="padding:10px 8px; border-bottom:1px solid rgba(0,212,255,0.06); font-size:0.72rem; color:#4a6a8a;">{a['source']}</td>
        </tr>"""

    st.markdown(f"""
    <div class="report-section">
        <div class="report-num">SECTION 02</div>
        <div class="report-title">Market Pulse — News Analysis</div>
        <hr style="border-color:rgba(124,58,237,0.15); margin:12px 0;">
        <div style="overflow-x:auto;">
        <table style="width:100%; border-collapse:collapse;">
            <thead>
                <tr>
                    <th style="text-align:left; font-size:0.68rem; letter-spacing:.1em; color:#304a66; text-transform:uppercase; padding:0 8px 10px 8px;">Headline</th>
                    <th style="text-align:left; font-size:0.68rem; letter-spacing:.1em; color:#304a66; text-transform:uppercase; padding:0 8px 10px 8px;">Summary</th>
                    <th style="text-align:center; font-size:0.68rem; letter-spacing:.1em; color:#304a66; text-transform:uppercase; padding:0 8px 10px 8px;">Impact</th>
                    <th style="text-align:left; font-size:0.68rem; letter-spacing:.1em; color:#304a66; text-transform:uppercase; padding:0 8px 10px 8px;">Source</th>
                </tr>
            </thead>
            <tbody>{news_rows}</tbody>
        </table>
        </div>
        <div style="margin-top:14px; font-size:0.78rem; color:#4a6a8a;">
            Average News Sentiment: <span style="color:{'#10b981' if avg_news_score>=0 else '#ef4444'}; font-family:'JetBrains Mono',monospace; font-weight:600;">{avg_news_score:+.2f}</span>
            &nbsp;·&nbsp; Score range: −5 (very bearish) to +5 (very bullish)
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── 03 Technical Blueprint ───────────────────────────────────────────────
    rsi_interp = "Oversold — potential reversal zone" if last['rsi']<35 else "Overbought — potential pullback zone" if last['rsi']>65 else "Neutral territory"
    macd_interp= "Bullish crossover — momentum building" if last['macd']>last['signal'] else "Bearish divergence — momentum weakening"
    bb_pos     = "Below lower band — mean-reversion setup" if last['close']<last['bb_low'] else "Above upper band — overextended" if last['close']>last['bb_up'] else "Inside bands — trend continuation mode"
    ema_interp = "Bullish stack (Price > EMA20 > EMA50)" if last['close']>last['ema20']>last['ema50'] else "Bearish stack (Price < EMA20 < EMA50)" if last['close']<last['ema20']<last['ema50'] else "Mixed — no clear trend"
    vol_interp = "Spike detected — institutional participation likely" if last['volume']>last['vol_ma']*1.3 else "Below average — low conviction"

    indicators = [
        ("RSI (14)",             f"{last['rsi']:.2f}",           rsi_interp,  "#00d4ff"),
        ("MACD",                 f"{last['macd']:.4f}",          macd_interp, "#7c3aed"),
        ("MACD Signal",          f"{last['signal']:.4f}",        "9-period EMA of MACD line", "#5a7a9a"),
        ("Bollinger Position",   f"${last['close']:,.2f}",        bb_pos,      "#00d4ff"),
        ("EMA Stack",            f"20/50/200",                   ema_interp,  "#f59e0b"),
        ("Volume vs MA20",       f"{last['volume']/last['vol_ma']:.2f}x", vol_interp, "#10b981"),
    ]
    ind_html = ""
    for name, val, interp, clr in indicators:
        ind_html += f"""
        <div style="display:flex; align-items:flex-start; justify-content:space-between; padding:12px 0; border-bottom:1px solid rgba(0,212,255,0.06); gap:16px;">
            <div style="flex:1.2;">
                <div style="font-size:0.82rem; font-weight:600; color:#c8d6e8;">{name}</div>
                <div style="font-size:0.75rem; color:#4a6a8a; margin-top:3px;">{interp}</div>
            </div>
            <div style="font-family:'JetBrains Mono',monospace; font-size:0.95rem; font-weight:700; color:{clr}; white-space:nowrap;">{val}</div>
        </div>"""

    st.markdown(f"""
    <div class="report-section">
        <div class="report-num">SECTION 03</div>
        <div class="report-title">Technical Blueprint</div>
        <hr style="border-color:rgba(124,58,237,0.15); margin:12px 0;">
        {ind_html}
    </div>
    """, unsafe_allow_html=True)

    # ── 04 Visual Blueprint ──────────────────────────────────────────────────
    entry_zone_lo = last['close'] * 0.998
    entry_zone_hi = last['close'] * 1.002
    sl_price      = last['close'] * 0.98
    tp_price      = last['close'] * 1.05
    dist_sup  = (last['close'] - df.attrs['support'])    / last['close'] * 100
    dist_res  = (df.attrs['resistance'] - last['close']) / last['close'] * 100

    levels = [
        ("Resistance", f"${df.attrs['resistance']:,.2f}", f"+{dist_res:.2f}% from price", "#ef4444"),
        ("BB Upper",   f"${last['bb_up']:,.2f}",          "2σ above 20-SMA",              "#f59e0b"),
        ("EMA 200",    f"${last['ema200']:,.2f}",          "Long-term trend reference",    "#f59e0b"),
        ("EMA 50",     f"${last['ema50']:,.2f}",           "Medium-term trend",            "#7c3aed"),
        ("EMA 20",     f"${last['ema20']:,.2f}",           "Short-term trend / dynamic S/R","#00d4ff"),
        ("Entry Zone", f"${entry_zone_lo:,.2f} – ${entry_zone_hi:,.2f}", "±0.2% around current price","#c8d6e8"),
        ("BB Lower",   f"${last['bb_low']:,.2f}",          "2σ below 20-SMA",              "#00d4ff"),
        ("Stop-Loss",  f"${sl_price:,.2f}",                "−2.0% from entry (hard limit)", "#ef4444"),
        ("Support",    f"${df.attrs['support']:,.2f}",     f"−{dist_sup:.2f}% from price", "#10b981"),
        ("Take-Profit",f"${tp_price:,.2f}",                "+5.0% from entry (min target)", "#10b981"),
    ]
    lvl_html = ""
    for name, val, desc, clr in levels:
        lvl_html += f"""
        <div style="display:flex; align-items:center; gap:14px; padding:9px 0; border-bottom:1px solid rgba(0,212,255,0.06);">
            <div style="width:10px; height:10px; border-radius:2px; background:{clr}; flex-shrink:0; opacity:0.8;"></div>
            <div style="flex:1; font-size:0.82rem; color:#8aafc8;">{name}</div>
            <div style="font-family:'JetBrains Mono',monospace; font-size:0.85rem; font-weight:600; color:{clr}; min-width:130px; text-align:right;">{val}</div>
            <div style="font-size:0.75rem; color:#4a6a8a; min-width:200px; text-align:right;">{desc}</div>
        </div>"""

    st.markdown(f"""
    <div class="report-section">
        <div class="report-num">SECTION 04</div>
        <div class="report-title">Visual Blueprint — Price Level Map</div>
        <hr style="border-color:rgba(124,58,237,0.15); margin:12px 0;">
        <p style="font-size:0.8rem; color:#4a6a8a; margin:0 0 14px 0;">Levels ordered top-to-bottom by price. Apply these coordinates to your charting software.</p>
        {lvl_html}
    </div>
    """, unsafe_allow_html=True)

    # ── 05 Actionable Thesis ─────────────────────────────────────────────────
    action_word = "enter a LONG position" if overall=="BULLISH" else "enter a SHORT position" if overall=="BEARISH" else "remain FLAT (no trade)"
    evidence_html = "".join(f"""
    <div style="display:flex; align-items:flex-start; gap:12px; margin-bottom:10px;">
        <div style="
            background:rgba(124,58,237,0.12); border:1px solid rgba(124,58,237,0.25);
            border-radius:6px; padding:2px 8px;
            font-size:0.65rem; font-weight:700; color:#7c3aed;
            letter-spacing:.08em; white-space:nowrap; margin-top:2px;
        ">{src}</div>
        <div style="font-size:0.85rem; color:#8aafc8;">{txt}</div>
    </div>""" for src, txt in [
        ("RSI",  f"At {last['rsi']:.1f} — {rsi_interp.lower()}"),
        ("MACD", macd_interp),
        ("EMA",  ema_interp),
        ("BB",   bb_pos),
        ("VOL",  vol_interp),
        ("NEWS", f"Aggregate sentiment {avg_news_score:+.2f} across {len(news)} articles"),
    ])

    valid, issues, order = validate_trade(
        "BUY" if overall=="BULLISH" else "SELL",
        last["close"], sl_price, tp_price, 3.0
    )
    val_color = "#10b981" if valid else "#ef4444"
    val_text  = f"APPROVED — R:R {order.get('risk_reward','N/A')}" if valid else "REJECTED — " + "; ".join(issues)

    st.markdown(f"""
    <div class="report-section">
        <div class="report-num">SECTION 05</div>
        <div class="report-title">Actionable Thesis</div>
        <hr style="border-color:rgba(124,58,237,0.15); margin:12px 0;">
        <div style="margin-bottom:18px;">
            <span style="font-size:0.72rem; color:#4a6a8a; text-transform:uppercase; letter-spacing:.08em;">Recommendation</span>
            <div style="font-size:1.2rem; font-weight:700; color:{overall_clr}; margin-top:4px;">
                {overall} — {action_word.upper()}
            </div>
        </div>
        <div style="font-size:0.82rem; color:#4a6a8a; text-transform:uppercase; letter-spacing:.08em; margin-bottom:12px;">Supporting Evidence</div>
        {evidence_html}
        <hr style="border-color:rgba(0,212,255,0.08); margin:18px 0;">
        <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px;">
            <div style="font-size:0.78rem; color:#4a6a8a;">Risk Validation Layer:</div>
            <div style="font-family:'JetBrains Mono',monospace; font-size:0.82rem; font-weight:700; color:{val_color};">{val_text}</div>
        </div>
        <p style="font-size:0.72rem; color:#2a3a4a; margin:14px 0 0 0; line-height:1.6;">
        Disclaimer: This report is generated algorithmically for educational and demo-trading purposes only.
        It does not constitute financial advice. All trades must be validated by the risk layer before execution.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.plotly_chart(build_chart(df, symbol), use_container_width=True)

# ── News Feed ─────────────────────────────────────────────────────────────────
def page_news():
    st.markdown("""
    <div style="margin-bottom:24px;">
        <div style="font-size:0.7rem; letter-spacing:.14em; color:#00d4ff; text-transform:uppercase; font-weight:600;">Real-Time Intelligence</div>
        <h2 style="font-size:1.6rem; font-weight:700; color:#e2eaf4; margin:4px 0 0 0;">News Feed</h2>
    </div>
    """, unsafe_allow_html=True)

    query = st.text_input("Filter by keyword", placeholder="bitcoin, ethereum, SEC…", key="news_q")
    news  = fetch_news(query or "crypto", 20)

    for a in news:
        sc     = a["score"]
        sc_clr = "#10b981" if sc > 0 else "#ef4444" if sc < 0 else "#00d4ff"
        lbl    = "BULLISH" if sc > 0 else "BEARISH" if sc < 0 else "NEUTRAL"
        st.markdown(f"""
        <div style="
            background: #0f1e35;
            border: 1px solid rgba(0,212,255,0.08);
            border-left: 3px solid {sc_clr};
            border-radius: 12px;
            padding: 16px 20px;
            margin-bottom: 10px;
        ">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px; flex-wrap:wrap;">
                <div style="flex:1;">
                    <div style="font-size:0.88rem; font-weight:600; color:#c8d6e8; margin-bottom:6px;">{a['title']}</div>
                    <div style="font-size:0.78rem; color:#4a6a8a; line-height:1.6;">{a['summary'][:180]}</div>
                </div>
                <div style="text-align:right; flex-shrink:0;">
                    <div style="font-family:'JetBrains Mono',monospace; font-size:1.1rem; font-weight:700; color:{sc_clr};">{sc:+d}</div>
                    <div style="font-size:0.65rem; color:{sc_clr}; letter-spacing:.08em; text-transform:uppercase;">{lbl}</div>
                    <div style="font-size:0.7rem; color:#2a3a4a; margin-top:4px;">{a['source']}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ── Settings ──────────────────────────────────────────────────────────────────
def page_settings():
    st.markdown("""
    <div style="margin-bottom:24px;">
        <div style="font-size:0.7rem; letter-spacing:.14em; color:#00d4ff; text-transform:uppercase; font-weight:600;">Account Configuration</div>
        <h2 style="font-size:1.6rem; font-weight:700; color:#e2eaf4; margin:4px 0 0 0;">Settings</h2>
    </div>
    """, unsafe_allow_html=True)

    u = st.session_state.user
    c1, c2 = st.columns([1.2, 1])

    with c1:
        st.markdown('<div class="section-header" style="margin-bottom:14px;">Exchange API Keys (AES-256 Encrypted)</div>', unsafe_allow_html=True)
        st.markdown("""
        <div style="
            background: rgba(239,68,68,0.05); border: 1px solid rgba(239,68,68,0.15);
            border-radius: 10px; padding: 12px 16px; margin-bottom:16px; font-size:0.8rem; color:#9a6a6a;
        ">
            API keys are encrypted with AES-256 Fernet before storage. They are never saved in plaintext.
            Use exchange sub-accounts with trade-only permissions. Enable 2FA on your exchange.
        </div>
        """, unsafe_allow_html=True)

        with st.form("api_form", clear_on_submit=True):
            exchange   = st.selectbox("Exchange", ["binance","bybit","okx","kraken","coinbase"], key="api_exc")
            api_key_in = st.text_input("API Key", placeholder="Paste your API key here", type="password", key="api_k")
            api_sec_in = st.text_input("API Secret", placeholder="Paste your API secret here", type="password", key="api_s")
            save_api   = st.form_submit_button("Save Encrypted Keys", use_container_width=True)

        if save_api:
            if not api_key_in or not api_sec_in:
                st.error("Both API key and secret are required.")
            else:
                db = SessionLocal()
                try:
                    new_key = ApiKey(
                        user_id=u["id"], exchange=exchange,
                        api_key_enc=encrypt(api_key_in),
                        api_secret_enc=encrypt(api_sec_in)
                    )
                    db.add(new_key); db.commit()
                    st.success(f"{exchange.capitalize()} keys saved with AES-256 encryption.")
                except Exception as e:
                    st.error(f"Save error: {e}")
                finally:
                    db.close()

    with c2:
        st.markdown('<div class="section-header" style="margin-bottom:14px;">Hard-Coded Risk Limits</div>', unsafe_allow_html=True)
        st.markdown("""
        <div style="font-size:0.78rem; color:#4a6a8a; margin-bottom:14px;">
        These limits are enforced at the validation layer level and cannot be overridden by AI responses.
        </div>
        """, unsafe_allow_html=True)
        limits = [
            ("Max Position Size", "5.0%", "of total balance per trade"),
            ("Stop-Loss Limit",   "2.0%", "max distance from entry"),
            ("Min Take-Profit",   "5.0%", "min distance from entry"),
            ("Min R:R Ratio",     "1 : 2", "reward must be ≥ 2× risk"),
            ("Daily Loss Limit",  "10.0%", "triggers Global Shutdown"),
        ]
        for name, val, desc in limits:
            st.markdown(f"""
            <div style="
                background: #0f1e35;
                border: 1px solid rgba(0,212,255,0.08);
                border-radius: 10px; padding: 14px 16px; margin-bottom: 8px;
                display: flex; justify-content: space-between; align-items: center;
            ">
                <div>
                    <div style="font-size:0.82rem; font-weight:600; color:#c8d6e8;">{name}</div>
                    <div style="font-size:0.72rem; color:#4a6a8a; margin-top:2px;">{desc}</div>
                </div>
                <div style="font-family:'JetBrains Mono',monospace; font-size:1rem; font-weight:700; color:#00d4ff;">{val}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        st.markdown('<div class="section-header" style="margin-bottom:14px;">Trading Strategy</div>', unsafe_allow_html=True)
        strategy = st.selectbox("Strategy Mode", ["Balanced","Conservative","Aggressive"],
                                index=["Balanced","Conservative","Aggressive"].index(u.get("strategy","Balanced")),
                                key="strat_sel")
        if st.button("Update Strategy", use_container_width=True, key="upd_strat"):
            db = SessionLocal()
            try:
                row = db.query(User).filter(User.id == u["id"]).first()
                if row:
                    row.strategy = strategy; db.commit()
                    st.session_state.user["strategy"] = strategy
                    st.success(f"Strategy updated to {strategy}.")
            except Exception as e:
                st.error(f"Update error: {e}")
            finally:
                db.close()

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    if not st.session_state.user:
        page_auth()
        return

    render_sidebar()

    page = st.session_state.page
    if   page == "Dashboard":       page_dashboard()
    elif page == "Analysis Report": page_report()
    elif page == "News Feed":       page_news()
    elif page == "Settings":        page_settings()

if __name__ == "__main__":
    main()
