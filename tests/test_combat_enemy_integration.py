import pytest

from RPG.core.game_state import GameState
from RPG.core.player import Player
from RPG.systems.combat.combat_manager import CombatActionError, CombatManager, CombatState
from RPG.systems.combat.enemy import EnemyClassification, EnemyDefinition
from RPG.systems.combat.enemy_ability import EnemyAbilityDefinition, EnemyAbilityType
from RPG.systems.combat.enemy_database import EnemyDatabase
from RPG.systems.combat.loot_table import LootTableDatabase


class FixedRandom:
    def random(self):
        return 0.99

    def uniform(self, low, high):
        return 1.0


class GuaranteedLootRandom:
    def random(self):
        return 0.0

    def randint(self, low, high):
        return low


def game_state(*, attack=100, hp=100_000):
    player = Player()
    player.character_created = True
    player.level = 1
    player.stats["HP"].current = hp
    player.stats["Attack"].current = attack
    return GameState(player=player)


def test_database_selected_elite_awards_rewards_and_records_classification():
    state = game_state(attack=10_000_000)
    manager = CombatManager(state, rng=FixedRandom(), loot_rng=GuaranteedLootRandom())

    with pytest.raises(CombatActionError, match="dedicated start action"):
        manager.start_combat("ancient_guardian", now=0)
    started = manager.start_elite_encounter("ancient_guardian", now=0)
    defeated = manager.attack(now=0)

    assert started.kind == "elite_encounter_started"
    assert defeated.kind == "elite_defeated"
    assert defeated.exp_reward > 0
    assert defeated.reward_summary is not None
    assert defeated.reward_summary.guaranteed_gold == 350
    assert defeated.reward_summary.total_gold_credited >= 350
    assert state.economy.gold.balance == defeated.reward_summary.total_gold_credited
    assert any(drop.reward_id == "monster_essence" for drop in defeated.drops)
    assert state.combat_statistics.total_elites_defeated == 1
    assert manager.state is CombatState.IDLE


def test_boss_challenge_is_dedicated_and_emits_structured_loot_once():
    state = game_state(attack=10_000_000)
    manager = CombatManager(state, rng=FixedRandom(), loot_rng=GuaranteedLootRandom())

    manager.challenge_boss("dragon_lord", now=5)
    with pytest.raises(CombatActionError, match="idle"):
        manager.start_combat(now=5)
    defeated = manager.attack(now=5)

    assert defeated.kind == "boss_defeated"
    assert {drop.reward_id for drop in defeated.drops} >= {"boss_trophy", "ancient_shard"}
    assert "Loot:" in defeated.message
    assert defeated.reward_summary is not None
    assert defeated.reward_summary.guaranteed_gold == 3_000
    assert defeated.reward_summary.total_gold_credited >= 3_000
    assert any(drop.currency_type == "gold" for drop in defeated.drops)
    assert state.combat_statistics.total_bosses_defeated == 1
    assert state.combat_statistics.total_enemies_defeated == 1
    assert manager.state is CombatState.IDLE


def test_enemy_ability_uses_existing_mitigation_and_cleans_up_on_retreat():
    heavy = EnemyAbilityDefinition(
        "heavy_strike", "Heavy Strike", "A stronger physical hit.",
        EnemyAbilityType.HEAVY_STRIKE, "enemy_attack", cooldown_seconds=5,
        parameters={"damage_multiplier": 2.0},
    )
    definition = EnemyDefinition(
        "training_beast", "Training Beast", 1_000, 20, 10, 1,
        classification=EnemyClassification.COMMON, abilities=(heavy,),
    )
    state = game_state(attack=1)
    manager = CombatManager(
        state,
        rng=FixedRandom(),
        enemy_definitions=(definition,),
        loot_database=LootTableDatabase.from_tables([]),
    )
    manager.start_combat(now=0)

    tick = manager.tick(now=1)
    manager.retreat()

    assert tick.events[0].kind == "ability_activated"
    assert tick.events[0].message == "Training Beast uses Heavy Strike!"
    assert tick.events[1].kind == "enemy_hit"
    assert 39 < tick.events[1].damage < 40
    assert manager.active_ability_names == ()
    assert manager.current_enemy is None
