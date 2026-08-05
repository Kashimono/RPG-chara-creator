from typing import Any, Dict, Optional
from .stat import Stat
from .potential import PotentialRoller
from .leveling import LevelSystem
from .race import Race, RaceManager, Rarity
from .race_pity import RacePityManager
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
        self.race: Optional[Race] = None
        self.race_accepted = False
        self.race_name: Optional[str] = None
        self.race_rarity: Optional[str] = None
        self.race_min_potential: Optional[int] = None
        self.race_max_potential: Optional[int] = None
        self.race_text_color: Optional[str] = None
        self.race_pity = RacePityManager()
        self._sync_stat_race_context()

    def reset(self) -> None:
        self.level = 0
        self.exp = LevelSystem.starting_exp()
        self.exp_to_next = LevelSystem.next_level_exp()
        self.stat_points = 0
        self.character_created = False
        self.stats = {name: Stat(name) for name in STAT_NAMES}
        self.race = None
        self.race_accepted = False
        self.race_name = None
        self.race_rarity = None
        self.race_min_potential = None
        self.race_max_potential = None
        self.race_text_color = None
        self.race_pity = RacePityManager()
        self._sync_stat_race_context()

    def roll_race(self) -> Race:
        base_rarity = RaceManager.roll_rarity()
        final_rarity = self.race_pity.resolve_rarity(base_rarity)
        self.race = RaceManager.roll_race(final_rarity)
        self.race_name = self.race.name
        self.race_rarity = self.race.rarity_name
        self.race_min_potential = self.race.min_potential
        self.race_max_potential = self.race.max_potential
        self.race_text_color = self.race.text_color
        self.race_accepted = False
        self._sync_stat_race_context()
        return self.race

    def set_preview_race(self, race: Race) -> None:
        self.race = race
        self.race_name = race.name
        self.race_rarity = race.rarity_name
        self.race_min_potential = race.min_potential
        self.race_max_potential = race.max_potential
        self.race_text_color = race.text_color
        self.race_accepted = False
        self._sync_stat_race_context()

    def accept_race(self) -> None:
        if self.race is None:
            return
        self.race_accepted = True
        self._sync_stat_race_context()

    def roll_stat_potential(self, stat_name: str) -> int:
        if not self.race_accepted or self.race is None:
            raise ValueError("You must accept a race before rolling stat potentials.")
        stat = self.stats[stat_name]
        if stat.accepted:
            raise ValueError(f"{stat_name} potential has already been accepted.")
        return PotentialRoller.roll(stat, self.race.min_potential, self.race.max_potential)

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

    @property
    def current_race_max_multiplier(self) -> int:
        if self.race is None:
            return 10
        return self.race.max_multiplier

    def _sync_stat_race_context(self) -> None:
        cap = self.current_race_max_multiplier
        for stat in self.stats.values():
            stat.set_race_multiplier_cap(cap)

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
            "race": self.race.to_dict() if self.race is not None else None,
            "race_accepted": self.race_accepted,
            "race_name": self.race_name,
            "race_rarity": self.race_rarity,
            "race_min_potential": self.race_min_potential,
            "race_max_potential": self.race_max_potential,
            "race_text_color": self.race_text_color,
            "race_pity": self.race_pity.to_dict(),
            "stats": {name: stat.to_dict() for name, stat in self.stats.items()},
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        self.level = data.get("level", self.level)
        self.exp = data.get("exp", self.exp)
        self.exp_to_next = data.get("exp_to_next", self.exp_to_next)
        self.stat_points = data.get("stat_points", self.stat_points)
        self.character_created = data.get("character_created", self.character_created)
        self.race_accepted = data.get("race_accepted", self.race_accepted)
        self.race_name = data.get("race_name", self.race_name)
        self.race_rarity = data.get("race_rarity", self.race_rarity)
        self.race_min_potential = data.get("race_min_potential", self.race_min_potential)
        self.race_max_potential = data.get("race_max_potential", self.race_max_potential)
        self.race_text_color = data.get("race_text_color", self.race_text_color)
        self.race_pity = RacePityManager.from_dict(data.get("race_pity", {}))

        race_data = data.get("race")
        if race_data:
            self.race = Race.from_dict(race_data)
        else:
            self.race = None if not self.race_name else RaceManager.get_race_by_name(self.race_name)

        self.stats = {
            name: Stat.from_dict(stat_data)
            for name, stat_data in data.get("stats", {}).items()
        }

        for stat_name in STAT_NAMES:
            if stat_name not in self.stats:
                self.stats[stat_name] = Stat(stat_name)
        self._sync_stat_race_context()

    def get_stat(self, stat_name: str) -> Stat:
        return self.stats[stat_name]

    def get_summary(self) -> dict:
        return {
            "level": self.level,
            "exp": self.exp,
            "exp_to_next": self.exp_to_next,
            "stat_points": self.stat_points,
            "character_created": self.character_created,
            "race_name": self.race_name,
            "race_rarity": self.race_rarity,
            "race_min_potential": self.race_min_potential,
            "race_max_potential": self.race_max_potential,
        }
