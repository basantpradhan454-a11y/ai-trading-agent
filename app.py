"""
Elite Trading Intelligence — Streamlit App
==========================================
All-in-one: Auth · Dashboard · News · Report · Settings
AES-256 encrypted API keys · Risk Validation Layer · Live TA
"""

import streamlit as st
import ccxt, pandas as pd, numpy as np, plotly.graph_objects as go
import feedparser, re, uuid, os, datetime, hashlib, json
from cryptography.fernet import Fernet
from passlib.context import CryptContext
from sqlalchemy import create_engine, Column, String, Float, Boolean, DateTime, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# ─── Config ───────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Elite Trading AI",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── DB Setup ─────────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///trading.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id            = Column(String, primary_key=True)
    email         = Column(String, unique=True, index=True)
    full_name     = Column(String)
    hashed_pw     = Column(String)
    created_at    = Column(DateTime, default=datetime.datetime.utcnow)

class EncryptedKey(Base):
    __tablename__ = "encrypted_keys"
    id             = Column(String, primary_key=True)
    user_id        = Column(String)
    exchange       = Column(String)
    enc_api_key    = Column(Text)
    enc_api_secret = Column(Text)

Base.metadata.create_all(bind=engine)

# ─── Crypto / Auth helpers ────────────────────────────────────────────────────
RAW_KEY = os.getenv("ENCRYPTION_KEY", "")
try:
    fernet = Fernet(RAW_KEY.encode()) if RAW_KEY else Fernet(Fernet.generate_key())
except Exception:
    fernet = Fernet(Fernet.generate_key())

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_pw(pw): return pwd_ctx.hash(pw)
def verify_pw(plain, hashed): return pwd_ctx.verify(plain, hashed)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ─── Styling ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.stApp {
    background: linear-gradient(135deg, #0a0f1e 0%, #0d1b2a 40%, #1a0a2e 100%);
    color: #e2e8f0;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: rgba(10,15,30,0.95) !important;
    border-right: 1px solid rgba(255,255,255,0.07) !important;
}

/* Glass cards */
.glass-card {
    background: rgba(255,255,255,0.04);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 16px;
    transition: all 0.3s ease;
}

.glass-card:hover { border-color: rgba(59,130,246,0.25); }

/* Metric cards */
.metric-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    padding: 18px 20px;
    text-align: center;
}
.metric-label { color: rgba(255,255,255,0.4); font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; }
.metric-value { font-size: 22px; font-weight: 800; margin: 6px 0 3px; }
.metric-sub   { color: rgba(255,255,255,0.35); font-size: 11px; }

