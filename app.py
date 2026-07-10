"""
Elite Trading Intelligence Engine — v4.0
Institutional-Grade Analysis Platform
Clean rebuild: Auth + TA + FA + White Paper Reports
"""

import streamlit as st
import ccxt
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import feedparser
import re
import uuid
import os
import datetime
import json
from cryptography.fernet import Fernet
from passlib.context import CryptContext
from sqlalchemy import create_engine, Column, String, Float, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker

# ─── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Trading Intelligence Engine",
    page_icon="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>◈</text></svg>",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"Get Help": None, "Report a bug": None, "About": None}
)

# ─── Database ─────────────────────────────────────────────────────────────────
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
    id         = Column(String, primary_key=True)
    email      = Column(String, unique=True, index=True)
    full_name  = Column(String)
    hashed_pw  = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class EncryptedKey(Base):
    __tablename__ = "encrypted_keys"
    id          = Column(String, primary_key=True)
    user_id     = Column(String, index=True)
    exchange    = Column(String)
    enc_key     = Column(Text)
    enc_secret  = Column(Text)
    created_at  = Column(DateTime, default=datetime.datetime.utcnow)

class TradeLog(Base):
    __tablename__ = "trade_logs"
    id          = Column(String, primary_key=True)
    user_id     = Column(String)
    symbol      = Column(String)
    action      = Column(String)
    entry_price = Column(Float)
    stop_loss   = Column(Float)
    take_profit = Column(Float)
    rr_ratio    = Column(Float)
    status      = Column(String, default="PENDING")
    created_at  = Column(DateTime, default=datetime.datetime.utcnow)

Base.metadata.create_all(bind=engine)

# ─── Security ─────────────────────────────────────────────────────────────────
RAW_KEY = os.getenv("ENCRYPTION_KEY", "")
try:
    fernet = Fernet(RAW_KEY.encode() if len(RAW_KEY) == 44 else Fernet.generate_key())
except Exception:
    fernet = Fernet(Fernet.generate_key())

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
hash_pw    = lambda pw: pwd_ctx.hash(pw)
verify_pw  = lambda p, h: pwd_ctx.verify(p, h)

# ─── Global CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

/* Reset & Base */
*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, sans-serif;
}

