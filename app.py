"""
FinsageAI — Trading Intelligence Engine v7.0
Clean, modular, actually-works edition.
"""
import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os, sys, json, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

st.set_page_config(
    page_title="FinsageAI — Trading Intelligence Engine",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
:root {
    --bg: #0a0e1a;
    --card: #0f1525;
    --border: #1a2744;
    --accent: #00d4ff;
    --text: #e2eaf4;
    --muted: #6b8aad;
    --green: #00d97e;
    --red: #ff4d6d;
}
[data-testid="stAppViewContainer"] > .main { background: var(--bg); }
[data-testid="stSidebar"] { background: #060912; }
.stApp { background: var(--bg); }
#MainMenu, footer, header { display: none !important; }

div.stButton > button {
    background: #0f1525 !important; border: 1px solid #1a2744 !important;
    border-radius: 10px !important; color: #e2eaf4 !important;
    text-align: left !important; padding: 10px 14px !important;
    font-size: 0.85rem !important; width: 100% !important;
}
div.stButton > button:hover {
    border-color: #00d4ff !important; background: #0c182e !important;
    box-shadow: 0 0 8px rgba(0,212,255,0.15) !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background: #0f1525 !important; border: 1px solid #1a2744 !important;
    border-radius: 10px !important; color: #00d4ff !important;
    font-weight: 600 !important;
}
div[data-testid="stAlert"] {
    background: #0f1525 !important; border: 1px solid #1a2744 !important;
    border-radius: 10px !important;
}
</style>
""", unsafe_allow_html=True)

STOCK_LIST = [
    {"ticker": "RELIANCE.NS",  "name": "Reliance Industries",  "logo": "🛢️"},
    {"ticker": "TCS.NS",       "name": "Tata Consultancy",     "logo": "💻"},
    {"ticker": "HDFCBANK.NS",  "name": "HDFC Bank",            "logo": "🏦"},
    {"ticker": "INFY.NS",      "name": "Infosys",              "logo": "🔷"},
    {"ticker": "ICICIBANK.NS", "name": "ICICI Bank",           "logo": "🏧"},
    {"ticker": "SBIN.NS",      "name": "State Bank of India",  "logo": "🏛️"},
    {"ticker": "BAJFINANCE.NS","name": "Bajaj Finance",        "logo": "💰"},
    {"ticker": "TATAMOTORS.NS","name": "Tata Motors",          "logo": "🚗"},
    {"ticker": "AAPL",         "name": "Apple Inc.",           "logo": "🍎"},
    {"ticker": "MSFT",         "name": "Microsoft",            "logo": "🪟"},
    {"ticker": "GOOGL",        "name": "Alphabet (Google)",    "logo": "🔍"},
    {"ticker": "TSLA",         "name": "Tesla",                "logo": "⚡"},
    {"ticker": "NVDA",         "name": "NVIDIA",               "logo": "🎮"},
    {"ticker": "AMZN",         "name": "Amazon",               "logo": "📦"},
    {"ticker": "META",         "name": "Meta Platforms",      "logo": "📘"},
]

@st.cache_data(ttl=300, show_spinner=False)
def get_stock_info(ticker):
    try:
        t = yf.Ticker(ticker)
        info = t.fast_info
        return {
            "price": info.last_price or 0,
            "prev_close": info.previous_close or info.last_price or 0,
            "market_cap": info.market_cap or 0,
        }
    except:
        return {"price": 0, "prev_close": 0, "market_cap": 0}

@st.cache_data(ttl=300, show_spinner=False)
def get_ohlcv(ticker, period="3mo", interval="1d"):
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False)
        if df.empty:
            return pd.DataFrame()
        df.columns = [c.lower() if isinstance(c, str) else c[0].lower() for c in df.columns]
        return df
    except:
        return pd.DataFrame()

@st.cache_data(ttl=300, show_spinner=False)
def get_full_info(ticker):
    try:
        t = yf.Ticker(ticker)
        info = t.info
        return {
            "pe_ratio": info.get("trailingPE", "N/A"),
            "market_cap": info.get("marketCap", "N/A"),
            "revenue": info.get("totalRevenue", "N/A"),
            "profit_margin": info.get("profitMargins", "N/A"),
            "52w_high": info.get("fiftyTwoWeekHigh", "N/A"),
            "52w_low": info.get("fiftyTwoWeekLow", "N/A"),
            "dividend_yield": info.get("dividendYield", "N/A"),
            "beta": info.get("beta", "N/A"),
            "name": info.get("shortName", ticker),
            "description": info.get("longBusinessSummary", ""),
        }
    except:
        return {}

def calc_indicators(df):
    if df.empty or len(df) < 30:
        return df
    df = df.copy()
    delta = df["close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss
    df["rsi"] = 100 - (100 / (1 + rs))
    df["ma20"] = df["close"].rolling(20).mean()
    df["ma50"] = df["close"].rolling(50).mean()
    ema12 = df["close"].ewm(span=12).mean()
    ema26 = df["close"].ewm(span=26).mean()
    df["macd"] = ema12 - ema26
    df["signal"] = df["macd"].ewm(span=9).mean()
    df["bb_mid"] = df["close"].rolling(20).mean()
    df["bb_std"] = df["close"].rolling(20).std()
    df["bb_upper"] = df["bb_mid"] + 2 * df["bb_std"]
    df["bb_lower"] = df["bb_mid"] - 2 * df["bb_std"]
    return df

def detect_patterns(df):
    patterns = []
    if len(df) < 5:
        return patterns
    last = df.iloc[-1]
    prev = df.iloc[-2]
    prev2 = df.iloc[-3]
    body = abs(last["close"] - last["open"])
    rng = last["high"] - last["low"]
    upper_wick = last["high"] - max(last["open"], last["close"])
    lower_wick = min(last["open"], last["close"]) - last["low"]
    if rng > 0 and body / rng < 0.1:
        patterns.append({"name": "Doji", "signal": "Neutral", "desc": "Indecision — possible reversal"})
    if lower_wick > 2 * body and upper_wick < body and last["close"] < prev["close"]:
        patterns.append({"name": "Hammer", "signal": "Bullish", "desc": "Potential bottom reversal"})
    if upper_wick > 2 * body and lower_wick < body and last["close"] > prev["close"]:
        patterns.append({"name": "Shooting Star", "signal": "Bearish", "desc": "Potential top reversal"})
    if prev["close"] < prev["open"] and last["close"] > last["open"] and last["open"] < prev["close"] and last["close"] > prev["open"]:
        patterns.append({"name": "Bullish Engulfing", "signal": "Bullish", "desc": "Strong reversal signal"})
    if prev["close"] > prev["open"] and last["close"] < last["open"] and last["open"] > prev["close"] and last["close"] < prev["open"]:
        patterns.append({"name": "Bearish Engulfing", "signal": "Bearish", "desc": "Strong downtrend signal"})
    return patterns

def format_num(n):
    if n == "N/A" or n is None: return "N/A"
    try:
        n = float(n)
        if abs(n) >= 1e12: return f"{n/1e12:.2f}T"
        if abs(n) >= 1e9:  return f"{n/1e9:.2f}B"
        if abs(n) >= 1e7:  return f"{n/1e7:.2f}Cr"
        if abs(n) >= 1e5:  return f"{n/1e5:.2f}L"
        return f"{n:,.0f}"
    except: return str(n)

# ─── Sidebar ──────────────────────────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style="padding: 10px 0 20px 0; text-align:center;">
            <span style="font-size:1.5rem; font-weight:800;
                background: linear-gradient(90deg,#00d4ff,#7c3aed);
                -webkit-background-clip:text; -webkit-text-fill-color:transparent;">
                FinsageAI
            </span>
            <p style="color:#304a66; font-size:0.7rem; margin-top:4px; letter-spacing:.08em;">
                TRADING INTELLIGENCE ENGINE v7.0
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("**Navigation**")
        pages = [
            "Stock Dashboard",
            "Market Overview",
            "Advanced Analyzer",
            "Pattern Detector",
            "Backtesting",
            "Portfolio",
            "News Feed",
            "AI Chat",
            "Academy",
            "Terms & Policy",
        ]
        st.session_state.setdefault("page", pages[0])
        current_idx = pages.index(st.session_state.page) if st.session_state.page in pages else 0
        st.session_state.page = st.selectbox("Page", pages, label_visibility="collapsed",
                                              index=current_idx, key="nav_select")

        st.markdown("---")
        st.caption("Educational use only")
        st.caption("Not SEBI investment advice")
        st.caption("© 2026 FinsageAI")

# ─── Pages ─────────────────────────────────────────────────────────────────────

def page_stock_dashboard():
    st.markdown("## Stock Dashboard")

    search = st.text_input("Search stocks...", placeholder="Type name or ticker", key="sd_search")
    filtered = [s for s in STOCK_LIST if
                search.lower() in s["name"].lower() or
                search.lower() in s["ticker"].lower()] if search else STOCK_LIST

    if "sd_selected" not in st.session_state:
        st.session_state.sd_selected = None

    col_list, col_detail = st.columns([1, 2.5], gap="medium")

    with col_list:
        st.markdown(f"**Stocks ({len(filtered)})**")
        for s in filtered:
            info = get_stock_info(s["ticker"])
            price = info["price"]
            prev = info["prev_close"]
            chg_pct = ((price - prev) / prev * 100) if prev and prev > 0 else 0
            arrow = "+" if chg_pct >= 0 else "-"
            label = f"{s['logo']} {s['name'][:20]}  {arrow}{abs(chg_pct):.2f}%"
            if st.button(label, key=f"sd_{s['ticker']}", use_container_width=True):
                st.session_state.sd_selected = s["ticker"]
                st.rerun()

    with col_detail:
        sel = st.session_state.sd_selected
        if not sel:
            st.info("Select a stock from the list to see detailed analysis")
        else:
            stock_info = next((s for s in STOCK_LIST if s["ticker"] == sel), {"name": sel, "logo": "📊"})
            st.markdown(f"### {stock_info['logo']} {stock_info['name']} — `{sel}`")

            chart_type = st.radio("Chart Type",
                ["TradingView", "Candlestick", "Line Chart"],
                horizontal=True, key="sd_chart")

            if chart_type == "TradingView":
                tv_sym = sel.replace(".NS", "").replace(".BSE", "")
                if ".NS" in sel: tv_sym = f"NSE:{tv_sym}"
                elif ".BSE" in sel: tv_sym = f"BSE:{tv_sym}"
                else: tv_sym = f"NASDAQ:{tv_sym}"

                components.html(f"""
                <div style="height:450px;">
                <script src="https://s3.tradingview.com/tv.js"></script>
                <script>
                new TradingView.widget({{
                    "width": "100%", "height": 450,
                    "symbol": "{tv_sym}",
                    "interval": "D", "timezone": "Asia/Kolkata",
                    "theme": "dark", "style": "1", "locale": "en",
                    "toolbar_bg": "#0a0e1a",
                    "enable_publishing": false, "allow_symbol_change": true,
                    "studies": ["RSI@tv-basicstudies","MACD@tv-basicstudies"],
                    "container_id": "tv_chart"
                }});
                </script>
                <div id="tv_chart" style="height:450px;"></div>
                </div>
                """, height=460)

            elif chart_type in ["Candlestick", "Line Chart"]:
                period = st.select_slider("Period", ["1mo","3mo","6mo","1y","2y"], value="3mo", key="sd_period")
                df = get_ohlcv(sel, period=period)
                if df.empty:
                    st.error("Could not fetch data. Market might be closed.")
                else:
                    df = calc_indicators(df)
                    fig = go.Figure()
                    if chart_type == "Candlestick":
                        fig.add_trace(go.Candlestick(
                            x=df.index, open=df["open"], high=df["high"],
                            low=df["low"], close=df["close"], name="OHLC"
                        ))
                        if "ma20" in df.columns:
                            fig.add_trace(go.Scatter(x=df.index, y=df["ma20"], name="MA20",
                                line=dict(color="#00d4ff", width=1)))
                        if "ma50" in df.columns:
                            fig.add_trace(go.Scatter(x=df.index, y=df["ma50"], name="MA50",
                                line=dict(color="#7c3aed", width=1)))
                        if "bb_upper" in df.columns:
                            fig.add_trace(go.Scatter(x=df.index, y=df["bb_upper"], name="BB Upper",
                                line=dict(color="#2a3f5f", width=1, dash="dash"), opacity=0.5))
                            fig.add_trace(go.Scatter(x=df.index, y=df["bb_lower"], name="BB Lower",
                                line=dict(color="#2a3f5f", width=1, dash="dash"), opacity=0.5,
                                fill="tonexty", fillcolor="rgba(42,63,95,0.1)"))
                    else:
                        fig.add_trace(go.Scatter(x=df.index, y=df["close"], name="Close",
                            line=dict(color="#00d4ff", width=2)))
                        if "ma20" in df.columns:
                            fig.add_trace(go.Scatter(x=df.index, y=df["ma20"], name="MA20",
                                line=dict(color="#7c3aed", width=1.5)))

                    fig.update_layout(
                        template="plotly_dark",
                        paper_bgcolor="#0a0e1a", plot_bgcolor="#0a0e1a",
                        font=dict(color="#e2eaf4"), height=450,
                        margin=dict(l=0, r=0, t=10, b=0),
                        xaxis_rangeslider_visible=False,
                        showlegend=True, legend=dict(orientation="h", y=1.02),
                    )
                    fig.update_xaxes(gridcolor="#1a2744")
                    fig.update_yaxes(gridcolor="#1a2744")
                    st.plotly_chart(fig, use_container_width=True)

                    pats = detect_patterns(df)
                    if pats:
                        st.markdown("**Detected Patterns:**")
                        for p in pats:
                            emoji = "🟢" if "Bullish" in p["signal"] else "🔴" if "Bearish" in p["signal"] else "⚠️"
                            st.markdown(f"- {emoji} **{p['name']}** — {p['signal']} — {p['desc']}")

            st.markdown("---")
            st.markdown("### Fundamentals")
            full = get_full_info(sel)
            if full and full.get("pe_ratio") != "N/A":
                c1, c2, c3, c4 = st.columns(4)
                with c1: st.metric("P/E Ratio", str(full.get("pe_ratio", "N/A")))
                with c2: st.metric("52W High", str(full.get("52w_high", "N/A")))
                with c3: st.metric("52W Low", str(full.get("52w_low", "N/A")))
                with c4: st.metric("Beta", str(full.get("beta", "N/A")))

                c5, c6, c7, c8 = st.columns(4)
                with c5: st.metric("Market Cap", format_num(full.get("market_cap", "N/A")))
                with c6: st.metric("Revenue", format_num(full.get("revenue", "N/A")))
                pm = full.get("profit_margin", "N/A")
                with c7: st.metric("Profit Margin", f"{pm*100:.1f}%" if isinstance(pm, (int,float)) else "N/A")
                dy = full.get("dividend_yield", "N/A")
                with c8: st.metric("Div Yield", f"{dy*100:.2f}%" if isinstance(dy, (int,float)) else "N/A")

                if full.get("description"):
                    with st.expander("Company Description"):
                        st.write(full["description"])
            else:
                st.warning("Could not load fundamentals for this stock.")


def page_market_overview():
    st.markdown("## Market Overview")
    st.markdown("Live market snapshot of top stocks")

    cols = st.columns(5)
    for i, s in enumerate(STOCK_LIST[:5]):
        info = get_stock_info(s["ticker"])
        price = info["price"]
        prev = info["prev_close"]
        chg_pct = ((price - prev) / prev * 100) if prev and prev > 0 else 0
        with cols[i]:
            st.metric(
                label=f"{s['logo']} {s['name'][:12]}",
                value=f"{price:,.2f}",
                delta=f"{chg_pct:+.2f}%",
                delta_color="normal" if chg_pct >= 0 else "inverse"
            )

    st.markdown("---")
    st.markdown("### All Stocks")
    data = []
    for s in STOCK_LIST:
        info = get_stock_info(s["ticker"])
        price = info["price"]
        prev = info["prev_close"]
        chg_pct = ((price - prev) / prev * 100) if prev and prev > 0 else 0
        data.append({
            "Stock": f"{s['logo']} {s['name']}",
            "Ticker": s["ticker"],
            "Price": f"{price:,.2f}",
            "Change %": f"{chg_pct:+.2f}%",
            "Trend": "UP" if chg_pct >= 0 else "DOWN",
        })
    st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

    st.markdown("### RSI Scanner")
    rsi_data = []
    for s in STOCK_LIST:
        df = get_ohlcv(s["ticker"], period="3mo")
        if not df.empty and len(df) > 14:
            df = calc_indicators(df)
            last_rsi = df["rsi"].iloc[-1]
            signal = "Oversold" if last_rsi < 30 else "Overbought" if last_rsi > 70 else "Neutral"
            rsi_data.append({"Stock": s["name"], "RSI": f"{last_rsi:.1f}", "Signal": signal})
    if rsi_data:
        st.dataframe(pd.DataFrame(rsi_data), use_container_width=True, hide_index=True)


def page_advanced_analyzer():
    st.markdown("## Advanced Market Analyzer")
    st.markdown("Deep technical analysis with AI-powered insights")

    sel = st.selectbox("Select stock", [f"{s['logo']} {s['name']} ({s['ticker']})" for s in STOCK_LIST],
                       key="aa_sel")
    ticker = sel.split("(")[-1].rstrip(")")

    period = st.select_slider("Analysis Period", ["1mo","3mo","6mo","1y","2y"], value="3mo", key="aa_period")

    df = get_ohlcv(ticker, period=period)
    if df.empty:
        st.error("Could not fetch data.")
        return

    df = calc_indicators(df)
    last = df.iloc[-1]

    st.markdown("### Technical Indicators")
    c1, c2, c3, c4, c5 = st.columns(5)

    rsi_val = last.get("rsi", 50)
    rsi_sig = "Oversold" if rsi_val < 30 else "Overbought" if rsi_val > 70 else "Neutral"

    macd_val = last.get("macd", 0)
    sig_val = last.get("signal", 0)
    macd_sig = "Bullish" if macd_val > sig_val else "Bearish"

    ma20 = last.get("ma20", 0)
    ma50 = last.get("ma50", 0)
    trend = "Uptrend" if ma20 > ma50 else "Downtrend"

    with c1: st.metric("RSI (14)", f"{rsi_val:.1f}", rsi_sig)
    with c2: st.metric("MACD", f"{macd_val:.2f}", macd_sig)
    with c3: st.metric("MA20", f"{ma20:.2f}", trend)
    with c4: st.metric("MA50", f"{ma50:.2f}", trend)
    with c5: st.metric("Volume", f"{last.get('volume', 0):,.0f}")

    st.markdown("### Price + Indicators")
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["open"], high=df["high"],
        low=df["low"], close=df["close"], name="OHLC"
    ))
    if "ma20" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["ma20"], name="MA20",
            line=dict(color="#00d4ff", width=1.5)))
    if "ma50" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["ma50"], name="MA50",
            line=dict(color="#7c3aed", width=1.5)))
    if "bb_upper" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["bb_upper"], name="BB Upper",
            line=dict(color="#2a3f5f", width=1, dash="dash"), opacity=0.4))
        fig.add_trace(go.Scatter(x=df.index, y=df["bb_lower"], name="BB Lower",
            line=dict(color="#2a3f5f", width=1, dash="dash"), opacity=0.4,
            fill="tonexty", fillcolor="rgba(42,63,95,0.1)"))
    fig.update_layout(template="plotly_dark", paper_bgcolor="#0a0e1a",
        plot_bgcolor="#0a0e1a", font=dict(color="#e2eaf4"),
        height=400, margin=dict(l=0,r=0,t=10,b=0),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", y=1.02))
    st.plotly_chart(fig, use_container_width=True)

    if "rsi" in df.columns:
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=df.index, y=df["rsi"], name="RSI",
            line=dict(color="#00d4ff", width=2)))
        fig2.add_hline(y=70, line_dash="dash", line_color="#ff4d6d", annotation_text="Overbought (70)")
        fig2.add_hline(y=30, line_dash="dash", line_color="#00d97e", annotation_text="Oversold (30)")
        fig2.update_layout(template="plotly_dark", paper_bgcolor="#0a0e1a",
            plot_bgcolor="#0a0e1a", font=dict(color="#e2eaf4"),
            height=250, margin=dict(l=0,r=0,t=10,b=0),
            yaxis=dict(range=[0,100]))
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("### AI Signal Analysis")
    groq_key = st.secrets.get("GROQ_API_KEY", os.environ.get("GROQ_API_KEY", ""))

    if st.button("Generate AI Analysis", key="aa_gen"):
        if not groq_key:
            st.warning("Groq API key not configured. Add GROQ_API_KEY in Streamlit Secrets.")
            st.info(f"""
            Technical Summary:
            - RSI: {rsi_val:.1f} ({rsi_sig})
            - MACD: {macd_val:.2f} vs Signal {sig_val:.2f} ({macd_sig})
            - Trend: {trend} (MA20 {'>' if ma20 > ma50 else '<'} MA50)
            - Volume: {last.get('volume', 0):,.0f}
            """)
        else:
            with st.spinner("AI analyzing market data..."):
                try:
                    import requests
                    prompt = f"""Analyze this stock technically and give a recommendation:
Ticker: {ticker}
Current Price: {last['close']:.2f}
RSI: {rsi_val:.1f}
MACD: {macd_val:.2f}, Signal: {sig_val:.2f}
MA20: {ma20:.2f}, MA50: {ma50:.2f}
Volume: {last.get('volume', 0):,.0f}
Trend: {trend}

Give: 1) Signal (BUY/SELL/HOLD) 2) Confidence % 3) Key levels 4) Brief reasoning (3-4 lines max)."""

                    resp = requests.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={"Authorization": f"Bearer {groq_key}",
                                 "Content-Type": "application/json"},
                        json={"model": "llama-3.3-70b-versatile",
                              "messages": [{"role": "user", "content": prompt}],
                              "max_tokens": 400, "temperature": 0.3},
                        timeout=30
                    )
                    if resp.status_code == 200:
                        result = resp.json()["choices"][0]["message"]["content"]
                        st.success("AI Analysis Ready")
                        st.markdown(result)
                    else:
                        st.error(f"API error: {resp.status_code}")
                except Exception as e:
                    st.error(f"Error: {e}")


def page_pattern_detector():
    st.markdown("## Candlestick Pattern Detector")
    st.markdown("Detect candlestick patterns across all stocks")

    sel = st.selectbox("Select stock", [f"{s['logo']} {s['name']} ({s['ticker']})" for s in STOCK_LIST],
                       key="pd_sel")
    ticker = sel.split("(")[-1].rstrip(")")

    period = st.select_slider("Period", ["1mo","3mo","6mo","1y"], value="3mo", key="pd_period")
    df = get_ohlcv(ticker, period=period)

    if df.empty:
        st.error("Could not fetch data.")
        return

    df = calc_indicators(df)

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["open"], high=df["high"],
        low=df["low"], close=df["close"], name="OHLC"
    ))
    if "ma20" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["ma20"], name="MA20",
            line=dict(color="#00d4ff", width=1.5)))
    if "ma50" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["ma50"], name="MA50",
            line=dict(color="#7c3aed", width=1.5)))

    fig.update_layout(template="plotly_dark", paper_bgcolor="#0a0e1a",
        plot_bgcolor="#0a0e1a", font=dict(color="#e2eaf4"),
        height=450, margin=dict(l=0,r=0,t=10,b=0),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", y=1.02))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Detected Patterns (Last 3 Candles)")
    pats = detect_patterns(df)
    if pats:
        for p in pats:
            emoji = "🟢" if "Bullish" in p["signal"] else "🔴" if "Bearish" in p["signal"] else "⚠️"
            st.markdown(f"{emoji} **{p['name']}** — {p['signal']} — {p['desc']}")
    else:
        st.info("No significant patterns detected in the last 3 candles.")

    st.markdown("---")
    st.markdown("### Multi-Stock Pattern Scanner")
    if st.button("Scan All Stocks", key="pd_scan"):
        with st.spinner("Scanning all stocks for patterns..."):
            scan_results = []
            for s in STOCK_LIST:
                d = get_ohlcv(s["ticker"], period="1mo")
                if d.empty or len(d) < 5:
                    continue
                d = calc_indicators(d)
                ps = detect_patterns(d)
                for p in ps:
                    scan_results.append({
                        "Stock": s["name"],
                        "Pattern": p["name"],
                        "Signal": p["signal"],
                        "Description": p["desc"],
                    })
            if scan_results:
                st.dataframe(pd.DataFrame(scan_results), use_container_width=True, hide_index=True)
            else:
                st.info("No patterns detected across stocks right now.")


def page_backtesting():
    st.markdown("## Strategy Backtesting")
    st.markdown("Test trading strategies on historical data")

    sel = st.selectbox("Select stock", [f"{s['logo']} {s['name']} ({s['ticker']})" for s in STOCK_LIST],
                       key="bt_sel")
    ticker = sel.split("(")[-1].rstrip(")")

    strategy = st.selectbox("Strategy", ["SMA Crossover (20/50)", "RSI Mean Reversion", "MACD Crossover"])
    period = st.select_slider("Backtest Period", ["6mo","1y","2y","5y"], value="1y", key="bt_period")

    df = get_ohlcv(ticker, period=period)
    if df.empty:
        st.error("Could not fetch data.")
        return

    df = calc_indicators(df)

    if strategy == "SMA Crossover (20/50)":
        df["signal"] = 0
        df.loc[df["ma20"] > df["ma50"], "signal"] = 1
        df.loc[df["ma20"] < df["ma50"], "signal"] = -1
    elif strategy == "RSI Mean Reversion":
        df["signal"] = 0
        df.loc[df["rsi"] < 30, "signal"] = 1
        df.loc[df["rsi"] > 70, "signal"] = -1
    else:
        df["signal"] = 0
        df.loc[df["macd"] > df["signal"], "signal"] = 1
        df.loc[df["macd"] < df["signal"], "signal"] = -1

    df["returns"] = df["close"].pct_change()
    df["strategy"] = df["signal"].shift(1) * df["returns"]
    df = df.dropna()
    buy_hold = (1 + df["returns"]).cumprod() * 100
    strat = (1 + df["strategy"]).cumprod() * 100

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Buy & Hold", f"{(buy_hold.iloc[-1]-100):.1f}%")
    with c2: st.metric("Strategy", f"{(strat.iloc[-1]-100):.1f}%")
    with c3: st.metric("Trades", f"{(df['signal'].diff().abs() > 0).sum()}")
    with c4:
        sr = df["strategy"].mean() / df["strategy"].std() * (252**0.5) if df["strategy"].std() > 0 else 0
        st.metric("Sharpe Ratio", f"{sr:.2f}")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=buy_hold, name="Buy & Hold",
        line=dict(color="#6b8aad", width=2)))
    fig.add_trace(go.Scatter(x=df.index, y=strat, name="Strategy",
        line=dict(color="#00d4ff", width=2)))
    fig.update_layout(template="plotly_dark", paper_bgcolor="#0a0e1a",
        plot_bgcolor="#0a0e1a", font=dict(color="#e2eaf4"),
        height=400, margin=dict(l=0,r=0,t=10,b=0),
        legend=dict(orientation="h", y=1.02))
    st.plotly_chart(fig, use_container_width=True)

    st.caption("Educational only. Past performance does not guarantee future results.")


def page_portfolio():
    st.markdown("## Portfolio Tracker")
    st.markdown("Track your virtual portfolio")

    if "portfolio" not in st.session_state:
        st.session_state.portfolio = []

    c1, c2, c3 = st.columns(3)
    with c1:
        sel = st.selectbox("Add Stock", [f"{s['name']} ({s['ticker']})" for s in STOCK_LIST], key="pf_add")
    with c2:
        qty = st.number_input("Quantity", min_value=1, value=10, key="pf_qty")
    with c3:
        price = st.number_input("Buy Price", min_value=0.0, value=100.0, step=0.5, key="pf_price")
        if st.button("Add to Portfolio", key="pf_add_btn"):
            ticker = sel.split("(")[-1].rstrip(")")
            st.session_state.portfolio.append({"ticker": ticker, "name": sel.split("(")[0].strip(), "qty": qty, "buy_price": price})
            st.rerun()

    if not st.session_state.portfolio:
        st.info("No holdings yet. Add stocks above to start tracking.")
        return

    st.markdown("### Current Holdings")
    data = []
    total_invested = 0
    total_current = 0
    for h in st.session_state.portfolio:
        info = get_stock_info(h["ticker"])
        cur_price = info["price"]
        invested = h["qty"] * h["buy_price"]
        current = h["qty"] * cur_price
        pnl = current - invested
        pnl_pct = (pnl / invested * 100) if invested else 0
        total_invested += invested
        total_current += current
        data.append({
            "Stock": h["name"], "Ticker": h["ticker"], "Qty": h["qty"],
            "Buy Price": f"{h['buy_price']:.2f}", "Current": f"{cur_price:.2f}",
            "Invested": f"{invested:,.2f}", "Current Value": f"{current:,.2f}",
            "P&L": f"{pnl:,.2f} ({pnl_pct:+.1f}%)", "Status": "UP" if pnl >= 0 else "DOWN",
        })

    st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

    total_pnl = total_current - total_invested
    total_pnl_pct = (total_pnl / total_invested * 100) if total_invested else 0
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("Total Invested", f"{total_invested:,.2f}")
    with c2: st.metric("Current Value", f"{total_current:,.2f}")
    with c3: st.metric("Total P&L", f"{total_pnl:,.2f}", f"{total_pnl_pct:+.1f}%")

    if st.button("Clear Portfolio", key="pf_clear"):
        st.session_state.portfolio = []
        st.rerun()


def page_news():
    st.markdown("## Market News Feed")
    st.markdown("Latest financial news")

    try:
        import feedparser
        feeds = [
            ("Google Finance", "https://news.google.com/rss/search?q=stock+market+india&hl=en-IN&gl=IN&ceid=IN:en"),
            ("Yahoo Finance", "https://finance.yahoo.com/news/rssindex"),
        ]
        all_news = []
        for name, url in feeds:
            try:
                parsed = feedparser.parse(url)
                for entry in parsed.entries[:10]:
                    all_news.append({
                        "Source": name, "Title": entry.get("title", ""),
                        "Link": entry.get("link", ""), "Published": entry.get("published", "")[:25],
                    })
            except:
                pass

        if all_news:
            for n in all_news[:20]:
                st.markdown(f"""
                <div style="background:#0f1525;border:1px solid #1a2744;border-radius:10px;
                    padding:12px 16px;margin-bottom:8px;">
                    <a href="{n['Link']}" target="_blank" style="color:#00d4ff;text-decoration:none;font-weight:600;">
                        {n['Title']}
                    </a>
                    <br><span style="color:#6b8aad;font-size:0.75rem;">{n['Source']} - {n['Published']}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Could not load news right now.")
    except ImportError:
        st.warning("feedparser not installed")


