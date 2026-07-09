"""
Trade Validation Layer
-----------------------
Sits between the AI agent's JSON output and the exchange (CCXT).
It NEVER sends an AI response straight to the exchange. Every field
is re-checked against the user's own hard-coded risk limits before
an order is allowed to proceed.
"""

from dataclasses import dataclass, field
from typing import Optional
import datetime


@dataclass
class RiskLimits:
    max_position_pct: float = 5.0
    max_sl_pct: float = 2.0
    min_tp_pct: float = 5.0
    min_risk_reward: float = 2.0
    max_daily_loss_pct: float = 10.0
    allowed_symbols: Optional[list] = None


@dataclass
class AccountState:
    total_balance: float
    daily_pnl_pct: float = 0.0
    is_shutdown: bool = False
    shutdown_until: Optional[datetime.datetime] = None


@dataclass
class ValidationResult:
    is_valid: bool
    reasons: list = field(default_factory=list)
    sanitized_order: Optional[dict] = None


def validate_trade(ai_response: dict, account: AccountState, limits: RiskLimits) -> ValidationResult:
    reasons = []

    if account.is_shutdown:
        return ValidationResult(False, ["Account is in Global Shutdown state. No trades allowed."])

    if account.daily_pnl_pct <= -abs(limits.max_daily_loss_pct):
        account.is_shutdown = True
        account.shutdown_until = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        return ValidationResult(False, [
            f"Daily loss limit breached ({account.daily_pnl_pct}%). "
            f"Global Shutdown activated for 24 hours."
        ])

    required_fields = ["action", "symbol", "entry_price", "stop_loss",
                        "take_profit", "position_size_pct"]
    missing = [f for f in required_fields if f not in ai_response]
    if missing:
        return ValidationResult(False, [f"Missing required field(s): {missing}"])

    action = str(ai_response["action"]).lower()
    symbol = ai_response["symbol"]
    entry = float(ai_response["entry_price"])
    sl = float(ai_response["stop_loss"])
    tp = float(ai_response["take_profit"])
    size_pct = float(ai_response["position_size_pct"])

    if action not in ("buy", "sell", "hold"):
        reasons.append(f"Invalid action '{action}'.")

    if action == "hold":
        return ValidationResult(True, ["Hold signal, no order placed."], {"action": "hold"})

    if limits.allowed_symbols and symbol not in limits.allowed_symbols:
        reasons.append(f"Symbol '{symbol}' is not in the allowed list.")

    if size_pct > limits.max_position_pct:
        reasons.append(f"Position size {size_pct}% exceeds max allowed {limits.max_position_pct}%.")
    if size_pct <= 0:
        reasons.append("Position size must be positive.")

    if entry <= 0:
        reasons.append("Entry price must be positive.")
    else:
        sl_pct = abs((entry - sl) / entry) * 100
        if action == "buy" and sl >= entry:
            reasons.append("Stop-loss must be below entry price for a buy order.")
        if action == "sell" and sl <= entry:
            reasons.append("Stop-loss must be above entry price for a sell order.")
        if sl_pct > limits.max_sl_pct + 1e-9:
            reasons.append(f"Stop-loss distance {sl_pct:.2f}% exceeds max allowed {limits.max_sl_pct}%.")

    if action == "buy" and tp <= entry:
        reasons.append("Take-profit must be above entry price for a buy order.")
    if action == "sell" and tp >= entry:
        reasons.append("Take-profit must be below entry price for a sell order.")

    if entry > 0 and sl != entry:
        risk = abs(entry - sl)
        reward = abs(tp - entry)
        rr_ratio = reward / risk if risk > 0 else 0
        if rr_ratio < limits.min_risk_reward:
            reasons.append(
                f"Risk/Reward ratio {rr_ratio:.2f} is below minimum required {limits.min_risk_reward}:1."
            )
    else:
        rr_ratio = 0
        reasons.append("Cannot compute Risk/Reward ratio (invalid SL/entry).")

    trade_value = account.total_balance * (size_pct / 100)
    if trade_value > account.total_balance:
        reasons.append("Insufficient balance for the requested trade size.")

    is_valid = len(reasons) == 0
    sanitized_order = None
    if is_valid:
        sanitized_order = {
            "action": action,
            "symbol": symbol,
            "entry_price": entry,
            "stop_loss": sl,
            "take_profit": tp,
            "position_size_pct": size_pct,
            "trade_value": round(trade_value, 2),
            "risk_reward_ratio": round(rr_ratio, 2),
            "reason": ai_response.get("reason", ""),
        }

    return ValidationResult(is_valid, reasons, sanitized_order)


def format_reasoning_log(result: ValidationResult, strategy: str = "Balanced") -> str:
    if result.is_valid and result.sanitized_order and result.sanitized_order["action"] != "hold":
        o = result.sanitized_order
        return (
            f"[Reasoning Log]\n"
            f"Symbol: {o['symbol']}\n"
            f"Action: {o['action'].upper()}\n"
            f"Entry Price: {o['entry_price']}\n"
            f"Stop-Loss: {o['stop_loss']}\n"
            f"Take-Profit: {o['take_profit']}\n"
            f"Position Size: {o['position_size_pct']}% (${o['trade_value']})\n"
            f"Risk/Reward: 1:{o['risk_reward_ratio']}\n"
            f"Strategy: {strategy}\n"
            f"Reason: {o['reason']}\n"
            f"Status: APPROVED"
        )
    elif result.is_valid:
        return "[Reasoning Log] No action taken (HOLD signal)."
    else:
        return "[Reasoning Log] Status: REJECTED\nReasons:\n- " + "\n- ".join(result.reasons)