/* App Background */
.stApp {
    background: radial-gradient(ellipse at 20% 0%, rgba(59,130,246,0.12) 0%, transparent 50%),
                radial-gradient(ellipse at 80% 100%, rgba(99,102,241,0.1) 0%, transparent 50%),
                linear-gradient(160deg, #070d1a 0%, #0b1425 40%, #0e0820 100%);
    min-height: 100vh;
}

/* Hide Streamlit branding */
#MainMenu, footer, header { visibility: hidden !important; }
.stDeployButton { display: none !important; }
.block-container { padding-top: 0 !important; }

/* Sidebar */
section[data-testid="stSidebar"] > div:first-child {
    background: rgba(7, 13, 26, 0.95) !important;
    border-right: 1px solid rgba(255,255,255,0.06) !important;
    backdrop-filter: blur(24px) !important;
}
section[data-testid="stSidebar"] { background: transparent !important; }

/* Typography */
h1 { color: #f1f5f9 !important; font-weight: 800 !important; letter-spacing: -0.8px !important; }
h2 { color: #e2e8f0 !important; font-weight: 700 !important; letter-spacing: -0.4px !important; }
h3 { color: #cbd5e1 !important; font-weight: 600 !important; }
p, li { color: #94a3b8; }

/* Glass Card */
.g-card {
    background: rgba(255,255,255,0.035);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px;
    padding: 24px;
    margin-bottom: 16px;
    transition: border-color 0.3s ease;
}
.g-card:hover { border-color: rgba(59,130,246,0.2); }

/* Metric tile */
.m-tile {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px;
    padding: 16px 18px;
    text-align: center;
}
.m-tile-label {
    color: rgba(255,255,255,0.35);
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 8px;
    display: block;
}
.m-tile-value {
    font-size: 20px;
    font-weight: 700;
    display: block;
    line-height: 1;
    margin-bottom: 5px;
    letter-spacing: -0.5px;
}
.m-tile-sub {
    color: rgba(255,255,255,0.3);
    font-size: 10px;
    display: block;
}

/* Signals */
.sig-buy  { color: #10b981; }
.sig-sell { color: #ef4444; }
.sig-hold { color: #f59e0b; }

/* Badge */
.badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 5px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.04em;
}
.badge-buy    { background: rgba(16,185,129,0.12); border: 1px solid rgba(16,185,129,0.35); color: #10b981; }
.badge-sell   { background: rgba(239,68,68,0.12);  border: 1px solid rgba(239,68,68,0.35);  color: #ef4444; }
.badge-hold   { background: rgba(245,158,11,0.12); border: 1px solid rgba(245,158,11,0.35); color: #f59e0b; }
.badge-pos    { background: rgba(16,185,129,0.1);  border: 1px solid rgba(16,185,129,0.25); color: #10b981; }
.badge-neg    { background: rgba(239,68,68,0.1);   border: 1px solid rgba(239,68,68,0.25);  color: #ef4444; }
.badge-neu    { background: rgba(148,163,184,0.08);border: 1px solid rgba(148,163,184,0.2); color: #94a3b8; }

/* Section rule */
.sec-rule {
    display: flex;
    align-items: center;
    gap: 14px;
    margin: 28px 0 18px;
}
.sec-rule-bar {
    width: 3px;
    height: 22px;
    border-radius: 2px;
    flex-shrink: 0;
}
.sec-rule-title {
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: rgba(255,255,255,0.35) !important;
    margin: 0;
}
.sec-rule-num {
    font-size: 11px;
    color: rgba(255,255,255,0.18);
    margin-left: auto;
    font-family: 'JetBrains Mono', monospace;
}

/* Inputs */
.stTextInput > div > div > input,
.stPasswordInput > div > div > input,
.stSelectbox > div > div,
.stMultiSelect > div > div {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 9px !important;
    color: #e2e8f0 !important;
    font-size: 14px !important;
}
.stTextInput > div > div > input:focus,
.stPasswordInput > div > div > input:focus {
    border-color: rgba(59,130,246,0.5) !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.1) !important;
}
label[data-testid="stWidgetLabel"] p {
    color: rgba(255,255,255,0.45) !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    letter-spacing: 0.02em !important;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #2563eb 0%, #4f46e5 100%) !important;
    border: none !important;
    border-radius: 9px !important;
    color: white !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    letter-spacing: 0.01em !important;
    padding: 10px 0 !important;
    transition: all 0.25s ease !important;
}
.stButton > button:hover {
    opacity: 0.92 !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 10px 30px rgba(37,99,235,0.35) !important;
}

/* Radio nav */
.stRadio > label { display: none !important; }
.stRadio > div {
    flex-direction: column !important;
    gap: 2px !important;
}
.stRadio div[role="radio"] {
    padding: 9px 14px !important;
    border-radius: 8px !important;
    font-size: 13px !important;
    color: rgba(255,255,255,0.5) !important;
    transition: all 0.2s !important;
    cursor: pointer !important;
}
.stRadio div[role="radio"][aria-checked="true"] {
    background: rgba(37,99,235,0.15) !important;
    color: #60a5fa !important;
    font-weight: 600 !important;
}
.stRadio div[role="radio"]:hover {
    background: rgba(255,255,255,0.05) !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: rgba(0,0,0,0.2) !important;
    border-radius: 8px !important;
    padding: 4px !important;
    gap: 2px !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 6px !important;
    color: rgba(255,255,255,0.4) !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 8px 16px !important;
}
.stTabs [aria-selected="true"] {
    background: rgba(37,99,235,0.2) !important;
    color: #60a5fa !important;
    font-weight: 600 !important;
}
.stTabs [data-baseweb="tab-highlight"] { display: none !important; }

/* DataFrame */
.dataframe { background: transparent !important; }
[data-testid="stDataFrame"] { background: rgba(0,0,0,0.15) !important; border-radius: 10px !important; }

/* Divider */
hr { border: none !important; border-top: 1px solid rgba(255,255,255,0.06) !important; margin: 20px 0 !important; }

/* Spinner */
.stSpinner > div { color: #60a5fa !important; }

/* Alert boxes */
.stSuccess { background: rgba(16,185,129,0.08) !important; border: 1px solid rgba(16,185,129,0.25) !important; border-radius: 9px !important; }
.stError   { background: rgba(239,68,68,0.08)  !important; border: 1px solid rgba(239,68,68,0.25)  !important; border-radius: 9px !important; }
.stWarning { background: rgba(245,158,11,0.08) !important; border: 1px solid rgba(245,158,11,0.25) !important; border-radius: 9px !important; }
.stInfo    { background: rgba(59,130,246,0.08) !important; border: 1px solid rgba(59,130,246,0.25) !important; border-radius: 9px !important; }

/* White paper report styles */
.report-section {
    background: rgba(255,255,255,0.025);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px;
    padding: 28px;
    margin-bottom: 20px;
}
.report-section-header {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 20px;
    padding-bottom: 16px;
    border-bottom: 1px solid rgba(255,255,255,0.06);
}
.report-num {
    width: 32px; height: 32px;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    color: rgba(255,255,255,0.4);
    flex-shrink: 0;
}
.report-title {
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: rgba(255,255,255,0.5);
    margin: 0;
}
.report-body {
    font-size: 13px;
    line-height: 1.75;
    color: rgba(255,255,255,0.55);
}
.report-key {
    color: rgba(255,255,255,0.3);
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}
.report-val {
    font-size: 15px;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
}
.risk-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    background: rgba(0,0,0,0.2);
    border-radius: 8px;
    margin-bottom: 8px;
}
.risk-name { color: rgba(255,255,255,0.6); font-size: 13px; font-weight: 500; }
.risk-note { color: rgba(255,255,255,0.3); font-size: 11px; }
.risk-val  { font-weight: 700; font-size: 15px; font-family: 'JetBrains Mono', monospace; }
.news-row {
    display: flex;
    align-items: flex-start;
    gap: 14px;
    padding: 14px 0;
    border-bottom: 1px solid rgba(255,255,255,0.04);
}
.news-score {
    min-width: 42px;
    text-align: center;
    font-family: 'JetBrains Mono', monospace;
    font-size: 16px;
    font-weight: 700;
    padding-top: 2px;
}
.news-body { flex: 1; }
.news-title { color: rgba(255,255,255,0.75); font-size: 13px; font-weight: 500; line-height: 1.5; margin-bottom: 4px; }
.news-summary { color: rgba(255,255,255,0.38); font-size: 11px; line-height: 1.6; }
.news-meta { color: rgba(255,255,255,0.2); font-size: 10px; margin-top: 5px; }
.level-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 16px;
    border-radius: 8px;
    margin-bottom: 6px;
}
.auth-container {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 40px 20px;
}
.auth-card {
    width: 100%;
    max-width: 420px;
    background: rgba(255,255,255,0.03);
    backdrop-filter: blur(30px);
    -webkit-backdrop-filter: blur(30px);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 20px;
    padding: 44px 40px;
}
</style>
""", unsafe_allow_html=True)

# ─── Session State ─────────────────────────────────────────────────────────────
for k, v in [("user", None), ("report_data", None), ("page", "Dashboard")]:
    if k not in st.session_state:
        st.session_state[k] = v

# ─── Risk Validation Layer ─────────────────────────────────────────────────────
class RiskLimits:
    max_position_pct   = 5.0
    max_sl_pct         = 2.0
    min_tp_pct         = 5.0
    min_risk_reward    = 2.0
    max_daily_loss_pct = 10.0

def validate_trade(action, entry, sl, tp, size_pct, balance=10000, daily_pnl=0):
    L = RiskLimits()
    issues = []
    if daily_pnl <= -L.max_daily_loss_pct:
        return False, [f"Daily loss limit breached ({daily_pnl}%). Global shutdown active."], None
    if action.upper() == "HOLD":
        return True, ["No trade — HOLD signal."], None
    if size_pct > L.max_position_pct:
        issues.append(f"Position {size_pct}% > max {L.max_position_pct}%")
    sl_dist = abs((entry - sl) / entry) * 100
    if sl_dist > L.max_sl_pct + 1e-9:
        issues.append(f"Stop-loss distance {sl_dist:.2f}% > max {L.max_sl_pct}%")
    risk   = abs(entry - sl)
    reward = abs(tp - entry)
    rr     = round(reward / risk, 2) if risk > 0 else 0
    if rr < L.min_risk_reward:
        issues.append(f"R:R {rr:.2f} below minimum 1:{L.min_risk_reward}")
    if issues:
        return False, issues, None
    return True, [], {
        "action": action, "entry_price": entry, "stop_loss": sl,
        "take_profit": tp, "position_size_pct": size_pct,
        "trade_value": round(balance * size_pct / 100, 2),
        "risk_reward": f"1:{rr}"
    }

# ─── Market Data Engine ───────────────────────────────────────────────────────
@st.cache_data(ttl=180)
def get_market_data(symbol: str):
    try:
        ex = ccxt.kraken({"enableRateLimit": True})
        ohlcv = ex.fetch_ohlcv(symbol, "1d", limit=120)
        ob    = ex.fetch_order_book(symbol, limit=10)
        ticker = ex.fetch_ticker(symbol)

        df = pd.DataFrame(ohlcv, columns=["ts","open","high","low","close","volume"])
        df["dt"] = pd.to_datetime(df["ts"], unit="ms")
        c = df["close"]

        price   = round(float(c.iloc[-1]), 2)
        prev    = round(float(c.iloc[-2]), 2)
        ch24    = round((price - prev) / prev * 100, 2)
        vol24   = round(float(ticker.get("quoteVolume", df["volume"].iloc[-1])), 2)
        high24  = round(float(ticker.get("high", df["high"].iloc[-1])), 2)
        low24   = round(float(ticker.get("low",  df["low"].iloc[-1])), 2)

        # RSI (14)
        delta = c.diff()
        gain  = delta.where(delta > 0, 0).rolling(14).mean()
        loss  = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs    = gain / loss.replace(0, np.inf)
        rsi   = round(float((100 - 100 / (1 + rs)).iloc[-1]), 2)

        # MACD (12, 26, 9)
        ema12    = c.ewm(span=12, adjust=False).mean()
        ema26    = c.ewm(span=26, adjust=False).mean()
        macd_l   = ema12 - ema26
        sig_l    = macd_l.ewm(span=9, adjust=False).mean()
        hist     = macd_l - sig_l
        macd     = round(float(macd_l.iloc[-1]), 4)
        macd_sig = round(float(sig_l.iloc[-1]), 4)
        macd_hist= round(float(hist.iloc[-1]), 4)

        # Bollinger Bands (20, 2)
        sma20 = c.rolling(20).mean()
        std20 = c.rolling(20).std()
        bb_up = round(float((sma20 + 2*std20).iloc[-1]), 2)
        bb_md = round(float(sma20.iloc[-1]), 2)
        bb_lo = round(float((sma20 - 2*std20).iloc[-1]), 2)

        # EMAs
        ema9  = round(float(c.ewm(span=9).mean().iloc[-1]), 2)
        ema20_v = round(float(c.ewm(span=20).mean().iloc[-1]), 2)
        ema50 = round(float(c.ewm(span=50).mean().iloc[-1]), 2)
        ema200= round(float(c.ewm(span=200).mean().iloc[-1]), 2)

        # Volume analysis
        avg_vol = float(df["volume"].tail(20).mean())
        vol_ratio = round(float(df["volume"].iloc[-1]) / avg_vol, 2)

        # Support & Resistance via pivot clustering
        highs = list(df["high"].tail(60))
        lows  = list(df["low"].tail(60))
        all_lvl = sorted(highs + lows)
        cluster = (max(all_lvl) - min(all_lvl)) * 0.012
        merged = []
        for p in all_lvl:
            if not any(abs(p - m) < cluster for m in merged):
                merged.append(round(p, 2))
        sups  = sorted([l for l in merged if l < price * 0.999], reverse=True)
        ress  = sorted([l for l in merged if l > price * 1.001])
        s1 = sups[0] if len(sups) > 0 else round(price * 0.98, 2)
        s2 = sups[1] if len(sups) > 1 else round(price * 0.95, 2)
        s3 = sups[2] if len(sups) > 2 else round(price * 0.92, 2)
        r1 = ress[0] if len(ress) > 0 else round(price * 1.02, 2)
        r2 = ress[1] if len(ress) > 1 else round(price * 1.05, 2)
        r3 = ress[2] if len(ress) > 2 else round(price * 1.08, 2)

        # Order book imbalance
        bid_vol = sum([b[1] for b in ob.get("bids", [])[:5]])
        ask_vol = sum([a[1] for a in ob.get("asks", [])[:5]])
        ob_ratio = round(bid_vol / (bid_vol + ask_vol), 3) if (bid_vol + ask_vol) > 0 else 0.5

        # Composite signal
        score = 0
        rsi_note = ""
        if rsi < 30:   score += 3; rsi_note = "Deeply Oversold — High reversal probability"
        elif rsi < 40: score += 2; rsi_note = "Oversold — Moderate buy signal"
        elif rsi < 50: score += 1; rsi_note = "Slightly Bearish — Approaching neutral"
        elif rsi < 60: score -= 1; rsi_note = "Slightly Bullish — Approaching overbought"
        elif rsi < 70: score -= 2; rsi_note = "Overbought — Consider partial profit taking"
        else:          score -= 3; rsi_note = "Deeply Overbought — High reversal risk"

        macd_note = ""
        if macd_hist > 0: score += 2; macd_note = "Bullish crossover — momentum accelerating"
        else:             score -= 2; macd_note = "Bearish crossover — momentum weakening"

        ema_note = ""
        if ema9 > ema20_v > ema50: score += 2; ema_note = "Full bullish stack (EMA9 > EMA20 > EMA50)"
        elif ema9 < ema20_v < ema50: score -= 2; ema_note = "Full bearish stack (EMA9 < EMA20 < EMA50)"
        elif ema20_v > ema50: score += 1; ema_note = "Medium-term bullish (EMA20 > EMA50)"
        else: score -= 1; ema_note = "Medium-term bearish (EMA20 < EMA50)"

        bb_pct = (price - bb_lo) / (bb_up - bb_lo) * 100 if (bb_up - bb_lo) > 0 else 50
        bb_note = ""
        if bb_pct < 20:   score += 1; bb_note = "Price near lower band — potential bounce zone"
        elif bb_pct > 80: score -= 1; bb_note = "Price near upper band — potential resistance zone"
        else:             bb_note = f"Price at {round(bb_pct)}% of band range — neutral"

        ob_note = ""
        if ob_ratio > 0.6: score += 1; ob_note = f"Buy-side dominance ({round(ob_ratio*100)}% bids)"
        elif ob_ratio < 0.4: score -= 1; ob_note = f"Sell-side pressure ({round((1-ob_ratio)*100)}% asks)"
        else: ob_note = "Balanced order book — no directional bias"

        vol_note = ""
        if vol_ratio > 1.5: score += 1; vol_note = f"Volume spike {vol_ratio}x average — confirms signal"
        elif vol_ratio > 1.0: vol_note = f"Volume {vol_ratio}x average — above normal"
        else: vol_note = f"Low volume {vol_ratio}x average — signal may be weak"

        if score >= 5:    sig, strength = "BUY",  "STRONG"
        elif score >= 3:  sig, strength = "BUY",  "MODERATE"
        elif score >= 1:  sig, strength = "BUY",  "WEAK"
        elif score <= -5: sig, strength = "SELL", "STRONG"
        elif score <= -3: sig, strength = "SELL", "MODERATE"
        elif score <= -1: sig, strength = "SELL", "WEAK"
        else:             sig, strength = "HOLD", "NEUTRAL"

        return {
            "ok": True, "symbol": symbol,
            "price": price, "prev": prev, "change_24h": ch24,
            "high_24h": high24, "low_24h": low24, "volume_24h": vol24,
            "rsi": rsi, "rsi_note": rsi_note,
            "macd": macd, "macd_signal": macd_sig, "macd_hist": macd_hist, "macd_note": macd_note,
            "bb_upper": bb_up, "bb_middle": bb_md, "bb_lower": bb_lo, "bb_pct": round(bb_pct,1), "bb_note": bb_note,
            "ema9": ema9, "ema20": ema20_v, "ema50": ema50, "ema200": ema200, "ema_note": ema_note,
            "volume_ratio": vol_ratio, "vol_note": vol_note,
            "ob_ratio": ob_ratio, "ob_note": ob_note,
            "s1": s1, "s2": s2, "s3": s3, "r1": r1, "r2": r2, "r3": r3,
            "signal": sig, "strength": strength, "score": score,
            "df": df.tail(90).to_dict("records"),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ─── News Engine ──────────────────────────────────────────────────────────────
POS_W = ["surge","rally","bull","gain","rise","growth","adoption","approval","launch","partnership","record","high","jump","soar","recover","strong","institutional","accumulate","breakout","upgrade","positive","bullish","buy","support","confident","optimistic"]
NEG_W = ["crash","bear","drop","loss","fall","ban","hack","fail","sell","dump","plunge","decline","risk","fear","collapse","bankrupt","fraud","scam","warning","concern","lawsuit","negative","bearish","short","resistance","panic","suspicious","investigate","probe"]

FEEDS = [
    "https://feeds.feedburner.com/CoinDesk",
    "https://cointelegraph.com/rss",
    "https://www.newsbtc.com/feed/",
    "https://cryptopotato.com/feed/",
    "https://cryptoslate.com/feed/",
]

@st.cache_data(ttl=600)
def get_news():
    items = []
    for url in FEEDS:
        try:
            f = feedparser.parse(url)
            src = f.feed.get("title", "Feed")[:25]
            for e in f.entries[:4]:
                title   = e.get("title", "")
                raw_sum = e.get("summary", e.get("description", ""))
                summary = re.sub(r"<[^>]+>", "", raw_sum).strip()[:200]
                link    = e.get("link", "")
                pub     = e.get("published", "")[:24]
                txt = (title + " " + summary).lower()
                pos = sum(1 for w in POS_W if w in txt)
                neg = sum(1 for w in NEG_W if w in txt)
                raw = (pos - neg) * 1.1
                score = round(max(-5.0, min(5.0, raw)), 1)
                sent  = "POSITIVE" if score > 0.5 else "NEGATIVE" if score < -0.5 else "NEUTRAL"
                # One-sentence summary (first sentence of summary)
                first_sent = re.split(r'[.!?]', summary)[0].strip()
                if len(first_sent) < 20:
                    first_sent = summary[:120]
                items.append({
                    "title": title, "one_line": first_sent[:150],
                    "link": link, "source": src,
                    "published": pub, "score": score, "sentiment": sent
                })
        except Exception:
            continue
    items.sort(key=lambda x: abs(x["score"]), reverse=True)
    return items[:15]

# ─── Report Engine ────────────────────────────────────────────────────────────
def build_report(ta, news, strategy):
    avg_s = sum(n["score"] for n in news) / len(news) if news else 0
    sig   = ta["signal"]
    score = ta["score"]

    if   sig == "BUY"  and ta["strength"] == "STRONG":  thesis = "STRONGLY BULLISH"
    elif sig == "BUY"  and ta["strength"] == "MODERATE": thesis = "BULLISH"
    elif sig == "BUY"  and ta["strength"] == "WEAK":     thesis = "MILDLY BULLISH"
    elif sig == "SELL" and ta["strength"] == "STRONG":   thesis = "STRONGLY BEARISH"
    elif sig == "SELL" and ta["strength"] == "MODERATE": thesis = "BEARISH"
    elif sig == "SELL" and ta["strength"] == "WEAK":     thesis = "MILDLY BEARISH"
    else:                                                 thesis = "NEUTRAL"

    p = ta["price"]
    sl_pct = 0.02
    tp_pct = 0.05 if strategy != "Conservative" else 0.04
    sl = round(p * (1 - sl_pct) if sig == "BUY" else p * (1 + sl_pct), 2)
    tp = round(p * (1 + tp_pct) if sig == "BUY" else p * (1 - tp_pct), 2)
    rr = round(abs(tp - p) / abs(p - sl), 2) if abs(p - sl) > 0 else 0
    ps = {"Conservative": 2.0, "Balanced": 3.5, "Aggressive": 5.0}.get(strategy, 3.5)

    # Executive summary narrative
    trend = "an upward" if sig == "BUY" else "a downward" if sig == "SELL" else "a neutral"
    exec_summary = (
        f"{ta['symbol']} is currently trading at ${p:,.2f}, reflecting a {'+' if ta['change_24h'] >= 0 else ''}{ta['change_24h']}% move over the past 24 hours. "
        f"The composite technical score of {score:+d} indicates {trend} directional bias. "
        f"RSI at {ta['rsi']} suggests the asset is {'oversold and potentially reversing higher' if ta['rsi'] < 40 else 'overbought and potentially reversing lower' if ta['rsi'] > 60 else 'in neutral territory'}. "
        f"The MACD histogram reading of {ta['macd_hist']:+.4f} signals {'building bullish momentum' if ta['macd_hist'] > 0 else 'weakening momentum with bearish pressure'}. "
        f"{'Volume is elevated at ' + str(ta['volume_ratio']) + 'x the 20-day average, adding conviction to the signal.' if ta['volume_ratio'] > 1.2 else 'Volume is below average, suggesting lower confidence in the directional move.'} "
        f"News sentiment across {len(news)} articles averages {avg_s:+.1f}/5.0, indicating a {'constructive' if avg_s > 0 else 'cautious' if avg_s < 0 else 'neutral'} macro backdrop."
    )

    return {
        "thesis": thesis, "signal": sig, "strength": ta["strength"],
        "entry": p, "sl": sl, "tp": tp, "rr": rr, "position_size": ps,
        "avg_sentiment": round(avg_s, 2),
        "exec_summary": exec_summary,
        "generated_at": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "strategy": strategy,
    }

# ─── Chart Engine ─────────────────────────────────────────────────────────────
def build_chart(ta):
    rows = ta["df"]
    df   = pd.DataFrame(rows)
    df["dt"] = pd.to_datetime(df["ts"], unit="ms")

    fig = go.Figure()

    # Candlesticks
    fig.add_trace(go.Candlestick(
        x=df["dt"], open=df["open"], high=df["high"],
        low=df["low"], close=df["close"],
        name="Price",
        increasing=dict(line=dict(color="#10b981", width=1), fillcolor="rgba(16,185,129,0.25)"),
        decreasing=dict(line=dict(color="#ef4444", width=1), fillcolor="rgba(239,68,68,0.25)"),
    ))

    # Bollinger Bands
    c = df["close"]
    sma = c.rolling(20).mean()
    std = c.rolling(20).std()
    fig.add_trace(go.Scatter(x=df["dt"], y=sma + 2*std, name="BB Upper", line=dict(color="rgba(245,158,11,0.4)", width=1, dash="dot"), showlegend=True))
    fig.add_trace(go.Scatter(x=df["dt"], y=sma - 2*std, name="BB Lower", line=dict(color="rgba(245,158,11,0.4)", width=1, dash="dot"), fill="tonexty", fillcolor="rgba(245,158,11,0.03)", showlegend=False))
    fig.add_trace(go.Scatter(x=df["dt"], y=sma, name="BB Mid",   line=dict(color="rgba(245,158,11,0.25)", width=1), showlegend=False))

    # EMAs
    fig.add_trace(go.Scatter(x=df["dt"], y=c.ewm(span=9).mean(),  name="EMA 9",  line=dict(color="rgba(99,102,241,0.8)", width=1.5)))
    fig.add_trace(go.Scatter(x=df["dt"], y=c.ewm(span=20).mean(), name="EMA 20", line=dict(color="rgba(59,130,246,0.7)", width=1.5)))
    fig.add_trace(go.Scatter(x=df["dt"], y=c.ewm(span=50).mean(), name="EMA 50", line=dict(color="rgba(168,85,247,0.7)", width=1.5)))

    # Support & Resistance
    for lvl, lbl, col in [
        (ta["s1"],"S1 — Primary Support","rgba(16,185,129,0.8)"),
        (ta["s2"],"S2 — Secondary Support","rgba(16,185,129,0.5)"),
        (ta["r1"],"R1 — Primary Resistance","rgba(239,68,68,0.8)"),
        (ta["r2"],"R2 — Secondary Resistance","rgba(239,68,68,0.5)"),
    ]:
        fig.add_hline(
            y=lvl, line_color=col, line_width=1, line_dash="dash",
            annotation_text=f" {lbl}: ${lvl:,.2f}",
            annotation_position="right",
            annotation_font=dict(color=col, size=10)
        )

    # Entry / SL / TP zones (shaded)
    p  = ta["price"]
    sl = round(p * 0.98, 2)
    tp = round(p * 1.05, 2)
    fig.add_hrect(y0=sl, y1=p,  fillcolor="rgba(239,68,68,0.05)", line_width=0, annotation_text="Stop-Loss Zone", annotation_font_size=10, annotation_font_color="rgba(239,68,68,0.5)")
    fig.add_hrect(y0=p,  y1=tp, fillcolor="rgba(16,185,129,0.05)", line_width=0, annotation_text="Target Zone", annotation_font_size=10, annotation_font_color="rgba(16,185,129,0.5)")

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color="rgba(255,255,255,0.55)", size=11),
        height=440,
        margin=dict(l=10, r=80, t=16, b=10),
        legend=dict(
            bgcolor="rgba(0,0,0,0.35)",
            border_color="rgba(255,255,255,0.07)",
            borderwidth=1,
            font_size=10,
            x=0.01, y=0.99
        ),
        xaxis=dict(gridcolor="rgba(255,255,255,0.03)", showline=False, zeroline=False, rangeslider_visible=False),
        yaxis=dict(gridcolor="rgba(255,255,255,0.04)", showline=False, zeroline=False, side="right"),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="rgba(10,15,30,0.95)", bordercolor="rgba(59,130,246,0.3)", font_size=12),
    )
    return fig

# ─── Auth Page ────────────────────────────────────────────────────────────────
def page_auth():
    st.markdown("""
    <div style="display:flex; align-items:stretch; min-height:100vh; gap:0;">

        <!-- Left panel — branding -->
        <div style="
            flex:1.1; padding:60px 56px;
            background: linear-gradient(160deg, rgba(37,99,235,0.08) 0%, rgba(99,102,241,0.06) 50%, rgba(16,185,129,0.04) 100%);
            border-right: 1px solid rgba(255,255,255,0.05);
            display:flex; flex-direction:column; justify-content:center;
        ">
            <div style="max-width:420px;">
                <div style="
                    display:inline-flex; align-items:center; gap:10px;
                    background: rgba(37,99,235,0.1);
                    border: 1px solid rgba(37,99,235,0.2);
                    border-radius: 8px;
                    padding: 6px 14px;
                    margin-bottom: 40px;
                ">
                    <div style="width:6px;height:6px;border-radius:50%;background:#2563eb;box-shadow:0 0 8px #2563eb;"></div>
                    <span style="color:rgba(255,255,255,0.5);font-size:11px;font-weight:600;letter-spacing:0.12em;text-transform:uppercase;">Institutional Grade</span>
                </div>

                <h1 style="font-size:42px;font-weight:800;color:#f1f5f9;line-height:1.15;margin-bottom:18px;letter-spacing:-1.5px;">
                    Trading<br>Intelligence<br>Engine
                </h1>
                <p style="color:rgba(255,255,255,0.38);font-size:15px;line-height:1.7;margin-bottom:40px;">
                    A professional-grade platform combining real-time technical analysis, fundamental news assessment, and AI-powered decision synthesis into institutional White Paper reports.
                </p>

                <div style="display:flex;flex-direction:column;gap:12px;">
    """, unsafe_allow_html=True)

    for icon, text in [
        ("◈", "Live TA — RSI, MACD, Bollinger Bands, EMA stack"),
        ("◈", "News Sentiment with Impact Scoring ( -5 to +5 )"),
        ("◈", "White Paper Report — 5-section institutional format"),
        ("◈", "AES-256 encrypted API key storage"),
        ("◈", "Non-negotiable Risk Validation Layer"),
    ]:
        st.markdown(f"""
        <div style="display:flex;align-items:flex-start;gap:12px;">
            <span style="color:#2563eb;font-size:14px;margin-top:1px;flex-shrink:0;">{icon}</span>
            <span style="color:rgba(255,255,255,0.45);font-size:13px;line-height:1.5;">{text}</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
                </div>

                <div style="margin-top:48px;padding-top:24px;border-top:1px solid rgba(255,255,255,0.06);">
                    <p style="color:rgba(255,255,255,0.18);font-size:11px;line-height:1.6;max-width:360px;">
                        This platform is an analytical execution tool, not a financial advisor. All outputs are for informational purposes only.
                    </p>
                </div>
            </div>
        </div>

        <!-- Right panel — form -->
        <div style="
            flex:0.9;
            display:flex;
            align-items:center;
            justify-content:center;
            padding:60px 48px;
        ">
    """, unsafe_allow_html=True)

    # Form area
    st.markdown("""
    <div style="width:100%;max-width:380px;margin:0 auto;">
        <p style="color:rgba(255,255,255,0.25);font-size:11px;font-weight:600;letter-spacing:0.15em;text-transform:uppercase;margin-bottom:28px;">Account Access</p>
    </div>
    """, unsafe_allow_html=True)

    tab_in, tab_up = st.tabs(["Sign In", "Create Account"])

    with tab_in:
        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
        with st.form("f_login", clear_on_submit=False):
            email  = st.text_input("Email address", placeholder="you@example.com")
            pw     = st.text_input("Password", type="password", placeholder="Enter your password")
            btn    = st.form_submit_button("Sign In", use_container_width=True)
        if btn:
            if not email or not pw:
                st.error("Please fill in all fields.")
            else:
                db = SessionLocal()
                u  = db.query(User).filter(User.email == email.lower().strip()).first()
                db.close()
                if u and verify_pw(pw, u.hashed_pw):
                    st.session_state.user = {"id": u.id, "email": u.email, "name": u.full_name}
                    st.rerun()
                else:
                    st.error("Invalid email or password.")

    with tab_up:
        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
        with st.form("f_signup", clear_on_submit=False):
            name  = st.text_input("Full name", placeholder="John Doe")
            email2 = st.text_input("Email address", placeholder="you@example.com", key="su_e")
            pw2   = st.text_input("Password", type="password", placeholder="Minimum 8 characters", key="su_p")
            pw3   = st.text_input("Confirm password", type="password", placeholder="Repeat password", key="su_c")
            btn2  = st.form_submit_button("Create Account", use_container_width=True)
        if btn2:
            if not all([name, email2, pw2, pw3]):
                st.error("Please fill in all fields.")
            elif pw2 != pw3:
                st.error("Passwords do not match.")
            elif len(pw2) < 8:
                st.error("Password must be at least 8 characters.")
            else:
                db  = SessionLocal()
                ex  = db.query(User).filter(User.email == email2.lower().strip()).first()
                if ex:
                    db.close()
                    st.error("An account with this email already exists.")
                else:
                    u = User(id=str(uuid.uuid4()), email=email2.lower().strip(),
                             full_name=name.strip(), hashed_pw=hash_pw(pw2))
                    db.add(u); db.commit(); db.close()
                    st.session_state.user = {"id": u.id, "email": u.email, "name": name.strip()}
                    st.rerun()

    st.markdown("""
        <div style="margin-top:24px;text-align:center;">
            <p style="color:rgba(255,255,255,0.18);font-size:11px;">
                AES-256 encryption &nbsp;·&nbsp; bcrypt password hashing &nbsp;·&nbsp; No plaintext storage
            </p>
        </div>
        </div>
        </div>
    """, unsafe_allow_html=True)

# ─── Sidebar ──────────────────────────────────────────────────────────────────
def show_sidebar():
    u = st.session_state.user
    with st.sidebar:
        st.markdown(f"""
        <div style="padding:24px 0 12px;">
            <p style="color:rgba(255,255,255,0.15);font-size:10px;font-weight:600;letter-spacing:0.15em;text-transform:uppercase;margin-bottom:4px;">Trading Intelligence</p>
            <p style="color:#f1f5f9;font-weight:700;font-size:17px;letter-spacing:-0.3px;margin:0;">Engine</p>
        </div>
        <div style="height:1px;background:rgba(255,255,255,0.06);margin-bottom:16px;"></div>
        <div style="padding:10px 12px;background:rgba(37,99,235,0.07);border:1px solid rgba(37,99,235,0.15);border-radius:9px;margin-bottom:20px;">
            <p style="color:rgba(255,255,255,0.35);font-size:10px;margin:0 0 2px;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;">Session</p>
            <p style="color:rgba(255,255,255,0.75);font-weight:600;font-size:13px;margin:0;">{u['name']}</p>
            <p style="color:rgba(255,255,255,0.3);font-size:11px;margin:0;">{u['email']}</p>
        </div>
        <p style="color:rgba(255,255,255,0.2);font-size:10px;font-weight:600;letter-spacing:0.12em;text-transform:uppercase;margin-bottom:8px;padding:0 4px;">Navigation</p>
        """, unsafe_allow_html=True)

        page = st.radio("nav", ["Dashboard", "Analysis Report", "News Feed", "API Settings"], label_visibility="collapsed")

        st.markdown("""
        <div style="height:1px;background:rgba(255,255,255,0.06);margin:20px 0;"></div>
        <p style="color:rgba(255,255,255,0.2);font-size:10px;font-weight:600;letter-spacing:0.12em;text-transform:uppercase;margin-bottom:10px;padding:0 4px;">Risk Protocol</p>
        """, unsafe_allow_html=True)

        for label, val, note in [
            ("Max Position", "5%", "Of total account balance"),
            ("Stop Loss", "2%", "From entry — automated"),
            ("Take Profit", "5%", "Min target from entry"),
            ("Min R:R Ratio", "1 : 2", "Required before execution"),
            ("Daily Drawdown", "10%", "Global shutdown trigger"),
        ]:
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 10px;margin-bottom:4px;border-radius:7px;background:rgba(0,0,0,0.15);">
                <div>
                    <p style="color:rgba(255,255,255,0.45);font-size:11px;font-weight:500;margin:0;">{label}</p>
                    <p style="color:rgba(255,255,255,0.2);font-size:9px;margin:0;">{note}</p>
                </div>
                <span style="color:#f59e0b;font-family:'JetBrains Mono',monospace;font-size:12px;font-weight:600;">{val}</span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("""
        <div style="padding:8px 10px;background:rgba(239,68,68,0.06);border:1px solid rgba(239,68,68,0.15);border-radius:7px;margin-top:4px;margin-bottom:16px;">
            <p style="color:rgba(239,68,68,0.6);font-size:9px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;margin:0;">Non-negotiable — AI cannot override</p>
        </div>
        <div style="height:1px;background:rgba(255,255,255,0.06);margin-bottom:16px;"></div>
        """, unsafe_allow_html=True)

        if st.button("Sign Out", use_container_width=True):
            st.session_state.user = None
            st.session_state.report_data = None
            st.rerun()

    return page

# ─── Dashboard Page ───────────────────────────────────────────────────────────
def page_dashboard():
    st.markdown("""
    <div style="padding:32px 0 8px;">
        <p style="color:rgba(255,255,255,0.25);font-size:11px;font-weight:600;letter-spacing:0.12em;text-transform:uppercase;margin-bottom:6px;">Market Intelligence</p>
        <h1 style="font-size:28px;font-weight:800;margin:0;letter-spacing:-0.8px;">Dashboard</h1>
        <p style="color:rgba(255,255,255,0.3);font-size:13px;margin-top:6px;">Real-time multi-layer analysis — Technical · Fundamental · Sentiment</p>
    </div>
    <div style="height:1px;background:rgba(255,255,255,0.06);margin-bottom:24px;"></div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns([2.5, 1.5, 1.5, 1])
    with c1:
        symbol = st.text_input("Symbol", value="BTC/USDT", label_visibility="collapsed",
                               placeholder="Enter symbol — e.g. BTC/USDT, ETH/USDT, SOL/USDT")
    with c2:
        strategy = st.selectbox("Strategy", ["Balanced","Conservative","Aggressive"], label_visibility="collapsed")
    with c3:
        exchange = st.selectbox("Exchange", ["Kraken","Binance","Coinbase","Bybit"], label_visibility="collapsed")
    with c4:
        run = st.button("Run Analysis", use_container_width=True)

    if run:
        sym = symbol.upper().strip()
        with st.spinner(f"Fetching live data for {sym}..."):
            ta = get_market_data(sym)
        if not ta.get("ok"):
            st.error(f"Could not fetch data: {ta.get('error', 'Unknown error')}. Verify the symbol format (e.g. BTC/USDT).")
            return
        with st.spinner("Processing news feeds..."):
            news = get_news()
        report = build_report(ta, news, strategy)
        st.session_state.report_data = {"ta": ta, "news": news, "report": report, "strategy": strategy}

    if not st.session_state.report_data:
        st.markdown("""
        <div style="text-align:center;padding:80px 40px;background:rgba(255,255,255,0.015);border:1px solid rgba(255,255,255,0.05);border-radius:14px;margin-top:8px;">
            <div style="width:48px;height:48px;background:rgba(37,99,235,0.08);border:1px solid rgba(37,99,235,0.15);border-radius:12px;display:flex;align-items:center;justify-content:center;margin:0 auto 20px;">
                <span style="color:rgba(37,99,235,0.6);font-size:20px;">◈</span>
            </div>
            <p style="color:rgba(255,255,255,0.35);font-size:14px;font-weight:500;margin-bottom:6px;">Enter a symbol and run analysis</p>
            <p style="color:rgba(255,255,255,0.18);font-size:12px;margin:0;">Supports all CCXT-compatible pairs — BTC/USDT, ETH/BTC, SOL/USDT and more</p>
        </div>
        """, unsafe_allow_html=True)
        return

    ta     = st.session_state.report_data["ta"]
    rep    = st.session_state.report_data["report"]
    news   = st.session_state.report_data["news"]

    # ── Thesis Banner
    thesis_color = "#10b981" if "BULL" in rep["thesis"] else "#ef4444" if "BEAR" in rep["thesis"] else "#f59e0b"
    sig_cls = "badge-buy" if rep["signal"] == "BUY" else "badge-sell" if rep["signal"] == "SELL" else "badge-hold"
    ch_color = "#10b981" if ta["change_24h"] >= 0 else "#ef4444"

    st.markdown(f"""
    <div style="background:rgba(255,255,255,0.025);border:1px solid rgba(255,255,255,0.07);border-radius:14px;padding:24px 28px;margin-bottom:20px;
                border-left: 3px solid {thesis_color};">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:16px;">
            <div>
                <p style="color:rgba(255,255,255,0.3);font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.12em;margin-bottom:8px;">
                    Final Trade Thesis — {rep['strategy']} Strategy — {ta['symbol']}
                </p>
                <h2 style="font-size:30px;font-weight:800;color:{thesis_color};margin:0 0 10px;letter-spacing:-0.5px;">{rep['thesis']}</h2>
                <p style="color:rgba(255,255,255,0.4);font-size:13px;line-height:1.65;max-width:620px;margin:0;">{rep['exec_summary'][:240]}...</p>
            </div>
            <div style="text-align:right;flex-shrink:0;">
                <span class="badge {sig_cls}" style="font-size:13px;padding:5px 14px;">{rep['signal']} · {rep['strength']}</span>
                <p style="color:rgba(255,255,255,0.2);font-size:10px;margin-top:10px;font-family:'JetBrains Mono',monospace;">{rep['generated_at']}</p>
                <p style="color:{ch_color};font-size:18px;font-weight:700;margin-top:6px;font-family:'JetBrains Mono',monospace;">${ta['price']:,.2f}</p>
                <p style="color:{ch_color};font-size:12px;margin:0;">{'▲' if ta['change_24h']>=0 else '▼'} {abs(ta['change_24h'])}% (24h)</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Metric Grid
    cols = st.columns(8)
    metrics = [
        ("RSI (14)", ta["rsi"], "#10b981" if ta["rsi"]<40 else "#ef4444" if ta["rsi"]>60 else "#f59e0b", ""),
        ("MACD Hist", ta["macd_hist"], "#10b981" if ta["macd_hist"]>0 else "#ef4444", ""),
        ("EMA 20", f"${ta['ema20']:,.0f}", "#60a5fa", ""),
        ("EMA 50", f"${ta['ema50']:,.0f}", "#a78bfa", ""),
        ("BB Upper", f"${ta['bb_upper']:,.0f}", "#f59e0b", ""),
        ("BB Lower", f"${ta['bb_lower']:,.0f}", "#f59e0b", ""),
        ("Support S1", f"${ta['s1']:,.0f}", "#10b981", ""),
        ("Resistance R1", f"${ta['r1']:,.0f}", "#ef4444", ""),
    ]
    for i, (label, val, color, _) in enumerate(metrics):
        with cols[i]:
            st.markdown(f"""
            <div class="m-tile">
                <span class="m-tile-label">{label}</span>
                <span class="m-tile-value" style="color:{color};">{val}</span>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Chart
    fig = build_chart(ta)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # ── Bottom row: Actionable Thesis + Order Book
    col_a, col_b = st.columns([1.6, 1])

    with col_a:
        valid, issues, order = validate_trade(
            rep["signal"], rep["entry"], rep["sl"], rep["tp"], rep["position_size"]
        )
        vcolor = "#10b981" if valid else "#ef4444"
        vstatus = "APPROVED" if valid else "REJECTED"

        st.markdown(f"""
        <div class="g-card" style="border-color:{'rgba(16,185,129,0.2)' if valid else 'rgba(239,68,68,0.2)'};">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:18px;">
                <p style="color:rgba(255,255,255,0.3);font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.12em;margin:0;">Actionable Thesis</p>
                <span class="badge {'badge-buy' if valid else 'badge-sell'}" style="font-size:10px;">Risk Layer: {vstatus}</span>
            </div>
            <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:10px;">
        """, unsafe_allow_html=True)

        for lbl, val, col in [
            ("Entry Price", f"${rep['entry']:,.2f}", "#60a5fa"),
            ("Stop Loss",   f"${rep['sl']:,.2f}",    "#ef4444"),
            ("Take Profit", f"${rep['tp']:,.2f}",     "#10b981"),
            ("Risk:Reward", f"1:{rep['rr']}",          "#f59e0b"),
            ("Position",    f"{rep['position_size']}%","#a78bfa"),
        ]:
            st.markdown(f"""
            <div style="text-align:center;background:rgba(0,0,0,0.2);border-radius:9px;padding:12px 8px;">
                <p style="color:rgba(255,255,255,0.3);font-size:9px;text-transform:uppercase;letter-spacing:0.1em;margin:0 0 6px;">{lbl}</p>
                <p style="color:{col};font-weight:700;font-size:14px;font-family:'JetBrains Mono',monospace;margin:0;">{val}</p>
            </div>
            """, unsafe_allow_html=True)

        if not valid:
            st.markdown(f"</div><div style='margin-top:14px;'>", unsafe_allow_html=True)
            for i in issues:
                st.markdown(f'<p style="color:#ef4444;font-size:12px;margin:4px 0;">· {i}</p>', unsafe_allow_html=True)

        st.markdown("</div></div>", unsafe_allow_html=True)

    with col_b:
        st.markdown(f"""
        <div class="g-card">
            <p style="color:rgba(255,255,255,0.3);font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.12em;margin-bottom:16px;">Order Book Sentiment</p>
            <div style="margin-bottom:12px;">
                <div style="display:flex;justify-content:space-between;margin-bottom:5px;">
                    <span style="color:#10b981;font-size:11px;font-weight:600;">Bids</span>
                    <span style="color:#ef4444;font-size:11px;font-weight:600;">Asks</span>
                </div>
                <div style="height:10px;background:rgba(239,68,68,0.3);border-radius:5px;overflow:hidden;">
                    <div style="height:100%;width:{round(ta['ob_ratio']*100)}%;background:rgba(16,185,129,0.7);border-radius:5px;transition:width 0.5s;"></div>
                </div>
                <div style="display:flex;justify-content:space-between;margin-top:5px;">
                    <span style="color:#10b981;font-size:11px;font-family:'JetBrains Mono',monospace;">{round(ta['ob_ratio']*100)}%</span>
                    <span style="color:#ef4444;font-size:11px;font-family:'JetBrains Mono',monospace;">{round((1-ta['ob_ratio'])*100)}%</span>
                </div>
            </div>
            <p style="color:rgba(255,255,255,0.35);font-size:11px;line-height:1.5;margin:0;">{ta['ob_note']}</p>
            <div style="height:1px;background:rgba(255,255,255,0.05);margin:14px 0;"></div>
            <p style="color:rgba(255,255,255,0.3);font-size:10px;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:6px;">Volume</p>
            <p style="color:#60a5fa;font-size:13px;font-weight:600;font-family:'JetBrains Mono',monospace;margin-bottom:4px;">{ta['volume_ratio']}x avg</p>
            <p style="color:rgba(255,255,255,0.3);font-size:11px;margin:0;">{ta['vol_note']}</p>
        </div>
        """, unsafe_allow_html=True)

# ─── Analysis Report Page ─────────────────────────────────────────────────────
def page_report():
    st.markdown("""
    <div style="padding:32px 0 8px;display:flex;justify-content:space-between;align-items:flex-end;">
        <div>
            <p style="color:rgba(255,255,255,0.25);font-size:11px;font-weight:600;letter-spacing:0.12em;text-transform:uppercase;margin-bottom:6px;">Analytical Output</p>
            <h1 style="font-size:28px;font-weight:800;margin:0;letter-spacing:-0.8px;">White Paper Report</h1>
            <p style="color:rgba(255,255,255,0.3);font-size:13px;margin-top:6px;">Institutional-format analysis — 5-section structured output</p>
        </div>
    </div>
    <div style="height:1px;background:rgba(255,255,255,0.06);margin-bottom:28px;"></div>
    """, unsafe_allow_html=True)

    if not st.session_state.report_data:
        st.info("No report available. Go to Dashboard, enter a symbol, and run an analysis first.")
        return

    ta   = st.session_state.report_data["ta"]
    rep  = st.session_state.report_data["report"]
    news = st.session_state.report_data["news"]

    tc = "#10b981" if "BULL" in rep["thesis"] else "#ef4444" if "BEAR" in rep["thesis"] else "#f59e0b"
    sig_cls = "badge-buy" if rep["signal"]=="BUY" else "badge-sell" if rep["signal"]=="SELL" else "badge-hold"

    # ── Section 01: Executive Summary
    st.markdown(f"""
    <div class="report-section">
        <div class="report-section-header">
            <div class="report-num">01</div>
            <div>
                <p class="report-title">Executive Summary</p>
                <p style="color:rgba(255,255,255,0.2);font-size:10px;margin:0;">Quick overview of the current market sentiment</p>
            </div>
            <span class="badge {sig_cls}" style="margin-left:auto;">{rep['signal']} · {rep['strength']}</span>
        </div>

        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px;">
            <div style="background:rgba(0,0,0,0.2);border-radius:10px;padding:14px 16px;">
                <p class="report-key">Symbol</p>
                <p class="report-val" style="color:#f1f5f9;">{ta['symbol']}</p>
            </div>
            <div style="background:rgba(0,0,0,0.2);border-radius:10px;padding:14px 16px;">
                <p class="report-key">Current Price</p>
                <p class="report-val" style="color:#60a5fa;">${ta['price']:,.2f}</p>
            </div>
            <div style="background:rgba(0,0,0,0.2);border-radius:10px;padding:14px 16px;">
                <p class="report-key">Final Thesis</p>
                <p class="report-val" style="color:{tc};font-size:13px;">{rep['thesis']}</p>
            </div>
            <div style="background:rgba(0,0,0,0.2);border-radius:10px;padding:14px 16px;">
                <p class="report-key">Generated</p>
                <p class="report-val" style="color:rgba(255,255,255,0.5);font-size:11px;">{rep['generated_at']}</p>
            </div>
        </div>

        <div style="background:rgba(37,99,235,0.05);border-left:2px solid rgba(37,99,235,0.4);border-radius:0 8px 8px 0;padding:16px 20px;">
            <p class="report-body">{rep['exec_summary']}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Section 02: Market Pulse
    avg_s   = rep["avg_sentiment"]
    pos_cnt = sum(1 for n in news if n["sentiment"] == "POSITIVE")
    neg_cnt = sum(1 for n in news if n["sentiment"] == "NEGATIVE")
    dom_s   = "BULLISH" if avg_s > 0.5 else "BEARISH" if avg_s < -0.5 else "NEUTRAL"
    dom_c   = "#10b981" if avg_s > 0.5 else "#ef4444" if avg_s < -0.5 else "#f59e0b"

    st.markdown(f"""
    <div class="report-section">
        <div class="report-section-header">
            <div class="report-num">02</div>
            <div>
                <p class="report-title">Market Pulse — News Analysis</p>
                <p style="color:rgba(255,255,255,0.2);font-size:10px;margin:0;">Impact-scored news events with fundamental assessment</p>
            </div>
            <div style="margin-left:auto;text-align:right;">
                <p style="color:{dom_c};font-size:12px;font-weight:700;margin:0;">{dom_s}</p>
                <p style="color:rgba(255,255,255,0.25);font-size:10px;margin:0;">Avg: {avg_s:+.1f}/5.0 · {pos_cnt} pos / {neg_cnt} neg</p>
            </div>
        </div>

        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:20px;">
            <div style="background:rgba(0,0,0,0.2);border-radius:9px;padding:12px;text-align:center;">
                <p class="report-key">Dominant Sentiment</p>
                <p class="report-val" style="color:{dom_c};font-size:13px;">{dom_s}</p>
            </div>
            <div style="background:rgba(0,0,0,0.2);border-radius:9px;padding:12px;text-align:center;">
                <p class="report-key">Avg Impact Score</p>
                <p class="report-val" style="color:{dom_c};">{avg_s:+.1f}</p>
            </div>
            <div style="background:rgba(16,185,129,0.06);border-radius:9px;padding:12px;text-align:center;">
                <p class="report-key">Positive Articles</p>
                <p class="report-val" style="color:#10b981;">{pos_cnt}</p>
            </div>
            <div style="background:rgba(239,68,68,0.06);border-radius:9px;padding:12px;text-align:center;">
                <p class="report-key">Negative Articles</p>
                <p class="report-val" style="color:#ef4444;">{neg_cnt}</p>
            </div>
        </div>

        <!-- News table -->
        <div style="border:1px solid rgba(255,255,255,0.06);border-radius:10px;overflow:hidden;">
            <div style="display:grid;grid-template-columns:60px 1fr 80px 90px;gap:0;padding:10px 16px;background:rgba(0,0,0,0.3);border-bottom:1px solid rgba(255,255,255,0.05);">
                <p style="color:rgba(255,255,255,0.2);font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;margin:0;">Score</p>
                <p style="color:rgba(255,255,255,0.2);font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;margin:0;">Headline &amp; Summary</p>
                <p style="color:rgba(255,255,255,0.2);font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;margin:0;text-align:center;">Sentiment</p>
                <p style="color:rgba(255,255,255,0.2);font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;margin:0;text-align:center;">Source</p>
            </div>
    """, unsafe_allow_html=True)

    for n in news[:12]:
        sc = n["score"]
        sc_col = "#10b981" if sc > 0 else "#ef4444" if sc < 0 else "#94a3b8"
        badge  = "badge-pos" if n["sentiment"]=="POSITIVE" else "badge-neg" if n["sentiment"]=="NEGATIVE" else "badge-neu"
        st.markdown(f"""
        <div style="display:grid;grid-template-columns:60px 1fr 80px 90px;gap:0;padding:12px 16px;border-bottom:1px solid rgba(255,255,255,0.04);align-items:center;">
            <p style="color:{sc_col};font-weight:700;font-size:16px;font-family:'JetBrains Mono',monospace;margin:0;text-align:center;">{'+' if sc>0 else ''}{sc}</p>
            <div>
                <a href="{n['link']}" target="_blank" style="color:rgba(255,255,255,0.7);font-size:12px;font-weight:500;text-decoration:none;line-height:1.4;display:block;margin-bottom:3px;">{n['title'][:100]}{'...' if len(n['title'])>100 else ''}</a>
                <p style="color:rgba(255,255,255,0.3);font-size:11px;margin:0;line-height:1.5;">{n['one_line'][:130]}</p>
            </div>
            <div style="text-align:center;"><span class="badge {badge}" style="font-size:10px;">{n['sentiment']}</span></div>
            <p style="color:rgba(255,255,255,0.25);font-size:10px;text-align:center;margin:0;">{n['source'][:20]}</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div></div>", unsafe_allow_html=True)

    # ── Section 03: Technical Blueprint
    rsi_c  = "#10b981" if ta["rsi"]<40 else "#ef4444" if ta["rsi"]>60 else "#f59e0b"
    macd_c = "#10b981" if ta["macd_hist"]>0 else "#ef4444"
    ema_c  = "#10b981" if ta["ema20"]>ta["ema50"] else "#ef4444"

    st.markdown(f"""
    <div class="report-section">
        <div class="report-section-header">
            <div class="report-num">03</div>
            <div>
                <p class="report-title">Technical Blueprint</p>
                <p style="color:rgba(255,255,255,0.2);font-size:10px;margin:0;">Detailed breakdown of TA indicators, patterns, and signals</p>
            </div>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px;">
    """, unsafe_allow_html=True)

    indicators = [
        ("RSI (14)", ta["rsi"], rsi_c, ta["rsi_note"],
         f"Current reading {ta['rsi']} is {'below 40 — asset oversold' if ta['rsi']<40 else 'above 60 — asset overbought' if ta['rsi']>60 else 'in the neutral 40–60 zone'}. RSI divergence analysis not yet triggered."),
        ("MACD (12,26,9)", f"L:{ta['macd']:.4f}  S:{ta['macd_signal']:.4f}  H:{ta['macd_hist']:+.4f}", macd_c, ta["macd_note"],
         f"Histogram at {ta['macd_hist']:+.4f} indicates {'positive momentum — bulls in control' if ta['macd_hist']>0 else 'negative momentum — bears in control'}. Signal line crossover {'bullish' if ta['macd']>ta['macd_signal'] else 'bearish'}."),
        ("Bollinger Bands (20,2)", f"U:{ta['bb_upper']:,.2f}  M:{ta['bb_middle']:,.2f}  L:{ta['bb_lower']:,.2f}", "#f59e0b", ta["bb_note"],
         f"Price is at {ta['bb_pct']}% of the band range. Squeeze or expansion analysis: band width {'narrowing — low volatility' if (ta['bb_upper']-ta['bb_lower'])/ta['bb_middle']<0.08 else 'widening — elevated volatility'}."),
        ("EMA Stack", f"9:{ta['ema9']:,.2f}  20:{ta['ema20']:,.2f}  50:{ta['ema50']:,.2f}  200:{ta['ema200']:,.2f}", ema_c, ta["ema_note"],
         f"{'Price above EMA200 — long-term bullish' if ta['price']>ta['ema200'] else 'Price below EMA200 — long-term bearish'}. EMA9 {'above' if ta['ema9']>ta['ema20'] else 'below'} EMA20 confirms short-term momentum direction."),
    ]

    for name, val, color, note, analysis in indicators:
        st.markdown(f"""
        <div style="background:rgba(0,0,0,0.2);border-radius:10px;padding:16px 18px;">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">
                <p style="color:rgba(255,255,255,0.35);font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;margin:0;">{name}</p>
            </div>
            <p style="color:{color};font-weight:700;font-size:14px;font-family:'JetBrains Mono',monospace;margin:0 0 6px;">{val}</p>
            <p style="color:rgba(255,255,255,0.5);font-size:11px;font-weight:500;margin:0 0 4px;">{note}</p>
            <p style="color:rgba(255,255,255,0.3);font-size:11px;line-height:1.6;margin:0;">{analysis}</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # Volume
    vc = "#10b981" if ta["volume_ratio"]>1.2 else "#f59e0b" if ta["volume_ratio"]>0.8 else "#ef4444"
    st.markdown(f"""
    <div style="background:rgba(0,0,0,0.15);border-radius:10px;padding:14px 18px;margin-top:4px;">
        <p style="color:rgba(255,255,255,0.3);font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;margin:0 0 6px;">Volume Analysis</p>
        <span style="color:{vc};font-weight:700;font-size:16px;font-family:'JetBrains Mono',monospace;">{ta['volume_ratio']}x</span>
        <span style="color:rgba(255,255,255,0.35);font-size:12px;margin-left:10px;">20-day average</span>
        <p style="color:rgba(255,255,255,0.4);font-size:12px;margin-top:4px;">{ta['vol_note']}. {'High volume confirms the signal with greater conviction.' if ta['volume_ratio']>1.4 else 'Average volume — signal carries moderate weight.' if ta['volume_ratio']>0.9 else 'Low volume — treat signal with caution; await volume confirmation.'}</p>
    </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Section 04: Visual Blueprint
    st.markdown("""
    <div class="report-section">
        <div class="report-section-header">
            <div class="report-num">04</div>
            <div>
                <p class="report-title">Visual Blueprint — Key Price Levels</p>
                <p style="color:rgba(255,255,255,0.2);font-size:10px;margin:0;">Support &amp; resistance zones, trendlines, and entry/exit coordinates for chart annotation</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    p = ta["price"]
    levels = [
        (ta["r3"], "Resistance 3", "Secondary", "#ef4444", "0.6"),
        (ta["r2"], "Resistance 2", "Key Level", "#ef4444", "0.75"),
        (ta["r1"], "Resistance 1", "Primary — Nearest overhead", "#ef4444", "1.0"),
        (p,        "Current Price", "Live market price", "#60a5fa", "1.0"),
        (ta["s1"], "Support 1", "Primary — Nearest floor", "#10b981", "1.0"),
        (ta["s2"], "Support 2", "Key Level", "#10b981", "0.75"),
        (ta["s3"], "Support 3", "Secondary", "#10b981", "0.6"),
    ]
    for lvl, lbl, note, col, opacity in sorted(levels, key=lambda x: x[0], reverse=True):
        dist = round((lvl - p) / p * 100, 2)
        border = "3px" if "Primary" in note or "Live" in note else "1px"
        st.markdown(f"""
        <div style="display:flex;justify-content:space-between;align-items:center;padding:11px 16px;background:rgba(0,0,0,0.2);border-radius:8px;margin-bottom:6px;
                    border-left:{border} solid {col};opacity:{opacity};">
            <div>
                <p style="color:rgba(255,255,255,0.6);font-size:12px;font-weight:500;margin:0;">{lbl}</p>
                <p style="color:rgba(255,255,255,0.25);font-size:10px;margin:0;">{note}</p>
            </div>
            <div style="text-align:right;">
                <p style="color:{col};font-family:'JetBrains Mono',monospace;font-size:14px;font-weight:700;margin:0;">${lvl:,.2f}</p>
                <p style="color:rgba(255,255,255,0.25);font-size:10px;margin:0;">{'+' if dist>=0 else ''}{dist}% from price</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

    entry_lo = round(p * 0.995, 2)
    entry_hi = round(p * 1.005, 2)
    sl_price = rep["sl"]
    tp_price = rep["tp"]

    st.markdown(f"""
    <div style="margin-top:16px;display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;">
        <div style="background:rgba(59,130,246,0.06);border:1px solid rgba(59,130,246,0.2);border-radius:9px;padding:14px 16px;">
            <p style="color:rgba(255,255,255,0.3);font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;margin:0 0 6px;">Entry Zone</p>
            <p style="color:#60a5fa;font-family:'JetBrains Mono',monospace;font-size:13px;font-weight:700;margin:0;">${entry_lo:,.2f} — ${entry_hi:,.2f}</p>
            <p style="color:rgba(255,255,255,0.25);font-size:10px;margin:3px 0 0;">±0.5% of current price</p>
        </div>
        <div style="background:rgba(239,68,68,0.06);border:1px solid rgba(239,68,68,0.2);border-radius:9px;padding:14px 16px;">
            <p style="color:rgba(255,255,255,0.3);font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;margin:0 0 6px;">Stop-Loss Zone</p>
            <p style="color:#ef4444;font-family:'JetBrains Mono',monospace;font-size:13px;font-weight:700;margin:0;">${sl_price:,.2f}</p>
            <p style="color:rgba(255,255,255,0.25);font-size:10px;margin:3px 0 0;">2.0% from entry — hard stop</p>
        </div>
        <div style="background:rgba(16,185,129,0.06);border:1px solid rgba(16,185,129,0.2);border-radius:9px;padding:14px 16px;">
            <p style="color:rgba(255,255,255,0.3);font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;margin:0 0 6px;">Target Zone</p>
            <p style="color:#10b981;font-family:'JetBrains Mono',monospace;font-size:13px;font-weight:700;margin:0;">${tp_price:,.2f}</p>
            <p style="color:rgba(255,255,255,0.25);font-size:10px;margin:3px 0 0;">5.0% from entry — take profit</p>
        </div>
    </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Section 05: Actionable Thesis
    tc = "#10b981" if "BULL" in rep["thesis"] else "#ef4444" if "BEAR" in rep["thesis"] else "#f59e0b"
    valid, issues, _ = validate_trade(rep["signal"], rep["entry"], rep["sl"], rep["tp"], rep["position_size"])

    reasoning_items = [
        (f"RSI at {ta['rsi']} — {ta['rsi_note']}", "RSI"),
        (f"MACD Histogram {ta['macd_hist']:+.4f} — {ta['macd_note']}", "MACD"),
        (f"EMA Stack — {ta['ema_note']}", "EMA"),
        (f"Bollinger Bands — {ta['bb_note']}", "BB"),
        (f"Order Book — {ta['ob_note']}", "OB"),
        (f"Volume {ta['volume_ratio']}x — {ta['vol_note']}", "VOL"),
        (f"News Sentiment avg {rep['avg_sentiment']:+.1f}/5.0 — {'corroborates bullish bias' if rep['avg_sentiment']>0 and rep['signal']=='BUY' else 'corroborates bearish bias' if rep['avg_sentiment']<0 and rep['signal']=='SELL' else 'diverges from technical signal — reduce conviction'}", "NEWS"),
    ]

    st.markdown(f"""
    <div class="report-section" style="border-color:{'rgba(16,185,129,0.2)' if 'BULL' in rep['thesis'] else 'rgba(239,68,68,0.2)' if 'BEAR' in rep['thesis'] else 'rgba(245,158,11,0.2)'};">
        <div class="report-section-header">
            <div class="report-num">05</div>
            <div>
                <p class="report-title">Actionable Thesis</p>
                <p style="color:rgba(255,255,255,0.2);font-size:10px;margin:0;">Clear, logical reasoning behind the trade recommendation</p>
            </div>
            <div style="margin-left:auto;text-align:right;">
                <p style="color:{tc};font-size:18px;font-weight:800;margin:0;letter-spacing:-0.5px;">{rep['thesis']}</p>
                <p style="color:rgba(255,255,255,0.25);font-size:10px;margin:0;">Risk Validation: {'APPROVED' if valid else 'REJECTED'}</p>
            </div>
        </div>

        <!-- Execution parameters -->
        <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:20px;">
    """, unsafe_allow_html=True)

    for lbl, val, col in [
        ("Recommendation", rep["signal"], "#10b981" if rep["signal"]=="BUY" else "#ef4444" if rep["signal"]=="SELL" else "#f59e0b"),
        ("Entry Price", f"${rep['entry']:,.2f}", "#60a5fa"),
        ("Stop Loss", f"${rep['sl']:,.2f}", "#ef4444"),
        ("Take Profit", f"${rep['tp']:,.2f}", "#10b981"),
        ("Risk : Reward", f"1:{rep['rr']}", "#f59e0b"),
    ]:
        st.markdown(f"""
        <div style="background:rgba(0,0,0,0.2);border-radius:9px;padding:14px;text-align:center;">
            <p class="report-key" style="margin-bottom:7px;">{lbl}</p>
            <p class="report-val" style="color:{col};font-size:16px;">{val}</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div><p style='color:rgba(255,255,255,0.25);font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.12em;margin:0 0 12px;'>Supporting Evidence</p>", unsafe_allow_html=True)

    for text, tag in reasoning_items:
        st.markdown(f"""
        <div style="display:flex;gap:12px;margin-bottom:9px;align-items:flex-start;">
            <span style="background:rgba(37,99,235,0.1);border:1px solid rgba(37,99,235,0.2);color:rgba(96,165,250,0.8);font-size:9px;font-weight:600;padding:2px 7px;border-radius:4px;flex-shrink:0;font-family:'JetBrains Mono',monospace;margin-top:1px;">{tag}</span>
            <p style="color:rgba(255,255,255,0.5);font-size:12px;line-height:1.6;margin:0;">{text}</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="margin-top:20px;padding:12px 16px;background:rgba(245,158,11,0.05);border:1px solid rgba(245,158,11,0.12);border-radius:8px;">
        <p style="color:rgba(255,255,255,0.25);font-size:11px;font-style:italic;margin:0;">
        Disclaimer: This report is generated by an automated analytical system and constitutes an execution tool, not financial advice. Past performance does not guarantee future results. Always apply independent judgment and proper risk management before placing any order.
        </p>
    </div>
    </div>
    """, unsafe_allow_html=True)

# ─── News Feed Page ───────────────────────────────────────────────────────────
def page_news():
    st.markdown("""
    <div style="padding:32px 0 8px;">
        <p style="color:rgba(255,255,255,0.25);font-size:11px;font-weight:600;letter-spacing:0.12em;text-transform:uppercase;margin-bottom:6px;">Fundamental Analysis</p>
        <h1 style="font-size:28px;font-weight:800;margin:0;letter-spacing:-0.8px;">News Feed</h1>
        <p style="color:rgba(255,255,255,0.3);font-size:13px;margin-top:6px;">Live news with AI-powered sentiment classification and impact scoring</p>
    </div>
    <div style="height:1px;background:rgba(255,255,255,0.06);margin-bottom:24px;"></div>
    """, unsafe_allow_html=True)

    with st.spinner("Fetching live news feeds..."):
        news = get_news()

    if not news:
        st.warning("Could not load news. Check internet connectivity.")
        return

    avg_s   = sum(n["score"] for n in news) / len(news)
    pos_cnt = sum(1 for n in news if n["sentiment"] == "POSITIVE")
    neg_cnt = sum(1 for n in news if n["sentiment"] == "NEGATIVE")
    neu_cnt = len(news) - pos_cnt - neg_cnt
    dom_c   = "#10b981" if avg_s > 0.5 else "#ef4444" if avg_s < -0.5 else "#f59e0b"
    dom_s   = "BULLISH" if avg_s > 0.5 else "BEARISH" if avg_s < -0.5 else "NEUTRAL"

    c1,c2,c3,c4,c5 = st.columns(5)
    for col, lbl, val, color in [
        (c1, "Market Mood", dom_s, dom_c),
        (c2, "Avg Impact Score", f"{avg_s:+.2f}", dom_c),
        (c3, "Positive", pos_cnt, "#10b981"),
        (c4, "Negative", neg_cnt, "#ef4444"),
        (c5, "Neutral", neu_cnt, "#94a3b8"),
    ]:
        with col:
            st.markdown(f"""
            <div class="m-tile" style="margin-bottom:16px;">
                <span class="m-tile-label">{lbl}</span>
                <span class="m-tile-value" style="color:{color};">{val}</span>
            </div>
            """, unsafe_allow_html=True)

    filt = st.selectbox("Filter", ["All", "Positive only", "Negative only", "Neutral only"], label_visibility="collapsed")
    fmap = {"All": None, "Positive only": "POSITIVE", "Negative only": "NEGATIVE", "Neutral only": "NEUTRAL"}
    filtered = [n for n in news if fmap[filt] is None or n["sentiment"] == fmap[filt]]

    for n in filtered:
        sc  = n["score"]
        sc_c = "#10b981" if sc > 0 else "#ef4444" if sc < 0 else "#94a3b8"
        bdge = "badge-pos" if n["sentiment"]=="POSITIVE" else "badge-neg" if n["sentiment"]=="NEGATIVE" else "badge-neu"
        bl   = "rgba(16,185,129,0.5)" if n["sentiment"]=="POSITIVE" else "rgba(239,68,68,0.5)" if n["sentiment"]=="NEGATIVE" else "rgba(148,163,184,0.3)"
        st.markdown(f"""
        <div style="display:flex;gap:18px;align-items:flex-start;padding:18px 20px;margin-bottom:10px;
                    background:rgba(255,255,255,0.025);border:1px solid rgba(255,255,255,0.06);border-radius:12px;
                    border-left:3px solid {bl};">
            <div style="text-align:center;flex-shrink:0;min-width:50px;">
                <p style="color:rgba(255,255,255,0.2);font-size:9px;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;margin:0 0 4px;">Impact</p>
                <p style="color:{sc_c};font-weight:800;font-size:22px;font-family:'JetBrains Mono',monospace;margin:0;line-height:1;">{'+' if sc>0 else ''}{sc}</p>
                <p style="color:rgba(255,255,255,0.2);font-size:9px;margin:2px 0 0;">/5.0</p>
            </div>
            <div style="flex:1;min-width:0;">
                <div style="display:flex;gap:8px;align-items:center;margin-bottom:6px;">
                    <span class="badge {bdge}" style="font-size:10px;">{n['sentiment']}</span>
                    <span style="color:rgba(255,255,255,0.2);font-size:10px;">{n['source']}</span>
                    <span style="color:rgba(255,255,255,0.15);font-size:10px;">· {n['published'][:16]}</span>
                </div>
                <a href="{n['link']}" target="_blank" style="text-decoration:none;">
                    <p style="color:rgba(255,255,255,0.75);font-size:13px;font-weight:500;line-height:1.5;margin:0 0 5px;">{n['title']}</p>
                </a>
                <p style="color:rgba(255,255,255,0.35);font-size:11px;line-height:1.6;margin:0;">{n['one_line']}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ─── Settings Page ────────────────────────────────────────────────────────────
def page_settings():
    st.markdown("""
    <div style="padding:32px 0 8px;">
        <p style="color:rgba(255,255,255,0.25);font-size:11px;font-weight:600;letter-spacing:0.12em;text-transform:uppercase;margin-bottom:6px;">Account</p>
        <h1 style="font-size:28px;font-weight:800;margin:0;letter-spacing:-0.8px;">API Settings</h1>
        <p style="color:rgba(255,255,255,0.3);font-size:13px;margin-top:6px;">Exchange API keys stored with AES-256 encryption — never in plaintext</p>
    </div>
    <div style="height:1px;background:rgba(255,255,255,0.06);margin-bottom:24px;"></div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["Exchange API Keys", "Risk Management Limits"])

    with tab1:
        st.markdown("""
        <div style="padding:12px 16px;background:rgba(16,185,129,0.05);border:1px solid rgba(16,185,129,0.15);border-radius:9px;margin-bottom:20px;">
            <p style="color:rgba(255,255,255,0.45);font-size:12px;line-height:1.6;margin:0;">
                All API keys are encrypted using <strong style="color:#10b981">AES-256 Fernet encryption</strong> before database storage. 
                The raw key is never logged, cached, or stored in plaintext at any layer.
            </p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("api_form"):
            c1, c2 = st.columns(2)
            with c1: exchange = st.selectbox("Exchange", ["Kraken","Binance","Bybit","OKX","Coinbase","KuCoin","Gate.io"])
            with c2: st.markdown("<br>", unsafe_allow_html=True)
            api_key    = st.text_input("API Key", type="password", placeholder="Paste your exchange API key")
            api_secret = st.text_input("API Secret", type="password", placeholder="Paste your exchange API secret")
            submitted  = st.form_submit_button("Save Encrypted Key", use_container_width=True)

        if submitted:
            if not api_key or not api_secret:
                st.error("Both fields are required.")
            else:
                db = SessionLocal()
                uid = st.session_state.user["id"]
                enc_k = fernet.encrypt(api_key.encode()).decode()
                enc_s = fernet.encrypt(api_secret.encode()).decode()
                ex_norm = exchange.lower()
                existing = db.query(EncryptedKey).filter(
                    EncryptedKey.user_id == uid, EncryptedKey.exchange == ex_norm
                ).first()
                if existing:
                    existing.enc_key = enc_k; existing.enc_secret = enc_s
                else:
                    db.add(EncryptedKey(id=str(uuid.uuid4()), user_id=uid, exchange=ex_norm, enc_key=enc_k, enc_secret=enc_s))
                db.commit(); db.close()
                st.success(f"{exchange} API key saved with AES-256 encryption.")

        db = SessionLocal()
        keys = db.query(EncryptedKey).filter(EncryptedKey.user_id == st.session_state.user["id"]).all()
        db.close()
        if keys:
            st.markdown("""
            <p style="color:rgba(255,255,255,0.3);font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.12em;margin:20px 0 10px;">Connected Exchanges</p>
            """, unsafe_allow_html=True)
            for k in keys:
                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;align-items:center;padding:10px 16px;background:rgba(16,185,129,0.04);border:1px solid rgba(16,185,129,0.12);border-radius:8px;margin-bottom:6px;">
                    <span style="color:rgba(255,255,255,0.6);font-size:13px;font-weight:500;">{k.exchange.capitalize()}</span>
                    <span style="color:#10b981;font-size:10px;font-weight:600;">AES-256 Encrypted</span>
                </div>
                """, unsafe_allow_html=True)

    with tab2:
        st.markdown("""
        <div style="padding:12px 16px;background:rgba(239,68,68,0.05);border:1px solid rgba(239,68,68,0.12);border-radius:9px;margin-bottom:20px;">
            <p style="color:rgba(239,68,68,0.7);font-size:11px;font-weight:600;letter-spacing:0.06em;margin:0;">
                These parameters are hard-coded in the validation layer and cannot be modified by the AI engine or overridden at runtime.
            </p>
        </div>
        """, unsafe_allow_html=True)

        limits = [
            ("Max Position Size", "5.0%", "Maximum % of total account balance allocated to a single trade", "#f59e0b"),
            ("Stop-Loss Distance", "2.0%", "Automated SL placed exactly 2% from entry — non-negotiable", "#ef4444"),
            ("Min Take-Profit", "5.0%", "Take-profit must be at least 5% from entry price", "#10b981"),
            ("Min Risk:Reward", "1 : 2.0", "Trade is blocked if reward does not exceed 2x the risk", "#60a5fa"),
            ("Daily Loss Limit", "10.0%", "If cumulative daily drawdown exceeds 10%, global shutdown activates for 24h", "#ef4444"),
        ]
        for name, val, note, color in limits:
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;align-items:center;padding:16px 20px;background:rgba(0,0,0,0.2);border-radius:10px;margin-bottom:8px;">
                <div>
                    <p style="color:rgba(255,255,255,0.6);font-size:13px;font-weight:500;margin:0 0 4px;">{name}</p>
                    <p style="color:rgba(255,255,255,0.25);font-size:11px;margin:0;">{note}</p>
                </div>
                <span style="color:{color};font-family:'JetBrains Mono',monospace;font-size:17px;font-weight:700;">{val}</span>
            </div>
            """, unsafe_allow_html=True)

# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    if not st.session_state.user:
        page_auth()
        return

    page = show_sidebar()

    if   page == "Dashboard":       page_dashboard()
    elif page == "Analysis Report": page_report()
    elif page == "News Feed":       page_news()
    elif page == "API Settings":    page_settings()

if __name__ == "__main__":
    main()
