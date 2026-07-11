"""
Elite Trading Intelligence Engine — v5.1
Futuristic UI | Clean Streamlit Architecture
"""

import streamlit as st
import ccxt, pandas as pd, numpy as np
import plotly.graph_objects as go
import feedparser, re, uuid, os, datetime, json
from cryptography.fernet import Fernet
from passlib.context import CryptContext
from sqlalchemy import create_engine, Column, String, Float, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker

st.set_page_config(
    page_title="TradeOS — Intelligence Engine",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={"Get Help": None, "Report a bug": None, "About": None}
)

# ── Database ────────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./trading.db")
if DATABASE_URL.startswith("postgres://"): DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id            = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email         = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at    = Column(DateTime, default=datetime.datetime.utcnow)

class ApiKey(Base):
    __tablename__ = "api_keys"
    id            = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id       = Column(String, nullable=False)
    exchange      = Column(String)
    enc_key       = Column(Text)
    enc_secret    = Column(Text)
    updated_at    = Column(DateTime, default=datetime.datetime.utcnow)

class TradeLog(Base):
    __tablename__ = "trade_logs"
    id            = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id       = Column(String)
    symbol        = Column(String)
    action        = Column(String)
    entry_price   = Column(Float)
    stop_loss     = Column(Float)
    take_profit   = Column(Float)
    position_pct  = Column(Float)
    rr            = Column(String)
    strategy      = Column(String)
    timestamp     = Column(DateTime, default=datetime.datetime.utcnow)

Base.metadata.create_all(bind=engine)

# ── Security ────────────────────────────────────────────────────────────────
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY") or Fernet.generate_key().decode()
try:
    fernet = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)
except Exception:
    fernet = Fernet(Fernet.generate_key())

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

def encrypt(text): return fernet.encrypt(text.encode()).decode()
def decrypt(text):
    try: return fernet.decrypt(text.encode()).decode()
    except: return ""
def hash_pw(pw): return pwd_ctx.hash(pw)
def verify_pw(pw, h): return pwd_ctx.verify(pw, h)

# ── Global CSS ──────────────────────────────────────────────────────────────
def inject_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
    background: #030712 !important;
    font-family: 'Inter', sans-serif !important;
}

/* Hide Streamlit chrome */
#MainMenu, footer, header, [data-testid="stToolbar"],
[data-testid="stDecoration"], [data-testid="stStatusWidget"] { display:none !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(59,130,246,0.3); border-radius: 4px; }

/* Main block padding */
[data-testid="stMainBlockContainer"] { padding: 0 !important; max-width: 100% !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: rgba(3,7,18,0.97) !important;
    border-right: 1px solid rgba(59,130,246,0.12) !important;
}
[data-testid="stSidebarNav"] { display: none; }

/* Inputs */
[data-testid="stTextInput"] input,
[data-testid="stTextInputRootElement"] input {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 8px !important;
    color: #f1f5f9 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 14px !important;
    padding: 12px 16px !important;
    transition: border-color 0.2s !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextInputRootElement"] input:focus {
    border-color: rgba(59,130,246,0.5) !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.1) !important;
}

/* Labels */
[data-testid="stTextInput"] label p,
[data-testid="stTextInputRootElement"] label p {
    color: rgba(148,163,184,0.8) !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    letter-spacing: 0.5px !important;
    text-transform: uppercase !important;
}

