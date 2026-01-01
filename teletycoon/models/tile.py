"""Tile and board models for TeleTycoon 1889."""

from dataclasses import dataclass, field
from enum import Enum


class TileType(Enum):
    """Types of tiles in the game."""

    EMPTY = "empty"
    PLAIN = "plain"
    CITY = "city"
    DOUBLE_CITY = "double_city"
    TOWN = "town"
    MOUNTAIN = "mountain"
    WATER = "water"
    OFFBOARD = "offboard"


class TrackDirection(Enum):
    """Directions tracks can connect."""

    NORTH = 0
    NORTHEAST = 1
    SOUTHEAST = 2
    SOUTH = 3
    SOUTHWEST = 4
    NORTHWEST = 5


@dataclass
class City:
    """Represents a city on the board.

    Attributes:
        name: Name of the city.
        revenue_values: List of revenue values for different phases.
        station_slots: Number of station token slots.
        tokens: List of company IDs with tokens here.
    """

    name: str
    revenue_values: list[int] = field(default_factory=list)
    station_slots: int = 1
    tokens: list[str] = field(default_factory=list)

    def get_revenue(self, phase: int) -> int:
        """Get revenue for current phase."""
        if not self.revenue_values:
            return 0
        index = min(phase - 1, len(self.revenue_values) - 1)
        return self.revenue_values[index]

    def can_place_token(self) -> bool:
        """Check if a token can be placed here."""
        return len(self.tokens) < self.station_slots

    def place_token(self, company_id: str) -> bool:
        """Place a station token for a company."""
        if not self.can_place_token():
            return False
        if company_id in self.tokens:
            return False  # Already has token
        self.tokens.append(company_id)
        return True

    def has_token(self, company_id: str) -> bool:
        """Check if company has a token here."""
        return company_id in self.tokens


@dataclass
class Tile:
    """Represents a tile on the game board.

    Attributes:
        id: Unique tile identifier (e.g., 'A1', 'B2').
        tile_type: Type of tile.
        row: Row position on board.
        col: Column position on board.
        tile_number: The tile number placed here (None if no track).
        rotation: Rotation of tile (0-5).
        cities: List of cities on this tile.
        track_connections: Set of connected directions.
        terrain_cost: Extra cost to lay track here.
    """

    id: str
    tile_type: TileType
    row: int
    col: int
    tile_number: str | None = None
    rotation: int = 0
    cities: list[City] = field(default_factory=list)
    track_connections: set[TrackDirection] = field(default_factory=set)
    terrain_cost: int = 0

    @property
    def has_track(self) -> bool:
        """Check if this tile has track laid."""
        return self.tile_number is not None

    @property
    def is_upgradable(self) -> bool:
        """Check if this tile can be upgraded."""
        # Empty, water, and offboard cannot have track
        if self.tile_type in (TileType.EMPTY, TileType.WATER, TileType.OFFBOARD):
            return False
        return True

    def place_tile(self, tile_number: str, rotation: int = 0) -> None:
        """Place a track tile here."""
        self.tile_number = tile_number
        self.rotation = rotation

    def get_revenue(self, phase: int) -> int:
        """Get total revenue from cities on this tile."""
        return sum(city.get_revenue(phase) for city in self.cities)


# 1889 Map Constants
BOARD_ROWS = 9
BOARD_COLS = 12

# Major cities in 1889 Shikoku
CITIES_1889 = {
    "Takamatsu": {"revenue": [20, 30, 40, 50], "slots": 2},
    "Kotohira": {"revenue": [10, 20, 30, 40], "slots": 1},
    "Marugame": {"revenue": [10, 20, 30, 40], "slots": 2},
    "Matsuyama": {"revenue": [20, 30, 40, 50], "slots": 2},
    "Uwajima": {"revenue": [10, 20, 30, 40], "slots": 1},
    "Kochi": {"revenue": [20, 30, 40, 50], "slots": 2},
    "Tokushima": {"revenue": [20, 30, 40, 50], "slots": 2},
    "Anan": {"revenue": [10, 20, 30, 40], "slots": 1},
    "Imabari": {"revenue": [10, 20, 30, 40], "slots": 1},
    "Niihama": {"revenue": [10, 20, 30, 40], "slots": 1},
}


