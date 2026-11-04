import json

import pytest

from RPG.core.game_state import GameState
from RPG.core.player import Player
from RPG.core.stat_calculator import AttributeSheet
from RPG.systems.combat.combat_manager import CombatActionError, CombatManager
from RPG.systems.combat.enemy import BossPhaseDefinition, Enemy, EnemyClassification, EnemyDefinition
from RPG.systems.combat.status_effect_manager import StatusEffectManager
from RPG.systems.economy.economy_manager import EconomyManager
from RPG.systems.skills.skill import SkillDefinition, SkillEffect
from RPG.systems.skills.skill_calculator import calculate_skill_damage, effect_magnitude
from RPG.systems.skills.skill_database import SkillDatabase, SkillDatabaseError
from RPG.systems.skills.skill_manager import SkillActionError, SkillManager


class FixedRandom:
    def __init__(self, chance=0.99, variation=1.0):
        self.chance = chance
        self.variation = variation

    def random(self):
        return self.chance

    def uniform(self, low, high):
        return min(high, max(low, self.variation))


def make_state(*, hp=1_000, mp=100, attack=100, current_mp=None, level=10):
    player = Player()
    player.character_created = True
    player.level = level
    player.stats["HP"].current = hp
    player.stats["MP"].current = mp
    player.stats["Attack"].current = attack
    if current_mp is not None:
        player.set_current_mp(current_mp)
    return GameState(player=player)


def enemy(hp=10_000, *, classification=EnemyClassification.COMMON, physical=0, magical=0):
    phases = (BossPhaseDefinition("opening", "Opening", 1.0),) if classification in {EnemyClassification.BOSS, EnemyClassification.WORLD_BOSS} else ()
    return Enemy.spawn(EnemyDefinition("training", "Training Dummy", hp, 0, 1, 2.0,
                                       physical_defense=physical, magical_defense=magical,
                                       classification=classification, boss_phases=phases))


def combat_manager(state, target=None):
    return CombatManager(state, rng=FixedRandom(), enemy_definitions=(
        target.definition if target else EnemyDefinition("training", "Training Dummy", 10_000, 0, 1, 2.0),
    ))


def test_default_database_has_all_classifications_and_seventeen_skills():
    database = SkillDatabase.load_default()

    assert len(database.list_skills()) == 17
    assert {skill.classification for skill in database.list_skills()} == {"physical", "magical", "defensive", "support"}
    assert database.get("POWER_STRIKE").name == "Power Strike"
    assert len(database.by_classification("support")) >= 3


def test_database_rejects_duplicate_and_malformed_definitions(tmp_path):
    skill = {
        "id": "sample", "name": "Sample", "description": "A sample skill.", "classification": "physical", "type": "damage",
        "effects": [{"kind": "damage", "scaling": {"attack": 1}}],
    }
    path = tmp_path / "skills.json"
    path.write_text(json.dumps({"skills": [skill, skill]}), encoding="utf-8")
    with pytest.raises(SkillDatabaseError, match="Duplicate skill ID"):
        SkillDatabase.from_files([path])
    path.write_text("{broken", encoding="utf-8")
    with pytest.raises(SkillDatabaseError, match="Could not load"):
        SkillDatabase.from_files([path])
    path.write_text(json.dumps({"skills": [{**skill, "classification": "unknown"}]}), encoding="utf-8")
    with pytest.raises(SkillDatabaseError, match="unsupported classification"):
        SkillDatabase.from_files([path])


def test_current_mp_boundaries_consumption_restoration_and_equipment_maximum():
    player = make_state(mp=100, current_mp=42).character
    starting_maximum = player.maximum_mp
    assert starting_maximum > 0
    assert player.current_mp == pytest.approx(42)
    assert player.consume_mp(20)
    assert player.current_mp == pytest.approx(22)
    assert not player.consume_mp(23)
    assert player.current_mp == pytest.approx(22)
    assert player.restore_mp(200) == pytest.approx(starting_maximum - 22)
    assert player.current_mp == pytest.approx(starting_maximum)
    player.set_current_mp(35)
    player.set_equipment_bonuses({"mp": 50})
    assert player.maximum_mp == pytest.approx(starting_maximum + 50)
    assert player.current_mp == pytest.approx(35)
    player.set_current_mp(-5)
    assert player.current_mp == 0


def test_uninitialized_current_mp_stays_full_when_equipment_changes_maximum():
    player = make_state(mp=100).character
    assert not player.has_saved_current_mp
    player.set_equipment_bonuses({"mp": 50})
    assert not player.has_saved_current_mp
    assert player.current_mp == pytest.approx(player.maximum_mp)


