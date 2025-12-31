"""Company model for TeleTycoon 1889."""

from dataclasses import dataclass, field
from enum import Enum

from .train import Train


class CompanyStatus(Enum):
    """Status of a company in the game."""

    UNSTARTED = "unstarted"  # Not yet floated
    ACTIVE = "active"  # Operating normally
    RECEIVERSHIP = "receivership"  # In receivership (no president)
    CLOSED = "closed"  # Company has closed


# 1889 Companies with their abbreviations and colors
COMPANIES_1889 = {
    "AR": {"name": "Awa Railroad", "color": "🟤"},
    "IR": {"name": "Iyo Railway", "color": "🟠"},
    "SR": {"name": "Sanuki Railway", "color": "🟢"},
    "KO": {"name": "Kotohira Railway", "color": "🔵"},
    "TR": {"name": "Tosa Railway", "color": "🔴"},
    "KU": {"name": "Takamatsu Railway", "color": "🟡"},
    "UR": {"name": "Uwajima Railway", "color": "🟣"},
}

# 1889 Stock price chart (par values and movements)
STOCK_PRICES_1889 = [
    0,
    5,
    10,
    15,
    20,
    25,
    30,
    35,
    40,
    45,
    50,
    55,
    60,
    65,
    70,
    75,
    80,
    85,
    90,
    95,
    100,
    110,
    120,
    130,
    140,
    150,
    160,
    170,
    180,
    190,
    200,
    220,
    240,
    260,
    280,
    300,
    330,
    360,
    400,
]

# Valid par values for starting a company
PAR_VALUES_1889 = [65, 70, 75, 80, 85, 90, 95, 100]


@dataclass
class Company:
    """Represents a railroad company in 1889.

    Attributes:
        id: Company abbreviation (e.g., 'AR', 'IR').
        name: Full company name.
        color: Emoji representing company color.
        status: Current status of the company.
        president_id: Player ID of the current president.
        treasury: Cash in company treasury.
        stock_price_index: Index in the stock price chart.
        shares_in_ipo: Shares still in initial public offering.
        shares_in_market: Shares sold to the open market.
        trains: List of trains owned by the company.
        tokens_remaining: Number of station tokens remaining.
        operated_this_round: Whether company has operated this OR.
    """

    id: str
    name: str
    color: str
    status: CompanyStatus = CompanyStatus.UNSTARTED
    president_id: str | None = None
    treasury: int = 0
    stock_price_index: int = 0
    shares_in_ipo: int = 10  # 1889 companies have 10 shares
    shares_in_market: int = 0
    trains: list[Train] = field(default_factory=list)
    tokens_remaining: int = 3
    operated_this_round: bool = False

    @property
    def stock_price(self) -> int:
        """Get current stock price."""
        if self.stock_price_index < len(STOCK_PRICES_1889):
            return STOCK_PRICES_1889[self.stock_price_index]
        return STOCK_PRICES_1889[-1]

    @property
    def shares_owned_by_players(self) -> int:
        """Calculate shares owned by players."""
        return 10 - self.shares_in_ipo - self.shares_in_market

    @property
    def is_floated(self) -> bool:
        """Check if company has floated (50% sold from IPO)."""
        return self.shares_in_ipo <= 5 and self.status != CompanyStatus.UNSTARTED

    def float_company(self, par_value: int) -> None:
        """Float the company at given par value."""
        if par_value not in PAR_VALUES_1889:
            raise ValueError(f"Invalid par value: {par_value}")

        # Find the stock price index for this par value
        try:
            self.stock_price_index = STOCK_PRICES_1889.index(par_value)
        except ValueError:
            # Find closest value
            self.stock_price_index = min(
                range(len(STOCK_PRICES_1889)),
                key=lambda i: abs(STOCK_PRICES_1889[i] - par_value),
            )

        self.status = CompanyStatus.ACTIVE
        # Treasury gets 10 * par value when floated
        self.treasury = par_value * 10

    def add_train(self, train: Train) -> None:
        """Add a train to the company."""
        self.trains.append(train)

    def remove_train(self, train: Train) -> None:
        """Remove a train from the company."""
        if train in self.trains:
            self.trains.remove(train)

    def move_stock_price_up(self, steps: int = 1) -> None:
        """Move stock price up on the chart."""
        self.stock_price_index = min(
            self.stock_price_index + steps, len(STOCK_PRICES_1889) - 1
        )

    def move_stock_price_down(self, steps: int = 1) -> None:
        """Move stock price down on the chart."""
        self.stock_price_index = max(self.stock_price_index - steps, 0)

    def can_buy_train(self, train_cost: int) -> bool:
        """Check if company can afford a train."""
        return self.treasury >= train_cost

    def buy_train(self, train: Train, cost: int) -> None:
        """Buy a train for the company."""
        if not self.can_buy_train(cost):
            raise ValueError(f"Cannot afford train costing {cost}")
        self.treasury -= cost
        self.add_train(train)


def create_1889_companies() -> dict[str, Company]:
    """Create all companies for an 1889 game."""
    companies = {}
    for company_id, info in COMPANIES_1889.items():
        companies[company_id] = Company(
            id=company_id,
            name=info["name"],
            color=info["color"],
        )
    return companies