def page_ai_chat():
    st.markdown("## AI Trading Assistant")
    st.markdown("Ask questions about stocks, strategies, and market analysis")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            st.chat_message("user").write(msg["content"])
        else:
            st.chat_message("assistant").write(msg["content"])

    user_input = st.chat_input("Ask about stocks, strategies, technical analysis...")

    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        st.chat_message("user").write(user_input)

        gemini_key = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
        groq_key = st.secrets.get("GROQ_API_KEY", os.environ.get("GROQ_API_KEY", ""))

        response_text = ""
        if groq_key:
            try:
                import requests
                resp = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                    json={"model": "llama-3.3-70b-versatile",
                          "messages": [{"role": "system",
                            "content": "You are a helpful trading assistant. Keep answers concise and educational."},
                            {"role": "user", "content": user_input}],
                          "max_tokens": 500, "temperature": 0.4},
                    timeout=30
                )
                if resp.status_code == 200:
                    response_text = resp.json()["choices"][0]["message"]["content"]
            except:
                pass
        elif gemini_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=gemini_key)
                model = genai.GenerativeModel("gemini-1.5-flash")
                response_text = model.generate_content(f"You are a trading assistant. Answer concisely: {user_input}").text
            except:
                pass

        if not response_text:
            response_text = "I need a GROQ_API_KEY or GEMINI_API_KEY in Streamlit Secrets to provide AI responses. Meanwhile, always combine multiple indicators (RSI, MACD, Moving Averages) for better signal confirmation."

        st.session_state.chat_history.append({"role": "assistant", "content": response_text})
        st.chat_message("assistant").write(response_text)


