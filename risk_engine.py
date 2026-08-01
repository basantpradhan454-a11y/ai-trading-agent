"""
FinsageAI Risk Engine — CRO (Chief Risk Officer) Module
Institutional Trading Risk Management, Dynamic Exits, Circuit Breakers, State Machine, and Signal Scanner.

File: /app/finsage/risk_engine.py
Theme: Dark theme with Cyan (#22d3ee), Violet (#7c6ff0), Dark Background (#0a0e14), Card (#0f172a).
CSS Class: finsage-card
"""

import datetime
import math
import time
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS & THEME
# ─────────────────────────────────────────────────────────────────────────────
COLOR_CYAN = "#22d3ee"
COLOR_VIOLET = "#7c6ff0"
COLOR_BG = "#0a0e14"
COLOR_CARD = "#0f172a"
COLOR_BORDER = "#1e293b"
COLOR_TEXT = "#e2e8f0"
COLOR_MUTED = "#8b93a7"
COLOR_SUCCESS = "#10b981"
COLOR_DANGER = "#ef4444"
COLOR_WARNING = "#f59e0b"

# Limits & Rules
MAX_RISK_PER_TRADE_PCT = 1.0     # Never risk more than 1% of total account equity
MAX_DAILY_DRAWDOWN_PCT = 3.0      # 3% daily drop triggers 24h kill-switch
MAX_CONSECUTIVE_LOSSES = 4        # 4 consecutive losses trigger emergency halt
KILL_SWITCH_DURATION_HOURS = 24

# State Machine Enums
STATE_IDLE = "IDLE"
STATE_SCANNING = "SCANNING"
STATE_ENTRY_PENDING = "ENTRY_PENDING"
STATE_POSITION_ACTIVE = "POSITION_ACTIVE"
STATE_CLOSED = "CLOSED"
STATE_KILL_SWITCH = "KILL_SWITCH"

VALID_STATES = [
    STATE_IDLE,
    STATE_SCANNING,
    STATE_ENTRY_PENDING,
    STATE_POSITION_ACTIVE,
    STATE_CLOSED,
    STATE_KILL_SWITCH,
]

# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM CSS INJECTION
# ─────────────────────────────────────────────────────────────────────────────
def inject_finsage_css():
    """Inject CSS styling matching FinsageAI visual identity."""
    st.markdown(
        f"""
        <style>
        /* Base page tweaks */
        .stApp {{
            background-color: {COLOR_BG};
            color: {COLOR_TEXT};
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }}
        
        /* Finsage Card styling */
        .finsage-card {{
            background: {COLOR_CARD};
            border: 1px solid {COLOR_BORDER};
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 16px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
            color: {COLOR_TEXT};
        }}

        .finsage-card-header {{
            font-size: 16px;
            font-weight: 700;
            letter-spacing: 0.5px;
            color: {COLOR_CYAN};
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}

        .finsage-card-title {{
            font-size: 14px;
            font-weight: 600;
            color: {COLOR_MUTED};
            text-transform: uppercase;
            letter-spacing: 0.8px;
        }}

        .finsage-badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 9999px;
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .badge-idle {{ background: rgba(139, 147, 167, 0.2); color: {COLOR_MUTED}; border: 1px solid {COLOR_MUTED}; }}
        .badge-scanning {{ background: rgba(34, 211, 238, 0.2); color: {COLOR_CYAN}; border: 1px solid {COLOR_CYAN}; }}
        .badge-entry_pending {{ background: rgba(245, 158, 11, 0.2); color: {COLOR_WARNING}; border: 1px solid {COLOR_WARNING}; }}
        .badge-position_active {{ background: rgba(124, 111, 240, 0.2); color: {COLOR_VIOLET}; border: 1px solid {COLOR_VIOLET}; }}
        .badge-closed {{ background: rgba(16, 185, 129, 0.2); color: {COLOR_SUCCESS}; border: 1px solid {COLOR_SUCCESS}; }}
        .badge-kill_switch {{ background: rgba(239, 68, 68, 0.25); color: {COLOR_DANGER}; border: 1px solid {COLOR_DANGER}; }}

        /* Metric Highlights */
        .metric-value {{
            font-size: 24px;
            font-weight: 700;
            color: #ffffff;
            margin-top: 4px;
        }}
        .metric-subtext {{
            font-size: 12px;
            color: {COLOR_MUTED};
            margin-top: 2px;
        }}

        /* Signal Match Pill */
        .match-pass {{
            color: {COLOR_SUCCESS};
            font-weight: 700;
        }}
        .match-fail {{
            color: {COLOR_DANGER};
            font-weight: 700;
        }}

        /* Progress Bar override */
        .stProgress > div > div > div > div {{
            background-color: {COLOR_CYAN};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1. POSITION SIZING ENGINE
# ─────────────────────────────────────────────────────────────────────────────
class PositionSizer:
    """
    Calculates position sizes based on Fixed Fractional (1% max equity risk)
    and Kelly Criterion logic.
    """

    @staticmethod
    def calculate_fixed_fractional(
        equity: float,
        entry_price: float,
        stop_loss_price: float,
        risk_pct: float = 1.0,
    ) -> dict:
        """
        Formula: Position Size = (Equity * Risk per Trade) / |Entry Price - Stop Loss Price|
        Enforces maximum 1% risk per trade.
        """
        if equity <= 0:
            return {"error": "Equity must be greater than 0"}
        if entry_price <= 0 or stop_loss_price <= 0:
            return {"error": "Entry and Stop Loss prices must be greater than 0"}
        
        risk_per_unit = abs(entry_price - stop_loss_price)
        if risk_per_unit == 0:
            return {"error": "Entry Price and Stop Loss Price cannot be identical"}

        # Strictly cap risk at 1.0% maximum
        effective_risk_pct = min(abs(risk_pct), MAX_RISK_PER_TRADE_PCT)
        risk_amount = equity * (effective_risk_pct / 100.0)

        position_size_units = risk_amount / risk_per_unit
        position_value = position_size_units * entry_price
        leverage_required = position_value / equity if equity > 0 else 0

        is_capped = abs(risk_pct) > MAX_RISK_PER_TRADE_PCT

        return {
            "method": "Fixed Fractional",
            "requested_risk_pct": risk_pct,
            "effective_risk_pct": effective_risk_pct,
            "equity": equity,
            "entry_price": entry_price,
            "stop_loss_price": stop_loss_price,
            "risk_per_unit": risk_per_unit,
            "risk_amount": risk_amount,
            "position_size_units": position_size_units,
            "position_value": position_value,
            "leverage_required": leverage_required,
            "risk_capped_warning": is_capped,
            "capped_limit_pct": MAX_RISK_PER_TRADE_PCT,
        }

    @staticmethod
    def calculate_kelly(
        equity: float,
        entry_price: float,
        stop_loss_price: float,
        win_rate: float,
        win_loss_ratio: float,
        kelly_fraction: float = 0.5,
    ) -> dict:
        """
        Formula: Kelly% = W - (1 - W) / R
        where W = win rate (0..1), R = win/loss ratio (Reward/Risk).
        """
        if equity <= 0:
            return {"error": "Equity must be greater than 0"}
        if entry_price <= 0 or stop_loss_price <= 0:
            return {"error": "Entry and Stop Loss prices must be greater than 0"}

        risk_per_unit = abs(entry_price - stop_loss_price)
        if risk_per_unit == 0:
            return {"error": "Entry Price and Stop Loss Price cannot be identical"}

        # Normalize win_rate if passed as percentage (e.g. 55 -> 0.55)
        w = win_rate / 100.0 if win_rate > 1.0 else win_rate
        w = max(0.0, min(1.0, w))

        r = max(0.001, win_loss_ratio)

        # Full Kelly formula: Kelly% = W - (1 - W) / R
        full_kelly_pct = (w - ((1.0 - w) / r)) * 100.0
        
        # Fractional Kelly
        adjusted_kelly_pct = full_kelly_pct * max(0.0, kelly_fraction)

        # Kelly can be negative or zero (indicating no edge)
        has_positive_edge = adjusted_kelly_pct > 0

        # Cap recommended trade risk at 1% max account equity limit
        if has_positive_edge:
            recommended_risk_pct = min(adjusted_kelly_pct, MAX_RISK_PER_TRADE_PCT)
        else:
            recommended_risk_pct = 0.0

        risk_amount = equity * (recommended_risk_pct / 100.0)
        position_size_units = risk_amount / risk_per_unit if risk_per_unit > 0 else 0
        position_value = position_size_units * entry_price
        leverage_required = position_value / equity if equity > 0 else 0

        return {
            "method": "Kelly Criterion",
            "win_rate_pct": w * 100.0,
            "win_loss_ratio": r,
            "full_kelly_pct": full_kelly_pct,
            "kelly_fraction": kelly_fraction,
            "adjusted_kelly_pct": adjusted_kelly_pct,
            "has_positive_edge": has_positive_edge,
            "recommended_risk_pct": recommended_risk_pct,
            "risk_amount": risk_amount,
            "position_size_units": position_size_units,
            "position_value": position_value,
            "leverage_required": leverage_required,
            "cap_applied": adjusted_kelly_pct > MAX_RISK_PER_TRADE_PCT,
        }


# ─────────────────────────────────────────────────────────────────────────────
# 2. DYNAMIC EXITS ENGINE
# ─────────────────────────────────────────────────────────────────────────────
class DynamicExitEngine:
    """
    Computes ATR-based Hard Stop Loss, Take Profit (min 1:2 R:R),
    and 1:1 Profit Locking Trailing Stops.
    """

    @staticmethod
    def calculate_exits(
        entry_price: float,
        atr: float,
        direction: str = "LONG",
        rr_ratio: float = 2.0,
        current_price: float = None,
    ) -> dict:
        """
        - Hard Stop Loss: 1.5 * ATR below entry for Longs, above for Shorts
        - Take Profit: minimum 1:2 Risk-to-Reward ratio
        - Trailing Stop: activates at 1:1 R:R, locks 50% of peak profits
        """
        direction = direction.upper()
        if direction not in ["LONG", "SHORT"]:
            direction = "LONG"

        atr = max(0.0001, abs(atr))
        rr_ratio = max(2.0, rr_ratio)  # Minimum 1:2 R:R enforced

        risk_distance = 1.5 * atr
        reward_distance = risk_distance * rr_ratio

        if direction == "LONG":
            hard_sl = entry_price - risk_distance
            take_profit = entry_price + reward_distance
            trailing_activation_price = entry_price + risk_distance
        else:  # SHORT
            hard_sl = entry_price + risk_distance
            take_profit = entry_price - reward_distance
            trailing_activation_price = entry_price - risk_distance

        # Evaluate current price & trailing stop status
        cp = current_price if current_price is not None else entry_price

        is_trailing_active = False
        locked_profit_per_unit = 0.0
        trailing_stop_level = hard_sl

        if direction == "LONG":
            pnl_per_unit = cp - entry_price
            if cp >= trailing_activation_price:
                is_trailing_active = True
                # Lock 50% of unrealized profit
                locked_profit_per_unit = max(0.0, pnl_per_unit * 0.5)
                trailing_stop_level = max(hard_sl, entry_price + locked_profit_per_unit)
        else:  # SHORT
            pnl_per_unit = entry_price - cp
            if cp <= trailing_activation_price:
                is_trailing_active = True
                # Lock 50% of unrealized profit
                locked_profit_per_unit = max(0.0, pnl_per_unit * 0.5)
                trailing_stop_level = min(hard_sl, entry_price - locked_profit_per_unit)

        return {
            "entry_price": entry_price,
            "atr": atr,
            "direction": direction,
            "rr_ratio": rr_ratio,
            "risk_distance": risk_distance,
            "reward_distance": reward_distance,
            "hard_stop_loss": hard_sl,
            "take_profit": take_profit,
            "trailing_activation_price": trailing_activation_price,
            "current_price": cp,
            "is_trailing_active": is_trailing_active,
            "locked_profit_per_unit": locked_profit_per_unit,
            "effective_stop_loss": trailing_stop_level,
            "risk_per_unit": risk_distance,
            "reward_per_unit": reward_distance,
        }


# ─────────────────────────────────────────────────────────────────────────────
# 3 & 4. CIRCUIT BREAKERS & STATE MACHINE
# ─────────────────────────────────────────────────────────────────────────────
class CircuitBreakerManager:
    """
    Manages Max Daily Drawdown (3%), Max Consecutive Losses (4),
    and State Transitions for FinsageAI.
    """

    @staticmethod
    def evaluate_circuit_breakers(
        starting_daily_equity: float,
        current_equity: float,
        consecutive_losses: int,
        kill_switch_active: bool = False,
    ) -> dict:
        """
        Checks max daily drawdown >= 3% and max consecutive losses >= 4.
        """
        if starting_daily_equity <= 0:
            drawdown_pct = 0.0
        else:
            drawdown = max(0.0, starting_daily_equity - current_equity)
            drawdown_pct = (drawdown / starting_daily_equity) * 100.0

        drawdown_breach = drawdown_pct >= MAX_DAILY_DRAWDOWN_PCT
        losses_breach = consecutive_losses >= MAX_CONSECUTIVE_LOSSES

        should_trigger_kill_switch = drawdown_breach or losses_breach or kill_switch_active

        breach_reasons = []
        if drawdown_breach:
            breach_reasons.append(
                f"Max Daily Drawdown breached ({drawdown_pct:.2f}% >= {MAX_DAILY_DRAWDOWN_PCT}%)"
            )
        if losses_breach:
            breach_reasons.append(
                f"Max Consecutive Losses breached ({consecutive_losses} >= {MAX_CONSECUTIVE_LOSSES})"
            )
        if kill_switch_active and not (drawdown_breach or losses_breach):
            breach_reasons.append("Manual Emergency Kill Switch Activated")

        return {
            "drawdown_pct": drawdown_pct,
            "max_drawdown_limit_pct": MAX_DAILY_DRAWDOWN_PCT,
            "drawdown_breach": drawdown_breach,
            "consecutive_losses": consecutive_losses,
            "max_consecutive_losses_limit": MAX_CONSECUTIVE_LOSSES,
            "losses_breach": losses_breach,
            "should_trigger_kill_switch": should_trigger_kill_switch,
            "breach_reasons": breach_reasons,
        }


class RiskStateMachine:
    """State machine controller for bot execution status."""

    def __init__(self, current_state: str = STATE_IDLE):
        if current_state not in VALID_STATES:
            current_state = STATE_IDLE
        self.state = current_state

    def transition_to(self, new_state: str, is_kill_switch_tripped: bool = False) -> tuple[bool, str]:
        """Validates and performs state transition."""
        new_state = new_state.upper()
        if new_state not in VALID_STATES:
            return False, f"Invalid state requested: {new_state}"

        # Kill Switch override
        if is_kill_switch_tripped or new_state == STATE_KILL_SWITCH:
            self.state = STATE_KILL_SWITCH
            return True, "Emergency Kill Switch Activated — System Locked for 24h!"

        # Block leaving KILL_SWITCH if kill switch is active
        if self.state == STATE_KILL_SWITCH and new_state != STATE_IDLE:
            return False, "Cannot transition out of KILL_SWITCH without manual circuit breaker reset!"

        # State transition validation
        valid_transitions = {
            STATE_IDLE: [STATE_SCANNING, STATE_KILL_SWITCH],
            STATE_SCANNING: [STATE_ENTRY_PENDING, STATE_IDLE, STATE_KILL_SWITCH],
            STATE_ENTRY_PENDING: [STATE_POSITION_ACTIVE, STATE_IDLE, STATE_KILL_SWITCH],
            STATE_POSITION_ACTIVE: [STATE_CLOSED, STATE_KILL_SWITCH],
            STATE_CLOSED: [STATE_IDLE, STATE_SCANNING, STATE_KILL_SWITCH],
            STATE_KILL_SWITCH: [STATE_IDLE],
        }

        if new_state in valid_transitions.get(self.state, []):
            old_state = self.state
            self.state = new_state
            return True, f"State transitioned from {old_state} -> {new_state}"
        else:
            return False, f"Illegal transition from {self.state} to {new_state}"


# ─────────────────────────────────────────────────────────────────────────────
# 5. TECHNICAL INDICATOR ENGINE & SIGNAL SCANNER
# ─────────────────────────────────────────────────────────────────────────────
class TechnicalIndicators:
    """Calculates EMA, Bollinger Bands, RSI, MACD, and RSI Divergence."""

    @staticmethod
    def calculate_ema(series: pd.Series, period: int = 200) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()

    @staticmethod
    def calculate_bollinger_bands(
        series: pd.Series, period: int = 20, std_dev: float = 2.0
    ) -> tuple[pd.Series, pd.Series, pd.Series]:
        sma = series.rolling(window=period).mean()
        std = series.rolling(window=period).std()
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        return upper, sma, lower

    @staticmethod
    def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50)

    @staticmethod
    def calculate_macd(
        series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
    ) -> tuple[pd.Series, pd.Series, pd.Series]:
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        high = df['high']
        low = df['low']
        close = df['close']
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return atr.bfill()

    @staticmethod
    def detect_rsi_divergence(
        close_series: pd.Series, rsi_series: pd.Series, lookback: int = 10
    ) -> tuple[bool, bool]:
        """
        Bullish Divergence: Price makes lower low while RSI makes higher low.
        Bearish Divergence: Price makes higher high while RSI makes lower high.
        """
        if len(close_series) < lookback:
            return False, False

        recent_prices = close_series.iloc[-lookback:].values
        recent_rsi = rsi_series.iloc[-lookback:].values

        half = lookback // 2
        price_prev_min = np.min(recent_prices[:half])
        price_curr_min = recent_prices[-1]

        rsi_prev_min = np.min(recent_rsi[:half])
        rsi_curr_min = recent_rsi[-1]

        price_prev_max = np.max(recent_prices[:half])
        price_curr_max = recent_prices[-1]

        rsi_prev_max = np.max(recent_rsi[:half])
        rsi_curr_max = recent_rsi[-1]

        # Bullish Divergence
        bullish_div = (price_curr_min < price_prev_min) and (rsi_curr_min > rsi_prev_min) and (recent_rsi[-1] < 45)

        # Bearish Divergence
        bearish_div = (price_curr_max > price_prev_max) and (rsi_curr_max < rsi_prev_max) and (recent_rsi[-1] > 55)

        return bool(bullish_div), bool(bearish_div)


class SignalScanner:
    """
    4H + 15M multi-timeframe entry trigger scanner.
    LONG: 4H price > 200 EMA, 15M touches lower BB, 15M RSI < 30 + Bullish Div, 15M MACD green (>0).
    SHORT: 4H price < 200 EMA, 15M touches upper BB, 15M RSI > 70 + Bearish Div, 15M MACD red (<0).
    All 4 criteria must match simultaneously.
    """

    @staticmethod
    def scan_asset(symbol: str, df_4h: pd.DataFrame, df_15m: pd.DataFrame) -> dict:
        # Prepare 4H indicator
        df_4h = df_4h.copy()
        df_4h['ema_200'] = TechnicalIndicators.calculate_ema(df_4h['close'], 200)

        price_4h = df_4h['close'].iloc[-1]
        ema_200_4h = df_4h['ema_200'].iloc[-1]

        # Prepare 15M indicators
        df_15m = df_15m.copy()
        df_15m['upper_bb'], df_15m['mid_bb'], df_15m['lower_bb'] = TechnicalIndicators.calculate_bollinger_bands(
            df_15m['close'], 20, 2
        )
        df_15m['rsi'] = TechnicalIndicators.calculate_rsi(df_15m['close'], 14)
        df_15m['macd'], df_15m['signal'], df_15m['hist'] = TechnicalIndicators.calculate_macd(
            df_15m['close'], 12, 26, 9
        )
        df_15m['atr'] = TechnicalIndicators.calculate_atr(df_15m, 14)

        price_15m = df_15m['close'].iloc[-1]
        lower_bb_15m = df_15m['lower_bb'].iloc[-1]
        upper_bb_15m = df_15m['upper_bb'].iloc[-1]
        rsi_15m = df_15m['rsi'].iloc[-1]
        macd_hist_15m = df_15m['hist'].iloc[-1]
        atr_15m = df_15m['atr'].iloc[-1]

        bullish_div, bearish_div = TechnicalIndicators.detect_rsi_divergence(
            df_15m['close'], df_15m['rsi'], lookback=12
        )

        # Evaluate LONG criteria
        c1_long = price_4h > ema_200_4h
        c2_long = price_15m <= lower_bb_15m * 1.002  # Touch or dip below lower BB
        c3_long = (rsi_15m < 35) or (rsi_15m < 45 and bullish_div)  # Strong RSI low or RSI low with bullish div
        c4_long = macd_hist_15m > 0

        long_match_count = sum([c1_long, c2_long, c3_long, c4_long])
        long_signal = long_match_count == 4

        # Evaluate SHORT criteria
        c1_short = price_4h < ema_200_4h
        c2_short = price_15m >= upper_bb_15m * 0.998  # Touch or exceed upper BB
        c3_short = (rsi_15m > 65) or (rsi_15m > 55 and bearish_div)  # Strong RSI high or RSI high with bearish div
        c4_short = macd_hist_15m < 0

        short_match_count = sum([c1_short, c2_short, c3_short, c4_short])
        short_signal = short_match_count == 4

        if long_signal:
            signal_type = "LONG"
        elif short_signal:
            signal_type = "SHORT"
        else:
            signal_type = "NEUTRAL"

        return {
            "symbol": symbol,
            "signal": signal_type,
            "price_15m": price_15m,
            "price_4h": price_4h,
            "ema_200_4h": ema_200_4h,
            "atr_15m": atr_15m,
            "rsi_15m": rsi_15m,
            "macd_hist_15m": macd_hist_15m,
            "upper_bb_15m": upper_bb_15m,
            "lower_bb_15m": lower_bb_15m,
            "bullish_div": bullish_div,
            "bearish_div": bearish_div,
            "long_criteria": {
                "4H_above_200EMA": c1_long,
                "15M_touch_lower_BB": c2_long,
                "15M_RSI_low_div": c3_long,
                "15M_MACD_green": c4_long,
                "score": f"{long_match_count}/4",
            },
            "short_criteria": {
                "4H_below_200EMA": c1_short,
                "15M_touch_upper_BB": c2_short,
                "15M_RSI_high_div": c3_short,
                "15M_MACD_red": c4_short,
                "score": f"{short_match_count}/4",
            },
            "df_4h": df_4h,
            "df_15m": df_15m,
        }

    @staticmethod
    def generate_mock_market_data(symbol: str, force_signal: str = None) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Generates realistic market candles for testing and demonstration."""
        np.random.seed(abs(hash(symbol)) % 10000)

        base_prices = {
            "BTC/USDT": 64500.0,
            "ETH/USDT": 3480.0,
            "SOL/USDT": 182.0,
            "NIFTY50": 24350.0,
            "BANKNIFTY": 51200.0,
        }
        base_price = base_prices.get(symbol, 1000.0)

        # 4H data (250 candles)
        dates_4h = pd.date_range(end=datetime.datetime.now(), periods=250, freq='4h')
        returns_4h = np.random.normal(0.0003, 0.012, 250)
        
        if force_signal == "LONG":
            returns_4h += 0.002  # Bullish drift for 4H
        elif force_signal == "SHORT":
            returns_4h -= 0.002  # Bearish drift for 4H

        price_path_4h = base_price * np.cumprod(1 + returns_4h)
        highs_4h = price_path_4h * (1 + abs(np.random.normal(0, 0.005, 250)))
        lows_4h = price_path_4h * (1 - abs(np.random.normal(0, 0.005, 250)))

        df_4h = pd.DataFrame({
            "timestamp": dates_4h,
            "open": price_path_4h * (1 - np.random.normal(0, 0.002, 250)),
            "high": highs_4h,
            "low": lows_4h,
            "close": price_path_4h,
            "volume": np.random.randint(1000, 50000, 250),
        })

        # 15M data (150 candles)
        dates_15m = pd.date_range(end=datetime.datetime.now(), periods=150, freq='15min')
        returns_15m = np.random.normal(0.0, 0.004, 150)
        
        # Adjust end of 15m to create specific pattern if requested
        if force_signal == "LONG":
            returns_15m[-15:] = -0.006  # Dip to lower BB
            returns_15m[-1] = 0.002     # Turn MACD positive
        elif force_signal == "SHORT":
            returns_15m[-15:] = 0.006   # Surge to upper BB
            returns_15m[-1] = -0.002    # Turn MACD negative

        price_path_15m = price_path_4h[-1] * np.cumprod(1 + returns_15m)
        highs_15m = price_path_15m * (1 + abs(np.random.normal(0, 0.002, 150)))
        lows_15m = price_path_15m * (1 - abs(np.random.normal(0, 0.002, 150)))

        df_15m = pd.DataFrame({
            "timestamp": dates_15m,
            "open": price_path_15m * (1 - np.random.normal(0, 0.001, 150)),
            "high": highs_15m,
            "low": lows_15m,
            "close": price_path_15m,
            "volume": np.random.randint(200, 10000, 150),
        })

        return df_4h, df_15m


# ─────────────────────────────────────────────────────────────────────────────
# 6 & 7. STREAMLIT UI RENDERER
# ─────────────────────────────────────────────────────────────────────────────
def render_risk_engine_page():
    """
    Main Streamlit entry point for the FinsageAI CRO Risk Engine module.
    Exposes position sizers, dynamic exit calculators, signal scanner,
    circuit breakers, and risk dashboard.
    """
    inject_finsage_css()

    # Initialize Session State Variables
    if "equity" not in st.session_state:
        st.session_state.equity = 100000.0
    if "starting_daily_equity" not in st.session_state:
        st.session_state.starting_daily_equity = 100000.0
    if "consecutive_losses" not in st.session_state:
        st.session_state.consecutive_losses = 0
    if "total_trades" not in st.session_state:
        st.session_state.total_trades = 12
    if "winning_trades" not in st.session_state:
        st.session_state.winning_trades = 7
    if "bot_state" not in st.session_state:
        st.session_state.bot_state = STATE_SCANNING
    if "kill_switch_active" not in st.session_state:
        st.session_state.kill_switch_active = False
    if "kill_switch_timestamp" not in st.session_state:
        st.session_state.kill_switch_timestamp = None
    if "trade_history" not in st.session_state:
        st.session_state.trade_history = [
            {"id": "TRD-101", "type": "LONG", "pnl": 420.0, "result": "WIN"},
            {"id": "TRD-102", "type": "SHORT", "pnl": 610.0, "result": "WIN"},
            {"id": "TRD-103", "type": "LONG", "pnl": -250.0, "result": "LOSS"},
            {"id": "TRD-104", "type": "LONG", "pnl": 530.0, "result": "WIN"},
        ]

    # Evaluate Circuit Breakers
    cb_metrics = CircuitBreakerManager.evaluate_circuit_breakers(
        starting_daily_equity=st.session_state.starting_daily_equity,
        current_equity=st.session_state.equity,
        consecutive_losses=st.session_state.consecutive_losses,
        kill_switch_active=st.session_state.kill_switch_active,
    )

    # Sync Kill Switch state
    if cb_metrics["should_trigger_kill_switch"] and st.session_state.bot_state != STATE_KILL_SWITCH:
        st.session_state.bot_state = STATE_KILL_SWITCH
        st.session_state.kill_switch_active = True
        if not st.session_state.kill_switch_timestamp:
            st.session_state.kill_switch_timestamp = datetime.datetime.now()

    # Calculate Top Metrics
    daily_pnl = st.session_state.equity - st.session_state.starting_daily_equity
    daily_pnl_pct = (daily_pnl / st.session_state.starting_daily_equity) * 100.0 if st.session_state.starting_daily_equity > 0 else 0.0
    win_rate_pct = (st.session_state.winning_trades / st.session_state.total_trades) * 100.0 if st.session_state.total_trades > 0 else 0.0

    # ── TOP BAR HEADER ──
    st.markdown(
        f"""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 20px; border-bottom: 1px solid {COLOR_BORDER}; padding-bottom: 12px;">
            <div>
                <h1 style="color:{COLOR_CYAN}; margin:0; font-size: 28px; font-weight:800; letter-spacing: -0.5px;">
                    🛡️ FinsageAI — CRO Risk Engine
                </h1>
                <p style="color:{COLOR_MUTED}; margin:4px 0 0 0; font-size:14px;">
                    Institutional Risk Control • Kelly Position Sizer • Dynamic Exits • Circuit Breakers
                </p>
            </div>
            <div>
                <span class="finsage-badge badge-{st.session_state.bot_state.lower()}">
                    State: {st.session_state.bot_state}
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Emergency Kill Switch Alert Banner if Active
    if st.session_state.bot_state == STATE_KILL_SWITCH or st.session_state.kill_switch_active:
        reasons_str = " | ".join(cb_metrics["breach_reasons"]) if cb_metrics["breach_reasons"] else "Manual Lockout"
        st.error(f"🚨 **CIRCUIT BREAKER ACTIVATED / KILL SWITCH ENGAGED**: {reasons_str}. All trading activity suspended.")

    # ── METRICS DASHBOARD ROW ──
    m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)

    with m_col1:
        st.markdown(
            f"""
            <div class="finsage-card" style="padding: 14px; text-align: center;">
                <div class="finsage-card-title">Account Equity</div>
                <div class="metric-value">${st.session_state.equity:,.2f}</div>
                <div class="metric-subtext">Start: ${st.session_state.starting_daily_equity:,.2f}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with m_col2:
        pnl_color = COLOR_SUCCESS if daily_pnl >= 0 else COLOR_DANGER
        st.markdown(
            f"""
            <div class="finsage-card" style="padding: 14px; text-align: center;">
                <div class="finsage-card-title">Daily P&L</div>
                <div class="metric-value" style="color:{pnl_color};">${daily_pnl:+,.2f}</div>
                <div class="metric-subtext" style="color:{pnl_color};">{daily_pnl_pct:+.2f}%</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with m_col3:
        dd_color = COLOR_DANGER if cb_metrics["drawdown_breach"] else (COLOR_WARNING if cb_metrics["drawdown_pct"] > 1.5 else COLOR_SUCCESS)
        st.markdown(
            f"""
            <div class="finsage-card" style="padding: 14px; text-align: center;">
                <div class="finsage-card-title">Daily Drawdown</div>
                <div class="metric-value" style="color:{dd_color};">{cb_metrics['drawdown_pct']:.2f}%</div>
                <div class="metric-subtext">Limit: {MAX_DAILY_DRAWDOWN_PCT:.1f}%</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with m_col4:
        st.markdown(
            f"""
            <div class="finsage-card" style="padding: 14px; text-align: center;">
                <div class="finsage-card-title">Win Rate</div>
                <div class="metric-value" style="color:{COLOR_CYAN};">{win_rate_pct:.1f}%</div>
                <div class="metric-subtext">{st.session_state.winning_trades}W / {st.session_state.total_trades - st.session_state.winning_trades}L ({st.session_state.total_trades} Trades)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with m_col5:
        loss_color = COLOR_DANGER if cb_metrics["losses_breach"] else (COLOR_WARNING if st.session_state.consecutive_losses >= 2 else COLOR_SUCCESS)
        st.markdown(
            f"""
            <div class="finsage-card" style="padding: 14px; text-align: center;">
                <div class="finsage-card-title">Consec. Losses</div>
                <div class="metric-value" style="color:{loss_color};">{st.session_state.consecutive_losses}</div>
                <div class="metric-subtext">Max Allowed: {MAX_CONSECUTIVE_LOSSES}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── TABBED NAVIGATION ──
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Live Risk Dashboard & Circuit Breakers",
        "🧮 Position Sizer (1% Cap & Kelly)",
        "🎯 Dynamic Exit Calculator",
        "📡 Multi-Timeframe Signal Scanner",
        "⚙️ CRO State Machine Controller",
    ])

    # =========================================================================
    # TAB 1: LIVE RISK DASHBOARD & CIRCUIT BREAKERS
    # =========================================================================
    with tab1:
        st.markdown("<h3 style='color:#22d3ee;'>Circuit Breaker Status & Risk Monitor</h3>", unsafe_allow_html=True)

        col_left, col_right = st.columns([1, 1])

        with col_left:
            st.markdown(
                f"""
                <div class="finsage-card">
                    <div class="finsage-card-header">
                        <span>⚡ Daily Drawdown Protection (Max 3%)</span>
                        <span style="color:{COLOR_MUTED}; font-size:12px;">24h Breaker</span>
                    </div>
                    <p style="font-size:13px; color:{COLOR_MUTED};">
                        If daily account equity falls by 3.0% or more, all active trades are closed, open orders cancelled, and the bot is put into a 24-hour cooling lock.
                    </p>
                """,
                unsafe_allow_html=True,
            )
            # Drawdown progress meter
            dd_pct_value = min(100.0, (cb_metrics["drawdown_pct"] / MAX_DAILY_DRAWDOWN_PCT) * 100.0)
            st.progress(int(dd_pct_value))
            st.write(f"**Current Peak Drawdown:** {cb_metrics['drawdown_pct']:.2f}% / {MAX_DAILY_DRAWDOWN_PCT:.1f}%")
            if cb_metrics["drawdown_breach"]:
                st.error("❌ BREACHED: Daily Drawdown Limit Exceeded!")
            else:
                st.success("✅ SAFE: Within Daily Drawdown Buffer")
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown(
                f"""
                <div class="finsage-card">
                    <div class="finsage-card-header">
                        <span>🛑 Consecutive Loss Counter (Max 4)</span>
                        <span style="color:{COLOR_MUTED}; font-size:12px;">Emergency Halt</span>
                    </div>
                    <p style="font-size:13px; color:{COLOR_MUTED};">
                        4 consecutive losses trigger an automatic trading halt to protect capital against adverse regime shifts.
                    </p>
                """,
                unsafe_allow_html=True,
            )
            loss_progress = min(100, int((st.session_state.consecutive_losses / MAX_CONSECUTIVE_LOSSES) * 100))
            st.progress(loss_progress)
            st.write(f"**Consecutive Losses:** {st.session_state.consecutive_losses} / {MAX_CONSECUTIVE_LOSSES}")
            if cb_metrics["losses_breach"]:
                st.error("❌ BREACHED: 4 Consecutive Losses Reached!")
            else:
                st.success("✅ SAFE: Consecutive Loss Counter Normal")
            st.markdown("</div>", unsafe_allow_html=True)

        with col_right:
            st.markdown(
                f"""
                <div class="finsage-card">
                    <div class="finsage-card-header">
                        <span>🚨 Emergency Kill Switch Control</span>
                    </div>
                    <p style="font-size:13px; color:{COLOR_MUTED};">
                        Manually trigger or reset the master emergency kill-switch. Resetting requires manual CRO clearance.
                    </p>
                """,
                unsafe_allow_html=True,
            )

            c_btn1, c_btn2 = st.columns(2)
            with c_btn1:
                if st.button("🔥 Trigger Emergency Kill Switch", use_container_width=True, type="primary"):
                    st.session_state.kill_switch_active = True
                    st.session_state.bot_state = STATE_KILL_SWITCH
                    st.session_state.kill_switch_timestamp = datetime.datetime.now()
                    st.rerun()

            with c_btn2:
                if st.button("🔄 Reset Circuit Breaker / Override", use_container_width=True):
                    st.session_state.kill_switch_active = False
                    st.session_state.consecutive_losses = 0
                    st.session_state.starting_daily_equity = st.session_state.equity
                    st.session_state.bot_state = STATE_IDLE
                    st.session_state.kill_switch_timestamp = None
                    st.success("Circuit breakers reset. State restored to IDLE.")
                    st.rerun()

            st.markdown("---")
            st.subheader("🧪 Trade Simulator (Test Circuit Breakers)")
            sim_col1, sim_col2 = st.columns(2)
            with sim_col1:
                if st.button("➕ Simulate Winning Trade (+$750)", use_container_width=True):
                    st.session_state.equity += 750.0
                    st.session_state.total_trades += 1
                    st.session_state.winning_trades += 1
                    st.session_state.consecutive_losses = 0
                    st.session_state.trade_history.insert(0, {
                        "id": f"TRD-{st.session_state.total_trades+100}",
                        "type": "LONG",
                        "pnl": 750.0,
                        "result": "WIN"
                    })
                    st.rerun()

            with sim_col2:
                if st.button("➖ Simulate Loss Trade (-$1,000)", use_container_width=True):
                    st.session_state.equity -= 1000.0
                    st.session_state.total_trades += 1
                    st.session_state.consecutive_losses += 1
                    st.session_state.trade_history.insert(0, {
                        "id": f"TRD-{st.session_state.total_trades+100}",
                        "type": "SHORT",
                        "pnl": -1000.0,
                        "result": "LOSS"
                    })
                    st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)

        # Trade History Table
        st.markdown("<h4 style='color:#7c6ff0;'>Recent Execution & Audit Log</h4>", unsafe_allow_html=True)
        if st.session_state.trade_history:
            df_trades = pd.DataFrame(st.session_state.trade_history)
            st.dataframe(df_trades, use_container_width=True, hide_index=True)

    # =========================================================================
    # TAB 2: POSITION SIZER CALCULATOR
    # =========================================================================
    with tab2:
        st.markdown("<h3 style='color:#22d3ee;'>Position Sizing Engine (1% Risk Cap & Kelly Criterion)</h3>", unsafe_allow_html=True)

        p_col1, p_col2 = st.columns([1, 1])

        with p_col1:
            st.markdown(
                f"""
                <div class="finsage-card">
                    <div class="finsage-card-header">
                        <span>⚙️ Position Sizing Parameters</span>
                    </div>
                """,
                unsafe_allow_html=True,
            )

            calc_equity = st.number_input("Account Equity ($)", min_value=100.0, value=float(st.session_state.equity), step=1000.0)
            calc_entry = st.number_input("Entry Price ($)", min_value=0.01, value=65000.0, step=100.0)
            calc_sl = st.number_input("Stop Loss Price ($)", min_value=0.01, value=64000.0, step=100.0)
            calc_risk_pct = st.slider("Target Risk per Trade (%)", min_value=0.1, max_value=5.0, value=1.0, step=0.1,
                                     help="Hard capped at 1.0% by CRO Risk policy")
            
            st.markdown("---")
            st.markdown("<strong>Kelly Criterion Inputs</strong>", unsafe_allow_html=True)
            calc_win_rate = st.slider("Historical Win Rate (%)", min_value=10.0, max_value=90.0, value=55.0, step=1.0)
            calc_rr_ratio = st.slider("Win/Loss Ratio (Avg Win / Avg Loss)", min_value=0.5, max_value=5.0, value=2.0, step=0.1)
            calc_kelly_fraction = st.select_slider("Kelly Fraction", options=[0.25, 0.50, 0.75, 1.00], value=0.50,
                                                   format_func=lambda x: f"{x*100:.0f}% Kelly")

            st.markdown("</div>", unsafe_allow_html=True)

        with p_col2:
            fixed_res = PositionSizer.calculate_fixed_fractional(
                equity=calc_equity,
                entry_price=calc_entry,
                stop_loss_price=calc_sl,
                risk_pct=calc_risk_pct,
            )

            kelly_res = PositionSizer.calculate_kelly(
                equity=calc_equity,
                entry_price=calc_entry,
                stop_loss_price=calc_sl,
                win_rate=calc_win_rate,
                win_loss_ratio=calc_rr_ratio,
                kelly_fraction=calc_kelly_fraction,
            )

            st.markdown(
                f"""
                <div class="finsage-card">
                    <div class="finsage-card-header">
                        <span>📊 Position Sizing Results</span>
                    </div>
                """,
                unsafe_allow_html=True,
            )

            if "error" in fixed_res:
                st.error(fixed_res["error"])
            else:
                r1, r2 = st.columns(2)
                with r1:
                    st.markdown("##### Fixed Fractional (1% Cap)")
                    st.metric("Risk Amount ($)", f"${fixed_res['risk_amount']:,.2f}")
                    st.metric("Position Size (Units)", f"{fixed_res['position_size_units']:.4f}")
                    st.metric("Position Value ($)", f"${fixed_res['position_value']:,.2f}")
                    st.metric("Effective Risk %", f"{fixed_res['effective_risk_pct']:.2f}%")
                    if fixed_res["risk_capped_warning"]:
                        st.warning("⚠️ Requested risk > 1% was automatically capped to 1.0% by CRO engine.")

                with r2:
                    st.markdown("##### Kelly Criterion")
                    st.metric("Full Kelly %", f"{kelly_res['full_kelly_pct']:.2f}%")
                    st.metric(f"Adjusted Kelly ({calc_kelly_fraction*100:.0f}%)", f"{kelly_res['adjusted_kelly_pct']:.2f}%")
                    st.metric("Recommended Risk %", f"{kelly_res['recommended_risk_pct']:.2f}%")
                    st.metric("Position Size (Units)", f"{kelly_res['position_size_units']:.4f}")
                    if not kelly_res["has_positive_edge"]:
                        st.error("🚫 Negative expectation! Kelly recommends 0 units (Do not trade).")

            st.markdown("</div>", unsafe_allow_html=True)

        # Plotly Comparison Chart
        if "error" not in fixed_res and "error" not in kelly_res:
            st.markdown("<h4 style='color:#7c6ff0;'>Position Size & Risk Comparison</h4>", unsafe_allow_html=True)
            
            fig_ps = go.Figure()
            fig_ps.add_trace(go.Bar(
                x=["Fixed Fractional (1% Cap)", "Full Kelly", f"Fractional Kelly ({calc_kelly_fraction*100:.0f}%)"],
                y=[fixed_res["risk_amount"], kelly_res["full_kelly_pct"] * calc_equity / 100.0, kelly_res["risk_amount"]],
                marker_color=[COLOR_CYAN, COLOR_VIOLET, COLOR_SUCCESS],
                text=[f"${fixed_res['risk_amount']:,.2f}", 
                      f"${(kelly_res['full_kelly_pct']*calc_equity/100.0):,.2f}", 
                      f"${kelly_res['risk_amount']:,.2f}"],
                textposition='auto'
            ))
            fig_ps.update_layout(
                title="Risk Capital Allocated ($)",
                paper_bgcolor=COLOR_CARD,
                plot_bgcolor=COLOR_CARD,
                font=dict(color=COLOR_TEXT),
                height=300,
                margin=dict(l=20, r=20, t=40, b=20),
            )
            st.plotly_chart(fig_ps, use_container_width=True)

    # =========================================================================
    # TAB 3: DYNAMIC EXIT CALCULATOR
    # =========================================================================
    with tab3:
        st.markdown("<h3 style='color:#22d3ee;'>Dynamic Exit Engine (ATR Stop, Take Profit & Trailing Stop)</h3>", unsafe_allow_html=True)

        e_col1, e_col2 = st.columns([1, 1])

        with e_col1:
            st.markdown(
                f"""
                <div class="finsage-card">
                    <div class="finsage-card-header">
                        <span>⚙️ Dynamic Exit Parameters</span>
                    </div>
                """,
                unsafe_allow_html=True,
            )

            exit_entry = st.number_input("Trade Entry Price ($)", min_value=0.01, value=65000.0, step=100.0, key="e_entry")
            exit_atr = st.number_input("Current ATR (14-period)", min_value=0.01, value=850.0, step=10.0, key="e_atr")
            exit_dir = st.radio("Position Direction", options=["LONG", "SHORT"], horizontal=True, key="e_dir")
            exit_rr = st.slider("Target Risk-to-Reward Ratio (Min 1:2)", min_value=2.0, max_value=5.0, value=2.0, step=0.1, key="e_rr")
            exit_current_price = st.number_input("Live Market Price ($)", min_value=0.01, value=66200.0, step=100.0, key="e_cp")

            st.markdown("</div>", unsafe_allow_html=True)

        with e_col2:
            exit_res = DynamicExitEngine.calculate_exits(
                entry_price=exit_entry,
                atr=exit_atr,
                direction=exit_dir,
                rr_ratio=exit_rr,
                current_price=exit_current_price,
            )

            st.markdown(
                f"""
                <div class="finsage-card">
                    <div class="finsage-card-header">
                        <span>🎯 Calculated Exit Thresholds</span>
                    </div>
                """,
                unsafe_allow_html=True,
            )

            e_m1, e_m2 = st.columns(2)
            with e_m1:
                st.metric("Hard Stop Loss (1.5x ATR)", f"${exit_res['hard_stop_loss']:,.2f}")
                st.metric("Take Profit (1:{:.1f} R:R)".format(exit_res['rr_ratio']), f"${exit_res['take_profit']:,.2f}")
                st.metric("1:1 R:R Trailing Activation", f"${exit_res['trailing_activation_price']:,.2f}")

            with e_m2:
                st.metric("Effective Stop Loss", f"${exit_res['effective_stop_loss']:,.2f}")
                st.metric("Trailing Stop Status", "ACTIVE" if exit_res["is_trailing_active"] else "INACTIVE")
                st.metric("Locked Profit / Unit", f"${exit_res['locked_profit_per_unit']:,.2f}")

            if exit_res["is_trailing_active"]:
                st.success(f"🔒 Trailing stop activated! 50% of peak profit locked at ${exit_res['effective_stop_loss']:,.2f}.")
            else:
                st.info("ℹ️ Trailing stop pending. Activates when price reaches 1:1 R:R profit.")

            st.markdown("</div>", unsafe_allow_html=True)

        # Plotly Ladder Visualizer
        st.markdown("<h4 style='color:#7c6ff0;'>Price Ladder & Exit Zones</h4>", unsafe_allow_html=True)
        fig_ladder = go.Figure()

        fig_ladder.add_trace(go.Scatter(
            x=["Hard SL", "Effective SL", "Entry", "1:1 Activation", "Take Profit", "Live Price"],
            y=[
                exit_res["hard_stop_loss"],
                exit_res["effective_stop_loss"],
                exit_res["entry_price"],
                exit_res["trailing_activation_price"],
                exit_res["take_profit"],
                exit_res["current_price"],
            ],
            mode="lines+markers+text",
            text=[
                f"${exit_res['hard_stop_loss']:,.2f}",
                f"${exit_res['effective_stop_loss']:,.2f}",
                f"${exit_res['entry_price']:,.2f}",
                f"${exit_res['trailing_activation_price']:,.2f}",
                f"${exit_res['take_profit']:,.2f}",
                f"${exit_res['current_price']:,.2f}",
            ],
            textposition="top center",
            marker=dict(size=12, color=[COLOR_DANGER, COLOR_WARNING, COLOR_CYAN, COLOR_VIOLET, COLOR_SUCCESS, "#ffffff"]),
            line=dict(color=COLOR_MUTED, dash="dash"),
        ))

        fig_ladder.update_layout(
            title=f"{exit_dir} Trade Price Levels — Entry: ${exit_entry:,.2f} | ATR: ${exit_atr:,.2f}",
            paper_bgcolor=COLOR_CARD,
            plot_bgcolor=COLOR_CARD,
            font=dict(color=COLOR_TEXT),
            height=350,
            margin=dict(l=20, r=20, t=40, b=20),
        )
        st.plotly_chart(fig_ladder, use_container_width=True)

    # =========================================================================
    # TAB 4: MULTI-TIMEFRAME SIGNAL SCANNER
    # =========================================================================
    with tab4:
        st.markdown("<h3 style='color:#22d3ee;'>Multi-Timeframe Entry Trigger Scanner (4H + 15M)</h3>", unsafe_allow_html=True)

        scan_symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "NIFTY50", "BANKNIFTY"]

        sc_col1, sc_col2 = st.columns([1, 3])

        with sc_col1:
            st.markdown(
                f"""
                <div class="finsage-card">
                    <div class="finsage-card-header">
                        <span>🔍 Scanner Controls</span>
                    </div>
                """,
                unsafe_allow_html=True,
            )

            selected_symbol = st.selectbox("Select Asset to Inspect", options=scan_symbols, index=0)
            force_sim_signal = st.radio("Simulate Scanner State", options=["Random Market", "Force LONG", "Force SHORT"], index=0)

            force_param = None
            if force_sim_signal == "Force LONG":
                force_param = "LONG"
            elif force_sim_signal == "Force SHORT":
                force_param = "SHORT"

            run_scan = st.button("🚀 Run Live MTF Scan", use_container_width=True, type="primary")

            st.markdown("---")
            st.markdown(
                """
                <strong>Strategy Rules (All 4 must match):</strong><br/>
                1. <strong>4H Trend:</strong> Price vs 200 EMA<br/>
                2. <strong>15M BB:</strong> Touches Upper/Lower Bollinger Band<br/>
                3. <strong>15M RSI:</strong> Extreme (<30 / >70) + Divergence<br/>
                4. <strong>15M MACD:</strong> Histogram sign (Green / Red)
                """,
                unsafe_allow_html=True,
            )

            st.markdown("</div>", unsafe_allow_html=True)

        with sc_col2:
            st.markdown(
                f"""
                <div class="finsage-card">
                    <div class="finsage-card-header">
                        <span>📡 Live Asset Matrix Scan Results</span>
                    </div>
                """,
                unsafe_allow_html=True,
            )

            scan_results = []
            for sym in scan_symbols:
                sym_force = force_param if sym == selected_symbol else None
                df_4h, df_15m = SignalScanner.generate_mock_market_data(sym, force_signal=sym_force)
                res = SignalScanner.scan_asset(sym, df_4h, df_15m)
                scan_results.append(res)

            matrix_rows = []
            for r in scan_results:
                long_score = r["long_criteria"]["score"]
                short_score = r["short_criteria"]["score"]
                sig = r["signal"]

                matrix_rows.append({
                    "Asset": r["symbol"],
                    "15M Price": f"${r['price_15m']:,.2f}",
                    "4H 200 EMA": f"${r['ema_200_4h']:,.2f}",
                    "15M RSI": f"{r['rsi_15m']:.1f}",
                    "MACD Hist": f"{r['macd_hist_15m']:+.2f}",
                    "Long Match": long_score,
                    "Short Match": short_score,
                    "Signal": sig,
                })

            df_matrix = pd.DataFrame(matrix_rows)
            st.dataframe(df_matrix, use_container_width=True, hide_index=True)

            st.markdown("</div>", unsafe_allow_html=True)

        # Detailed Asset Technical Breakdown
        active_res = next((r for r in scan_results if r["symbol"] == selected_symbol), scan_results[0])
        
        st.markdown(f"<h4 style='color:#7c6ff0;'>Deep Inspection: {selected_symbol} Technical Criteria</h4>", unsafe_allow_html=True)
        
        c_long_col, c_short_col = st.columns(2)
        with c_long_col:
            st.markdown(
                f"""
                <div class="finsage-card">
                    <div class="finsage-card-header">
                        <span>🟢 LONG Signal Checklist ({active_res['long_criteria']['score']})</span>
                    </div>
                    <ul>
                        <li>4H Price > 200 EMA: <strong class="{'match-pass' if active_res['long_criteria']['4H_above_200EMA'] else 'match-fail'}">{active_res['long_criteria']['4H_above_200EMA']}</strong></li>
                        <li>15M Price <= Lower BB: <strong class="{'match-pass' if active_res['long_criteria']['15M_touch_lower_BB'] else 'match-fail'}">{active_res['long_criteria']['15M_touch_lower_BB']}</strong></li>
                        <li>15M RSI < 30 / Bull Div: <strong class="{'match-pass' if active_res['long_criteria']['15M_RSI_low_div'] else 'match-fail'}">{active_res['long_criteria']['15M_RSI_low_div']}</strong></li>
                        <li>15M MACD Hist > 0: <strong class="{'match-pass' if active_res['long_criteria']['15M_MACD_green'] else 'match-fail'}">{active_res['long_criteria']['15M_MACD_green']}</strong></li>
                    </ul>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with c_short_col:
            st.markdown(
                f"""
                <div class="finsage-card">
                    <div class="finsage-card-header">
                        <span>🔴 SHORT Signal Checklist ({active_res['short_criteria']['score']})</span>
                    </div>
                    <ul>
                        <li>4H Price < 200 EMA: <strong class="{'match-pass' if active_res['short_criteria']['4H_below_200EMA'] else 'match-fail'}">{active_res['short_criteria']['4H_below_200EMA']}</strong></li>
                        <li>15M Price >= Upper BB: <strong class="{'match-pass' if active_res['short_criteria']['15M_touch_upper_BB'] else 'match-fail'}">{active_res['short_criteria']['15M_touch_upper_BB']}</strong></li>
                        <li>15M RSI > 70 / Bear Div: <strong class="{'match-pass' if active_res['short_criteria']['15M_RSI_high_div'] else 'match-fail'}">{active_res['short_criteria']['15M_RSI_high_div']}</strong></li>
                        <li>15M MACD Hist < 0: <strong class="{'match-pass' if active_res['short_criteria']['15M_MACD_red'] else 'match-fail'}">{active_res['short_criteria']['15M_MACD_red']}</strong></li>
                    </ul>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Plotly Candlestick Chart for 15M Data
        df_chart_15m = active_res["df_15m"].tail(60)
        fig_candle = go.Figure()
        fig_candle.add_trace(go.Candlestick(
            x=df_chart_15m['timestamp'],
            open=df_chart_15m['open'],
            high=df_chart_15m['high'],
            low=df_chart_15m['low'],
            close=df_chart_15m['close'],
            name="15M Price"
        ))
        fig_candle.add_trace(go.Scatter(x=df_chart_15m['timestamp'], y=df_chart_15m['upper_bb'], line=dict(color=COLOR_CYAN, width=1), name="Upper BB"))
        fig_candle.add_trace(go.Scatter(x=df_chart_15m['timestamp'], y=df_chart_15m['mid_bb'], line=dict(color=COLOR_MUTED, width=1, dash='dot'), name="Mid BB"))
        fig_candle.add_trace(go.Scatter(x=df_chart_15m['timestamp'], y=df_chart_15m['lower_bb'], line=dict(color=COLOR_VIOLET, width=1), name="Lower BB"))

        fig_candle.update_layout(
            title=f"{selected_symbol} — 15M Chart with Bollinger Bands",
            paper_bgcolor=COLOR_CARD,
            plot_bgcolor=COLOR_CARD,
            font=dict(color=COLOR_TEXT),
            height=400,
            xaxis_rangeslider_visible=False,
            margin=dict(l=20, r=20, t=40, b=20),
        )
        st.plotly_chart(fig_candle, use_container_width=True)

    # =========================================================================
    # TAB 5: CRO STATE MACHINE CONTROLLER
    # =========================================================================
    with tab5:
        st.markdown("<h3 style='color:#22d3ee;'>CRO Bot State Machine & Execution Flow</h3>", unsafe_allow_html=True)

        st.markdown(
            f"""
            <div class="finsage-card">
                <div class="finsage-card-header">
                    <span>🔄 Finite State Machine Graph</span>
                </div>
                <p style="color:{COLOR_MUTED}; font-size:13px;">
                    State Flow: <strong>IDLE</strong> ➔ <strong>SCANNING</strong> ➔ <strong>ENTRY_PENDING</strong> ➔ <strong>POSITION_ACTIVE</strong> ➔ <strong>CLOSED</strong> (or <strong>KILL_SWITCH</strong> on circuit breach).
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        sm = RiskStateMachine(current_state=st.session_state.bot_state)

        st.write(f"**Current Machine State:** `{sm.state}`")

        s_col1, s_col2, s_col3, s_col4, s_col5 = st.columns(5)

        with s_col1:
            if st.button("Set IDLE", use_container_width=True):
                ok, msg = sm.transition_to(STATE_IDLE)
                if ok:
                    st.session_state.bot_state = STATE_IDLE
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

        with s_col2:
            if st.button("Set SCANNING", use_container_width=True):
                ok, msg = sm.transition_to(STATE_SCANNING)
                if ok:
                    st.session_state.bot_state = STATE_SCANNING
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

        with s_col3:
            if st.button("Set ENTRY_PENDING", use_container_width=True):
                ok, msg = sm.transition_to(STATE_ENTRY_PENDING)
                if ok:
                    st.session_state.bot_state = STATE_ENTRY_PENDING
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

        with s_col4:
            if st.button("Set POSITION_ACTIVE", use_container_width=True):
                ok, msg = sm.transition_to(STATE_POSITION_ACTIVE)
                if ok:
                    st.session_state.bot_state = STATE_POSITION_ACTIVE
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

        with s_col5:
            if st.button("Set CLOSED", use_container_width=True):
                ok, msg = sm.transition_to(STATE_CLOSED)
                if ok:
                    st.session_state.bot_state = STATE_CLOSED
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)


# Standalone runner for testing
if __name__ == "__main__":
    st.set_page_config(page_title="FinsageAI Risk Engine", layout="wide")
    render_risk_engine_page()
