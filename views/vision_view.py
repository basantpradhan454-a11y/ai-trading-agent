"""FinsageAI — AI Vision Analyst (Chart Image → Strategy → Backtest)"""
import streamlit as st
import io
import json
import yfinance as yf
import pandas as pd
from datetime import date
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.backtest_engine import BacktestEngine

MAX_DAILY_USES = 5
STRATEGY_MAP = {
    "RSI_Oversold": ("RSI Oversold/Overbought", {"rsi_period": 14, "oversold": 30, "overbought": 70}),
    "MACD_Crossover": ("MACD Crossover", {"macd_fast": 12, "macd_slow": 26, "macd_signal": 9}),
    "EMA_Crossover": ("EMA Crossover", {"ema_fast": 9, "ema_slow": 21}),
    "Bollinger_Bounce": ("Bollinger Bands Bounce", {"bb_period": 20, "bb_std": 2}),
}


def _check_limit():
    today = str(date.today())
    if st.session_state.get("vision_date") != today:
        st.session_state["vision_date"] = today
        st.session_state["vision_uses"] = 0
    return st.session_state.get("vision_uses", 0)


def _analyze_with_gemini(img_bytes, api_key):
    try:
        from PIL import Image
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        img = Image.open(io.BytesIO(img_bytes))
        prompt = """You are an expert technical analyst. Analyze this stock/crypto chart image.
Respond ONLY with valid JSON (no markdown, no code blocks):
{
  "trend": "UPTREND or DOWNTREND or SIDEWAYS",
  "patterns_detected": ["list of pattern names"],
  "support_level": "approximate support description",
  "resistance_level": "approximate resistance description",
  "reasoning": "2-3 sentence analysis",
  "recommended_strategy": "RSI_Oversold or MACD_Crossover or EMA_Crossover or Bollinger_Bounce",
  "confidence": "HIGH or MEDIUM or LOW"
}"""
        response = model.generate_content([prompt, img])
        text = response.text.strip()
        if "```" in text:
            parts = text.split("```")
            for part in parts:
                if part.startswith("json"):
                    text = part[4:].strip()
                    break
                elif "{" in part:
                    text = part.strip(); break
        return json.loads(text)
    except Exception as e:
        return {"error": str(e), "trend": "UNKNOWN", "patterns_detected": [],
                "reasoning": f"AI analysis failed: {str(e)}. Check API key.",
                "recommended_strategy": "RSI_Oversold", "confidence": "LOW",
                "support_level": "N/A", "resistance_level": "N/A"}


