"""Revenue calculation for TeleTycoon 1889."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from teletycoon.models.company import Company
    from teletycoon.models.game_state import GameState
    from teletycoon.models.train import Train


@dataclass
class Route:
    """Represents a train route.

    Attributes:
        train_id: ID of the train running the route.
        cities: List of city names in the route.
        revenue: Total revenue from the route.
    """

    train_id: str
    cities: list[str]
    revenue: int


class RevenueCalculator:
    """Calculates revenue for train routes.

    Attributes:
        state: Reference to game state.
    """

    def __init__(self, state: "GameState") -> None:
        """Initialize revenue calculator.

        Args:
            state: The game state.
        """
        self.state = state

    def calculate_route_revenue(self, route: list[str], phase: int) -> int:
        """Calculate revenue for a route.

        Args:
            route: List of city names in the route.
            phase: Current game phase.

        Returns:
            Total revenue for the route.
        """
        total = 0
        for city_name in route:
            city = self.state.board.cities.get(city_name)
            if city:
                total += city.get_revenue(phase)
        return total

    def find_best_routes(self, company: "Company") -> list[Route]:
        """Find optimal routes for a company's trains.

        This is a simplified implementation. A full implementation
        would use graph algorithms to find optimal non-overlapping routes.

        Args:
            company: The company to find routes for.

        Returns:
            List of Route objects representing optimal routes.
        """
        routes = []
        phase = self.state.train_depot.current_phase

        # Get cities with company tokens
        company_cities = []
        for city_name, city in self.state.board.cities.items():
            if city.has_token(company.id):
                company_cities.append(city_name)

        if not company_cities:
            return routes

        # Simplified: for each train, calculate revenue based on capacity
        used_cities: set[str] = set()
        for train in company.trains:
            if train.rusted:
                continue

            route_cities = self._find_route_for_train(
                train, company_cities, used_cities
            )

            if route_cities:
                revenue = self.calculate_route_revenue(route_cities, phase)
                routes.append(
                    Route(
                        train_id=train.id,
                        cities=route_cities,
                        revenue=revenue,
                    )
                )
                # Mark cities as used (in real game, only hex stops are exclusive)
                used_cities.update(route_cities)

        return routes

    def _find_route_for_train(
        self,
        train: "Train",
        company_cities: list[str],
        used_cities: set[str],
    ) -> list[str]:
        """Find a route for a specific train.

        Simplified implementation that picks highest-revenue cities.

        Args:
            train: The train to find route for.
            company_cities: Cities with company tokens.
            used_cities: Cities already used by other trains.

        Returns:
            List of city names in the route.
        """
        phase = self.state.train_depot.current_phase

        # Get all accessible cities (simplified: all board cities)
        available_cities = []
        for city_name, city in self.state.board.cities.items():
            if city_name not in used_cities:
                revenue = city.get_revenue(phase)
                available_cities.append((city_name, revenue))

        # Sort by revenue descending
        available_cities.sort(key=lambda x: x[1], reverse=True)

        # Take up to train capacity cities
        route = []
        for city_name, _ in available_cities:
            if len(route) >= train.cities:
                break
            route.append(city_name)

        return route

    def calculate_total_revenue(self, company: "Company") -> tuple[int, list[Route]]:
        """Calculate total revenue for a company.

        Args:
            company: The company to calculate for.

        Returns:
            Tuple of (total revenue, list of routes).
        """
        routes = self.find_best_routes(company)
        total = sum(route.revenue for route in routes)
        return total, routes

    def get_dividend_options(
        self, company: "Company", total_revenue: int
    ) -> list[dict]:
        """Get dividend distribution options.

        Args:
            company: The company.
            total_revenue: Total revenue earned.

        Returns:
            List of dividend option dictionaries.
        """
        per_share = total_revenue // 10

        options = [
            {
                "type": "full",
                "description": f"Pay ¥{per_share} per share (¥{total_revenue} total)",
                "to_treasury": 0,
                "stock_effect": "up",
            },
            {
                "type": "withhold",
                "description": f"Withhold ¥{total_revenue} to treasury",
                "to_treasury": total_revenue,
                "stock_effect": "down",
            },
        ]

        # Half dividend option (available in some variants)
        half = total_revenue // 2
        options.insert(
            1,
            {
                "type": "half",
                "description": f"Pay half (¥{half // 10}/share), keep ¥{total_revenue - half}",
                "to_treasury": total_revenue - half,
                "stock_effect": "none",
            },
        )

        return options
