"""Board renderer for TeleTycoon visualization."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from teletycoon.models.game_state import GameState


class BoardRenderer:
    """Renders the game board for display.

    Produces ASCII + emoji representations of the board state.

    Attributes:
        state: Reference to game state.
    """

    def __init__(self, state: "GameState") -> None:
        """Initialize board renderer.

        Args:
            state: The game state to render.
        """
        self.state = state

    def render_full(self) -> str:
        """Render full board with details.

        Returns:
            Full board representation.
        """
        return self.state.board.render_ascii()

    def render_compact(self) -> str:
        """Render compact board overview.

        Returns:
            Compact board representation.
        """
        lines = ["🗺️ Board Overview:"]

        # Show cities with tokens
        cities_with_tokens = []
        for city_name, city in self.state.board.cities.items():
            if city.tokens:
                token_str = ", ".join(city.tokens)
                cities_with_tokens.append(f"  {city_name}: {token_str}")

        if cities_with_tokens:
            lines.append("📍 Station Tokens:")
            lines.extend(cities_with_tokens)
        else:
            lines.append("  No station tokens placed yet")

        return "\n".join(lines)

    def render_route_map(self, company_id: str) -> str:
        """Render routes for a specific company.

        Args:
            company_id: Company to show routes for.

        Returns:
            Route visualization for the company.
        """
        company = self.state.companies.get(company_id)
        if not company:
            return f"Company {company_id} not found"

        lines = [f"🛤️ Routes for {company.name}:"]

        # Find cities with company tokens
        company_cities = []
        for city_name, city in self.state.board.cities.items():
            if city.has_token(company_id):
                revenue = city.get_revenue(self.state.phase_number)
                company_cities.append(f"  📍 {city_name}: ¥{revenue}")

        if company_cities:
            lines.extend(company_cities)
        else:
            lines.append("  No station tokens placed")

        return "\n".join(lines)

    def render_tile_options(self, tile_id: str) -> str:
        """Render available tile upgrades for a hex.

        Args:
            tile_id: Tile to show options for.

        Returns:
            Available tile options.
        """
        tile = self.state.board.get_tile(tile_id)
        if not tile:
            return f"Tile {tile_id} not found"

        lines = [f"🔧 Options for {tile_id}:"]

        if not tile.is_upgradable:
            lines.append("  This hex cannot have track")
        elif tile.has_track:
            lines.append(f"  Current tile: {tile.tile_number}")
            lines.append("  Upgrade options available")
        else:
            lines.append("  No track laid yet")
            lines.append("  Can place initial track tile")

        return "\n".join(lines)

    def render_token_locations(self) -> str:
        """Render all token locations on the board.

        Returns:
            Token location summary.
        """
        lines = ["📍 Station Token Locations:"]

        for city_name, city in self.state.board.cities.items():
            slots = city.station_slots
            used = len(city.tokens)
            revenue = city.get_revenue(self.state.phase_number)

            slot_display = "●" * used + "○" * (slots - used)
            token_list = ", ".join(city.tokens) if city.tokens else "empty"

            lines.append(f"  {city_name} [{slot_display}] ¥{revenue}: {token_list}")

        return "\n".join(lines)

    def render_hex_info(self, tile_id: str) -> str:
        """Render detailed information about a hex.

        Args:
            tile_id: Tile ID to show info for.

        Returns:
            Detailed hex information.
        """
        tile = self.state.board.get_tile(tile_id)
        if not tile:
            return f"Tile {tile_id} not found"

        lines = [f"📌 Hex {tile_id}:"]
        lines.append(f"  Type: {tile.tile_type.value}")

        if tile.has_track:
            lines.append(f"  Tile: {tile.tile_number}")
            lines.append(f"  Rotation: {tile.rotation}")

        if tile.terrain_cost > 0:
            lines.append(f"  Terrain cost: ¥{tile.terrain_cost}")

        if tile.cities:
            lines.append("  Cities:")
            for city in tile.cities:
                revenue = city.get_revenue(self.state.phase_number)
                lines.append(f"    {city.name}: ¥{revenue}")

        return "\n".join(lines)

    def render_connection_check(self, from_city: str, to_city: str) -> str:
        """Check if two cities are connected.

        Args:
            from_city: Starting city name.
            to_city: Destination city name.

        Returns:
            Connection status message.
        """
        # Simplified - would need full route tracing
        city_a = self.state.board.cities.get(from_city)
        city_b = self.state.board.cities.get(to_city)

        if not city_a or not city_b:
            return "❓ One or both cities not found"

        # For now, assume connected if both have tokens from same company
        shared = set(city_a.tokens) & set(city_b.tokens)

        if shared:
            companies = ", ".join(shared)
            return f"🔗 {from_city} ↔ {to_city}: Connected via {companies}"
        else:
            return f"❌ {from_city} ↔ {to_city}: Not connected"
