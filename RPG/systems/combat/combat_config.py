"""Balance and timing settings for the initial ordinary-enemy combat loop."""

from __future__ import annotations

from .enemy import EnemyDefinition

PLAYER_DAMAGE_VARIATION_MIN = 0.90
PLAYER_DAMAGE_VARIATION_MAX = 1.10
ENEMY_DAMAGE_VARIATION_MIN = 0.90
ENEMY_DAMAGE_VARIATION_MAX = 1.10
DEFENSE_MITIGATION_CONSTANT = 1_000.0
MINIMUM_DAMAGE = 1.0
MINIMUM_ATTACK_COOLDOWN_SECONDS = 0.05
RESPAWN_DELAY_SECONDS = 2.0
RECOVERY_HP_FRACTION = 0.50
UI_COMBAT_TICK_MS = 100
MAX_REGEN_ELAPSED_PER_TICK_SECONDS = 0.25

ENEMY_DEFINITIONS: tuple[EnemyDefinition, ...] = (
    EnemyDefinition(
        definition_id="slime", name="Slime", max_hp=100, attack=5, exp_reward=10,
        attack_interval=2.0, description="A small, quivering creature found near quiet roads.",
    ),
    EnemyDefinition(
        definition_id="goblin", name="Goblin", max_hp=250, attack=12, exp_reward=25,
        attack_interval=1.8, physical_defense=5,
        description="A quick raider armed with crude tools.",
    ),
    EnemyDefinition(
        definition_id="wolf", name="Wolf", max_hp=400, attack=18, exp_reward=40,
        attack_interval=1.5, physical_defense=8,
        description="A hungry forest hunter that strikes quickly.",
    ),
    EnemyDefinition(
        definition_id="skeleton", name="Skeleton", max_hp=750, attack=30, exp_reward=75,
        attack_interval=2.0, physical_defense=15,
        description="An animated skeleton held together by old magic.",
    ),
    EnemyDefinition(
        definition_id="orc", name="Orc", max_hp=1_500, attack=50, exp_reward=150,
        attack_interval=2.5, physical_defense=30,
        description="A broad-shouldered warrior with a heavy swing.",
    ),
)

ENEMY_DEFINITIONS_BY_ID = {definition.definition_id: definition for definition in ENEMY_DEFINITIONS}
