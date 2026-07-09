"""
Backtests N strategy parameter combinations (default 200) over historical
OHLCV in one shot and returns a ranked report — the "200 strategy backtest"
feature.
"""
import random
import pandas as pd
from core.indicators import add_indicators

PARAM_SPACE = {
    "rsi_buy": [20, 25, 30, 35, 40, 45],
    "rsi_sell": [55, 60, 65, 70, 75, 80],
    "ema_fast": [5, 8, 10, 12, 16, 20],
    "ema_slow": [21, 26, 30, 34, 40, 50],
    "sl_pct": [1.0, 1.5, 2.0],
    "tp_pct": [3.0, 4.0, 5.0, 6.0, 8.0],
    "size_pct": [1.5, 3.0, 5.0],
}


def _run_single_backtest(df_ind: pd.DataFrame, params: dict, initial_balance: float = 10000.0) -> dict:
    balance = initial_balance
    position = None
    trade_pnls = []

    for i in range(1, len(df_ind)):
        row = df_ind.iloc[i]
        price, rsi, ema_fast, ema_slow = row["close"], row["rsi"], row["ema_fast"], row["ema_slow"]
        if pd.isna(rsi) or pd.isna(ema_fast) or pd.isna(ema_slow):
            continue

        if position is None:
            if rsi < params["rsi_buy"] and ema_fast > ema_slow:
                entry = price
                position = {
                    "entry": entry,
                    "sl": entry * (1 - params["sl_pct"] / 100),
                    "tp": entry * (1 + params["tp_pct"] / 100),
                    "size": balance * (params["size_pct"] / 100),
                }
        else:
            low = row.get("low", price)
            high = row.get("high", price)
            if low <= position["sl"]:
                pnl = -position["size"] * (params["sl_pct"] / 100)
                balance += pnl
                trade_pnls.append(pnl)
                position = None
            elif high >= position["tp"]:
                pnl = position["size"] * (params["tp_pct"] / 100)
                balance += pnl
                trade_pnls.append(pnl)
                position = None

    total_return_pct = (balance - initial_balance) / initial_balance * 100
    wins = [t for t in trade_pnls if t > 0]
    win_rate = (len(wins) / len(trade_pnls) * 100) if trade_pnls else 0.0
    return {
        "final_balance": round(balance, 2),
        "total_return_pct": round(total_return_pct, 2),
        "num_trades": len(trade_pnls),
        "win_rate_pct": round(win_rate, 1),
    }


def run_bulk_backtest(df_raw: pd.DataFrame, n_strategies: int = 200, seed: int = 42) -> pd.DataFrame:
    random.seed(seed)
    seen = set()
    combos = []
    keys = list(PARAM_SPACE.keys())
    while len(combos) < n_strategies:
        combo = tuple(random.choice(PARAM_SPACE[k]) for k in keys)
        if combo in seen:
            continue
        seen.add(combo)
        combos.append(dict(zip(keys, combo)))

    indicator_cache = {}
    results = []
    for idx, params in enumerate(combos):
        cache_key = (params["ema_fast"], params["ema_slow"])
        if cache_key not in indicator_cache:
            indicator_cache[cache_key] = add_indicators(df_raw, ema_fast=cache_key[0], ema_slow=cache_key[1])
        df_ind = indicator_cache[cache_key]
        metrics = _run_single_backtest(df_ind, params)
        results.append({"strategy_id": idx + 1, **params, **metrics})

    report = pd.DataFrame(results).sort_values("total_return_pct", ascending=False).reset_index(drop=True)
    return report
