"""Repository for game data persistence."""

import json
import logging
import os
import time
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from teletycoon.models.company import Company, CompanyStatus
from teletycoon.models.game_state import GamePhase, GameState, RoundType
from teletycoon.models.player import Player, PlayerType
from teletycoon.models.stock import StockMarket
from teletycoon.models.train import TrainDepot

from .models import (
    CompanyModel,
    GameLogModel,
    GameModel,
    GamePlayerModel,
    PlayerModel,
    TrainModel,
)


class GameRepository:
    """Repository for saving and loading game state.

    Attributes:
        session: SQLAlchemy database session.
    """

    def __init__(self, session: Session) -> None:
        """Initialize repository.

        Args:
            session: Database session.
        """
        self.session = session
        self.logger = logging.getLogger(__name__)

    # Player operations

    def get_or_create_player(
        self,
        player_id: str,
        telegram_id: int | None = None,
        name: str = "",
        player_type: PlayerType = PlayerType.HUMAN,
    ) -> PlayerModel:
        """Get or create a player record.

        Args:
            player_id: Unique player ID.
            telegram_id: Telegram user ID.
            name: Display name.
            player_type: Type of player.

        Returns:
            Player database model.
        """
        player = self.session.query(PlayerModel).filter_by(id=player_id).first()
        if not player:
            player = PlayerModel(
                id=player_id,
                telegram_id=telegram_id,
                name=name or player_id,
                player_type=player_type.value,
            )
            self.session.add(player)
            self.session.commit()
        return player

    def get_player_by_telegram_id(self, telegram_id: int) -> PlayerModel | None:
        """Get player by Telegram ID.

        Args:
            telegram_id: Telegram user ID.

        Returns:
            Player model or None.
        """
        return (
            self.session.query(PlayerModel).filter_by(telegram_id=telegram_id).first()
        )

    # Game operations

    def create_game(self, game_id: str) -> GameModel:
        """Create a new game record.

        Args:
            game_id: Unique game ID.

        Returns:
            Game database model.
        """
        game = GameModel(
            id=game_id,
            status="setup",
            current_phase=GamePhase.SETUP.value,
            round_type=RoundType.STOCK.value,
        )
        self.session.add(game)
        self.session.commit()
        return game

    def get_game(self, game_id: str) -> GameModel | None:
        """Get a game by ID.

        Args:
            game_id: Game ID.

        Returns:
            Game model or None.
        """
        return self.session.query(GameModel).filter_by(id=game_id).first()

    def save_game_state(self, state: GameState) -> None:
        """Save complete game state to database.

        Args:
            state: GameState object to save.
        """
        self.logger.info(f"Saving game state for game {state.id}")

        game = self.get_game(state.id)
        if not game:
            self.logger.debug(f"Game {state.id} not found, creating new game record")
            game = self.create_game(state.id)

        # Update game fields
        game.status = (
            "active" if state.current_phase != GamePhase.GAME_END else "completed"
        )
        game.current_phase = state.current_phase.value
        game.round_type = state.round_type.value
        game.stock_round_number = state.stock_round_number
        game.operating_round_number = state.operating_round_number
        game.current_player_index = state.current_player_index
        game.bank_cash = state.bank_cash
        game.train_phase = state.train_depot.current_phase
        game.player_order = state.player_order
        game.passed_players = state.passed_players

        # Save players
        for player_id, player in state.players.items():
            self._save_game_player(game.id, player)

        # Save companies
        for company_id, company in state.companies.items():
            self._save_company(game.id, company)

        # Save trains
        self._save_trains(game.id, state.train_depot)

        # Save game log
        start_index = state.persisted_game_log_count
        if start_index < 0:
            start_index = 0
        if start_index > len(state.game_log):
            start_index = len(state.game_log)

        self._save_log_entries(game.id, state.game_log[start_index:])
        self._prune_persisted_game_log(game.id)

        self.session.commit()
        state.persisted_game_log_count = len(state.game_log)
        self.logger.info(
            f"Successfully saved game state for game {state.id} with {len(state.players)} players and {len(state.companies)} companies"
        )

    def _save_game_player(self, game_id: str, player: Player) -> None:
        """Save player game state."""
        game_player = (
            self.session.query(GamePlayerModel)
            .filter_by(game_id=game_id, player_id=player.id)
            .first()
        )

        if not game_player:
            # Ensure player exists
            self.get_or_create_player(
                player.id,
                player.telegram_id,
                player.name,
                player.player_type,
            )
            game_player = GamePlayerModel(
                game_id=game_id,
                player_id=player.id,
            )
            self.session.add(game_player)

        game_player.cash = player.cash
        game_player.priority_deal = 1 if player.priority_deal else 0
        game_player.stocks = player.stocks

    def _save_company(self, game_id: str, company: Company) -> None:
        """Save company state."""
        db_company = (
            self.session.query(CompanyModel)
            .filter_by(game_id=game_id, company_id=company.id)
            .first()
        )

        if not db_company:
            db_company = CompanyModel(
                game_id=game_id,
                company_id=company.id,
                name=company.name,
                color=company.color,
            )
            self.session.add(db_company)

        db_company.status = company.status.value
        db_company.president_id = company.president_id
        db_company.treasury = company.treasury
        db_company.stock_price_index = company.stock_price_index
        db_company.shares_in_ipo = company.shares_in_ipo
        db_company.shares_in_market = company.shares_in_market
        db_company.tokens_remaining = company.tokens_remaining
        db_company.operated_this_round = 1 if company.operated_this_round else 0

    def _save_trains(self, game_id: str, depot: TrainDepot) -> None:
        """Save train state."""
        # Clear existing trains
        self.session.query(TrainModel).filter_by(game_id=game_id).delete()

        for train in depot.trains:
            db_train = TrainModel(
                game_id=game_id,
                train_id=train.id,
                train_type=train.train_type.value,
                rusted=1 if train.rusted else 0,
            )

            # Link to company if owned
            if train.owner_id:
                db_company = (
                    self.session.query(CompanyModel)
                    .filter_by(game_id=game_id, company_id=train.owner_id)
                    .first()
                )
                if db_company:
                    db_train.company_db_id = db_company.id

            self.session.add(db_train)

    def _save_log_entry(self, game_id: str, entry: dict[str, Any]) -> None:
        """Save a game log entry."""
        log = GameLogModel(
            game_id=game_id,
            event_type=entry.get("type", "unknown"),
            event_data_json=json.dumps(entry.get("data", {})),
            stock_round=entry.get("sr", 0),
            operating_round=entry.get("or", 0),
        )
        self.session.add(log)

    def _save_log_entries(self, game_id: str, entries: list[dict[str, Any]]) -> None:
        if not entries:
            return

        created_at = datetime.utcnow()
        mappings = [
            {
                "game_id": game_id,
                "event_type": entry.get("type", "unknown"),
                "event_data_json": json.dumps(entry.get("data", {})),
                "stock_round": entry.get("sr", 0),
                "operating_round": entry.get("or", 0),
                "created_at": created_at,
            }
            for entry in entries
        ]
        self.session.bulk_insert_mappings(GameLogModel, mappings)

    def _prune_persisted_game_log(self, game_id: str) -> None:
        max_entries_str = os.getenv("TELETYCOON_MAX_LOG_ENTRIES", "2000")
        try:
            max_entries = int(max_entries_str)
        except ValueError:
            max_entries = 2000

        if max_entries <= 0:
            return

        self.session.execute(
            text(
                """
                DELETE FROM game_log
                WHERE game_id = :game_id
                  AND id <= (
                    SELECT id
                    FROM game_log
                    WHERE game_id = :game_id
                    ORDER BY id DESC
                    LIMIT 1 OFFSET :max_entries
                  )
                """
            ),
            {"game_id": game_id, "max_entries": max_entries},
        )

    def load_game_state(self, game_id: str) -> GameState | None:
        """Load complete game state from database.

        Args:
            game_id: Game ID to load.

        Returns:
            GameState object or None if not found.
        """
        t0 = time.perf_counter()
        game = self.get_game(game_id)
        if not game:
            return None

        state = GameState(id=game_id)

        # Load basic game state
        t_basic_start = time.perf_counter()
        state.current_phase = GamePhase(game.current_phase)
        state.round_type = RoundType(game.round_type)
        state.stock_round_number = game.stock_round_number
        state.operating_round_number = game.operating_round_number
        state.current_player_index = game.current_player_index
        state.bank_cash = game.bank_cash
        state.player_order = game.player_order
        state.passed_players = game.passed_players
        t_basic_ms = (time.perf_counter() - t_basic_start) * 1000

        # Load players
        t_players_start = time.perf_counter()
        for game_player in game.game_players:
            player = Player(
                id=game_player.player_id,
                name=game_player.player.name,
                player_type=PlayerType(game_player.player.player_type),
                telegram_id=game_player.player.telegram_id,
                cash=game_player.cash,
                stocks=game_player.stocks,
                priority_deal=bool(game_player.priority_deal),
            )
            state.players[player.id] = player
        t_players_ms = (time.perf_counter() - t_players_start) * 1000

        # Load companies
        t_companies_start = time.perf_counter()
        for db_company in game.companies:
            company = Company(
                id=db_company.company_id,
                name=db_company.name,
                color=db_company.color,
                status=CompanyStatus(db_company.status),
                president_id=db_company.president_id,
                treasury=db_company.treasury,
                stock_price_index=db_company.stock_price_index,
                shares_in_ipo=db_company.shares_in_ipo,
                shares_in_market=db_company.shares_in_market,
                tokens_remaining=db_company.tokens_remaining,
                operated_this_round=bool(db_company.operated_this_round),
            )
            state.companies[company.id] = company
        t_companies_ms = (time.perf_counter() - t_companies_start) * 1000

        # Load trains
        t_trains_start = time.perf_counter()
        state.train_depot = TrainDepot()
        state.train_depot.current_phase = game.train_phase

        for db_train in game.trains:
            for train in state.train_depot.trains:
                if train.id == db_train.train_id:
                    train.rusted = bool(db_train.rusted)
                    if db_train.company:
                        train.owner_id = db_train.company.company_id
                        company = state.companies.get(db_train.company.company_id)
                        if company:
                            company.trains.append(train)
                    break
        t_trains_ms = (time.perf_counter() - t_trains_start) * 1000

        # Initialize stock market
        t_stock_start = time.perf_counter()
        state.stock_market = StockMarket()
        for company_id in state.companies:
            state.stock_market.add_company(company_id)
        t_stock_ms = (time.perf_counter() - t_stock_start) * 1000

        # Load game log
        t_log_start = time.perf_counter()
        max_entries_str = os.getenv("TELETYCOON_MAX_LOG_ENTRIES", "2000")
        try:
            max_entries = int(max_entries_str)
        except ValueError:
            max_entries = 2000

        max_log_id = (
            self.session.query(GameLogModel.id)
            .filter_by(game_id=game_id)
            .order_by(GameLogModel.id.desc())
            .limit(1)
            .scalar()
        )
        if max_entries <= 0:
            logs: list[GameLogModel] = []
        elif max_entries >= 50_000:
            logs = (
                self.session.query(GameLogModel)
                .filter_by(game_id=game_id)
                .order_by(GameLogModel.id.asc())
                .all()
            )
        else:
            logs = (
                self.session.query(GameLogModel)
                .filter_by(game_id=game_id)
                .order_by(GameLogModel.id.desc())
                .limit(max_entries)
                .all()
            )
            logs.reverse()

        for log in logs:
            state.game_log.append(
                {
                    "type": log.event_type,
                    "data": log.event_data,
                    "sr": log.stock_round,
                    "or": log.operating_round,
                }
            )
        t_log_ms = (time.perf_counter() - t_log_start) * 1000
        state.persisted_game_log_count = len(state.game_log)

        total_ms = (time.perf_counter() - t0) * 1000
        trace = os.getenv("TELETYCOON_DB_TRACE") == "1"
        if trace or total_ms > 750:
            loaded_log_count = len(state.game_log)
            max_log_id_display = int(max_log_id) if max_log_id is not None else 0
            self.logger.info(
                "DB load_state: game_id=%s total=%.0fms basic=%.0fms players=%.0fms companies=%.0fms trains=%.0fms stock=%.0fms log=%.0fms counts(players=%d companies=%d trains=%d log_loaded=%d log_max_id=%d)",
                game_id,
                total_ms,
                t_basic_ms,
                t_players_ms,
                t_companies_ms,
                t_trains_ms,
                t_stock_ms,
                t_log_ms,
                len(state.players),
                len(state.companies),
                len(game.trains),
                loaded_log_count,
                max_log_id_display,
            )

        return state

    def get_active_games_for_player(self, player_id: str) -> list[GameModel]:
        """Get active games for a player.

        Args:
            player_id: Player ID.

        Returns:
            List of active game models.
        """
        return (
            self.session.query(GameModel)
            .join(GamePlayerModel)
            .filter(
                GamePlayerModel.player_id == player_id,
                GameModel.status == "active",
            )
            .all()
        )

    def delete_game(self, game_id: str) -> bool:
        """Delete a game and all associated data.

        Args:
            game_id: Game ID to delete.

        Returns:
            True if deleted, False if not found.
        """
        game = self.get_game(game_id)
        if not game:
            return False

        self.session.delete(game)
        self.session.commit()
        return True
