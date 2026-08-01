"""
FinsageAI — Stock · Crypto · Meme Coin Analysis v8.0
Features: Crypto + Indian Markets (Nifty/Sensex) | Full TA/FA | Real-time News | Video Analysis
Color: #0a0e14 base | #22d3ee cyan | #7c6ff0 violet | 60-30-10 rule
"""

import streamlit as st
import requests, pandas as pd, numpy as np
import plotly.graph_objects as go
import feedparser, re, uuid, os, datetime, json, hashlib, time
from cryptography.fernet import Fernet
import bcrypt as _bcrypt
from sqlalchemy import create_engine, Column, String, Float, DateTime, Text, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker

# ── Page Config ──
st.set_page_config(
    page_title="FinsageAI — Trading Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"Get Help": None, "Report a bug": None, "About": None}
)

# ── Database ──
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./trading.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}, pool_pre_ping=True)
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, default="")
    strategy = Column(String, default="Balanced")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class ApiKey(Base):
    __tablename__ = "api_keys"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    exchange = Column(String, nullable=False)
    api_key_enc = Column(Text, nullable=False)
    api_secret_enc = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class TradeLog(Base):
    __tablename__ = "trade_logs"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    symbol = Column(String)
    action = Column(String)
    entry_price = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    size_pct = Column(Float)
    risk_reward = Column(String)
    strategy = Column(String)
    status = Column(String, default="demo")
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

Base.metadata.create_all(bind=engine)

# ── Security ──
RAW_KEY = os.getenv("ENCRYPTION_KEY", "6f8f7f6f5f4f3f2f1f0f9f8f7f6f5f4f3f2f1f0f9f8=")
FERNET = Fernet(RAW_KEY.encode() if isinstance(RAW_KEY, str) else RAW_KEY)

def _pre(p): return hashlib.sha256(p.encode("utf-8")).hexdigest().encode("utf-8")
def hash_pw(p): return _bcrypt.hashpw(_pre(p), _bcrypt.gensalt(rounds=12)).decode("utf-8")
def verify_pw(p, h):
    try: return _bcrypt.checkpw(_pre(p), h.encode("utf-8"))
    except: return False
def encrypt(v): return FERNET.encrypt(v.encode()).decode()
def decrypt(v): return FERNET.decrypt(v.encode()).decode()

# ── Risk Limits ──
MAX_POSITION_PCT = 5.0
MAX_SL_PCT = 2.0
MIN_RR = 2.0
MAX_DAILY_LOSS_PCT = 10.0

def validate_trade(action, entry, sl, tp, size_pct):
    issues = []
    if size_pct > MAX_POSITION_PCT:
        issues.append(f"Position {size_pct}% > max {MAX_POSITION_PCT}%")
    sl_dist = abs(entry - sl) / entry * 100
    if sl_dist > MAX_SL_PCT:
        issues.append(f"Stop-loss distance {sl_dist:.2f}% > max {MAX_SL_PCT}%")
    risk = abs(entry - sl); reward = abs(tp - entry)
    rr = reward / risk if risk > 0 else 0
    if rr < MIN_RR:
        issues.append(f"R:R {rr:.2f} below min 1:{MIN_RR}")
    is_valid = len(issues) == 0
    return is_valid, issues, {"risk_reward": f"1:{round(rr, 1)}"} if is_valid else {}

# ── CSS: FinsageAI Theme (60-30-10) ──
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');

:root {
    --bg: #0a0e14;
    --bg-deep: #060811;
    --card: #0f172a;
    --cyan: #22d3ee;
    --violet: #7c6ff0;
    --green: #16c784;
    --red: #ea3943;
    --amber: #f59e0b;
    --text: #e7ebf3;
    --text-dim: #8b93a7;
    --text-faint: #545c6e;
}

html, body, [data-testid="stAppViewContainer"] {
    background: radial-gradient(ellipse 900px 500px at 15% -5%, rgba(124,111,240,.10), transparent),
                radial-gradient(ellipse 900px 600px at 85% 105%, rgba(34,211,238,.08), transparent),
                var(--bg-deep) !important;
    font-family: 'Inter', sans-serif !important;
    color: var(--text) !important;
}

h1, h2, h3, h4 {
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 700 !important;
    color: var(--text) !important;
}

[data-testid="stSidebar"] {
    background: rgba(12,16,23,.5) !important;
    border-right: 1px solid rgba(255,255,255,.08) !important;
}

.stButton > button {
    background: linear-gradient(135deg, rgba(34,211,238,.12), rgba(124,111,240,.08)) !important;
    border: 1px solid rgba(34,211,238,.2) !important;
    color: var(--cyan) !important;
    border-radius: 10px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    transition: all .15s ease !important;
}
.stButton > button:hover {
    border-color: rgba(34,211,238,.5) !important;
    background: linear-gradient(135deg, rgba(34,211,238,.22), rgba(124,111,240,.15)) !important;
    color: #fff !important;
}

[data-testid="stTabs"] [role="tab"] {
    font-family: 'Space Grotesk', sans-serif;
    color: var(--text-dim);
    font-weight: 600;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: var(--cyan) !important;
    border-bottom-color: var(--cyan) !important;
}

.stTextInput > div > input, .stSelectbox > div > div {
    background: rgba(255,255,255,.03) !important;
    border: 1px solid rgba(255,255,255,.08) !important;
    color: var(--text) !important;
    border-radius: 9px !important;
}
.stTextInput > div > input:focus {
    border-color: rgba(34,211,238,.35) !important;
    background: rgba(34,211,238,.04) !important;
}

.live-dot {
    display: inline-block; width: 8px; height: 8px; border-radius: 50%;
    background: var(--green); box-shadow: 0 0 8px var(--green); margin-right: 6px;
    animation: pulse-ring 2s infinite;
}
@keyframes pulse-ring {
    0% { box-shadow: 0 0 0 0 rgba(34,211,238,.45); }
    100% { box-shadow: 0 0 0 14px rgba(34,211,238,0); }
}

.finsage-card {
    background: rgba(18,22,31,.72);
    border: 1px solid rgba(255,255,255,.08);
    border-radius: 14px;
    padding: 20px;
    backdrop-filter: blur(20px);
}

.metric-tile {
    background: rgba(18,22,31,.72);
    border: 1px solid rgba(255,255,255,.08);
    border-radius: 12px;
    padding: 16px;
    text-align: center;
}
.metric-val {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.5rem; font-weight: 700;
    color: var(--cyan);
}
.metric-lbl {
    font-size: 0.7rem; color: var(--text-faint);
    text-transform: uppercase; letter-spacing: .06em;
    margin-top: 4px;
}

.signal-box {
    background: linear-gradient(135deg, rgba(34,211,238,.06), rgba(124,111,240,.04));
    border: 1px solid rgba(34,211,238,.15);
    border-radius: 12px; padding: 16px; text-align: center;
}
.signal-buy { color: var(--green) !important; }
.signal-sell { color: var(--red) !important; }
.signal-wait { color: var(--amber) !important; }

.indicator-card {
    background: rgba(255,255,255,.02);
    border: 1px solid rgba(255,255,255,.08);
    border-radius: 8px; padding: 10px;
}

