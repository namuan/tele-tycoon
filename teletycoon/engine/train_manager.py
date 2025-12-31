"""Train management for TeleTycoon 1889."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from teletycoon.models.company import Company
    from teletycoon.models.game_state import GameState

from teletycoon.models.train import TRAIN_DEFINITIONS, Train, TrainType


class TrainManager:
    """Manages train purchases, rust, and forced buys.

    Attributes:
        state: Reference to game state.
        depot: The train depot.
    """

    def __init__(self, state: "GameState") -> None:
        """Initialize train manager.

        Args:
            state: The game state.
        """
        self.state = state
        self.depot = state.train_depot

    def get_available_trains(self) -> list[dict[str, Any]]:
        """Get trains available for purchase.

        Returns:
            List of available train type information.
        """
        available = []
        seen_types: set[TrainType] = set()

        for train in self.depot.get_available_trains():
            if train.train_type not in seen_types:
                available.append(
                    {
                        "type": train.train_type.value,
                        "name": train.name,
                        "cost": train.cost,
                        "cities": train.cities,
                        "phase": train.phase,
                    }
                )
                seen_types.add(train.train_type)

        return available

    def can_company_buy_train(
        self, company: "Company", train_type: TrainType
    ) -> tuple[bool, str]:
        """Check if a company can buy a train.

        Args:
            company: The company wanting to buy.
            train_type: Type of train to buy.

        Returns:
            Tuple of (can_buy, reason).
        """
        # Check if train is available
        train_info = TRAIN_DEFINITIONS.get(train_type)
        if not train_info:
            return False, "Invalid train type"

        # Check phase
        if train_info["phase"] > self.depot.current_phase:
            return False, "Train not yet available"

        # Check if any available
        available = [
            t
            for t in self.depot.trains
            if t.train_type == train_type and t.owner_id is None and not t.rusted
        ]
        if not available:
            return False, "No trains of this type available"

        # Check train limit
        train_limit = self._get_train_limit()
        if len(company.trains) >= train_limit:
            return False, f"At train limit ({train_limit})"

        # Check treasury
        cost = train_info["cost"]
        if company.treasury < cost:
            return False, f"Insufficient funds (need ¥{cost})"

        return True, "OK"

    def buy_train(
        self, company: "Company", train_type: TrainType
    ) -> tuple[Train | None, list[Train]]:
        """Buy a train for a company.

        Args:
            company: The company buying.
            train_type: Type of train to buy.

        Returns:
            Tuple of (purchased train or None, list of rusted trains).
        """
        can_buy, reason = self.can_company_buy_train(company, train_type)
        if not can_buy:
            return None, []

        cost = TRAIN_DEFINITIONS[train_type]["cost"]
        train = self.depot.buy_train(train_type, company.id)

        if train:
            company.treasury -= cost
            company.add_train(train)

            # Handle rust
            rusted = self._process_rust(train_type)

            return train, rusted

        return None, []

    def _process_rust(self, new_train_type: TrainType) -> list[Train]:
        """Process train rusting when a new train type is bought.

        Args:
            new_train_type: The type of train just purchased.

        Returns:
            List of trains that rusted.
        """
        rusted_trains = self.depot.rust_trains(new_train_type)

        # Remove rusted trains from companies
        for train in rusted_trains:
            for company in self.state.companies.values():
                if train in company.trains:
                    company.remove_train(train)

        return rusted_trains

    def _get_train_limit(self) -> int:
        """Get train limit based on current phase.

        Returns:
            Maximum number of trains a company can own.
        """
        phase = self.depot.current_phase
        if phase <= 3:
            return 4
        elif phase <= 5:
            return 3
        return 2

    def check_forced_train_buy(self, company: "Company") -> dict[str, Any] | None:
        """Check if a company needs to make a forced train purchase.

        Args:
            company: The company to check.

        Returns:
            Forced buy information or None.
        """
        if company.trains:
            return None  # Has trains, no forced buy

        # Company must buy a train
        available = self.get_available_trains()
        if not available:
            return None

        cheapest = min(available, key=lambda t: t["cost"])

        if company.treasury >= cheapest["cost"]:
            return {
                "type": "company_buy",
                "train": cheapest,
                "message": f"{company.name} must buy a train",
            }

        # President must help
        president = self.state.players.get(company.president_id or "")
        if president:
            needed = cheapest["cost"] - company.treasury

            if president.can_afford(needed):
                return {
                    "type": "president_assist",
                    "train": cheapest,
                    "president_contribution": needed,
                    "message": f"President must contribute ¥{needed}",
                }
            else:
                # President cannot afford - bankruptcy
                return {
                    "type": "bankruptcy",
                    "message": f"{company.name} cannot afford train, bankruptcy!",
                }

        return None

    def execute_forced_buy(
        self, company: "Company", train_type: TrainType
    ) -> dict[str, Any]:
        """Execute a forced train purchase.

        Args:
            company: The company buying.
            train_type: Type of train to buy.

        Returns:
            Result of the forced purchase.
        """
        cost = TRAIN_DEFINITIONS[train_type]["cost"]
        shortfall = max(0, cost - company.treasury)

        if shortfall > 0:
            president = self.state.players.get(company.president_id or "")
            if president and president.can_afford(shortfall):
                president.remove_cash(shortfall)
                company.treasury += shortfall
            else:
                return {
                    "success": False,
                    "error": "Cannot complete forced buy",
                }

        train, rusted = self.buy_train(company, train_type)

        if train:
            return {
                "success": True,
                "train": train.name,
                "rusted": len(rusted),
                "message": f"{company.name} bought {train.name}",
            }

        return {"success": False, "error": "Could not buy train"}

    def get_phase_info(self) -> dict[str, Any]:
        """Get information about current phase.

        Returns:
            Phase information dictionary.
        """
        phase = self.depot.current_phase

        return {
            "phase": phase,
            "train_limit": self._get_train_limit(),
            "available_trains": self.get_available_trains(),
            "rust_triggered": self._get_rust_info(phase),
        }

    def _get_rust_info(self, phase: int) -> list[str]:
        """Get information about which trains have rusted.

        Args:
            phase: Current phase.

        Returns:
            List of rusted train type descriptions.
        """
        rusted = []
        if phase >= 4:
            rusted.append("2-trains rusted")
        if phase >= 6:
            rusted.append("3-trains rusted")
        if phase >= 7:
            rusted.append("4-trains rusted")
        return rusted
