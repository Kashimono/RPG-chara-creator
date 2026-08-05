from typing import Any, Dict
from .stat import Stat
from .potential import PotentialRoller
from .leveling import LevelSystem
from ..constants import STAT_NAMES


class Player:
    """Tracks the player progression, stat state, and allocation rules."""

    def __init__(self) -> None:
        self.level = 0
        self.exp = LevelSystem.starting_exp()
        self.exp_to_next = LevelSystem.next_level_exp()
        self.stat_points = 0
        self.character_created = False
        self.stats: Dict[str, Stat] = {name: Stat(name) for name in STAT_NAMES}

    def reset(self) -> None:
        self.level = 0
        self.exp = LevelSystem.starting_exp()
        self.exp_to_next = LevelSystem.next_level_exp()
        self.stat_points = 0
        self.character_created = False
        self.stats = {name: Stat(name) for name in STAT_NAMES}

    def roll_stat_potential(self, stat_name: str) -> int:
        stat = self.stats[stat_name]
        if stat.accepted:
            raise ValueError(f"{stat_name} potential has already been accepted.")
        return PotentialRoller.roll(stat)

    def accept_stat_potential(self, stat_name: str) -> None:
        stat = self.stats[stat_name]
        if not PotentialRoller.can_accept(stat):
            return
        stat.accept_potential()
        if self.all_potentials_accepted and not self.character_created:
            self._initialize_character()

    def _initialize_character(self) -> None:
        self.level = LevelSystem.starting_level()
        self.exp = LevelSystem.starting_exp()
        self.exp_to_next = LevelSystem.next_level_exp()
        self.stat_points = 0
        self.character_created = True

    @property
    def all_potentials_accepted(self) -> bool:
        return all(stat.accepted for stat in self.stats.values())

    def level_up(self, times: int = 1) -> None:
        if not self.character_created:
            return
        self.level += times
        self.stat_points += LevelSystem.stat_points_for_levels(times)

    def can_allocate(self, stat_name: str, amount: int = 1) -> bool:
        if amount <= 0:
            return False
        stat = self.stats[stat_name]
        if not self.character_created or self.stat_points < amount or not stat.accepted:
            return False
        available_capacity = (stat.potential or 0) - stat.current
        return available_capacity >= amount

    def allocate_point(self, stat_name: str) -> bool:
        return self.allocate_points(stat_name, 1)

    def allocate_points(self, stat_name: str, amount: int) -> bool:
        if not self.can_allocate(stat_name, amount):
            return False
        stat = self.stats[stat_name]
        stat.current += amount
        self.stat_points -= amount
        return True

    def can_refund(self, stat_name: str) -> bool:
        stat = self.stats[stat_name]
        return stat.current > 0

    def refund_point(self, stat_name: str) -> bool:
        if not self.can_refund(stat_name):
            return False
        stat = self.stats[stat_name]
        stat.current -= 1
        self.stat_points += 1
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level,
            "exp": self.exp,
            "exp_to_next": self.exp_to_next,
            "stat_points": self.stat_points,
            "character_created": self.character_created,
            "stats": {name: stat.to_dict() for name, stat in self.stats.items()},
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        self.level = data.get("level", self.level)
        self.exp = data.get("exp", self.exp)
        self.exp_to_next = data.get("exp_to_next", self.exp_to_next)
        self.stat_points = data.get("stat_points", self.stat_points)
        self.character_created = data.get("character_created", self.character_created)

        self.stats = {
            name: Stat.from_dict(stat_data)
            for name, stat_data in data.get("stats", {}).items()
        }

        for stat_name in STAT_NAMES:
            if stat_name not in self.stats:
                self.stats[stat_name] = Stat(stat_name)

    def get_stat(self, stat_name: str) -> Stat:
        return self.stats[stat_name]

    def get_summary(self) -> dict:
        return {
            "level": self.level,
            "exp": self.exp,
            "exp_to_next": self.exp_to_next,
            "stat_points": self.stat_points,
            "character_created": self.character_created,
        }