def page_academy():
    st.markdown("## Trading Academy")
    st.markdown("Learn trading concepts")

    topics = {
        "Technical Analysis": {
            "Moving Averages (MA)": "MA smooths price data to show trend direction. MA20 crossing above MA50 is a 'Golden Cross' (bullish). Below = 'Death Cross' (bearish).",
            "RSI (Relative Strength Index)": "RSI measures 0-100. Below 30 = oversold (possible buy). Above 70 = overbought (possible sell). Best used with other indicators.",
            "MACD": "MACD = difference between 12 and 26 EMA. Signal line = 9 EMA of MACD. MACD above Signal = bullish momentum.",
            "Bollinger Bands": "20 SMA +/- 2 standard deviations. Upper band = overbought. Lower band = oversold. Bands squeeze before big moves.",
            "Candlestick Patterns": "Key patterns: Doji (indecision), Hammer (reversal), Engulfing (strong signal), Morning/Evening Star (3-candle reversal).",
        },
        "Fundamental Analysis": {
            "P/E Ratio": "Price-to-Earnings ratio. Low P/E may indicate undervalued stock. High P/E may mean overvalued or high growth expectations.",
            "Market Capitalization": "Total market value = share price x shares outstanding. Large cap (stable), Mid cap (growth), Small cap (volatile).",
            "Dividend Yield": "Annual dividend / share price. Higher yield = more income, but may signal slow growth.",
            "52-Week High/Low": "Shows the trading range over a year. Breaking above 52W high = bullish breakout.",
        },
        "Trading Strategies": {
            "Trend Following": "Buy when price is above MA50. Sell when below. Simple but effective in trending markets.",
            "Mean Reversion": "Buy when RSI < 30 (oversold). Sell when RSI > 70 (overbought). Works in range-bound markets.",
            "Breakout Trading": "Buy when price breaks above resistance with high volume. Sell when breaks below support.",
            "Position Sizing": "Never risk more than 2% of capital on a single trade.",
        },
    }

    for category, lessons in topics.items():
        st.markdown(f"### {category}")
        for title, content in lessons.items():
            with st.expander(f"📖 {title}"):
                st.write(content)

    st.markdown("---")
    st.info("All content is for educational purposes only. Not investment advice.")


