import datetime
import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.db import init_db, get_session, ApiKeyRecord, Trade, BacktestRun, AccountLog
from core.security import encrypt_value, decrypt_value, mask
from core.data_feed import fetch_ohlcv, fetch_ticker
from core.indicators import add_indicators
from core.strategy import generate_signal
from core.risk_validator import validate_trade, RiskLimits, AccountState, format_reasoning_log
from core.backtest_engine import run_bulk_backtest
from core.news_quant import fetch_news, quant_metrics
from core.demo_engine import run_cycle, get_or_create_account

st.set_page_config(page_title="AI Trading Agent", page_icon="📈", layout="wide")
init_db()

SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "DOGE/USDT"]
STRATEGIES = ["Aggressive", "Balanced", "Conservative"]

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.title("📈 AI Trading Agent")
st.sidebar.caption("Demo-first fintech assistant — not financial advice, execution tool only.")

symbol = st.sidebar.selectbox("Favourite symbol", SYMBOLS, index=0)
strategy = st.sidebar.selectbox("Strategy profile", STRATEGIES, index=1)
timeframe = st.sidebar.selectbox("Timeframe", ["15m", "1h", "4h", "1d"], index=1)

session = get_session()
account = get_or_create_account(session)
st.sidebar.divider()
st.sidebar.metric("Demo balance", f"${account.balance:,.2f}")
st.sidebar.metric("Today's P&L", f"{account.daily_pnl_pct:+.2f}%")
if account.is_shutdown:
    st.sidebar.error(f"🚨 GLOBAL SHUTDOWN until {account.shutdown_until}")
session.close()

tab_dashboard, tab_backtest, tab_news, tab_settings = st.tabs(
    ["🖥️ Dashboard", "🧪 200-Strategy Backtest", "📰 News & Quant", "🔐 API & Risk Settings"]
)

# ---------------------------------------------------------------------------
# TAB 1 — Dashboard (live demo trading)
# ---------------------------------------------------------------------------
with tab_dashboard:
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader(f"{symbol} — live chart ({timeframe})")
        try:
            df = fetch_ohlcv(symbol, timeframe=timeframe)
            df = add_indicators(df)
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=df["timestamp"], open=df["open"], high=df["high"],
                low=df["low"], close=df["close"], name=symbol,
            ))
            fig.add_trace(go.Scatter(x=df["timestamp"], y=df["ema_fast"], name="EMA fast", line=dict(width=1)))
            fig.add_trace(go.Scatter(x=df["timestamp"], y=df["ema_slow"], name="EMA slow", line=dict(width=1)))
            fig.update_layout(height=420, xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)

            latest = df.dropna(subset=["rsi"]).iloc[-1]
            m1, m2, m3 = st.columns(3)
            m1.metric("Price", f"${latest['close']:,.2f}")
            m2.metric("RSI(14)", f"{latest['rsi']:.1f}")
            m3.metric("Volume spike", "Yes" if latest["vol_spike"] else "No")
        except Exception as e:
            st.error(f"Couldn't load market data: {e}")

    with col2:
        st.subheader("AI cycle")
        st.caption("Runs one signal-generation + risk-validation pass. Schedule this via the GitHub Actions worker for real 24/7 operation.")
        if st.button("▶ Run trading cycle now", use_container_width=True):
            result = run_cycle(symbol=symbol, strategy=strategy, timeframe=timeframe)
            st.code(result["log"] or "No action this cycle.", language="text")
            st.rerun()

    st.divider()
    st.subheader("Trade log (demo)")
    session = get_session()
    trades = session.query(Trade).filter(Trade.symbol == symbol).order_by(Trade.opened_at.desc()).limit(25).all()
    session.close()
    if trades:
        rows = [{
            "Opened": t.opened_at, "Action": t.action.upper(), "Entry": t.entry_price,
            "SL": t.stop_loss, "TP": t.take_profit, "Size %": t.position_size_pct,
            "Status": t.status, "Exit": t.exit_price, "PnL %": t.pnl_pct, "Strategy": t.strategy,
        } for t in trades]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No trades yet — click 'Run trading cycle now' to generate the first signal.")

