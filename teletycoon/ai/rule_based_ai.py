"""Rule-based AI for TeleTycoon."""

import random
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from teletycoon.models.game_state import GameState


from .base_ai import BaseAI


class RuleBasedAI(BaseAI):
    """Rule-based AI using heuristics for decisions.

    Implements simple but effective strategies for both
    stock rounds and operating rounds.

    Attributes:
        player_id: ID of the player this AI controls.
        state: Reference to game state.
        last_reasoning: Explanation of last decision.
        aggressiveness: How aggressive the AI plays (0.0-1.0).
    """

    def __init__(
        self,
        player_id: str,
        state: "GameState",
        aggressiveness: float = 0.5,
    ) -> None:
        """Initialize rule-based AI.

        Args:
            player_id: Player ID this AI controls.
            state: The game state.
            aggressiveness: Aggression level (0=conservative, 1=aggressive).
        """
        super().__init__(player_id, state)
        self.last_reasoning = ""
        self.aggressiveness = max(0.0, min(1.0, aggressiveness))

    def choose_action(self, available_actions: list[dict[str, Any]]) -> dict[str, Any]:
        """Choose an action using rule-based heuristics.

        Args:
            available_actions: List of valid action dictionaries.

        Returns:
            The chosen action dictionary.
        """
        if not available_actions:
            self.last_reasoning = "No actions available"
            return {"type": "pass"}

        # Route to appropriate strategy
        if self.state.round_type.value == "stock":
            return self._choose_stock_action(available_actions)
        else:
            return self._choose_operating_action(available_actions)

    def get_reasoning(self) -> str:
        """Get explanation for last decision.

        Returns:
            String explaining the decision reasoning.
        """
        return self.last_reasoning

    def _choose_stock_action(self, actions: list[dict[str, Any]]) -> dict[str, Any]:
        """Choose a stock round action."""
        cash = self.get_player_cash()
        self.get_owned_shares()

        # Priority 1: Start a company if we have enough cash and no presidencies
        start_actions = [a for a in actions if a.get("type") == "start_company"]
        my_presidencies = [
            c for c in self.state.companies.values() if c.president_id == self.player_id
        ]

        if start_actions and len(my_presidencies) < 2:
            # Choose par value based on aggressiveness
            best_start = self._evaluate_company_starts(start_actions)
            if best_start:
                self.last_reasoning = (
                    f"Starting company to secure a presidency. " f"Cash: ¥{cash}"
                )
                return best_start

        # Priority 2: Buy shares in good companies
        buy_actions = [a for a in actions if a.get("type") in ("buy_ipo", "buy_market")]

        if buy_actions:
            best_buy = self._evaluate_buys(buy_actions)
            if best_buy:
                self.last_reasoning = (
                    f"Buying shares for portfolio growth. "
                    f"Cash after: ¥{cash - best_buy.get('price', 0)}"
                )
                return best_buy

        # Priority 3: Sell if needed for liquidity
        sell_actions = [a for a in actions if a.get("type") == "sell"]
        if sell_actions and cash < 100:
            best_sell = self._evaluate_sells(sell_actions)
            if best_sell:
                self.last_reasoning = f"Selling for liquidity. Low cash: ¥{cash}"
                return best_sell

        # Default: Pass
        pass_action = next(
            (a for a in actions if a.get("type") == "pass"), {"type": "pass"}
        )
        self.last_reasoning = "No attractive actions, passing"
        return pass_action

    def _evaluate_company_starts(
        self, actions: list[dict[str, Any]]
    ) -> dict[str, Any] | None:
        """Evaluate company start options."""
        if not actions:
            return None

        cash = self.get_player_cash()

        # Filter affordable options
        affordable = [a for a in actions if a.get("cost", 0) <= cash * 0.7]
        if not affordable:
            affordable = [a for a in actions if a.get("cost", 0) <= cash]

        if not affordable:
            return None

        # Prefer middle par values
        def par_score(action: dict) -> float:
            par = action.get("par_value", 80)
            # Prefer 75-85 range
            if 75 <= par <= 85:
                return 10
            elif 70 <= par <= 90:
                return 8
            return 5 + self.aggressiveness * (par / 100)

        best = max(affordable, key=par_score)
        return best

    def _evaluate_buys(self, actions: list[dict[str, Any]]) -> dict[str, Any] | None:
        """Evaluate buy options."""
        if not actions:
            return None

        cash = self.get_player_cash()
        scored_actions = []

        for action in actions:
            price = action.get("price", 0)
            if price > cash:
                continue

            company_id = action.get("company_id", "")
            company = self.state.companies.get(company_id)

            if not company:
                continue

            score = self._score_company(company, action.get("type") == "buy_ipo")

            # Adjust for affordability (prefer to keep some cash)
            if price > cash * 0.8:
                score *= 0.7
            elif price > cash * 0.5:
                score *= 0.9

            scored_actions.append((action, score))

        if not scored_actions:
            return None

        # Add some randomness
        scored_actions.sort(key=lambda x: x[1], reverse=True)
        top_actions = scored_actions[: min(3, len(scored_actions))]

        # Choose from top actions with probability
        if random.random() < 0.7:
            return top_actions[0][0]
        else:
            return random.choice(top_actions)[0]

    def _score_company(self, company, from_ipo: bool) -> float:
        """Score a company for buying."""
        score = 50.0

        # Good treasury is positive
        if company.treasury > 200:
            score += 10
        if company.treasury > 400:
            score += 10

        # Trains are important
        if company.trains:
            score += 15
        else:
            score -= 10

        # High stock price suggests success
        if company.stock_price > 100:
            score += 5
        if company.stock_price > 150:
            score += 10

        # Owning more gives control
        stock = self.state.stock_market.get_stock(company.id)
        if stock:
            my_shares = stock.get_player_shares(self.player_id)
            if my_shares >= 1:
                score += 5  # Already invested

        # IPO is usually better than market
        if from_ipo:
            score += 5

        return score

    def _evaluate_sells(self, actions: list[dict[str, Any]]) -> dict[str, Any] | None:
        """Evaluate sell options."""
        if not actions:
            return None

        # Prefer selling companies we don't control
        for action in actions:
            company_id = action.get("company_id", "")
            company = self.state.companies.get(company_id)

            if company and company.president_id != self.player_id:
                # Sell from non-controlled companies first
                return {
                    "type": "sell",
                    "company_id": company_id,
                    "count": 1,
                }

        # Otherwise sell smallest position
        return actions[0]

    def _choose_operating_action(self, actions: list[dict[str, Any]]) -> dict[str, Any]:
        """Choose an operating round action."""
        company = self.state.operating_company
        if not company:
            return {"type": "done"}

        # Find action types
        action_types = {a.get("type"): a for a in actions}

        # Priority 1: Buy trains if none
        if not company.trains and "buy_train" in action_types:
            self.last_reasoning = f"Must buy train - {company.name} has no trains"
            return self._choose_train_to_buy(actions)

        # Priority 2: Run trains if available
        if company.trains and "run_trains" in action_types:
            self.last_reasoning = f"Running trains for {company.name}"
            run_action = action_types["run_trains"]
            # Decide on dividend
            run_action["dividend"] = self._choose_dividend_strategy(company)
            return run_action

        # Priority 3: Buy better trains if affordable
        if "buy_train" in action_types:
            train_action = self._maybe_buy_train(actions, company)
            if train_action:
                return train_action

        # Priority 4: Place token
        if "place_token" in action_types and company.tokens_remaining > 0:
            token_action = action_types["place_token"]
            cities = token_action.get("cities", [])
            if cities:
                # Choose highest revenue city
                city_name = max(
                    cities,
                    key=lambda c: self.state.board.cities.get(
                        c.get("name", ""),
                        type("obj", (), {"get_revenue": lambda p: 0})(),
                    ).get_revenue(self.state.phase_number)
                    if c.get("name")
                    else 0,
                ).get("name")

                self.last_reasoning = f"Placing token in {city_name}"
                return {
                    "type": "place_token",
                    "city": city_name,
                }

        # Default: Done
        self.last_reasoning = f"Finished operating {company.name}"
        return {"type": "done"}

    def _choose_train_to_buy(self, actions: list[dict[str, Any]]) -> dict[str, Any]:
        """Choose which train to buy."""
        buy_actions = [a for a in actions if a.get("type") == "buy_train"]

        if not buy_actions:
            return {"type": "done"}

        # Get available trains from actions
        available = [a.get("available", []) for a in buy_actions]
        if available and available[0]:
            trains = available[0]
            # Choose cheapest that company can afford
            company = self.state.operating_company
            affordable = [
                t for t in trains if company and company.treasury >= t.get("cost", 0)
            ]

            if affordable:
                # Prefer higher capacity trains if affordable
                chosen = max(affordable, key=lambda t: t.get("cities", 0))
                return {
                    "type": "buy_train",
                    "train_type": chosen.get("type"),
                }

        return {"type": "done"}

    def _maybe_buy_train(
        self, actions: list[dict[str, Any]], company
    ) -> dict[str, Any] | None:
        """Decide if should buy an additional train."""
        # Don't buy if at train limit
        phase = self.state.train_depot.current_phase
        limit = 4 if phase <= 3 else 3 if phase <= 5 else 2

        if len(company.trains) >= limit:
            return None

        # Check if upgrade is worthwhile
        current_max = max(
            (t.cities for t in company.trains if not t.rusted),
            default=0,
        )

        buy_actions = [a for a in actions if a.get("type") == "buy_train"]

        for action in buy_actions:
            available = action.get("available", [])
            for train in available:
                if train.get("cities", 0) > current_max:
                    cost = train.get("cost", 0)
                    if company.treasury >= cost * 1.5:  # Keep buffer
                        self.last_reasoning = (
                            f"Upgrading train fleet for {company.name}"
                        )
                        return {
                            "type": "buy_train",
                            "train_type": train.get("type"),
                        }

        return None

    def _choose_dividend_strategy(self, company) -> str:
        """Decide whether to pay dividends or withhold."""
        # Factors: treasury needs, stock price position

        # If treasury is low, withhold
        if company.treasury < 150:
            self.last_reasoning += " - withholding for treasury"
            return "withhold"

        # If need to buy train soon, keep cash
        if not company.trains:
            return "withhold"

        # Otherwise pay dividends (helps stock price)
        self.last_reasoning += " - paying dividends"
        return "full"
