"""
One "AI trading cycle": fetch data -> generate signal -> validate against
hard-coded risk limits -> record a DEMO (paper) trade if approved. Also
manages the shared AccountLog row used for the daily-loss Global Shutdown.

Called both from the Streamlit app (button / auto-refresh) and from
worker.py (the GitHub Actions cron job) so the same logic drives 24/7
demo trading regardless of who triggers the cycle.
"""
import datetime
from core.data_feed import fetch_ohlcv, fetch_ticker
from core.indicators import add_indicators
from core.strategy import generate_signal
from core.risk_validator import validate_trade, RiskLimits, AccountState, format_reasoning_log
from core.db import get_session, Trade, AccountLog


def get_or_create_account(session, starting_balance: float = 10000.0) -> AccountLog:
    acc = session.query(AccountLog).first()
    if not acc:
        acc = AccountLog(balance=starting_balance, daily_pnl_pct=0.0)
        session.add(acc)
        session.commit()
        session.refresh(acc)
    return acc


def _maybe_reset_shutdown(acc: AccountLog):
    if acc.is_shutdown and acc.shutdown_until and datetime.datetime.utcnow() >= acc.shutdown_until:
        acc.is_shutdown = False
        acc.daily_pnl_pct = 0.0
        acc.shutdown_until = None


def run_cycle(symbol: str = "BTC/USDT", strategy: str = "Balanced", timeframe: str = "1h") -> dict:
    session = get_session()
    try:
        acc = get_or_create_account(session)
        _maybe_reset_shutdown(acc)
        limits = RiskLimits()
        log_lines = []

        # 1. Manage open positions for this symbol against latest price
        ticker = fetch_ticker(symbol)
        last_price = ticker["last"]
        open_trades = session.query(Trade).filter(Trade.symbol == symbol, Trade.status == "open").all()
        for t in open_trades:
            hit = None
            if t.action == "buy":
                if last_price <= t.stop_loss:
                    hit = "sl"
                elif last_price >= t.take_profit:
                    hit = "tp"
            else:
                if last_price >= t.stop_loss:
                    hit = "sl"
                elif last_price <= t.take_profit:
                    hit = "tp"
            if hit:
                pnl_pct = (
                    (last_price - t.entry_price) / t.entry_price * 100
                    if t.action == "buy"
                    else (t.entry_price - last_price) / t.entry_price * 100
                )
                t.status = f"closed_{hit}"
                t.exit_price = last_price
                t.pnl_pct = round(pnl_pct, 2)
                t.closed_at = datetime.datetime.utcnow()
                acc.daily_pnl_pct += pnl_pct * (t.position_size_pct / 100)
                log_lines.append(f"{t.symbol} {t.action.upper()} closed at {hit.upper()} ({pnl_pct:.2f}%)")

        # 2. Global shutdown check
        if acc.daily_pnl_pct <= -abs(limits.max_daily_loss_pct):
            acc.is_shutdown = True
            acc.shutdown_until = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
            session.commit()
            log_lines.append("GLOBAL SHUTDOWN triggered — daily loss limit breached. No trades for 24h.")
            return {"log": "\n".join(log_lines), "shutdown": True}

        if acc.is_shutdown:
            session.commit()
            log_lines.append("Account in shutdown state — no new trades.")
            return {"log": "\n".join(log_lines), "shutdown": True}

        # 3. Generate + validate a new signal only if no open position on this symbol
        still_open = session.query(Trade).filter(Trade.symbol == symbol, Trade.status == "open").count()
        if still_open == 0:
            df = fetch_ohlcv(symbol, timeframe=timeframe)
            df = add_indicators(df)
            signal = generate_signal(df, strategy=strategy)
            signal["symbol"] = symbol

            account_state = AccountState(total_balance=acc.balance, daily_pnl_pct=acc.daily_pnl_pct)
            result = validate_trade(signal, account_state, limits)
            log_lines.append(format_reasoning_log(result, strategy=strategy))

            if result.is_valid and result.sanitized_order and result.sanitized_order["action"] != "hold":
                o = result.sanitized_order
                session.add(Trade(
                    symbol=o["symbol"], action=o["action"], entry_price=o["entry_price"],
                    stop_loss=o["stop_loss"], take_profit=o["take_profit"],
                    position_size_pct=o["position_size_pct"], trade_value=o["trade_value"],
                    strategy=strategy, reason=o["reason"], mode="demo", status="open",
                ))

        session.commit()
        return {"log": "\n".join(log_lines), "shutdown": False}
    finally:
        session.close()