class Board:
    """Represents the game board for 1889.

    Attributes:
        tiles: 2D grid of tiles.
        cities: Dictionary of city names to City objects.
    """

    def __init__(self) -> None:
        """Initialize the 1889 board."""
        self.tiles: dict[str, Tile] = {}
        self.cities: dict[str, City] = {}
        self._initialize_board()

    def _initialize_board(self) -> None:
        """Set up the initial board state."""
        # Create city objects
        for city_name, city_info in CITIES_1889.items():
            self.cities[city_name] = City(
                name=city_name,
                revenue_values=city_info["revenue"],
                station_slots=city_info["slots"],
            )

        # Create basic grid
        for row in range(BOARD_ROWS):
            for col in range(BOARD_COLS):
                tile_id = f"{chr(65 + row)}{col + 1}"  # A1, A2, ... I12
                # Default to plain terrain
                tile_type = TileType.PLAIN
                self.tiles[tile_id] = Tile(
                    id=tile_id,
                    tile_type=tile_type,
                    row=row,
                    col=col,
                )

    def get_tile(self, tile_id: str) -> Tile | None:
        """Get a tile by its ID."""
        return self.tiles.get(tile_id)

    def get_adjacent_tiles(self, tile_id: str) -> list[Tile]:
        """Get tiles adjacent to the given tile."""
        tile = self.tiles.get(tile_id)
        if not tile:
            return []

        adjacent = []
        # Hex grid adjacency (simplified for rectangular representation)
        offsets = [
            (-1, 0),  # North
            (-1, 1),  # Northeast
            (0, 1),  # East
            (1, 0),  # South
            (1, -1),  # Southwest
            (0, -1),  # West
        ]

        for dr, dc in offsets:
            new_row = tile.row + dr
            new_col = tile.col + dc
            adj_id = f"{chr(65 + new_row)}{new_col + 1}"
            if adj_id in self.tiles:
                adjacent.append(self.tiles[adj_id])

        return adjacent

    def can_lay_track(self, tile_id: str, company_id: str) -> bool:
        """Check if a company can lay track on a tile."""
        tile = self.tiles.get(tile_id)
        if not tile:
            return False
        if not tile.is_upgradable:
            return False
        # Additional rules can be added here
        return True

    def lay_track(self, tile_id: str, tile_number: str, rotation: int = 0) -> bool:
        """Lay a track tile on the board."""
        tile = self.tiles.get(tile_id)
        if not tile:
            return False
        tile.place_tile(tile_number, rotation)
        return True

    def render_ascii(self) -> str:
        """Render the board as ASCII art."""
        lines = []
        lines.append("   " + " ".join(f"{i + 1:2}" for i in range(BOARD_COLS)))

        for row in range(BOARD_ROWS):
            row_char = chr(65 + row)
            row_tiles = []
            for col in range(BOARD_COLS):
                tile_id = f"{row_char}{col + 1}"
                tile = self.tiles.get(tile_id)
                if tile:
                    if tile.has_track:
                        row_tiles.append("🛤️")
                    elif tile.tile_type == TileType.CITY:
                        row_tiles.append("🏙️")
                    elif tile.tile_type == TileType.MOUNTAIN:
                        row_tiles.append("⛰️")
                    elif tile.tile_type == TileType.WATER:
                        row_tiles.append("🌊")
                    else:
                        row_tiles.append("⬜")
                else:
                    row_tiles.append("  ")
            lines.append(f"{row_char}  " + " ".join(row_tiles))

        return "\n".join(lines)
