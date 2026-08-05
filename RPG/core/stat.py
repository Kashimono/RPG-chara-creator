from __future__ import annotations
import random
from typing import Any, Dict, Optional
from ..constants import MAX_POTENTIAL_ROLLS
from .multiplier import StatMultiplier


class Stat:
    """Represents a single stat with current value and potential."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.current = 0
        self.potential: Optional[int] = None
        self.roll_value: Optional[int] = None
        self.roll_attempts = 0
        self.accepted = False
        self._race_multiplier_cap = 10.0

    @property
    def max_rolls(self) -> int:
        return MAX_POTENTIAL_ROLLS

    @property
    def can_roll(self) -> bool:
        return not self.accepted and self.roll_attempts < self.max_rolls

    def roll_potential(self, min_potential: int, max_potential: int) -> int:
        if not self.can_roll:
            raise ValueError(f"{self.name} has reached the maximum roll limit.")
        self.roll_attempts += 1
        self.roll_value = random.randint(min_potential, max_potential)
        return self.roll_value

    def accept_potential(self) -> None:
        if self.roll_value is None:
            raise ValueError("Cannot accept potential before rolling.")
        self.potential = self.roll_value
        self.accepted = True

    @property
    def can_allocate(self) -> bool:
        return self.accepted and self.current < (self.potential or 0)

    @property
    def multiplier(self) -> float:
        return StatMultiplier.compute(self.current, self.max_multiplier)

    def set_race_multiplier_cap(self, max_multiplier: float | None) -> None:
        self._race_multiplier_cap = float(max_multiplier or 10.0)

    @property
    def max_multiplier(self) -> float:
        return self._race_multiplier_cap

    @property
    def effective_value(self) -> float:
        return round(self.current * self.multiplier, 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "current": self.current,
            "potential": self.potential,
            "roll_value": self.roll_value,
            "accepted": self.accepted,
            "roll_attempts": self.roll_attempts,
            "multiplier": self.multiplier,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Stat":
        stat = cls(data.get("name", ""))
        stat.current = data.get("current", 0)
        stat.potential = data.get("potential")
        stat.roll_value = data.get("roll_value")
        stat.accepted = data.get("accepted", False)
        stat.roll_attempts = data.get("roll_attempts", 0)
        return stat
