import pytest

from RPG.core.game_state import GameState
from RPG.systems.combat.enemy import Enemy, EnemyClassification
from RPG.systems.combat.enemy_database import EnemyDatabase
from RPG.systems.combat.boss_manager import BossManager
from RPG.systems.combat.loot_table import LootEntry, LootTable, LootTableDatabase
from RPG.systems.economy.economy_config import EconomyConfig
from RPG.systems.economy.reward_calculator import RewardCalculator
from RPG.systems.economy.reward_manager import RewardManager
from RPG.systems.economy.transaction import TransactionType


class FixedRandom:
    def random(self):
        return 0.0

    def randint(self, low, high):
        return low


@pytest.mark.parametrize(
    "enemy_id,classification",
    [
        ("slime", "common"),
        ("dire_wolf", "uncommon"),
        ("ogre", "rare"),
        ("ancient_guardian", "elite"),
        ("dragon_lord", "boss"),
        ("primordial_entity", "world_boss"),
    ],
)
def test_configured_reward_calculation_covers_all_enemy_classifications(enemy_id, classification):
    config = EconomyConfig.load_default()
    result = RewardCalculator(config).calculate(enemy_id, classification)
    assert result.final_gold == result.base_gold > 0
    assert result.classification_multiplier == 1.0


def test_reward_multipliers_are_centralized_and_round_half_up():
    config = EconomyConfig(
        enemy_gold_rewards={"test": 3},
        global_gold_multiplier=1.5,
        classification_gold_multipliers={"rare": 2},
        enemy_gold_multipliers={"test": 0.5},
    )
    result = RewardCalculator(config).calculate("test", "rare", temporary_multiplier=1.0)
    assert result.final_gold == 5
    assert result.multiplier_sources == (("global", 1.5), ("classification", 2.0), ("enemy", 0.5), ("temporary", 1.0))


@pytest.mark.parametrize("kwargs", [
    {"global_gold_multiplier": 0},
    {"global_gold_multiplier": float("nan")},
    {"global_gold_multiplier": -1},
    {"global_gold_multiplier": True},
])
def test_invalid_reward_multipliers_are_rejected(kwargs):
    with pytest.raises(ValueError, match="multiplier"):
        EconomyConfig(enemy_gold_rewards={}, **kwargs)


def test_unconfigured_enemy_and_unsafe_reward_are_rejected():
    calculator = RewardCalculator(EconomyConfig(enemy_gold_rewards={"test": 10}))
    with pytest.raises(ValueError, match="No base Gold"):
        calculator.calculate("missing", "common")
    huge = RewardCalculator(EconomyConfig(enemy_gold_rewards={"test": 10}, global_gold_multiplier=1e100))
    with pytest.raises(ValueError, match="safe integer"):
        huge.calculate("test", "common")


def test_invalid_multiplier_keys_and_duplicate_normalized_enemy_ids_are_rejected():
    with pytest.raises(ValueError, match="classification"):
        EconomyConfig(enemy_gold_rewards={}, classification_gold_multipliers={"mythic": 2})
    with pytest.raises(ValueError, match="configured base Gold"):
        EconomyConfig(enemy_gold_rewards={"known": 1}, enemy_gold_multipliers={"missing": 2})
    with pytest.raises(ValueError, match="Duplicate enemy reward ID"):
        EconomyConfig(enemy_gold_rewards={"slime": 1, "SLIME": 2})


def test_defeat_rewards_use_one_loot_roll_and_preserve_item_drops():
    definition = EnemyDatabase.load_default().get_by_id("slime")
    enemy = Enemy.spawn(definition)
    enemy.current_hp = 0
    loot = LootTableDatabase.from_tables([
        LootTable("common_drop", (
            LootEntry("gold_cache", 1, 2, 2, guaranteed=True, currency_type="gold"),
            LootEntry("relic", 1, guaranteed=True),
        )),
    ])
    config = EconomyConfig(enemy_gold_rewards={"slime": 9})
    state = GameState()
    state.character.character_created = True
    manager = RewardManager(config)
    kwargs = dict(loot_database=loot, loot_rng=FixedRandom(), claim_reward=enemy.claim_reward)

    summary = manager.process_defeat(state, enemy, **kwargs)
    duplicate = manager.process_defeat(state, enemy, **kwargs)

    assert summary is not None
    assert summary.guaranteed_gold == 9
    assert summary.bonus_gold == 2
    assert summary.total_gold_credited == 11
    assert summary.item_drops[0].reward_id == "relic"
    assert summary.currency_drops[0].currency_type == "gold"
    assert state.economy.gold.balance == 11
    assert state.combat_statistics.total_enemies_defeated == 1
    assert len(state.economy.transactions) == 2
    assert state.economy.transactions[0].transaction_type is TransactionType.ENEMY_REWARD
    assert state.economy.transactions[1].transaction_type is TransactionType.LOOT_CURRENCY_DROP
    assert duplicate is None


def test_default_enemy_gold_rewards_cover_entire_roster():
    config = EconomyConfig.load_default()
    ids = {definition.definition_id for definition in EnemyDatabase.load_default().list_enemies()}
    assert ids == set(config.enemy_gold_rewards)


@pytest.mark.parametrize(
    "enemy_id,expected_type",
    [
        ("dragon_lord", TransactionType.BOSS_REWARD),
        ("primordial_entity", TransactionType.WORLD_BOSS_REWARD),
    ],
)
def test_boss_and_world_boss_rewards_use_their_existing_claim_lifecycle(enemy_id, expected_type):
    definition = EnemyDatabase.load_default().get_by_id(enemy_id)
    enemy = Enemy.spawn(definition)
    enemy.current_hp = 0
    state = GameState()
    state.character.character_created = True
    manager = RewardManager(EconomyConfig(enemy_gold_rewards={enemy_id: 500}))
    summary = manager.process_defeat(
        state,
        enemy,
            loot_database=LootTableDatabase.from_tables([LootTable(definition.loot_table_id, ())]),
        loot_rng=FixedRandom(),
        claim_reward=lambda: BossManager().claim_defeat(enemy),
    )

    assert summary is not None and summary.total_gold_credited == 500
    assert state.economy.transactions[0].transaction_type is expected_type
