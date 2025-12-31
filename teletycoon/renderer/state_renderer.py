"""State renderer for TeleTycoon visualization."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from teletycoon.models.game_state import GameState

from .board_renderer import BoardRenderer
from .stock_renderer import StockRenderer


class StateRenderer:
    """Main renderer for game state visualization.

    Combines all renderers to produce complete game snapshots.

    Attributes:
        state: Reference to game state.
        board_renderer: Renderer for board visualization.
        stock_renderer: Renderer for stock information.
    """

    def __init__(self, state: "GameState") -> None:
        """Initialize state renderer.

        Args:
            state: The game state to render.
        """
        self.state = state
        self.board_renderer = BoardRenderer(state)
        self.stock_renderer = StockRenderer(state)

    def render_full_snapshot(self) -> str:
        """Render complete game state snapshot.

        Returns:
            Formatted string with complete game state.
        """
        sections = [
            self._render_header(),
            self._render_player_cash(),
            self._render_companies(),
            self.stock_renderer.render_stock_table(),
            self.board_renderer.render_compact(),
            self._render_train_info(),
            self._render_turn_info(),
        ]

        return "\n\n".join(sections)

    def render_compact_snapshot(self) -> str:
        """Render compact game state for quick reference.

        Returns:
            Compact formatted string.
        """
        sections = [
            self._render_player_cash(),
            self._render_company_summary(),
            self._render_turn_info(),
        ]

        return "\n".join(sections)

    def _render_header(self) -> str:
        """Render game header."""
        phase = self.state.current_phase.value.replace("_", " ").title()
        round_info = f"SR{self.state.stock_round_number}"
        if self.state.operating_round_number > 0:
            round_info += f" OR{self.state.operating_round_number}"

        return f"═══════════════════════════════════\n🎮 TeleTycoon 1889 | {phase}\n📅 {round_info} | Phase {self.state.phase_number}\n═══════════════════════════════════"

    def _render_player_cash(self) -> str:
        """Render player cash information."""
        lines = ["💰 Player Cash:"]

        for player_id in self.state.player_order:
            player = self.state.players.get(player_id)
            if player:
                indicator = "👑" if player.priority_deal else "  "
                passed = "✓" if player_id in self.state.passed_players else " "
                lines.append(f"{indicator} {player.name}: ¥{player.cash} {passed}")

        return "\n".join(lines)

    def _render_companies(self) -> str:
        """Render company information."""
        lines = ["🚂 Companies:"]

        active = [c for c in self.state.companies.values() if c.is_floated]

        if not active:
            lines.append("  No companies started yet")
            return "\n".join(lines)

        for company in sorted(active, key=lambda c: c.stock_price, reverse=True):
            president = self.state.players.get(company.president_id or "")
            pres_name = president.name if president else "None"

            trains_str = ", ".join(t.emoji() for t in company.trains if not t.rusted)
            if not trains_str:
                trains_str = "No trains"

            lines.append(
                f"  {company.color} {company.id} | Pres: {pres_name} | "
                f"Treasury: ¥{company.treasury} | {trains_str}"
            )

        return "\n".join(lines)

    def _render_company_summary(self) -> str:
        """Render brief company summary."""
        active = [c for c in self.state.companies.values() if c.is_floated]
        if not active:
            return "🚂 No companies started"

        parts = []
        for c in sorted(active, key=lambda x: x.stock_price, reverse=True):
            parts.append(f"{c.color}{c.id}:¥{c.stock_price}")

        return "🚂 " + " | ".join(parts)

    def _render_train_info(self) -> str:
        """Render train availability information."""
        lines = ["🚃 Train Depot:"]

        available = self.state.train_depot.get_available_trains()
        if not available:
            lines.append("  No trains available")
            return "\n".join(lines)

        # Group by type
        from collections import Counter

        type_counts: Counter[str] = Counter()
        for train in available:
            type_counts[train.train_type.value] += 1

        from teletycoon.models.train import TRAIN_DEFINITIONS, TrainType

        for train_type in TrainType:
            if train_type.value in type_counts:
                count = type_counts[train_type.value]
                cost = TRAIN_DEFINITIONS[train_type]["cost"]
                cities = TRAIN_DEFINITIONS[train_type]["cities"]
                lines.append(
                    f"  {train_type.value}-train: {count} available | ¥{cost} | {cities} cities"
                )

        return "\n".join(lines)

    def _render_turn_info(self) -> str:
        """Render current turn information."""
        current = self.state.current_player
        if not current:
            return "⏳ Waiting for game to start..."

        if self.state.round_type.value == "stock":
            return f"🔔 {current.name}'s turn to act in Stock Round"
        else:
            company = self.state.operating_company
            if company:
                return f"🔔 {current.name} operating {company.name}"
            return f"🔔 {current.name}'s turn"

    def render_action_prompt(self, actions: list[dict], player_name: str) -> str:
        """Render action options for a player.

        Args:
            actions: List of available actions.
            player_name: Name of the player.

        Returns:
            Formatted action prompt.
        """
        lines = [f"📋 Options for {player_name}:"]

        for i, action in enumerate(actions, 1):
            emoji = self._action_emoji(action.get("type", ""))
            description = action.get("description", "Unknown action")
            lines.append(f"{emoji} {i}. {description}")

        return "\n".join(lines)

    def _action_emoji(self, action_type: str) -> str:
        """Get emoji for action type."""
        emojis = {
            "start_company": "🏢",
            "buy_ipo": "📈",
            "buy_market": "🛒",
            "sell": "📉",
            "pass": "⏭️",
            "lay_track": "🛤️",
            "place_token": "📍",
            "run_trains": "🚂",
            "buy_train": "🚃",
            "done": "✅",
        }
        return emojis.get(action_type, "▪️")

    def render_action_result(self, result: dict) -> str:
        """Render the result of an action.

        Args:
            result: Action result dictionary.

        Returns:
            Formatted result message.
        """
        if result.get("success"):
            emoji = "✅"
            message = result.get("message", "Action completed")
        else:
            emoji = "❌"
            message = result.get("error", "Action failed")

        return f"{emoji} {message}"

    def render_game_end(self) -> str:
        """Render game end summary.

        Returns:
            Formatted game end message.
        """
        scores = self.state.get_player_scores()
        winner = self.state.get_winner()

        lines = [
            "═══════════════════════════════════",
            "🏆 GAME OVER! 🏆",
            "═══════════════════════════════════",
            "",
            "Final Scores:",
        ]

        for player_id, score in sorted(
            scores.items(), key=lambda x: x[1], reverse=True
        ):
            player = self.state.players.get(player_id)
            name = player.name if player else player_id
            crown = "👑 " if winner and winner.id == player_id else "   "
            lines.append(f"{crown}{name}: ¥{score}")

        if winner:
            lines.append("")
            lines.append(f"🎉 {winner.name} wins! 🎉")

        return "\n".join(lines)

    def render_teaching_tip(self, context: str) -> str:
        """Render a teaching tip based on context.

        Args:
            context: Context for the tip (e.g., "stock_round", "buy_train").

        Returns:
            Formatted teaching tip.
        """
        tips = {
            "stock_round": (
                "💡 Tip: In stock rounds, you can buy shares to control companies "
                "or sell shares for cash. Getting 2 shares makes you president!"
            ),
            "operating_round": (
                "💡 Tip: Companies operate in stock price order (highest first). "
                "Presidents decide where to lay track and how to run trains."
            ),
            "buy_train": (
                "💡 Tip: Companies MUST have at least one train. "
                "New train types cause older trains to rust!"
            ),
            "start_company": (
                "💡 Tip: Starting a company costs 2× par value for the "
                "president's certificate. Choose par carefully!"
            ),
            "dividends": (
                "💡 Tip: Paying dividends increases stock price. "
                "Withholding keeps cash in treasury but decreases price."
            ),
        }

        return tips.get(context, "💡 Tip: Think strategically about your moves!")
