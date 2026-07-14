"""FinsageAI — Backtesting UI View"""
import streamlit as st
import yfinance as yf
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.backtest_engine import BacktestEngine


def render_backtesting_page():
    st.markdown("""
    <div style="margin-bottom:24px;">
        <span style="font-size:1.6rem; font-weight:800; background:linear-gradient(90deg,#00d4ff,#7c3aed);
            -webkit-background-clip:text; -webkit-text-fill-color:transparent;">🔬 Strategy Backtesting Engine</span>
        <p style="color:#5a7a9a; margin-top:4px; font-size:0.9rem;">
            Test RSI, MACD, EMA crossover strategies on real historical data (yfinance)
        </p>
    </div>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown('<div style="font-size:0.68rem; letter-spacing:.1em; color:#304a66; text-transform:uppercase; margin-bottom:8px;">Bot Builder</div>', unsafe_allow_html=True)
        ticker = st.text_input("Ticker Symbol", "RELIANCE.NS", help="E.g. RELIANCE.NS, INFY.NS, AAPL, BTC-USD")
        period = st.selectbox("Backtest Period", ["6mo", "1y", "2y", "3y", "5y"], index=1)
        strategy = st.selectbox("Strategy", [
            "RSI_Oversold", "MACD_Crossover", "EMA_Crossover",
            "Bollinger_Bounce", "Combined_RSI_MACD"
        ])
        initial_cap = st.number_input("Starting Capital (₹)", value=1_000_000, step=100_000, format="%d")
        st.markdown('<div style="font-size:0.68rem; letter-spacing:.1em; color:#304a66; text-transform:uppercase; margin:12px 0 8px;">Parameters</div>', unsafe_allow_html=True)
        params = {}
        if "RSI" in strategy:
            params["rsi_period"] = st.slider("RSI Period", 7, 21, 14)
            params["oversold"] = st.slider("Oversold Level", 15, 40, 30)
            params["overbought"] = st.slider("Overbought Level", 60, 90, 70)
        if "EMA" in strategy:
            params["ema_fast"] = st.slider("Fast EMA", 5, 20, 9)
            params["ema_slow"] = st.slider("Slow EMA", 15, 50, 21)
        if "MACD" in strategy and "Combined" not in strategy:
            params["macd_fast"] = st.slider("MACD Fast", 8, 16, 12)
            params["macd_slow"] = st.slider("MACD Slow", 20, 32, 26)
            params["macd_signal"] = st.slider("Signal Line", 7, 12, 9)
        if "Bollinger" in strategy:
            params["bb_period"] = st.slider("BB Period", 10, 30, 20)
            params["bb_std"] = st.slider("BB Std Dev", 1.0, 3.0, 2.0, 0.5)
        run = st.button("🚀 Run Backtest", type="primary", use_container_width=True)

    if run:
        with st.spinner(f"📡 Fetching {ticker} data and running {strategy}..."):
            try:
                df = yf.download(ticker, period=period, auto_adjust=True, progress=False)
                if df.empty:
                    st.error(f"❌ No data for '{ticker}'. Check the symbol.")
                    return
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                engine = BacktestEngine(df, initial_capital=float(initial_cap))
                signals = engine.compile_signals(strategy, params)
                trade_df, metrics, full_df = engine.run(signals)
            except Exception as e:
                st.error(f"Error: {e}")
                return

        st.markdown("""<div style="background:#0f1e35; border:1px solid rgba(0,212,255,0.15);
            border-radius:14px; padding:20px 24px; margin-bottom:16px;">""", unsafe_allow_html=True)
        st.markdown('<div style="font-size:0.68rem; letter-spacing:.1em; color:#00d4ff; text-transform:uppercase; margin-bottom:12px;">Performance Summary</div>', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        delta_color = "normal" if metrics["Total Return (%)"] >= 0 else "inverse"
        c1.metric("Total Return", f"{metrics['Total Return (%)']}%", delta=f"Alpha: {metrics['Alpha (%)']}%", delta_color=delta_color)
        c2.metric("Max Drawdown", f"{metrics['Max Drawdown (%)']}%")
        c3.metric("Sharpe Ratio", metrics["Sharpe Ratio"])
        c4.metric("Win Rate", f"{metrics['Win Rate (%)']}%", delta=f"{metrics['Total Trades']} trades")
        c5, c6 = st.columns(2)
        c5.metric("Final Capital", f"₹{metrics['Final Capital (Rs)']:,.0f}")
        c6.metric("Benchmark (Buy & Hold)", f"{metrics['Benchmark Return (%)']}%")
        st.markdown("</div>", unsafe_allow_html=True)

        st.plotly_chart(engine.build_equity_chart(full_df, trade_df), use_container_width=True)

        if not trade_df.empty:
            st.markdown('<div style="font-size:0.68rem; letter-spacing:.1em; color:#00d4ff; text-transform:uppercase; margin:16px 0 8px;">Trade Log</div>', unsafe_allow_html=True)
            def color_action(val):
                return "color: #00ff88; font-weight:bold" if val == "BUY" else "color: #ff4444; font-weight:bold"
            try:
                styled = trade_df.style.map(color_action, subset=["Action"])
            except AttributeError:
                styled = trade_df.style.applymap(color_action, subset=["Action"])
            st.dataframe(styled, use_container_width=True)
            csv = trade_df.to_csv(index=False)
            st.download_button("📥 Download Trade Log CSV", csv, f"{ticker}_trades.csv", "text/csv")
        else:
            st.warning("⚠️ No trades triggered. Try adjusting parameters or a longer period.")

        st.info("⚖️ FinsageAI Educational Simulator. Past performance does not predict future results. Not SEBI investment advice.")
