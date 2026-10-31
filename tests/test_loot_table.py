import json

import pytest

from RPG.systems.combat.loot_table import LootEntry, LootTable, LootTableDatabase, LootTableError


class FixedLootRandom:
    def __init__(self, rolls=(), quantities=()):
        self.rolls = iter(rolls)
        self.quantities = iter(quantities)

    def random(self):
        return next(self.rolls)

    def randint(self, low, high):
        return min(high, max(low, next(self.quantities)))


def test_rolls_guaranteed_and_successful_entries_with_quantities():
    table = LootTable("test", (
        LootEntry("shard", 0.5, 1, 3, rolls=2),
        LootEntry("trophy", 0.0, 1, 1, guaranteed=True),
    ))

    drops = table.roll(FixedLootRandom([0.4, 0.9], [1, 2]))

    assert [(drop.reward_id, drop.quantity, drop.guaranteed) for drop in drops] == [
        ("trophy", 1, True), ("shard", 2, False),
    ]


def test_failed_probability_roll_produces_no_drop():
    table = LootTable("test", (LootEntry("rare_item", 0.25),))
    assert table.roll(FixedLootRandom([0.8], [])) == ()


def test_invalid_probabilities_and_guaranteed_drop_limit_are_rejected():
    with pytest.raises(ValueError, match="between zero and one"):
        LootEntry("bad", 1.1)
    with pytest.raises(ValueError, match="suppress configured guaranteed"):
        LootTable("bad", (LootEntry("sure", 1, guaranteed=True, rolls=2),), max_drops=1)


def test_loader_and_missing_table_errors_are_readable(tmp_path):
    with pytest.raises(LootTableError, match="file is missing"):
        LootTableDatabase.load(tmp_path / "absent.json")

    path = tmp_path / "loot.json"
    path.write_text(json.dumps({"loot_tables": [{"table_id": "small", "entries": []}]}), encoding="utf-8")
    database = LootTableDatabase.load(path)
    assert database.has("small")
    with pytest.raises(LootTableError, match="Unknown loot table"):
        database.get_by_id("missing")

    path.write_text("{invalid", encoding="utf-8")
    with pytest.raises(LootTableError, match="Could not load loot tables"):
        LootTableDatabase.load(path)


def test_duplicate_loot_table_ids_are_detected_without_case_sensitivity():
    with pytest.raises(LootTableError, match="Duplicate loot table IDs"):
        LootTableDatabase.from_tables([LootTable("Small", ()), LootTable("small", ())])


def test_currency_entries_roll_and_same_reward_id_keeps_currency_separate_from_items():
    table = LootTable("mixed", (
        LootEntry("gold_cache", 1.0, 2, 2, guaranteed=True, currency_type="gold"),
        LootEntry("gold_cache", 1.0, 3, 3, guaranteed=True),
    ))

    drops = table.roll(FixedLootRandom([], [2, 3]))

    assert [(drop.reward_id, drop.quantity, drop.currency_type) for drop in drops] == [
        ("gold_cache", 2, "gold"),
        ("gold_cache", 3, None),
    ]


def test_unknown_currency_type_is_rejected_and_existing_tables_still_load():
    with pytest.raises(ValueError, match="unsupported currency"):
        LootEntry("bad", 1, currency_type="gems")
    database = LootTableDatabase.load_default()
    assert database.has("common_drop")
    assert any(entry.currency_type == "gold" for entry in database.get_by_id("world_boss_drop").entries)
