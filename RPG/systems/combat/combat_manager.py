"""UI-independent combat encounter and event processing."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from enum import Enum
from math import isfinite
from typing import TYPE_CHECKING, Iterable

from . import combat_config
from .damage_calculator import RandomSource, calculate_enemy_damage, calculate_player_damage
from .enemy import Enemy, EnemyDefinition

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


@dataclass(frozen=True)
class CombatTickResult:
    changed: bool = False
    events: tuple[CombatEvent, ...] = ()


class CombatManager:
    """Own transient encounter state while modifying character data via GameState."""

    def __init__(
        self,
        game_state: "GameState",
        *,
        rng: RandomSource | None = None,
        enemy_definitions: Iterable[EnemyDefinition] = combat_config.ENEMY_DEFINITIONS,
        respawn_delay: float = combat_config.RESPAWN_DELAY_SECONDS,
        recovery_fraction: float = combat_config.RECOVERY_HP_FRACTION,
    ) -> None:
        self.game_state = game_state
        self.rng = rng or random.Random()
        self.enemy_definitions = tuple(enemy_definitions)
        if not self.enemy_definitions:
            raise ValueError("Combat requires at least one enemy definition.")
        self._definitions_by_id = {definition.definition_id: definition for definition in self.enemy_definitions}
        if len(self._definitions_by_id) != len(self.enemy_definitions):
            raise ValueError("Enemy definition IDs must be unique.")
        if not isfinite(respawn_delay) or respawn_delay < 0:
            raise ValueError("Respawn delay must be a finite non-negative number.")
        if not isfinite(recovery_fraction) or not 0 < recovery_fraction <= 1:
            raise ValueError("Recovery HP fraction must be greater than zero and at most one.")

        self.respawn_delay = float(respawn_delay)
        self.recovery_fraction = float(recovery_fraction)
        self.state = CombatState.IDLE
        self.current_enemy: Enemy | None = None
        self._next_enemy_index = 0
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

    def start_combat(self, enemy_id: str | None = None, *, now: float | None = None) -> CombatEvent:
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

        enemy = self._spawn_enemy(enemy_id)
        self.state = CombatState.ACTIVE
        self._next_enemy_attack_at = now + enemy.attack_interval
        self._next_player_attack_at = now
        self._last_regeneration_at = now
        return CombatEvent("combat_started", f"Combat started. {enemy.name} approaches.")

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
        if self.current_enemy.is_defeated:
            raise CombatActionError("That enemy has already been defeated.")

        next_attack = self._next_player_attack_at if self._next_player_attack_at is not None else now
        if now + 1e-9 < next_attack:
            remaining = next_attack - now
            return CombatEvent("cooldown", f"Attack is recharging ({remaining:.2f}s).")

        player = self.game_state.character
        result = calculate_player_damage(player.calculated_attributes, self.current_enemy, self.rng)
        applied = self.current_enemy.receive_damage(result.damage)
        self.game_state.record_player_attack(applied, result.critical)
        self._next_player_attack_at = now + self.attack_cooldown_seconds()

        if result.critical:
            kind = "critical_hit"
            message = f"Critical hit! You dealt {applied:,.1f} damage to {self.current_enemy.name}."
        else:
            kind = "player_hit"
            message = f"You dealt {applied:,.1f} damage to {self.current_enemy.name}."

        if self.current_enemy.is_defeated:
            enemy_name = self.current_enemy.name
            reward = self.current_enemy.exp_reward
            levels = self.game_state.award_combat_exp(reward) if reward > 0 else 0
            self.game_state.record_enemy_defeated(reward)
            self.state = CombatState.ENEMY_DEFEATED
            self._next_enemy_attack_at = None
            self._last_regeneration_at = None
            self._next_respawn_at = now + self.respawn_delay
            critical_text = "Critical hit! " if result.critical else ""
            suffix = f" Earned {reward:,} EXP."
            if levels:
                suffix += f" Level up: +{levels} level(s), +{levels * 10} stat points."
            return CombatEvent(
                "enemy_defeated",
                f"{critical_text}{enemy_name} defeated for {applied:,.1f} damage!{suffix}",
                damage=applied,
                critical=result.critical,
                exp_reward=reward,
                levels_gained=levels,
            )
        return CombatEvent(kind, message, damage=applied, critical=result.critical)

    def retreat(self) -> CombatEvent:
        if self.state not in {CombatState.ACTIVE, CombatState.ENEMY_DEFEATED}:
            raise CombatActionError("There is no active encounter to retreat from.")
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
            if self._next_respawn_at is not None and now >= self._next_respawn_at:
                enemy = self._spawn_enemy()
                self.state = CombatState.ACTIVE
                self._next_enemy_attack_at = now + enemy.attack_interval
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
            changed = healed > 0

        if self._next_enemy_attack_at is not None and now >= self._next_enemy_attack_at:
            enemy = self.current_enemy
            result = calculate_enemy_damage(enemy.attack, player.calculated_attributes.physical_defense, self.rng)
            received = self.game_state.take_combat_damage(result.damage)
            self.game_state.record_damage_received(received)
            changed = True
            events.append(CombatEvent("enemy_hit", f"{enemy.name} hit you for {received:,.1f} damage.", damage=received))
            if player.current_hp <= 0:
                self._enter_player_defeated()
                events.append(CombatEvent("player_defeated", "You have been defeated. Recover to continue."))
            else:
                self._next_enemy_attack_at = now + enemy.attack_interval
        return CombatTickResult(changed=changed, events=tuple(events))

    def _spawn_enemy(self, enemy_id: str | None = None) -> Enemy:
        if enemy_id is not None:
            definition = self._definitions_by_id.get(enemy_id)
            if definition is None:
                raise CombatActionError(f"Unknown enemy: {enemy_id}")
            index = self.enemy_definitions.index(definition)
            self._next_enemy_index = (index + 1) % len(self.enemy_definitions)
        else:
            definition = self.enemy_definitions[self._next_enemy_index]
            self._next_enemy_index = (self._next_enemy_index + 1) % len(self.enemy_definitions)
        self.current_enemy = Enemy.spawn(definition)
        self._next_respawn_at = None
        return self.current_enemy

    def _enter_player_defeated(self) -> None:
        self.game_state.character.set_current_hp(0)
        self.state = CombatState.PLAYER_DEFEATED
        self._clear_timers()

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
