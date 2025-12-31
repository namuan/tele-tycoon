"""Game state model for TeleTycoon 1889."""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .company import Company, create_1889_companies
from .player import Player
from .stock import StockMarket
from .tile import Board
from .train import TrainDepot


class GamePhase(Enum):
    """Phases of the game."""

    SETUP = "setup"
    STOCK_ROUND = "stock_round"
    OPERATING_ROUND = "operating_round"
    EMERGENCY_TRAIN_BUY = "emergency_train_buy"
    GAME_END = "game_end"


class RoundType(Enum):
    """Type of current round."""

    STOCK = "stock"
    OPERATING = "operating"


# 1889 Starting money based on player count
STARTING_MONEY_1889 = {
    2: 420,
    3: 420,
    4: 420,
    5: 390,
    6: 390,
}

# Operating rounds per stock round based on phase
OR_PER_SR = {
    2: 1,  # Phase 2: 1 OR per SR
    3: 2,  # Phase 3: 2 ORs per SR
    4: 2,
    5: 3,  # Phase 5+: 3 ORs per SR
    6: 3,
    7: 3,
}


@dataclass
class GameState:
    """Complete game state for TeleTycoon 1889.

    This class holds all state needed to fully represent a game in progress.

    Attributes:
        id: Unique game identifier.
        players: Dictionary of player_id to Player.
        companies: Dictionary of company_id to Company.
        board: The game board.
        stock_market: Stock market state.
        train_depot: Train supply.
        current_phase: Current game phase.
        round_type: Current round type (stock or operating).
        current_player_index: Index into player order for current turn.
        player_order: List of player IDs in turn order.
        stock_round_number: Current stock round number.
        operating_round_number: Current operating round within SR.
        operating_rounds_remaining: ORs remaining before next SR.
        bank_cash: Cash remaining in the bank.
        actions_this_turn: Number of actions taken this turn.
        passed_players: Set of players who have passed this SR.
        game_log: Log of game events.
    """

    id: str
    players: dict[str, Player] = field(default_factory=dict)
    companies: dict[str, Company] = field(default_factory=dict)
    board: Board = field(default_factory=Board)
    stock_market: StockMarket = field(default_factory=StockMarket)
    train_depot: TrainDepot = field(default_factory=TrainDepot)
    current_phase: GamePhase = GamePhase.SETUP
    round_type: RoundType = RoundType.STOCK
    current_player_index: int = 0
    player_order: list[str] = field(default_factory=list)
    stock_round_number: int = 1
    operating_round_number: int = 0
    operating_rounds_remaining: int = 0
    bank_cash: int = 12000  # 1889 bank size
    actions_this_turn: int = 0
    passed_players: set[str] = field(default_factory=set)
    game_log: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Post-initialization setup."""
        self.logger = logging.getLogger(__name__)

    @property
    def current_player(self) -> Player | None:
        """Get the current player."""
        if not self.player_order:
            return None
        if self.current_player_index >= len(self.player_order):
            return None
        player_id = self.player_order[self.current_player_index]
        return self.players.get(player_id)

    @property
    def active_companies(self) -> list[Company]:
        """Get all floated/active companies."""
        from .company import CompanyStatus

        return [c for c in self.companies.values() if c.status == CompanyStatus.ACTIVE]

    @property
    def operating_company(self) -> Company | None:
        """Get the currently operating company (during OR)."""
        if self.round_type != RoundType.OPERATING:
            return None
        active = self.active_companies
        if not active:
            return None
        # Companies operate in stock price order (highest first)
        sorted_companies = sorted(active, key=lambda c: c.stock_price, reverse=True)
        for company in sorted_companies:
            if not company.operated_this_round:
                return company
        return None

    @property
    def phase_number(self) -> int:
        """Get current phase number (based on train type available)."""
        return self.train_depot.current_phase

    def add_player(self, player: Player) -> None:
        """Add a player to the game."""
        self.players[player.id] = player
        self.player_order.append(player.id)
        self.logger.info(f"Player {player.name} ({player.id}) added to game {self.id}")

    def initialize_game(self) -> None:
        """Initialize a new game of 1889."""
        self.logger.info(
            f"Initializing game {self.id} with {len(self.players)} players"
        )

        # Set up companies
        self.companies = create_1889_companies()
        self.logger.debug(f"Created {len(self.companies)} companies")

        # Add companies to stock market
        for company_id in self.companies:
            self.stock_market.add_company(company_id)

        # Distribute starting money
        player_count = len(self.players)
        if player_count not in STARTING_MONEY_1889:
            raise ValueError(f"Invalid player count: {player_count}")

        starting_money = STARTING_MONEY_1889[player_count]
        for player in self.players.values():
            player.cash = starting_money

        # Start stock round
        self.current_phase = GamePhase.STOCK_ROUND
        self.round_type = RoundType.STOCK
        self.stock_round_number = 1
        self.operating_rounds_remaining = OR_PER_SR[self.phase_number]

        self.log_event("game_start", {"player_count": player_count})
        self.logger.info(
            f"Game {self.id} initialized - SR1 starting with {player_count} players, ¥{starting_money} each"
        )

    def advance_to_next_player(self) -> None:
        """Move to the next player in turn order."""
        self.current_player_index = (self.current_player_index + 1) % len(
            self.player_order
        )
        self.actions_this_turn = 0

    def all_players_passed(self) -> bool:
        """Check if all players have passed this stock round."""
        return len(self.passed_players) >= len(self.players)

    def end_stock_round(self) -> None:
        """End the current stock round and start operating rounds."""
        self.logger.info(
            f"Ending SR{self.stock_round_number}, starting operating rounds"
        )

        # If no companies are active, skip operating rounds and start new stock round
        if not self.active_companies:
            self.logger.info("No active companies, skipping to next stock round")
            self.start_stock_round()
            return

        self.round_type = RoundType.OPERATING
        self.current_phase = GamePhase.OPERATING_ROUND
        self.operating_round_number = 1
        self.operating_rounds_remaining = OR_PER_SR[
            min(self.phase_number, max(OR_PER_SR.keys()))
        ]
        self.passed_players.clear()

        # Reset operated flags
        for company in self.companies.values():
            company.operated_this_round = False

        self.log_event("stock_round_end", {"round_number": self.stock_round_number})

    def end_operating_round(self) -> None:
        """End the current operating round."""
        self.logger.info(
            f"Ending OR{self.operating_round_number}, {self.operating_rounds_remaining - 1} ORs remaining"
        )

        self.operating_rounds_remaining -= 1

        # Reset operated flags
        for company in self.companies.values():
            company.operated_this_round = False

        if self.operating_rounds_remaining <= 0:
            # Start new stock round
            self.start_stock_round()
        else:
            self.operating_round_number += 1

        self.log_event(
            "operating_round_end",
            {"round_number": self.operating_round_number},
        )

    def start_stock_round(self) -> None:
        """Start a new stock round."""
        self.round_type = RoundType.STOCK
        self.current_phase = GamePhase.STOCK_ROUND
        self.stock_round_number += 1
        self.operating_rounds_remaining = OR_PER_SR[
            min(self.phase_number, max(OR_PER_SR.keys()))
        ]
        self.passed_players.clear()

        # Determine player order (priority deal first, then clockwise)
        # For simplicity, keep current order for now

        self.log_event("stock_round_start", {"round_number": self.stock_round_number})

    def check_game_end(self) -> bool:
        """Check if the game should end."""
        # Game ends when bank breaks
        if self.bank_cash <= 0:
            self.current_phase = GamePhase.GAME_END
            return True
        return False

    def log_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Log a game event."""
        self.game_log.append(
            {
                "type": event_type,
                "data": data,
                "sr": self.stock_round_number,
                "or": self.operating_round_number,
            }
        )

    def get_player_scores(self) -> dict[str, int]:
        """Calculate final scores for all players."""
        stock_prices = {
            company_id: company.stock_price
            for company_id, company in self.companies.items()
        }
        return {
            player_id: player.net_worth(stock_prices)
            for player_id, player in self.players.items()
        }

    def get_winner(self) -> Player | None:
        """Get the winning player."""
        if self.current_phase != GamePhase.GAME_END:
            return None
        scores = self.get_player_scores()
        if not scores:
            return None
        winner_id = max(scores, key=lambda pid: scores[pid])
        return self.players.get(winner_id)
