"""Stock round handling for TeleTycoon 1889."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from teletycoon.models.game_state import GameState
    from teletycoon.models.player import Player

from teletycoon.models.company import PAR_VALUES_1889, CompanyStatus


@dataclass
class StockAction:
    """Represents a stock round action.

    Attributes:
        action_type: Type of action (buy, sell, start, pass).
        player_id: Player taking the action.
        company_id: Company involved (if applicable).
        shares: Number of shares involved.
        price: Price per share.
        par_value: Par value for starting company.
    """

    action_type: str
    player_id: str
    company_id: str | None = None
    shares: int = 0
    price: int = 0
    par_value: int = 0


class StockRound:
    """Manages stock round logic.

    Attributes:
        state: Reference to game state.
        actions_this_round: List of actions taken this round.
        priority_player_id: Player with priority deal.
    """

    def __init__(self, state: "GameState") -> None:
        """Initialize stock round handler.

        Args:
            state: The game state.
        """
        self.state = state
        self.actions_this_round: list[StockAction] = []
        self.priority_player_id: str | None = None

    def get_valid_actions(self, player: "Player") -> list[dict[str, Any]]:
        """Get valid actions for a player.

        Args:
            player: The player to get actions for.

        Returns:
            List of valid action dictionaries.
        """
        actions = []

        # Check certificate limit
        total_certs = self._count_player_certificates(player.id)
        cert_limit = self._get_certificate_limit()
        can_buy = total_certs < cert_limit

        for company_id, company in self.state.companies.items():
            stock = self.state.stock_market.get_stock(company_id)
            if not stock:
                continue

            player_shares = stock.get_player_shares(player.id)

            # Start company (buy president's certificate)
            if company.status == CompanyStatus.UNSTARTED and can_buy:
                for par_value in PAR_VALUES_1889:
                    if player.can_afford(par_value * 2):
                        actions.append(
                            {
                                "type": "start_company",
                                "company_id": company_id,
                                "par_value": par_value,
                                "cost": par_value * 2,
                                "description": f"Start {company.name} at ¥{par_value}",
                            }
                        )

            # Buy from IPO
            if (
                company.status == CompanyStatus.ACTIVE
                and stock.ipo_shares > 0
                and can_buy
                and player.can_afford(company.stock_price)
            ):
                actions.append(
                    {
                        "type": "buy_ipo",
                        "company_id": company_id,
                        "price": company.stock_price,
                        "description": f"Buy {company_id} from IPO at ¥{company.stock_price}",
                    }
                )

            # Buy from market
            if (
                stock.market_shares > 0
                and can_buy
                and player.can_afford(company.stock_price)
            ):
                actions.append(
                    {
                        "type": "buy_market",
                        "company_id": company_id,
                        "price": company.stock_price,
                        "description": f"Buy {company_id} from market at ¥{company.stock_price}",
                    }
                )

            # Sell shares
            if player_shares > 0:
                # Cannot sell if this is first stock round
                if self.state.stock_round_number > 1:
                    # Check if can sell without causing president issues
                    can_sell = self._can_sell_shares(player.id, company_id, 1)
                    if can_sell:
                        for count in range(1, player_shares + 1):
                            if self._can_sell_shares(player.id, company_id, count):
                                total_price = company.stock_price * count
                                actions.append(
                                    {
                                        "type": "sell",
                                        "company_id": company_id,
                                        "count": count,
                                        "total_price": total_price,
                                        "description": f"Sell {count} {company_id} for ¥{total_price}",
                                    }
                                )

        # Pass
        actions.append(
            {
                "type": "pass",
                "description": "Pass (done for this round)",
            }
        )

        return actions

    def _count_player_certificates(self, player_id: str) -> int:
        """Count total certificates held by a player."""
        total = 0
        for company_id in self.state.companies:
            stock = self.state.stock_market.get_stock(company_id)
            if stock:
                shares = stock.get_player_shares(player_id)
                # President cert counts as 1, others as 1 each
                if shares > 0:
                    company = self.state.companies[company_id]
                    if company.president_id == player_id:
                        total += 1  # President cert
                        total += max(0, shares - 2)  # Other shares
                    else:
                        total += shares
        return total

    def _get_certificate_limit(self) -> int:
        """Get certificate limit based on player count."""
        limits = {2: 28, 3: 20, 4: 16, 5: 13, 6: 11}
        return limits.get(len(self.state.players), 16)

    def _can_sell_shares(self, player_id: str, company_id: str, count: int) -> bool:
        """Check if player can sell shares without breaking rules."""
        stock = self.state.stock_market.get_stock(company_id)
        company = self.state.companies.get(company_id)
        if not stock or not company:
            return False

        player_shares = stock.get_player_shares(player_id)
        if count > player_shares:
            return False

        # If player is president, cannot sell below 2 shares
        # unless there's another player with 2+ shares
        if company.president_id == player_id:
            remaining = player_shares - count
            if remaining < 2:
                # Check if someone else can be president
                for other_id, other_shares in stock.player_shares.items():
                    if other_id != player_id and other_shares >= 2:
                        return True
                return False

        return True

    def execute_action(
        self, player: "Player", action: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute a stock round action.

        Args:
            player: Player taking action.
            action: Action dictionary.

        Returns:
            Result dictionary.
        """
        action_type = action.get("type")

        if action_type == "start_company":
            return self._start_company(
                player,
                action["company_id"],
                action["par_value"],
            )
        elif action_type == "buy_ipo":
            return self._buy_ipo(player, action["company_id"])
        elif action_type == "buy_market":
            return self._buy_market(player, action["company_id"])
        elif action_type == "sell":
            return self._sell(player, action["company_id"], action["count"])
        elif action_type == "pass":
            return self._pass(player)

        return {"success": False, "error": f"Unknown action: {action_type}"}

    def _start_company(
        self, player: "Player", company_id: str, par_value: int
    ) -> dict[str, Any]:
        """Start a new company."""
        company = self.state.companies.get(company_id)
        stock = self.state.stock_market.get_stock(company_id)
        if not company or not stock:
            return {"success": False, "error": "Company not found"}

        cost = par_value * 2
        if not player.can_afford(cost):
            return {"success": False, "error": "Insufficient funds"}

        player.remove_cash(cost)
        company.float_company(par_value)
        company.president_id = player.id
        stock.buy_from_ipo(player.id, 2)

        self.actions_this_round.append(
            StockAction(
                action_type="start_company",
                player_id=player.id,
                company_id=company_id,
                shares=2,
                price=cost,
                par_value=par_value,
            )
        )

        return {
            "success": True,
            "message": f"{player.name} started {company.name} at ¥{par_value}",
            "company": company,
        }

    def _buy_ipo(self, player: "Player", company_id: str) -> dict[str, Any]:
        """Buy share from IPO."""
        company = self.state.companies.get(company_id)
        stock = self.state.stock_market.get_stock(company_id)
        if not company or not stock:
            return {"success": False, "error": "Company not found"}

        price = company.stock_price
        if not player.can_afford(price):
            return {"success": False, "error": "Insufficient funds"}

        if not stock.buy_from_ipo(player.id):
            return {"success": False, "error": "No shares available"}

        player.remove_cash(price)
        company.treasury += price

        self.actions_this_round.append(
            StockAction(
                action_type="buy_ipo",
                player_id=player.id,
                company_id=company_id,
                shares=1,
                price=price,
            )
        )

        return {
            "success": True,
            "message": f"{player.name} bought {company_id} from IPO",
        }

    def _buy_market(self, player: "Player", company_id: str) -> dict[str, Any]:
        """Buy share from market."""
        company = self.state.companies.get(company_id)
        stock = self.state.stock_market.get_stock(company_id)
        if not company or not stock:
            return {"success": False, "error": "Company not found"}

        price = company.stock_price
        if not player.can_afford(price):
            return {"success": False, "error": "Insufficient funds"}

        if not stock.buy_from_market(player.id):
            return {"success": False, "error": "No shares available"}

        player.remove_cash(price)
        self.state.bank_cash += price

        self.actions_this_round.append(
            StockAction(
                action_type="buy_market",
                player_id=player.id,
                company_id=company_id,
                shares=1,
                price=price,
            )
        )

        return {
            "success": True,
            "message": f"{player.name} bought {company_id} from market",
        }

    def _sell(self, player: "Player", company_id: str, count: int) -> dict[str, Any]:
        """Sell shares to market."""
        company = self.state.companies.get(company_id)
        stock = self.state.stock_market.get_stock(company_id)
        if not company or not stock:
            return {"success": False, "error": "Company not found"}

        total_price = company.stock_price * count

        for _ in range(count):
            if not stock.sell_to_market(player.id):
                return {"success": False, "error": "Could not sell share"}
            company.move_stock_price_down()

        player.add_cash(total_price)
        self.state.bank_cash -= total_price

        # Check for president change
        self._check_president_change(company_id)

        self.actions_this_round.append(
            StockAction(
                action_type="sell",
                player_id=player.id,
                company_id=company_id,
                shares=count,
                price=total_price,
            )
        )

        return {
            "success": True,
            "message": f"{player.name} sold {count} {company_id}",
        }

    def _pass(self, player: "Player") -> dict[str, Any]:
        """Player passes."""
        self.state.passed_players.add(player.id)

        self.actions_this_round.append(
            StockAction(action_type="pass", player_id=player.id)
        )

        return {"success": True, "message": f"{player.name} passed"}

    def _check_president_change(self, company_id: str) -> None:
        """Check if president needs to change after a sale."""
        company = self.state.companies.get(company_id)
        stock = self.state.stock_market.get_stock(company_id)
        if not company or not stock:
            return

        current_president = company.president_id
        if not current_president:
            return

        current_shares = stock.get_player_shares(current_president)

        # Find player with most shares >= 2
        new_president = None
        max_shares = current_shares

        for player_id, shares in stock.player_shares.items():
            if shares >= 2 and shares > max_shares:
                max_shares = shares
                new_president = player_id

        if new_president and new_president != current_president:
            company.president_id = new_president