def test_legacy_current_mp_defaults_full_and_round_trips():
    state = make_state(mp=120)
    state.character.set_current_mp(45)
    restored = GameState.from_dict(state.to_dict())
    assert restored.character.current_mp == pytest.approx(45)
    old = state.to_dict()
    old["save_version"] = 7
    old["character"].pop("current_mp")
    old.pop("skill_state")
    migrated = GameState.from_dict(old)
    assert migrated.character.current_mp == pytest.approx(migrated.character.maximum_mp)
    assert migrated.skill_state.unlocked_skill_ids == ["power_strike", "arcane_bolt"]


def test_unlock_upgrade_prerequisites_gold_costs_and_maximum_level_are_enforced():
    state = make_state(level=10)
    manager = SkillManager(state)
    economy = EconomyManager(state)
    economy.credit_currency(1_000, source="test", description="skill currency")
    can_unlock, requirement = manager.unlock_requirements("whirlwind_slash")
    assert not can_unlock and "Heavy Slash" in requirement
    assert manager.unlock("heavy_slash")
    assert manager.unlock("whirlwind_slash")
    assert manager.level("heavy_slash") == 1
    assert state.economy.gold.balance == 620
    assert manager.upgrade("heavy_slash") == 2
    assert state.economy.gold.balance == 560
    for _ in range(3):
        manager.upgrade("heavy_slash")
    with pytest.raises(SkillActionError, match="maximum level"):
        manager.upgrade("heavy_slash")
    with pytest.raises(SkillActionError, match="already unlocked"):
        manager.unlock("heavy_slash")
    assert [tx.transaction_type.value for tx in state.economy.transactions if tx.transaction_type.value == "skill_unlock"] == ["skill_unlock", "skill_unlock"]


def test_failed_unlock_and_upgrade_leave_wallet_and_progress_unchanged():
    state = make_state(level=10)
    manager = SkillManager(state)
    with pytest.raises(SkillActionError, match="Insufficient Gold"):
        manager.unlock("heavy_slash")
    assert not manager.is_unlocked("heavy_slash")
    assert state.economy.gold.balance == 0
    manager.progress.unlocked_skill_ids.append("heavy_slash")
    manager.progress.skill_levels["heavy_slash"] = 1
    with pytest.raises(SkillActionError, match="Insufficient Gold"):
        manager.upgrade("heavy_slash")
    assert manager.level("heavy_slash") == 1


def test_loadout_capacity_duplicate_locked_rejection_and_replacement():
    state = make_state()
    manager = SkillManager(state)
    manager.progress.max_equipped_skills = 2
    manager.equip("power_strike")
    assert manager.progress.equipped_skill_ids.count("power_strike") == 1
    with pytest.raises(SkillActionError, match="Locked"):
        manager.equip("fireball")
    manager.progress.unlocked_skill_ids.append("fireball")
    manager.progress.skill_levels["fireball"] = 1
    with pytest.raises(SkillActionError, match="full"):
        manager.equip("fireball")
    manager.equip("fireball", slot=0)
    assert manager.progress.equipped_skill_ids == ["fireball", "arcane_bolt"]


def test_skill_damage_uses_level_scaling_defense_and_critical_rules():
    attributes = AttributeSheet(100, 200, 100, 0, 0, 0, 0, 0.75, 2.5, 1, 0, 0)
    physical = SkillEffect.from_dict({"kind": "damage", "damage_type": "physical", "scaling": {"attack": 1.5}})
    target = enemy(physical=1_000)
    hit = calculate_skill_damage(attributes, target, physical, 2, critical_eligible=True, rng=FixedRandom(chance=0.5))
    assert hit.critical
    assert hit.raw_damage == pytest.approx(100 * 1.5 * 1.15 * 2.5)
    assert hit.damage < hit.raw_damage
    assert effect_magnitude(attributes, physical, 3) == pytest.approx(195)
    magical = SkillEffect.from_dict({"kind": "damage", "damage_type": "magical", "scaling": {"mp": 1.0}})
    assert calculate_skill_damage(attributes, enemy(magical=100), magical, rng=FixedRandom()).damage < 200