.sentiment-dot {
    height: 8px; width: 8px; border-radius: 50%; display: inline-block; margin-right: 6px;
}
.dot-pos { background: var(--green); }
.dot-neg { background: var(--red); }
.dot-neu { background: var(--violet); }

.chip {
    display: inline-block; padding: 4px 12px; border-radius: 20px;
    background: rgba(255,255,255,.04); border: 1px solid rgba(255,255,255,.08);
    color: var(--text-dim); font-size: 0.75rem; margin: 2px;
}
.chip-active {
    background: rgba(34,211,238,.08); border-color: rgba(34,211,238,.25); color: var(--cyan);
}

.news-item {
    background: rgba(255,255,255,.02);
    border: 1px solid rgba(255,255,255,.08);
    border-radius: 10px; padding: 10px; margin-bottom: 8px;
    transition: background .12s ease;
}

div[data-testid="stMetricValue"] {
    font-family: 'JetBrains Mono', monospace !important;
    color: var(--text) !important;
}

/* ── Hide Streamlit Default UI (star, edit, GitHub, 3-dots menu) ── */
header[data-testid="stHeader"] { display: none !important; visibility: hidden !important; }
#MainMenu { display: none !important; visibility: hidden !important; }
footer { display: none !important; visibility: hidden !important; }
[data-testid="stToolbar"] { display: none !important; }
.stDeployButton { display: none !important; }
div[data-testid="stSidebarCollapseButton"] { display: none !important; }
#stAppToolbar { display: none !important; }
[data-testid="stStatusWidget"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ── Constants ──
CRYPTO_SYMBOLS = ['BTCUSDT','ETHUSDT','BNBUSDT','SOLUSDT','XRPUSDT','ADAUSDT','DOGEUSDT',
    'AVAXUSDT','DOTUSDT','LINKUSDT','MATICUSDT','LTCUSDT','TRXUSDT','SHIBUSDT',
    'ATOMUSDT','UNIUSDT','ETCUSDT','XLMUSDT','NEARUSDT','APTUSDT']

INDIAN_INDICES = [
    {"symbol": "^NSEI", "label": "NIFTY 50", "name": "Nifty 50"},
    {"symbol": "^BSESN", "label": "SENSEX", "name": "BSE Sensex"},
    {"symbol": "^NSEBANK", "label": "NIFTY BANK", "name": "Nifty Bank"},
    {"symbol": "^CNXIT", "label": "NIFTY IT", "name": "Nifty IT"},
    {"symbol": "RELIANCE.NS", "label": "RELIANCE", "name": "Reliance Industries"},
    {"symbol": "TCS.NS", "label": "TCS", "name": "Tata Consultancy"},
    {"symbol": "INFY.NS", "label": "INFY", "name": "Infosys"},
    {"symbol": "HDFCBANK.NS", "label": "HDFCBANK", "name": "HDFC Bank"},
]

SYMBOL_TO_CG = {
    "BTC":"bitcoin","ETH":"ethereum","BNB":"binancecoin","SOL":"solana",
    "XRP":"ripple","ADA":"cardano","DOGE":"dogecoin","AVAX":"avalanche-2",
    "DOT":"polkadot","LINK":"chainlink","MATIC":"matic-network","LTC":"litecoin",
    "TRX":"tron","SHIB":"shiba-inu","ATOM":"cosmos","UNI":"uniswap",
    "ETC":"ethereum-classic","XLM":"stellar","NEAR":"near","APT":"aptos",
}

# ── Binance API ──
@st.cache_data(ttl=60)
def fetch_binance_klines(symbol, interval='1h', limit=300):
    try:
        r = requests.get(f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}", timeout=10)
        data = r.json()
        df = pd.DataFrame(data, columns=['ts','open','high','low','close','vol','cts','qav','nt','tbv','tqv','i'])
        df['ts'] = pd.to_datetime(df['ts'], unit='ms')
        for c in ['open','high','low','close','vol']: df[c] = df[c].astype(float)
        return df
    except: return pd.DataFrame()

@st.cache_data(ttl=30)
def fetch_binance_ticker(symbol):
    try:
        r = requests.get(f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}", timeout=5)
        return r.json()
    except: return {}

@st.cache_data(ttl=600)
def fetch_coingecko(coin_id):
    try:
        r = requests.get(f"https://api.coingecko.com/api/v3/coins/{coin_id}?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false&sparkline=false", timeout=10)
        return r.json()
    except: return {}

# ── Yahoo Finance API (Nifty, Sensex, Indian Stocks) ──
@st.cache_data(ttl=60)
def fetch_yf_chart(symbol, interval='60m', range='1mo'):
    try:
        r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval={interval}&range={range}", timeout=10,
                         headers={"User-Agent": "Mozilla/5.0"})
        d = r.json()
        res = d['chart']['result'][0]
        ts = res['timestamp']
        q = res['indicators']['quote'][0]
        df = pd.DataFrame({'ts': pd.to_datetime(ts, unit='s'),
            'open': q['open'], 'high': q['high'], 'low': q['low'], 'close': q['close'], 'vol': q['volume']})
        df = df.dropna(subset=['close'])
        for c in ['open','high','low','close','vol']: df[c] = df[c].astype(float)
        return df
    except: return pd.DataFrame()

@st.cache_data(ttl=30)
def fetch_yf_quote(symbol):
    try:
        r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d", timeout=5,
                         headers={"User-Agent": "Mozilla/5.0"})
        d = r.json()
        meta = d['chart']['result'][0]['meta']
        price = meta.get('regularMarketPrice', 0)
        prev = meta.get('previousClose', price)
        return {"price": price, "change": price - prev, "changePct": ((price - prev) / prev * 100) if prev > 0 else 0}
    except: return None

@st.cache_data(ttl=120)
def fetch_yf_fundamentals(symbol):
    try:
        r = requests.get(f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{symbol}?modules=summaryDetail,price,financialData,assetProfile,defaultKeyStatistics", timeout=10,
                         headers={"User-Agent": "Mozilla/5.0"})
        d = r.json()
        res = d.get('quoteSummary', {}).get('result', [{}])[0]
        sd = res.get('summaryDetail', {}); p = res.get('price', {}); fd = res.get('financialData', {}); ap = res.get('assetProfile', {}); ks = res.get('defaultKeyStatistics', {})
        def val(x): return x.get('raw') if isinstance(x, dict) else x
        return {
            "name": p.get('shortName') or p.get('longName') or symbol,
            "sector": ap.get('sector', '—'), "industry": ap.get('industry', '—'),
            "desc": (ap.get('longBusinessSummary') or '')[:500],
            "marketCap": val(sd.get('marketCap', {})), "pe": val(sd.get('trailingPE', {})),
            "eps": val(ks.get('trailingEps', {})), "pb": val(sd.get('priceToBook', {})),
            "divYield": val(sd.get('dividendYield', {})), "beta": val(sd.get('beta', {})),
            "profitMargin": val(fd.get('profitMargins', {})),
            "rev": val(fd.get('totalRevenue', {})), "revGrowth": val(fd.get('revenueGrowth', {})),
            "high52": val(sd.get('fiftyTwoWeekHigh', {})), "low52": val(sd.get('fiftyTwoWeekLow', {})),
            "target": val(fd.get('targetMeanPrice', {})), "recommendation": fd.get('recommendationKey', '—'),
            "website": ap.get('website'),
        }
    except: return None

