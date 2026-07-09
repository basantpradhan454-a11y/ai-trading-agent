"""
Standalone worker for TRUE 24/7 demo trading, meant to be run on a schedule
by GitHub Actions (see .github/workflows/demo_trader.yml) — independent of
whether anyone has the Streamlit dashboard open.

Requires DATABASE_URL to point at a shared hosted Postgres (e.g. free-tier
Neon/Supabase) so the worker and the deployed Streamlit app read/write the
same account & trade history. With plain SQLite the worker's local file
would NOT be visible to the deployed app.

Usage: python worker.py --symbols BTC/USDT ETH/USDT --strategy Balanced
"""
import argparse
from core.demo_engine import run_cycle


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", nargs="+", default=["BTC/USDT"])
    parser.add_argument("--strategy", default="Balanced", choices=["Aggressive", "Balanced", "Conservative"])
    parser.add_argument("--timeframe", default="1h")
    args = parser.parse_args()

    for symbol in args.symbols:
        result = run_cycle(symbol=symbol, strategy=args.strategy, timeframe=args.timeframe)
        print(f"=== {symbol} ===")
        print(result["log"] or "No action this cycle.")
        print()


if __name__ == "__main__":
    main()
