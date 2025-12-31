"""Base AI class for TeleTycoon."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from teletycoon.models.game_state import GameState


class BaseAI(ABC):
    """Abstract base class for AI players.

    Provides interface for AI decision making.

    Attributes:
        player_id: ID of the player this AI controls.
        state: Reference to game state.
    """

    def __init__(self, player_id: str, state: "GameState") -> None:
        """Initialize AI player.

        Args:
            player_id: Player ID this AI controls.
            state: The game state.
        """
        self.player_id = player_id
        self.state = state

    @abstractmethod
    def choose_action(self, available_actions: list[dict[str, Any]]) -> dict[str, Any]:
        """Choose an action from available options.

        Args:
            available_actions: List of valid action dictionaries.

        Returns:
            The chosen action dictionary.
        """

    @abstractmethod
    def get_reasoning(self) -> str:
        """Get explanation for last decision.

        Returns:
            String explaining the decision reasoning.
        """

    def get_player(self):
        """Get the player object for this AI."""
        return self.state.players.get(self.player_id)

    def get_player_cash(self) -> int:
        """Get current cash for this AI's player."""
        player = self.get_player()
        return player.cash if player else 0

    def get_owned_shares(self) -> dict[str, int]:
        """Get shares owned by this AI's player."""
        player = self.get_player()
        if not player:
            return {}
        return player.stocks.copy()

    def is_president_of(self, company_id: str) -> bool:
        """Check if AI player is president of a company."""
        company = self.state.companies.get(company_id)
        return company is not None and company.president_id == self.player_id
