"""Game engine for TeleTycoon 1889."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from teletycoon.models.company import CompanyStatus

if TYPE_CHECKING:
    from teletycoon.models.company import Company
from teletycoon.models.game_state import GamePhase, GameState
from teletycoon.models.player import Player, PlayerType
from teletycoon.models.train import TrainType


class GameEngine:
    """Main game engine orchestrating game flow.

    Attributes:
        state: The current game state.
    """

    def __init__(self, game_id: str) -> None:
        """Initialize a new game engine.

        Args:
            game_id: Unique identifier for this game.
        """
        self.state = GameState(id=game_id)

    def add_player(
        self,
        player_id: str,
        name: str,
        player_type: PlayerType = PlayerType.HUMAN,
        telegram_id: int | None = None,
    ) -> Player:
        """Add a player to the game.

        Args:
            player_id: Unique identifier for the player.
            name: Display name of the player.
            player_type: Type of player (human, AI, LLM).
            telegram_id: Telegram user ID for human players.

        Returns:
            The created Player object.
        """
        player = Player(
            id=player_id,
            name=name,
            player_type=player_type,
            telegram_id=telegram_id,
        )
        self.state.add_player(player)
        return player

    def start_game(self) -> None:
        """Start the game after all players have joined."""
        if len(self.state.players) < 2:
            raise ValueError("Need at least 2 players to start")
        if len(self.state.players) > 6:
            raise ValueError("Maximum 6 players allowed")

        self.state.initialize_game()

    def get_available_actions(self) -> list[dict[str, Any]]:
        """Get list of available actions for the current player.

        Returns:
            List of action dictionaries with type and parameters.
        """
        if self.state.current_phase == GamePhase.STOCK_ROUND:
            return self._get_stock_round_actions()
        elif self.state.current_phase == GamePhase.OPERATING_ROUND:
            return self._get_operating_round_actions()
        return []

    def _get_stock_round_actions(self) -> list[dict[str, Any]]:
        """Get available actions during stock round."""
        actions = []
        player = self.state.current_player
        if not player:
            return actions

        # Buy shares from IPO or market
        for company_id, company in self.state.companies.items():
            stock = self.state.stock_market.get_stock(company_id)
            if not stock:
                continue

            # Can start a new company
            if company.status == CompanyStatus.UNSTARTED:
                if player.can_afford(65):  # Minimum par value
                    actions.append(
                        {
                            "type": "start_company",
                            "company_id": company_id,
                            "description": f"Start {company.name}",
                        }
                    )

            # Can buy from IPO
            elif stock.ipo_shares > 0:
                if player.can_afford(company.stock_price):
                    actions.append(
                        {
                            "type": "buy_ipo",
                            "company_id": company_id,
                            "price": company.stock_price,
                            "description": f"Buy {company_id} from IPO at ¥{company.stock_price}",
                        }
                    )

            # Can buy from market
            if stock.market_shares > 0:
                if player.can_afford(company.stock_price):
                    actions.append(
                        {
                            "type": "buy_market",
                            "company_id": company_id,
                            "price": company.stock_price,
                            "description": f"Buy {company_id} from market at ¥{company.stock_price}",
                        }
                    )

            # Can sell shares
            player_shares = stock.get_player_shares(player.id)
            if player_shares > 0:
                # Cannot sell if president and would lose presidency
                actions.append(
                    {
                        "type": "sell",
                        "company_id": company_id,
                        "shares": player_shares,
                        "price": company.stock_price,
                        "description": f"Sell {company_id} shares at ¥{company.stock_price}",
                    }
                )

        # Pass action
        actions.append(
            {
                "type": "pass",
                "description": "Pass (done for this stock round)",
            }
        )

        return actions

    def _get_operating_round_actions(self) -> list[dict[str, Any]]:
        """Get available actions during operating round."""
        actions = []
        company = self.state.operating_company
        if not company:
            return actions

        # Lay track
        actions.append(
            {
                "type": "lay_track",
                "description": f"Lay track for {company.name}",
            }
        )

        # Place station token
        if company.tokens_remaining > 0:
            actions.append(
                {
                    "type": "place_token",
                    "description": f"Place station token ({company.tokens_remaining} remaining)",
                }
            )

        # Run trains
        if company.trains:
            actions.append(
                {
                    "type": "run_trains",
                    "description": f"Run trains ({len(company.trains)} trains)",
                }
            )

        # Buy trains
        available_trains = self.state.train_depot.get_available_trains()
        for train in available_trains:
            if company.can_buy_train(train.cost):
                actions.append(
                    {
                        "type": "buy_train",
                        "train_type": train.train_type.value,
                        "cost": train.cost,
                        "description": f"Buy {train.name} for ¥{train.cost}",
                    }
                )

        # Done operating
        actions.append(
            {
                "type": "done",
                "description": "Done operating",
            }
        )

        return actions

    def execute_action(self, action_type: str, **kwargs: Any) -> dict[str, Any]:
        """Execute a player action.

        Args:
            action_type: Type of action to execute.
            **kwargs: Action-specific parameters.

        Returns:
            Result dictionary with success status and details.
        """
        if self.state.current_phase == GamePhase.STOCK_ROUND:
            return self._execute_stock_action(action_type, **kwargs)
        elif self.state.current_phase == GamePhase.OPERATING_ROUND:
            return self._execute_operating_action(action_type, **kwargs)
        return {"success": False, "error": "Invalid game phase"}

    def _execute_stock_action(self, action_type: str, **kwargs: Any) -> dict[str, Any]:
        """Execute a stock round action."""
        player = self.state.current_player
        if not player:
            return {"success": False, "error": "No current player"}

        if action_type == "start_company":
            return self._start_company(
                player, kwargs["company_id"], kwargs.get("par_value", 65)
            )
        elif action_type == "buy_ipo":
            return self._buy_from_ipo(player, kwargs["company_id"])
        elif action_type == "buy_market":
            return self._buy_from_market(player, kwargs["company_id"])
        elif action_type == "sell":
            return self._sell_shares(
                player, kwargs["company_id"], kwargs.get("count", 1)
            )
        elif action_type == "pass":
            return self._pass_stock_round(player)

        return {"success": False, "error": f"Unknown action: {action_type}"}

    def _start_company(
        self, player: Player, company_id: str, par_value: int
    ) -> dict[str, Any]:
        """Start a new company."""
        company = self.state.companies.get(company_id)
        if not company:
            return {"success": False, "error": "Company not found"}

        if company.status != CompanyStatus.UNSTARTED:
            return {"success": False, "error": "Company already started"}

        cost = par_value * 2  # Buy 2 shares (president's certificate)
        if not player.can_afford(cost):
            return {"success": False, "error": "Cannot afford"}

        # Buy president's certificate
        player.remove_cash(cost)
        company.float_company(par_value)
        company.president_id = player.id

        # Update stock tracking
        stock = self.state.stock_market.get_stock(company_id)
        if stock:
            stock.buy_from_ipo(player.id, 2)

        self.state.log_event(
            "company_started",
            {
                "company_id": company_id,
                "president": player.id,
                "par_value": par_value,
            },
        )

        self.state.actions_this_turn += 1
        self.state.advance_to_next_player()

        return {
            "success": True,
            "message": f"{player.name} started {company.name} at ¥{par_value}",
        }

    def _buy_from_ipo(self, player: Player, company_id: str) -> dict[str, Any]:
        """Buy a share from IPO."""
        company = self.state.companies.get(company_id)
        stock = self.state.stock_market.get_stock(company_id)
        if not company or not stock:
            return {"success": False, "error": "Company not found"}

        price = company.stock_price
        if not player.can_afford(price):
            return {"success": False, "error": "Cannot afford"}

        if stock.ipo_shares <= 0:
            return {"success": False, "error": "No shares in IPO"}

        player.remove_cash(price)
        company.treasury += price
        stock.buy_from_ipo(player.id)

        self.state.log_event(
            "buy_ipo",
            {"player": player.id, "company_id": company_id, "price": price},
        )

        self.state.actions_this_turn += 1
        self.state.advance_to_next_player()

        return {
            "success": True,
            "message": f"{player.name} bought {company_id} from IPO at ¥{price}",
        }

    def _buy_from_market(self, player: Player, company_id: str) -> dict[str, Any]:
        """Buy a share from the market."""
        company = self.state.companies.get(company_id)
        stock = self.state.stock_market.get_stock(company_id)
        if not company or not stock:
            return {"success": False, "error": "Company not found"}

        price = company.stock_price
        if not player.can_afford(price):
            return {"success": False, "error": "Cannot afford"}

        if stock.market_shares <= 0:
            return {"success": False, "error": "No shares in market"}

        player.remove_cash(price)
        self.state.bank_cash += price
        stock.buy_from_market(player.id)

        self.state.log_event(
            "buy_market",
            {"player": player.id, "company_id": company_id, "price": price},
        )

        self.state.actions_this_turn += 1
        self.state.advance_to_next_player()

        return {
            "success": True,
            "message": f"{player.name} bought {company_id} from market at ¥{price}",
        }

    def _sell_shares(
        self, player: Player, company_id: str, count: int
    ) -> dict[str, Any]:
        """Sell shares to the market."""
        company = self.state.companies.get(company_id)
        stock = self.state.stock_market.get_stock(company_id)
        if not company or not stock:
            return {"success": False, "error": "Company not found"}

        player_shares = stock.get_player_shares(player.id)
        if count > player_shares:
            return {"success": False, "error": "Not enough shares"}

        price = company.stock_price * count
        player.add_cash(price)
        self.state.bank_cash -= price

        for _ in range(count):
            stock.sell_to_market(player.id)
            company.move_stock_price_down()

        self.state.log_event(
            "sell_shares",
            {
                "player": player.id,
                "company_id": company_id,
                "count": count,
                "price": price,
            },
        )

        self.state.actions_this_turn += 1
        # Selling doesn't end turn in some variants, but for simplicity advance
        self.state.advance_to_next_player()

        return {
            "success": True,
            "message": f"{player.name} sold {count} {company_id} for ¥{price}",
        }

    def _pass_stock_round(self, player: Player) -> dict[str, Any]:
        """Player passes for rest of stock round."""
        self.state.passed_players.add(player.id)

        self.state.log_event("pass", {"player": player.id})

        if self.state.all_players_passed():
            self.state.end_stock_round()
            return {
                "success": True,
                "message": f"{player.name} passed. Stock round ended.",
            }

        self.state.advance_to_next_player()

        # Skip passed players
        while (
            self.state.current_player
            and self.state.current_player.id in self.state.passed_players
        ):
            self.state.advance_to_next_player()

        return {"success": True, "message": f"{player.name} passed."}

    def _execute_operating_action(
        self, action_type: str, **kwargs: Any
    ) -> dict[str, Any]:
        """Execute an operating round action."""
        company = self.state.operating_company
        if not company:
            return {"success": False, "error": "No operating company"}

        if action_type == "lay_track":
            return self._lay_track(company, kwargs.get("tile_id", ""))
        elif action_type == "place_token":
            return self._place_token(company, kwargs.get("city", ""))
        elif action_type == "run_trains":
            return self._run_trains(company)
        elif action_type == "buy_train":
            return self._buy_train(company, TrainType(kwargs["train_type"]))
        elif action_type == "done":
            return self._done_operating(company)

        return {"success": False, "error": f"Unknown action: {action_type}"}

    def _lay_track(self, company: Company, tile_id: str) -> dict[str, Any]:
        """Lay track for a company."""
        # Simplified track laying
        if tile_id and self.state.board.can_lay_track(tile_id, company.id):
            self.state.board.lay_track(tile_id, "generic")
            self.state.log_event(
                "lay_track",
                {"company": company.id, "tile": tile_id},
            )
            return {
                "success": True,
                "message": f"{company.name} laid track on {tile_id}",
            }
        return {"success": True, "message": "Track laying skipped"}

    def _place_token(self, company: Company, city: str) -> dict[str, Any]:
        """Place a station token."""
        if city and city in self.state.board.cities:
            city_obj = self.state.board.cities[city]
            if city_obj.place_token(company.id):
                company.tokens_remaining -= 1
                self.state.log_event(
                    "place_token",
                    {"company": company.id, "city": city},
                )
                return {
                    "success": True,
                    "message": f"{company.name} placed token in {city}",
                }
        return {"success": True, "message": "Token placement skipped"}

    def _run_trains(self, company: Company) -> dict[str, Any]:
        """Run trains and calculate revenue."""
        # Simplified revenue calculation
        total_revenue = 0
        for train in company.trains:
            # Base revenue based on train type
            base_revenue = train.cities * 20
            total_revenue += base_revenue

        self.state.log_event(
            "run_trains",
            {"company": company.id, "revenue": total_revenue},
        )

        return {
            "success": True,
            "revenue": total_revenue,
            "message": f"{company.name} ran trains for ¥{total_revenue}",
        }

    def _buy_train(self, company: Company, train_type: TrainType) -> dict[str, Any]:
        """Buy a train for a company."""
        cost = self.state.train_depot.get_train_cost(train_type)

        if not company.can_buy_train(cost):
            return {"success": False, "error": "Cannot afford train"}

        train = self.state.train_depot.buy_train(train_type, company.id)
        if not train:
            return {"success": False, "error": "Train not available"}

        company.treasury -= cost
        company.add_train(train)

        # Handle rust
        rusted = self.state.train_depot.rust_trains(train_type)

        self.state.log_event(
            "buy_train",
            {
                "company": company.id,
                "train_type": train_type.value,
                "cost": cost,
                "rusted": len(rusted),
            },
        )

        return {
            "success": True,
            "message": f"{company.name} bought {train.name} for ¥{cost}",
            "rusted": len(rusted),
        }

    def _done_operating(self, company: Company) -> dict[str, Any]:
        """Complete operating for a company."""
        company.operated_this_round = True

        # Check if all companies have operated
        all_operated = all(c.operated_this_round for c in self.state.active_companies)

        if all_operated:
            self.state.end_operating_round()

            if self.state.check_game_end():
                return {"success": True, "message": "Game over!"}

        self.state.log_event("done_operating", {"company": company.id})

        return {"success": True, "message": f"{company.name} finished operating"}
