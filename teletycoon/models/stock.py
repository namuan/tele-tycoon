"""Stock model for TeleTycoon 1889."""

from dataclasses import dataclass, field

from .company import STOCK_PRICES_1889


@dataclass
class StockPrice:
    """Represents a position on the stock price chart.

    Attributes:
        index: Position on the stock price chart.
        value: Actual price value at this position.
    """

    index: int
    value: int

    @classmethod
    def from_index(cls, index: int) -> "StockPrice":
        """Create StockPrice from chart index."""
        if index < 0:
            index = 0
        if index >= len(STOCK_PRICES_1889):
            index = len(STOCK_PRICES_1889) - 1
        return cls(index=index, value=STOCK_PRICES_1889[index])

    @classmethod
    def from_value(cls, value: int) -> "StockPrice":
        """Create StockPrice from price value (finds closest)."""
        if value in STOCK_PRICES_1889:
            index = STOCK_PRICES_1889.index(value)
        else:
            # Find closest value
            index = min(
                range(len(STOCK_PRICES_1889)),
                key=lambda i: abs(STOCK_PRICES_1889[i] - value),
            )
        return cls(index=index, value=STOCK_PRICES_1889[index])


@dataclass
class Stock:
    """Represents stock ownership information.

    Attributes:
        company_id: Company this stock belongs to.
        player_shares: Dictionary mapping player_id to shares owned.
        ipo_shares: Number of shares still in IPO.
        market_shares: Number of shares in the open market.
    """

    company_id: str
    player_shares: dict[str, int] = field(default_factory=dict)
    ipo_shares: int = 10
    market_shares: int = 0

    @property
    def total_player_shares(self) -> int:
        """Get total shares owned by players."""
        return sum(self.player_shares.values())

    @property
    def is_floated(self) -> bool:
        """Check if 50% of shares have been sold from IPO."""
        return self.ipo_shares <= 5

    def get_player_shares(self, player_id: str) -> int:
        """Get number of shares owned by a player."""
        return self.player_shares.get(player_id, 0)

    def get_president(self) -> str | None:
        """Get the player ID with most shares (president)."""
        if not self.player_shares:
            return None
        max_shares = max(self.player_shares.values())
        if max_shares < 2:
            return None  # Need at least 2 shares to be president
        # Return first player with max shares (priority order)
        for player_id, shares in self.player_shares.items():
            if shares == max_shares:
                return player_id
        return None

    def buy_from_ipo(self, player_id: str, count: int = 1) -> bool:
        """Player buys shares from IPO."""
        if count > self.ipo_shares:
            return False
        self.ipo_shares -= count
        current = self.player_shares.get(player_id, 0)
        self.player_shares[player_id] = current + count
        return True

    def buy_from_market(self, player_id: str, count: int = 1) -> bool:
        """Player buys shares from open market."""
        if count > self.market_shares:
            return False
        self.market_shares -= count
        current = self.player_shares.get(player_id, 0)
        self.player_shares[player_id] = current + count
        return True

    def sell_to_market(self, player_id: str, count: int = 1) -> bool:
        """Player sells shares to open market."""
        current = self.player_shares.get(player_id, 0)
        if count > current:
            return False
        self.player_shares[player_id] = current - count
        if self.player_shares[player_id] == 0:
            del self.player_shares[player_id]
        self.market_shares += count
        return True


class StockMarket:
    """Manages the stock market for all companies.

    Attributes:
        stocks: Dictionary mapping company_id to Stock.
    """

    def __init__(self) -> None:
        """Initialize empty stock market."""
        self.stocks: dict[str, Stock] = {}

    def add_company(self, company_id: str) -> None:
        """Add a company's stock to the market."""
        self.stocks[company_id] = Stock(company_id=company_id)

    def get_stock(self, company_id: str) -> Stock | None:
        """Get stock information for a company."""
        return self.stocks.get(company_id)

    def get_player_portfolio(self, player_id: str) -> dict[str, int]:
        """Get all shares owned by a player."""
        portfolio = {}
        for company_id, stock in self.stocks.items():
            shares = stock.get_player_shares(player_id)
            if shares > 0:
                portfolio[company_id] = shares
        return portfolio

    def get_total_shares_owned(self, player_id: str) -> int:
        """Get total number of shares owned by a player."""
        return sum(self.get_player_portfolio(player_id).values())

    def can_buy_share(
        self,
        player_id: str,
        company_id: str,
        player_cash: int,
        stock_price: int,
        from_ipo: bool = True,
    ) -> bool:
        """Check if a player can buy a share."""
        stock = self.stocks.get(company_id)
        if not stock:
            return False

        # Check cash
        if player_cash < stock_price:
            return False

        # Check availability
        if from_ipo:
            return stock.ipo_shares > 0
        else:
            return stock.market_shares > 0

    def can_sell_share(
        self,
        player_id: str,
        company_id: str,
    ) -> bool:
        """Check if a player can sell a share."""
        stock = self.stocks.get(company_id)
        if not stock:
            return False
        return stock.get_player_shares(player_id) > 0
