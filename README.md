# FinsageAI (demo-first)

An execution-tool-style trading dashboard: live market data via CCXT, RSI/EMA/volume
signal generation, a **non-negotiable risk validation layer** (position size ≤5%,
SL ≤2%, R:R ≥1:2, daily-loss global shutdown), a 200-strategy backtest engine,
lightweight news sentiment + quant metrics, and encrypted per-user API key storage.

Runs in **demo/paper mode by default** — live order execution with real funds is an
explicit opt-in per user (see Settings tab) and is intentionally not wired to
`ccxt.create_order` in this build; that's the next phase once the demo engine has
been proven out. Not financial advice — this is an execution/validation tool only.

## Project layout

```
trading_agent/
├── app.py                     # Streamlit UI (Dashboard / Backtest / News+Quant / Settings)
├── worker.py                  # standalone script for 24/7 demo trading via cron
├── core/
│   ├── risk_validator.py      # hard-coded risk limits — AI output never bypasses this
│   ├── security.py            # Fernet encryption for API keys (never plaintext)
│   ├── db.py                  # SQLAlchemy models (SQLite by default, Postgres via DATABASE_URL)
│   ├── data_feed.py            # CCXT public market data (kraken by default)
│   ├── indicators.py          # RSI / EMA / volume-spike
│   ├── strategy.py            # Aggressive/Balanced/Conservative signal generation
│   ├── backtest_engine.py     # 200-strategy grid-search backtester
│   ├── news_quant.py          # Google News RSS sentiment + volatility/Sharpe/drawdown
│   └── demo_engine.py         # one full "AI trading cycle" (signal → validate → paper trade)
├── .github/workflows/demo_trader.yml   # cron: runs worker.py every 15 min for true 24/7
├── requirements.txt
└── .streamlit/config.toml, secrets.toml.example
```

## Run locally

```bash
pip install -r requirements.txt
export ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
streamlit run app.py
```

## Deploy — GitHub + Streamlit Community Cloud

Streamlit Cloud deploys directly from a GitHub repo, so:

1. **Create a GitHub repo** (e.g. `ai-trading-agent`) and push this folder's contents to it.
2. Go to **share.streamlit.io** → "New app" → pick your repo/branch → main file path `app.py`.
3. In the app's **Settings → Secrets**, paste:
   ```toml
   ENCRYPTION_KEY = "<your generated key>"
   # optional, for persistence + shared state with the GitHub Actions worker:
   # DATABASE_URL = "postgresql://..."
   ```
4. Deploy. First boot takes ~1-2 min while dependencies install.

### For real 24/7 demo trading (not just while the tab is open)
Streamlit Cloud only computes while the app is being viewed/pinged, so for genuine
around-the-clock demo trading:
- Use a free hosted Postgres (Neon or Supabase free tier) and set `DATABASE_URL` as a
  secret **both** in Streamlit Cloud and as a GitHub Actions repo secret.
- The included `.github/workflows/demo_trader.yml` runs `worker.py` every 15 minutes
  via GitHub Actions cron, writing trades/account state to that same Postgres DB —
  the dashboard just reads and displays it.

## Security notes
- API keys/secrets are encrypted with Fernet before hitting the database — the
  `api_key_enc` / `api_secret_enc` columns never hold plaintext.
- `ENCRYPTION_KEY` must be set as an environment variable / secret, never committed.
- Live trading is OFF by default per user; enabling it is an explicit checkbox in Settings.
- The AI's JSON signal is **always** re-validated in `core/risk_validator.py` against
  hard-coded limits before anything could reach an exchange — it is never trusted directly.

## Next phase (live execution)
When you're ready to wire real order placement:
1. Decrypt the user's key/secret only inside the backend process (never in the browser).
2. Call `ccxt.<exchange>.create_order(...)` only when `validate_trade(...).is_valid == True`
   **and** the user has the live-trading checkbox enabled.
3. Log every order attempt (approved or rejected) for audit.