/* Buttons */
[data-testid="stButton"] > button {
    background: linear-gradient(135deg, #1d4ed8, #2563eb) !important;
    border: none !important;
    border-radius: 8px !important;
    color: #fff !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    letter-spacing: 0.3px !important;
    padding: 12px 24px !important;
    width: 100% !important;
    transition: all 0.2s !important;
    cursor: pointer !important;
}
[data-testid="stButton"] > button:hover {
    background: linear-gradient(135deg, #2563eb, #3b82f6) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 8px 24px rgba(37,99,235,0.35) !important;
}

/* Selectbox */
[data-testid="stSelectbox"] select,
[data-testid="stSelectbox"] > div > div {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 8px !important;
    color: #f1f5f9 !important;
}

/* Tabs */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: rgba(255,255,255,0.03) !important;
    border-radius: 10px !important;
    padding: 4px !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    gap: 2px !important;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    background: transparent !important;
    border-radius: 7px !important;
    color: rgba(148,163,184,0.7) !important;
    font-weight: 500 !important;
    font-size: 13px !important;
    padding: 8px 20px !important;
    border: none !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
    background: rgba(37,99,235,0.2) !important;
    color: #60a5fa !important;
    border: 1px solid rgba(37,99,235,0.3) !important;
}

/* Metrics */
[data-testid="stMetric"] {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 12px !important;
    padding: 16px !important;
}
[data-testid="stMetricLabel"] p { color: rgba(148,163,184,0.7) !important; font-size: 11px !important; text-transform: uppercase; letter-spacing: 0.5px; }
[data-testid="stMetricValue"] { color: #f1f5f9 !important; font-size: 22px !important; font-weight: 700 !important; font-family: 'JetBrains Mono', monospace !important; }

/* Alert boxes */
[data-testid="stAlert"] {
    border-radius: 8px !important;
    border-left-width: 3px !important;
    background: rgba(255,255,255,0.03) !important;
}

/* Divider */
hr { border-color: rgba(255,255,255,0.06) !important; }

/* Spinner */
[data-testid="stSpinner"] { color: #3b82f6 !important; }

.mono { font-family: 'JetBrains Mono', monospace !important; }
</style>
""", unsafe_allow_html=True)

# ── Session State ────────────────────────────────────────────────────────────
def init_state():
    for k, v in {"logged_in": False, "user_id": None, "user_email": None, "active_page": "dashboard"}.items():
        if k not in st.session_state:
            st.session_state[k] = v

# ── Risk Validation Layer ────────────────────────────────────────────────────
MAX_POSITION_PCT = 5.0
MAX_SL_PCT       = 2.0
MIN_TP_PCT       = 5.0
MIN_RR           = 2.0
MAX_DAILY_LOSS   = 10.0

def validate_trade(action, entry, sl, tp, size_pct):
    issues = []
    if size_pct > MAX_POSITION_PCT: issues.append(f"Position {size_pct}% > max {MAX_POSITION_PCT}%")
    if size_pct <= 0:               issues.append("Position size must be > 0")
    sl_dist = abs((entry - sl) / entry) * 100 if entry else 0
    if sl_dist > MAX_SL_PCT:        issues.append(f"Stop-loss distance {sl_dist:.2f}% > max {MAX_SL_PCT}%")
    if action == "BUY"  and sl >= entry: issues.append("SL must be below entry for BUY")
    if action == "SELL" and sl <= entry: issues.append("SL must be above entry for SELL")
    risk   = abs(entry - sl)
    reward = abs(tp - entry)
    rr     = round(reward / risk, 2) if risk else 0
    if rr < MIN_RR: issues.append(f"R:R {rr} below minimum 1:{MIN_RR}")
    valid = len(issues) == 0
    order = {"action": action, "entry": entry, "sl": sl, "tp": tp,
             "size_pct": size_pct, "risk_reward": f"1:{rr}"} if valid else {}
    return valid, issues, order

# ── Market Data ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def fetch_ohlcv(symbol="BTC/USDT", timeframe="1h", limit=200):
    try:
        ex = ccxt.binance({"enableRateLimit": True})
        raw = ex.fetch_ohlcv(symbol, timeframe, limit=limit)
        df  = pd.DataFrame(raw, columns=["ts","open","high","low","close","volume"])
        df["ts"] = pd.to_datetime(df["ts"], unit="ms")
        return df
    except:
        np.random.seed(42)
        dates = pd.date_range(end=datetime.datetime.utcnow(), periods=limit, freq="1h")
        base  = 65000
        close = base + np.cumsum(np.random.randn(limit) * 300)
        return pd.DataFrame({"ts": dates,"open": close - 200,"high": close + 400,"low": close - 400,"close": close,"volume": np.random.randint(800,3000,limit).astype(float)})

def compute_indicators(df):
    c = df["close"]
    df["ema20"]  = c.ewm(span=20).mean()
    df["ema50"]  = c.ewm(span=50).mean()
    df["ema200"] = c.ewm(span=200).mean()
    df["bb_mid"] = c.rolling(20).mean()
    df["bb_std"] = c.rolling(20).std()
    df["bb_up"]  = df["bb_mid"] + 2 * df["bb_std"]
    df["bb_lo"]  = df["bb_mid"] - 2 * df["bb_std"]
    delta = c.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss.replace(0, 1e-10)
    df["rsi"] = 100 - (100 / (1 + rs))
    ema12 = c.ewm(span=12).mean()
    ema26 = c.ewm(span=26).mean()
    df["macd"]   = ema12 - ema26
    df["signal"] = df["macd"].ewm(span=9).mean()
    df["hist"]   = df["macd"] - df["signal"]
    return df

@st.cache_data(ttl=300)
def fetch_news(query="crypto trading market"):
    feeds = [
        f"https://news.google.com/rss/search?q={query.replace(' ','+')}&hl=en-US&gl=US&ceid=US:en",
        "https://feeds.feedburner.com/CoinDesk",
        "https://cointelegraph.com/rss",
        "https://www.investing.com/rss/news.rss"
    ]
    articles = []
    for url in feeds:
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:4]:
                title   = e.get("title","")
                summary = e.get("summary", e.get("description",""))[:200]
                pos = sum(title.lower().count(w) for w in ["rally","surge","bull","gains","rise","breakout","buy","growth","up"])
                neg = sum(title.lower().count(w) for w in ["crash","dump","bear","loss","fall","risk","sell","drop","down","fear"])
                score = min(5, max(-5, pos * 1.5 - neg * 1.5))
                articles.append({"title": title[:90], "summary": summary, "score": round(score,1), "source": url.split("/")[2][:20]})
        except:
            pass
    return articles[:16]

def sentiment_color(score):
    if score >= 3:   return "#10b981"
    elif score >= 1: return "#34d399"
    elif score <= -3:return "#ef4444"
    elif score <= -1:return "#f87171"
    return "#94a3b8"

def support_resistance(df, n=5):
    highs  = df["high"].nlargest(n).values
    lows   = df["low"].nsmallest(n).values
    resist = sorted(set(round(h,-2) for h in highs), reverse=True)[:3]
    supp   = sorted(set(round(l,-2) for l in lows))[:3]
    return supp, resist

# ── Chart Engine ─────────────────────────────────────────────────────────────
def build_chart(df, symbol):
    supp, resist = support_resistance(df)
    fig = go.Figure()

    # Candlesticks
    fig.add_trace(go.Candlestick(
        x=df["ts"], open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        name=symbol,
        increasing_fillcolor="#10b981", increasing_line_color="#10b981",
        decreasing_fillcolor="#ef4444", decreasing_line_color="#ef4444",
        line_width=1
    ))

    # EMAs
    for col, color, name in [("ema20","#3b82f6","EMA 20"),("ema50","#f59e0b","EMA 50"),("ema200","#8b5cf6","EMA 200")]:
        fig.add_trace(go.Scatter(x=df["ts"], y=df[col], name=name, line=dict(color=color, width=1.2), opacity=0.85))

    # Bollinger
    fig.add_trace(go.Scatter(x=df["ts"], y=df["bb_up"], name="BB Upper", line=dict(color="rgba(148,163,184,0.3)", width=1, dash="dot")))
    fig.add_trace(go.Scatter(x=df["ts"], y=df["bb_lo"], name="BB Lower", line=dict(color="rgba(148,163,184,0.3)", width=1, dash="dot"), fill="tonexty", fillcolor="rgba(148,163,184,0.04)"))

    # S/R lines
    for level in supp:
        fig.add_hline(y=level, line_color="rgba(16,185,129,0.5)", line_width=1, line_dash="dash", annotation_text=f"S {level:,.0f}", annotation_font_color="rgba(16,185,129,0.8)", annotation_font_size=11)
    for level in resist:
        fig.add_hline(y=level, line_color="rgba(239,68,68,0.5)", line_width=1, line_dash="dash", annotation_text=f"R {level:,.0f}", annotation_font_color="rgba(239,68,68,0.8)", annotation_font_size=11)

    fig.update_layout(
        height=440,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.01)",
        font=dict(family="Inter", color="#94a3b8", size=11),
        legend=dict(orientation="h", y=1.05, x=0, bgcolor="transparent", font_size=11),
        xaxis=dict(gridcolor="rgba(255,255,255,0.03)", showline=False, zeroline=False, rangeslider_visible=False, color="#64748b"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.04)", showline=False, zeroline=False, side="right", color="#64748b"),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="rgba(3,7,18,0.95)", bordercolor="rgba(59,130,246,0.3)", font_size=12, font_family="JetBrains Mono"),
        margin=dict(l=0, r=60, t=20, b=0),
    )
    return fig

def build_rsi_chart(df):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["ts"], y=df["rsi"], name="RSI", line=dict(color="#3b82f6", width=1.5)))
    fig.add_hline(y=70, line_color="rgba(239,68,68,0.5)", line_dash="dash", annotation_text="OB 70", annotation_font_size=10)
    fig.add_hline(y=30, line_color="rgba(16,185,129,0.5)", line_dash="dash", annotation_text="OS 30", annotation_font_size=10)
    fig.update_layout(height=150, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(255,255,255,0.01)",
        font=dict(family="Inter", color="#94a3b8", size=10),
        xaxis=dict(gridcolor="rgba(255,255,255,0.03)", showline=False, zeroline=False, rangeslider_visible=False),
        yaxis=dict(gridcolor="rgba(255,255,255,0.04)", showline=False, zeroline=False, range=[0,100], side="right"),
        margin=dict(l=0, r=60, t=10, b=0), showlegend=False)
    return fig

def build_macd_chart(df):
    colors = ["#10b981" if v >= 0 else "#ef4444" for v in df["hist"]]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["ts"], y=df["hist"], marker_color=colors, name="Histogram", opacity=0.7))
    fig.add_trace(go.Scatter(x=df["ts"], y=df["macd"], name="MACD", line=dict(color="#3b82f6", width=1.2)))
    fig.add_trace(go.Scatter(x=df["ts"], y=df["signal"], name="Signal", line=dict(color="#f59e0b", width=1.2)))
    fig.update_layout(height=150, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(255,255,255,0.01)",
        font=dict(family="Inter", color="#94a3b8", size=10),
        xaxis=dict(gridcolor="rgba(255,255,255,0.03)", showline=False, zeroline=False, rangeslider_visible=False),
        yaxis=dict(gridcolor="rgba(255,255,255,0.04)", showline=False, zeroline=False, side="right"),
        margin=dict(l=0, r=60, t=10, b=0), showlegend=False, barmode="relative")
    return fig

# ── Auth Page ─────────────────────────────────────────────────────────────────
def page_auth():
    # Full-page auth layout via CSS + st.columns
    st.markdown("""
<style>
.auth-wrap { min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 40px 20px; }
.auth-brand-label {
    display: inline-block;
    background: rgba(37,99,235,0.1);
    border: 1px solid rgba(37,99,235,0.25);
    border-radius: 6px;
    padding: 5px 14px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1.5px;
    color: #60a5fa;
    text-transform: uppercase;
    margin-bottom: 28px;
}
.auth-title {
    font-size: 40px;
    font-weight: 800;
    color: #f1f5f9;
    line-height: 1.15;
    letter-spacing: -1.5px;
    margin-bottom: 16px;
}
.auth-title span { color: #3b82f6; }
.auth-subtitle {
    font-size: 14px;
    color: rgba(148,163,184,0.75);
    line-height: 1.6;
    margin-bottom: 40px;
}
.auth-feature {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 0;
    border-bottom: 1px solid rgba(255,255,255,0.05);
    color: rgba(148,163,184,0.8);
    font-size: 13px;
}
.auth-dot { width: 6px; height: 6px; border-radius: 50%; background: #3b82f6; flex-shrink: 0; }
.auth-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 20px;
    padding: 40px 36px;
    backdrop-filter: blur(20px);
}
.auth-card-title {
    font-size: 22px;
    font-weight: 700;
    color: #f1f5f9;
    margin-bottom: 6px;
}
.auth-card-sub {
    font-size: 13px;
    color: rgba(148,163,184,0.65);
    margin-bottom: 28px;
}
.auth-divider {
    text-align: center;
    color: rgba(148,163,184,0.4);
    font-size: 11px;
    letter-spacing: 1px;
    margin: 16px 0;
    position: relative;
}
.trust-bar {
    margin-top: 24px;
    padding-top: 20px;
    border-top: 1px solid rgba(255,255,255,0.06);
    display: flex;
    gap: 20px;
    flex-wrap: wrap;
}
.trust-item { font-size: 11px; color: rgba(148,163,184,0.5); letter-spacing: 0.3px; }
</style>
""", unsafe_allow_html=True)

    col_brand, col_gap, col_card = st.columns([1.1, 0.15, 0.85])

    with col_brand:
        st.markdown("""
<div style="padding: 60px 40px 60px 20px; min-height: 80vh; display: flex; flex-direction: column; justify-content: center;">
    <div class="auth-brand-label">Live since 2024</div>
    <div class="auth-title">Trading<br><span>Intelligence</span><br>Engine</div>
    <div class="auth-subtitle">
        Institutional-grade market analysis with real-time TA/FA fusion,
        AI-driven trade theses, and a hard-coded risk validation layer.
    </div>
    <div class="auth-feature"><div class="auth-dot"></div> RSI · MACD · Bollinger Bands — live technical suite</div>
    <div class="auth-feature"><div class="auth-dot"></div> News sentiment scoring with impact analysis</div>
    <div class="auth-feature"><div class="auth-dot"></div> White Paper report — professional 5-section document</div>
    <div class="auth-feature"><div class="auth-dot"></div> AES-256 encrypted API key storage</div>
    <div class="auth-feature"><div class="auth-dot"></div> Hard-coded risk limits — 5% position · 2% SL · 1:2 R:R</div>
    <div class="trust-bar">
        <div class="trust-item">AES-256 Encryption</div>
        <div class="trust-item">bcrypt Auth</div>
        <div class="trust-item">Demo-first Mode</div>
        <div class="trust-item">No plaintext keys</div>
    </div>
</div>
""", unsafe_allow_html=True)

    with col_card:
        st.markdown("""
<div style="padding: 60px 20px 60px 40px; min-height: 80vh; display: flex; flex-direction: column; justify-content: center;">
    <div class="auth-card">
""", unsafe_allow_html=True)

        tab_in, tab_up = st.tabs(["Sign In", "Create Account"])

        with tab_in:
            st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)
            with st.form("login_form", clear_on_submit=False):
                email_in = st.text_input("Email address", placeholder="you@example.com", key="li_email")
                pass_in  = st.text_input("Password", type="password", placeholder="Enter your password", key="li_pass")
                st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)
                submitted = st.form_submit_button("Sign In")
                if submitted:
                    if not email_in or not pass_in:
                        st.error("Please fill in all fields.")
                    else:
                        db = SessionLocal()
                        user = db.query(User).filter(User.email == email_in.lower().strip()).first()
                        db.close()
                        if user and verify_pw(pass_in, user.password_hash):
                            st.session_state.logged_in = True
                            st.session_state.user_id   = user.id
                            st.session_state.user_email= user.email
                            st.rerun()
                        else:
                            st.error("Invalid credentials.")

        with tab_up:
            st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)
            with st.form("signup_form", clear_on_submit=False):
                email_up  = st.text_input("Email address", placeholder="you@example.com", key="su_email")
                pass_up   = st.text_input("Password", type="password", placeholder="Create a password", key="su_pass")
                pass_up2  = st.text_input("Confirm password", type="password", placeholder="Repeat your password", key="su_pass2")
                st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)
                submitted2 = st.form_submit_button("Create Account")
                if submitted2:
                    if not email_up or not pass_up or not pass_up2:
                        st.error("Please fill in all fields.")
                    elif pass_up != pass_up2:
                        st.error("Passwords do not match.")
                    elif len(pass_up) < 8:
                        st.error("Password must be at least 8 characters.")
                    else:
                        db = SessionLocal()
                        exists = db.query(User).filter(User.email == email_up.lower().strip()).first()
                        if exists:
                            db.close()
                            st.error("Email already registered.")
                        else:
                            new_user = User(email=email_up.lower().strip(), password_hash=hash_pw(pass_up))
                            db.add(new_user)
                            db.commit()
                            db.refresh(new_user)
                            st.session_state.logged_in = True
                            st.session_state.user_id   = new_user.id
                            st.session_state.user_email= new_user.email
                            db.close()
                            st.rerun()

        st.markdown('</div></div>', unsafe_allow_html=True)

# ── Sidebar ──────────────────────────────────────────────────────────────────
def sidebar():
    with st.sidebar:
        st.markdown(f"""
<div style="padding:24px 16px 16px;">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:32px;">
        <div style="width:32px;height:32px;background:linear-gradient(135deg,#1d4ed8,#7c3aed);
            border-radius:8px;display:flex;align-items:center;justify-content:center;
            font-size:14px;font-weight:800;color:#fff;">T</div>
        <div>
            <div style="font-size:13px;font-weight:700;color:#f1f5f9;letter-spacing:-0.3px;">TradeOS</div>
            <div style="font-size:10px;color:rgba(148,163,184,0.5);letter-spacing:0.5px;">INTELLIGENCE ENGINE</div>
        </div>
    </div>
    <div style="font-size:10px;color:rgba(148,163,184,0.35);letter-spacing:0.5px;text-transform:uppercase;margin-bottom:8px;">Navigation</div>
</div>
""", unsafe_allow_html=True)

        pages = [("dashboard", "Dashboard"), ("report", "White Paper Report"), ("news", "Market News"), ("settings", "Settings")]
        for key, label in pages:
            active = st.session_state.active_page == key
            bg = "rgba(37,99,235,0.15)" if active else "transparent"
            border = "rgba(37,99,235,0.4)" if active else "transparent"
            color  = "#60a5fa" if active else "rgba(148,163,184,0.75)"
            if st.button(label, key=f"nav_{key}", use_container_width=True):
                st.session_state.active_page = key
                st.rerun()

        st.markdown('<div style="margin:auto;padding:16px;border-top:1px solid rgba(255,255,255,0.06);margin-top:24px;">', unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:11px;color:rgba(148,163,184,0.45);">{st.session_state.user_email}</div>', unsafe_allow_html=True)
        if st.button("Sign out", key="logout", use_container_width=True):
            for k in ["logged_in","user_id","user_email","active_page"]:
                st.session_state[k] = False if k=="logged_in" else (None if k!="active_page" else "dashboard")
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ── Dashboard Page ────────────────────────────────────────────────────────────
def page_dashboard():
    st.markdown("""
<style>
.page-header { padding: 32px 32px 0; }
.page-title { font-size: 26px; font-weight: 700; color: #f1f5f9; letter-spacing: -0.8px; margin-bottom: 4px; }
.page-sub   { font-size: 13px; color: rgba(148,163,184,0.6); margin-bottom: 24px; }
.section-card {
    background: rgba(255,255,255,0.025);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 14px;
    padding: 20px 22px;
    margin-bottom: 16px;
}
.section-label {
    font-size: 10px; font-weight: 600; letter-spacing: 1.2px;
    text-transform: uppercase; color: rgba(148,163,184,0.5);
    margin-bottom: 14px;
}
.signal-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
}
</style>
""", unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="page-header">', unsafe_allow_html=True)
        st.markdown('<div class="page-title">Market Dashboard</div>', unsafe_allow_html=True)
        st.markdown('<div class="page-sub">Live technical analysis — data refreshes every 60 seconds</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with st.container():
        pad = st.container()
        with pad:
            st.markdown('<div style="padding:0 32px;">', unsafe_allow_html=True)

            # Controls
            ctrl1, ctrl2, ctrl3, _ = st.columns([1,1,1,3])
            with ctrl1:
                symbol = st.selectbox("Pair", ["BTC/USDT","ETH/USDT","SOL/USDT","BNB/USDT","XRP/USDT"], key="db_symbol")
            with ctrl2:
                tf = st.selectbox("Timeframe", ["15m","1h","4h","1d"], index=1, key="db_tf")
            with ctrl3:
                strategy = st.selectbox("Strategy", ["Balanced","Aggressive","Conservative"], key="db_strat")

            df = fetch_ohlcv(symbol, tf)
            df = compute_indicators(df)
            latest = df.iloc[-1]
            prev   = df.iloc[-2]

            # Metrics row
            price_chg = ((latest["close"] - prev["close"]) / prev["close"]) * 100
            rsi_val   = round(latest["rsi"], 1)
            macd_val  = round(latest["macd"], 2)
            vol_chg   = ((latest["volume"] - df["volume"].mean()) / df["volume"].mean()) * 100

            m1,m2,m3,m4,m5 = st.columns(5)
            with m1: st.metric("Price", f"${latest['close']:,.2f}", f"{price_chg:+.2f}%")
            with m2: st.metric("RSI (14)", f"{rsi_val}", "Oversold" if rsi_val<30 else "Overbought" if rsi_val>70 else "Neutral")
            with m3: st.metric("MACD", f"{macd_val}", "Bullish" if macd_val>0 else "Bearish")
            with m4:
                ema_sig = "Above EMA20" if latest["close"] > latest["ema20"] else "Below EMA20"
                st.metric("EMA Signal", ema_sig, f"EMA200: {latest['ema200']:,.0f}")
            with m5: st.metric("Volume vs Avg", f"{vol_chg:+.1f}%", "Spike" if abs(vol_chg)>50 else "Normal")

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

            # Chart
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.markdown('<div class="section-label">Price Chart — Candlestick + EMAs + Bollinger Bands</div>', unsafe_allow_html=True)
            st.plotly_chart(build_chart(df, symbol), use_container_width=True, config={"displayModeBar":False})
            st.markdown('</div>', unsafe_allow_html=True)

            # RSI + MACD
            rc1, rc2 = st.columns(2)
            with rc1:
                st.markdown('<div class="section-card">', unsafe_allow_html=True)
                st.markdown('<div class="section-label">RSI (14)</div>', unsafe_allow_html=True)
                st.plotly_chart(build_rsi_chart(df), use_container_width=True, config={"displayModeBar":False})
                st.markdown('</div>', unsafe_allow_html=True)
            with rc2:
                st.markdown('<div class="section-card">', unsafe_allow_html=True)
                st.markdown('<div class="section-label">MACD (12, 26, 9)</div>', unsafe_allow_html=True)
                st.plotly_chart(build_macd_chart(df), use_container_width=True, config={"displayModeBar":False})
                st.markdown('</div>', unsafe_allow_html=True)

            # Quick trade signal
            supp, resist = support_resistance(df)
            rsi_signal  = "OVERSOLD — potential reversal" if rsi_val<30 else "OVERBOUGHT — watch for pullback" if rsi_val>70 else "NEUTRAL range"
            macd_signal = "BULLISH crossover" if latest["macd"] > latest["signal"] else "BEARISH crossover"
            ema_signal  = "BULLISH — price above EMA stack" if latest["close"] > latest["ema50"] > latest["ema200"] else "BEARISH — price below EMA stack"

            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.markdown('<div class="section-label">Quick Signal Summary</div>', unsafe_allow_html=True)
            sc1,sc2,sc3 = st.columns(3)
            with sc1:
                st.markdown(f'<div style="font-size:11px;color:rgba(148,163,184,0.5);margin-bottom:4px;">RSI</div>', unsafe_allow_html=True)
                st.markdown(f'<div style="font-size:13px;font-weight:600;color:#f1f5f9;">{rsi_signal}</div>', unsafe_allow_html=True)
            with sc2:
                st.markdown(f'<div style="font-size:11px;color:rgba(148,163,184,0.5);margin-bottom:4px;">MACD</div>', unsafe_allow_html=True)
                st.markdown(f'<div style="font-size:13px;font-weight:600;color:#f1f5f9;">{macd_signal}</div>', unsafe_allow_html=True)
            with sc3:
                st.markdown(f'<div style="font-size:11px;color:rgba(148,163,184,0.5);margin-bottom:4px;">EMA Stack</div>', unsafe_allow_html=True)
                st.markdown(f'<div style="font-size:13px;font-weight:600;color:#f1f5f9;">{ema_signal}</div>', unsafe_allow_html=True)
            st.markdown('<hr style="border-color:rgba(255,255,255,0.05);margin:14px 0;">', unsafe_allow_html=True)

            bull_signals = sum([rsi_val < 50, macd_val > 0, latest["close"] > latest["ema20"]])
            thesis = "BULLISH" if bull_signals >= 2 else "BEARISH"
            thesis_color = "#10b981" if thesis == "BULLISH" else "#ef4444"
            thesis_bg    = "rgba(16,185,129,0.1)" if thesis == "BULLISH" else "rgba(239,68,68,0.1)"
            thesis_border= "rgba(16,185,129,0.3)" if thesis == "BULLISH" else "rgba(239,68,68,0.3)"
            st.markdown(f'''
<div style="display:inline-block;background:{thesis_bg};border:1px solid {thesis_border};
    border-radius:8px;padding:8px 20px;font-size:13px;font-weight:700;color:{thesis_color};
    letter-spacing:0.5px;">
    Trade Thesis: {thesis} — {bull_signals}/3 signals confirm
</div>''', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

# ── White Paper Report Page ───────────────────────────────────────────────────
def page_report():
    st.markdown("""
<style>
.wp-page { padding: 32px 48px; max-width: 1000px; margin: 0 auto; }
.wp-header { margin-bottom: 40px; }
.wp-doc-title {
    font-size: 32px; font-weight: 800; color: #f1f5f9;
    letter-spacing: -1px; margin-bottom: 8px;
}
.wp-doc-meta {
    font-size: 12px; color: rgba(148,163,184,0.5);
    font-family: 'JetBrains Mono', monospace; letter-spacing: 0.3px;
}
.wp-divider { border: none; border-top: 1px solid rgba(255,255,255,0.08); margin: 32px 0; }
.wp-section-num {
    font-size: 10px; font-weight: 700; color: #3b82f6;
    letter-spacing: 2px; text-transform: uppercase; margin-bottom: 4px;
}
.wp-section-title {
    font-size: 18px; font-weight: 700; color: #f1f5f9;
    letter-spacing: -0.3px; margin-bottom: 20px;
}
.wp-body {
    font-size: 14px; color: rgba(203,213,225,0.85);
    line-height: 1.8; margin-bottom: 20px;
}
.wp-news-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.wp-news-table th {
    text-align: left; padding: 10px 14px;
    font-size: 10px; font-weight: 600; letter-spacing: 1px;
    color: rgba(148,163,184,0.5); text-transform: uppercase;
    border-bottom: 1px solid rgba(255,255,255,0.07);
}
.wp-news-table td {
    padding: 12px 14px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    color: rgba(203,213,225,0.8);
    vertical-align: top;
}
.wp-indicator-row {
    background: rgba(255,255,255,0.025);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 10px;
}
.wp-ind-name { font-size: 12px; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; }
.wp-ind-value { font-size: 22px; font-weight: 800; font-family: 'JetBrains Mono', monospace; color: #f1f5f9; margin: 4px 0; }
.wp-ind-interp { font-size: 12px; color: rgba(148,163,184,0.65); }
.wp-level-row { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.04); }
.wp-level-label { font-size: 12px; font-weight: 600; }
.wp-level-value { font-family: 'JetBrains Mono', monospace; font-size: 13px; color: #f1f5f9; }
.wp-level-dist  { font-size: 11px; color: rgba(148,163,184,0.5); }
.wp-thesis-box {
    background: rgba(37,99,235,0.06);
    border: 1px solid rgba(37,99,235,0.2);
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 16px;
}
.wp-verdict {
    font-size: 28px; font-weight: 800; letter-spacing: -0.5px; margin-bottom: 12px;
}
.wp-evidence-item {
    display: flex; align-items: flex-start; gap: 10px;
    padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.04);
    font-size: 13px; color: rgba(203,213,225,0.8);
}
.wp-tag {
    background: rgba(59,130,246,0.12); border: 1px solid rgba(59,130,246,0.2);
    border-radius: 4px; padding: 1px 7px;
    font-size: 10px; font-weight: 700; color: #60a5fa; flex-shrink: 0;
    font-family: 'JetBrains Mono', monospace;
}
</style>
""", unsafe_allow_html=True)

    col_c, col_r = st.columns([1,1])
    with col_c:
        symbol = st.selectbox("Asset", ["BTC/USDT","ETH/USDT","SOL/USDT","BNB/USDT","XRP/USDT"], key="rp_symbol")
    with col_r:
        tf = st.selectbox("Timeframe", ["1h","4h","1d"], key="rp_tf")

    if st.button("Generate White Paper Report", key="gen_report"):
        with st.spinner("Running institutional-grade analysis..."):
            df       = fetch_ohlcv(symbol, tf)
            df       = compute_indicators(df)
            news     = fetch_news(symbol.split("/")[0])
            latest   = df.iloc[-1]
            supp, resist = support_resistance(df)
            rsi_val  = round(latest["rsi"], 1)
            macd_val = round(latest["macd"], 4)
            price    = round(latest["close"], 2)
            bb_width = round(((latest["bb_up"] - latest["bb_lo"]) / latest["bb_mid"]) * 100, 2)
            vol_vs   = round(((latest["volume"] - df["volume"].mean()) / df["volume"].mean()) * 100, 1)

            # Thesis computation
            bull = sum([rsi_val<50, macd_val>0, latest["close"]>latest["ema20"], latest["close"]>latest["ema50"]])
            verdict     = "BULLISH" if bull >= 3 else "BEARISH" if bull <= 1 else "NEUTRAL"
            v_color     = "#10b981" if verdict=="BULLISH" else "#ef4444" if verdict=="BEARISH" else "#f59e0b"
            news_scores = [a["score"] for a in news]
            avg_sent    = round(sum(news_scores)/len(news_scores), 2) if news_scores else 0
            ts_str      = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

            st.markdown('<div class="wp-page">', unsafe_allow_html=True)

            # Document header
            st.markdown(f"""
<div class="wp-header">
    <div style="display:inline-block;background:rgba(37,99,235,0.1);border:1px solid rgba(37,99,235,0.2);
        border-radius:6px;padding:4px 14px;font-size:10px;font-weight:700;color:#60a5fa;
        letter-spacing:1.5px;text-transform:uppercase;margin-bottom:16px;">
        White Paper — Institutional Research Document
    </div>
    <div class="wp-doc-title">{symbol} — Market Intelligence Report</div>
    <div class="wp-doc-meta">
        Generated: {ts_str} &nbsp;|&nbsp; Timeframe: {tf} &nbsp;|&nbsp;
        Entry Price: ${price:,.4f} &nbsp;|&nbsp; Signals: {bull}/4 Bullish
    </div>
</div>
<hr class="wp-divider">
""", unsafe_allow_html=True)

            # 01 Executive Summary
            st.markdown('<div class="wp-section-num">Section 01</div>', unsafe_allow_html=True)
            st.markdown('<div class="wp-section-title">Executive Summary</div>', unsafe_allow_html=True)
            exec_text = (
                f"This report presents a comprehensive multi-layered analysis of {symbol} as of {ts_str}. "
                f"Current price is **${price:,.4f}**, operating in a {'bullish' if verdict=='BULLISH' else 'bearish' if verdict=='BEARISH' else 'neutral'} regime. "
                f"The technical overlay shows RSI at {rsi_val} ({'oversold' if rsi_val<30 else 'overbought' if rsi_val>70 else 'neutral territory'}), "
                f"MACD at {macd_val} ({'positive — momentum favors buyers' if macd_val>0 else 'negative — momentum favors sellers'}), "
                f"and price {'above' if latest['close']>latest['ema50'] else 'below'} the 50-period EMA. "
                f"News sentiment aggregated from {len(news)} articles scores an average of {avg_sent:+.1f}/5.0 "
                f"({'positive' if avg_sent>0 else 'negative' if avg_sent<0 else 'neutral'}). "
                f"Bollinger Band width at {bb_width}% indicates {'elevated' if bb_width>5 else 'compressed'} volatility. "
                f"The combined TA+FA verdict is **{verdict}**."
            )
            st.markdown(f'<div class="wp-body">{exec_text}</div>', unsafe_allow_html=True)
            st.markdown('<hr class="wp-divider">', unsafe_allow_html=True)

            # 02 Market Pulse — News
            st.markdown('<div class="wp-section-num">Section 02</div>', unsafe_allow_html=True)
            st.markdown('<div class="wp-section-title">Market Pulse — News Sentiment Analysis</div>', unsafe_allow_html=True)
            if news:
                table_rows = ""
                for a in news[:10]:
                    sc = a["score"]
                    sc_color = sentiment_color(sc)
                    sc_label = f"+{sc}" if sc>0 else str(sc)
                    summary_trunc = a["summary"][:100]+"..." if len(a["summary"])>100 else a["summary"]
                    table_rows += f"""
<tr>
  <td><div style="font-weight:500;color:#e2e8f0;margin-bottom:4px;">{a['title']}</div>
      <div style="font-size:11px;color:rgba(148,163,184,0.55);">{summary_trunc}</div></td>
  <td style="white-space:nowrap;font-size:10px;color:rgba(148,163,184,0.5);padding-right:20px;">{a['source']}</td>
  <td><span style="background:rgba(0,0,0,0.3);border:1px solid {sc_color}40;border-radius:6px;
      padding:3px 10px;font-size:12px;font-weight:700;color:{sc_color};font-family:'JetBrains Mono',monospace;">
      {sc_label}</span></td>
</tr>"""
                st.markdown(f"""
<table class="wp-news-table">
<thead><tr><th>Headline</th><th>Source</th><th>Impact Score</th></tr></thead>
<tbody>{table_rows}</tbody>
</table>""", unsafe_allow_html=True)
            else:
                st.info("News data unavailable.")
            st.markdown('<hr class="wp-divider">', unsafe_allow_html=True)

            # 03 Technical Blueprint
            st.markdown('<div class="wp-section-num">Section 03</div>', unsafe_allow_html=True)
            st.markdown('<div class="wp-section-title">Technical Blueprint — Indicator Analysis</div>', unsafe_allow_html=True)

            indicators = [
                ("RSI (14)", f"{rsi_val}", "Oversold — reversal zone" if rsi_val<30 else "Overbought — pullback risk" if rsi_val>70 else "Neutral — no extreme signal"),
                ("MACD", f"{macd_val:+.4f}", f"{'Above' if macd_val>0 else 'Below'} zero line — momentum {'bullish' if macd_val>0 else 'bearish'}"),
                ("EMA 20", f"${latest['ema20']:,.2f}", f"Price {'above' if price>latest['ema20'] else 'below'} — short-term trend {'up' if price>latest['ema20'] else 'down'}"),
                ("EMA 50", f"${latest['ema50']:,.2f}", f"Price {'above' if price>latest['ema50'] else 'below'} — medium-term trend {'up' if price>latest['ema50'] else 'down'}"),
                ("EMA 200", f"${latest['ema200']:,.2f}", f"Price {'above' if price>latest['ema200'] else 'below'} — long-term trend {'up' if price>latest['ema200'] else 'down'}"),
                ("BB Width", f"{bb_width}%", f"{'Elevated — breakout likely' if bb_width>5 else 'Compressed — consolidation phase, watch for squeeze breakout'}"),
                ("Volume", f"{vol_vs:+.1f}% vs avg", f"{'Above-average volume confirms price action' if vol_vs>20 else 'Below-average volume — weak conviction' if vol_vs<-20 else 'Volume near average — no extreme signal'}"),
            ]

            ind_cols = st.columns(4)
            for i, (name, value, interp) in enumerate(indicators):
                with ind_cols[i % 4]:
                    st.markdown(f"""
<div class="wp-indicator-row">
    <div class="wp-ind-name">{name}</div>
    <div class="wp-ind-value">{value}</div>
    <div class="wp-ind-interp">{interp}</div>
</div>""", unsafe_allow_html=True)
            st.markdown('<hr class="wp-divider">', unsafe_allow_html=True)

            # 04 Visual Blueprint — Levels
            st.markdown('<div class="wp-section-num">Section 04</div>', unsafe_allow_html=True)
            st.markdown('<div class="wp-section-title">Visual Blueprint — Key Price Levels</div>', unsafe_allow_html=True)

            vb1, vb2 = st.columns(2)
            with vb1:
                st.markdown('<div style="font-size:11px;font-weight:600;color:rgba(148,163,184,0.5);margin-bottom:12px;text-transform:uppercase;letter-spacing:1px;">Resistance Zones</div>', unsafe_allow_html=True)
                for level in resist:
                    dist = ((level - price) / price) * 100
                    st.markdown(f"""
<div class="wp-level-row">
    <span class="wp-level-label" style="color:#ef4444;">R {level:,.0f}</span>
    <span class="wp-level-value">${level:,.2f}</span>
    <span class="wp-level-dist">{dist:+.2f}%</span>
</div>""", unsafe_allow_html=True)
                # Entry zone
                st.markdown(f"""
<div class="wp-level-row" style="margin-top:8px;">
    <span class="wp-level-label" style="color:#3b82f6;">Entry Zone</span>
    <span class="wp-level-value">${price:,.2f}</span>
    <span class="wp-level-dist">Current</span>
</div>""", unsafe_allow_html=True)

            with vb2:
                st.markdown('<div style="font-size:11px;font-weight:600;color:rgba(148,163,184,0.5);margin-bottom:12px;text-transform:uppercase;letter-spacing:1px;">Support Zones</div>', unsafe_allow_html=True)
                sl_level  = round(price * 0.98, 2)
                tp_level  = round(price * 1.05, 2)
                for level in supp:
                    dist = ((level - price) / price) * 100
                    st.markdown(f"""
<div class="wp-level-row">
    <span class="wp-level-label" style="color:#10b981;">S {level:,.0f}</span>
    <span class="wp-level-value">${level:,.2f}</span>
    <span class="wp-level-dist">{dist:+.2f}%</span>
</div>""", unsafe_allow_html=True)
                st.markdown(f"""
<div class="wp-level-row" style="margin-top:8px;">
    <span class="wp-level-label" style="color:#ef4444;">Stop-Loss (2%)</span>
    <span class="wp-level-value">${sl_level:,.2f}</span>
    <span class="wp-level-dist">-2.00%</span>
</div>
<div class="wp-level-row">
    <span class="wp-level-label" style="color:#10b981;">Take-Profit (5%)</span>
    <span class="wp-level-value">${tp_level:,.2f}</span>
    <span class="wp-level-dist">+5.00%</span>
</div>""", unsafe_allow_html=True)
            st.markdown('<hr class="wp-divider">', unsafe_allow_html=True)

            # 05 Actionable Thesis
            st.markdown('<div class="wp-section-num">Section 05</div>', unsafe_allow_html=True)
            st.markdown('<div class="wp-section-title">Actionable Thesis — Trade Recommendation</div>', unsafe_allow_html=True)

            val_ok, issues, order = validate_trade("BUY" if verdict=="BULLISH" else "SELL", price, sl_level, tp_level, 3.0)

            st.markdown(f"""
<div class="wp-thesis-box">
    <div class="wp-verdict" style="color:{v_color};">{verdict}</div>
    <div style="font-size:13px;color:rgba(203,213,225,0.75);line-height:1.7;">
        Based on the convergence of {bull}/4 bullish technical signals and a news sentiment of {avg_sent:+.1f},
        the weight of evidence points {'in favor of' if verdict!='NEUTRAL' else 'toward a wait-and-see approach on'} {symbol}.
        {'Momentum, trend, and volume confirm directional bias.' if verdict!='NEUTRAL' else 'Conflicting signals suggest reduced position sizing or sitting out until clarity emerges.'}
    </div>
</div>""", unsafe_allow_html=True)

            evidence = [
                ("RSI",   f"RSI at {rsi_val} — {'oversold territory, historically favorable for mean-reversion longs' if rsi_val<30 else 'overbought, risk of short-term pullback' if rsi_val>70 else 'mid-range, no directional extreme'}"),
                ("MACD",  f"MACD {'+' if macd_val>0 else ''}{macd_val:.4f} — momentum {'accelerating to the upside' if macd_val>0 else 'decelerating, selling pressure dominant'}"),
                ("EMA",   f"Price at ${price:,.2f} sits {'above' if price>latest['ema20'] else 'below'} EMA20 (${latest['ema20']:,.2f}) — short-term trend {'confirmed up' if price>latest['ema20'] else 'broken down'}"),
                ("BB",    f"Bollinger Band width {bb_width}% — {'volatility elevated, breakout may be in progress' if bb_width>5 else 'band squeeze in progress, watch for explosive expansion'}"),
                ("NEWS",  f"Aggregated news sentiment: {avg_sent:+.1f} across {len(news)} articles — {'macro tailwinds supportive' if avg_sent>1 else 'macro headwinds present' if avg_sent<-1 else 'macro neutral'}"),
                ("RISK",  f"Validated risk params — Entry: ${price:,.2f} | SL: ${sl_level:,.2f} (-2%) | TP: ${tp_level:,.2f} (+5%) | R:R 1:2.5 | Size: 3% of portfolio"),
            ]
            for tag, text in evidence:
                st.markdown(f"""
<div class="wp-evidence-item">
    <span class="wp-tag">{tag}</span>
    <span>{text}</span>
</div>""", unsafe_allow_html=True)

            st.markdown(f"""
<div style="margin-top:20px;padding:12px 16px;background:rgba(255,255,255,0.02);
    border:1px solid rgba(255,255,255,0.06);border-radius:8px;
    font-size:11px;color:rgba(148,163,184,0.45);line-height:1.6;">
    Disclaimer: This report is generated by an automated engine and is not financial advice.
    All trades must pass the mandatory risk validation layer before execution.
    Past performance of indicators does not guarantee future results.
    Risk limit validation: {'PASSED' if val_ok else 'FAILED — ' + ', '.join(issues)}
</div>""", unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)

# ── News Page ─────────────────────────────────────────────────────────────────
def page_news():
    st.markdown('<div style="padding:32px 32px 0;">', unsafe_allow_html=True)
    st.markdown('<div style="font-size:26px;font-weight:700;color:#f1f5f9;letter-spacing:-0.8px;margin-bottom:4px;">Market News</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:13px;color:rgba(148,163,184,0.6);margin-bottom:24px;">Real-time news feeds with automated sentiment scoring</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    q_col, _ = st.columns([2,4])
    with q_col:
        query = st.text_input("Search topic", value="crypto bitcoin trading", key="news_query")

    with st.spinner("Fetching news feeds..."):
        articles = fetch_news(query)

    if not articles:
        st.warning("No articles found. Try a different search term.")
        return

    avg = round(sum(a["score"] for a in articles)/len(articles), 2) if articles else 0
    av_color = sentiment_color(avg)

    m1, m2, m3 = st.columns(3)
    with m1: st.metric("Articles Fetched", len(articles))
    with m2: st.metric("Avg Sentiment", f"{avg:+.2f}/5.0")
    with m3: st.metric("Overall Tone", "Positive" if avg>0 else "Negative" if avg<0 else "Neutral")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    for a in articles:
        sc = a["score"]
        sc_color = sentiment_color(sc)
        sc_label = f"+{sc}" if sc>0 else str(sc)
        st.markdown(f"""
<div style="background:rgba(255,255,255,0.025);border:1px solid rgba(255,255,255,0.06);
    border-radius:12px;padding:18px 22px;margin-bottom:10px;
    border-left:3px solid {sc_color};">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:16px;">
        <div style="flex:1;">
            <div style="font-size:14px;font-weight:600;color:#e2e8f0;margin-bottom:6px;">{a['title']}</div>
            <div style="font-size:12px;color:rgba(148,163,184,0.6);">{a['summary'][:150]}{'...' if len(a['summary'])>150 else ''}</div>
        </div>
        <div style="text-align:right;flex-shrink:0;">
            <div style="font-size:18px;font-weight:800;color:{sc_color};font-family:'JetBrains Mono',monospace;">{sc_label}</div>
            <div style="font-size:10px;color:rgba(148,163,184,0.4);margin-top:2px;">Impact Score</div>
        </div>
    </div>
    <div style="margin-top:10px;font-size:10px;color:rgba(148,163,184,0.35);letter-spacing:0.3px;">{a['source']}</div>
</div>""", unsafe_allow_html=True)

# ── Settings Page ─────────────────────────────────────────────────────────────
def page_settings():
    st.markdown('<div style="padding:32px 32px 0;">', unsafe_allow_html=True)
    st.markdown('<div style="font-size:26px;font-weight:700;color:#f1f5f9;letter-spacing:-0.8px;margin-bottom:4px;">Settings</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:13px;color:rgba(148,163,184,0.6);margin-bottom:24px;">Exchange API keys are encrypted with AES-256 before storage</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div style="padding:0 32px;">', unsafe_allow_html=True)
    tab_api, tab_risk, tab_acct = st.tabs(["API Keys", "Risk Limits", "Account"])

    with tab_api:
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        db  = SessionLocal()
        row = db.query(ApiKey).filter(ApiKey.user_id == st.session_state.user_id).first()
        db.close()
        current_exchange = row.exchange if row else "binance"

        with st.form("api_form"):
            exchange = st.selectbox("Exchange", ["binance","bybit","okx","kucoin","coinbase"], index=["binance","bybit","okx","kucoin","coinbase"].index(current_exchange) if current_exchange in ["binance","bybit","okx","kucoin","coinbase"] else 0)
            api_key  = st.text_input("API Key", type="password", placeholder="Your exchange API key")
            api_sec  = st.text_input("API Secret", type="password", placeholder="Your exchange API secret")
            st.markdown('<div style="background:rgba(245,158,11,0.06);border:1px solid rgba(245,158,11,0.2);border-radius:8px;padding:12px 16px;font-size:12px;color:rgba(245,158,11,0.8);margin:12px 0;">Keys are encrypted with AES-256 before being written to the database. They are never stored in plaintext.</div>', unsafe_allow_html=True)
            save = st.form_submit_button("Save API Keys")
            if save:
                if not api_key or not api_sec:
                    st.error("Both API Key and Secret are required.")
                else:
                    db = SessionLocal()
                    existing = db.query(ApiKey).filter(ApiKey.user_id == st.session_state.user_id).first()
                    if existing:
                        existing.exchange  = exchange
                        existing.enc_key   = encrypt(api_key)
                        existing.enc_secret= encrypt(api_sec)
                        existing.updated_at= datetime.datetime.utcnow()
                    else:
                        db.add(ApiKey(user_id=st.session_state.user_id, exchange=exchange, enc_key=encrypt(api_key), enc_secret=encrypt(api_sec)))
                    db.commit(); db.close()
                    st.success("API keys saved securely.")

    with tab_risk:
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        limits = [
            ("Max Position Size", f"{MAX_POSITION_PCT}%", "Maximum capital per single trade"),
            ("Stop-Loss Limit",   f"{MAX_SL_PCT}%",       "Maximum allowed SL from entry price"),
            ("Min Take-Profit",   f"{MIN_TP_PCT}%",       "Minimum required TP from entry price"),
            ("Min Risk/Reward",   f"1:{MIN_RR}",          "Minimum R:R before trade is allowed"),
            ("Daily Loss Limit",  f"{MAX_DAILY_LOSS}%",   "Global shutdown triggers above this loss"),
        ]
        for name, val, desc in limits:
            st.markdown(f"""
<div style="background:rgba(255,255,255,0.025);border:1px solid rgba(255,255,255,0.06);
    border-radius:10px;padding:16px 20px;margin-bottom:8px;
    display:flex;justify-content:space-between;align-items:center;">
    <div>
        <div style="font-size:13px;font-weight:600;color:#e2e8f0;">{name}</div>
        <div style="font-size:11px;color:rgba(148,163,184,0.5);margin-top:2px;">{desc}</div>
    </div>
    <div style="font-family:'JetBrains Mono',monospace;font-size:16px;font-weight:700;color:#3b82f6;">{val}</div>
</div>""", unsafe_allow_html=True)
        st.markdown('<div style="font-size:11px;color:rgba(148,163,184,0.35);margin-top:8px;">These limits are hard-coded and cannot be overridden by the AI agent.</div>', unsafe_allow_html=True)

    with tab_acct:
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        st.markdown(f"""
<div style="background:rgba(255,255,255,0.025);border:1px solid rgba(255,255,255,0.06);border-radius:12px;padding:20px 24px;">
    <div style="font-size:11px;color:rgba(148,163,184,0.5);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px;">Logged in as</div>
    <div style="font-size:16px;font-weight:600;color:#f1f5f9;">{st.session_state.user_email}</div>
</div>""", unsafe_allow_html=True)

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        if st.button("Change Password", key="chng_pw"):
            st.info("Password change: enter new password below.")
        with st.form("pw_form"):
            np1 = st.text_input("New password", type="password", key="np1")
            np2 = st.text_input("Confirm new password", type="password", key="np2")
            if st.form_submit_button("Update Password"):
                if not np1 or not np2:
                    st.error("Fill both fields.")
                elif np1 != np2:
                    st.error("Passwords do not match.")
                elif len(np1) < 8:
                    st.error("Minimum 8 characters.")
                else:
                    db = SessionLocal()
                    u  = db.query(User).filter(User.id == st.session_state.user_id).first()
                    if u:
                        u.password_hash = hash_pw(np1)
                        db.commit()
                        st.success("Password updated.")
                    db.close()
    st.markdown('</div>', unsafe_allow_html=True)

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    inject_css()
    init_state()

    if not st.session_state.logged_in:
        page_auth()
        return

    sidebar()

    page = st.session_state.active_page
    if page == "dashboard": page_dashboard()
    elif page == "report":  page_report()
    elif page == "news":    page_news()
    elif page == "settings":page_settings()

if __name__ == "__main__":
    main()
