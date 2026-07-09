"""
Turns indicators into an AI-style JSON signal, e.g.:
{"action": "buy", "symbol": "BTC/USDT", "stop_loss": 63700, "reason": "..."}
This is intentionally simple/transparent (RSI + EMA cross + volume spike) —
the point is every output still has to pass core/risk_validator.py before
anything is ever sent to an exchange.
"""

PROFILES = {
    "Aggressive":   {"rsi_buy": 45, "rsi_sell": 65, "size": 5.0, "sl_pct": 2.0, "tp_pct": 6.0},
    "Balanced":     {"rsi_buy": 35, "rsi_sell": 70, "size": 3.0, "sl_pct": 2.0, "tp_pct": 5.0},
    "Conservative": {"rsi_buy": 25, "rsi_sell": 75, "size": 1.5, "sl_pct": 1.5, "tp_pct": 5.0},
}


def generate_signal(df, strategy: str = "Balanced") -> dict:
    p = PROFILES.get(strategy, PROFILES["Balanced"])
    latest = df.dropna(subset=["rsi", "ema_fast", "ema_slow"]).iloc[-1]

    entry = float(latest["close"])
    rsi = float(latest["rsi"])
    ema_fast, ema_slow = float(latest["ema_fast"]), float(latest["ema_slow"])
    vol_spike = bool(latest["vol_spike"])

    action, reason = "hold", "No clear signal — RSI/EMA not aligned"
    if rsi < p["rsi_buy"] and ema_fast > ema_slow:
        action = "buy"
        reason = f"RSI {rsi:.1f} oversold + EMA bullish cross"
        if vol_spike:
            reason += " + volume spike confirmation"
    elif rsi > p["rsi_sell"] and ema_fast < ema_slow:
        action = "sell"
        reason = f"RSI {rsi:.1f} overbought + EMA bearish cross"
        if vol_spike:
            reason += " + volume spike confirmation"

    if action == "buy":
        sl = entry * (1 - p["sl_pct"] / 100)
        tp = entry * (1 + p["tp_pct"] / 100)
    elif action == "sell":
        sl = entry * (1 + p["sl_pct"] / 100)
        tp = entry * (1 - p["tp_pct"] / 100)
    else:
        sl = tp = entry

    return {
        "action": action,
        "entry_price": round(entry, 4),
        "stop_loss": round(sl, 4),
        "take_profit": round(tp, 4),
        "position_size_pct": p["size"],
        "reason": reason,
        "rsi": round(rsi, 1),
        "ema_fast": round(ema_fast, 2),
        "ema_slow": round(ema_slow, 2),
        "vol_spike": vol_spike,
    }
