"""FinsageAI — Terms & Privacy Policy"""
import streamlit as st

def render_terms_page():
    st.markdown("""
    <div style="margin-bottom:24px;">
        <span style="font-size:1.6rem; font-weight:800; background:linear-gradient(90deg,#00d4ff,#7c3aed);
            -webkit-background-clip:text; -webkit-text-fill-color:transparent;">📜 Terms of Service & Privacy Policy</span>
    </div>""", unsafe_allow_html=True)

    st.error("⚠️ **Risk Disclaimer:** This platform is for educational purposes only. Not SEBI registered investment advice. Trading in equities, derivatives, and cryptocurrencies involves substantial financial risk.")

    st.markdown("""
    <div style="background:rgba(2,6,9,0.6);border:1px solid rgba(0,212,255,0.2);border-radius:12px;padding:20px 24px;margin-bottom:16px;">
    <h4 style="color:#00d4ff;">📋 Terms of Service</h4>
    <p style="color:#c8d6e8;font-size:0.9rem;line-height:1.8;">
    By accessing this application, you acknowledge that all technical indicators, backtesting results,
    AI analysis, and pattern detection outputs represent historical evaluations and educational analysis.
    No trade execution capability is offered. Past performance does not guarantee future results.
    You are solely responsible for any trading decisions you make.
    </p></div>""", unsafe_allow_html=True)

    st.markdown("""
    <div style="background:rgba(2,6,9,0.6);border:1px solid rgba(0,212,255,0.2);border-radius:12px;padding:20px 24px;margin-bottom:16px;">
    <h4 style="color:#00d4ff;">🔐 Privacy & Data Usage Policy</h4>
    <p style="color:#c8d6e8;font-size:0.9rem;line-height:1.8;">
    This platform respects user privacy. External API keys (Groq, Gemini, etc.) are stored securely
    and never shared with third parties. No financial transaction logs or personal trading data
    are stored on our servers. Market data is fetched in real-time from public APIs (yfinance, etc.).
    </p></div>""", unsafe_allow_html=True)

    st.markdown("""
    <div style="background:rgba(2,6,9,0.6);border:1px solid rgba(0,212,255,0.2);border-radius:12px;padding:20px 24px;margin-bottom:16px;">
    <h4 style="color:#00d4ff;">⚠️ Risk Disclosure</h4>
    <p style="color:#c8d6e8;font-size:0.9rem;line-height:1.8;">
    Trading in financial markets carries significant risk. You can lose more than your initial investment.
    Options, futures, and crypto trading involve leverage that can amplify both gains and losses.
    Never invest money you cannot afford to lose. Always consult a SEBI-registered financial advisor
    before making investment decisions.
    </p></div>""", unsafe_allow_html=True)

    st.markdown("""
    <div style="background:rgba(2,6,9,0.6);border:1px solid rgba(0,212,255,0.2);border-radius:12px;padding:20px 24px;margin-bottom:16px;">
    <h4 style="color:#00d4ff;">📊 Data Sources</h4>
    <p style="color:#c8d6e8;font-size:0.9rem;line-height:1.8;">
    Market data: Yahoo Finance (yfinance) · AI Analysis: Groq (Llama 3.3 70B) & Google Gemini ·
    Technical Indicators: Computed in-house using pandas/numpy · No data is sold or distributed.
    </p></div>""", unsafe_allow_html=True)

    st.markdown("""
    <div style="background:rgba(2,6,9,0.6);border:1px solid rgba(0,212,255,0.2);border-radius:12px;padding:20px 24px;margin-bottom:16px;">
    <h4 style="color:#00d4ff;">📧 Contact</h4>
    <p style="color:#c8d6e8;font-size:0.9rem;line-height:1.8;">
    For questions, concerns, or feedback regarding this platform, please reach out via the
    GitHub repository: <a href="https://github.com/basantpradhan454-a11y/ai-trading-agent" style="color:#00d4ff;">ai-trading-agent</a>
    </p></div>""", unsafe_allow_html=True)

    st.caption("Last Updated: July 2026 | Version 6.0 | FinsageAI Trading Intelligence Engine")
