"""Deterministic-in-tests physical combat damage calculations."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Protocol

from ...core.game_config import MAX_CRITICAL_CHANCE
from ...core.stat_calculator import AttributeSheet
from . import combat_config
from .enemy import Enemy


class RandomSource(Protocol):
    def random(self) -> float: ...
    def uniform(self, a: float, b: float) -> float: ...


@dataclass(frozen=True)
class DamageResult:
    damage: float
    raw_damage: float
    critical: bool = False
    damage_reduction: float = 0.0
    variation: float = 1.0


def calculate_damage_reduction(defense: float) -> float:
    defense = max(0.0, float(defense))
    constant = combat_config.DEFENSE_MITIGATION_CONSTANT
    if constant <= 0:
        return 0.0
    return min(1.0, defense / (defense + constant))


def _mitigate(raw_damage: float, defense: float, variation: float, *, enforce_minimum: bool) -> DamageResult:
    raw_damage = max(0.0, float(raw_damage))
    reduction = calculate_damage_reduction(defense)
    damage = raw_damage * (1.0 - reduction)
    if enforce_minimum and raw_damage > 0:
        damage = max(combat_config.MINIMUM_DAMAGE, damage)
    return DamageResult(damage=damage, raw_damage=raw_damage, damage_reduction=reduction, variation=variation)


def calculate_player_damage(
    attributes: AttributeSheet,
    enemy: Enemy,
    rng: RandomSource | None = None,
) -> DamageResult:
    source = rng or random
    variation = source.uniform(combat_config.PLAYER_DAMAGE_VARIATION_MIN, combat_config.PLAYER_DAMAGE_VARIATION_MAX)
    base_damage = max(0.0, attributes.attack) * variation
    critical_chance = min(MAX_CRITICAL_CHANCE, max(0.0, attributes.critical_chance))
    critical = source.random() < critical_chance
    raw_damage = base_damage * (max(1.0, attributes.critical_damage) if critical else 1.0)
    result = _mitigate(raw_damage, enemy.physical_defense, variation, enforce_minimum=True)
    return DamageResult(
        damage=result.damage,
        raw_damage=raw_damage,
        critical=critical,
        damage_reduction=result.damage_reduction,
        variation=variation,
    )


def calculate_enemy_damage(
    attack: float,
    physical_defense: float,
    rng: RandomSource | None = None,
) -> DamageResult:
    source = rng or random
    variation = source.uniform(combat_config.ENEMY_DAMAGE_VARIATION_MIN, combat_config.ENEMY_DAMAGE_VARIATION_MAX)
    raw_damage = max(0.0, float(attack)) * variation
    result = _mitigate(raw_damage, physical_defense, variation, enforce_minimum=True)
    return result
