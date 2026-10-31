"""Pure calculations for primary and derived character attributes."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping

from .game_config import (
    ATTACK_SPEED_AGILITY_FACTOR,
    ATTACK_SPEED_AGILITY_SCALE,
    BASE_ATTACK_SPEED,
    BASE_CRITICAL_CHANCE,
    BASE_CRITICAL_DAMAGE,
    CRITICAL_AGILITY_SCALE,
    CRITICAL_ATTACK_SCALE,
    CRITICAL_CHANCE_AGILITY_FACTOR,
    HP_REGEN_HP_FACTOR,
    HP_REGEN_STAMINA_FACTOR,
    MAGICAL_DEFENSE_MP_FACTOR,
    MAGICAL_DEFENSE_STAMINA_FACTOR,
    MAX_ATTACK_SPEED,
    MAX_CRITICAL_CHANCE,
    MAX_CRITICAL_DAMAGE,
    MP_REGEN_MP_FACTOR,
    MP_REGEN_STAMINA_FACTOR,
    PHYSICAL_DEFENSE_ATTACK_FACTOR,
    PHYSICAL_DEFENSE_STAMINA_FACTOR,
)
from .progression_config import PassiveBonuses, get_class_definition, get_race_bonuses
from .race import Race
from .stat import Stat

@dataclass(frozen=True)
class AttributeSheet:
    hp: float
    mp: float
    attack: float
    agility: float
    stamina: float
    physical_defense: float
    magical_defense: float
    critical_chance: float
    critical_damage: float
    attack_speed: float
    hp_regeneration: float
    mp_regeneration: float

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


def _combined_bonuses(race: PassiveBonuses, character_class: PassiveBonuses) -> PassiveBonuses:
    multiplied_fields = (
        "hp_multiplier", "mp_multiplier", "attack_multiplier", "agility_multiplier",
        "stamina_multiplier", "physical_defense_multiplier", "magical_defense_multiplier",
        "critical_damage_multiplier", "attack_speed_multiplier", "hp_regen_multiplier", "mp_regen_multiplier",
    )
    values = {field: getattr(race, field) * getattr(character_class, field) for field in multiplied_fields}
    values["critical_chance_bonus"] = race.critical_chance_bonus + character_class.critical_chance_bonus
    return PassiveBonuses(**values)


def calculate_attributes(
    stats: Mapping[str, Stat],
    race: Race | None = None,
    class_id: str | None = None,
) -> AttributeSheet:
    """Calculate effective primary stats and combat-ready derived values.

    Primary values start from the existing Stat.effective_value calculation.
    Passive multipliers are applied to that result exactly once, at read time.
    """
    class_definition = get_class_definition(class_id)
    class_bonuses = class_definition.bonuses if class_definition else PassiveBonuses()
    bonuses = _combined_bonuses(get_race_bonuses(race), class_bonuses)

    def primary(name: str, multiplier: float) -> float:
        return max(0.0, stats[name].effective_value * multiplier)

    hp = primary("HP", bonuses.hp_multiplier)
    mp = primary("MP", bonuses.mp_multiplier)
    attack = primary("Attack", bonuses.attack_multiplier)
    agility = primary("Agility", bonuses.agility_multiplier)
    stamina = primary("Stamina", bonuses.stamina_multiplier)

    physical_defense = max(
        0.0,
        (stamina * PHYSICAL_DEFENSE_STAMINA_FACTOR + attack * PHYSICAL_DEFENSE_ATTACK_FACTOR)
        * bonuses.physical_defense_multiplier,
    )
    magical_defense = max(
        0.0,
        (mp * MAGICAL_DEFENSE_MP_FACTOR + stamina * MAGICAL_DEFENSE_STAMINA_FACTOR)
        * bonuses.magical_defense_multiplier,
    )
    critical_chance = min(
        MAX_CRITICAL_CHANCE,
        max(
            0.0,
            BASE_CRITICAL_CHANCE
            + CRITICAL_CHANCE_AGILITY_FACTOR * agility / (agility + CRITICAL_AGILITY_SCALE)
            + bonuses.critical_chance_bonus,
        ),
    )
    critical_damage = min(
        MAX_CRITICAL_DAMAGE,
        max(BASE_CRITICAL_DAMAGE, (BASE_CRITICAL_DAMAGE + attack / (attack + CRITICAL_ATTACK_SCALE)) * bonuses.critical_damage_multiplier),
    )
    attack_speed = min(
        MAX_ATTACK_SPEED,
        max(
            BASE_ATTACK_SPEED,
            (BASE_ATTACK_SPEED + ATTACK_SPEED_AGILITY_FACTOR * agility / (agility + ATTACK_SPEED_AGILITY_SCALE))
            * bonuses.attack_speed_multiplier,
        ),
    )
    hp_regeneration = max(
        0.0,
        (stamina * HP_REGEN_STAMINA_FACTOR + hp * HP_REGEN_HP_FACTOR) * bonuses.hp_regen_multiplier,
    )
    mp_regeneration = max(
        0.0,
        (mp * MP_REGEN_MP_FACTOR + stamina * MP_REGEN_STAMINA_FACTOR) * bonuses.mp_regen_multiplier,
    )

    return AttributeSheet(
        hp=round(hp, 2),
        mp=round(mp, 2),
        attack=round(attack, 2),
        agility=round(agility, 2),
        stamina=round(stamina, 2),
        physical_defense=round(physical_defense, 2),
        magical_defense=round(magical_defense, 2),
        critical_chance=round(critical_chance, 4),
        critical_damage=round(critical_damage, 4),
        attack_speed=round(attack_speed, 4),
        hp_regeneration=round(hp_regeneration, 2),
        mp_regeneration=round(mp_regeneration, 2),
    )
