
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base
import os

# Default to sqlite file in data/, override via env DB_URL
DB_URL = os.environ.get("DB_URL", "sqlite:///./data/ledger.db")
# Use connect_args for SQLite to allow multithreading in simple dev setups
connect_args = {"check_same_thread": False} if DB_URL.startswith("sqlite") else {}

engine = create_engine(DB_URL, echo=False, future=True, connect_args=connect_args)
SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False, autocommit=False))
Base = declarative_base()

def init_db():
    # Import models here so they are registered on Base
    import ledger.db.models as _models  # noqa: F401
    Base.metadata.create_all(bind=engine)
