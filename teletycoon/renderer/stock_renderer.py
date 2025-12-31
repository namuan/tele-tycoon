"""Stock renderer for TeleTycoon visualization."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from teletycoon.models.game_state import GameState


class StockRenderer:
    """Renders stock market information.

    Produces formatted tables and summaries of stock ownership.

    Attributes:
        state: Reference to game state.
    """

    def __init__(self, state: "GameState") -> None:
        """Initialize stock renderer.

        Args:
            state: The game state to render.
        """
        self.state = state

    def render_stock_table(self) -> str:
        """Render the full stock ownership table.

        Returns:
            Formatted stock table.
        """
        lines = ["📈 Stock Prices & Ownership:"]

        # Header row
        player_names = [
            self.state.players[pid].name[:3] for pid in self.state.player_order
        ]
        header = "Company | Price | IPO | Mkt | " + " | ".join(player_names)
        lines.append(header)
        lines.append("-" * len(header))

        from teletycoon.models.company import CompanyStatus

        # Company rows
        for company_id, company in sorted(
            self.state.companies.items(),
            key=lambda x: x[1].stock_price
            if x[1].status == CompanyStatus.ACTIVE
            else 0,
            reverse=True,
        ):
            if company.status != CompanyStatus.ACTIVE:
                continue

            stock = self.state.stock_market.get_stock(company_id)
            if not stock:
                continue

            player_shares = []
            for player_id in self.state.player_order:
                shares = stock.get_player_shares(player_id)
                pres = "P" if company.president_id == player_id else " "
                player_shares.append(f"{shares}{pres}" if shares else "  ")

            row = (
                f"{company.color}{company.id:3} | "
                f"¥{company.stock_price:3} | "
                f" {stock.ipo_shares:2} | "
                f" {stock.market_shares:2} | "
                + " | ".join(f"{s:>2}" for s in player_shares)
            )
            lines.append(row)

        # Unstarted companies
        unstarted = [
            c
            for c in self.state.companies.values()
            if c.status == CompanyStatus.UNSTARTED
        ]
        if unstarted:
            lines.append("")
            lines.append(
                "Not Started: " + ", ".join(f"{c.color}{c.id}" for c in unstarted)
            )

        return "\n".join(lines)

    def render_player_portfolio(self, player_id: str) -> str:
        """Render a player's stock portfolio.

        Args:
            player_id: Player to show portfolio for.

        Returns:
            Formatted portfolio.
        """
        player = self.state.players.get(player_id)
        if not player:
            return f"Player {player_id} not found"

        lines = [f"📊 Portfolio for {player.name}:"]
        lines.append(f"💵 Cash: ¥{player.cash}")
        lines.append("")

        total_value = player.cash
        holdings = []

        for company_id, company in self.state.companies.items():
            stock = self.state.stock_market.get_stock(company_id)
            if not stock:
                continue

            shares = stock.get_player_shares(player_id)
            if shares > 0:
                value = shares * company.stock_price
                pres = " (President)" if company.president_id == player_id else ""
                holdings.append(
                    f"  {company.color} {company.id}: {shares} shares × "
                    f"¥{company.stock_price} = ¥{value}{pres}"
                )
                total_value += value

        if holdings:
            lines.append("📈 Holdings:")
            lines.extend(holdings)
        else:
            lines.append("📈 No stock holdings")

        lines.append("")
        lines.append(f"💰 Total Value: ¥{total_value}")

        return "\n".join(lines)

    def render_company_stock_info(self, company_id: str) -> str:
        """Render detailed stock info for a company.

        Args:
            company_id: Company to show info for.

        Returns:
            Formatted company stock info.
        """
        company = self.state.companies.get(company_id)
        stock = self.state.stock_market.get_stock(company_id)

        if not company or not stock:
            return f"Company {company_id} not found"

        lines = [f"📊 {company.name} ({company_id}) Stock Info:"]

        if not company.is_floated:
            lines.append("  Status: Not yet started")
            lines.append(f"  Shares in IPO: {stock.ipo_shares}")
            return "\n".join(lines)

        lines.append(f"  {company.color} Status: {company.status.value}")
        lines.append(f"  💹 Stock Price: ¥{company.stock_price}")
        lines.append(f"  🏦 Treasury: ¥{company.treasury}")
        lines.append("")
        lines.append("  📊 Share Distribution:")
        lines.append(f"    IPO: {stock.ipo_shares}")
        lines.append(f"    Market: {stock.market_shares}")

        for player_id, shares in stock.player_shares.items():
            player = self.state.players.get(player_id)
            name = player.name if player else player_id
            pres = " (President)" if company.president_id == player_id else ""
            lines.append(f"    {name}: {shares}{pres}")

        return "\n".join(lines)

    def render_market_summary(self) -> str:
        """Render summary of shares available in market.

        Returns:
            Market summary.
        """
        lines = ["🛒 Open Market:"]

        available = []
        for company_id, company in self.state.companies.items():
            stock = self.state.stock_market.get_stock(company_id)
            if stock and stock.market_shares > 0:
                available.append(
                    f"  {company.color}{company_id}: {stock.market_shares} "
                    f"@ ¥{company.stock_price}"
                )

        if available:
            lines.extend(available)
        else:
            lines.append("  No shares available in market")

        return "\n".join(lines)

    def render_ipo_summary(self) -> str:
        """Render summary of shares available in IPO.

        Returns:
            IPO summary.
        """
        lines = ["📦 IPO Shares:"]

        for company_id, company in self.state.companies.items():
            stock = self.state.stock_market.get_stock(company_id)
            if not stock:
                continue

            if stock.ipo_shares > 0:
                if company.is_floated:
                    lines.append(
                        f"  {company.color}{company_id}: {stock.ipo_shares} "
                        f"@ ¥{company.stock_price}"
                    )
                else:
                    lines.append(
                        f"  {company.color}{company_id}: {stock.ipo_shares} "
                        f"(not started)"
                    )

        return "\n".join(lines)

    def render_stock_price_chart(self) -> str:
        """Render visual stock price chart.

        Returns:
            Stock price chart visualization.
        """
        from teletycoon.models.company import STOCK_PRICES_1889

        lines = ["📈 Stock Price Chart:"]

        # Show relevant portion of chart with company positions
        company_positions: dict[int, list[str]] = {}
        for company in self.state.companies.values():
            if company.is_floated:
                idx = company.stock_price_index
                if idx not in company_positions:
                    company_positions[idx] = []
                company_positions[idx].append(company.id)

        # Display chart (simplified - show around active prices)
        if company_positions:
            min_idx = max(0, min(company_positions.keys()) - 2)
            max_idx = min(
                len(STOCK_PRICES_1889) - 1,
                max(company_positions.keys()) + 2,
            )

            for idx in range(min_idx, max_idx + 1):
                price = STOCK_PRICES_1889[idx]
                companies = company_positions.get(idx, [])
                company_str = " ".join(companies) if companies else ""
                marker = ">" if companies else " "
                lines.append(f"  {marker} ¥{price:3} {company_str}")
        else:
            lines.append("  No companies on chart yet")

        return "\n".join(lines)

    def render_certificate_count(self, player_id: str) -> str:
        """Render certificate count for a player.

        Args:
            player_id: Player to count for.

        Returns:
            Certificate count info.
        """
        player = self.state.players.get(player_id)
        if not player:
            return f"Player {player_id} not found"

        count = 0
        for company_id in self.state.companies:
            stock = self.state.stock_market.get_stock(company_id)
            if stock:
                shares = stock.get_player_shares(player_id)
                if shares > 0:
                    company = self.state.companies[company_id]
                    if company.president_id == player_id:
                        count += 1 + max(0, shares - 2)
                    else:
                        count += shares

        # Get limit
        limits = {2: 28, 3: 20, 4: 16, 5: 13, 6: 11}
        limit = limits.get(len(self.state.players), 16)

        return f"📜 {player.name}: {count}/{limit} certificates"