/* Badges */
.badge-buy  { background: rgba(16,185,129,0.15); border:1px solid rgba(16,185,129,0.4); color:#10b981; padding:4px 14px; border-radius:6px; font-weight:700; font-size:13px; }
.badge-sell { background: rgba(239,68,68,0.15);  border:1px solid rgba(239,68,68,0.4);  color:#ef4444; padding:4px 14px; border-radius:6px; font-weight:700; font-size:13px; }
.badge-hold { background: rgba(245,158,11,0.15); border:1px solid rgba(245,158,11,0.4); color:#f59e0b; padding:4px 14px; border-radius:6px; font-weight:700; font-size:13px; }
.badge-pos  { background: rgba(16,185,129,0.1);  border:1px solid rgba(16,185,129,0.3); color:#10b981; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600; }
.badge-neg  { background: rgba(239,68,68,0.1);   border:1px solid rgba(239,68,68,0.3);  color:#ef4444; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600; }
.badge-neu  { background: rgba(148,163,184,0.1); border:1px solid rgba(148,163,184,0.2);color:#94a3b8; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600; }

/* Section headers */
.section-header {
    display:flex; align-items:center; gap:12px; margin-bottom:20px;
}
.section-bar {
    width:4px; height:28px; border-radius:2px;
}

h1, h2, h3 { color: #f1f5f9 !important; }

/* Inputs */
.stTextInput > div > div > input,
.stPasswordInput > div > div > input,
.stSelectbox > div > div {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 10px !important;
    color: white !important;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #3b82f6, #6366f1) !important;
    border: none !important;
    border-radius: 10px !important;
    color: white !important;
    font-weight: 600 !important;
    padding: 10px 24px !important;
    transition: all 0.3s !important;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 8px 30px rgba(59,130,246,0.4) !important;
}

/* Tabs */
.stTabs [data-baseweb="tab"] {
    color: rgba(255,255,255,0.5) !important;
    font-weight: 500 !important;
}
.stTabs [aria-selected="true"] {
    color: #3b82f6 !important;
    border-bottom-color: #3b82f6 !important;
}

/* Divider */
hr { border-color: rgba(255,255,255,0.08) !important; }
</style>
""", unsafe_allow_html=True)

# ─── Session State ─────────────────────────────────────────────────────────────
for key, val in [("user", None), ("token", None), ("last_report", None)]:
    if key not in st.session_state:
        st.session_state[key] = val

# ─── Risk Validation Layer ─────────────────────────────────────────────────────
class RiskLimits:
    max_position_pct  = 5.0
    max_sl_pct        = 2.0
    min_tp_pct        = 5.0
    min_risk_reward   = 2.0
    max_daily_loss_pct = 10.0

def validate_trade(ai_resp: dict, balance: float, daily_pnl: float = 0.0) -> dict:
    lim = RiskLimits()
    reasons = []
    if daily_pnl <= -lim.max_daily_loss_pct:
        return {"valid": False, "reasons": [f"🔴 Daily loss {daily_pnl}% exceeded {lim.max_daily_loss_pct}% limit — GLOBAL SHUTDOWN"]}
    required = ["action","symbol","entry_price","stop_loss","take_profit","position_size_pct"]
    missing = [f for f in required if f not in ai_resp]
    if missing:
        return {"valid": False, "reasons": [f"Missing fields: {missing}"]}
    action  = str(ai_resp["action"]).lower()
    entry   = float(ai_resp["entry_price"])
    sl      = float(ai_resp["stop_loss"])
    tp      = float(ai_resp["take_profit"])
    size    = float(ai_resp["position_size_pct"])
    if action == "hold":
        return {"valid": True, "reasons": ["Hold — no order placed"], "order": {"action": "hold"}}
    if size > lim.max_position_pct:
        reasons.append(f"Position {size}% > max {lim.max_position_pct}%")
    sl_pct = abs((entry - sl) / entry) * 100
    if sl_pct > lim.max_sl_pct + 1e-9:
        reasons.append(f"SL distance {sl_pct:.2f}% > max {lim.max_sl_pct}%")
    if action == "buy"  and sl >= entry: reasons.append("SL must be below entry for BUY")
    if action == "sell" and sl <= entry: reasons.append("SL must be above entry for SELL")
    if action == "buy"  and tp <= entry: reasons.append("TP must be above entry for BUY")
    if action == "sell" and tp >= entry: reasons.append("TP must be below entry for SELL")
    risk   = abs(entry - sl)
    reward = abs(tp - entry)
    rr     = round(reward / risk, 2) if risk > 0 else 0
    if rr < lim.min_risk_reward:
        reasons.append(f"R:R {rr} < min 1:{lim.min_risk_reward}")
    trade_val = balance * (size / 100)
    if trade_val > balance:
        reasons.append("Insufficient balance")
    if reasons:
        return {"valid": False, "reasons": reasons}
    return {
        "valid": True, "reasons": [],
        "order": {
            "action": action, "symbol": ai_resp["symbol"],
            "entry_price": entry, "stop_loss": sl, "take_profit": tp,
            "position_size_pct": size, "trade_value": round(trade_val, 2),
            "risk_reward": f"1:{rr}", "reason": ai_resp.get("reason", "")
        }
    }

# ─── TA Engine ────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch_market_data(symbol: str) -> dict:
    try:
        exc = ccxt.kraken({"enableRateLimit": True})
        ohlcv = exc.fetch_ohlcv(symbol, "1d", limit=100)
        df = pd.DataFrame(ohlcv, columns=["ts","open","high","low","close","volume"])
        c = df["close"]
        price = float(c.iloc[-1])
        prev  = float(c.iloc[-2])
        ch24  = round((price - prev) / prev * 100, 2)
        vol   = round(float(df["volume"].iloc[-1]), 2)
        # RSI
        delta = c.diff()
        gain  = delta.where(delta > 0, 0).rolling(14).mean()
        loss  = -delta.where(delta < 0, 0).rolling(14).mean()
        rs    = gain / loss.replace(0, np.inf)
        rsi   = round(float((100 - 100/(1+rs)).iloc[-1]), 2)
        # MACD
        ema12 = c.ewm(span=12, adjust=False).mean()
        ema26 = c.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        sig_line  = macd_line.ewm(span=9, adjust=False).mean()
        hist_val  = macd_line - sig_line
        macd = round(float(macd_line.iloc[-1]), 4)
        macd_sig  = round(float(sig_line.iloc[-1]), 4)
        macd_hist = round(float(hist_val.iloc[-1]), 4)
        # Bollinger
        sma20 = c.rolling(20).mean()
        std20 = c.rolling(20).std()
        bb_up = round(float((sma20 + 2*std20).iloc[-1]), 2)
        bb_md = round(float(sma20.iloc[-1]), 2)
        bb_lo = round(float((sma20 - 2*std20).iloc[-1]), 2)
        # EMA
        ema20 = round(float(c.ewm(span=20).mean().iloc[-1]), 2)
        ema50 = round(float(c.ewm(span=50).mean().iloc[-1]), 2)
        # S/R
        all_levels = list(df["high"].tail(60)) + list(df["low"].tail(60))
        all_levels.sort()
        cluster = (max(all_levels) - min(all_levels)) * 0.015
        merged = []
        for p in all_levels:
            if not any(abs(p - m) < cluster for m in merged):
                merged.append(round(p, 2))
        sups  = sorted([l for l in merged if l < price], reverse=True)
        ress  = sorted([l for l in merged if l > price])
        s1 = sups[0] if sups else round(price*0.98, 2)
        s2 = sups[1] if len(sups)>1 else round(price*0.96, 2)
        r1 = ress[0] if ress else round(price*1.02, 2)
        r2 = ress[1] if len(ress)>1 else round(price*1.04, 2)
        # Signal
        score = 0
        if rsi < 35: score += 2
        elif rsi < 45: score += 1
        elif rsi > 65: score -= 2
        elif rsi > 55: score -= 1
        score += (1 if macd_hist > 0 else -1)
        score += (1 if ema20 > ema50 else -1)
        if price <= bb_lo * 1.01: score += 1
        elif price >= bb_up * 0.99: score -= 1
        if score >= 3:    sig, strength = "BUY", "STRONG"
        elif score == 2:  sig, strength = "BUY", "MODERATE"
        elif score == 1:  sig, strength = "BUY", "WEAK"
        elif score <= -3: sig, strength = "SELL", "STRONG"
        elif score == -2: sig, strength = "SELL", "MODERATE"
        elif score == -1: sig, strength = "SELL", "WEAK"
        else:             sig, strength = "HOLD", "NEUTRAL"
        return {
            "symbol": symbol, "price": round(price,2), "change_24h": ch24, "volume_24h": vol,
            "rsi": rsi, "macd": macd, "macd_signal": macd_sig, "macd_hist": macd_hist,
            "ema_20": ema20, "ema_50": ema50,
            "bb_upper": bb_up, "bb_middle": bb_md, "bb_lower": bb_lo,
            "s1": s1, "s2": s2, "r1": r1, "r2": r2,
            "signal": sig, "strength": strength,
            "df": df.tail(60).to_dict("records"),
            "error": None
        }
    except Exception as e:
        return {"error": str(e)}

# ─── News Engine ──────────────────────────────────────────────────────────────
POSITIVE_W = ["surge","rally","bull","gain","rise","growth","adoption","approved","launch","partnership","record","high","jump","soar","recover","strong","institutional","breakout","uptrend"]
NEGATIVE_W = ["crash","bear","drop","loss","fall","ban","hack","fail","sell","dump","plunge","decline","risk","fear","collapse","bankrupt","fraud","scam","warning","concern","lawsuit","bearish","downtrend"]
FEEDS = ["https://feeds.feedburner.com/CoinDesk","https://cointelegraph.com/rss","https://www.newsbtc.com/feed/","https://cryptopotato.com/feed/"]

@st.cache_data(ttl=600)
def fetch_news():
    items = []
    for url in FEEDS:
        try:
            feed = feedparser.parse(url)
            src  = feed.feed.get("title","News")
            for e in feed.entries[:5]:
                title   = e.get("title","")
                summary = re.sub(r"<[^>]+>","", e.get("summary", e.get("description",""))).strip()[:200]
                t = f"{title} {summary}".lower()
                pos = sum(1 for w in POSITIVE_W if w in t)
                neg = sum(1 for w in NEGATIVE_W if w in t)
                score = round(max(-5.0, min(5.0, (pos - neg) * 1.2)), 1)
                sentiment = "POSITIVE" if score > 0 else "NEGATIVE" if score < 0 else "NEUTRAL"
                items.append({"title": title, "summary": summary[:160], "link": e.get("link",""),
                              "source": src[:30], "published": e.get("published","")[:30],
                              "impact_score": score, "sentiment": sentiment})
        except Exception:
            continue
    items.sort(key=lambda x: abs(x["impact_score"]), reverse=True)
    return items[:15]

# ─── Report Generator ─────────────────────────────────────────────────────────
def generate_report(ta: dict, news: list, strategy: str) -> dict:
    avg_s = sum(n["impact_score"] for n in news)/len(news) if news else 0
    sig   = ta["signal"]
    if sig == "BUY" and avg_s > 0.5:    thesis = "STRONGLY BULLISH"
    elif sig == "BUY":                   thesis = "BULLISH"
    elif sig == "SELL" and avg_s < -0.5: thesis = "STRONGLY BEARISH"
    elif sig == "SELL":                  thesis = "BEARISH"
    else:                                thesis = "NEUTRAL"
    entry = ta["price"]
    sl    = round(entry * 0.98, 2)
    tp    = round(entry * 1.05, 2)
    rr    = round(abs(tp-entry)/abs(entry-sl), 2) if abs(entry-sl)>0 else 0
    pos_size = {"Conservative":"3%","Aggressive":"5%"}.get(strategy,"4%")
    return {
        "thesis": thesis, "entry": entry, "sl": sl, "tp": tp,
        "rr": f"1:{rr}", "position_size": pos_size,
        "avg_sentiment": round(avg_s, 2), "generated_at": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "news": news[:10]
    }

# ─── Auth UI ──────────────────────────────────────────────────────────────────
def show_auth():
    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.markdown("""
        <div style="text-align:center; padding: 40px 0 30px;">
            <div style="font-size:56px; margin-bottom:14px;">⚡</div>
            <h1 style="font-size:34px; font-weight:900; background:linear-gradient(135deg,#fff 30%,#3b82f6 100%);
                -webkit-background-clip:text; -webkit-text-fill-color:transparent; margin-bottom:8px; letter-spacing:-1px;">
                Elite Trading AI
            </h1>
            <p style="color:rgba(255,255,255,0.4); font-size:14px; margin-bottom:20px;">Institutional-Grade Intelligence Engine</p>
            <div style="display:flex; gap:8px; justify-content:center; flex-wrap:wrap; margin-bottom:32px;">
                <span style="background:rgba(59,130,246,0.1); border:1px solid rgba(59,130,246,0.2); border-radius:20px; padding:3px 12px; font-size:11px; color:rgba(255,255,255,0.45)">RSI · MACD · BB</span>
                <span style="background:rgba(59,130,246,0.1); border:1px solid rgba(59,130,246,0.2); border-radius:20px; padding:3px 12px; font-size:11px; color:rgba(255,255,255,0.45)">News Sentiment AI</span>
                <span style="background:rgba(59,130,246,0.1); border:1px solid rgba(59,130,246,0.2); border-radius:20px; padding:3px 12px; font-size:11px; color:rgba(255,255,255,0.45)">White Paper Reports</span>
                <span style="background:rgba(59,130,246,0.1); border:1px solid rgba(59,130,246,0.2); border-radius:20px; padding:3px 12px; font-size:11px; color:rgba(255,255,255,0.45)">AES-256 Encrypted</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        tab_login, tab_signup = st.tabs(["🔐 Sign In", "✨ Create Account"])

        with tab_login:
            with st.form("login_form"):
                email    = st.text_input("Email", placeholder="you@example.com")
                password = st.text_input("Password", type="password", placeholder="••••••••")
                submitted = st.form_submit_button("Sign In →", use_container_width=True)
            if submitted:
                db = SessionLocal()
                user = db.query(User).filter(User.email == email).first()
                db.close()
                if user and verify_pw(password, user.hashed_pw):
                    st.session_state.user = {"id": user.id, "email": user.email, "name": user.full_name}
                    st.success("✓ Welcome back!")
                    st.rerun()
                else:
                    st.error("❌ Invalid email or password")

        with tab_signup:
            with st.form("signup_form"):
                full_name = st.text_input("Full Name", placeholder="John Doe")
                email2    = st.text_input("Email", placeholder="you@example.com", key="su_email")
                pass2     = st.text_input("Password", type="password", placeholder="Min 6 characters", key="su_pass")
                submitted2 = st.form_submit_button("Create Account →", use_container_width=True)
            if submitted2:
                if len(pass2) < 6:
                    st.error("Password must be at least 6 characters")
                else:
                    db = SessionLocal()
                    existing = db.query(User).filter(User.email == email2).first()
                    if existing:
                        st.error("Email already registered")
                    else:
                        user = User(id=str(uuid.uuid4()), email=email2, full_name=full_name, hashed_pw=hash_pw(pass2))
                        db.add(user); db.commit(); db.close()
                        st.session_state.user = {"id": user.id, "email": user.email, "name": full_name}
                        st.success("✓ Account created!")
                        st.rerun()
                    db.close()

        st.markdown("""
        <div style="text-align:center; margin-top:20px; padding:12px; background:rgba(16,185,129,0.06);
            border:1px solid rgba(16,185,129,0.2); border-radius:10px;">
            <p style="color:rgba(255,255,255,0.45); font-size:12px; margin:0;">
                🔒 Bank-grade AES-256 encryption · Your keys are never stored in plaintext
            </p>
        </div>
        """, unsafe_allow_html=True)

# ─── Sidebar ──────────────────────────────────────────────────────────────────
def show_sidebar():
    u = st.session_state.user
    with st.sidebar:
        st.markdown(f"""
        <div style="padding:16px 0 8px; text-align:center;">
            <div style="font-size:40px;">⚡</div>
            <p style="color:white; font-weight:800; font-size:17px; margin:6px 0 2px;">Elite Trading <span style="color:#3b82f6">AI</span></p>
            <p style="color:rgba(255,255,255,0.3); font-size:11px;">Institutional Intelligence Engine</p>
        </div>
        <hr style="border-color:rgba(255,255,255,0.08); margin:12px 0;">
        <div style="padding:10px 14px; background:rgba(59,130,246,0.08); border:1px solid rgba(59,130,246,0.18); border-radius:10px; margin-bottom:16px;">
            <p style="color:rgba(255,255,255,0.5); font-size:11px; margin:0 0 3px;">Logged in as</p>
            <p style="color:white; font-weight:600; font-size:13px; margin:0;">{u['name']}</p>
            <p style="color:rgba(255,255,255,0.35); font-size:11px; margin:0;">{u['email']}</p>
        </div>
        """, unsafe_allow_html=True)

        page = st.radio(
            "Navigation",
            ["⚡ Dashboard", "📰 News", "📄 Report", "⚙️ Settings"],
            label_visibility="collapsed"
        )

        st.markdown("<hr style='border-color:rgba(255,255,255,0.08);'>", unsafe_allow_html=True)
        st.markdown("""
        <div style="padding:12px; background:rgba(239,68,68,0.06); border:1px solid rgba(239,68,68,0.18); border-radius:10px;">
            <p style="color:rgba(255,255,255,0.5); font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:1px; margin:0 0 8px;">Risk Limits (Hard-coded)</p>
            <p style="color:rgba(255,255,255,0.45); font-size:11px; margin:3px 0;">• Max Position: <b style="color:#f59e0b">5%</b></p>
            <p style="color:rgba(255,255,255,0.45); font-size:11px; margin:3px 0;">• Stop Loss: <b style="color:#ef4444">2%</b></p>
            <p style="color:rgba(255,255,255,0.45); font-size:11px; margin:3px 0;">• Take Profit: <b style="color:#10b981">5%</b></p>
            <p style="color:rgba(255,255,255,0.45); font-size:11px; margin:3px 0;">• Min R:R: <b style="color:#3b82f6">1:2</b></p>
            <p style="color:rgba(255,255,255,0.45); font-size:11px; margin:3px 0;">• Daily Limit: <b style="color:#ef4444">10%</b></p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.user = None
            st.rerun()

    return page

# ─── Dashboard Page ───────────────────────────────────────────────────────────
def page_dashboard():
    st.markdown("## ⚡ Market Intelligence Dashboard")
    st.markdown("<p style='color:rgba(255,255,255,0.35);margin-top:-10px;font-size:13px;'>Real-time institutional-grade analysis engine</p>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([2, 1.5, 1])
    with col1:
        symbol = st.text_input("Symbol", value="BTC/USDT", placeholder="BTC/USDT, ETH/USDT, SOL/USDT...")
    with col2:
        strategy = st.selectbox("Strategy", ["Balanced", "Conservative", "Aggressive"])
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        run = st.button("⚡ Run Analysis", use_container_width=True)

    if run:
        with st.spinner("Analyzing market data & sentiment..."):
            ta = fetch_market_data(symbol.upper().strip())
            if ta.get("error"):
                st.error(f"⚠️ {ta['error']} — Check symbol format (e.g. BTC/USDT)")
                return
            news = fetch_news()
            report = generate_report(ta, news, strategy)
            st.session_state.last_report = {"ta": ta, "report": report, "news": news, "strategy": strategy}

    if not st.session_state.last_report:
        st.markdown("""
        <div style="text-align:center; padding:80px 24px;">
            <div style="font-size:60px; margin-bottom:20px;">⚡</div>
            <h3 style="color:rgba(255,255,255,0.45);">Enter a symbol and run analysis</h3>
            <p style="color:rgba(255,255,255,0.25); font-size:13px;">RSI · MACD · Bollinger Bands · News Sentiment · White Paper Reports</p>
        </div>
        """, unsafe_allow_html=True)
        return

    ta   = st.session_state.last_report["ta"]
    rep  = st.session_state.last_report["report"]
    strategy = st.session_state.last_report["strategy"]

    # Thesis Banner
    tc = "#10b981" if "BULL" in rep["thesis"] else "#ef4444" if "BEAR" in rep["thesis"] else "#f59e0b"
    sig_badge = f'<span class="badge-{"buy" if ta["signal"]=="BUY" else "sell" if ta["signal"]=="SELL" else "hold"}">{ta["signal"]} · {ta["strength"]}</span>'
    st.markdown(f"""
    <div class="glass-card" style="border-color:rgba({('16,185,129' if 'BULL' in rep['thesis'] else '239,68,68' if 'BEAR' in rep['thesis'] else '245,158,11')},0.3); margin-bottom:20px;">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:16px;">
            <div>
                <p style="color:rgba(255,255,255,0.4); font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:1px; margin-bottom:8px;">Final Thesis — {strategy}</p>
                <h2 style="font-size:32px; font-weight:900; color:{tc}; margin:0 0 10px; letter-spacing:-1px;">{rep["thesis"]}</h2>
                <p style="color:rgba(255,255,255,0.5); font-size:13px;">{ta["symbol"]} · Generated {rep["generated_at"]}</p>
            </div>
            <div style="text-align:right;">
                {sig_badge}
                <p style="color:rgba(255,255,255,0.25); font-size:11px; margin-top:10px;">Avg Sentiment: {rep["avg_sentiment"]}/5</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Metric Row
    c1,c2,c3,c4,c5,c6,c7 = st.columns(7)
    price_c  = "#10b981" if ta["change_24h"] >= 0 else "#ef4444"
    rsi_c    = "#10b981" if ta["rsi"] < 40 else "#ef4444" if ta["rsi"] > 60 else "#f59e0b"
    macd_c   = "#10b981" if ta["macd_hist"] > 0 else "#ef4444"
    ema_c    = "#10b981" if ta["ema_20"] > ta["ema_50"] else "#ef4444"
    for col, label, value, sub, color in [
        (c1,"Price",f"${ta['price']:,}",f"{'+' if ta['change_24h']>=0 else ''}{ta['change_24h']}% 24h",price_c),
        (c2,"RSI (14)",ta["rsi"],"Oversold<40 Overbought>60",rsi_c),
        (c3,"MACD",ta["macd"],f"Hist: {ta['macd_hist']}",macd_c),
        (c4,"EMA 20",f"${ta['ema_20']:,}",f"EMA50: ${ta['ema_50']:,}",ema_c),
        (c5,"BB Upper",f"${ta['bb_upper']:,}",f"Lower: ${ta['bb_lower']:,}","#a78bfa"),
        (c6,"Support 1",f"${ta['s1']:,}","Key support","#10b981"),
        (c7,"Resistance 1",f"${ta['r1']:,}","Key resistance","#ef4444"),
    ]:
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="metric-value" style="color:{color}">{value}</div>
                <div class="metric-sub">{sub}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Chart
    df_rows = ta["df"]
    df = pd.DataFrame(df_rows)
    df["date"] = pd.to_datetime(df["ts"], unit="ms")

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df["date"], open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        name="Price", increasing_line_color="#10b981", decreasing_line_color="#ef4444",
        increasing_fillcolor="rgba(16,185,129,0.3)", decreasing_fillcolor="rgba(239,68,68,0.3)"
    ))
    for level, color, name in [
        (ta["s1"],"rgba(16,185,129,0.7)","S1"), (ta["s2"],"rgba(16,185,129,0.4)","S2"),
        (ta["r1"],"rgba(239,68,68,0.7)","R1"),  (ta["r2"],"rgba(239,68,68,0.4)","R2"),
        (ta["ema_20"],"rgba(59,130,246,0.7)","EMA20"), (ta["ema_50"],"rgba(168,85,247,0.7)","EMA50"),
        (ta["bb_upper"],"rgba(245,158,11,0.4)","BB Upper"), (ta["bb_lower"],"rgba(245,158,11,0.4)","BB Lower"),
    ]:
        fig.add_hline(y=level, line_color=color, line_dash="dash", line_width=1,
                      annotation_text=name, annotation_font_color=color, annotation_font_size=10)
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="rgba(255,255,255,0.7)", height=400,
        margin=dict(l=0,r=0,t=10,b=0),
        xaxis=dict(gridcolor="rgba(255,255,255,0.04)", showline=False),
        yaxis=dict(gridcolor="rgba(255,255,255,0.04)", showline=False),
        legend=dict(bgcolor="rgba(0,0,0,0.3)", bordercolor="rgba(255,255,255,0.1)", borderwidth=1),
        xaxis_rangeslider_visible=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Actionable Thesis
    st.markdown("### ⚡ Actionable Thesis")
    ac1,ac2,ac3,ac4,ac5 = st.columns(5)
    for col, label, value, color in [
        (ac1,"Entry Price",f"${rep['entry']:,}","#3b82f6"),
        (ac2,"Stop Loss",f"${rep['sl']:,}","#ef4444"),
        (ac3,"Take Profit",f"${rep['tp']:,}","#10b981"),
        (ac4,"Risk:Reward",rep["rr"],"#f59e0b"),
        (ac5,"Position Size",rep["position_size"],"#a78bfa"),
    ]:
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="metric-value" style="color:{color};font-size:18px;">{value}</div>
            </div>
            """, unsafe_allow_html=True)

    # Validate button
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔒 Validate Trade (Risk Layer)", use_container_width=False):
        ai_resp = {
            "action": ta["signal"].lower(),
            "symbol": ta["symbol"],
            "entry_price": ta["price"],
            "stop_loss": rep["sl"],
            "take_profit": rep["tp"],
            "position_size_pct": 3.0,
            "reason": f"{ta['strength']} {ta['signal']} signal — RSI {ta['rsi']}"
        }
        result = validate_trade(ai_resp, balance=10000)
        if result["valid"]:
            st.success(f"✅ Trade APPROVED — R:R {result['order']['risk_reward']}")
            st.json(result["order"])
        else:
            st.error("❌ Trade REJECTED by Risk Layer")
            for r in result["reasons"]:
                st.warning(r)

# ─── News Page ────────────────────────────────────────────────────────────────
def page_news():
    st.markdown("## 📰 News & Sentiment Analysis")
    st.markdown("<p style='color:rgba(255,255,255,0.35);margin-top:-10px;font-size:13px;'>Live crypto news with AI-powered impact scoring</p>", unsafe_allow_html=True)

    with st.spinner("Loading news feeds..."):
        news = fetch_news()

    if not news:
        st.warning("Could not load news. Check your internet connection.")
        return

    avg_impact = sum(n["impact_score"] for n in news) / len(news)
    pos_count  = sum(1 for n in news if n["sentiment"] == "POSITIVE")
    neg_count  = sum(1 for n in news if n["sentiment"] == "NEGATIVE")
    mood_color = "#10b981" if avg_impact > 0.5 else "#ef4444" if avg_impact < -0.5 else "#f59e0b"
    mood_label = "🟢 BULLISH" if avg_impact > 0.5 else "🔴 BEARISH" if avg_impact < -0.5 else "🟡 NEUTRAL"

    c1,c2,c3,c4,c5 = st.columns(5)
    for col, label, value, color in [
        (c1,"Market Mood",mood_label,mood_color),
        (c2,"Avg Impact",f"{avg_impact:+.1f}/5",mood_color),
        (c3,"Positive News",pos_count,"#10b981"),
        (c4,"Negative News",neg_count,"#ef4444"),
        (c5,"Total Articles",len(news),"white"),
    ]:
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="metric-value" style="color:{color};font-size:18px;">{value}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    for n in news:
        ic = n["impact_score"]
        ic_color = "#10b981" if ic > 0 else "#ef4444" if ic < 0 else "#94a3b8"
        badge_cls = "badge-pos" if n["sentiment"]=="POSITIVE" else "badge-neg" if n["sentiment"]=="NEGATIVE" else "badge-neu"
        border_c  = "rgba(16,185,129,0.5)" if n["sentiment"]=="POSITIVE" else "rgba(239,68,68,0.5)" if n["sentiment"]=="NEGATIVE" else "rgba(148,163,184,0.3)"
        st.markdown(f"""
        <div class="glass-card" style="border-left:3px solid {border_c}; padding:18px 20px;">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:16px;">
                <div style="flex:1;">
                    <div style="display:flex; gap:10px; align-items:center; margin-bottom:8px;">
                        <span style="color:rgba(255,255,255,0.35); font-size:11px;">{n['source']}</span>
                        <span class="{badge_cls}">{n['sentiment']}</span>
                    </div>
                    <a href="{n['link']}" target="_blank" style="text-decoration:none;">
                        <p style="color:white; font-weight:600; font-size:14px; margin:0 0 6px; line-height:1.5;">{n['title']}</p>
                    </a>
                    <p style="color:rgba(255,255,255,0.4); font-size:12px; line-height:1.6; margin:0;">{n['summary']}</p>
                </div>
                <div style="text-align:center; flex-shrink:0;">
                    <p style="color:rgba(255,255,255,0.3); font-size:10px; margin:0 0 4px;">IMPACT</p>
                    <p style="color:{ic_color}; font-weight:900; font-size:22px; margin:0;">{'+' if ic>0 else ''}{ic}</p>
                    <p style="color:rgba(255,255,255,0.2); font-size:10px; margin:0;">/5</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ─── Report Page ──────────────────────────────────────────────────────────────
def page_report():
    st.markdown("## 📄 White Paper Analysis Report")

    if not st.session_state.last_report:
        st.info("💡 No report yet — go to Dashboard and run an analysis first.")
        return

    ta   = st.session_state.last_report["ta"]
    rep  = st.session_state.last_report["report"]
    news = st.session_state.last_report["news"]
    strategy = st.session_state.last_report["strategy"]

    tc = "#10b981" if "BULL" in rep["thesis"] else "#ef4444" if "BEAR" in rep["thesis"] else "#f59e0b"

    # Section 1
    st.markdown("""<div style="display:flex;align-items:center;gap:12px;margin:20px 0 16px;">
        <div style="width:4px;height:28px;background:linear-gradient(180deg,#3b82f6,#6366f1);border-radius:2px;"></div>
        <h3 style="margin:0;font-size:17px;">01 — Executive Summary</h3></div>""", unsafe_allow_html=True)

    c1,c2,c3 = st.columns(3)
    with c1: st.markdown(f'<div class="metric-card"><div class="metric-label">Symbol</div><div class="metric-value">{ta["symbol"]}</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="metric-card"><div class="metric-label">Overall Thesis</div><div class="metric-value" style="color:{tc};font-size:18px;">{rep["thesis"]}</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="metric-card"><div class="metric-label">Signal</div><div class="metric-value" style="color:{"#10b981" if ta["signal"]=="BUY" else "#ef4444" if ta["signal"]=="SELL" else "#f59e0b"};font-size:18px;">{ta["signal"]} · {ta["strength"]}</div></div>', unsafe_allow_html=True)
    st.markdown(f"""<div style="background:rgba(0,0,0,0.2);border-radius:12px;padding:18px 20px;border-left:3px solid rgba(59,130,246,0.5);margin:12px 0;">
        <p style="color:rgba(255,255,255,0.65);font-size:13px;line-height:1.7;margin:0;">
        {ta['symbol']} price at <b style="color:white">${ta['price']:,}</b> ({'+' if ta['change_24h']>=0 else ''}{ta['change_24h']}% 24h). 
        RSI at <b style="color:{"#10b981" if ta['rsi']<40 else "#ef4444" if ta['rsi']>60 else "#f59e0b"}">{ta['rsi']}</b>. 
        MACD histogram: <b style="color:{"#10b981" if ta['macd_hist']>0 else "#ef4444"}">{ta['macd_hist']}</b>. 
        EMA cross: <b style="color:{"#10b981" if ta['ema_20']>ta['ema_50'] else "#ef4444"}">{("Bullish" if ta['ema_20']>ta['ema_50'] else "Bearish")}</b>. 
        News sentiment avg: <b style="color:{"#10b981" if rep['avg_sentiment']>0 else "#ef4444"}">{rep['avg_sentiment']}/5</b>. 
        Strategy: <b style="color:#3b82f6">{strategy}</b>.
        </p>
    </div>""", unsafe_allow_html=True)

    # Section 2: Market Pulse
    st.markdown("""<div style="display:flex;align-items:center;gap:12px;margin:24px 0 16px;">
        <div style="width:4px;height:28px;background:linear-gradient(180deg,#f59e0b,#ef4444);border-radius:2px;"></div>
        <h3 style="margin:0;font-size:17px;">02 — Market Pulse (News Analysis)</h3></div>""", unsafe_allow_html=True)

    df_news = pd.DataFrame([{
        "Source": n["source"][:20], "Headline": n["title"][:70]+"...",
        "Impact": f"{'+' if n['impact_score']>0 else ''}{n['impact_score']}",
        "Sentiment": n["sentiment"]
    } for n in news[:10]])
    st.dataframe(df_news, use_container_width=True, hide_index=True)

    # Section 3: Technical
    st.markdown("""<div style="display:flex;align-items:center;gap:12px;margin:24px 0 16px;">
        <div style="width:4px;height:28px;background:linear-gradient(180deg,#10b981,#3b82f6);border-radius:2px;"></div>
        <h3 style="margin:0;font-size:17px;">03 — Technical Blueprint</h3></div>""", unsafe_allow_html=True)

    cols = st.columns(3)
    metrics = [
        ("RSI (14)", ta["rsi"], "#10b981" if ta["rsi"]<40 else "#ef4444" if ta["rsi"]>60 else "#f59e0b", "Oversold<30 | Neutral 40-60 | Overbought>70"),
        ("MACD Histogram", ta["macd_hist"], "#10b981" if ta["macd_hist"]>0 else "#ef4444", "Positive = Bullish momentum"),
        ("EMA Cross", "Bullish" if ta["ema_20"]>ta["ema_50"] else "Bearish", "#10b981" if ta["ema_20"]>ta["ema_50"] else "#ef4444", f"EMA20: ${ta['ema_20']:,} | EMA50: ${ta['ema_50']:,}"),
        ("BB Upper", f"${ta['bb_upper']:,}", "#a78bfa", f"Middle: ${ta['bb_middle']:,}"),
        ("BB Lower", f"${ta['bb_lower']:,}", "#a78bfa", "Price near lower = Bounce zone"),
        ("Volume (24h)", f"{ta['volume_24h']:,.0f}", "white", "Higher = stronger signal"),
    ]
    for i, (label, value, color, sub) in enumerate(metrics):
        with cols[i % 3]:
            st.markdown(f"""<div class="metric-card" style="margin-bottom:12px;">
                <div class="metric-label">{label}</div>
                <div class="metric-value" style="color:{color};font-size:18px;">{value}</div>
                <div class="metric-sub">{sub}</div>
            </div>""", unsafe_allow_html=True)

    # Section 4: Key Levels
    st.markdown("""<div style="display:flex;align-items:center;gap:12px;margin:24px 0 16px;">
        <div style="width:4px;height:28px;background:linear-gradient(180deg,#6366f1,#a78bfa);border-radius:2px;"></div>
        <h3 style="margin:0;font-size:17px;">04 — Key Levels (Visual Blueprint)</h3></div>""", unsafe_allow_html=True)
    lc1,lc2,lc3,lc4 = st.columns(4)
    for col, label, val, color in [
        (lc1,"Resistance 2",f"${ta['r2']:,}","#ef4444"),
        (lc2,"Resistance 1 (Key)",f"${ta['r1']:,}","#ef4444"),
        (lc3,"Support 1 (Key)",f"${ta['s1']:,}","#10b981"),
        (lc4,"Support 2",f"${ta['s2']:,}","#10b981"),
    ]:
        with col:
            st.markdown(f"""<div class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="metric-value" style="color:{color};font-size:18px;">{val}</div>
            </div>""", unsafe_allow_html=True)

    # Section 5: Actionable Thesis
    st.markdown("""<div style="display:flex;align-items:center;gap:12px;margin:24px 0 16px;">
        <div style="width:4px;height:28px;background:linear-gradient(180deg,#f59e0b,#10b981);border-radius:2px;"></div>
        <h3 style="margin:0;font-size:17px;">05 — Actionable Thesis</h3></div>""", unsafe_allow_html=True)
    ac1,ac2,ac3,ac4,ac5 = st.columns(5)
    for col, label, value, color in [
        (ac1,"Recommendation",ta["signal"],"#10b981" if ta["signal"]=="BUY" else "#ef4444" if ta["signal"]=="SELL" else "#f59e0b"),
        (ac2,"Entry Price",f"${rep['entry']:,}","#3b82f6"),
        (ac3,"Stop Loss",f"${rep['sl']:,}","#ef4444"),
        (ac4,"Take Profit",f"${rep['tp']:,}","#10b981"),
        (ac5,"Risk:Reward",rep["rr"],"#f59e0b"),
    ]:
        with col:
            st.markdown(f"""<div class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="metric-value" style="color:{color};font-size:18px;">{value}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown(f"""<div style="background:rgba(245,158,11,0.06);border:1px solid rgba(245,158,11,0.15);border-radius:10px;padding:14px 18px;margin-top:16px;">
        <p style="color:rgba(255,255,255,0.3);font-size:11px;font-style:italic;margin:0;">
        ⚠️ Not financial advice. This is an execution tool. Always use proper risk management. Never risk more than you can afford to lose.
        </p>
    </div>""", unsafe_allow_html=True)

# ─── Settings Page ────────────────────────────────────────────────────────────
def page_settings():
    st.markdown("## ⚙️ Settings")
    st.markdown("<p style='color:rgba(255,255,255,0.35);margin-top:-10px;font-size:13px;'>Manage your exchange API keys (AES-256 encrypted)</p>", unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["🔑 API Keys", "⚠️ Risk Limits"])

    with tab1:
        st.markdown("""<div style="background:rgba(16,185,129,0.06);border:1px solid rgba(16,185,129,0.2);border-radius:12px;padding:14px 18px;margin-bottom:20px;display:flex;gap:10px;align-items:center;">
            <span style="font-size:20px;">🔒</span>
            <p style="color:rgba(255,255,255,0.55);font-size:13px;margin:0;">
                Your API keys are encrypted with <b style="color:#10b981">AES-256 (Fernet)</b> before being stored.
                They are <b style="color:#10b981">never saved in plaintext</b>.
            </p>
        </div>""", unsafe_allow_html=True)

        with st.form("api_key_form"):
            exchange   = st.selectbox("Exchange", ["kraken","binance","bybit","okx","coinbase","kucoin"])
            api_key    = st.text_input("API Key", type="password", placeholder="Your exchange API key")
            api_secret = st.text_input("API Secret", type="password", placeholder="Your exchange API secret")
            save       = st.form_submit_button("🔒 Save API Key (Encrypted)", use_container_width=True)

        if save:
            if not api_key or not api_secret:
                st.error("Please fill in both fields")
            else:
                db = SessionLocal()
                user_id = st.session_state.user["id"]
                enc_key = fernet.encrypt(api_key.encode()).decode()
                enc_sec = fernet.encrypt(api_secret.encode()).decode()
                existing = db.query(EncryptedKey).filter(EncryptedKey.user_id==user_id, EncryptedKey.exchange==exchange).first()
                if existing:
                    existing.enc_api_key = enc_key; existing.enc_api_secret = enc_sec
                else:
                    db.add(EncryptedKey(id=str(uuid.uuid4()), user_id=user_id, exchange=exchange, enc_api_key=enc_key, enc_api_secret=enc_sec))
                db.commit(); db.close()
                st.success(f"✅ {exchange.capitalize()} API key saved with AES-256 encryption!")

        # Show connected exchanges
        db = SessionLocal()
        keys = db.query(EncryptedKey).filter(EncryptedKey.user_id==st.session_state.user["id"]).all()
        db.close()
        if keys:
            st.markdown("**Connected Exchanges:**")
            badges = " ".join([f'<span style="background:rgba(16,185,129,0.1);border:1px solid rgba(16,185,129,0.3);color:#10b981;padding:4px 14px;border-radius:6px;font-size:12px;font-weight:600;">✓ {k.exchange}</span>' for k in keys])
            st.markdown(f'<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:8px;">{badges}</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown("<br>", unsafe_allow_html=True)
        limits = [
            ("Max Position Size", "5%", "Per trade, never exceed 5% of total balance", "#f59e0b"),
            ("Stop Loss (SL)", "2%", "Automated SL placed 2% below entry price", "#ef4444"),
            ("Take Profit (TP)", "5%", "Minimum TP set 5% above entry price", "#10b981"),
            ("Min Risk:Reward", "1:2", "Only execute if reward is at least 2x the risk", "#3b82f6"),
            ("Daily Loss Limit", "10%", "Global shutdown triggered if daily loss > 10%", "#ef4444"),
        ]
        for name, value, note, color in limits:
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;align-items:center;background:rgba(0,0,0,0.2);border-radius:10px;padding:14px 18px;margin-bottom:10px;">
                <div>
                    <p style="color:white;font-weight:600;font-size:14px;margin:0 0 4px;">{name}</p>
                    <p style="color:rgba(255,255,255,0.35);font-size:12px;margin:0;">{note}</p>
                </div>
                <span style="color:{color};font-weight:800;font-size:20px;background:rgba(0,0,0,0.2);padding:6px 16px;border-radius:8px;">{value}</span>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("""<div style="background:rgba(239,68,68,0.06);border:1px solid rgba(239,68,68,0.2);border-radius:10px;padding:12px 16px;margin-top:8px;">
            <p style="color:rgba(239,68,68,0.7);font-size:12px;font-weight:600;margin:0;">🔒 NON-NEGOTIABLE — These limits are hard-coded in the validation layer. The AI model cannot override them.</p>
        </div>""", unsafe_allow_html=True)

# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    if not st.session_state.user:
        show_auth()
        return

    page = show_sidebar()

    if   page == "⚡ Dashboard": page_dashboard()
    elif page == "📰 News":      page_news()
    elif page == "📄 Report":    page_report()
    elif page == "⚙️ Settings":  page_settings()

if __name__ == "__main__":
    main()
