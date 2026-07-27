import streamlit as st
from utils import crypto_data, ai_analysis, telegram_alert, fundamentals

st.set_page_config(page_title="Crypto Analysis Agent", layout="wide", page_icon="🪙")

if "last_analysis" not in st.session_state:
    st.session_state.last_analysis = ""
if "signal" not in st.session_state:
    st.session_state.signal = "HOLD"
if "confidence" not in st.session_state:
    st.session_state.confidence = 0
if "mode" not in st.session_state:
    st.session_state.mode = "signal"

st.title("🪙 Crypto Analysis Agent")

COINS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "DOGE/USDT", "ADA/USDT", "MATIC/USDT"]

col_left, col_mid, col_right = st.columns([1, 2.2, 1.3])

with col_left:
    st.subheader("Watchlist")
    selected_coin = st.radio("Select coin", COINS, label_visibility="collapsed")
    st.divider()
    st.caption("Live price feed source")
    exchange = st.selectbox("Exchange (data source)", ["Binance", "CoinGecko", "CoinMarketCap", "KuCoin"])

with col_mid:
    st.subheader(f"{selected_coin} chart")

    df = crypto_data.get_price_data(selected_coin, exchange)
    fig = crypto_data.plot_candles(df, selected_coin)
    st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        run_clicked = st.button("🤖 Run AI technical analysis", use_container_width=True)
    with c2:
        speak_clicked = st.button("🔊 Explain what happened", use_container_width=True)

    if run_clicked:
        result = ai_analysis.analyse(selected_coin, df)
        st.session_state.last_analysis = result["summary"]
        st.session_state.signal = result["signal"]
        st.session_state.confidence = result["confidence"]

        if st.session_state.mode == "signal":
            telegram_alert.send_signal(
                selected_coin, result["signal"], result["confidence"], result["summary"]
            )

    st.markdown("### AI technical summary")
    st.info(st.session_state.last_analysis or "Click 'Run AI technical analysis' to generate a summary.")

    if speak_clicked:
        if st.session_state.last_analysis:
            crypto_data.speak_text(st.session_state.last_analysis)
        else:
            st.warning("Pehle AI technical analysis run karein.")

    st.markdown("### Signal & execution")
    badge_color = "green" if st.session_state.signal == "BUY" else ("red" if st.session_state.signal == "SELL" else "gray")
    st.markdown(
        f"**Signal:** :{badge_color}[{st.session_state.signal}]  &nbsp;&nbsp; "
        f"**Confidence:** {st.session_state.confidence}%"
    )

    st.session_state.mode = st.radio(
        "Trade mode",
        options=["execute", "signal"],
        format_func=lambda x: "Execute via exchange API" if x == "execute" else "Signal only (Telegram)",
        horizontal=True,
    )

    qty = st.number_input("Quantity", min_value=0.0, value=0.01, step=0.01, format="%.4f")
    b1, b2 = st.columns(2)
    with b1:
        if st.button("BUY", use_container_width=True, type="primary"):
            crypto_data.place_or_signal(selected_coin, "BUY", qty, st.session_state.mode)
    with b2:
        if st.button("SELL", use_container_width=True):
            crypto_data.place_or_signal(selected_coin, "SELL", qty, st.session_state.mode)

with col_right:
    st.subheader("Fundamental & on-chain / macro summary")
    if st.button("🔄 Refresh AI news summary", use_container_width=True):
        st.session_state.news = fundamentals.get_summary(selected_coin)

    news = st.session_state.get("news", fundamentals.get_summary(selected_coin))
    for item in news:
        st.markdown(f"**{item['tag']}** — {item['text']}")

    st.divider()
    st.subheader("Exchange & API keys")
    st.caption("Keys sirf is session ke liye memory mein rehte hain. Production mein Streamlit secrets use karein.")

    exch = st.selectbox("Exchange for trading", ["Binance", "CoinDCX", "WazirX", "Bybit", "Coinbase"])
    api_key = st.text_input("Exchange API key", type="password")
    api_secret = st.text_input("Exchange API secret", type="password")
    tg_token = st.text_input("Telegram bot token", type="password")
    tg_chat = st.text_input("Telegram chat ID")
    gemini_key = st.text_input("Gemini / news API key", type="password")

    if st.button("💾 Save keys", use_container_width=True):
        st.session_state["keys"] = {
            "exchange": exch,
            "api_key": api_key,
            "api_secret": api_secret,
            "tg_token": tg_token,
            "tg_chat": tg_chat,
            "gemini_key": gemini_key,
        }
        st.success("Keys saved for this session.")
