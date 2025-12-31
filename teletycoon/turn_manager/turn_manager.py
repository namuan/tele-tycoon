"""Turn manager for TeleTycoon game flow control."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from teletycoon.models.game_state import GameState

from teletycoon.models.game_state import GamePhase, RoundType


class TurnManager:
    """Manages turn order and game flow.

    Handles enforcement of turn order, tracks current player,
    and manages transitions between stock rounds and operating rounds.

    Attributes:
        state: Reference to game state.
    """

    def __init__(self, state: "GameState") -> None:
        """Initialize turn manager.

        Args:
            state: The game state to manage.
        """
        self.state = state

    def get_current_player_id(self) -> str | None:
        """Get the ID of the current player.

        Returns:
            Current player ID or None if no current player.
        """
        if not self.state.player_order:
            return None
        if self.state.current_player_index >= len(self.state.player_order):
            return None
        return self.state.player_order[self.state.current_player_index]

    def is_player_turn(self, player_id: str) -> bool:
        """Check if it's a specific player's turn.

        Args:
            player_id: Player ID to check.

        Returns:
            True if it's this player's turn.
        """
        return self.get_current_player_id() == player_id

    def advance_turn(self) -> str | None:
        """Advance to the next player's turn.

        Handles skipping passed players in stock rounds.

        Returns:
            ID of the new current player, or None if round ended.
        """
        if self.state.round_type == RoundType.STOCK:
            return self._advance_stock_round_turn()
        else:
            return self._advance_operating_round_turn()

    def _advance_stock_round_turn(self) -> str | None:
        """Advance turn during stock round."""
        # Move to next player
        self.state.current_player_index = (self.state.current_player_index + 1) % len(
            self.state.player_order
        )
        self.state.actions_this_turn = 0

        # Skip passed players
        attempts = 0
        while (
            self.get_current_player_id() in self.state.passed_players
            and attempts < len(self.state.player_order)
        ):
            self.state.current_player_index = (
                self.state.current_player_index + 1
            ) % len(self.state.player_order)
            attempts += 1

        # Check if everyone has passed
        if self.state.all_players_passed():
            self._end_stock_round()
            return None

        return self.get_current_player_id()

    def _advance_operating_round_turn(self) -> str | None:
        """Advance turn during operating round.

        In operating rounds, companies operate in order,
        and the president controls each company.
        """
        # The current company should be marked as operated
        # and we move to the next unoperated company
        active = self.state.active_companies
        for company in sorted(active, key=lambda c: c.stock_price, reverse=True):
            if not company.operated_this_round:
                # Return the president of this company
                return company.president_id

        # All companies operated - end the operating round
        self._end_operating_round()
        return self.get_current_player_id()

    def _end_stock_round(self) -> None:
        """End the current stock round and start operating rounds."""
        self.state.end_stock_round()

    def _end_operating_round(self) -> None:
        """End the current operating round."""
        self.state.end_operating_round()

    def mark_player_passed(self, player_id: str) -> bool:
        """Mark a player as passed for the current stock round.

        Args:
            player_id: Player ID to mark.

        Returns:
            True if this was the last player to pass.
        """
        self.state.passed_players.add(player_id)
        return self.state.all_players_passed()

    def get_turn_info(self) -> dict[str, Any]:
        """Get information about the current turn.

        Returns:
            Dictionary with turn information.
        """
        current_player = self.state.current_player
        operating_company = self.state.operating_company

        return {
            "phase": self.state.current_phase.value,
            "round_type": self.state.round_type.value,
            "stock_round": self.state.stock_round_number,
            "operating_round": self.state.operating_round_number,
            "current_player": {
                "id": current_player.id if current_player else None,
                "name": current_player.name if current_player else None,
            },
            "operating_company": {
                "id": operating_company.id if operating_company else None,
                "name": operating_company.name if operating_company else None,
            },
            "passed_players": list(self.state.passed_players),
            "players_remaining": len(self.state.player_order)
            - len(self.state.passed_players),
        }

    def can_take_action(self, player_id: str) -> bool:
        """Check if a player can take an action now.

        Args:
            player_id: Player to check.

        Returns:
            True if player can take action.
        """
        if self.state.current_phase == GamePhase.GAME_END:
            return False

        if self.state.round_type == RoundType.STOCK:
            return self.is_player_turn(player_id)
        else:
            # In operating round, check if player is president of operating company
            company = self.state.operating_company
            if company:
                return company.president_id == player_id
            return False

    def handle_timeout(self, player_id: str) -> dict[str, Any]:
        """Handle a player timeout (auto-pass or skip).

        Args:
            player_id: Player who timed out.

        Returns:
            Result of handling the timeout.
        """
        if not self.is_player_turn(player_id):
            return {"success": False, "error": "Not this player's turn"}

        if self.state.round_type == RoundType.STOCK:
            # Auto-pass in stock round
            self.mark_player_passed(player_id)
            self.advance_turn()
            return {
                "success": True,
                "action": "auto_pass",
                "message": f"Player {player_id} auto-passed due to timeout",
            }
        else:
            # In operating round, auto-complete
            company = self.state.operating_company
            if company:
                company.operated_this_round = True
                self.advance_turn()
                return {
                    "success": True,
                    "action": "auto_complete",
                    "message": f"{company.name} auto-completed due to timeout",
                }

        return {"success": False, "error": "Could not handle timeout"}

    def set_priority_deal(self, player_id: str) -> None:
        """Set priority deal for next stock round.

        Args:
            player_id: Player to give priority deal.
        """
        for player in self.state.players.values():
            player.priority_deal = player.id == player_id

    def get_player_order(self) -> list[str]:
        """Get current player order.

        Returns:
            List of player IDs in turn order.
        """
        return self.state.player_order.copy()

    def reorder_players_for_stock_round(self) -> None:
        """Reorder players for new stock round based on priority deal."""
        # Find player with priority deal
        priority_player = None
        for player in self.state.players.values():
            if player.priority_deal:
                priority_player = player.id
                break

        if priority_player and priority_player in self.state.player_order:
            # Rotate order so priority player is first
            idx = self.state.player_order.index(priority_player)
            self.state.player_order = (
                self.state.player_order[idx:] + self.state.player_order[:idx]
            )
            self.state.current_player_index = 0
