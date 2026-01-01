"""Database base configuration for TeleTycoon."""

import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# Default database path
DEFAULT_DB_PATH = Path(__file__).parent.parent.parent / "data" / "teletycoon.db"

_ENGINE_CACHE: dict[str, Engine] = {}
_SESSIONMAKER_CACHE: dict[str, sessionmaker] = {}


def get_db_path() -> Path:
    """Get database path from environment or use default.

    Returns:
        Path to database file.
    """
    db_path_str = os.getenv("DATABASE_PATH")
    if db_path_str:
        return Path(db_path_str)
    return DEFAULT_DB_PATH


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""


def get_engine(db_path: Path | str | None = None):
    """Create a database engine.

    Args:
        db_path: Path to the SQLite database file. If None, uses DATABASE_PATH from env or default.

    Returns:
        SQLAlchemy engine.
    """
    if db_path is None:
        db_path = get_db_path()

    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    cache_key = str(db_path.resolve())

    engine = _ENGINE_CACHE.get(cache_key)
    if engine:
        return engine

    t0 = time.perf_counter()
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    _ENGINE_CACHE[cache_key] = engine

    elapsed_ms = (time.perf_counter() - t0) * 1000
    if elapsed_ms > 250:
        import logging

        logging.getLogger(__name__).info(
            f"Database engine creation took {elapsed_ms:.0f}ms for {db_path}"
        )

    return engine


@contextmanager
def get_session(db_path: Path | str | None = None) -> Iterator[Session]:
    """Get a database session.

    Args:
        db_path: Path to the SQLite database file.

    Yields:
        Database session.
    """
    engine = get_engine(db_path)
    cache_key = str(Path(get_db_path() if db_path is None else db_path).resolve())
    SessionLocal = _SESSIONMAKER_CACHE.get(cache_key)
    if SessionLocal is None:
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        _SESSIONMAKER_CACHE[cache_key] = SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def init_db(db_path: Path | str | None = None) -> None:
    """Initialize the database, creating all tables.

    Args:
        db_path: Path to the SQLite database file.
    """
    engine = get_engine(db_path)
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(text("DROP INDEX IF EXISTS ix_game_log_game_id"))
