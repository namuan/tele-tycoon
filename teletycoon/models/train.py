"""Train model for TeleTycoon 1889."""

from dataclasses import dataclass
from enum import Enum


class TrainType(Enum):
    """Types of trains available in 1889."""

    TRAIN_2 = "2"
    TRAIN_3 = "3"
    TRAIN_4 = "4"
    TRAIN_5 = "5"
    TRAIN_6 = "6"
    DIESEL = "D"


# Train definitions for 1889
TRAIN_DEFINITIONS = {
    TrainType.TRAIN_2: {
        "name": "2-Train",
        "cities": 2,
        "cost": 80,
        "rusts_on": TrainType.TRAIN_4,
        "quantity": 6,
        "phase": 2,
    },
    TrainType.TRAIN_3: {
        "name": "3-Train",
        "cities": 3,
        "cost": 180,
        "rusts_on": TrainType.TRAIN_6,
        "quantity": 5,
        "phase": 3,
    },
    TrainType.TRAIN_4: {
        "name": "4-Train",
        "cities": 4,
        "cost": 300,
        "rusts_on": TrainType.DIESEL,
        "quantity": 4,
        "phase": 4,
    },
    TrainType.TRAIN_5: {
        "name": "5-Train",
        "cities": 5,
        "cost": 450,
        "rusts_on": None,
        "quantity": 3,
        "phase": 5,
    },
    TrainType.TRAIN_6: {
        "name": "6-Train",
        "cities": 6,
        "cost": 630,
        "rusts_on": None,
        "quantity": 2,
        "phase": 6,
    },
    TrainType.DIESEL: {
        "name": "Diesel",
        "cities": 99,  # Unlimited
        "cost": 1100,
        "rusts_on": None,
        "quantity": 99,  # Unlimited
        "phase": 7,
    },
}


@dataclass
class Train:
    """Represents a train in the game.

    Attributes:
        id: Unique identifier for this train.
        train_type: Type of train (2, 3, 4, etc.).
        owner_id: Company ID that owns this train, or None if in depot.
        rusted: Whether the train has rusted.
    """

    id: str
    train_type: TrainType
    owner_id: str | None = None
    rusted: bool = False

    @property
    def name(self) -> str:
        """Get the display name of this train."""
        return TRAIN_DEFINITIONS[self.train_type]["name"]

    @property
    def cities(self) -> int:
        """Get number of cities this train can visit."""
        return TRAIN_DEFINITIONS[self.train_type]["cities"]

    @property
    def cost(self) -> int:
        """Get the purchase cost of this train type."""
        return TRAIN_DEFINITIONS[self.train_type]["cost"]

    @property
    def rusts_on(self) -> TrainType | None:
        """Get the train type that causes this train to rust."""
        return TRAIN_DEFINITIONS[self.train_type]["rusts_on"]

    @property
    def phase(self) -> int:
        """Get the phase this train type is available."""
        return TRAIN_DEFINITIONS[self.train_type]["phase"]

    def should_rust(self, new_train_type: TrainType) -> bool:
        """Check if this train should rust when a new train type is bought."""
        return self.rusts_on == new_train_type

    def rust(self) -> None:
        """Mark this train as rusted (removed from game)."""
        self.rusted = True
        self.owner_id = None

    def emoji(self) -> str:
        """Get emoji representation of this train."""
        emoji_map = {
            TrainType.TRAIN_2: "🚂2️⃣",
            TrainType.TRAIN_3: "🚂3️⃣",
            TrainType.TRAIN_4: "🚂4️⃣",
            TrainType.TRAIN_5: "🚂5️⃣",
            TrainType.TRAIN_6: "🚂6️⃣",
            TrainType.DIESEL: "🚃⚡",
        }
        return emoji_map.get(self.train_type, "🚂")


class TrainDepot:
    """Manages the supply of trains available for purchase.

    Attributes:
        trains: List of trains available for purchase.
        current_phase: Current game phase (affects available trains).
    """

    def __init__(self) -> None:
        """Initialize the train depot with all trains."""
        self.trains: list[Train] = []
        self.current_phase: int = 2
        self._next_train_id: int = 1
        self._initialize_trains()

    def _initialize_trains(self) -> None:
        """Create all trains for the game."""
        for train_type, definition in TRAIN_DEFINITIONS.items():
            quantity = definition["quantity"]
            # Don't create infinite diesel trains upfront
            if train_type == TrainType.DIESEL:
                quantity = 10  # Reasonable number for diesel
            for _ in range(quantity):
                train = Train(
                    id=f"train_{self._next_train_id}",
                    train_type=train_type,
                )
                self._next_train_id += 1
                self.trains.append(train)

    def get_available_trains(self) -> list[Train]:
        """Get trains available for purchase in current phase."""
        available = []
        for train in self.trains:
            if train.owner_id is None and not train.rusted:
                if train.phase <= self.current_phase:
                    available.append(train)
        return available

    def get_next_available_train_type(self) -> TrainType | None:
        """Get the type of the next train available for purchase."""
        available = self.get_available_trains()
        if available:
            return available[0].train_type
        return None

    def buy_train(self, train_type: TrainType, company_id: str) -> Train | None:
        """Buy a train from the depot for a company."""
        for train in self.trains:
            if (
                train.train_type == train_type
                and train.owner_id is None
                and not train.rusted
            ):
                train.owner_id = company_id
                # Check if this advances the phase
                self._check_phase_advance(train_type)
                return train
        return None

    def _check_phase_advance(self, bought_type: TrainType) -> None:
        """Check if buying a train advances the phase."""
        train_phase = TRAIN_DEFINITIONS[bought_type]["phase"]
        if train_phase > self.current_phase:
            self.current_phase = train_phase

    def rust_trains(self, trigger_type: TrainType) -> list[Train]:
        """Rust all trains that should rust when trigger_type is bought."""
        rusted_trains = []
        for train in self.trains:
            if not train.rusted and train.should_rust(trigger_type):
                train.rust()
                rusted_trains.append(train)
        return rusted_trains

    def get_train_cost(self, train_type: TrainType) -> int:
        """Get the cost of a train type."""
        return TRAIN_DEFINITIONS[train_type]["cost"]
