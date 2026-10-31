"""Data-driven race passives, character classes, and cosmetic titles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .race import Race


@dataclass(frozen=True)
class PassiveBonuses:
    hp_multiplier: float = 1.0
    mp_multiplier: float = 1.0
    attack_multiplier: float = 1.0
    agility_multiplier: float = 1.0
    stamina_multiplier: float = 1.0
    physical_defense_multiplier: float = 1.0
    magical_defense_multiplier: float = 1.0
    critical_chance_bonus: float = 0.0
    critical_damage_multiplier: float = 1.0
    attack_speed_multiplier: float = 1.0
    hp_regen_multiplier: float = 1.0
    mp_regen_multiplier: float = 1.0


DEFAULT_RACE_BONUSES = PassiveBonuses()

# Races use their rarity name as the default profile. Individual races can
# select a more specific key on Race.bonus_profile without changing roll logic.
RACE_BONUS_PROFILES: dict[str, PassiveBonuses] = {
    "default": DEFAULT_RACE_BONUSES,
    "common": PassiveBonuses(),
    "uncommon": PassiveBonuses(agility_multiplier=1.04, attack_multiplier=1.02),
    "rare": PassiveBonuses(stamina_multiplier=1.05, physical_defense_multiplier=1.08),
    "epic": PassiveBonuses(mp_multiplier=1.07, magical_defense_multiplier=1.10, mp_regen_multiplier=1.08),
    "legendary": PassiveBonuses(attack_multiplier=1.08, physical_defense_multiplier=1.06, critical_damage_multiplier=1.08),
    "mythical": PassiveBonuses(hp_multiplier=1.08, mp_multiplier=1.08, agility_multiplier=1.08, critical_chance_bonus=0.02),
    "primordial": PassiveBonuses(
        hp_multiplier=1.12,
        mp_multiplier=1.12,
        attack_multiplier=1.12,
        agility_multiplier=1.12,
        stamina_multiplier=1.12,
        physical_defense_multiplier=1.12,
        magical_defense_multiplier=1.12,
        critical_chance_bonus=0.03,
        critical_damage_multiplier=1.10,
        hp_regen_multiplier=1.10,
        mp_regen_multiplier=1.10,
    ),
    "verdant": PassiveBonuses(hp_multiplier=1.04, stamina_multiplier=1.06, hp_regen_multiplier=1.12),
    "arcane": PassiveBonuses(mp_multiplier=1.08, magical_defense_multiplier=1.08, mp_regen_multiplier=1.12),
    "draconic": PassiveBonuses(attack_multiplier=1.10, physical_defense_multiplier=1.05, critical_damage_multiplier=1.05),
    "phoenix": PassiveBonuses(hp_multiplier=1.10, critical_chance_bonus=0.02, hp_regen_multiplier=1.15),
    "world_first": PassiveBonuses(
        hp_multiplier=1.15,
        mp_multiplier=1.15,
        attack_multiplier=1.15,
        agility_multiplier=1.15,
        stamina_multiplier=1.15,
        physical_defense_multiplier=1.15,
        magical_defense_multiplier=1.15,
        critical_chance_bonus=0.04,
        critical_damage_multiplier=1.12,
        hp_regen_multiplier=1.12,
        mp_regen_multiplier=1.12,
    ),
}


@dataclass(frozen=True)
class ClassRequirements:
    minimum_level: int = 0
    requires_character_created: bool = False


@dataclass(frozen=True)
class CharacterClassDefinition:
    class_id: str
    name: str
    description: str
    icon: str
    specialization: str
    bonuses: PassiveBonuses
    requirements: ClassRequirements = ClassRequirements()


CLASS_DEFINITIONS: dict[str, CharacterClassDefinition] = {
    "warrior": CharacterClassDefinition(
        "warrior", "Warrior", "A frontline combatant with powerful strikes and steady defenses.", "W",
        "Attack and Physical Defense", PassiveBonuses(attack_multiplier=1.15, physical_defense_multiplier=1.15),
    ),
    "mage": CharacterClassDefinition(
        "mage", "Mage", "A focused scholar with deep reserves and strong magical resistance.", "M",
        "MP and Magical Defense", PassiveBonuses(mp_multiplier=1.15, magical_defense_multiplier=1.15, mp_regen_multiplier=1.08),
    ),
    "assassin": CharacterClassDefinition(
        "assassin", "Assassin", "A precise skirmisher who relies on speed and critical openings.", "A",
        "Agility and Critical Chance", PassiveBonuses(agility_multiplier=1.15, critical_chance_bonus=0.08, attack_speed_multiplier=1.08),
    ),
    "guardian": CharacterClassDefinition(
        "guardian", "Guardian", "A steadfast protector built to endure physical and magical threats.", "G",
        "HP and Defense", PassiveBonuses(hp_multiplier=1.18, stamina_multiplier=1.10, physical_defense_multiplier=1.10, magical_defense_multiplier=1.08),
    ),
    "ranger": CharacterClassDefinition(
        "ranger", "Ranger", "A versatile hunter balancing quick movement with decisive attacks.", "R",
        "Agility and Attack", PassiveBonuses(agility_multiplier=1.10, attack_multiplier=1.10, attack_speed_multiplier=1.05),
    ),
}


@dataclass(frozen=True)
class CharacterTitleDefinition:
    title_id: str
    name: str
    description: str
    minimum_level: int
    starting: bool = False


TITLE_DEFINITIONS: dict[str, CharacterTitleDefinition] = {
    "novice": CharacterTitleDefinition("novice", "Novice", "A new adventurer beginning their journey.", 1, starting=True),
    "apprentice": CharacterTitleDefinition("apprentice", "Apprentice", "A growing adventurer who has reached level 10.", 10),
    "veteran": CharacterTitleDefinition("veteran", "Veteran", "An experienced adventurer who has reached level 50.", 50),
    "elite": CharacterTitleDefinition("elite", "Elite", "A formidable adventurer who has reached level 100.", 100),
    "master": CharacterTitleDefinition("master", "Master", "A master of their craft who has reached level 250.", 250),
    "ascendant": CharacterTitleDefinition("ascendant", "Ascendant", "A peerless adventurer who has reached level 500.", 500),
}


def get_race_bonuses(race: Race | None) -> PassiveBonuses:
    if race is None:
        return DEFAULT_RACE_BONUSES
    profile = str(race.bonus_profile or race.rarity.value.lower()).strip().casefold()
    return RACE_BONUS_PROFILES.get(profile, DEFAULT_RACE_BONUSES)


def get_class_definition(class_id: str | None) -> CharacterClassDefinition | None:
    if class_id is None:
        return None
    normalized = str(class_id).strip().casefold()
    if normalized in CLASS_DEFINITIONS:
        return CLASS_DEFINITIONS[normalized]
    return next((item for item in CLASS_DEFINITIONS.values() if item.name.casefold() == normalized), None)


def get_title_definition(title_id: str | None) -> CharacterTitleDefinition | None:
    if title_id is None:
        return None
    normalized = str(title_id).strip().casefold()
    if normalized in TITLE_DEFINITIONS:
        return TITLE_DEFINITIONS[normalized]
    return next((item for item in TITLE_DEFINITIONS.values() if item.name.casefold() == normalized), None)
