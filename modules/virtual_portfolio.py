"""FinsageAI — Virtual Paper Trading Portfolio Manager"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

INITIAL_CAPITAL = 1_000_000.0

def init_portfolio():
    if "finsage_portfolio" not in st.session_state:
        st.session_state["finsage_portfolio"] = {
            "cash": INITIAL_CAPITAL,
            "positions": {},
            "history": [],
        }

def get_portfolio():
    init_portfolio()
    return st.session_state["finsage_portfolio"]

def add_position(ticker, qty, price):
    p = get_portfolio()
    cost = qty * price
    if cost > p["cash"]:
        return False, f"Insufficient cash. Need ₹{cost:,.2f}, have ₹{p['cash']:,.2f}"
    p["cash"] -= cost
    if ticker in p["positions"]:
        old = p["positions"][ticker]
        total_qty = old["qty"] + qty
        total_cost = old["avg_cost"] * old["qty"] + price * qty
        p["positions"][ticker] = {"qty": total_qty, "avg_cost": total_cost / total_qty,
                                   "total_invested": old["total_invested"] + cost}
    else:
        p["positions"][ticker] = {"qty": qty, "avg_cost": price, "total_invested": cost}
    p["history"].append({"Date": datetime.now().strftime("%Y-%m-%d %H:%M"), "Ticker": ticker,
                         "Action": "BUY", "Qty": qty, "Price": price, "Amount": round(cost,2)})
    return True, f"Bought {qty} units of {ticker} @ ₹{price:,.2f}"

def close_position(ticker, qty, price):
    p = get_portfolio()
    if ticker not in p["positions"]:
        return False, f"No position in {ticker}"
    pos = p["positions"][ticker]
    if qty > pos["qty"]:
        return False, f"You only hold {pos['qty']} units of {ticker}"
    proceeds = qty * price
    p["cash"] += proceeds
    avg_cost = pos["avg_cost"]
    pnl = (price - avg_cost) * qty
    pos["qty"] -= qty
    pos["total_invested"] -= avg_cost * qty
    if pos["qty"] <= 0.0001:
        del p["positions"][ticker]
    p["history"].append({"Date": datetime.now().strftime("%Y-%m-%d %H:%M"), "Ticker": ticker,
                         "Action": "SELL", "Qty": qty, "Price": price,
                         "Amount": round(proceeds,2), "Realized P&L": round(pnl,2)})
    return True, f"Sold {qty} units of {ticker} @ ₹{price:,.2f} | P&L: ₹{pnl:+,.2f}"

def get_pnl_summary(prices):
    p = get_portfolio()
    rows = []
    for ticker, pos in p["positions"].items():
        curr = prices.get(ticker, pos["avg_cost"])
        val = pos["qty"] * curr
        pnl = val - pos["total_invested"]
        pnl_pct = (pnl / pos["total_invested"] * 100) if pos["total_invested"] else 0
        rows.append({"Ticker": ticker, "Qty": pos["qty"], "Avg Cost (₹)": round(pos["avg_cost"],2),
                     "Current Price (₹)": round(curr,2), "Invested (₹)": round(pos["total_invested"],2),
                     "Current Value (₹)": round(val,2), "P&L (₹)": round(pnl,2), "P&L (%)": round(pnl_pct,2)})
    return pd.DataFrame(rows)

def get_total_value(prices):
    p = get_portfolio()
    invested_val = sum(pos["qty"] * prices.get(t, pos["avg_cost"]) for t, pos in p["positions"].items())
    return p["cash"] + invested_val

def get_allocation_chart(prices):
    p = get_portfolio()
    labels, values = ["Cash"], [p["cash"]]
    for t, pos in p["positions"].items():
        labels.append(t)
        values.append(pos["qty"] * prices.get(t, pos["avg_cost"]))
    fig = go.Figure(go.Pie(labels=labels, values=values, hole=0.45,
                            marker=dict(colors=["#4a9eff","#00d4ff","#7c3aed","#ffaa00","#ff6b6b","#00ff88"])))
    fig.update_layout(title="Portfolio Allocation", template="plotly_dark",
                      paper_bgcolor="#0c1222", height=350, font=dict(color="#c8d6e8"))
    return fig

def get_transaction_history():
    return pd.DataFrame(get_portfolio()["history"])