# ---------------------------------------------------------------------------
# TAB 2 — Backtest (200 strategies at once)
# ---------------------------------------------------------------------------
with tab_backtest:
    st.subheader("Backtest up to 200 strategy variants in one run")
    bt_symbol = st.selectbox("Symbol", SYMBOLS, key="bt_symbol")
    bt_timeframe = st.selectbox("Timeframe", ["15m", "1h", "4h", "1d"], index=1, key="bt_tf")
    n_strategies = st.slider("Number of strategies to test", 20, 200, 200, step=20)

    if st.button("🧪 Run backtest report", type="primary"):
        with st.spinner(f"Backtesting {n_strategies} strategy variants on {bt_symbol}..."):
            df_raw = fetch_ohlcv(bt_symbol, timeframe=bt_timeframe, limit=500)
            report = run_bulk_backtest(df_raw, n_strategies=n_strategies)

            session = get_session()
            session.add(BacktestRun(
                symbol=bt_symbol, timeframe=bt_timeframe, strategies_tested=len(report),
                report_json=report.head(50).to_json(orient="records"),
            ))
            session.commit()
            session.close()

        st.success(f"Tested {len(report)} strategies on {bt_symbol} ({bt_timeframe}).")
        best = report.iloc[0]
        b1, b2, b3, b4 = st.columns(4)
        b1.metric("Best return", f"{best['total_return_pct']:+.2f}%")
        b2.metric("Win rate", f"{best['win_rate_pct']:.1f}%")
        b3.metric("Trades", int(best["num_trades"]))
        b4.metric("Final balance", f"${best['final_balance']:,.0f}")

        st.dataframe(report.head(50), use_container_width=True, hide_index=True)
        st.download_button(
            "⬇ Download full report (CSV)",
            report.to_csv(index=False).encode(),
            file_name=f"backtest_{bt_symbol.replace('/', '_')}.csv",
        )

# ---------------------------------------------------------------------------
# TAB 3 — News & Quant
# ---------------------------------------------------------------------------
with tab_news:
    st.subheader(f"Social/news sentiment — {symbol}")
    try:
        news_items = fetch_news(symbol)
        if news_items:
            for item in news_items:
                icon = {"Positive": "🟢", "Negative": "🔴", "Neutral": "⚪"}[item["sentiment"]]
                st.markdown(f"{icon} [{item['title']}]({item['link']})")
        else:
            st.info("No recent headlines found.")
    except Exception as e:
        st.warning(f"News feed unavailable right now: {e}")

    st.divider()
    st.subheader("Quant risk metrics")
    try:
        df_q = fetch_ohlcv(symbol, timeframe="1d", limit=90)
        metrics = quant_metrics(df_q)
        q1, q2, q3 = st.columns(3)
        q1.metric("Annualized volatility", f"{metrics['annualized_volatility_pct']}%")
        q2.metric("Sharpe estimate", metrics["sharpe_estimate"])
        q3.metric("Max drawdown (90d)", f"{metrics['max_drawdown_pct']}%")
    except Exception as e:
        st.warning(f"Quant metrics unavailable: {e}")

# ---------------------------------------------------------------------------
# TAB 4 — API keys (encrypted) & risk settings
# ---------------------------------------------------------------------------
with tab_settings:
    st.subheader("Exchange API key (encrypted at rest)")
    st.caption(
        "Your key/secret are encrypted with Fernet before being written to the database — "
        "never stored in plain text. Live execution stays OFF by default; this app runs in "
        "**demo/paper mode** unless you explicitly enable live trading below."
    )

    session = get_session()
    existing = session.query(ApiKeyRecord).filter_by(username="default_user").first()

    with st.form("api_key_form"):
        exchange_name = st.selectbox("Exchange", ["kraken", "coinbase", "okx", "kucoin", "bitstamp", "binance"])
        api_key_input = st.text_input("API Key", type="password",
                                       placeholder="already saved" if existing else "")
        api_secret_input = st.text_input("API Secret", type="password",
                                          placeholder="already saved" if existing else "")
        live_enabled = st.checkbox(
            "⚠️ I understand the risks — enable LIVE trading with real funds",
            value=bool(existing.live_trading_enabled) if existing else False,
        )
        submitted = st.form_submit_button("Save (encrypted)")
        if submitted:
            enc_key = encrypt_value(api_key_input) if api_key_input else (existing.api_key_enc if existing else "")
            enc_secret = encrypt_value(api_secret_input) if api_secret_input else (existing.api_secret_enc if existing else "")
            if existing:
                existing.exchange = exchange_name
                existing.api_key_enc = enc_key
                existing.api_secret_enc = enc_secret
                existing.live_trading_enabled = live_enabled
            else:
                session.add(ApiKeyRecord(
                    username="default_user", exchange=exchange_name,
                    api_key_enc=enc_key, api_secret_enc=enc_secret,
                    live_trading_enabled=live_enabled,
                ))
            session.commit()
            st.success("Saved — key/secret stored encrypted, not in plain text.")

    if existing and existing.api_key_enc:
        try:
            shown = mask(decrypt_value(existing.api_key_enc))
        except Exception:
            shown = "(set ENCRYPTION_KEY to view)"
        st.text(f"Current key on file: {shown} | Live trading: {'ON' if existing.live_trading_enabled else 'OFF'}")
    session.close()

    st.divider()
    st.subheader("Hard-coded risk limits (non-negotiable — AI cannot override these)")
    limits = RiskLimits()
    st.json({
        "max_position_pct": limits.max_position_pct,
        "max_sl_pct": limits.max_sl_pct,
        "min_tp_pct": limits.min_tp_pct,
        "min_risk_reward": limits.min_risk_reward,
        "max_daily_loss_pct": limits.max_daily_loss_pct,
    })
    st.caption("Every AI-generated order is re-validated against these limits in core/risk_validator.py before anything reaches the exchange — the AI's output is never sent to CCXT directly.")
