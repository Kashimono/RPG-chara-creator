"""Data-driven enemy abilities and encounter-local ability cooldowns."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from types import MappingProxyType
from typing import TYPE_CHECKING, Mapping

if TYPE_CHECKING:
    from .enemy import Enemy


class EnemyAbilityType(str, Enum):
    HEAVY_STRIKE = "heavy_strike"
    ENRAGE = "enrage"
    DEFENSIVE_STANCE = "defensive_stance"
    REGENERATION = "regeneration"
    PIERCING_STRIKE = "piercing_strike"


class AbilityTrigger(str, Enum):
    ENEMY_ATTACK = "enemy_attack"
    HP_THRESHOLD = "hp_threshold"


@dataclass(frozen=True)
class EnemyAbilityDefinition:
    ability_id: str
    name: str
    description: str
    ability_type: EnemyAbilityType | str
    trigger: AbilityTrigger | str
    cooldown_seconds: float = 0.0
    duration_seconds: float = 0.0
    activation_threshold: float | None = None
    parameters: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if any(not isinstance(value, str) or not value.strip() for value in (self.ability_id, self.name, self.description)):
            raise ValueError("Enemy abilities require an ID, name, and description.")
        try:
            ability_type = EnemyAbilityType(self.ability_type)
            trigger = AbilityTrigger(self.trigger)
        except ValueError as exc:
            raise ValueError(f"Invalid ability type or trigger for '{self.ability_id}'.") from exc
        object.__setattr__(self, "ability_type", ability_type)
        object.__setattr__(self, "trigger", trigger)
        if isinstance(self.cooldown_seconds, bool) or not isinstance(self.cooldown_seconds, (int, float)) or not isfinite(self.cooldown_seconds) or self.cooldown_seconds < 0:
            raise ValueError("Ability cooldown must be finite and non-negative.")
        if isinstance(self.duration_seconds, bool) or not isinstance(self.duration_seconds, (int, float)) or not isfinite(self.duration_seconds) or self.duration_seconds < 0:
            raise ValueError("Ability duration must be finite and non-negative.")
        if self.activation_threshold is not None and (
            isinstance(self.activation_threshold, bool)
            or not isinstance(self.activation_threshold, (int, float))
            or not isfinite(self.activation_threshold)
            or not 0 < self.activation_threshold <= 1
        ):
            raise ValueError("Ability HP threshold must be greater than zero and at most one.")

        if not isinstance(self.parameters, Mapping):
            raise ValueError("Enemy ability parameters must be an object of numeric values.")
        normalized_parameters: dict[str, float] = {}
        for key, value in self.parameters.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
                raise ValueError(f"Ability parameter '{key}' must be a finite number.")
            normalized_parameters[str(key)] = float(value)
        object.__setattr__(self, "parameters", MappingProxyType(normalized_parameters))

        if ability_type in {EnemyAbilityType.HEAVY_STRIKE, EnemyAbilityType.PIERCING_STRIKE}:
            if trigger is not AbilityTrigger.ENEMY_ATTACK:
                raise ValueError(f"{ability_type.value} must trigger on an enemy attack.")
        elif ability_type is EnemyAbilityType.ENRAGE and trigger is not AbilityTrigger.HP_THRESHOLD:
            raise ValueError("Enrage must use an HP-threshold trigger.")
        elif trigger is AbilityTrigger.HP_THRESHOLD and self.activation_threshold is None:
            raise ValueError("HP-threshold abilities require an activation threshold.")

        if ability_type is EnemyAbilityType.HEAVY_STRIKE:
            if self.parameters.get("damage_multiplier", 1.5) <= 1:
                raise ValueError("Heavy Strike damage multiplier must be greater than one.")
        elif ability_type is EnemyAbilityType.ENRAGE:
            if self.parameters.get("attack_multiplier", 1.5) <= 1:
                raise ValueError("Enrage attack multiplier must be greater than one.")
        elif ability_type is EnemyAbilityType.DEFENSIVE_STANCE:
            if self.duration_seconds <= 0 or self.parameters.get("physical_defense_multiplier", 1.5) <= 1:
                raise ValueError("Defensive Stance requires a duration and a defense multiplier above one.")
        elif ability_type is EnemyAbilityType.REGENERATION:
            fraction = self.parameters.get("heal_fraction", 0.0)
            amount = self.parameters.get("heal_amount", 0.0)
            if fraction < 0 or amount < 0 or fraction > 1 or (fraction == 0 and amount == 0):
                raise ValueError("Regeneration needs a valid positive heal amount or fraction.")
        elif ability_type is EnemyAbilityType.PIERCING_STRIKE:
            effectiveness = self.parameters.get("defense_effectiveness", 0.5)
            multiplier = self.parameters.get("damage_multiplier", 1.25)
            if not 0.05 <= effectiveness <= 1:
                raise ValueError("Piercing Strike must retain at least five percent of physical defense.")
            if multiplier < 1:
                raise ValueError("Piercing Strike damage multiplier cannot be below one.")


@dataclass(frozen=True)
class AbilityEvent:
    ability_id: str
    name: str
    message: str


@dataclass(frozen=True)
class EnemyAttackProfile:
    damage_multiplier: float = 1.0
    defense_effectiveness: float = 1.0
    ability: EnemyAbilityDefinition | None = None


class EnemyAbilityRuntime:
    """Tracks cooldowns and active effects for one enemy instance."""

    def __init__(self, enemy: "Enemy") -> None:
        self.enemy = enemy
        self._cooldown_until: dict[str, float] = {}
        self._last_activation_at: dict[str, float] = {}
        self._attack_cursor = 0

    @property
    def active_ability_names(self) -> tuple[str, ...]:
        active_ids = set(self.enemy.active_effect_ids)
        return tuple(ability.name for ability in self.enemy.available_abilities if ability.ability_id in active_ids)

    def update(self, now: float) -> tuple[AbilityEvent, ...]:
        now = self._validated_time(now)
        if self.enemy.is_defeated:
            return ()
        events: list[AbilityEvent] = []
        for ability_id in self.enemy.expire_effects(now):
            ability = self.enemy.get_ability(ability_id)
            if ability is not None:
                events.append(AbilityEvent(ability_id, ability.name, f"{ability.name} has ended."))

        for ability in self.enemy.available_abilities:
            if ability.trigger is not AbilityTrigger.HP_THRESHOLD:
                continue
            if ability.activation_threshold is not None and self.enemy.hp_ratio > ability.activation_threshold:
                continue
            event = self._activate(ability, now)
            if event is not None:
                events.append(event)
        return tuple(events)

    def before_enemy_attack(self, now: float) -> tuple[EnemyAttackProfile, tuple[AbilityEvent, ...]]:
        now = self._validated_time(now)
        if self.enemy.is_defeated:
            return EnemyAttackProfile(), ()
        events = list(self.update(now))
        for ability in self.enemy.available_abilities:
            if ability.trigger is not AbilityTrigger.ENEMY_ATTACK:
                continue
            if ability.ability_type in {EnemyAbilityType.HEAVY_STRIKE, EnemyAbilityType.PIERCING_STRIKE}:
                continue
            threshold = ability.activation_threshold
            if threshold is not None and self.enemy.hp_ratio > threshold:
                continue
            event = self._activate(ability, now)
            if event is not None:
                events.append(event)

        attack_abilities = [
            ability for ability in self.enemy.available_abilities
            if ability.ability_type in {EnemyAbilityType.HEAVY_STRIKE, EnemyAbilityType.PIERCING_STRIKE}
        ]
        selected = self._next_ready_attack_ability(attack_abilities, now)
        if selected is None:
            return EnemyAttackProfile(), tuple(events)

        self._cooldown_until[selected.ability_id] = now + selected.cooldown_seconds
        self._last_activation_at[selected.ability_id] = now
        events.append(AbilityEvent(
            selected.ability_id,
            selected.name,
            f"{self.enemy.name} uses {selected.name}!",
        ))
        if selected.ability_type is EnemyAbilityType.PIERCING_STRIKE:
            profile = EnemyAttackProfile(
                damage_multiplier=selected.parameters.get("damage_multiplier", 1.25),
                defense_effectiveness=selected.parameters.get("defense_effectiveness", 0.5),
                ability=selected,
            )
        else:
            profile = EnemyAttackProfile(
                damage_multiplier=selected.parameters.get("damage_multiplier", 1.5),
                ability=selected,
            )
        return profile, tuple(events)

    def clear(self) -> None:
        self.enemy.clear_effects()
        self._cooldown_until.clear()
        self._last_activation_at.clear()

    def _next_ready_attack_ability(
        self,
        abilities: list[EnemyAbilityDefinition],
        now: float,
    ) -> EnemyAbilityDefinition | None:
        if not abilities:
            return None
        start = self._attack_cursor % len(abilities)
        for offset in range(len(abilities)):
            index = (start + offset) % len(abilities)
            ability = abilities[index]
            if ability.activation_threshold is not None and self.enemy.hp_ratio > ability.activation_threshold:
                continue
            if self._ready(ability, now):
                self._attack_cursor = (index + 1) % len(abilities)
                return ability
        return None

    def _ready(self, ability: EnemyAbilityDefinition, now: float) -> bool:
        if ability.ability_id in self.enemy.active_effect_ids:
            return False
        if now <= self._last_activation_at.get(ability.ability_id, float("-inf")):
            return False
        return now >= self._cooldown_until.get(ability.ability_id, float("-inf"))

    @staticmethod
    def _validated_time(now: float) -> float:
        if isinstance(now, bool) or not isinstance(now, (int, float)) or not isfinite(now):
            raise ValueError("Enemy ability time must be a finite number.")
        return float(now)

    def _activate(self, ability: EnemyAbilityDefinition, now: float) -> AbilityEvent | None:
        if not self._ready(ability, now):
            return None

        if ability.ability_type is EnemyAbilityType.ENRAGE:
            multiplier = ability.parameters.get("attack_multiplier", 1.5)
            until = now + ability.duration_seconds if ability.duration_seconds > 0 else None
            self.enemy.add_effect(ability.ability_id, ability.name, "attack", multiplier, until)
            event = AbilityEvent(ability.ability_id, ability.name, f"{self.enemy.name} becomes enraged! Attack increased.")
        elif ability.ability_type is EnemyAbilityType.DEFENSIVE_STANCE:
            multiplier = ability.parameters.get("physical_defense_multiplier", 1.5)
            self.enemy.add_effect(
                ability.ability_id, ability.name, "physical_defense", multiplier, now + ability.duration_seconds,
            )
            event = AbilityEvent(ability.ability_id, ability.name, f"{self.enemy.name} enters a defensive stance.")
        elif ability.ability_type is EnemyAbilityType.REGENERATION:
            amount = (
                self.enemy.max_hp * ability.parameters.get("heal_fraction", 0.0)
                + ability.parameters.get("heal_amount", 0.0)
            )
            healed = self.enemy.heal(amount)
            event = AbilityEvent(ability.ability_id, ability.name, f"{self.enemy.name} regenerates {healed:,.1f} HP.")
        else:
            return None
        self._cooldown_until[ability.ability_id] = now + ability.cooldown_seconds
        self._last_activation_at[ability.ability_id] = now
        return event
