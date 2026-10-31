"""UI-independent combat encounter, enemy ability, boss, and loot processing."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from enum import Enum
from math import isfinite
from typing import TYPE_CHECKING, Iterable

from . import combat_config
from .boss_manager import BossManager
from .damage_calculator import RandomSource, calculate_enemy_damage, calculate_player_damage
from .enemy import Enemy, EnemyClassification, EnemyDefinition
from .enemy_ability import AbilityEvent, EnemyAbilityRuntime, EnemyAttackProfile
from .enemy_database import EnemyDatabase, EnemyDatabaseError
from .loot_table import LootDrop, LootRandomSource, LootTableDatabase
from ..economy.reward_manager import RewardManager, RewardSummary

if TYPE_CHECKING:
    from ...core.game_state import GameState


class CombatState(str, Enum):
    IDLE = "idle"
    ACTIVE = "active"
    ENEMY_DEFEATED = "enemy_defeated"
    PLAYER_DEFEATED = "player_defeated"
    RECOVERING = "recovering"


class CombatActionError(ValueError):
    """Raised when an action is invalid for the current combat state."""


@dataclass(frozen=True)
class CombatEvent:
    kind: str
    message: str
    damage: float = 0.0
    critical: bool = False
    exp_reward: int = 0
    levels_gained: int = 0
    drops: tuple[LootDrop, ...] = ()
    notifications: tuple[str, ...] = ()
    reward_summary: RewardSummary | None = None


@dataclass(frozen=True)
class CombatTickResult:
    changed: bool = False
    events: tuple[CombatEvent, ...] = ()


class CombatManager:
    """Own transient encounters while modifying persistent data through GameState."""

    def __init__(
        self,
        game_state: "GameState",
        *,
        rng: RandomSource | None = None,
        loot_rng: LootRandomSource | None = None,
        enemy_database: EnemyDatabase | None = None,
        loot_database: LootTableDatabase | None = None,
        reward_manager: RewardManager | None = None,
        enemy_definitions: Iterable[EnemyDefinition] | None = None,
        respawn_delay: float = combat_config.RESPAWN_DELAY_SECONDS,
        recovery_fraction: float = combat_config.RECOVERY_HP_FRACTION,
    ) -> None:
        self.game_state = game_state
        self.rng = rng if rng is not None else random.Random()
        self.loot_rng = loot_rng if loot_rng is not None else (self.rng if hasattr(self.rng, "randint") else random.Random())
        if enemy_database is not None and enemy_definitions is not None:
            raise ValueError("Provide either enemy_database or enemy_definitions, not both.")
        try:
            self.enemy_database = enemy_database or (
                EnemyDatabase.from_definitions(enemy_definitions)
                if enemy_definitions is not None
                else EnemyDatabase.load_default()
            )
            self.loot_database = loot_database or LootTableDatabase.load_default()
            self.reward_manager = reward_manager or RewardManager()
            self.enemy_database.validate_loot_references(set(self.loot_database.table_ids))
        except (EnemyDatabaseError, ValueError) as exc:
            raise ValueError(f"Combat content could not be initialized: {exc}") from exc

        self.enemy_definitions = self.enemy_database.list_enemies()
        self._definitions_by_id = {definition.definition_id.casefold(): definition for definition in self.enemy_definitions}
        self._common_definitions = self.enemy_database.get_by_classification(EnemyClassification.COMMON)
        if not self._common_definitions:
            raise ValueError("Combat requires at least one Common enemy for the ordinary encounter rotation.")
        if not isfinite(respawn_delay) or respawn_delay < 0:
            raise ValueError("Respawn delay must be a finite non-negative number.")
        if not isfinite(recovery_fraction) or not 0 < recovery_fraction <= 1:
            raise ValueError("Recovery HP fraction must be greater than zero and at most one.")

        self.respawn_delay = float(respawn_delay)
        self.recovery_fraction = float(recovery_fraction)
        self.state = CombatState.IDLE
        self.current_enemy: Enemy | None = None
        self._next_common_index = 0
        self._encounter_mode = "single"
        self._ability_runtime: EnemyAbilityRuntime | None = None
        self._boss_manager = BossManager()
        self._next_enemy_attack_at: float | None = None
        self._next_respawn_at: float | None = None
        self._next_player_attack_at: float | None = None
        self._last_regeneration_at: float | None = None

        player = self.game_state.character
        if player.has_saved_current_hp and player.maximum_hp > 0 and player.current_hp <= 0:
            self.state = CombatState.PLAYER_DEFEATED

    @property
    def is_running(self) -> bool:
        return self.state in {CombatState.ACTIVE, CombatState.ENEMY_DEFEATED}

    @property
    def available_enemies(self) -> tuple[EnemyDefinition, ...]:
        return self.enemy_definitions

    @property
    def active_ability_names(self) -> tuple[str, ...]:
        return self._ability_runtime.active_ability_names if self._ability_runtime is not None else ()

    def get_by_classification(self, classification: str | EnemyClassification) -> tuple[EnemyDefinition, ...]:
        return self.enemy_database.get_by_classification(classification)

    def start_combat(self, enemy_id: str | None = None, *, now: float | None = None) -> CombatEvent:
        """Start a Common rotation or an explicitly selected Uncommon/Rare encounter."""
        if enemy_id is None:
            definition = self._common_definitions[self._next_common_index % len(self._common_definitions)]
            return self._begin_encounter(definition, now=now, mode="common")
        definition = self._get_definition(enemy_id)
        if definition.classification in {EnemyClassification.ELITE, EnemyClassification.BOSS, EnemyClassification.WORLD_BOSS}:
            raise CombatActionError(f"{definition.classification.display_name} encounters require their dedicated start action.")
        mode = "common" if definition.classification is EnemyClassification.COMMON else "single"
        return self._begin_encounter(definition, now=now, mode=mode)

    def start_classification_encounter(
        self,
        classification: str | EnemyClassification,
        enemy_id: str | None = None,
        *,
        now: float | None = None,
    ) -> CombatEvent:
        selected = EnemyClassification.from_value(classification)
        candidates = self.get_by_classification(selected)
        if not candidates:
            raise CombatActionError(f"There are no {selected.display_name} enemies configured.")
        definition = self._get_definition(enemy_id) if enemy_id is not None else candidates[0]
        if definition.classification is not selected:
            raise CombatActionError(f"{definition.name} is not classified as {selected.display_name}.")
        if selected is EnemyClassification.ELITE:
            return self.start_elite_encounter(definition.definition_id, now=now)
        if selected in {EnemyClassification.BOSS, EnemyClassification.WORLD_BOSS}:
            return self.challenge_boss(definition.definition_id, now=now)
        if selected is EnemyClassification.COMMON:
            return self.start_combat(definition.definition_id, now=now)
        return self._begin_encounter(definition, now=now, mode="single")

    def start_elite_encounter(self, enemy_id: str, *, now: float | None = None) -> CombatEvent:
        definition = self._get_definition(enemy_id)
        if definition.classification is not EnemyClassification.ELITE:
            raise CombatActionError(f"{definition.name} is not an Elite enemy.")
        return self._begin_encounter(definition, now=now, mode="single")

    def challenge_boss(self, enemy_id: str, *, now: float | None = None) -> CombatEvent:
        definition = self._get_definition(enemy_id)
        if definition.classification not in {EnemyClassification.BOSS, EnemyClassification.WORLD_BOSS}:
            raise CombatActionError(f"{definition.name} is not a Boss or World Boss.")
        return self._begin_encounter(definition, now=now, mode="single")

    def attack(self, *, now: float | None = None) -> CombatEvent:
        now = self._time(now)
        self.synchronize_player()
        if self.state is CombatState.PLAYER_DEFEATED:
            raise CombatActionError("A defeated player cannot attack. Recover first.")
        if self.state is not CombatState.ACTIVE or self.current_enemy is None:
            raise CombatActionError("There is no living enemy to attack right now.")
        if self.game_state.character.current_hp <= 0:
            self._enter_player_defeated()
            raise CombatActionError("A defeated player cannot attack. Recover first.")
        enemy = self.current_enemy
        if enemy.is_defeated:
            raise CombatActionError("That enemy has already been defeated.")

        next_attack = self._next_player_attack_at if self._next_player_attack_at is not None else now
        if now + 1e-9 < next_attack:
            remaining = next_attack - now
            return CombatEvent("cooldown", f"Attack is recharging ({remaining:.2f}s).")

        player = self.game_state.character
        result = calculate_player_damage(player.calculated_attributes, enemy, self.rng)
        applied = enemy.receive_damage(result.damage)
        self.game_state.record_player_attack(applied, result.critical)
        self._next_player_attack_at = now + self.attack_cooldown_seconds()
        notifications: list[str] = []
        old_interval = enemy.attack_interval
        for transition in self._boss_manager.advance_phases(enemy):
            text = f"{enemy.name} enters {transition.current_phase}."
            if transition.description:
                text += f" {transition.description}"
            notifications.append(text)
        if enemy.attack_interval != old_interval and self.state is CombatState.ACTIVE:
            self._next_enemy_attack_at = now + enemy.attack_interval
        if self._ability_runtime is not None and not enemy.is_defeated:
            notifications.extend(event.message for event in self._ability_runtime.update(now))

        if enemy.is_defeated:
            return self._resolve_defeat(enemy, applied, result.critical, now, tuple(notifications))

        if result.critical:
            kind = "critical_hit"
            message = f"Critical hit! You dealt {applied:,.1f} damage to {enemy.name}."
        else:
            kind = "player_hit"
            message = f"You dealt {applied:,.1f} damage to {enemy.name}."
        return CombatEvent(kind, message, damage=applied, critical=result.critical, notifications=tuple(notifications))

    def retreat(self) -> CombatEvent:
        if self.state not in {CombatState.ACTIVE, CombatState.ENEMY_DEFEATED}:
            raise CombatActionError("There is no active encounter to retreat from.")
        self._clear_ability_runtime()
        self.state = CombatState.IDLE
        self.current_enemy = None
        self._clear_timers()
        return CombatEvent("retreated", "You retreated. Your current HP is unchanged.")

    def recover(self) -> CombatEvent:
        if self.state is not CombatState.PLAYER_DEFEATED:
            raise CombatActionError("Recovery is only available after defeat.")
        player = self.game_state.character
        if player.maximum_hp <= 0:
            raise CombatActionError("Allocate at least one point to HP before recovering.")
        healed = player.set_current_hp(player.maximum_hp * self.recovery_fraction)
        self._clear_ability_runtime()
        self.state = CombatState.RECOVERING
        self.current_enemy = None
        self._clear_timers()
        self.state = CombatState.IDLE
        return CombatEvent("recovered", f"You recovered to {healed:,.1f} / {player.maximum_hp:,.1f} HP.")

    def synchronize_player(self) -> CombatEvent | None:
        """Apply max-HP clamps and transition to defeat if an active player has no HP."""
        player = self.game_state.character
        _ = player.current_hp
        if (
            self.state is CombatState.IDLE
            and player.has_saved_current_hp
            and player.maximum_hp > 0
            and player.current_hp <= 0
        ):
            self.state = CombatState.PLAYER_DEFEATED
            return CombatEvent("player_defeated", "This character has no current HP. Recover to continue.")
        if self.state in {CombatState.ACTIVE, CombatState.ENEMY_DEFEATED} and player.current_hp <= 0:
            self._enter_player_defeated()
            return CombatEvent("player_defeated", "You have been defeated.")
        return None

    def attack_cooldown_seconds(self) -> float:
        speed = max(0.01, self.game_state.character.calculated_attributes.attack_speed)
        return max(combat_config.MINIMUM_ATTACK_COOLDOWN_SECONDS, 1.0 / speed)

    def attack_cooldown_remaining(self, *, now: float | None = None) -> float:
        now = self._time(now)
        if self._next_player_attack_at is None:
            return 0.0
        return max(0.0, self._next_player_attack_at - now)

    def tick(self, *, now: float | None = None) -> CombatTickResult:
        """Advance scheduled combat effects without sleeping or creating threads."""
        now = self._time(now)
        transition = self.synchronize_player()
        if transition is not None:
            return CombatTickResult(changed=True, events=(transition,))

        if self.state is CombatState.ENEMY_DEFEATED:
            if self._encounter_mode == "common" and self._next_respawn_at is not None and now >= self._next_respawn_at:
                try:
                    enemy = self._spawn_common_enemy()
                except (OverflowError, ValueError) as exc:
                    self.state = CombatState.IDLE
                    self.current_enemy = None
                    self._clear_ability_runtime()
                    self._clear_timers()
                    return CombatTickResult(
                        changed=True,
                        events=(CombatEvent("enemy_spawn_failed", f"The next enemy could not be created: {exc}"),),
                    )
                self.state = CombatState.ACTIVE
                self._schedule_enemy(enemy, now)
                self._next_player_attack_at = now
                self._last_regeneration_at = now
                return CombatTickResult(
                    changed=True,
                    events=(CombatEvent("enemy_respawned", f"A new {enemy.name} has appeared."),),
                )
            return CombatTickResult()

        if self.state is not CombatState.ACTIVE or self.current_enemy is None:
            return CombatTickResult()

        changed = False
        events: list[CombatEvent] = []
        enemy = self.current_enemy
        if self._ability_runtime is not None:
            ability_events = self._ability_runtime.update(now)
            events.extend(self._ability_combat_events(ability_events))
            changed = bool(ability_events)

        player = self.game_state.character
        if self._last_regeneration_at is None:
            self._last_regeneration_at = now
        elapsed = min(
            combat_config.MAX_REGEN_ELAPSED_PER_TICK_SECONDS,
            max(0.0, now - self._last_regeneration_at),
        )
        self._last_regeneration_at = now
        regeneration = player.calculated_attributes.hp_regeneration * elapsed
        if regeneration > 0:
            healed = self.game_state.heal_combat_hp(regeneration)
            changed = changed or healed > 0

        if self._next_enemy_attack_at is not None and now >= self._next_enemy_attack_at:
            profile = None
            if self._ability_runtime is not None:
                profile, ability_events = self._ability_runtime.before_enemy_attack(now)
                events.extend(self._ability_combat_events(ability_events))
            if profile is None:
                profile = EnemyAttackProfile()
            defense = player.calculated_attributes.physical_defense * profile.defense_effectiveness
            result = calculate_enemy_damage(enemy.attack * profile.damage_multiplier, defense, self.rng)
            received = self.game_state.take_combat_damage(result.damage)
            self.game_state.record_damage_received(received)
            changed = True
            ability_label = f" with {profile.ability.name}" if profile.ability is not None else ""
            events.append(CombatEvent(
                "enemy_hit",
                f"{enemy.name} hit you{ability_label} for {received:,.1f} damage.",
                damage=received,
            ))
            if player.current_hp <= 0:
                self._enter_player_defeated()
                events.append(CombatEvent("player_defeated", "You have been defeated. Recover to continue."))
            else:
                self._next_enemy_attack_at = now + enemy.attack_interval
        return CombatTickResult(changed=changed, events=tuple(events))

    def _begin_encounter(self, definition: EnemyDefinition, *, now: float | None, mode: str) -> CombatEvent:
        now = self._time(now)
        if self.state is not CombatState.IDLE:
            raise CombatActionError("Combat can only start while the encounter is idle.")
        player = self.game_state.character
        if not player.character_created:
            raise CombatActionError("Create a character before starting combat.")
        attributes = player.calculated_attributes
        if player.maximum_hp <= 0 or player.current_hp <= 0:
            raise CombatActionError("Allocate at least one point to HP before starting combat.")
        if attributes.attack <= 0:
            raise CombatActionError("Allocate at least one point to Attack before starting combat.")

        try:
            enemy = Enemy.spawn(definition, level=max(1, player.level))
            _ = enemy.attack_interval, enemy.attack, enemy.physical_defense, enemy.magical_defense
        except (OverflowError, ValueError) as exc:
            raise CombatActionError(f"Could not create {definition.name}: {exc}") from exc
        self.current_enemy = enemy
        self._ability_runtime = EnemyAbilityRuntime(enemy)
        self._encounter_mode = mode
        if definition.classification is EnemyClassification.COMMON:
            current_index = next(
                index for index, common in enumerate(self._common_definitions)
                if common.definition_id.casefold() == definition.definition_id.casefold()
            )
            self._next_common_index = (current_index + 1) % len(self._common_definitions)
        self.state = CombatState.ACTIVE
        self._schedule_enemy(enemy, now)
        self._next_player_attack_at = now
        self._last_regeneration_at = now
        kind = "elite_encounter_started" if definition.classification is EnemyClassification.ELITE else "combat_started"
        return CombatEvent(kind, f"{definition.classification.display_name} encounter started. {enemy.name} approaches.")

    def _resolve_defeat(
        self,
        enemy: Enemy,
        damage: float,
        critical: bool,
        now: float,
        notifications: tuple[str, ...],
    ) -> CombatEvent:
        summary = self.reward_manager.process_defeat(
            self.game_state,
            enemy,
            loot_database=self.loot_database,
            loot_rng=self.loot_rng,
            claim_reward=(
                lambda: self._boss_manager.claim_defeat(enemy)
                if enemy.classification in {EnemyClassification.BOSS, EnemyClassification.WORLD_BOSS}
                else enemy.claim_reward()
            ),
        )
        if summary is None:
            return CombatEvent("duplicate_reward_blocked", f"{enemy.name}'s reward was already claimed.")

        reward = summary.exp_awarded
        levels = summary.levels_gained
        drops = summary.item_drops + summary.currency_drops
        self._clear_ability_runtime()
        self._next_enemy_attack_at = None
        self._last_regeneration_at = None
        if self._encounter_mode == "common":
            self.state = CombatState.ENEMY_DEFEATED
            self._next_respawn_at = now + self.respawn_delay
        else:
            self.state = CombatState.IDLE
            self._next_respawn_at = None

        suffix = f" Earned {reward:,} EXP."
        if summary.currency_error:
            suffix += (
                f" Gold reward was not credited because the wallet could not safely record it"
                f" ({summary.currency_error})."
            )
        else:
            suffix += (
                f" Guaranteed Gold: {summary.guaranteed_gold:,}; additional Gold drops: "
                f"{summary.bonus_gold:,}; total earned: {summary.total_gold_credited:,} G."
            )
        if summary.configuration_warning:
            suffix += f" Base Gold reward unavailable: {summary.configuration_warning}."
        if levels:
            suffix += f" Level up: +{levels} level(s), +{levels * 10} stat points."
        if summary.item_drops:
            suffix += " Loot: " + ", ".join(f"{drop.reward_id} x{drop.quantity}" for drop in summary.item_drops) + "."
        else:
            suffix += " No item loot dropped."
        if critical:
            suffix = "Critical hit! " + suffix.lstrip()
        if enemy.classification is EnemyClassification.WORLD_BOSS:
            kind = "world_boss_defeated"
        elif enemy.classification is EnemyClassification.BOSS:
            kind = "boss_defeated"
        elif enemy.classification is EnemyClassification.ELITE:
            kind = "elite_defeated"
        else:
            kind = "enemy_defeated"
        return CombatEvent(
            kind,
            f"{enemy.name} defeated for {damage:,.1f} damage!{suffix}",
            damage=damage,
            critical=critical,
            exp_reward=reward,
            levels_gained=levels,
            drops=drops,
            notifications=notifications,
            reward_summary=summary,
        )

    def _spawn_common_enemy(self) -> Enemy:
        definition = self._common_definitions[self._next_common_index % len(self._common_definitions)]
        enemy = Enemy.spawn(definition, level=max(1, self.game_state.character.level))
        _ = enemy.attack_interval, enemy.attack, enemy.physical_defense, enemy.magical_defense
        self._next_common_index = (self._next_common_index + 1) % len(self._common_definitions)
        self.current_enemy = enemy
        self._ability_runtime = EnemyAbilityRuntime(enemy)
        self._next_respawn_at = None
        return enemy

    def _get_definition(self, enemy_id: str) -> EnemyDefinition:
        try:
            return self.enemy_database.get_by_id(enemy_id)
        except EnemyDatabaseError as exc:
            raise CombatActionError(str(exc)) from exc

    def _schedule_enemy(self, enemy: Enemy, now: float) -> None:
        self._next_enemy_attack_at = now + enemy.attack_interval

    @staticmethod
    def _ability_combat_events(events: tuple[AbilityEvent, ...]) -> tuple[CombatEvent, ...]:
        return tuple(CombatEvent("ability_activated", event.message) for event in events)

    def _enter_player_defeated(self) -> None:
        self.game_state.character.set_current_hp(0)
        self._clear_ability_runtime()
        self.state = CombatState.PLAYER_DEFEATED
        self._clear_timers()

    def _clear_ability_runtime(self) -> None:
        if self._ability_runtime is not None:
            self._ability_runtime.clear()
            self._ability_runtime = None

    def _clear_timers(self) -> None:
        self._next_enemy_attack_at = None
        self._next_respawn_at = None
        self._next_player_attack_at = None
        self._last_regeneration_at = None

    @staticmethod
    def _time(value: float | None) -> float:
        result = time.monotonic() if value is None else float(value)
        if not isfinite(result):
            raise ValueError("Combat time must be finite.")
        return result
