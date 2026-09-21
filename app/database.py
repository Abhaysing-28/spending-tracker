"""
Database engine + session setup.

Uses SQLite by default (file-based, zero infra). The DB URL is overridable
via the SPEND_TRACKER_DB_URL env var so tests can point at an in-memory DB
instead of touching the real dev database file.
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.environ.get("SPEND_TRACKER_DB_URL", "sqlite:///./spend_tracker.db")

# check_same_thread=False is needed because SQLite by default only allows
# the thread that created a connection to use it, but FastAPI can handle
# requests on different threads. This is safe here because each request
# gets its own session (see get_db below).
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency: yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
