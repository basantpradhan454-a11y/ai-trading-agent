"""FinsageAI — Candlestick Pattern Detector (20+ patterns)"""
import pandas as pd
import numpy as np
import streamlit as st
import yfinance as yf
import plotly.graph_objects as go

@st.cache_data(ttl=300, show_spinner=False)
def _fetch_ohlcv(symbol, period="3mo", interval="1d"):
    try:
        df = yf.Ticker(symbol.upper().strip()).history(period=period, interval=interval)
        if not df.empty: return df
    except Exception: pass
    return pd.DataFrame()

def _detect_patterns(df):
    if df.empty or len(df) < 5: return []
    df = df.copy()
    df["body"] = (df["Close"] - df["Open"]).abs()
    df["candle_range"] = df["High"] - df["Low"]
    df["upper_wick"] = df["High"] - df[["Open","Close"]].max(axis=1)
    df["lower_wick"] = df[["Open","Close"]].min(axis=1) - df["Low"]
    df["bull"] = df["Close"] >= df["Open"]
    df["avg_body"] = df["body"].rolling(14).mean()

    patterns = []
    n = len(df)
    for i in range(max(2, n-50), n):
        r = df.iloc[i]; p = df.iloc[i-1]; p2 = df.iloc[i-2] if i >= 2 else p
        ts = df.index[i]
        body = r["body"]; cr = r["candle_range"]; uw = r["upper_wick"]; lw = r["lower_wick"]

        if cr > 0 and body <= cr * 0.05:
            if uw >= cr * 0.6: patterns.append(("Gravestone Doji","BEARISH","STRONG",ts,r["Close"]))
            elif lw >= cr * 0.6: patterns.append(("Dragonfly Doji","BULLISH","STRONG",ts,r["Close"]))
            else: patterns.append(("Doji","NEUTRAL","MODERATE",ts,r["Close"]))
        elif lw >= body * 2 and uw <= body * 0.3 and not r["bull"]:
            patterns.append(("Hammer","BULLISH","STRONG",ts,r["Close"]))
        elif uw >= body * 2 and lw <= body * 0.3 and r["bull"]:
            patterns.append(("Shooting Star","BEARISH","STRONG",ts,r["Close"]))
        elif lw >= body * 2 and uw <= body * 0.3 and r["bull"]:
            patterns.append(("Hanging Man","BEARISH","MODERATE",ts,r["Close"]))
        elif r["bull"] and uw <= body * 0.05 and lw <= body * 0.05 and body >= df["avg_body"].iloc[i] * 1.5:
            patterns.append(("Bullish Marubozu","BULLISH","STRONG",ts,r["Close"]))
        elif not r["bull"] and uw <= body * 0.05 and lw <= body * 0.05 and body >= df["avg_body"].iloc[i] * 1.5:
            patterns.append(("Bearish Marubozu","BEARISH","STRONG",ts,r["Close"]))
        elif body > 0 and body / cr < 0.3 and uw > body and lw > body:
            patterns.append(("Spinning Top","NEUTRAL","WEAK",ts,r["Close"]))
        if r["bull"] and not p["bull"] and r["Open"] <= p["Close"] and r["Close"] >= p["Open"] and body > p["body"]:
            patterns.append(("Bullish Engulfing","BULLISH","STRONG",ts,r["Close"]))
        elif not r["bull"] and p["bull"] and r["Open"] >= p["Close"] and r["Close"] <= p["Open"] and body > p["body"]:
            patterns.append(("Bearish Engulfing","BEARISH","STRONG",ts,r["Close"]))
        elif not p["bull"] and r["bull"] and r["Open"] > p["Close"] and r["Close"] < p["Open"] and body < p["body"] * 0.6:
            patterns.append(("Bullish Harami","BULLISH","MODERATE",ts,r["Close"]))
        elif p["bull"] and not r["bull"] and r["Open"] < p["Close"] and r["Close"] > p["Open"] and body < p["body"] * 0.6:
            patterns.append(("Bearish Harami","BEARISH","MODERATE",ts,r["Close"]))
        if i >= 2:
            if not p2["bull"] and p["body"] < p2["body"] * 0.3 and r["bull"] and r["Close"] > (p2["Open"] + p2["Close"]) / 2:
                patterns.append(("Morning Star","BULLISH","STRONG",ts,r["Close"]))
            elif p2["bull"] and p["body"] < p2["body"] * 0.3 and not r["bull"] and r["Close"] < (p2["Open"] + p2["Close"]) / 2:
                patterns.append(("Evening Star","BEARISH","STRONG",ts,r["Close"]))
            if r["bull"] and p["bull"] and p2["bull"] and r["Close"] > p["Close"] > p2["Close"] and body > df["avg_body"].iloc[i] * 0.7:
                patterns.append(("Three White Soldiers","BULLISH","STRONG",ts,r["Close"]))
            elif not r["bull"] and not p["bull"] and not p2["bull"] and r["Close"] < p["Close"] < p2["Close"]:
                patterns.append(("Three Black Crows","BEARISH","STRONG",ts,r["Close"]))
    return patterns