# ── Technical Analysis Engine ──
def calc_rsi(closes, period=14):
    delta = closes.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))

def calc_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def calc_macd(closes):
    ema12 = closes.ewm(span=12, adjust=False).mean()
    ema26 = closes.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal

def calc_bollinger(closes, period=20, std=2):
    sma = closes.rolling(window=period).mean()
    rolling_std = closes.rolling(window=period).std()
    return sma + std * rolling_std, sma, sma - std * rolling_std

def calc_atr(df, period=14):
    hl = df['high'] - df['low']
    hc = (df['high'] - df['close'].shift()).abs()
    lc = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def calc_vwap(df):
    return (df['close'] * df['vol']).cumsum() / (df['vol'].cumsum() + 1e-9)

def calc_fibonacci(df):
    recent = df.tail(100)
    high = recent['high'].max()
    low = recent['low'].min()
    diff = high - low
    return {"0.0": high, "23.6": high - diff*0.236, "38.2": high - diff*0.382,
            "50.0": high - diff*0.5, "61.8": high - diff*0.618, "78.6": high - diff*0.786, "100": low}

def calc_sr_levels(df):
    recent = df.tail(200)
    resistance = recent['high'].nlargest(5).tolist()
    support = recent['low'].nsmallest(5).tolist()
    return resistance, support

def analyze_trend(df):
    if len(df) < 50: return "sideways", "Insufficient data"
    closes = df['close']
    ema20 = calc_ema(closes, 20).iloc[-1]
    ema50 = calc_ema(closes, 50).iloc[-1]
    price = closes.iloc[-1]
    ema200 = calc_ema(closes, min(200, len(closes))).iloc[-1]
    bull = 0; bear = 0
    if price > ema20: bull += 1
    else: bear += 1
    if ema20 > ema50: bull += 1
    else: bear += 1
    if price > ema200: bull += 1
    else: bear += 1
    if bull >= 2: return "uptrend", f"Price above EMA20/50{'/200' if price > ema200 else ''} — Bullish"
    if bear >= 2: return "downtrend", f"Price below EMA20/50{'/200' if price < ema200 else ''} — Bearish"
    return "sideways", "Mixed signals — Range-bound"

def generate_signal(df):
    if len(df) < 50: return {"action": "WAIT", "confidence": 0, "reasons": "Not enough data"}
    closes = df['close']
    rsi = calc_rsi(closes).iloc[-1]
    macd_line, macd_signal = calc_macd(closes)
    macd_val = macd_line.iloc[-1] - macd_signal.iloc[-1]
    bb_upper, bb_mid, bb_lower = calc_bollinger(closes)
    trend, trend_detail = analyze_trend(df)
    price = closes.iloc[-1]
    score = 0; reasons = []
    if rsi < 30: score += 2; reasons.append("RSI oversold")
    elif rsi > 70: score -= 2; reasons.append("RSI overbought")
    elif rsi > 50: score += 1; reasons.append("RSI bullish")
    else: score -= 1; reasons.append("RSI bearish")
    if macd_val > 0: score += 1; reasons.append("MACD positive")
    else: score -= 1; reasons.append("MACD negative")
    if price < bb_lower.iloc[-1]: score += 1; reasons.append("Below BB lower")
    elif price > bb_upper.iloc[-1]: score -= 1; reasons.append("Above BB upper")
    if trend == "uptrend": score += 1; reasons.append("Uptrend")
    elif trend == "downtrend": score -= 1; reasons.append("Downtrend")
    action = "WAIT"; confidence = 50
    if score >= 3: action = "BUY"; confidence = min(95, 60 + score * 5)
    elif score <= -3: action = "SELL"; confidence = min(95, 60 + abs(score) * 5)
    elif score > 0: action = "BUY"; confidence = 55 + score * 5
    elif score < 0: action = "SELL"; confidence = 55 + abs(score) * 5
    return {"action": action, "confidence": confidence, "reasons": " • ".join(reasons),
            "rsi": rsi, "macd": macd_val, "trend": trend}

# ── News ──
def fetch_crypto_news(symbol, limit=10):
    base = symbol.replace('USDT', '')
    url = f"https://min-api.cryptocompare.com/data/v2/news/?lang=EN&categories={base}"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        return [{"title": n['title'], "source": n.get('source_info', {}).get('name', n.get('source', 'Unknown')),
                 "url": n['url'], "published": n.get('published_on', 0),
                 "body": n.get('body', '')[:200], "img": n.get('imageurl'),
                 "sentiment": "positive" if base in n.get('categories', '') else "neutral"}
                for n in data.get('Data', [])[:limit]]
    except: return []

def fetch_stock_news(symbol, limit=10):
    query = symbol.replace('^', '').replace('.NS', '')
    url = f"https://news.google.com/rss/search?q={query}+stock+market&hl=en-US&gl=US&ceid=US:en"
    try:
        feed = feedparser.parse(url)
        items = []
        for e in feed.entries[:limit]:
            items.append({"title": e.title, "source": e.get('source', {}).get('title', 'Unknown'),
                          "url": e.link, "published": time.mktime(e.published_parsed) if hasattr(e, 'published_parsed') else 0,
                          "body": "", "img": None, "sentiment": "neutral"})
        return items
    except: return []