def page_terms():
    st.markdown("## Terms of Service & Privacy Policy")
    st.markdown("""
    ### Terms of Service
    **Last updated:** July 2026

    **1. Educational Purpose**
    FinsageAI is an educational tool for learning about financial markets. All content is for educational purposes only.

    **2. Not Investment Advice**
    Nothing on this platform constitutes investment advice. Always consult a SEBI-registered advisor.

    **3. No Warranty**
    Market data may be delayed or inaccurate. We are not liable for any losses.

    **4. Risk Disclosure**
    Trading involves substantial risk. Never invest more than you can afford to lose.

    ---

    ### Privacy Policy

    **1. Data Collection**
    FinsageAI does not collect personal data. Portfolio data is stored locally in your browser session only.

    **2. API Keys**
    API keys are stored securely in Streamlit Secrets and never exposed to end users.

    **3. Third-Party Services**
    We use Yahoo Finance, TradingView, and optionally Groq/Gemini for AI features.

    **4. Contact**
    Questions? Contact the developer via GitHub.
    """)
    st.markdown("---")
    st.caption("© 2026 FinsageAI — Educational use only")


# ─── Main ──────────────────────────────────────────────────────────────────────
def main():
    render_sidebar()
    page = st.session_state.page

    if page == "Stock Dashboard":     page_stock_dashboard()
    elif page == "Market Overview":   page_market_overview()
    elif page == "Advanced Analyzer": page_advanced_analyzer()
    elif page == "Pattern Detector":  page_pattern_detector()
    elif page == "Backtesting":       page_backtesting()
    elif page == "Portfolio":         page_portfolio()
    elif page == "News Feed":         page_news()
    elif page == "AI Chat":           page_ai_chat()
    elif page == "Academy":           page_academy()
    elif page == "Terms & Policy":    page_terms()

if __name__ == "__main__":
    main()
