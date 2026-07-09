import ccxt
import pandas as pd
import streamlit as st


@st.cache_resource
def get_exchange(exchange_id: str = "kraken"):
    ex_class = getattr(ccxt, exchange_id)
    return ex_class({"enableRateLimit": True})


@st.cache_data(ttl=30)
def fetch_ohlcv(symbol: str = "BTC/USDT", timeframe: str = "1h", limit: int = 300,
                 exchange_id: str = "kraken") -> pd.DataFrame:
    ex = get_exchange(exchange_id)
    raw = ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df


@st.cache_data(ttl=15)
def fetch_ticker(symbol: str = "BTC/USDT", exchange_id: str = "kraken") -> dict:
    ex = get_exchange(exchange_id)
    return ex.fetch_ticker(symbol)