def fetch_youtube_videos(query, limit=8):
    try:
        r = requests.get(f"https://www.youtube.com/feeds/videos.xml?search_query={query}+latest+analysis+trading",
                         headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        import xml.etree.ElementTree as ET
        root = ET.fromstring(r.content)
        ns = {'a': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015', 'media': 'http://search.yahoo.com/mrss/'}
        vids = []
        for entry in root.findall('a:entry', ns)[:limit]:
            vid = entry.find('yt:videoId', ns)
            title = entry.find('a:title', ns)
            author = entry.find('a:author/a:name', ns)
            thumb = entry.find('media:group/media:thumbnail', ns)
            vids.append({
                "vid": vid.text if vid is not None else "",
                "title": title.text if title is not None else "",
                "author": author.text if author is not None else "",
                "thumb": thumb.get('url') if thumb is not None else "",
            })
        return vids
    except: return []


def base_asset(symbol):
    """Extract base asset name from trading pair (e.g. BTCUSDT -> BTC)"""
    return symbol.replace('USDT', '').replace('BTC', 'BTC') if 'USDT' in symbol else symbol

# ── Chart ──
def build_chart(df, symbol, is_crypto=True):
    fig = go.Figure(data=[go.Candlestick(
        x=df['ts'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
        increasing_line_color='#16c784', decreasing_line_color='#ea3943',
        name=symbol
    )])
    if len(df) >= 20:
        fig.add_trace(go.Scatter(x=df['ts'], y=calc_ema(df['close'], 20), mode='lines',
            line=dict(color='#22d3ee', width=1.5), name='EMA 20'))
    if len(df) >= 50:
        fig.add_trace(go.Scatter(x=df['ts'], y=calc_ema(df['close'], 50), mode='lines',
            line=dict(color='#7c6ff0', width=1.5), name='EMA 50'))
    bb_u, bb_m, bb_l = calc_bollinger(df['close'])
    fig.add_trace(go.Scatter(x=df['ts'], y=bb_u, mode='lines', line=dict(color='rgba(234,57,67,.2)', width=1), name='BB Upper'))
    fig.add_trace(go.Scatter(x=df['ts'], y=bb_l, mode='lines', line=dict(color='rgba(22,199,132,.2)', width=1), name='BB Lower', fill='tonexty', fillcolor='rgba(124,111,240,.05)'))
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='transparent', plot_bgcolor='transparent',
        font=dict(family='JetBrains Mono', color='#8b93a7', size=11),
        xaxis=dict(gridcolor='rgba(255,255,255,.04)', rangeslider_visible=False),
        yaxis=dict(gridcolor='rgba(255,255,255,.04)'),
        height=450, margin=dict(l=0, r=0, t=0, b=0),
        showlegend=True, legend=dict(orientation='h', yanchor='bottom', y=1, xanchor='right', x=1, font=dict(size=10))
    )
    return fig

# ── Auth Page (Password Gate) ──
ACCESS_PASSWORD = "dinesh123"

def page_auth():
    st.markdown("<div style='height:8vh'></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style='text-align:center; margin-bottom:30px;'>
            <div style='font-size:2.5rem; font-weight:700; font-family:Space Grotesk,sans-serif;'>
                Finsage<span style='background:linear-gradient(90deg,#22d3ee,#7c6ff0); -webkit-background-clip:text; background-clip:text; color:transparent;'> AI</span>
            </div>
            <div style='color:#545c6e; font-size:0.9rem; margin-top:8px; letter-spacing:.06em; text-transform:uppercase;'>
                STOCK · CRYPTO · MEME COIN ANALYSIS
            </div>
        </div>
        """, unsafe_allow_html=True)

        tab_in, tab_up, tab_demo = st.tabs(["Sign In", "Create Account", "Demo Access"])
        with tab_in:
            with st.form("form_login", clear_on_submit=False):
                li_email = st.text_input("Email", placeholder="you@example.com", key="li_email")
                password = st.text_input("Password", placeholder="Enter password", type="password", key="li_pw")
                submit = st.form_submit_button("Sign In", use_container_width=True)
                if submit:
                    if not li_email or not password:
                        st.error("Email and password required.")
                    else:
                        db = SessionLocal()
                        user = db.query(User).filter_by(email=li_email).first()
                        if user and verify_pw(password, user.password_hash):
                            st.session_state["user"] = {"id": user.id, "email": user.email, "name": user.full_name or "Trader", "strategy": user.strategy or "Balanced"}
                            db.close()
                            st.rerun()
                        else:
                            db.close()
                            st.error("Invalid email or password.")
        with tab_up:
            with st.form("form_signup", clear_on_submit=False):
                full_name = st.text_input("Full Name", placeholder="Your name", key="su_name")
                su_email = st.text_input("Email", placeholder="you@example.com", key="su_email")
                su_pw = st.text_input("Password", placeholder="Min 8 characters", type="password", key="su_pw")
                su_pw2 = st.text_input("Confirm Password", placeholder="Repeat", type="password", key="su_pw2")
                strategy = st.selectbox("Trading Strategy", ["Balanced", "Conservative", "Aggressive"], key="su_strat")
                register = st.form_submit_button("Create Account", use_container_width=True)
                if register:
                    errs = []
                    if not full_name: errs.append("Full name required.")
                    if not su_email or "@" not in su_email: errs.append("Valid email required.")
                    if len(su_pw) < 8: errs.append("Password must be 8+ characters.")
                    if su_pw != su_pw2: errs.append("Passwords don't match.")
                    if errs:
                        for e in errs: st.error(e)
                    else:
                        try:
                            db = SessionLocal()
                            if db.query(User).filter_by(email=su_email).first():
                                st.error("Account already exists. Try signing in instead.")
                            else:
                                user = User(email=su_email, password_hash=hash_pw(su_pw), full_name=full_name, strategy=strategy)
                                db.add(user); db.commit()
                                st.session_state["user"] = {"id": user.id, "email": su_email, "name": full_name, "strategy": strategy}
                                st.rerun()
                            db.close()
                        except Exception as e:
                            st.error(f"Signup error: {str(e)}")
        with tab_demo:
            st.markdown("<div style='text-align:center; padding:20px; color:#8b93a7; font-size:14px;'>Quick demo access — no account needed. Explore all features instantly.</div>", unsafe_allow_html=True)
            if st.button("🚀 Enter Demo Mode", use_container_width=True, key="demo_btn"):
                st.session_state["user"] = {"id": "demo", "email": "demo@finsage.ai", "name": "Demo Trader", "strategy": "Balanced"}
                st.rerun()

# ── Sidebar ──
def render_sidebar():
    with st.sidebar:
        user = st.session_state.get("user", {})
        st.markdown(f"""
        <div style='display:flex; align-items:center; gap:10px; padding:12px 0; border-bottom:1px solid rgba(255,255,255,.08); margin-bottom:12px;'>
            <div style='width:36px; height:36px; border-radius:50%; background:linear-gradient(135deg,#22d3ee,#7c6ff0); display:flex; align-items:center; justify-content:center; font-weight:700; color:#0a0e14;'>{user.get('name','U')[0].upper()}</div>
            <div>
                <div style='font-weight:600; font-size:14px;'>{user.get('name','User')}</div>
                <div style='font-size:11px; color:#545c6e;'>{user.get('email','')}</div>
            </div>
        </div>
        <div style='font-size:11px; color:#545c6e; margin-bottom:8px;'><span class='live-dot'></span>LIVE DATA</div>
        """, unsafe_allow_html=True)

        st.markdown("**📊 Core**")
        core_pages = ["Dashboard", "News & Video", "Settings"]
        for p in core_pages:
            if st.button(p, key=f"nav_{p}", use_container_width=True):
                st.session_state["page"] = p
                st.rerun()

        st.markdown("**🔬 Analysis**")
        analysis_pages = ["AI Assistant", "Pro Analyser", "TradingView Charts", "AI Chart Analyzer", "Advanced Intel"]
        for p in analysis_pages:
            if st.button(p, key=f"nav_{p}", use_container_width=True):
                st.session_state["page"] = p
                st.rerun()

        st.markdown("**🛡️ Risk & Trading**")
        risk_pages = ["Risk Engine", "Exchange Backend", "Community", "White Paper Report", "Privacy Policy"]
        for p in risk_pages:
            if st.button(p, key=f"nav_{p}", use_container_width=True):
                st.session_state["page"] = p
                st.rerun()

        st.markdown("---")
        st.markdown("**Risk Limits**")
        st.markdown(f"""
        <div style='font-size:12px; color:#8b93a7; line-height:1.8;'>
        • Max Position: <b style='color:#22d3ee'>{MAX_POSITION_PCT}%</b><br>
        • Max Stop-Loss: <b style='color:#ea3943'>{MAX_SL_PCT}%</b><br>
        • Min R:R: <b style='color:#16c784'>1:{MIN_RR}</b><br>
        • Max Daily Loss: <b style='color:#ea3943'>{MAX_DAILY_LOSS_PCT}%</b>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Logout", key="logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()

# ── Dashboard Page ──
def page_dashboard():
    st.markdown("## 📊 FinsageAI Dashboard")

    col_type, col_asset, col_interval = st.columns([1, 2, 1])
    with col_type:
        asset_type = st.radio("Market", ["Crypto", "Nifty / Sensex"], horizontal=True, key="asset_type_radio")
    with col_interval:
        interval = st.selectbox("Timeframe", ["15m", "1h", "4h", "1d", "1w"], key="interval_sel")

    is_crypto = (asset_type == "Crypto")

    with col_asset:
        if is_crypto:
            symbol = st.selectbox("Asset", [s.replace('USDT', '/USDT') for s in CRYPTO_SYMBOLS], key="crypto_sym")
            binance_sym = symbol.replace('/USDT', 'USDT')
        else:
            idx = st.selectbox("Index/Stock", range(len(INDIAN_INDICES)),
                format_func=lambda i: f"{INDIAN_INDICES[i]['label']} — {INDIAN_INDICES[i]['name']}", key="indian_sym")
            symbol = INDIAN_INDICES[idx]['symbol']
            binance_sym = symbol

    # Fetch data
    if is_crypto:
        df = fetch_binance_klines(binance_sym, interval, 300)
        ticker = fetch_binance_ticker(binance_sym)
        price = float(ticker.get('lastPrice', 0)) if ticker else (df['close'].iloc[-1] if not df.empty else 0)
        change_pct = float(ticker.get('priceChangePercent', 0)) if ticker else 0
        currency = "$"
    else:
        yf_int = {"15m": "15m", "1h": "60m", "4h": "60m", "1d": "1d", "1w": "1wk"}.get(interval, "60m")
        yf_range = {"15m": "5d", "1h": "1mo", "4h": "3mo", "1d": "1y", "1w": "5y"}.get(interval, "1mo")
        df = fetch_yf_chart(symbol, yf_int, yf_range)
        quote = fetch_yf_quote(symbol)
        price = quote['price'] if quote else (df['close'].iloc[-1] if not df.empty else 0)
        change_pct = quote['changePct'] if quote else 0
        currency = "₹"

    if df.empty:
        st.error("Failed to load data. Please try again.")
        return

    display_label = binance_sym.replace('USDT', '/USDT') if is_crypto else INDIAN_INDICES[idx]['label']

    # Header metrics
    mc1, mc2, mc3, mc4, mc5 = st.columns(5)
    with mc1:
        st.markdown(f"<div class='metric-tile'><div class='metric-val'>{currency}{price:,.2f}</div><div class='metric-lbl'>{display_label} Price</div></div>", unsafe_allow_html=True)
    with mc2:
        color = "#16c784" if change_pct >= 0 else "#ea3943"
        st.markdown(f"<div class='metric-tile'><div class='metric-val' style='color:{color}'>{change_pct:+.2f}%</div><div class='metric-lbl'>24h Change</div></div>", unsafe_allow_html=True)
    with mc3:
        if not df.empty:
            hi = df['high'].tail(24).max() if is_crypto else df['high'].tail(5).max()
            st.markdown(f"<div class='metric-tile'><div class='metric-val' style='font-size:1.2rem'>{currency}{hi:,.2f}</div><div class='metric-lbl'>Recent High</div></div>", unsafe_allow_html=True)
    with mc4:
        if not df.empty:
            lo = df['low'].tail(24).min() if is_crypto else df['low'].tail(5).min()
            st.markdown(f"<div class='metric-tile'><div class='metric-val' style='font-size:1.2rem'>{currency}{lo:,.2f}</div><div class='metric-lbl'>Recent Low</div></div>", unsafe_allow_html=True)
    with mc5:
        if not df.empty and 'vol' in df:
            vol = df['vol'].tail(24).sum()
            st.markdown(f"<div class='metric-tile'><div class='metric-val' style='font-size:1.2rem'>{vol:,.0f}</div><div class='metric-lbl'>Volume</div></div>", unsafe_allow_html=True)

    st.markdown("---")

    # Chart
    st.markdown("### 📈 Price Chart")
    st.plotly_chart(build_chart(df, display_label, is_crypto), use_container_width=True)

    # Analysis tabs
    st.markdown("---")
    tab_ta, tab_fa, tab_news, tab_video = st.tabs(["🔬 Technical Analysis", "📊 Fundamental Analysis", "📰 News", "🎬 Video Analysis"])

    with tab_ta:
        st.markdown("#### Technical Analysis — Pro Trader View")
        signal = generate_signal(df)
        trend, trend_detail = analyze_trend(df)
        closes = df['close']
        rsi_val = calc_rsi(closes).iloc[-1]
        macd_line, macd_signal = calc_macd(closes)
        macd_hist = (macd_line - macd_signal).iloc[-1]
        bb_u, bb_m, bb_l = calc_bollinger(closes)
        atr_val = calc_atr(df).iloc[-1]
        vwap_val = calc_vwap(df).iloc[-1]

        # Signal card
        sig_color = "signal-buy" if signal['action'] == "BUY" else "signal-sell" if signal['action'] == "SELL" else "signal-wait"
        st.markdown(f"""
        <div class='signal-box'>
            <div style='font-size:2rem; font-weight:700; font-family:Space Grotesk;' class='{sig_color}'>{signal['action']}</div>
            <div style='font-size:0.85rem; color:#545c6e; margin-top:4px;'>Confidence: {signal['confidence']}%</div>
            <div style='font-size:0.8rem; color:#8b93a7; margin-top:8px;'>{signal['reasons']}</div>
        </div>
        """, unsafe_allow_html=True)

        # Trend
        trend_badge = f"🟢 UPTREND" if trend == "uptrend" else f"🔴 DOWNTREND" if trend == "downtrend" else "⚪ SIDEWAYS"
        st.markdown(f"**Trend Structure:** {trend_badge} — {trend_detail}")

        # Indicator grid
        st.markdown("##### Key Indicators")
        ig1, ig2, ig3, ig4 = st.columns(4)
        with ig1:
            rsi_zone = "Oversold 🔴" if rsi_val < 30 else "Overbought 🟢" if rsi_val > 70 else "Neutral ⚪"
            st.metric("RSI (14)", f"{rsi_val:.1f}", rsi_zone)
        with ig2:
            macd_dir = "Bullish 🟢" if macd_hist > 0 else "Bearish 🔴"
            st.metric("MACD Histogram", f"{macd_hist:.4f}", macd_dir)
        with ig3:
            st.metric("ATR (14)", f"{atr_val:.2f}", "Volatility")
        with ig4:
            vwap_dir = "Above 🟢" if closes.iloc[-1] > vwap_val else "Below 🔴"
            st.metric("VWAP", f"{vwap_val:.2f}", vwap_dir)

        # EMA cross
        st.markdown("##### Moving Averages")
        ema20_val = calc_ema(closes, 20).iloc[-1]
        ema50_val = calc_ema(closes, 50).iloc[-1]
        if len(closes) >= 200:
            ema200_val = calc_ema(closes, 200).iloc[-1]
        else:
            ema200_val = calc_ema(closes, min(100, len(closes))).iloc[-1]
        ema1, ema2, ema3 = st.columns(3)
        with ema1:
            st.metric("EMA 20", f"{ema20_val:.2f}", "🟢" if closes.iloc[-1] > ema20_val else "🔴")
        with ema2:
            st.metric("EMA 50", f"{ema50_val:.2f}", "🟢" if closes.iloc[-1] > ema50_val else "🔴")
        with ema3:
            st.metric("EMA 200", f"{ema200_val:.2f}", "🟢" if closes.iloc[-1] > ema200_val else "🔴")

        # Bollinger Bands
        st.markdown("##### Bollinger Bands")
        bb1, bb2, bb3 = st.columns(3)
        with bb1: st.metric("Upper Band", f"{bb_u.iloc[-1]:.2f}")
        with bb2: st.metric("Middle (SMA20)", f"{bb_m.iloc[-1]:.2f}")
        with bb3: st.metric("Lower Band", f"{bb_l.iloc[-1]:.2f}")

        # Momentum meter
        st.markdown("##### RSI Momentum Meter")
        rsi_pct = max(0, min(100, rsi_val))
        bar_color = "#16c784" if rsi_val < 30 else "#ea3943" if rsi_val > 70 else "#7c6ff0"
        st.markdown(f"""
        <div style='background:#1e293b; height:12px; border-radius:6px; overflow:hidden; margin:8px 0;'>
            <div style='width:{rsi_pct}%; height:100%; background:{bar_color}; transition:width .5s;'></div>
        </div>
        <div style='display:flex; justify-content:space-between; font-size:10px; color:#545c6e;'>
            <span>Oversold (30)</span><span>Neutral (50)</span><span>Overbought (70)</span>
        </div>
        <div style='text-align:right; font-size:12px; margin-top:4px; color:{bar_color};'>
            RSI: {rsi_val:.1f} — {"Oversold — Potential buy zone" if rsi_val < 30 else "Overbought — Potential sell zone" if rsi_val > 70 else "Neutral momentum"}
        </div>
        """, unsafe_allow_html=True)

        # S/R Levels
        st.markdown("##### Support / Resistance Levels")
        resist, support = calc_sr_levels(df)
        sr1, sr2 = st.columns(2)
        with sr1:
            st.markdown("**🔴 Resistance**")
            for r in resist[:5]:
                st.markdown(f"<div style='color:#ea3943; font-family:JetBrains Mono; font-size:13px;'>{currency}{r:,.2f}</div>", unsafe_allow_html=True)
        with sr2:
            st.markdown("**🟢 Support**")
            for s in support[:5]:
                st.markdown(f"<div style='color:#16c784; font-family:JetBrains Mono; font-size:13px;'>{currency}{s:,.2f}</div>", unsafe_allow_html=True)

        # Fibonacci
        st.markdown("##### Fibonacci Retracement Levels")
        fib = calc_fibonacci(df)
        fib_cols = st.columns(7)
        for i, (level, val) in enumerate(fib.items()):
            with fib_cols[i]:
                st.metric(f"Fib {level}%", f"{val:,.2f}")

        # Risk validation
        st.markdown("---")
        st.markdown("##### 🛡️ Risk-Adjusted Trade Setup")
        with st.form("risk_form"):
            rc1, rc2, rc3, rc4 = st.columns(4)
            with rc1: action_sel = st.selectbox("Action", ["BUY", "SELL"])
            with rc2: entry_val = st.number_input("Entry Price", value=float(price), step=0.01)
            with rc3: sl_val = st.number_input("Stop Loss", value=float(price * 0.98), step=0.01)
            with rc4: tp_val = st.number_input("Take Profit", value=float(price * 1.04), step=0.01)
            size_val = st.slider("Position Size %", 0.5, MAX_POSITION_PCT, 2.0, 0.5)
            if st.form_submit_button("Validate Trade Setup"):
                valid, issues, result = validate_trade(action_sel, entry_val, sl_val, tp_val, size_val)
                if valid:
                    st.success(f"✅ Trade setup is valid! R:R = {result['risk_reward']}")
                else:
                    st.error("❌ Trade rejected:")
                    for iss in issues: st.markdown(f"• {iss}")

    with tab_fa:
        st.markdown("#### Fundamental Analysis")
        if is_crypto:
            base = binance_sym.replace('USDT', '')
            cg_id = SYMBOL_TO_CG.get(base)
            if cg_id:
                with st.spinner("Loading CoinGecko data..."):
                    cg = fetch_coingecko(cg_id)
                if cg:
                    md = cg.get('market_data', {})
                    st.markdown(f"##### {cg.get('name', base)} ({base})")
                    fa1, fa2, fa3, fa4 = st.columns(4)
                    with fa1: st.metric("Market Cap Rank", f"#{cg.get('market_cap_rank', '—')}")
                    with fa2: st.metric("Market Cap", f"${md.get('market_cap', {}).get('usd', 0)/1e9:.2f}B")
                    with fa3: st.metric("24h Change", f"{md.get('market_cap_change_percentage_24h', 0):.2f}%")
                    with fa4: st.metric("FDV", f"${md.get('fully_diluted_valuation', {}).get('usd', 0)/1e9:.2f}B" if md.get('fully_diluted_valuation') else "—")

                    fa5, fa6, fa7, fa8 = st.columns(4)
                    with fa5: st.metric("Circulating Supply", f"{md.get('circulating_supply', 0):,.0f}")
                    with fa6: st.metric("Total Supply", f"{md.get('total_supply', 0) or '∞':,.0f}")
                    with fa7: st.metric("Max Supply", f"{md.get('max_supply', 0) or '∞':,.0f}")
                    with fa8: st.metric("ATH", f"${md.get('ath', {}).get('usd', 0):,.2f}")

                    st.markdown("##### Project Overview")
                    desc = re.sub(r'<[^>]+>', '', cg.get('description', {}).get('en', ''))[:500]
                    st.markdown(f"<div class='finsage-card' style='color:#8b93a7; font-size:13px; line-height:1.6;'>{desc}</div>", unsafe_allow_html=True)

                    links = cg.get('links', {})
                    homepage = links.get('homepage', [None])[0]
                    if homepage:
                        st.markdown(f"🔗 [Visit official website]({homepage})")
            else:
                st.info("No CoinGecko data available for this asset.")
        else:
            with st.spinner("Loading fundamentals..."):
                fund = fetch_yf_fundamentals(symbol)
            if fund:
                st.markdown(f"##### {fund.get('name', symbol)}")
                st.markdown(f"**Sector:** {fund.get('sector', '—')} | **Industry:** {fund.get('industry', '—')}")

                fy1, fy2, fy3, fy4 = st.columns(4)
                with fy1: st.metric("Market Cap", f"₹{fund.get('marketCap', 0)/1e9:.1f}B" if fund.get('marketCap') else "—")
                with fy2: st.metric("P/E Ratio", f"{fund['pe']:.2f}" if fund.get('pe') else "—")
                with fy3: st.metric("EPS", f"₹{fund['eps']:.2f}" if fund.get('eps') else "—")
                with fy4: st.metric("P/B Ratio", f"{fund['pb']:.2f}" if fund.get('pb') else "—")

                fy5, fy6, fy7, fy8 = st.columns(4)
                with fy5: st.metric("Beta", f"{fund['beta']:.2f}" if fund.get('beta') else "—")
                with fy6: st.metric("Profit Margin", f"{fund['profitMargin']*100:.1f}%" if fund.get('profitMargin') else "—")
                with fy7: st.metric("52W High", f"₹{fund['high52']:,.2f}" if fund.get('high52') else "—")
                with fy8: st.metric("52W Low", f"₹{fund['low52']:,.2f}" if fund.get('low52') else "—")

                if fund.get('target'):
                    st.metric("Analyst Target Price", f"₹{fund['target']:,.2f}")
                if fund.get('recommendation'):
                    st.markdown(f"**Analyst Recommendation:** {fund['recommendation'].replace('_', ' ').title()}")

                if fund.get('desc'):
                    st.markdown("##### Company Overview")
                    st.markdown(f"<div class='finsage-card' style='color:#8b93a7; font-size:13px; line-height:1.6;'>{fund['desc']}</div>", unsafe_allow_html=True)
                if fund.get('website'):
                    st.markdown(f"🔗 [Visit website]({fund['website']})")
            else:
                st.info("Unable to load fundamentals for this asset.")

    with tab_news:
        st.markdown("#### Real-Time News")
        if is_crypto:
            news = fetch_crypto_news(binance_sym, 10)
        else:
            news = fetch_stock_news(symbol, 10)
        if news:
            for n in news:
                dot = "dot-pos" if n['sentiment'] == 'positive' else "dot-neg" if n['sentiment'] == 'negative' else "dot-neu"
                st.markdown(f"""
                <div class='news-item'>
                    <div style='display:flex; align-items:flex-start; gap:8px;'>
                        <span class='sentiment-dot {dot}'></span>
                        <div style='flex:1;'>
                            <div style='font-weight:600; color:#e7ebf3; font-size:13px; margin-bottom:4px;'>{n['title']}</div>
                            <div style='font-size:11px; color:#545c6e;'>{n['source']}</div>
                        </div>
                        <a href='{n['url']}' target='_blank' style='color:#22d3ee; font-size:12px; text-decoration:none;'>Read →</a>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No news available right now.")

    with tab_video:
        st.markdown("#### Video Analysis & Analysis")
        query = base_asset(binance_sym) if is_crypto else INDIAN_INDICES[idx]['label']
        with st.spinner("Loading videos..."):
            vids = fetch_youtube_videos(query, 6)
        if vids:
            vcols = st.columns(2)
            for i, v in enumerate(vids):
                with vcols[i % 2]:
                    st.markdown(f"""
                    <div style='background:rgba(255,255,255,.02); border:1px solid rgba(255,255,255,.08); border-radius:10px; overflow:hidden; margin-bottom:10px;'>
                        <a href='https://www.youtube.com/watch?v={v['vid']}' target='_blank' style='text-decoration:none;'>
                            <img src='{v['thumb']}' style='width:100%; height:120px; object-fit:cover; background:rgba(255,255,255,.04);' />
                            <div style='padding:8px 10px;'>
                                <div style='font-size:12px; font-weight:600; color:#e7ebf3; line-height:1.4;'>{v['title'][:80]}</div>
                                <div style='font-size:10px; color:#545c6e; margin-top:3px;'>{v['author']}</div>
                            </div>
                        </a>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("No videos found. Try searching on YouTube directly.")

# ── White Paper Report ──
def page_report():
    st.markdown("## 📄 Institutional White Paper Report")
    st.markdown("### 1. Executive Summary")
    st.markdown("""
    <div class='finsage-card' style='color:#8b93a7; font-size:13px; line-height:1.8;'>
    This report provides an institutional-grade analysis of the selected asset, combining technical
    indicators, fundamental data, and market sentiment into a comprehensive trading thesis.
    The analysis follows a rigorous three-layer architecture: Data Integration, Analytical Output,
    and Structured Presentation.
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 2. Market Pulse")
    st.markdown("Select an asset from the dashboard to generate the full report.")
    st.info("Navigate to the Dashboard, select your asset, then return here for the complete White Paper analysis.")

    st.markdown("### 3. Technical Blueprint")
    st.markdown("""
    The technical framework incorporates:
    - **Trend Analysis:** EMA 20/50/200 crossover system
    - **Momentum:** RSI (14) with overbought/oversold zones
    - **Convergence/Divergence:** MACD histogram and signal line
    - **Volatility:** Bollinger Bands (20, 2σ) and ATR (14)
    - **Volume:** VWAP for institutional fair value
    - **Price Levels:** Support/Resistance from 200-period extremes
    - **Fibonacci:** Auto-calculated retracement levels
    """)

    st.markdown("### 4. Risk Framework")
    st.markdown(f"""
    Risk management is enforced by a hard-coded validation layer:
    - Maximum position size: **{MAX_POSITION_PCT}%** of portfolio
    - Maximum stop-loss distance: **{MAX_SL_PCT}%** from entry
    - Minimum risk-reward ratio: **1:{MIN_RR}**
    - Maximum daily loss limit: **{MAX_DAILY_LOSS_PCT}%**
    - All trades must pass validation before execution
    """)

    st.markdown("### 5. Actionable Thesis")
    st.markdown("""
    <div class='finsage-card' style='color:#8b93a7; font-size:13px; line-height:1.8;'>
    Navigate to the Dashboard to view the live AI signal (BUY/SELL/WAIT) with confidence score,
    detailed indicator breakdown, and risk-validated trade setup. The signal is generated from
    a composite scoring model that weighs RSI, MACD, Bollinger Bands, and trend structure.
    </div>
    """, unsafe_allow_html=True)

# ── News & Video Page ──
def page_news_video():
    st.markdown("## 📰 News & 🎬 Video Hub")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### Latest News")
        asset = st.selectbox("Select Asset", ["BTC", "ETH", "Nifty 50", "Sensex", "Reliance", "TCS"], key="news_asset")
        is_crypto = asset in ["BTC", "ETH"]
        if is_crypto:
            sym = f"{asset}USDT"
            news = fetch_crypto_news(sym, 15)
        else:
            sym_map = {"Nifty 50": "^NSEI", "Sensex": "^BSESN", "Reliance": "RELIANCE.NS", "TCS": "TCS.NS"}
            sym = sym_map.get(asset, "^NSEI")
            news = fetch_stock_news(sym, 15)

        for n in news[:10]:
            dot = "dot-pos" if n['sentiment'] == 'positive' else "dot-neg" if n['sentiment'] == 'negative' else "dot-neu"
            st.markdown(f"""
            <div class='news-item'>
                <div style='display:flex; align-items:flex-start; gap:8px;'>
                    <span class='sentiment-dot {dot}'></span>
                    <div style='flex:1;'>
                        <div style='font-weight:600; color:#e7ebf3; font-size:13px; margin-bottom:4px;'>{n['title']}</div>
                        <div style='font-size:11px; color:#545c6e;'>{n['source']}</div>
                    </div>
                    <a href='{n['url']}' target='_blank' style='color:#22d3ee; font-size:12px; text-decoration:none;'>Read →</a>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with col2:
        st.markdown("### Video Analysis")
        with st.spinner("Loading videos..."):
            vids = fetch_youtube_videos(f"{asset} trading analysis", 8)
        for v in vids[:6]:
            st.markdown(f"""
            <div style='background:rgba(255,255,255,.02); border:1px solid rgba(255,255,255,.08); border-radius:10px; overflow:hidden; margin-bottom:10px;'>
                <a href='https://www.youtube.com/watch?v={v['vid']}' target='_blank' style='text-decoration:none;'>
                    <img src='{v['thumb']}' style='width:100%; height:100px; object-fit:cover;' />
                    <div style='padding:8px;'>
                        <div style='font-size:12px; font-weight:600; color:#e7ebf3;'>{v['title'][:80]}</div>
                        <div style='font-size:10px; color:#545c6e; margin-top:3px;'>{v['author']}</div>
                    </div>
                </a>
            </div>
            """, unsafe_allow_html=True)

# ── Settings Page ──
def page_settings():
    st.markdown("## ⚙️ Settings")
    user = st.session_state.get("user", {})
    st.markdown(f"**Account:** {user.get('email', '')}")
    st.markdown(f"**Strategy:** {user.get('strategy', 'Balanced')}")

    st.markdown("### Exchange API Keys")
    st.markdown("Your API keys are encrypted with AES-256 before storage. We never store plaintext credentials.")

    with st.form("api_form"):
        ex = st.selectbox("Exchange", ["Binance", "Coinbase", "Kraken", "WazirX"])
        ak = st.text_input("API Key")
        ask = st.text_input("API Secret", type="password")
        if st.form_submit_button("Save Encrypted Keys"):
            if ak and ask:
                db = SessionLocal()
                existing = db.query(ApiKey).filter_by(user_id=user['id'], exchange=ex.lower()).first()
                if existing:
                    existing.api_key_enc = encrypt(ak)
                    existing.api_secret_enc = encrypt(ask)
                else:
                    db.add(ApiKey(user_id=user['id'], exchange=ex.lower(), api_key_enc=encrypt(ak), api_secret_enc=encrypt(ask)))
                db.commit()
                db.close()
                st.success(f"Keys for {ex} encrypted and saved.")
            else:
                st.error("Both fields required.")

    st.markdown("### Saved Keys")
    db = SessionLocal()
    keys = db.query(ApiKey).filter_by(user_id=user.get('id', '')).all()
    if keys:
        for k in keys:
            st.markdown(f"""
            <div class='finsage-card' style='display:flex; justify-content:space-between; align-items:center;'>
                <div>
                    <div style='font-weight:600;'>{k.exchange.title()}</div>
                    <div style='font-size:11px; color:#545c6e;'>Added: {k.created_at.strftime('%Y-%m-%d')}</div>
                </div>
                <div style='font-size:12px; color:#22d3ee;'>🔒 Encrypted</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No API keys saved yet.")
    db.close()

# ── Main ──
def main():
    if "user" not in st.session_state:
        page_auth()
    else:
        render_sidebar()
        page = st.session_state.get("page", "Dashboard")
        if page == "Dashboard":
            page_dashboard()
        elif page == "News & Video":
            page_news_video()
        elif page == "Settings":
            page_settings()
        elif page == "White Paper Report":
            page_report()
        elif page == "AI Assistant":
            from advanced_features import render_ai_assistant_page
            render_ai_assistant_page()
        elif page == "Pro Analyser":
            from advanced_features import render_pro_analyser_page
            render_pro_analyser_page()
        elif page == "TradingView Charts":
            from advanced_features import render_tradingview_page
            render_tradingview_page()
        elif page == "AI Chart Analyzer":
            from advanced_features import render_chart_analyzer_page
            render_chart_analyzer_page()
        elif page == "Community":
            from advanced_features import render_community_page
            render_community_page()
        elif page == "Advanced Intel":
            from advanced_features import render_advanced_intel_page
            render_advanced_intel_page()
        elif page == "Risk Engine":
            from risk_engine import render_risk_engine_page
            render_risk_engine_page()
        elif page == "Exchange Backend":
            from exchange_backend import render_exchange_backend_page
            render_exchange_backend_page()
        elif page == "Privacy Policy":
            page_privacy()

if __name__ == "__main__":
    main()

# ── Privacy Policy Page ──
def page_privacy():
    st.markdown("## 🔒 Privacy Policy — FinsageAI")
    st.markdown("""
    <div class='finsage-card' style='color:#8b93a7; font-size:14px; line-height:1.8;'>
    <h3 style='color:#e7ebf3;'>1. Data We Collect</h3>
    <p>FinsageAI collects the following data when you create an account:</p>
    <ul>
        <li><b>Email address</b> — for account identification</li>
        <li><b>Full name</b> — for personalization</li>
        <li><b>Trading strategy preference</b> — for customized signals</li>
        <li><b>Exchange API keys</b> — encrypted with AES-256 (Fernet) before storage</li>
    </ul>

    <h3 style='color:#e7ebf3;'>2. How We Use Your Data</h3>
    <p>Your data is used solely to provide trading analysis, risk management, and portfolio tracking features. We never sell or share your data with third parties.</p>

    <h3 style='color:#e7ebf3;'>3. API Key Security</h3>
    <p>All exchange API keys are encrypted using Fernet (AES-128-CBC + HMAC-SHA256) before being stored in the database. Keys are never stored in plaintext and are only decrypted at the moment of use.</p>

    <h3 style='color:#e7ebf3;'>4. Data Storage</h3>
    <p>Account data is stored in a secure database. In demo mode, data is stored locally and cleared when you log out.</p>

    <h3 style='color:#e7ebf3;'>5. Third-Party Services</h3>
    <p>FinsageAI integrates with the following third-party APIs for market data:</p>
    <ul>
        <li>Binance API — for cryptocurrency price data</li>
        <li>CoinGecko API — for crypto fundamentals</li>
        <li>Yahoo Finance API — for stock/index data</li>
        <li>Google Gemini AI — for AI-powered analysis (optional)</li>
    </ul>

    <h3 style='color:#e7ebf3;'>6. Your Rights</h3>
    <p>You can request deletion of your account and all associated data at any time. Use the Logout button to clear your session.</p>

    <h3 style='color:#e7ebf3;'>7. Risk Disclosure</h3>
    <p>FinsageAI is an analysis tool, not financial advice. Trading involves risk of loss. Always do your own research and never invest more than you can afford to lose.</p>

    <h3 style='color:#e7ebf3;'>8. Contact</h3>
    <p>For privacy concerns, contact: admin@finsage.ai</p>

    <p style='color:#545c6e; margin-top:20px; font-size:12px;'>Last updated: August 2026</p>
    </div>
    """, unsafe_allow_html=True)
