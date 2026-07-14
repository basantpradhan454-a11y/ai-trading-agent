"""FinsageAI — AI Trading Chat Assistant UI"""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.ai_assistant import get_response

QUICK_TOPICS = ["RSI", "MACD", "Candlestick Patterns", "Risk Management",
                "Portfolio Building", "Options Basics", "Crypto Guide", "IPO Analysis",
                "Fibonacci", "Bollinger Bands", "Trading Psychology", "Volume Analysis"]

GUARDRAIL_KEYWORDS = [
    "should i buy", "should i sell", "will it go up", "will it go down",
    "buy now", "sell now", "kya kharidun", "kya bechan", "abhi kharidna chahiye",
    "kharidna chahiye", "bechna chahiye"
]

WELCOME_MSG = """👋 **Welcome to FinsageAI Trading Assistant!**

I'm your personal AI trading education guide. Ask me anything about:

📊 **Technical Analysis** — RSI, MACD, Bollinger Bands, Moving Averages
🕯️ **Candlestick Patterns** — Hammer, Doji, Engulfing, Morning Star
🛡️ **Risk Management** — Position sizing, Stop losses, R:R ratio
₿ **Crypto** — Bitcoin, DeFi, Altcoins, Meme coins
📁 **Portfolio Building** — Diversification, Asset allocation
⚙️ **Options** — Basics, Greeks, Strategies
📈 **IPO Analysis** — How to evaluate new listings

**Try asking:** *"Explain RSI"* • *"What is MACD?"* • *"How to manage risk?"*

> ⚖️ Educational guide only. Not SEBI investment advice."""

GUARDRAIL_RESPONSE = """⚠️ **I can't give specific buy/sell recommendations** — that would be financial advice.

But I can help you **learn how to analyze** for yourself:

📊 **Technical signals** — RSI, MACD, Support/Resistance levels
📋 **Fundamentals** — P/E ratio, Revenue growth, Debt levels
🛡️ **Risk management** — Stop loss placement, Position sizing
🕯️ **Chart patterns** — What the pattern suggests historically

**Ask me:** *"How do I evaluate a stock?"* or *"What is RSI?"* for a full education guide.

> ⚖️ FinsageAI is an educational tool only. Not a SEBI-registered financial advisor."""


def render_chat_page():
    st.markdown("""
    <div style="margin-bottom:16px;">
        <span style="font-size:1.6rem; font-weight:800; background:linear-gradient(90deg,#00d4ff,#7c3aed);
            -webkit-background-clip:text; -webkit-text-fill-color:transparent;">🤖 AI Trading Assistant</span>
        <p style="color:#5a7a9a; margin-top:4px; font-size:0.9rem;">
            Ask anything about trading, markets, and technical analysis.
        </p>
    </div>
    """, unsafe_allow_html=True)

    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []
        st.session_state["chat_history"].append({
            "role": "assistant", "content": WELCOME_MSG, "source": "local"
        })

    with st.sidebar:
        st.markdown('<div style="font-size:0.68rem; letter-spacing:.1em; color:#304a66; text-transform:uppercase; margin-bottom:10px;">Quick Topics</div>', unsafe_allow_html=True)
        for topic in QUICK_TOPICS:
            if st.button(topic, use_container_width=True, key=f"qt_{topic}"):
                st.session_state["quick_query"] = f"Explain {topic}"
        st.markdown("<hr>", unsafe_allow_html=True)
        if st.button("🗑️ Clear Chat", use_container_width=True, key="clear_chat"):
            st.session_state["chat_history"] = []
            st.session_state["chat_history"].append({
                "role": "assistant", "content": WELCOME_MSG, "source": "local"
            })
            st.rerun()
        st.markdown("""
        <div style="font-size:0.72rem; color:#304a66; margin-top:12px; line-height:1.5;">
            ⚖️ FinsageAI is for educational purposes only.<br>Not SEBI registered investment advice.
        </div>
        """, unsafe_allow_html=True)

    for msg in st.session_state["chat_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("source") == "gemini":
                st.caption("🤖 Powered by Gemini AI")
            elif msg.get("source") == "local":
                st.caption("📚 FinsageAI Knowledge Base")

    prompt = st.session_state.pop("quick_query", None) or st.chat_input("Ask anything about trading...")

    if prompt:
        lower_p = prompt.lower()
        if any(kw in lower_p for kw in GUARDRAIL_KEYWORDS):
            response = GUARDRAIL_RESPONSE
            source = "local"
        else:
            response, source = get_response(prompt, st.session_state["chat_history"])

        st.session_state["chat_history"].append({"role": "user", "content": prompt, "source": None})
        st.session_state["chat_history"].append({"role": "assistant", "content": response, "source": source})
        st.rerun()
