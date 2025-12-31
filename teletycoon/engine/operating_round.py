"""Operating round handling for TeleTycoon 1889."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from teletycoon.models.company import Company
    from teletycoon.models.game_state import GameState

from teletycoon.models.train import TrainType


@dataclass
class OperatingAction:
    """Represents an operating round action.

    Attributes:
        action_type: Type of action.
        company_id: Company performing action.
        details: Additional action details.
    """

    action_type: str
    company_id: str
    details: dict[str, Any]


class OperatingRound:
    """Manages operating round logic.

    Attributes:
        state: Reference to game state.
        current_company_index: Index of currently operating company.
        company_order: List of companies in operating order.
        actions_this_round: Actions taken this round.
    """

    def __init__(self, state: "GameState") -> None:
        """Initialize operating round handler.

        Args:
            state: The game state.
        """
        self.state = state
        self.current_company_index = 0
        self.company_order: list[str] = []
        self.actions_this_round: list[OperatingAction] = []
        self._set_company_order()

    def _set_company_order(self) -> None:
        """Set operating order based on stock prices (highest first)."""
        active = [
            c
            for c in self.state.companies.values()
            if c.is_floated and c.status.value == "active"
        ]
        sorted_companies = sorted(active, key=lambda c: c.stock_price, reverse=True)
        self.company_order = [c.id for c in sorted_companies]

    def get_current_company(self) -> "Company | None":
        """Get the currently operating company."""
        if self.current_company_index >= len(self.company_order):
            return None
        company_id = self.company_order[self.current_company_index]
        return self.state.companies.get(company_id)

    def get_valid_actions(self, company: "Company") -> list[dict[str, Any]]:
        """Get valid actions for operating company.

        Args:
            company: The operating company.

        Returns:
            List of valid action dictionaries.
        """
        actions = []

        # Phase-based actions
        # 1. Lay track (up to 2 tiles typically)
        actions.append(
            {
                "type": "lay_track",
                "max_tiles": 2,
                "description": "Lay track tiles",
            }
        )

        # 2. Place station token
        if company.tokens_remaining > 0:
            available_cities = self._get_available_cities(company)
            if available_cities:
                actions.append(
                    {
                        "type": "place_token",
                        "cities": available_cities,
                        "tokens_remaining": company.tokens_remaining,
                        "description": "Place station token",
                    }
                )

        # 3. Run trains
        if company.trains:
            actions.append(
                {
                    "type": "run_trains",
                    "trains": len(company.trains),
                    "description": "Run trains and collect revenue",
                }
            )

        # 4. Buy trains
        if not company.trains or len(company.trains) < self._train_limit():
            available_trains = self._get_available_trains(company)
            if available_trains:
                actions.append(
                    {
                        "type": "buy_train",
                        "available": available_trains,
                        "description": "Buy a train",
                    }
                )

        # Done operating
        actions.append(
            {
                "type": "done",
                "description": "Finish operating",
            }
        )

        return actions

    def _get_available_cities(self, company: "Company") -> list[dict[str, Any]]:
        """Get cities where company can place tokens."""
        available = []
        for city_name, city in self.state.board.cities.items():
            if city.can_place_token() and not city.has_token(company.id):
                # Must have track connection (simplified)
                available.append(
                    {
                        "name": city_name,
                        "slots": city.station_slots,
                        "occupied": len(city.tokens),
                    }
                )
        return available

    def _get_available_trains(self, company: "Company") -> list[dict[str, Any]]:
        """Get trains available for purchase."""
        available = []
        depot_trains = self.state.train_depot.get_available_trains()

        # Group by type
        seen_types: set[TrainType] = set()
        for train in depot_trains:
            if train.train_type not in seen_types:
                if company.can_buy_train(train.cost):
                    available.append(
                        {
                            "type": train.train_type.value,
                            "name": train.name,
                            "cost": train.cost,
                            "cities": train.cities,
                        }
                    )
                seen_types.add(train.train_type)

        return available

    def _train_limit(self) -> int:
        """Get train limit based on current phase."""
        phase = self.state.train_depot.current_phase
        if phase <= 3:
            return 4
        elif phase <= 5:
            return 3
        return 2

    def execute_action(
        self, company: "Company", action: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute an operating action.

        Args:
            company: Company taking action.
            action: Action dictionary.

        Returns:
            Result dictionary.
        """
        action_type = action.get("type")

        if action_type == "lay_track":
            return self._lay_track(company, action)
        elif action_type == "place_token":
            return self._place_token(company, action)
        elif action_type == "run_trains":
            return self._run_trains(company, action)
        elif action_type == "buy_train":
            return self._buy_train(company, action)
        elif action_type == "done":
            return self._done(company)

        return {"success": False, "error": f"Unknown action: {action_type}"}

    def _lay_track(self, company: "Company", action: dict[str, Any]) -> dict[str, Any]:
        """Lay track tiles."""
        tiles = action.get("tiles", [])
        laid = []

        for tile_info in tiles[:2]:  # Max 2 tiles
            tile_id = tile_info.get("tile_id")
            tile_number = tile_info.get("tile_number", "generic")
            rotation = tile_info.get("rotation", 0)

            if tile_id and self.state.board.can_lay_track(tile_id, company.id):
                cost = self.state.board.tiles[tile_id].terrain_cost
                if company.treasury >= cost:
                    company.treasury -= cost
                    self.state.board.lay_track(tile_id, tile_number, rotation)
                    laid.append(tile_id)

        self.actions_this_round.append(
            OperatingAction(
                action_type="lay_track",
                company_id=company.id,
                details={"tiles": laid},
            )
        )

        return {
            "success": True,
            "tiles_laid": laid,
            "message": f"{company.name} laid {len(laid)} tiles",
        }

    def _place_token(
        self, company: "Company", action: dict[str, Any]
    ) -> dict[str, Any]:
        """Place a station token."""
        city_name = action.get("city")
        if not city_name:
            return {"success": True, "message": "No token placed"}

        city = self.state.board.cities.get(city_name)
        if not city:
            return {"success": False, "error": "City not found"}

        if not city.can_place_token():
            return {"success": False, "error": "No slots available"}

        if city.has_token(company.id):
            return {"success": False, "error": "Already have token"}

        # Token cost (simplified: free for home, ¥40 otherwise)
        token_cost = 0 if company.tokens_remaining == 3 else 40
        if company.treasury < token_cost:
            return {"success": False, "error": "Cannot afford token"}

        company.treasury -= token_cost
        city.place_token(company.id)
        company.tokens_remaining -= 1

        self.actions_this_round.append(
            OperatingAction(
                action_type="place_token",
                company_id=company.id,
                details={"city": city_name, "cost": token_cost},
            )
        )

        return {
            "success": True,
            "message": f"{company.name} placed token in {city_name}",
        }

    def _run_trains(self, company: "Company", action: dict[str, Any]) -> dict[str, Any]:
        """Run trains and distribute revenue."""
        routes = action.get("routes", [])
        total_revenue = 0

        if routes:
            # Use specified routes
            for route in routes:
                total_revenue += route.get("revenue", 0)
        else:
            # Calculate automatic routes (simplified)
            for train in company.trains:
                if not train.rusted:
                    # Base revenue based on train capacity
                    base = train.cities * 20 * self.state.train_depot.current_phase
                    total_revenue += base

        # Dividend decision
        dividend_action = action.get("dividend", "full")

        if dividend_action == "full":
            # Pay dividends to shareholders
            self._pay_dividends(company, total_revenue)
            company.move_stock_price_up()
        elif dividend_action == "half":
            # Half to shareholders, half to treasury
            half = total_revenue // 2
            self._pay_dividends(company, half)
            company.treasury += total_revenue - half
        else:
            # Withhold all to treasury
            company.treasury += total_revenue
            company.move_stock_price_down()

        self.actions_this_round.append(
            OperatingAction(
                action_type="run_trains",
                company_id=company.id,
                details={
                    "revenue": total_revenue,
                    "dividend": dividend_action,
                },
            )
        )

        return {
            "success": True,
            "revenue": total_revenue,
            "dividend": dividend_action,
            "message": f"{company.name} earned ¥{total_revenue}",
        }

    def _pay_dividends(self, company: "Company", total_revenue: int) -> None:
        """Pay dividends to shareholders."""
        stock = self.state.stock_market.get_stock(company.id)
        if not stock:
            return

        # Per share dividend
        per_share = total_revenue // 10

        for player_id, shares in stock.player_shares.items():
            player = self.state.players.get(player_id)
            if player:
                dividend = per_share * shares
                player.add_cash(dividend)
                self.state.bank_cash -= dividend

    def _buy_train(self, company: "Company", action: dict[str, Any]) -> dict[str, Any]:
        """Buy a train."""
        train_type_str = action.get("train_type")
        if not train_type_str:
            return {"success": True, "message": "No train purchased"}

        try:
            train_type = TrainType(train_type_str)
        except ValueError:
            return {"success": False, "error": "Invalid train type"}

        cost = self.state.train_depot.get_train_cost(train_type)

        if not company.can_buy_train(cost):
            return {"success": False, "error": "Cannot afford train"}

        # Check train limit
        if len(company.trains) >= self._train_limit():
            return {"success": False, "error": "At train limit"}

        train = self.state.train_depot.buy_train(train_type, company.id)
        if not train:
            return {"success": False, "error": "Train not available"}

        company.treasury -= cost
        company.add_train(train)

        # Handle rust
        rusted = self.state.train_depot.rust_trains(train_type)
        for rusted_train in rusted:
            for c in self.state.companies.values():
                c.remove_train(rusted_train)

        self.actions_this_round.append(
            OperatingAction(
                action_type="buy_train",
                company_id=company.id,
                details={
                    "train_type": train_type_str,
                    "cost": cost,
                    "rusted": len(rusted),
                },
            )
        )

        return {
            "success": True,
            "train": train.name,
            "cost": cost,
            "rusted": len(rusted),
            "message": f"{company.name} bought {train.name}",
        }

    def _done(self, company: "Company") -> dict[str, Any]:
        """Finish operating."""
        # Check if company needs to buy a train
        if not company.trains:
            # Forced train buy logic would go here
            pass

        company.operated_this_round = True
        self.current_company_index += 1

        # Check if round is complete
        if self.current_company_index >= len(self.company_order):
            self.state.end_operating_round()
            return {
                "success": True,
                "round_complete": True,
                "message": "Operating round complete",
            }

        self.actions_this_round.append(
            OperatingAction(
                action_type="done",
                company_id=company.id,
                details={},
            )
        )

        return {
            "success": True,
            "round_complete": False,
            "message": f"{company.name} finished operating",
        }