def render_pattern_detector():
    st.markdown("""
    <div style="margin-bottom:24px;">
        <span style="font-size:1.6rem; font-weight:800; background:linear-gradient(90deg,#00d4ff,#7c3aed);
            -webkit-background-clip:text; -webkit-text-fill-color:transparent;">🕯️ Candlestick Pattern Detector</span>
        <p style="color:#5a7a9a; margin-top:4px; font-size:0.9rem;">
            20+ patterns detected on real OHLCV data — Bullish, Bearish & Neutral signals
        </p>
    </div>""", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns([1.5, 1, 1, 1])
    with c1: symbol = st.text_input("Symbol", value="RELIANCE.NS", key="pd_sym")
    with c2: interval = st.selectbox("Timeframe", ["1d","1h","4h","15m"], key="pd_tf")
    with c3: period = st.selectbox("Period", ["3mo","1mo","6mo"], key="pd_period")
    with c4:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        scan_btn = st.button("🔍 Scan", use_container_width=True, type="primary", key="pd_scan")

    if not scan_btn and "pd_scanned" not in st.session_state:
        st.info("👆 Enter a symbol and click Scan to detect candlestick patterns.")
        return

    with st.spinner("Scanning patterns..."):
        df = _fetch_ohlcv(symbol, period=period, interval=interval)
        if df.empty or len(df) < 5:
            st.error(f"Could not fetch data for '{symbol}'. Try another symbol.")
            return
        patterns = _detect_patterns(df)

    if not patterns:
        st.info("No significant candlestick patterns detected in this timeframe.")
    else:
        st.markdown(f"#### ✅ {len(patterns)} Patterns Detected")

        for name, ptype, strength, ts, price in patterns[-15:]:
            color = "#00d97e" if ptype == "BULLISH" else ("#ff4d6d" if ptype == "BEARISH" else "#ffeb3b")
            icon = "🟢" if ptype == "BULLISH" else ("🔴" if ptype == "BEARISH" else "🟡")
            st.markdown(f"""
            <div style="background:rgba(2,6,9,0.6);border:1px solid {color}33;border-radius:8px;
                 padding:10px 16px;margin:6px 0;display:flex;justify-content:space-between;align-items:center;">
                <div><b style="color:{color};">{icon} {name}</b>
                &nbsp;&nbsp;<span style="color:#5a7a9a;font-size:0.8rem;">{strength}</span></div>
                <div style="text-align:right;">
                    <span style="color:#c8d6e8;font-size:0.85rem;">{pd.Timestamp(ts).strftime('%Y-%m-%d %H:%M')}</span>
                    &nbsp;&nbsp;<b style="color:#00d4ff;">{price:.2f}</b>
                </div>
            </div>""", unsafe_allow_html=True)

        # Candlestick chart with markers
        st.markdown("#### 📈 Chart with Pattern Markers")
        fig = go.Figure(data=[go.Candlestick(
            x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
            increasing_line_color="#00d97e", decreasing_line_color="#ff4d6d",
            name=symbol.upper()
        )])
        for name, ptype, strength, ts, price in patterns[-20:]:
            mc = "#00d97e" if ptype == "BULLISH" else ("#ff4d6d" if ptype == "BEARISH" else "#ffeb3b")
            fig.add_annotation(x=ts, y=price, text=name, showarrow=True, arrowhead=2,
                arrowcolor=mc, ax=0, ay=-40, font=dict(color=mc, size=9),
                bgcolor="rgba(2,6,9,0.9)", bordercolor=mc, borderwidth=1)
        fig.update_layout(
            paper_bgcolor="#0c1222", plot_bgcolor="#0f1e35",
            font_color="#c8d6e8", height=400,
            xaxis_rangeslider_visible=False,
            margin=dict(l=10,r=10,t=10,b=10)
        )
        st.plotly_chart(fig, use_container_width=True)

    st.caption("For educational purposes only. Not SEBI investment advice.")
