from RPG.systems.combat.boss_manager import BossManager
from RPG.systems.combat.enemy import Enemy, EnemyClassification
from RPG.systems.combat.enemy_database import EnemyDatabase


def test_boss_phases_advance_once_when_hp_crosses_multiple_thresholds():
    definition = EnemyDatabase.load_default().get_by_id("dragon_lord")
    enemy = Enemy.spawn(definition)
    manager = BossManager()

    assert enemy.classification is EnemyClassification.BOSS
    assert enemy.boss_phase.name == "Dormant Flame"
    enemy.receive_damage(enemy.max_hp * 0.8)
    transitions = manager.advance_phases(enemy)

    assert [item.current_phase for item in transitions] == ["Rising Embers", "Worldfire"]
    assert enemy.boss_phase.name == "Worldfire"
    assert enemy.attack > definition.attack
    assert manager.advance_phases(enemy) == ()


def test_world_boss_has_multiple_phases_and_rewards_claim_only_once():
    enemy = Enemy.spawn(EnemyDatabase.load_default().get_by_id("primordial_entity"))
    manager = BossManager()

    assert enemy.classification is EnemyClassification.WORLD_BOSS
    assert len(enemy.definition.boss_phases) == 4
    enemy.receive_damage(enemy.max_hp)
    assert manager.advance_phases(enemy) == ()
    assert manager.claim_defeat(enemy) is True
    assert manager.claim_defeat(enemy) is False
