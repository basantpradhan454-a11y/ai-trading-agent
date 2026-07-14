"""
FinsageAI — Strategy Backtesting Engine
Vectorized: RSI, MACD, EMA Crossover, Bollinger, Combined.
"""
import pandas as pd
import numpy as np
import plotly.graph_objects as go


class BacktestEngine:
    def __init__(self, df, initial_capital=1_000_000.0, transaction_cost_pct=0.0005):
        self.df = df.copy()
        self.initial_capital = initial_capital
        self.tc = transaction_cost_pct

    def _rsi(self, period=14):
        d = self.df["Close"].diff()
        g = d.where(d > 0, 0.0).rolling(period).mean()
        l = (-d.where(d < 0, 0.0)).rolling(period).mean()
        return 100 - (100 / (1 + g / (l + 1e-9)))

    def _macd(self, fast=12, slow=26, signal=9):
        ef = self.df["Close"].ewm(span=fast, adjust=False).mean()
        es = self.df["Close"].ewm(span=slow, adjust=False).mean()
        m = ef - es
        s = m.ewm(span=signal, adjust=False).mean()
        return m, s, m - s

    def _ema(self, span):
        return self.df["Close"].ewm(span=span, adjust=False).mean()

    def _bollinger(self, period=20, std=2):
        sma = self.df["Close"].rolling(period).mean()
        sd = self.df["Close"].rolling(period).std()
        return sma + std * sd, sma, sma - std * sd

    def compile_signals(self, strategy, params):
        sig = pd.Series(0, index=self.df.index, dtype=int)
        if strategy == "RSI_Oversold":
            rsi = self._rsi(params.get("rsi_period", 14))
            sig[rsi < params.get("oversold", 30)] = 1
            sig[rsi > params.get("overbought", 70)] = -1
        elif strategy == "MACD_Crossover":
            m, s, _ = self._macd(params.get("macd_fast",12), params.get("macd_slow",26), params.get("macd_signal",9))
            sig[(m > s) & (m.shift(1) <= s.shift(1))] = 1
            sig[(m < s) & (m.shift(1) >= s.shift(1))] = -1
        elif strategy == "EMA_Crossover":
            f = self._ema(params.get("ema_fast", 9))
            sl = self._ema(params.get("ema_slow", 21))
            sig[(f > sl) & (f.shift(1) <= sl.shift(1))] = 1
            sig[(f < sl) & (f.shift(1) >= sl.shift(1))] = -1
        elif strategy == "Bollinger_Bounce":
            u, _, lo = self._bollinger(params.get("bb_period",20), params.get("bb_std",2))
            sig[self.df["Close"] <= lo] = 1
            sig[self.df["Close"] >= u] = -1
        elif strategy == "Combined_RSI_MACD":
            rsi = self._rsi(params.get("rsi_period", 14))
            m, s, _ = self._macd()
            sig[(rsi < params.get("oversold",35)) & (m > s) & (m.shift(1) <= s.shift(1))] = 1
            sig[(rsi > params.get("overbought",65)) & (m < s) & (m.shift(1) >= s.shift(1))] = -1
        return sig

    def run(self, signals):
        df = self.df.copy()
        df["Signal"] = signals
        capital = self.initial_capital; position = 0.0; state = 0
        log = []; equity = []
        for i in range(len(df)):
            price = float(df["Close"].iloc[i]); date = df.index[i]; s = df["Signal"].iloc[i]
            if s == 1 and state == 0:
                cost = capital * self.tc
                position = (capital - cost) / price; capital = 0.0; state = 1
                log.append({"Date": date, "Action": "BUY", "Price": round(price,2), "Units": round(position,4), "Brokerage": round(cost,2)})
            elif s == -1 and state == 1:
                proceeds = position * price; cost = proceeds * self.tc; capital = proceeds - cost
                log.append({"Date": date, "Action": "SELL", "Price": round(price,2), "Units": round(position,4), "Brokerage": round(cost,2)})
                position = 0.0; state = 0
            equity.append(capital + position * price)
        df["Equity"] = equity
        df["Benchmark"] = (df["Close"] / df["Close"].iloc[0]) * self.initial_capital
        trade_df = pd.DataFrame(log)
        metrics = self._metrics(df, log)
        return trade_df, metrics, df

    def _metrics(self, df, log):
        eq = df["Equity"]
        tr = (eq.iloc[-1] - self.initial_capital) / self.initial_capital * 100
        br = (df["Benchmark"].iloc[-1] - self.initial_capital) / self.initial_capital * 100
        dd = ((eq - eq.cummax()) / eq.cummax()).min() * 100
        dr = eq.pct_change().dropna()
        sharpe = (dr.mean() / (dr.std() + 1e-9)) * (252**0.5) if len(dr) > 1 else 0
        wins = sum(1 for i in range(1, len(log), 2) if i < len(log) and log[i]["Price"] > log[i-1]["Price"])
        total = len(log) // 2
        return {"Total Return (%)": round(tr,2), "Benchmark Return (%)": round(br,2),
                "Max Drawdown (%)": round(dd,2), "Sharpe Ratio": round(sharpe,2),
                "Win Rate (%)": round(wins/total*100 if total else 0, 2), "Total Trades": total,
                "Alpha (%)": round(tr-br,2), "Final Capital (Rs)": round(eq.iloc[-1],2)}

    def build_equity_chart(self, df, trade_df):
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df["Equity"], name="Strategy", line=dict(color="#00d4ff", width=2.5)))
        fig.add_trace(go.Scatter(x=df.index, y=df["Benchmark"], name="Buy & Hold", line=dict(color="#7c3aed", dash="dash", width=1.5)))
        if not trade_df.empty:
            buys = trade_df[trade_df["Action"]=="BUY"]
            sells = trade_df[trade_df["Action"]=="SELL"]
            if not buys.empty:
                buy_dates = buys["Date"].tolist()
                buy_eq = [float(df.loc[d,"Equity"]) if d in df.index else None for d in buy_dates]
                fig.add_trace(go.Scatter(x=buy_dates, y=buy_eq, mode="markers",
                    marker=dict(symbol="triangle-up", size=12, color="#00ff88"), name="Buy"))
            if not sells.empty:
                sell_dates = sells["Date"].tolist()
                sell_eq = [float(df.loc[d,"Equity"]) if d in df.index else None for d in sell_dates]
                fig.add_trace(go.Scatter(x=sell_dates, y=sell_eq, mode="markers",
                    marker=dict(symbol="triangle-down", size=12, color="#ff4444"), name="Sell"))
        fig.update_layout(title="📈 Equity Curve vs Buy & Hold", template="plotly_dark",
                          paper_bgcolor="#0c1222", plot_bgcolor="#0c1222", height=450,
                          xaxis_title="Date", yaxis_title="Portfolio Value (₹)",
                          font=dict(color="#c8d6e8"))
        return fig
