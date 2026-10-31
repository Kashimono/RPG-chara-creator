import pytest

from RPG.systems.combat.enemy import Enemy, EnemyDefinition
from RPG.systems.combat.enemy_ability import (
    AbilityTrigger,
    EnemyAbilityDefinition,
    EnemyAbilityRuntime,
    EnemyAbilityType,
)


def ability(ability_id, kind, *, trigger=AbilityTrigger.ENEMY_ATTACK, cooldown=0, duration=0, threshold=None, **parameters):
    return EnemyAbilityDefinition(
        ability_id, ability_id.replace("_", " ").title(), "Test ability.", kind, trigger,
        cooldown_seconds=cooldown,
        duration_seconds=duration,
        activation_threshold=threshold,
        parameters=parameters,
    )


def enemy_with(*abilities):
    definition = EnemyDefinition("test", "Test Beast", 100, 20, 10, 1, physical_defense=10, abilities=tuple(abilities))
    return Enemy.spawn(definition)


def test_heavy_strike_uses_cooldown_and_adds_damage_multiplier():
    enemy = enemy_with(ability("heavy", EnemyAbilityType.HEAVY_STRIKE, cooldown=5, damage_multiplier=2.0))
    runtime = EnemyAbilityRuntime(enemy)

    profile, events = runtime.before_enemy_attack(0)
    blocked, no_events = runtime.before_enemy_attack(1)
    ready, ready_events = runtime.before_enemy_attack(5)

    assert profile.damage_multiplier == 2
    assert events[0].ability_id == "heavy"
    assert blocked.damage_multiplier == 1
    assert no_events == ()
    assert ready.ability.ability_id == "heavy"
    assert ready_events[0].name == "Heavy"


def test_enrage_activates_once_at_threshold_and_cleans_up():
    enemy = enemy_with(ability(
        "enrage", EnemyAbilityType.ENRAGE, trigger=AbilityTrigger.HP_THRESHOLD,
        threshold=0.5, attack_multiplier=1.8,
    ))
    runtime = EnemyAbilityRuntime(enemy)
    enemy.receive_damage(50)

    events = runtime.update(0)
    repeated = runtime.update(100)

    assert events[0].ability_id == "enrage"
    assert enemy.attack == pytest.approx(36)
    assert repeated == ()
    runtime.clear()
    assert enemy.attack == 20
    assert enemy.active_effect_names == ()


def test_defensive_stance_expires_after_configured_duration():
    enemy = enemy_with(ability(
        "guard", EnemyAbilityType.DEFENSIVE_STANCE, cooldown=10, duration=3,
        physical_defense_multiplier=2,
    ))
    runtime = EnemyAbilityRuntime(enemy)

    _, events = runtime.before_enemy_attack(4)
    assert events[0].ability_id == "guard"
    assert enemy.physical_defense == 20
    assert runtime.active_ability_names == ("Guard",)
    assert runtime.update(6) == ()
    expired = runtime.update(7)

    assert expired[0].message == "Guard has ended."
    assert enemy.physical_defense == 10


def test_regeneration_restores_configured_fraction_when_wounded():
    enemy = enemy_with(ability(
        "regeneration", EnemyAbilityType.REGENERATION, threshold=0.75, cooldown=8, heal_fraction=0.25,
    ))
    enemy.receive_damage(80)
    runtime = EnemyAbilityRuntime(enemy)

    _, events = runtime.before_enemy_attack(2)
    _, duplicate = runtime.before_enemy_attack(2)

    assert enemy.current_hp == 45
    assert "regenerates 25.0 HP" in events[0].message
    assert duplicate == ()


def test_piercing_strike_retains_configured_fraction_of_player_defense():
    enemy = enemy_with(ability(
        "pierce", EnemyAbilityType.PIERCING_STRIKE, cooldown=4,
        damage_multiplier=1.25, defense_effectiveness=0.4,
    ))
    runtime = EnemyAbilityRuntime(enemy)

    profile, _ = runtime.before_enemy_attack(0)

    assert profile.damage_multiplier == 1.25
    assert profile.defense_effectiveness == 0.4
    assert profile.defense_effectiveness >= 0.05


def test_invalid_ability_configuration_and_defeated_enemy_activation_are_rejected():
    with pytest.raises(ValueError, match="greater than one"):
        ability("bad", EnemyAbilityType.HEAVY_STRIKE, damage_multiplier=1)

    enemy = enemy_with(ability("heavy", EnemyAbilityType.HEAVY_STRIKE))
    enemy.receive_damage(100)
    profile, events = EnemyAbilityRuntime(enemy).before_enemy_attack(0)
    assert profile.damage_multiplier == 1
    assert events == ()
