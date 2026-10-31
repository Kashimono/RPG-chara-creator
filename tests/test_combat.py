import pytest

from RPG.core.game_state import GameState
from RPG.core.player import Player
from RPG.systems.combat.combat_manager import CombatActionError, CombatManager, CombatState
from RPG.systems.combat.enemy import EnemyDefinition


class FixedRandom:
    def __init__(self, chance=0.99, variation=1.0):
        self.chance = chance
        self.variation = variation

    def random(self):
        return self.chance

    def uniform(self, low, high):
        return min(high, max(low, self.variation))


def make_state(*, hp=1_000, attack=100, agility=0, stamina=0, current_hp=None):
    player = Player()
    player.character_created = True
    player.level = 1
    player.stats["HP"].current = hp
    player.stats["Attack"].current = attack
    player.stats["Agility"].current = agility
    player.stats["Stamina"].current = stamina
    if current_hp is not None:
        player.set_current_hp(current_hp)
    return GameState(player=player)


def definition(*, hp=1_000, attack=5, exp=10, interval=2.0, defense=0):
    return EnemyDefinition(
        "test", "Training Slime", hp, attack, exp, interval, physical_defense=defense,
    )


def manager_for(state, *, enemy=None, rng=None, respawn=2.0):
    return CombatManager(
        state,
        rng=rng or FixedRandom(),
        enemy_definitions=(enemy or definition(),),
        respawn_delay=respawn,
    )


def test_start_attack_cooldown_and_retreat():
    state = make_state()
    manager = manager_for(state)

    started = manager.start_combat(now=10)
    first = manager.attack(now=10)
    blocked = manager.attack(now=10.5)

    assert started.kind == "combat_started"
    assert first.kind == "player_hit"
    assert blocked.kind == "cooldown"
    assert state.combat_statistics.total_attacks_performed == 1
    assert manager.retreat().kind == "retreated"
    assert manager.state is CombatState.IDLE
    assert manager.tick(now=20).events == ()
    assert state.combat_statistics.total_damage_received == 0


def test_start_combat_rejects_missing_character_hp_attack_and_invalid_state():
    empty = GameState()
    with pytest.raises(CombatActionError, match="Create a character"):
        manager_for(empty).start_combat(now=0)

    no_hp = make_state(hp=0, attack=10)
    with pytest.raises(CombatActionError, match="HP"):
        manager_for(no_hp).start_combat(now=0)

    no_attack = make_state(hp=100, attack=0)
    with pytest.raises(CombatActionError, match="Attack"):
        manager_for(no_attack).start_combat(now=0)

    manager = manager_for(make_state())
    manager.start_combat(now=0)
    with pytest.raises(CombatActionError, match="idle"):
        manager.start_combat(now=0)


def test_attack_uses_cooldown_from_existing_attack_speed():
    state = make_state(agility=100_000)
    manager = manager_for(state)
    manager.start_combat(now=0)

    cooldown = manager.attack_cooldown_seconds()

    assert cooldown < 1
    assert manager.attack(now=0).kind == "player_hit"
    assert manager.attack(now=cooldown * 0.5).kind == "cooldown"
    assert manager.attack(now=cooldown + 0.01).kind == "player_hit"


def test_enemy_defeat_awards_exp_stats_levels_and_respawns_once():
    state = make_state(attack=100)
    manager = manager_for(state, enemy=definition(hp=1, exp=400), rng=FixedRandom())
    manager.start_combat(now=5)
    enemy_id = manager.current_enemy.enemy_id

    result = manager.attack(now=5)
    duplicate_tick = manager.tick(now=6)

    assert result.kind == "enemy_defeated"
    assert result.exp_reward == 400
    assert result.levels_gained == 2
    assert state.character.level == 3
    assert state.character.stat_points == 20
    assert state.combat_statistics.total_enemies_defeated == 1
    assert state.combat_statistics.total_exp_earned == 400
    assert manager.state is CombatState.ENEMY_DEFEATED
    assert manager.attack_cooldown_remaining(now=6) == 0
    with pytest.raises(CombatActionError, match="living enemy"):
        manager.attack(now=6)
    assert not duplicate_tick.events

    respawn = manager.tick(now=7)
    assert respawn.events[0].kind == "enemy_respawned"
    assert manager.state is CombatState.ACTIVE
    assert manager.current_enemy.current_hp == manager.current_enemy.max_hp
    assert manager.current_enemy.enemy_id != enemy_id
    assert manager.tick(now=7.1).events == ()


