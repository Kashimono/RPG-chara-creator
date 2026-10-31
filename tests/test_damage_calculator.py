import pytest

from RPG.core.stat_calculator import AttributeSheet
from RPG.systems.combat.damage_calculator import (
    calculate_damage_reduction,
    calculate_enemy_damage,
    calculate_player_damage,
)
from RPG.systems.combat.enemy import Enemy, EnemyDefinition


class FixedRandom:
    def __init__(self, *, chance=0.99, variation=1.0):
        self.chance = chance
        self.variation = variation

    def random(self):
        return self.chance

    def uniform(self, low, high):
        assert low <= self.variation <= high
        return self.variation


def attributes(**overrides):
    values = dict(
        hp=100,
        mp=100,
        attack=100,
        agility=0,
        stamina=0,
        physical_defense=0,
        magical_defense=0,
        critical_chance=0,
        critical_damage=2,
        attack_speed=1,
        hp_regeneration=0,
        mp_regeneration=0,
    )
    values.update(overrides)
    return AttributeSheet(**values)


def enemy(defense=0):
    definition = EnemyDefinition("test", "Test", 100, 5, 1, 2.0, physical_defense=defense)
    return Enemy.spawn(definition)


def test_player_base_damage_and_variation_use_effective_attack():
    result = calculate_player_damage(attributes(attack=200), enemy(), FixedRandom(variation=1.1))

    assert result.raw_damage == pytest.approx(220)
    assert result.damage == pytest.approx(220)
    assert not result.critical


def test_critical_hit_uses_existing_chance_and_damage_attributes():
    result = calculate_player_damage(
        attributes(attack=100, critical_chance=0.75, critical_damage=2.5),
        enemy(),
        FixedRandom(chance=0.5),
    )

    assert result.critical
    assert result.raw_damage == pytest.approx(250)
    assert result.damage == pytest.approx(250)


def test_player_damage_is_reduced_by_enemy_physical_defense():
    result = calculate_player_damage(attributes(attack=100), enemy(defense=1_000), FixedRandom())

    assert result.damage_reduction == pytest.approx(0.5)
    assert result.damage == pytest.approx(50)


def test_enemy_damage_uses_player_physical_defense_and_configured_variation():
    result = calculate_enemy_damage(100, 1_000, FixedRandom(variation=0.9))

    assert result.raw_damage == pytest.approx(90)
    assert result.damage == pytest.approx(45)
    assert calculate_damage_reduction(1_000) == pytest.approx(0.5)


def test_minimum_damage_and_extreme_defense_are_safe():
    result = calculate_player_damage(attributes(attack=0.1), enemy(defense=1e300), FixedRandom())

    assert result.damage == 1
    assert calculate_damage_reduction(1e300) <= 1
    assert calculate_enemy_damage(0, 1e300, FixedRandom()).damage == 0