def test_equipment_bonuses_flow_into_physical_and_magical_skill_scaling():
    player = make_state(mp=100, attack=50).character
    physical = SkillEffect.from_dict({"kind": "damage", "damage_type": "physical", "scaling": {"attack": 1.0}})
    magical = SkillEffect.from_dict({"kind": "damage", "damage_type": "magical", "scaling": {"mp": 1.0}})
    target = enemy()
    before = player.calculated_attributes
    physical_before = calculate_skill_damage(before, target, physical, rng=FixedRandom()).damage
    magical_before = calculate_skill_damage(before, target, magical, rng=FixedRandom()).damage
    player.set_equipment_bonuses({"attack": 100, "mp": 100})
    after = player.calculated_attributes
    assert calculate_skill_damage(after, target, physical, rng=FixedRandom()).damage > physical_before
    assert calculate_skill_damage(after, target, magical, rng=FixedRandom()).damage > magical_before


def test_skill_activation_consumes_mp_once_and_cooldown_failure_is_atomic():
    state = make_state(mp=100, current_mp=40)
    manager = combat_manager(state)
    manager.start_combat(now=0)
    event = manager.activate_skill("power_strike", now=0)
    assert event.kind == "skill_activated"
    assert event.damage > 0
    assert state.character.current_mp == pytest.approx(32)
    assert state.combat_statistics.total_skills_used == 1
    with pytest.raises(CombatActionError, match="recharging"):
        manager.activate_skill("power_strike", now=0.5)
    assert state.character.current_mp == pytest.approx(32)
    with pytest.raises(CombatActionError, match="locked"):
        manager.activate_skill("fireball", now=3)


def test_skill_caused_defeat_keeps_existing_reward_and_enemy_statistics_path():
    state = make_state(mp=200, current_mp=100, attack=100_000)
    manager = CombatManager(state, rng=FixedRandom())
    manager.start_combat(now=0)

    result = manager.activate_skill("power_strike", now=0)

    assert result.kind == "enemy_defeated"
    assert result.exp_reward > 0
    assert state.combat_statistics.total_enemies_defeated == 1
    assert state.combat_statistics.total_skills_used == 1
    assert state.combat_statistics.total_damage_dealt == pytest.approx(result.damage)


def test_insufficient_mp_and_unequipped_skill_do_not_mutate_combat_state():
    state = make_state(mp=10, current_mp=5)
    manager = combat_manager(state)
    manager.start_combat(now=0)
    with pytest.raises(CombatActionError, match="Not enough MP"):
        manager.activate_skill("power_strike", now=0)
    assert state.character.current_mp == pytest.approx(5)
    assert state.combat_statistics.total_skills_used == 0
    state.character.set_current_mp(10)
    manager.skill_manager.unequip("power_strike")
    with pytest.raises(CombatActionError, match="not equipped"):
        manager.activate_skill("power_strike", now=1)
    assert state.character.current_mp == pytest.approx(10)


def test_player_mp_regeneration_uses_shared_effective_mp_regeneration():
    state = make_state(mp=200, current_mp=30)
    manager = combat_manager(state)
    manager.start_combat(now=0)
    rate = state.character.calculated_attributes.mp_regeneration
    result = manager.tick(now=1)
    assert result.changed
    assert state.character.current_mp == pytest.approx(30 + rate * 0.25)


def test_fireball_dot_ticks_and_deals_damage_to_enemies():
    state = make_state(mp=200, current_mp=100)
    state.skill_state.unlocked_skill_ids.append("fireball")
    state.skill_state.skill_levels["fireball"] = 1
    state.skill_state.equipped_skill_ids.append("fireball")
    manager = combat_manager(state)
    manager.start_combat(now=0)
    manager.activate_skill("fireball", now=0)
    before = manager.current_enemy.current_hp
    manager.tick(now=2)
    assert manager.current_enemy.current_hp < before
    assert state.combat_statistics.total_skill_damage > 0


def test_temporary_player_buff_and_enemy_defense_break_expire_on_combat_tick():
    state = make_state(mp=200, current_mp=100)
    for skill_id in ("battle_focus", "piercing_thrust"):
        state.skill_state.unlocked_skill_ids.append(skill_id)
        state.skill_state.skill_levels[skill_id] = 1
        state.skill_state.equipped_skill_ids.append(skill_id)
    manager = combat_manager(state, enemy(physical=1_000))
    manager.start_combat(now=0)
    before_attack = manager._player_attributes().attack
    manager.activate_skill("battle_focus", now=0)
    assert manager._player_attributes().attack > before_attack
    # Use a fresh encounter so the cooldown timeline is explicit.
    manager.retreat()
    manager.current_enemy = None
    manager.start_combat(now=20)
    manager.activate_skill("piercing_thrust", now=20)
    assert manager.current_enemy.physical_defense == pytest.approx(700)
    manager.tick(now=26)
    assert manager.current_enemy.physical_defense == pytest.approx(1_000)