def test_critical_killing_blow_is_reported_and_counted():
    state = make_state(attack=100, agility=1_000)
    manager = manager_for(state, enemy=definition(hp=1), rng=FixedRandom(chance=0))
    manager.start_combat(now=0)

    result = manager.attack(now=0)

    assert result.critical
    assert result.kind == "enemy_defeated"
    assert "Critical hit!" in result.message
    assert state.combat_statistics.total_critical_hits == 1


def test_regeneration_does_not_catch_up_after_a_long_pause():
    state = make_state(hp=1_000, attack=10, stamina=100, current_hp=100)
    manager = manager_for(state, enemy=definition(interval=1_000))
    manager.start_combat(now=0)
    regen_per_second = state.character.calculated_attributes.hp_regeneration

    manager.tick(now=100)

    assert state.character.current_hp == pytest.approx(100 + regen_per_second * 0.25)


def test_enemy_attacks_periodically_and_physical_defense_is_counted():
    state = make_state(hp=10_000, attack=100, stamina=1_000)
    manager = manager_for(state, enemy=definition(attack=100, interval=1))
    manager.start_combat(now=0)
    before = state.character.current_hp

    early = manager.tick(now=0.99)
    hit = manager.tick(now=1)

    assert not early.events
    assert hit.events[0].kind == "enemy_hit"
    assert state.character.current_hp < before
    assert state.combat_statistics.total_damage_received == pytest.approx(hit.events[0].damage)
    assert hit.events[0].damage < 100


def test_player_defeat_stops_combat_until_recovery():
    state = make_state(hp=100, attack=10, current_hp=5)
    manager = manager_for(state, enemy=definition(attack=10_000, interval=1))
    manager.start_combat(now=0)

    result = manager.tick(now=1)

    assert result.events[-1].kind == "player_defeated"
    assert manager.state is CombatState.PLAYER_DEFEATED
    assert state.character.current_hp == 0
    assert manager.tick(now=20).events == ()
    with pytest.raises(CombatActionError, match="Recover"):
        manager.attack(now=20)

    recovered = manager.recover()
    assert recovered.kind == "recovered"
    assert manager.state is CombatState.IDLE
    assert state.character.current_hp == pytest.approx(state.character.maximum_hp * 0.5)
    manager.start_combat(now=21)


def test_hp_regeneration_and_current_hp_clamps_when_maximum_changes():
    state = make_state(hp=100, attack=10, stamina=100, current_hp=10)
    manager = manager_for(state, enemy=definition(interval=100))
    manager.start_combat(now=0)
    manager.tick(now=1)

    assert state.character.current_hp > 10
    old_max = state.character.maximum_hp
    state.character.set_current_hp(old_max)
    state.character.stats["HP"].current = 200

    assert state.character.maximum_hp > old_max
    assert state.character.current_hp == old_max

    state.character.stats["HP"].current = 1
    assert state.character.current_hp == state.character.maximum_hp


def test_saved_hp_and_combat_statistics_round_trip_and_v3_defaults():
    state = make_state(hp=100, attack=10, current_hp=25)
    state.record_player_attack(12.5, critical=True)
    state.record_damage_received(4)
    state.record_enemy_defeated(10)

    restored = GameState.from_dict(state.to_dict())
    old_save = state.to_dict()
    old_save["save_version"] = 3
    old_save.pop("combat_statistics")
    old_save["character"].pop("current_hp")
    migrated = GameState.from_dict(old_save)

    assert restored.character.current_hp == 25
    assert restored.combat_statistics.total_damage_dealt == 12.5
    assert restored.combat_statistics.total_damage_received == 4
    assert restored.combat_statistics.total_enemies_defeated == 1
    assert restored.combat_statistics.total_critical_hits == 1
    assert restored.combat_statistics.total_attacks_performed == 1
    assert restored.combat_statistics.total_exp_earned == 10
    assert migrated.character.current_hp == migrated.character.maximum_hp
    assert migrated.combat_statistics.total_attacks_performed == 0


def test_loaded_defeated_character_starts_in_recovery_without_active_enemy():
    state = make_state(hp=100, attack=10, current_hp=0)
    restored = GameState.from_dict(state.to_dict())
    manager = manager_for(restored)

    assert manager.state is CombatState.PLAYER_DEFEATED
    assert manager.current_enemy is None
    assert manager.recover().kind == "recovered"

