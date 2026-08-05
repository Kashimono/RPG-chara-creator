from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class Rarity(Enum):
    COMMON = "Common"
    UNCOMMON = "Uncommon"
    RARE = "Rare"
    EPIC = "Epic"
    LEGENDARY = "Legendary"
    MYTHICAL = "Mythical"
    PRIMORDIAL = "Primordial"

    @classmethod
    def probability_table(cls) -> Dict["Rarity", float]:
        return {member: member.drop_rate_percent for member in cls}

    @classmethod
    def from_value(cls, value: Optional[str | "Rarity"]) -> "Rarity":
        if isinstance(value, cls):
            return value
        if not value:
            return cls.COMMON
        normalized = str(value).strip().lower()
        for member in cls:
            if member.value.lower() == normalized:
                return member
        return cls.COMMON

    @property
    def color_hex(self) -> str:
        colors = {
            self.COMMON: "#7f8c8d",
            self.UNCOMMON: "#4caf50",
            self.RARE: "#2e4b8b",
            self.EPIC: "#8b5cf6",
            self.LEGENDARY: "#d4af37",
            self.MYTHICAL: "#c8102e",
            self.PRIMORDIAL: "#000000",
        }
        return colors[self]

    @property
    def min_potential(self) -> int:
        values = {
            self.COMMON: 1,
            self.UNCOMMON: 100,
            self.RARE: 1_000,
            self.EPIC: 5_000,
            self.LEGENDARY: 100_000,
            self.MYTHICAL: 1_000_000,
            self.PRIMORDIAL: 10_000_000,
        }
        return values[self]

    @property
    def max_potential(self) -> int:
        values = {
            self.COMMON: 200,
            self.UNCOMMON: 1_000,
            self.RARE: 20_000,
            self.EPIC: 100_000,
            self.LEGENDARY: 1_000_000,
            self.MYTHICAL: 10_000_000,
            self.PRIMORDIAL: 1_000_000_000,
        }
        return values[self]

    @property
    def drop_rate_percent(self) -> float:
        return RARITY_DROP_RATES[self]

    @property
    def chance_weight(self) -> float:
        return self.drop_rate_percent


RARITY_DROP_RATES: Dict[Rarity, float] = {
    Rarity.COMMON: 60.0,
    Rarity.UNCOMMON: 25.0,
    Rarity.RARE: 10.0,
    Rarity.EPIC: 3.5,
    Rarity.LEGENDARY: 1.2,
    Rarity.MYTHICAL: 0.28,
    Rarity.PRIMORDIAL: 0.02,
}


@dataclass(frozen=True)
class Race:
    """Represents a playable race and the stat-potential range it grants."""

    name: str
    rarity: Rarity | str
    min_potential: int
    max_potential: int
    max_multiplier: int = 10
    text_color: str | None = None
    roll_chance: float = 0.0

    def __post_init__(self) -> None:
        if not isinstance(self.rarity, Rarity):
            object.__setattr__(self, "rarity", Rarity.from_value(self.rarity))
        if self.text_color is None:
            object.__setattr__(self, "text_color", self.rarity.color_hex)
        if self.min_potential == 0 and self.max_potential == 0:
            object.__setattr__(self, "min_potential", self.rarity.min_potential)
            object.__setattr__(self, "max_potential", self.rarity.max_potential)

    @property
    def rarity_name(self) -> str:
        return self.rarity.value

    @property
    def potential_range(self) -> str:
        return f"{self.min_potential:,} - {self.max_potential:,}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "rarity": self.rarity_name,
            "min_potential": self.min_potential,
            "max_potential": self.max_potential,
            "max_multiplier": self.max_multiplier,
            "text_color": self.text_color,
            "roll_chance": self.roll_chance,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Race":
        return cls(
            name=data.get("name", ""),
            rarity=data.get("rarity", Rarity.COMMON.value),
            min_potential=int(data.get("min_potential", 0)),
            max_potential=int(data.get("max_potential", 0)),
            max_multiplier=int(data.get("max_multiplier", 10)),
            text_color=data.get("text_color"),
            roll_chance=float(data.get("roll_chance", 0.0)),
        )


