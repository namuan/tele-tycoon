"""SQLAlchemy models for database persistence."""

import json
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class PlayerModel(Base):
    """Database model for players."""

    __tablename__ = "players"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    telegram_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    player_type: Mapped[str] = mapped_column(String(32))  # human, rule_based_ai, llm
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    game_players: Mapped[list["GamePlayerModel"]] = relationship(
        back_populates="player"
    )


class GameModel(Base):
    """Database model for games."""

    __tablename__ = "games"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(32))  # setup, active, completed
    current_phase: Mapped[str] = mapped_column(String(32))
    round_type: Mapped[str] = mapped_column(String(32))
    stock_round_number: Mapped[int] = mapped_column(Integer, default=1)
    operating_round_number: Mapped[int] = mapped_column(Integer, default=0)
    current_player_index: Mapped[int] = mapped_column(Integer, default=0)
    bank_cash: Mapped[int] = mapped_column(Integer, default=12000)
    train_phase: Mapped[int] = mapped_column(Integer, default=2)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # JSON fields for complex state
    player_order_json: Mapped[str] = mapped_column(Text, default="[]")
    passed_players_json: Mapped[str] = mapped_column(Text, default="[]")

    # Relationships
    game_players: Mapped[list["GamePlayerModel"]] = relationship(
        back_populates="game", cascade="all, delete-orphan"
    )
    companies: Mapped[list["CompanyModel"]] = relationship(
        back_populates="game", cascade="all, delete-orphan"
    )
    trains: Mapped[list["TrainModel"]] = relationship(
        back_populates="game", cascade="all, delete-orphan"
    )
    game_log: Mapped[list["GameLogModel"]] = relationship(
        back_populates="game", cascade="all, delete-orphan"
    )

    @property
    def player_order(self) -> list[str]:
        """Get player order as list."""
        return json.loads(self.player_order_json)

    @player_order.setter
    def player_order(self, value: list[str]) -> None:
        """Set player order from list."""
        self.player_order_json = json.dumps(value)

    @property
    def passed_players(self) -> set[str]:
        """Get passed players as set."""
        return set(json.loads(self.passed_players_json))

    @passed_players.setter
    def passed_players(self, value: set[str]) -> None:
        """Set passed players from set."""
        self.passed_players_json = json.dumps(list(value))


class GamePlayerModel(Base):
    """Database model for game-player relationship with game-specific state."""

    __tablename__ = "game_players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(String(64), ForeignKey("games.id"), index=True)
    player_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("players.id"), index=True
    )
    cash: Mapped[int] = mapped_column(Integer, default=0)
    priority_deal: Mapped[int] = mapped_column(Integer, default=0)  # 1 = true

    # Stock holdings as JSON
    stocks_json: Mapped[str] = mapped_column(Text, default="{}")

    # Relationships
    game: Mapped["GameModel"] = relationship(back_populates="game_players")
    player: Mapped["PlayerModel"] = relationship(back_populates="game_players")

    @property
    def stocks(self) -> dict[str, int]:
        """Get stocks as dictionary."""
        return json.loads(self.stocks_json)

    @stocks.setter
    def stocks(self, value: dict[str, int]) -> None:
        """Set stocks from dictionary."""
        self.stocks_json = json.dumps(value)


class CompanyModel(Base):
    """Database model for companies."""

    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(String(64), ForeignKey("games.id"), index=True)
    company_id: Mapped[str] = mapped_column(String(8))  # AR, IR, etc.
    name: Mapped[str] = mapped_column(String(255))
    color: Mapped[str] = mapped_column(String(8))
    status: Mapped[str] = mapped_column(String(32))
    president_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    treasury: Mapped[int] = mapped_column(Integer, default=0)
    stock_price_index: Mapped[int] = mapped_column(Integer, default=0)
    shares_in_ipo: Mapped[int] = mapped_column(Integer, default=10)
    shares_in_market: Mapped[int] = mapped_column(Integer, default=0)
    tokens_remaining: Mapped[int] = mapped_column(Integer, default=3)
    operated_this_round: Mapped[int] = mapped_column(Integer, default=0)

    # Relationship
    game: Mapped["GameModel"] = relationship(back_populates="companies")
    trains: Mapped[list["TrainModel"]] = relationship(back_populates="company")


class TrainModel(Base):
    """Database model for trains."""

    __tablename__ = "trains"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(String(64), ForeignKey("games.id"), index=True)
    train_id: Mapped[str] = mapped_column(String(64))
    train_type: Mapped[str] = mapped_column(String(8))
    company_db_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("companies.id"), nullable=True
    )
    rusted: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    game: Mapped["GameModel"] = relationship(back_populates="trains")
    company: Mapped["CompanyModel | None"] = relationship(back_populates="trains")


class GameLogModel(Base):
    """Database model for game event log."""

    __tablename__ = "game_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(String(64), ForeignKey("games.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(64))
    event_data_json: Mapped[str] = mapped_column(Text)
    stock_round: Mapped[int] = mapped_column(Integer)
    operating_round: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationship
    game: Mapped["GameModel"] = relationship(back_populates="game_log")

    @property
    def event_data(self) -> dict[str, Any]:
        """Get event data as dictionary."""
        return json.loads(self.event_data_json)

    @event_data.setter
    def event_data(self, value: dict[str, Any]) -> None:
        """Set event data from dictionary."""
        self.event_data_json = json.dumps(value)


class BoardStateModel(Base):
    """Database model for board state (tiles)."""

    __tablename__ = "board_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(String(64), ForeignKey("games.id"), index=True)
    tile_id: Mapped[str] = mapped_column(String(8))  # A1, B2, etc.
    tile_number: Mapped[str | None] = mapped_column(String(16), nullable=True)
    rotation: Mapped[int] = mapped_column(Integer, default=0)
    tokens_json: Mapped[str] = mapped_column(Text, default="[]")

    @property
    def tokens(self) -> list[str]:
        """Get tokens as list."""
        return json.loads(self.tokens_json)

    @tokens.setter
    def tokens(self, value: list[str]) -> None:
        """Set tokens from list."""
        self.tokens_json = json.dumps(value)
