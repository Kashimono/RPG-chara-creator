"""Skill damage and magnitude calculations using existing combat attributes."""

from __future__ import annotations

import random
from typing import Protocol

from ...core.game_config import MAX_CRITICAL_CHANCE
from ...core.stat_calculator import AttributeSheet
from ..combat.damage_calculator import DamageResult, _mitigate
from ..combat.enemy import Enemy
from .skill import SkillEffect


class SkillRandomSource(Protocol):
    def random(self) -> float: ...
    def uniform(self, a: float, b: float) -> float: ...


def effect_magnitude(attributes: AttributeSheet, effect: SkillEffect, skill_level: int = 1) -> float:
    if isinstance(skill_level, bool) or not isinstance(skill_level, int) or skill_level < 1:
        raise ValueError("Skill level must be a positive integer.")
    values = attributes.to_dict()
    raw = effect.magnitude + sum(max(0.0, values.get(name, 0.0)) * coefficient for name, coefficient in effect.scaling.items())
    return max(0.0, raw * (1.0 + 0.15 * (skill_level - 1)))


def calculate_skill_damage(
    attributes: AttributeSheet,
    enemy: Enemy,
    effect: SkillEffect,
    skill_level: int = 1,
    *,
    critical_eligible: bool = False,
    rng: SkillRandomSource | None = None,
) -> DamageResult:
    if effect.kind != "damage":
        raise ValueError("Skill damage calculation requires a damage effect.")
    source = rng or random
    variation = source.uniform(0.95, 1.05)
    raw = effect_magnitude(attributes, effect, skill_level) * variation
    chance = min(MAX_CRITICAL_CHANCE, max(0.0, attributes.critical_chance)) if critical_eligible else 0.0
    critical = source.random() < chance
    if critical:
        raw *= max(1.0, attributes.critical_damage)
    defense = enemy.physical_defense if effect.damage_type == "physical" else enemy.magical_defense
    result = _mitigate(raw, defense, variation, enforce_minimum=True)
    return DamageResult(result.damage, raw, critical, result.damage_reduction, variation)
