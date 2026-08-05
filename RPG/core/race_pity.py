from __future__ import annotations

from .race import Rarity, Race


class RacePityManager:
    """Handles pity counters and guaranteed minimum-rarity checks for race rolls."""

    MYTHICAL_INTERVAL = 100
    PRIMORDIAL_INTERVAL = 1000

    def __init__(self) -> None:
        self.total_race_rolls = 0
        self.mythical_pity_counter = 0
        self.primordial_pity_counter = 0

    def resolve_rarity(self, base_rarity: Rarity) -> Rarity:
        self.total_race_rolls += 1
        self.mythical_pity_counter += 1
        self.primordial_pity_counter += 1

        if self.primordial_pity_counter >= self.PRIMORDIAL_INTERVAL:
            self.reset_mythical_pity()
            self.reset_primordial_pity()
            return Rarity.PRIMORDIAL

        if self.mythical_pity_counter >= self.MYTHICAL_INTERVAL:
            self.reset_mythical_pity()
            if base_rarity is Rarity.PRIMORDIAL:
                self.reset_primordial_pity()
                return Rarity.PRIMORDIAL
            return Rarity.MYTHICAL

        return base_rarity

    def reset_mythical_pity(self) -> None:
        self.mythical_pity_counter = 0

    def reset_primordial_pity(self) -> None:
        self.primordial_pity_counter = 0

    def to_dict(self) -> dict:
        return {
            "total_race_rolls": self.total_race_rolls,
            "mythical_pity_counter": self.mythical_pity_counter,
            "primordial_pity_counter": self.primordial_pity_counter,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RacePityManager":
        manager = cls()
        manager.total_race_rolls = int(data.get("total_race_rolls", 0))
        manager.mythical_pity_counter = int(data.get("mythical_pity_counter", 0))
        manager.primordial_pity_counter = int(data.get("primordial_pity_counter", 0))
        return manager
