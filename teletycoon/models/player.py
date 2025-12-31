"""Player model for TeleTycoon."""

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class PlayerType(Enum):
    """Type of player in the game."""

    HUMAN = "human"
    RULE_BASED_AI = "rule_based_ai"
    LLM = "llm"


@dataclass
class Player:
    """Represents a player in the game.

    Attributes:
        id: Unique identifier for the player.
        name: Display name of the player.
        telegram_id: Telegram user ID (None for AI players).
        player_type: Type of player (human, AI, or LLM).
        cash: Current cash in yen.
        stocks: Dictionary of company_id -> shares owned.
        priority_deal: Whether this player has priority deal for next SR.
    """

    id: str
    name: str
    player_type: PlayerType
    cash: int = 0
    telegram_id: int | None = None
    stocks: dict[str, int] = field(default_factory=dict)
    priority_deal: bool = False

    def get_shares(self, company_id: str) -> int:
        """Get number of shares owned in a company."""
        return self.stocks.get(company_id, 0)

    def add_shares(self, company_id: str, count: int) -> None:
        """Add shares of a company to player's portfolio."""
        current = self.stocks.get(company_id, 0)
        self.stocks[company_id] = current + count

    def remove_shares(self, company_id: str, count: int) -> None:
        """Remove shares of a company from player's portfolio."""
        current = self.stocks.get(company_id, 0)
        if count > current:
            raise ValueError(f"Cannot remove {count} shares, only have {current}")
        self.stocks[company_id] = current - count
        if self.stocks[company_id] == 0:
            del self.stocks[company_id]

    def add_cash(self, amount: int) -> None:
        """Add cash to player."""
        self.cash += amount

    def remove_cash(self, amount: int) -> None:
        """Remove cash from player."""
        if amount > self.cash:
            raise ValueError(f"Cannot remove {amount}, only have {self.cash}")
        self.cash -= amount

    def can_afford(self, amount: int) -> bool:
        """Check if player can afford an amount."""
        return self.cash >= amount

    def net_worth(self, stock_prices: dict[str, int]) -> int:
        """Calculate total net worth including cash and stock value."""
        stock_value = sum(
            shares * stock_prices.get(company_id, 0)
            for company_id, shares in self.stocks.items()
        )
        return self.cash + stock_value