class RaceDatabase:
    """Stores every available race in the game."""

    def __init__(self) -> None:
        self._races = self._build_races()

    def _build_races(self) -> List[Race]:
        return [
            Race("Hearthfolk", Rarity.COMMON, 1, 200, 10),
            Race("Meadowkin", Rarity.COMMON, 1, 200, 10),
            Race("Riverborn", Rarity.COMMON, 1, 200, 10),
            Race("Mossstride", Rarity.COMMON, 1, 200, 10),
            Race("Orchardkin", Rarity.COMMON, 1, 200, 10),
            Race("Hollowmere", Rarity.COMMON, 1, 200, 10),
            Race("Thistledown", Rarity.COMMON, 1, 200, 10),
            Race("Briarfoot", Rarity.COMMON, 1, 200, 10),
            Race("Reedling", Rarity.COMMON, 1, 200, 10),
            Race("Stonehand", Rarity.COMMON, 1, 200, 10),
            Race("Ambervale", Rarity.COMMON, 1, 200, 10),
            Race("Cinderwick", Rarity.COMMON, 1, 200, 10),
            Race("Fenrunner", Rarity.COMMON, 1, 200, 10),
            Race("Willowmere", Rarity.COMMON, 1, 200, 10),
            Race("Rustfen", Rarity.COMMON, 1, 200, 10),
            Race("Brambleclan", Rarity.COMMON, 1, 200, 10),
            Race("Pinehollow", Rarity.COMMON, 1, 200, 10),
            Race("Moonfield", Rarity.COMMON, 1, 200, 10),
            Race("Embervale", Rarity.COMMON, 1, 200, 10),
            Race("Cliffreach", Rarity.COMMON, 1, 200, 10),
            Race("Marshstep", Rarity.COMMON, 1, 200, 10),
            Race("Duskroot", Rarity.COMMON, 1, 200, 10),
            Race("Sablebrook", Rarity.COMMON, 1, 200, 10),
            Race("Ashenvale", Rarity.COMMON, 1, 200, 10),
            Race("Tanglefoot", Rarity.COMMON, 1, 200, 10),
            Race("Larkspur", Rarity.COMMON, 1, 200, 10),
            Race("Cinderhollow", Rarity.COMMON, 1, 200, 10),
            Race("Rowanfolk", Rarity.COMMON, 1, 200, 10),
            Race("Claymarch", Rarity.COMMON, 1, 200, 10),
            Race("Mosswatch", Rarity.COMMON, 1, 200, 10),
            Race("Briarwisp", Rarity.UNCOMMON, 100, 1_000, 25),
            Race("Glasswing", Rarity.UNCOMMON, 100, 1_000, 25),
            Race("Thornveil", Rarity.UNCOMMON, 100, 1_000, 25),
            Race("Mistcaller", Rarity.UNCOMMON, 100, 1_000, 25),
            Race("Sunmoth", Rarity.UNCOMMON, 100, 1_000, 25),
            Race("Deepbloom", Rarity.UNCOMMON, 100, 1_000, 25),
            Race("Runebramble", Rarity.UNCOMMON, 100, 1_000, 25),
            Race("Hollowshade", Rarity.UNCOMMON, 100, 1_000, 25),
            Race("Gloamharvest", Rarity.UNCOMMON, 100, 1_000, 25),
            Race("Tideglass", Rarity.UNCOMMON, 100, 1_000, 25),
            Race("Starling", Rarity.UNCOMMON, 100, 1_000, 25),
            Race("Rivergale", Rarity.UNCOMMON, 100, 1_000, 25),
            Race("Cobaltroot", Rarity.UNCOMMON, 100, 1_000, 25),
            Race("Ashenbloom", Rarity.UNCOMMON, 100, 1_000, 25),
            Race("Wildspear", Rarity.UNCOMMON, 100, 1_000, 25),
            Race("Nightfern", Rarity.UNCOMMON, 100, 1_000, 25),
            Race("Hearthgale", Rarity.UNCOMMON, 100, 1_000, 25),
            Race("Moonreed", Rarity.UNCOMMON, 100, 1_000, 25),
            Race("Birchflame", Rarity.UNCOMMON, 100, 1_000, 25),
            Race("Hollowfern", Rarity.UNCOMMON, 100, 1_000, 25),
            Race("Sylvara", Rarity.RARE, 1_000, 20_000, 50),
            Race("Duskmarrow", Rarity.RARE, 1_000, 20_000, 50),
            Race("Ironbloom", Rarity.RARE, 1_000, 20_000, 50),
            Race("Froststep", Rarity.RARE, 1_000, 20_000, 50),
            Race("Sunforged", Rarity.RARE, 1_000, 20_000, 50),
            Race("Verdantheart", Rarity.RARE, 1_000, 20_000, 50),
            Race("Skycairn", Rarity.RARE, 1_000, 20_000, 50),
            Race("Thornwarden", Rarity.RARE, 1_000, 20_000, 50),
            Race("Emberglaive", Rarity.RARE, 1_000, 20_000, 50),
            Race("Moonvein", Rarity.RARE, 1_000, 20_000, 50),
            Race("Gildedroot", Rarity.RARE, 1_000, 20_000, 50),
            Race("Stormmantle", Rarity.RARE, 1_000, 20_000, 50),
            Race("Gravebranch", Rarity.RARE, 1_000, 20_000, 50),
            Race("Shiverhollow", Rarity.RARE, 1_000, 20_000, 50),
            Race("Rimebloom", Rarity.RARE, 1_000, 20_000, 50),
            Race("Wyrmkin", Rarity.EPIC, 5_000, 100_000, 100),
            Race("Starforged", Rarity.EPIC, 5_000, 100_000, 100),
            Race("Voidcaller", Rarity.EPIC, 5_000, 100_000, 100),
            Race("Aetherborne", Rarity.EPIC, 5_000, 100_000, 100),
            Race("Dawnclad", Rarity.EPIC, 5_000, 100_000, 100),
            Race("Obsidian Warden", Rarity.EPIC, 5_000, 100_000, 100),
            Race("Celestine Shade", Rarity.EPIC, 5_000, 100_000, 100),
            Race("Runecolossus", Rarity.EPIC, 5_000, 100_000, 100),
            Race("Stormbound Herald", Rarity.EPIC, 5_000, 100_000, 100),
            Race("Dragon Sovereign", Rarity.LEGENDARY, 100_000, 1_000_000, 250),
            Race("Sun Ascendant", Rarity.LEGENDARY, 100_000, 1_000_000, 250),
            Race("Moon Regent", Rarity.LEGENDARY, 100_000, 1_000_000, 250),
            Race("Worldshaper", Rarity.LEGENDARY, 100_000, 1_000_000, 250),
            Race("Tempest Emperor", Rarity.LEGENDARY, 100_000, 1_000_000, 250),
            Race("Phoenix Herald", Rarity.MYTHICAL, 1_000_000, 10_000_000, 500),
            Race("Abyssal Sovereign", Rarity.MYTHICAL, 1_000_000, 10_000_000, 500),
            Race("Celestial Choir", Rarity.MYTHICAL, 1_000_000, 10_000_000, 500),
            Race("Primordial Maw", Rarity.PRIMORDIAL, 10_000_000, 1_000_000_000, 1000),
            Race("World-First Spirit", Rarity.PRIMORDIAL, 10_000_000, 1_000_000_000, 1500),
        ]

    def get_all_races(self) -> List[Race]:
        return list(self._races)

    def get_races_by_rarity(self, rarity: Rarity | str) -> List[Race]:
        selected = Rarity.from_value(rarity)
        return [race for race in self._races if race.rarity is selected]


class RaceManager:
    """Chooses a race using the configured rarity weights."""

    @staticmethod
    def get_races() -> List[Race]:
        return RaceDatabase().get_all_races()

    @staticmethod
    def get_race_by_name(name: Optional[str]) -> Optional[Race]:
        if not name:
            return None
        for race in RaceManager.get_races():
            if race.name.lower() == name.lower():
                return race
        return None

    @staticmethod
    def roll_rarity() -> Rarity:
        return random.choices(
            population=list(Rarity),
            weights=[rarity.chance_weight for rarity in Rarity],
            k=1,
        )[0]

    @staticmethod
    def roll_race(required_rarity: Optional[Rarity] = None) -> Race:
        rarity = required_rarity or RaceManager.roll_rarity()
        races = RaceDatabase().get_races_by_rarity(rarity)
        return random.choice(races)
