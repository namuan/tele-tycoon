"""Database base configuration for TeleTycoon."""

from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# Default database path
DEFAULT_DB_PATH = Path(__file__).parent.parent.parent / "data" / "teletycoon.db"


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""


def get_engine(db_path: Path | str | None = None):
    """Create a database engine.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        SQLAlchemy engine.
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    # Ensure directory exists
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    return create_engine(f"sqlite:///{db_path}", echo=False)


def get_session(
    db_path: Path | str | None = None,
) -> Generator[Session, None, None]:
    """Get a database session.

    Args:
        db_path: Path to the SQLite database file.

    Yields:
        Database session.
    """
    engine = get_engine(db_path)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

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
