"""
FinsageAI — Advanced Market Analyzer
Technical Indicators + Groq AI Signal Generation
"""
import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st
import requests
import json
import os
from datetime import datetime

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

def _get_groq_key():
    try:
        v = st.secrets.get("GROQ_API_KEY", "")
        if v: return v
    except Exception:
        pass
    return os.environ.get("GROQ_API_KEY", "") or os.environ.get("GROW_API_KEY", "")

@st.cache_data(ttl=300, show_spinner=False)
def _fetch_ohlcv(symbol, period="6mo"):
    symbol = symbol.upper().strip()
    try:
        df = yf.Ticker(symbol).history(period=period, interval="1d")
        if not df.empty:
            df.index = pd.to_datetime(df.index)
            return df
    except Exception:
        pass
    return pd.DataFrame()

def _calc_rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(com=period-1, min_periods=period).mean()
    loss = (-delta.clip(upper=0)).ewm(com=period-1, min_periods=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return (100 - (100 / (1 + rs))).round(2)

def _calc_macd(close, fast=12, slow=26, sig=9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_ln = macd_line.ewm(span=sig, adjust=False).mean()
    return macd_line.round(4), signal_ln.round(4), (macd_line - signal_ln).round(4)

def _calc_bb(close, period=20, std=2.0):
    sma = close.rolling(period).mean()
    sigma = close.rolling(period).std()
    return (sma + sigma*std).round(2), sma.round(2), (sma - sigma*std).round(2)

def _calc_atr(high, low, close, period=14):
    tr = pd.concat([high-low, (high-close.shift()).abs(), (low-close.shift()).abs()], axis=1).max(axis=1)
    return tr.ewm(com=period-1, min_periods=period).mean().round(4)

def _calc_stoch(high, low, close, k=14, d=3):
    ll = low.rolling(k).min()
    hh = high.rolling(k).max()
    pct_k = 100 * (close - ll) / (hh - ll).replace(0, np.nan)
    return pct_k.round(2), pct_k.rolling(d).mean().round(2)

def _calc_adx(high, low, close, period=14):
    plus_dm = high.diff().clip(lower=0)
    minus_dm = (-low.diff()).clip(lower=0)
    tr = pd.concat([high-low, (high-close.shift()).abs(), (low-close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(com=period-1, min_periods=period).mean()
    plus_di = 100 * plus_dm.ewm(com=period-1, min_periods=period).mean() / atr
    minus_di = 100 * minus_dm.ewm(com=period-1, min_periods=period).mean() / atr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return dx.ewm(com=period-1, min_periods=period).mean().round(2)

def _calc_obv(close, vol):
    direction = close.diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
    return (vol * direction).cumsum()

def _generate_signals(df):
    if df.empty or len(df) < 30:
        return {"score": 0, "overall": "NEUTRAL", "signals": [], "latest_price": 0, "rsi": 50}
    row = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 2 else row
    sigs = []
    score = 0
    close = float(row["Close"])

    rsi = float(row.get("RSI", 50))
    if rsi < 30: score += 20; sigs.append({"indicator":"RSI","signal":"STRONG BUY","value":f"{rsi:.1f}","note":"Oversold (<30)"})
    elif rsi < 40: score += 10; sigs.append({"indicator":"RSI","signal":"BUY","value":f"{rsi:.1f}","note":"Approaching oversold"})
    elif rsi > 70: score -= 20; sigs.append({"indicator":"RSI","signal":"STRONG SELL","value":f"{rsi:.1f}","note":"Overbought (>70)"})
    elif rsi > 60: score -= 10; sigs.append({"indicator":"RSI","signal":"SELL","value":f"{rsi:.1f}","note":"Approaching overbought"})
    else: sigs.append({"indicator":"RSI","signal":"NEUTRAL","value":f"{rsi:.1f}","note":"Mid-range"})

    macd = float(row.get("MACD",0)); macd_sig = float(row.get("MACD_Sig",0))
    macd_hist = float(row.get("MACD_Hist",0)); prev_hist = float(prev.get("MACD_Hist",0))
    prev_macd = float(prev.get("MACD",0)); prev_ms = float(prev.get("MACD_Sig",0))
    if macd > macd_sig and prev_macd <= prev_ms: score += 20; sigs.append({"indicator":"MACD","signal":"BUY","value":f"{macd:.4f}","note":"Bullish crossover"})
    elif macd < macd_sig and prev_macd >= prev_ms: score -= 20; sigs.append({"indicator":"MACD","signal":"SELL","value":f"{macd:.4f}","note":"Bearish crossover"})
    elif macd_hist > 0 and macd_hist > prev_hist: score += 10; sigs.append({"indicator":"MACD","signal":"BUY","value":f"{macd:.4f}","note":"Bullish momentum"})
    elif macd_hist < 0 and macd_hist < prev_hist: score -= 10; sigs.append({"indicator":"MACD","signal":"SELL","value":f"{macd:.4f}","note":"Bearish momentum"})
    else: sigs.append({"indicator":"MACD","signal":"NEUTRAL","value":f"{macd:.4f}","note":"No clear signal"})

    pct_b = float(row.get("%B",0.5)); bb_width = float(row.get("BB_Width",10))
    if pct_b < 0.05: score += 15; sigs.append({"indicator":"BB","signal":"STRONG BUY","value":f"%B:{pct_b:.2f}","note":"Price at lower band"})
    elif pct_b > 0.95: score -= 15; sigs.append({"indicator":"BB","signal":"STRONG SELL","value":f"%B:{pct_b:.2f}","note":"Price at upper band"})
    elif bb_width < 5: sigs.append({"indicator":"BB","signal":"WATCH","value":f"W:{bb_width:.1f}%","note":"Squeeze — breakout incoming"})
    else: sigs.append({"indicator":"BB","signal":"NEUTRAL","value":f"%B:{pct_b:.2f}","note":"Inside bands"})

    e20 = float(row.get("EMA_20",close)); e50 = float(row.get("EMA_50",close))
    if close > e20 > e50: score += 10; sigs.append({"indicator":"EMA Trend","signal":"BUY","value":"P>E20>E50","note":"Uptrend"})
    elif close < e20 < e50: score -= 10; sigs.append({"indicator":"EMA Trend","signal":"SELL","value":"P<E20<E50","note":"Downtrend"})
    else: sigs.append({"indicator":"EMA Trend","signal":"NEUTRAL","value":"Mixed","note":"No clear trend"})

    vol_ratio = float(row.get("Vol_Ratio",1.0)); chg_1d = float(row.get("Chg_1d",0))
    if vol_ratio > 2.0 and chg_1d > 0: score += 10; sigs.append({"indicator":"Volume","signal":"BUY","value":f"{vol_ratio:.1f}x","note":"High-vol breakout"})
    elif vol_ratio > 2.0 and chg_1d < 0: score -= 10; sigs.append({"indicator":"Volume","signal":"SELL","value":f"{vol_ratio:.1f}x","note":"High-vol breakdown"})
    else: sigs.append({"indicator":"Volume","signal":"NEUTRAL","value":f"{vol_ratio:.1f}x","note":"Normal volume"})

    sk = float(row.get("Stoch_K",50)); sd = float(row.get("Stoch_D",50))
    if sk < 20 and sd < 20: score += 10; sigs.append({"indicator":"Stochastic","signal":"BUY","value":f"K:{sk:.0f}","note":"Oversold"})
    elif sk > 80 and sd > 80: score -= 10; sigs.append({"indicator":"Stochastic","signal":"SELL","value":f"K:{sk:.0f}","note":"Overbought"})
    else: sigs.append({"indicator":"Stochastic","signal":"NEUTRAL","value":f"K:{sk:.0f}","note":"Mid-range"})

    score = max(-100, min(100, score))
    if score >= 40: overall = "STRONG BUY"
    elif score >= 15: overall = "BUY"
    elif score <= -40: overall = "STRONG SELL"
    elif score <= -15: overall = "SELL"
    else: overall = "NEUTRAL / HOLD"

    return {"score": score, "overall": overall, "signals": sigs,
            "latest_price": round(close, 2), "rsi": round(rsi, 1),
            "macd": round(macd, 4), "macd_hist": round(macd_hist, 4),
            "atr": round(float(row.get("ATR",0)), 4),
            "adx": round(float(row.get("ADX",0)), 1),
            "vol_ratio": round(vol_ratio, 2), "stoch_k": round(sk, 1),
            "bb_width": round(bb_width, 2), "pct_b": round(pct_b, 4)}

def _groq_analysis(symbol, tech, df):
    api_key = _get_groq_key()
    sig_lines = "\n".join([f"  - {s['indicator']}: {s['signal']} | {s['value']} | {s['note']}" for s in tech.get("signals", [])])
    prompt = f"""You are a professional stock analyst. Analyze and give a trading recommendation.

ASSET: {symbol}
Price: {tech.get('latest_price')} | RSI: {tech.get('rsi')} | MACD Hist: {tech.get('macd_hist')}
ADX: {tech.get('adx')} | ATR: {tech.get('atr')} | BB %B: {tech.get('pct_b')}
Volume vs 20d avg: {tech.get('vol_ratio')}x | Stoch K: {tech.get('stoch_k')}

INDICATOR SIGNALS:
{sig_lines}

Technical Score: {tech.get('score')}/100 -> Signal: {tech.get('overall')}

Respond in this JSON format only:
{{"recommendation":"STRONG BUY/BUY/HOLD/SELL/STRONG SELL","confidence":"HIGH/MEDIUM/LOW","entry_price":"price","stop_loss":"price","target_1":"price","target_2":"price","risk_reward":"1:X","timeframe":"SHORT/MEDIUM/LONG TERM","reasoning":"3-4 sentence explanation","key_risks":"2-3 risks","key_catalysts":"2-3 catalysts"}}"""

    if not api_key:
        return {"recommendation": tech.get("overall","NEUTRAL"), "confidence":"MEDIUM",
                "entry_price": str(tech.get("latest_price",0)), "stop_loss":"N/A",
                "target_1":"N/A", "target_2":"N/A", "risk_reward":"N/A",
                "timeframe":"SHORT TERM", "reasoning": f"Rule-based score: {tech.get('score')}/100. Add GROQ_API_KEY for AI analysis.",
                "key_risks":"Macro events, earnings surprise", "key_catalysts":"Volume breakout, sector momentum",
                "source":"Rule-based engine"}

    try:
        resp = requests.post(GROQ_API_URL, headers={"Authorization":f"Bearer {api_key}","Content-Type":"application/json"},
            json={"model":"llama-3.3-70b-versatile","messages":[{"role":"user","content":prompt}],"temperature":0.25,"max_tokens":900},
            timeout=20)
        if resp.status_code == 200:
            raw = resp.json()["choices"][0]["message"]["content"].strip()
            raw = raw.replace("```json","").replace("```","").strip()
            result = json.loads(raw)
            result["source"] = "Groq AI - Llama 3.3 70B"
            return result
    except Exception:
        pass
    return {"recommendation": tech.get("overall","NEUTRAL"), "confidence":"MEDIUM",
            "entry_price": str(tech.get("latest_price",0)), "stop_loss":"N/A",
            "target_1":"N/A", "target_2":"N/A", "risk_reward":"N/A",
            "timeframe":"SHORT TERM", "reasoning": f"Rule-based score: {tech.get('score')}/100. AI temporarily unavailable.",
            "key_risks":"Macro events", "key_catalysts":"Volume breakout",
            "source":"Rule-based fallback"}

def render_advanced_analyzer():
    import plotly.graph_objects as go

    st.markdown("""
    <div style="margin-bottom:24px;">
        <span style="font-size:1.6rem; font-weight:800; background:linear-gradient(90deg,#00d4ff,#7c3aed);
            -webkit-background-clip:text; -webkit-text-fill-color:transparent;">📡 Advanced Market Analyzer</span>
        <p style="color:#5a7a9a; margin-top:4px; font-size:0.9rem;">
            10+ Technical Indicators · Groq AI Signal Generation · Real-time Analysis
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([3, 1])
    with col1:
        symbol = st.text_input("Asset Symbol", value="AAPL", key="adv_sym", help="e.g. AAPL, RELIANCE.NS, INFY.NS, BTC-USD")
    with col2:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        analyze_btn = st.button("🔍 Analyze", use_container_width=True, type="primary")

    sym = symbol.upper().strip()
    if not analyze_btn and "adv_last_sym" not in st.session_state:
        st.info("👆 Enter a symbol and click Analyze to get a full technical breakdown.")
        return
    if analyze_btn:
        st.session_state["adv_last_sym"] = sym
    sym = st.session_state.get("adv_last_sym", sym)

    with st.spinner(f"Fetching data for {sym}..."):
        df = _fetch_ohlcv(sym, period="6mo")
        if df.empty or len(df) < 30:
            st.error(f"Insufficient data for '{sym}'. Try another symbol.")
            return
        c, h, l, v = df["Close"], df["High"], df["Low"], df["Volume"]
        df["RSI"] = _calc_rsi(c)
        df["MACD"], df["MACD_Sig"], df["MACD_Hist"] = _calc_macd(c)
        df["BB_Up"], df["BB_Mid"], df["BB_Lo"] = _calc_bb(c)
        df["EMA_20"] = c.ewm(span=20, adjust=False).mean().round(2)
        df["EMA_50"] = c.ewm(span=50, adjust=False).mean().round(2)
        df["ATR"] = _calc_atr(h, l, c)
        df["Stoch_K"], df["Stoch_D"] = _calc_stoch(h, l, c)
        df["ADX"] = _calc_adx(h, l, c)
        df["OBV"] = _calc_obv(c, v)
        df["Vol_Ratio"] = (v / v.rolling(20).mean()).round(2)
        df["Chg_1d"] = c.pct_change(1).round(4)
        df["%B"] = ((c - df["BB_Lo"]) / (df["BB_Up"] - df["BB_Lo"])).round(4)
        df["BB_Width"] = ((df["BB_Up"] - df["BB_Lo"]) / df["BB_Mid"] * 100).round(2)
        tech = _generate_signals(df)
        ai_rec = _groq_analysis(sym, tech, df)

    score = tech["score"]; signal = tech["overall"]
    sig_color = "#00d97e" if "BUY" in signal else ("#ff4d6d" if "SELL" in signal else "#ffeb3b")

    st.markdown(f"""
    <div style="background:rgba(2,6,9,0.6);border:1px solid rgba(0,212,255,0.2);
         border-radius:12px;padding:20px 24px;margin-bottom:16px;">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <div><div style="font-size:0.7rem;color:#5a7a9a;letter-spacing:.1em;text-transform:uppercase;">Overall Signal</div>
            <div style="font-size:2rem;font-weight:800;color:{sig_color};">{signal}</div></div>
            <div style="text-align:right;"><div style="font-size:0.7rem;color:#5a7a9a;letter-spacing:.1em;text-transform:uppercase;">Score</div>
            <div style="font-size:2rem;font-weight:800;color:#00d4ff;">{score:+.0f}</div></div>
        </div>
        <div style="margin-top:12px;background:rgba(0,212,255,0.05);border-radius:8px;height:8px;overflow:hidden;">
            <div style="width:{(score+100)/2}%;height:100%;background:linear-gradient(90deg,#ff4d6d,#ffeb3b,#00d97e);border-radius:8px;"></div>
        </div>
    </div>""", unsafe_allow_html=True)

    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("Current Price", f"{tech['latest_price']}")
    mc2.metric("RSI (14)", f"{tech['rsi']}")
    mc3.metric("MACD Hist", f"{tech['macd_hist']}")
    mc4.metric("ADX", f"{tech['adx']}")

    st.markdown("#### 📊 Technical Indicators")
    for s in tech["signals"]:
        cs1, cs2, cs3 = st.columns([2, 1.5, 3])
        sig_c = "#00d97e" if "BUY" in s["signal"] else ("#ff4d6d" if "SELL" in s["signal"] else "#ffeb3b")
        with cs1: st.markdown(f"**{s['indicator']}**")
        with cs2: st.markdown(f"<span style='color:{sig_c};font-weight:700;'>{s['signal']}</span>", unsafe_allow_html=True)
        with cs3: st.caption(f"{s['value']} — {s['note']}")

    st.markdown("#### 🤖 AI Analysis")
    st.caption(f"Source: {ai_rec.get('source','Rule-based')}")
    ac1, ac2 = st.columns(2)
    with ac1:
        st.markdown(f"""<div style="background:rgba(2,6,9,0.6);border:1px solid rgba(0,212,255,0.15);border-radius:10px;padding:16px;">
            <div style="font-size:0.7rem;color:#5a7a9a;text-transform:uppercase;letter-spacing:.1em;">Recommendation</div>
            <div style="font-size:1.4rem;font-weight:700;color:{sig_color};">{ai_rec.get('recommendation','N/A')}</div>
            <div style="margin-top:8px;font-size:0.85rem;color:#c8d6e8;">{ai_rec.get('reasoning','')}</div></div>""", unsafe_allow_html=True)
    with ac2:
        st.markdown(f"""<div style="background:rgba(2,6,9,0.6);border:1px solid rgba(0,212,255,0.15);border-radius:10px;padding:16px;">
            <div style="font-size:0.7rem;color:#5a7a9a;text-transform:uppercase;letter-spacing:.1em;">Trade Setup</div>
            <div style="margin-top:8px;font-size:0.88rem;">
            <div><b>Entry:</b> {ai_rec.get('entry_price','N/A')}</div>
            <div><b>Stop Loss:</b> {ai_rec.get('stop_loss','N/A')}</div>
            <div><b>Target 1:</b> {ai_rec.get('target_1','N/A')}</div>
            <div><b>Target 2:</b> {ai_rec.get('target_2','N/A')}</div>
            <div><b>R:R:</b> {ai_rec.get('risk_reward','N/A')}</div>
            <div><b>Timeframe:</b> {ai_rec.get('timeframe','N/A')}</div></div></div>""", unsafe_allow_html=True)
    st.markdown(f"""<div style="background:rgba(2,6,9,0.4);border:1px solid rgba(0,212,255,0.1);border-radius:10px;padding:14px;margin-top:8px;">
        <div style="display:flex;gap:20px;flex-wrap:wrap;">
            <div><b style="color:#ff4d6d;">Risks:</b> {ai_rec.get('key_risks','N/A')}</div>
            <div><b style="color:#00d97e;">Catalysts:</b> {ai_rec.get('key_catalysts','N/A')}</div></div></div>""", unsafe_allow_html=True)
    st.caption("For educational purposes only. Not SEBI investment advice.")
