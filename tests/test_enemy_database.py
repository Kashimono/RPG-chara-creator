import json

import pytest

from RPG.systems.combat.enemy import (
    CLASSIFICATION_DIFFICULTY_MULTIPLIERS,
    Enemy,
    EnemyClassification,
    EnemyDefinition,
    EnemyScaling,
)
from RPG.systems.combat.enemy_database import EnemyDatabase, EnemyDatabaseError


def _write_common(directory, rows):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "common.json").write_text(json.dumps({"enemies": rows}), encoding="utf-8")


def _row(enemy_id="test"):
    return {
        "enemy_id": enemy_id,
        "name": "Test Enemy",
        "classification": "common",
        "description": "A configured test creature.",
        "max_hp": 100,
        "attack": 10,
        "physical_defense": 4,
        "magical_defense": 2,
        "exp_reward": 20,
        "attack_interval": 2,
        "abilities": [],
    }


def test_default_database_loads_all_classifications_and_preserves_original_common_values():
    database = EnemyDatabase.load_default()

    assert len(database.list_enemies()) == 17
    assert [item.name for item in database.get_by_classification(EnemyClassification.COMMON)] == [
        "Slime", "Goblin", "Wolf", "Skeleton", "Orc",
    ]
    slime = database.get_by_id("SLIME")
    assert (slime.max_hp, slime.attack, slime.exp_reward, slime.attack_interval) == (100, 5, 10, 2.0)
    assert (slime.scaled_attributes(100).max_hp, slime.scaled_attributes(100).attack) == (100, 5)
    assert database.get_by_classification("World Boss")[0].definition_id == "primordial_entity"


def test_database_detects_case_insensitive_duplicate_ids(tmp_path):
    data_dir = tmp_path / "enemies"
    _write_common(data_dir, [_row("Goblin"), _row("goblin")])

    with pytest.raises(EnemyDatabaseError, match="Duplicate enemy ID"):
        EnemyDatabase.load(data_dir, ability_file=tmp_path / "missing_abilities.json")


def test_database_rejects_invalid_attributes_and_classification_mismatch(tmp_path):
    data_dir = tmp_path / "enemies"
    invalid = _row()
    invalid["max_hp"] = -1
    _write_common(data_dir, [invalid])
    with pytest.raises(EnemyDatabaseError, match="invalid HP"):
        EnemyDatabase.load(data_dir, ability_file=tmp_path / "missing_abilities.json")

    _write_common(data_dir, [{**_row(), "classification": "rare"}])
    with pytest.raises(EnemyDatabaseError, match="does not match common.json"):
        EnemyDatabase.load(data_dir, ability_file=tmp_path / "missing_abilities.json")


def test_database_reports_missing_directory_and_malformed_json(tmp_path):
    with pytest.raises(EnemyDatabaseError, match="directory is missing"):
        EnemyDatabase.load(tmp_path / "missing")

    data_dir = tmp_path / "enemies"
    data_dir.mkdir()
    (data_dir / "common.json").write_text("{not-json", encoding="utf-8")
    with pytest.raises(EnemyDatabaseError, match="Could not load enemy definitions"):
        EnemyDatabase.load(data_dir, ability_file=tmp_path / "missing_abilities.json")


def test_database_validates_loot_table_references():
    definition = EnemyDefinition("looter", "Looter", 1, 1, 0, 1, loot_table_id="missing_table")
    database = EnemyDatabase.from_definitions([definition])

    with pytest.raises(EnemyDatabaseError, match="references missing loot table 'missing_table'"):
        database.validate_loot_references({"common_drop"})


def test_scaling_uses_immutable_base_attributes_and_does_not_stack():
    definition = EnemyDefinition(
        "scaler", "Scaler", 100, 10, 50, 2,
        physical_defense=5,
        scaling=EnemyScaling(
            enabled=True, base_level=1, max_hp_per_level=0.1, attack_per_level=0.2,
            physical_defense_per_level=0.1, exp_per_level=0.1,
        ),
    )
    first = definition.scaled_attributes(6)
    second = definition.scaled_attributes(6)
    enemy = Enemy.spawn(definition, level=6)

    assert first == second
    assert (first.max_hp, first.attack, first.physical_defense, first.exp_reward) == (150, 20, 7.5, 75)
    assert enemy.max_hp == 150
    assert (definition.max_hp, definition.attack, definition.physical_defense, definition.exp_reward) == (100, 10, 5, 50)
    assert definition.scaled_attributes(100_000).max_hp < float("inf")


def test_disabled_scaling_keeps_base_values():
    definition = EnemyDefinition(
        "fixed", "Fixed", 100, 10, 50, 2,
        scaling=EnemyScaling(enabled=False, max_hp_per_level=0.5, attack_per_level=0.5, exp_per_level=0.5),
    )

    values = definition.scaled_attributes(500)

    assert (values.max_hp, values.attack, values.exp_reward) == (100, 10, 50)


def test_classification_and_enemy_difficulty_multipliers_are_centralized(monkeypatch):
    monkeypatch.setitem(CLASSIFICATION_DIFFICULTY_MULTIPLIERS, EnemyClassification.ELITE, 2.0)
    definition = EnemyDefinition(
        "tuned_elite", "Tuned Elite", 100, 10, 50, 2,
        classification=EnemyClassification.ELITE,
        difficulty_multiplier=1.5,
    )

    scaled = definition.scaled_attributes(1)

    assert (scaled.max_hp, scaled.attack, scaled.exp_reward) == (300, 30, 150)


def test_non_finite_scaled_result_is_rejected_instead_of_becoming_an_enemy():
    definition = EnemyDefinition(
        "extreme", "Extreme", 100, 10, 50, 2,
        scaling=EnemyScaling(max_hp_per_level=1e308),
    )

    with pytest.raises(ValueError, match="exceeds numeric limits"):
        definition.scaled_attributes(10)
