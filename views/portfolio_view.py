"""FinsageAI — Virtual Paper Trading Portfolio UI"""
import streamlit as st
import yfinance as yf
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.virtual_portfolio import (
    init_portfolio, add_position, close_position,
    get_pnl_summary, get_total_value, get_allocation_chart,
    get_transaction_history, INITIAL_CAPITAL
)


def fetch_live_price(ticker):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="1d")
        return float(hist["Close"].iloc[-1]) if not hist.empty else 0.0
    except Exception:
        return 0.0


def render_portfolio_page():
    init_portfolio()
    st.markdown("""
    <div style="margin-bottom:20px;">
        <span style="font-size:1.6rem; font-weight:800; background:linear-gradient(90deg,#00d4ff,#7c3aed);
            -webkit-background-clip:text; -webkit-text-fill-color:transparent;">💼 Paper Trading Portfolio</span>
    </div>
    <div style="background:rgba(255,170,0,0.08); border:1px solid rgba(255,170,0,0.25);
        border-radius:12px; padding:12px 16px; margin-bottom:20px;">
        <span style="color:#ffaa00; font-size:0.85rem; font-weight:600;">
            🎭 PAPER TRADING ONLY — No real money involved. ₹10,00,000 virtual capital.
        </span>
    </div>
    """, unsafe_allow_html=True)

    p = st.session_state["finsage_portfolio"]
    prices = {}
    for ticker in p["positions"]:
        prices[ticker] = fetch_live_price(ticker)

    total_val = get_total_value(prices)
    total_pnl = total_val - INITIAL_CAPITAL
    pnl_pct = (total_pnl / INITIAL_CAPITAL) * 100

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Starting Capital", f"₹{INITIAL_CAPITAL:,.0f}")
    c2.metric("Current Value", f"₹{total_val:,.0f}", delta=f"₹{total_pnl:+,.0f}")
    c3.metric("Cash Available", f"₹{p['cash']:,.0f}")
    c4.metric("Total P&L", f"{pnl_pct:+.2f}%", delta_color="normal" if pnl_pct >= 0 else "inverse")

    tab1, tab2, tab3 = st.tabs(["➕ Add / Close Position", "📊 My Holdings", "📋 Transaction History"])

    with tab1:
        st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            ticker_in = st.text_input("Ticker Symbol", "RELIANCE.NS", key="port_ticker").upper().strip()
            action = st.radio("Action", ["BUY", "SELL"], horizontal=True, key="port_action")
            qty = st.number_input("Quantity (Units)", min_value=1, max_value=100000, value=10, key="port_qty")
        with col2:
            if st.button("📡 Fetch Live Price", key="fetch_price_btn"):
                if ticker_in:
                    live = fetch_live_price(ticker_in)
                    if live > 0:
                        st.session_state["fetched_price"] = live
                        st.success(f"✅ {ticker_in}: ₹{live:,.2f}")
                    else:
                        st.error("Could not fetch. Enter price manually.")
            price = st.number_input("Price per Unit (₹)", min_value=0.01,
                                     value=float(st.session_state.get("fetched_price", 100.0)),
                                     format="%.2f", key="port_price")
            trade_value = qty * price
            st.markdown(f"""
            <div style="background:rgba(0,212,255,0.06); border:1px solid rgba(0,212,255,0.15);
                border-radius:10px; padding:14px; text-align:center; margin-top:8px;">
                <div style="font-size:0.72rem; color:#5a7a9a; text-transform:uppercase; letter-spacing:.08em;">Trade Value</div>
                <div style="font-family:'JetBrains Mono',monospace; font-size:1.4rem; color:#00d4ff; font-weight:600;">
                    ₹{trade_value:,.2f}
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)
        btn_label = f"{'🟢 BUY' if action == 'BUY' else '🔴 SELL'} {ticker_in}"
        if st.button(btn_label, type="primary", use_container_width=True, key="execute_trade"):
            if action == "BUY":
                ok, msg = add_position(ticker_in, float(qty), float(price))
            else:
                ok, msg = close_position(ticker_in, float(qty), float(price))
            if ok:
                st.success(f"✅ {msg}")
                st.rerun()
            else:
                st.error(f"❌ {msg}")

    with tab2:
        if not p["positions"]:
            st.info("📭 No open positions. Use the 'Add Position' tab to start trading!")
        else:
            pnl_df = get_pnl_summary(prices)
            def color_pnl(val):
                if isinstance(val, (int, float)):
                    return "color:#00ff88" if val > 0 else ("color:#ff4444" if val < 0 else "")
                return ""
            try:
                styled_pnl = pnl_df.style.map(color_pnl, subset=["P&L (₹)", "P&L (%)"])
            except AttributeError:
                styled_pnl = pnl_df.style.applymap(color_pnl, subset=["P&L (₹)", "P&L (%)"])
            st.dataframe(styled_pnl, use_container_width=True, hide_index=True)

            c_a, c_b = st.columns(2)
            with c_a:
                if st.button("🔄 Refresh Live Prices", use_container_width=True):
                    for t in list(p["positions"].keys()):
                        prices[t] = fetch_live_price(t)
                    st.rerun()
            with c_b:
                if st.button("🗑️ Reset Portfolio", type="secondary", use_container_width=True):
                    del st.session_state["finsage_portfolio"]
                    st.rerun()

            st.plotly_chart(get_allocation_chart(prices), use_container_width=True)

    with tab3:
        hist_df = get_transaction_history()
        if hist_df.empty:
            st.info("📋 No transactions yet.")
        else:
            st.dataframe(hist_df, use_container_width=True, hide_index=True)
            csv = hist_df.to_csv(index=False)
            st.download_button("📥 Download History CSV", csv, "portfolio_history.csv", "text/csv")