def render_vision_page():
    st.markdown("""
    <div style="margin-bottom:20px;">
        <span style="font-size:1.6rem; font-weight:800; background:linear-gradient(90deg,#00d4ff,#7c3aed);
            -webkit-background-clip:text; -webkit-text-fill-color:transparent;">👁️ AI Vision Analyst</span>
        <p style="color:#5a7a9a; margin-top:4px; font-size:0.9rem;">
            Upload any chart screenshot → AI detects patterns → Auto-backtests a matching strategy
        </p>
    </div>
    """, unsafe_allow_html=True)

    uses_today = _check_limit()
    remaining = MAX_DAILY_USES - uses_today
    color = "#00d4ff" if remaining > 2 else ("#ffaa00" if remaining > 0 else "#ff4444")
    st.markdown(f"""
    <div style="background:rgba(0,212,255,0.04); border:1px solid rgba(0,212,255,0.12);
        border-radius:10px; padding:12px 16px; margin-bottom:16px; display:flex; align-items:center; gap:12px;">
        <span style="font-family:'JetBrains Mono',monospace; font-size:1.1rem; color:{color}; font-weight:700;">
            {uses_today}/{MAX_DAILY_USES}
        </span>
        <span style="color:#5a7a9a; font-size:0.85rem;">Daily analyses used &nbsp;·&nbsp; Resets at midnight</span>
    </div>
    """, unsafe_allow_html=True)

    if uses_today >= MAX_DAILY_USES:
        st.error(f"⛔ Daily limit of {MAX_DAILY_USES} analyses reached. Resets tomorrow.")
        return

    # Step 1
    st.markdown('<div style="font-size:0.68rem; letter-spacing:.1em; color:#00d4ff; text-transform:uppercase; margin-bottom:8px;">Step 1 — Gemini API Key</div>', unsafe_allow_html=True)
    api_key = st.text_input("Gemini API Key", type="password",
                             help="Free key: https://aistudio.google.com/app/apikey", key="vision_api_key")

    # Step 2
    st.markdown('<div style="font-size:0.68rem; letter-spacing:.1em; color:#00d4ff; text-transform:uppercase; margin:16px 0 8px;">Step 2 — Upload Chart Screenshot</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader("Upload chart image (PNG or JPG)", type=["png", "jpg", "jpeg"], key="vision_upload")

    if uploaded:
        try:
            from PIL import Image
            img_bytes = uploaded.read()
            img = Image.open(io.BytesIO(img_bytes))
            w, h = img.size
            st.image(img, caption=f"Uploaded chart ({w}×{h}px)", use_column_width=True)
            if w < 300 or h < 300:
                st.error("❌ Image too small. Minimum 300×300px required for accurate analysis.")
                return
        except Exception as e:
            st.error(f"Error loading image: {e}")
            return

        # Step 3
        st.markdown('<div style="font-size:0.68rem; letter-spacing:.1em; color:#00d4ff; text-transform:uppercase; margin:16px 0 8px;">Step 3 — Configure Backtest</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            ticker_bt = st.text_input("Backtest Ticker", "NIFTY50.NS",
                                       help="Which ticker to backtest on (e.g. RELIANCE.NS, AAPL)", key="vision_ticker")
        with col2:
            bt_period = st.selectbox("Backtest Period", ["6mo", "1y", "2y"], index=1, key="vision_period")

        if st.button("🔍 Analyze Chart & Auto-Backtest", type="primary", use_container_width=True, key="vision_run"):
            if not api_key:
                st.warning("⚠️ Enter your Gemini API key to use AI Vision analysis.")
                return

            with st.spinner("👁️ AI Vision analyzing your chart... (10-20 seconds)"):
                img_bytes_fresh = uploaded.getvalue()
                result = _analyze_with_gemini(img_bytes_fresh, api_key)
                st.session_state["vision_uses"] = uses_today + 1

            st.markdown("""<div style="background:#0f1e35; border:1px solid rgba(0,212,255,0.15);
                border-radius:14px; padding:20px 24px; margin:12px 0;">""", unsafe_allow_html=True)
            st.markdown('<div style="font-size:0.68rem; letter-spacing:.1em; color:#00d4ff; text-transform:uppercase; margin-bottom:12px;">AI Analysis Results</div>', unsafe_allow_html=True)

            trend = result.get("trend", "UNKNOWN")
            trend_icon = "📈" if trend == "UPTREND" else ("📉" if trend == "DOWNTREND" else "↔️")
            c1, c2, c3 = st.columns(3)
            c1.metric("Trend Detected", f"{trend_icon} {trend}")
            c2.metric("AI Confidence", result.get("confidence", "N/A"))
            c3.metric("Patterns Found", len(result.get("patterns_detected", [])))

            patterns = result.get("patterns_detected", [])
            if patterns:
                pat_html = " ".join([f'<span style="background:rgba(124,58,237,0.15); border:1px solid rgba(124,58,237,0.3); border-radius:20px; padding:3px 10px; font-size:0.78rem; color:#a78bfa;">{p}</span>' for p in patterns])
                st.markdown(f'<div style="margin:8px 0;">🕯️ Detected: {pat_html}</div>', unsafe_allow_html=True)

            col_s, col_r = st.columns(2)
            col_s.success(f"🟢 **Support:** {result.get('support_level', 'N/A')}")
            col_r.warning(f"🔴 **Resistance:** {result.get('resistance_level', 'N/A')}")

            with st.expander("🧠 AI Reasoning"):
                st.write(result.get("reasoning", "No reasoning provided."))
            st.markdown("</div>", unsafe_allow_html=True)

            if result.get("error"):
                st.warning(f"⚠️ AI had issues: {result['error']}. Running default strategy.")

            recommended = result.get("recommended_strategy", "RSI_Oversold")
            strat_name, strat_params = STRATEGY_MAP.get(recommended, STRATEGY_MAP["RSI_Oversold"])

            st.markdown(f'<div style="font-size:0.68rem; letter-spacing:.1em; color:#00d4ff; text-transform:uppercase; margin:16px 0 8px;">Auto-Backtest: {strat_name} on {ticker_bt}</div>', unsafe_allow_html=True)
            with st.spinner(f"Running {strat_name} backtest on {ticker_bt}..."):
                try:
                    df = yf.download(ticker_bt, period=bt_period, auto_adjust=True, progress=False)
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)
                    if df.empty:
                        st.error(f"No data for {ticker_bt}.")
                    else:
                        engine = BacktestEngine(df)
                        signals = engine.compile_signals(recommended, strat_params)
                        trade_df, metrics, full_df = engine.run(signals)
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Strategy Return", f"{metrics['Total Return (%)']}%")
                        c2.metric("vs Buy & Hold", f"{metrics['Benchmark Return (%)']}%")
                        c3.metric("Max Drawdown", f"{metrics['Max Drawdown (%)']}%")
                        c4.metric("Win Rate", f"{metrics['Win Rate (%)']}%")
                        st.plotly_chart(engine.build_equity_chart(full_df, trade_df), use_container_width=True)
                except Exception as e:
                    st.error(f"Backtest error: {e}")

            st.markdown("""
            <div style="background:rgba(255,68,68,0.06); border:1px solid rgba(255,68,68,0.2);
                border-radius:10px; padding:12px 16px; margin-top:12px;">
                <span style="color:#ff8888; font-size:0.82rem;">
                    ⚠️ AI-generated analysis. Always verify before use. 
                    For educational purposes only. FinsageAI is not a SEBI-registered advisor.
                    No real trading recommendations implied.
                </span>
            </div>
            """, unsafe_allow_html=True)
