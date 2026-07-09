import pandas as pd
import ta


def add_indicators(df: pd.DataFrame, ema_fast=12, ema_slow=26, rsi_period=14) -> pd.DataFrame:
    df = df.copy()
    df["ema_fast"] = ta.trend.ema_indicator(df["close"], window=ema_fast)
    df["ema_slow"] = ta.trend.ema_indicator(df["close"], window=ema_slow)
    df["rsi"] = ta.momentum.rsi(df["close"], window=rsi_period)
    df["vol_avg"] = df["volume"].rolling(20).mean()
    df["vol_spike"] = df["volume"] > (df["vol_avg"] * 1.5)
    return df