def test_healing_and_mana_recovery_skills_use_bounded_player_resource_methods():
    state = make_state(mp=200, current_mp=100)
    player = state.character
    player.set_current_hp(player.maximum_hp / 2)
    for skill_id in ("minor_healing", "mana_recovery"):
        state.skill_state.unlocked_skill_ids.append(skill_id)
        state.skill_state.skill_levels[skill_id] = 1
        state.skill_state.equipped_skill_ids.append(skill_id)
    manager = combat_manager(state)
    manager.start_combat(now=0)
    hp_before = player.current_hp
    healing = manager.activate_skill("minor_healing", now=0)
    assert player.current_hp > hp_before
    assert healing.kind == "skill_activated"
    player.set_current_mp(0)
    mana = manager.activate_skill("mana_recovery", now=0.1)
    assert player.current_mp > 0
    assert player.current_mp <= player.maximum_mp
    assert mana.mp_consumed == 0


def test_shield_bash_stun_skips_enemy_action_and_player_poison_can_defeat():
    state = make_state(mp=100, current_mp=80)
    state.skill_state.unlocked_skill_ids.append("shield_bash")
    state.skill_state.skill_levels["shield_bash"] = 1
    state.skill_state.equipped_skill_ids.append("shield_bash")
    quick_enemy = EnemyDefinition("quick", "Quick Dummy", 100_000, 100, 1, 0.5)
    manager = CombatManager(state, rng=FixedRandom(), enemy_definitions=(quick_enemy,))
    manager.start_combat(now=0)
    hp_before = state.character.current_hp
    manager.activate_skill("shield_bash", now=0)
    result = manager.tick(now=0.5)
    assert any(event.kind == "enemy_stunned" for event in result.events)
    assert state.character.current_hp == hp_before

    state.character.set_current_hp(1)
    manager.status_effect_manager.apply(target="player", status="poison", source_id="test_poison", magnitude=1,
                                        duration=2, now=1, tick_interval=1)
    result = manager.tick(now=2)
    assert manager.state.value == "player_defeated"
    assert any(event.kind == "player_defeated" for event in result.events)
    assert manager.status_effect_manager.active_effects == ()


def test_skill_damage_crosses_boss_phase_and_preserves_phase_events():
    state = make_state(mp=100, current_mp=100, attack=100)
    phases = (BossPhaseDefinition("opening", "Opening", 1.0), BossPhaseDefinition("rage", "Rage", 0.5))
    boss = EnemyDefinition("training_boss", "Training Boss", 600, 0, 1, 2.0,
                           classification=EnemyClassification.BOSS, boss_phases=phases)
    common = EnemyDefinition("training_common", "Training Common", 10_000, 0, 1, 2.0)
    manager = CombatManager(state, rng=FixedRandom(), enemy_definitions=(common, boss))
    manager.challenge_boss("training_boss", now=0)
    result = manager.activate_skill("power_strike", now=0)
    assert manager.current_enemy.phase_index == 1
    assert any("enters Rage" in message for message in result.notifications)


def test_status_stacking_stun_expiry_and_boss_duration_resistance():
    statuses = StatusEffectManager()
    target = enemy(classification=EnemyClassification.BOSS)
    statuses.apply(target="enemy", status="stun", source_id="test", magnitude=1, duration=10, now=0,
                   classification=target.classification)
    assert statuses.enemy_stunned()
    assert statuses.active_effects[0].expires_at == pytest.approx(5.5)
    statuses.update(6, make_state().character, target)
    assert not statuses.enemy_stunned()
    statuses.apply(target="enemy", status="poison", source_id="poison_skill", magnitude=0.01, duration=3,
                   now=0, tick_interval=1)
    statuses.apply(target="enemy", status="poison", source_id="poison_skill", magnitude=0.01, duration=3,
                   now=0.5, tick_interval=1)
    assert next(effect for effect in statuses.active_effects if effect.status == "poison").stacks == 2


def test_save_round_trip_persists_skill_progress_but_not_transient_cooldowns():
    state = make_state()
    manager = SkillManager(state)
    EconomyManager(state).credit_currency(500, source="test", description="skills")
    manager.unlock("heavy_slash")
    manager.upgrade("power_strike")
    manager.equip("heavy_slash")
    combat = combat_manager(state)
    combat.start_combat(now=0)
    combat.activate_skill("power_strike", now=0)
    restored = GameState.from_dict(json.loads(json.dumps(state.to_dict())))
    restored_manager = SkillManager(restored)
    assert restored.skill_state.to_dict() == state.skill_state.to_dict()
    assert restored_manager.cooldown_remaining("power_strike", now=0) == 0
    assert restored.combat_statistics.total_skills_used == 1

