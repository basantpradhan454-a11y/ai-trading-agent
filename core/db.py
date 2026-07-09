"""
Persistence layer. Defaults to a local SQLite file so the app runs with
zero config, but set DATABASE_URL (e.g. a free Neon/Supabase Postgres
connection string) to persist state across restarts / share it with the
GitHub Actions worker for true 24/7 demo trading.

API key/secret columns always hold ENCRYPTED text (see core/security.py) —
never plaintext.
"""
import os
import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///trading_agent.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class ApiKeyRecord(Base):
    __tablename__ = "api_keys"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, default="default_user")
    exchange = Column(String, default="binance")
    api_key_enc = Column(Text)      # ENCRYPTED
    api_secret_enc = Column(Text)   # ENCRYPTED
    live_trading_enabled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Trade(Base):
    __tablename__ = "trades"
    id = Column(Integer, primary_key=True)
    symbol = Column(String)
    action = Column(String)
    entry_price = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    position_size_pct = Column(Float)
    trade_value = Column(Float)
    strategy = Column(String)
    status = Column(String, default="open")  # open, closed_tp, closed_sl, closed_manual
    exit_price = Column(Float, nullable=True)
    pnl_pct = Column(Float, nullable=True)
    reason = Column(Text)
    mode = Column(String, default="demo")  # demo or live
    opened_at = Column(DateTime, default=datetime.datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)


class BacktestRun(Base):
    __tablename__ = "backtest_runs"
    id = Column(Integer, primary_key=True)
    symbol = Column(String)
    timeframe = Column(String)
    strategies_tested = Column(Integer)
    report_json = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class AccountLog(Base):
    __tablename__ = "account_log"
    id = Column(Integer, primary_key=True)
    balance = Column(Float, default=10000.0)
    daily_pnl_pct = Column(Float, default=0.0)
    is_shutdown = Column(Boolean, default=False)
    shutdown_until = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)


def init_db():
    Base.metadata.create_all(engine)


def get_session():
    return SessionLocal()
