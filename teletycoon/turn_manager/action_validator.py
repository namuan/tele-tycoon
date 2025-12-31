"""Action validator for TeleTycoon."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from teletycoon.models.game_state import GameState
    from teletycoon.models.player import Player

from teletycoon.models.company import PAR_VALUES_1889, CompanyStatus
from teletycoon.models.game_state import GamePhase, RoundType
from teletycoon.models.train import TRAIN_DEFINITIONS, TrainType


class ActionValidator:
    """Validates player actions for legality.

    Attributes:
        state: Reference to game state.
    """

    def __init__(self, state: "GameState") -> None:
        """Initialize action validator.

        Args:
            state: The game state to validate against.
        """
        self.state = state

    def validate_action(
        self, player_id: str, action: dict[str, Any]
    ) -> tuple[bool, str]:
        """Validate a player action.

        Args:
            player_id: Player attempting the action.
            action: Action dictionary.

        Returns:
            Tuple of (is_valid, error_message).
        """
        # Check game phase
        if self.state.current_phase == GamePhase.GAME_END:
            return False, "Game has ended"

        if self.state.current_phase == GamePhase.SETUP:
            return False, "Game has not started"

        # Route to appropriate validator
        if self.state.round_type == RoundType.STOCK:
            return self._validate_stock_action(player_id, action)
        else:
            return self._validate_operating_action(player_id, action)

    def _validate_stock_action(
        self, player_id: str, action: dict[str, Any]
    ) -> tuple[bool, str]:
        """Validate a stock round action."""
        # Check if it's player's turn
        current_player_id = self.state.player_order[self.state.current_player_index]
        if player_id != current_player_id:
            return False, "Not your turn"

        # Check if player has passed
        if player_id in self.state.passed_players:
            return False, "You have already passed this round"

        player = self.state.players.get(player_id)
        if not player:
            return False, "Player not found"

        action_type = action.get("type")

        if action_type == "pass":
            return True, ""

        elif action_type == "start_company":
            return self._validate_start_company(player, action)

        elif action_type == "buy_ipo":
            return self._validate_buy_ipo(player, action)

        elif action_type == "buy_market":
            return self._validate_buy_market(player, action)

        elif action_type == "sell":
            return self._validate_sell(player, action)

        return False, f"Unknown action type: {action_type}"

    def _validate_start_company(
        self, player: "Player", action: dict[str, Any]
    ) -> tuple[bool, str]:
        """Validate starting a company."""
        company_id = action.get("company_id")
        par_value = action.get("par_value", 65)

        if not company_id:
            return False, "Company ID required"

        company = self.state.companies.get(company_id)
        if not company:
            return False, "Company not found"

        if company.status != CompanyStatus.UNSTARTED:
            return False, "Company already started"

        if par_value not in PAR_VALUES_1889:
            return False, f"Invalid par value: {par_value}"

        cost = par_value * 2  # President's certificate is 2 shares
        if not player.can_afford(cost):
            return False, f"Cannot afford ¥{cost}"

        # Check certificate limit
        if not self._check_certificate_limit(player.id, 1):
            return False, "At certificate limit"

        return True, ""

    def _validate_buy_ipo(
        self, player: "Player", action: dict[str, Any]
    ) -> tuple[bool, str]:
        """Validate buying from IPO."""
        company_id = action.get("company_id")

        if not company_id:
            return False, "Company ID required"

        company = self.state.companies.get(company_id)
        stock = self.state.stock_market.get_stock(company_id)

        if not company or not stock:
            return False, "Company not found"

        if company.status == CompanyStatus.UNSTARTED:
            return False, "Company not yet started"

        if stock.ipo_shares <= 0:
            return False, "No shares available in IPO"

        if not player.can_afford(company.stock_price):
            return False, f"Cannot afford ¥{company.stock_price}"

        if not self._check_certificate_limit(player.id, 1):
            return False, "At certificate limit"

        return True, ""

    def _validate_buy_market(
        self, player: "Player", action: dict[str, Any]
    ) -> tuple[bool, str]:
        """Validate buying from market."""
        company_id = action.get("company_id")

        if not company_id:
            return False, "Company ID required"

        company = self.state.companies.get(company_id)
        stock = self.state.stock_market.get_stock(company_id)

        if not company or not stock:
            return False, "Company not found"

        if stock.market_shares <= 0:
            return False, "No shares available in market"

        if not player.can_afford(company.stock_price):
            return False, f"Cannot afford ¥{company.stock_price}"

        if not self._check_certificate_limit(player.id, 1):
            return False, "At certificate limit"

        return True, ""

    def _validate_sell(
        self, player: "Player", action: dict[str, Any]
    ) -> tuple[bool, str]:
        """Validate selling shares."""
        company_id = action.get("company_id")
        count = action.get("count", 1)

        if not company_id:
            return False, "Company ID required"

        company = self.state.companies.get(company_id)
        stock = self.state.stock_market.get_stock(company_id)

        if not company or not stock:
            return False, "Company not found"

        # Cannot sell in first stock round
        if self.state.stock_round_number == 1:
            return False, "Cannot sell in first stock round"

        player_shares = stock.get_player_shares(player.id)
        if count > player_shares:
            return False, f"Only have {player_shares} shares"

        # Check president rules
        if company.president_id == player.id:
            remaining = player_shares - count
            if remaining < 2:
                # Need someone else with 2+ shares
                has_successor = False
                for other_id, other_shares in stock.player_shares.items():
                    if other_id != player.id and other_shares >= 2:
                        has_successor = True
                        break
                if not has_successor:
                    return False, "Cannot dump presidency without successor"

        return True, ""

    def _validate_operating_action(
        self, player_id: str, action: dict[str, Any]
    ) -> tuple[bool, str]:
        """Validate an operating round action."""
        company = self.state.operating_company
        if not company:
            return False, "No company currently operating"

        # Check if player is president
        if company.president_id != player_id:
            return False, "Only the president can operate the company"

        action_type = action.get("type")

        if action_type == "done":
            return True, ""

        elif action_type == "lay_track":
            return self._validate_lay_track(company, action)

        elif action_type == "place_token":
            return self._validate_place_token(company, action)

        elif action_type == "run_trains":
            return self._validate_run_trains(company, action)

        elif action_type == "buy_train":
            return self._validate_buy_train(company, action)

        return False, f"Unknown action type: {action_type}"

    def _validate_lay_track(
        self, company: Any, action: dict[str, Any]
    ) -> tuple[bool, str]:
        """Validate track laying."""
        # Simplified validation - would need full tile rules
        tiles = action.get("tiles", [])
        if len(tiles) > 2:
            return False, "Cannot lay more than 2 tiles"
        return True, ""

    def _validate_place_token(
        self, company: Any, action: dict[str, Any]
    ) -> tuple[bool, str]:
        """Validate token placement."""
        if company.tokens_remaining <= 0:
            return False, "No tokens remaining"

        city_name = action.get("city")
        if city_name:
            city = self.state.board.cities.get(city_name)
            if not city:
                return False, "City not found"
            if not city.can_place_token():
                return False, "No slots available in city"
            if city.has_token(company.id):
                return False, "Already have token in city"

        return True, ""

    def _validate_run_trains(
        self, company: Any, action: dict[str, Any]
    ) -> tuple[bool, str]:
        """Validate train running."""
        if not company.trains:
            return False, "No trains to run"
        return True, ""

    def _validate_buy_train(
        self, company: Any, action: dict[str, Any]
    ) -> tuple[bool, str]:
        """Validate train purchase."""
        train_type_str = action.get("train_type")
        if not train_type_str:
            return False, "Train type required"

        try:
            train_type = TrainType(train_type_str)
        except ValueError:
            return False, "Invalid train type"

        train_def = TRAIN_DEFINITIONS.get(train_type)
        if not train_def:
            return False, "Train type not found"

        # Check phase
        if train_def["phase"] > self.state.train_depot.current_phase:
            return False, "Train not yet available"

        # Check availability
        available = [
            t
            for t in self.state.train_depot.trains
            if t.train_type == train_type and t.owner_id is None and not t.rusted
        ]
        if not available:
            return False, "No trains of this type available"

        # Check train limit
        phase = self.state.train_depot.current_phase
        limit = 4 if phase <= 3 else 3 if phase <= 5 else 2
        if len(company.trains) >= limit:
            return False, f"At train limit ({limit})"

        # Check treasury
        cost = train_def["cost"]
        if company.treasury < cost:
            return False, f"Cannot afford ¥{cost}"

        return True, ""

    def _check_certificate_limit(self, player_id: str, additional: int = 0) -> bool:
        """Check if player is within certificate limit.

        Args:
            player_id: Player to check.
            additional: Additional certificates being added.

        Returns:
            True if within limit.
        """
        # Certificate limits by player count
        limits = {2: 28, 3: 20, 4: 16, 5: 13, 6: 11}
        limit = limits.get(len(self.state.players), 16)

        current = 0
        for company_id in self.state.companies:
            stock = self.state.stock_market.get_stock(company_id)
            if stock:
                shares = stock.get_player_shares(player_id)
                if shares > 0:
                    company = self.state.companies[company_id]
                    if company.president_id == player_id:
                        current += 1  # President cert = 1
                        current += max(0, shares - 2)
                    else:
                        current += shares

        return current + additional <= limit

    def get_validation_errors(
        self, player_id: str, action: dict[str, Any]
    ) -> list[str]:
        """Get all validation errors for an action.

        Args:
            player_id: Player attempting action.
            action: Action dictionary.

        Returns:
            List of error messages (empty if valid).
        """
        is_valid, error = self.validate_action(player_id, action)
        if is_valid:
            return []
        return [error]
