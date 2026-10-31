from typing import Any, Dict, Optional
from .stat import Stat
from .potential import PotentialRoller
from .leveling import LevelSystem
from .race import Race, RaceManager, Rarity
from .race_pity import RacePityManager
from .progression_config import (
    TITLE_DEFINITIONS,
    CharacterClassDefinition,
    get_class_definition,
    get_title_definition,
)
from .stat_calculator import AttributeSheet, calculate_attributes
from ..constants import STAT_NAMES


class Player:
    """Tracks the player progression, stat state, and allocation rules."""

    def __init__(self) -> None:
        self.character_name = "Adventurer"
        self.level = 0
        self.exp = LevelSystem.starting_exp()
        self.exp_to_next = LevelSystem.next_level_exp(self.level)
        self.stat_points = 0
        self.character_created = False
        self.class_id: Optional[str] = None
        self.unlocked_titles = ["novice"]
        self.equipped_title = "novice"
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
        self.character_name = "Adventurer"
        self.level = 0
        self.exp = LevelSystem.starting_exp()
        self.exp_to_next = LevelSystem.next_level_exp(self.level)
        self.stat_points = 0
        self.character_created = False
        self.class_id = None
        self.unlocked_titles = ["novice"]
        self.equipped_title = "novice"
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
        self.exp_to_next = LevelSystem.next_level_exp(self.level)
        self.stat_points = 0
        self.character_created = True
        self._unlock_titles_for_level()

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
        if isinstance(times, bool) or not isinstance(times, int) or times <= 0:
            raise ValueError("Level count must be a positive whole number.")
        self.level += times
        self.stat_points += LevelSystem.stat_points_for_levels(times)
        self.exp_to_next = LevelSystem.required_exp(self.level)
        self._unlock_titles_for_level()

    def gain_exp(self, amount: int) -> int:
        """Add EXP, return levels gained, and preserve any EXP overflow."""
        if not self.character_created:
            raise ValueError("Create a character before gaining EXP.")
        if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
            raise ValueError("EXP gain must be a positive whole number.")

        self.exp += amount
        levels_gained = 0
        self.exp_to_next = LevelSystem.required_exp(self.level)
        while self.exp >= self.exp_to_next:
            self.exp -= self.exp_to_next
            self.level += 1
            self.stat_points += LevelSystem.stat_points_for_levels(1)
            levels_gained += 1
            self.exp_to_next = LevelSystem.required_exp(self.level)
        if levels_gained:
            self._unlock_titles_for_level()
        return levels_gained

    def select_class(self, class_id: str | None) -> None:
        """Select a configured class, or clear the selection with ``None``."""
        if class_id is None or not str(class_id).strip():
            self.class_id = None
            return
        definition = get_class_definition(class_id)
        if definition is None:
            raise ValueError(f"Unknown character class: {class_id}")
        requirements = definition.requirements
        if self.level < requirements.minimum_level:
            raise ValueError(f"{definition.name} requires level {requirements.minimum_level}.")
        if requirements.requires_character_created and not self.character_created:
            raise ValueError(f"{definition.name} requires a completed character.")
        self.class_id = definition.class_id

    def equip_title(self, title_id: str) -> None:
        definition = get_title_definition(title_id)
        normalized_id = definition.title_id if definition else str(title_id).strip().casefold()
        if definition is None or normalized_id not in self.unlocked_titles:
            raise ValueError("You can only equip a title that has been unlocked.")
        self.equipped_title = normalized_id

    def _unlock_titles_for_level(self) -> None:
        unlocked = set(self.unlocked_titles)
        for title in TITLE_DEFINITIONS.values():
            if title.starting or self.level >= title.minimum_level:
                unlocked.add(title.title_id)
        self.unlocked_titles = [title_id for title_id in TITLE_DEFINITIONS if title_id in unlocked]

    @property
    def equipped_title_name(self) -> str:
        title = get_title_definition(self.equipped_title)
        return title.name if title else "Novice"

    @property
    def selected_class(self) -> CharacterClassDefinition | None:
        return get_class_definition(self.class_id)

    @property
    def calculated_attributes(self) -> AttributeSheet:
        active_race = self.race if self.race_accepted else None
        return calculate_attributes(self.stats, active_race, self.class_id)

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
            "character_name": self.character_name,
            "level": self.level,
            "exp": self.exp,
            "stat_points": self.stat_points,
            "character_created": self.character_created,
            "class_id": self.class_id,
            "unlocked_titles": list(self.unlocked_titles),
            "equipped_title": self.equipped_title,
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
        self.character_name = data.get("character_name", self.character_name)
        self.level = data.get("level", self.level)
        self.exp = data.get("exp", self.exp)
        # Old saves stored a fixed EXP threshold. Recalculate it from level.
        self.exp_to_next = LevelSystem.required_exp(self.level)
        self.stat_points = data.get("stat_points", self.stat_points)
        self.character_created = data.get("character_created", self.character_created)
        raw_class = data.get("class_id")
        class_definition = get_class_definition(raw_class)
        self.class_id = class_definition.class_id if class_definition else None
        raw_titles = data.get("unlocked_titles", ["novice"])
        if isinstance(raw_titles, (list, tuple, set)):
            self.unlocked_titles = list(dict.fromkeys(
                definition.title_id
                for item in raw_titles
                if (definition := get_title_definition(str(item))) is not None
            ))
        else:
            self.unlocked_titles = ["novice"]
        if "novice" not in self.unlocked_titles:
            self.unlocked_titles.insert(0, "novice")
        requested_title = get_title_definition(data.get("equipped_title", "novice"))
        self.equipped_title = requested_title.title_id if requested_title else "novice"
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
        self._unlock_titles_for_level()
        if self.equipped_title not in self.unlocked_titles:
            self.equipped_title = "novice"
        if self.character_created:
            self._apply_saved_exp_overflow()

    def _apply_saved_exp_overflow(self) -> None:
        self.exp = max(0, int(self.exp))
        self.exp_to_next = LevelSystem.required_exp(self.level)
        while self.exp >= self.exp_to_next:
            self.exp -= self.exp_to_next
            self.level += 1
            self.stat_points += LevelSystem.stat_points_for_levels(1)
            self.exp_to_next = LevelSystem.required_exp(self.level)
        self._unlock_titles_for_level()

    def get_stat(self, stat_name: str) -> Stat:
        return self.stats[stat_name]

    def get_character_profile(self) -> Dict[str, Any]:
        race_name = self.race.name if self.race is not None else self.race_name
        race_rarity = self.race.rarity_name if self.race is not None else self.race_rarity
        return {
            "race": race_name or "Unknown",
            "rarity": race_rarity or "Unknown",
            "level": self.level,
            "stats": {name: self.stats[name].current for name in STAT_NAMES},
        }

    def get_summary(self) -> dict:
        return {
            "character_name": self.character_name,
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
