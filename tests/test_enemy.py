import pytest

from RPG.systems.combat.enemy import Enemy, EnemyDefinition


def make_definition(**overrides):
    values = {
        "definition_id": "slime",
        "name": "Slime",
        "max_hp": 100,
        "attack": 5,
        "exp_reward": 10,
        "attack_interval": 2.0,
    }
    values.update(overrides)
    return EnemyDefinition(**values)


def test_enemy_starts_at_full_health_and_has_unique_instance_id():
    definition = make_definition()
    first = Enemy.spawn(definition)
    second = Enemy.spawn(definition)

    assert first.current_hp == first.max_hp == 100
    assert not first.is_defeated
    assert first.enemy_id != second.enemy_id


def test_enemy_damage_clamps_and_detects_defeat():
    enemy = Enemy.spawn(make_definition())

    assert enemy.receive_damage(35) == 35
    assert enemy.current_hp == 65
    assert enemy.receive_damage(500) == 65
    assert enemy.current_hp == 0
    assert enemy.is_defeated
    assert enemy.receive_damage(10) == 0


def test_enemy_reset_restores_health_and_rejects_negative_damage():
    enemy = Enemy.spawn(make_definition())
    enemy.receive_damage(100)
    enemy.reset()

    assert enemy.current_hp == 100
    with pytest.raises(ValueError, match="non-negative"):
        enemy.receive_damage(-1)

