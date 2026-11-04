"""Single tick-driven owner for temporary player and enemy skill effects."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from typing import Mapping

from ...core.stat_calculator import AttributeSheet
from .enemy import Enemy, EnemyClassification


@dataclass
class ActiveStatus:
    target: str
    status: str
    source_id: str
    magnitude: float
    expires_at: float
    next_tick_at: float
    tick_interval: float
    modifiers: dict[str, float] = field(default_factory=dict)
    stacks: int = 1


@dataclass(frozen=True)
class StatusTick:
    target: str
    status: str
    amount: float
    source_id: str


class StatusEffectManager:
    """Effects are transient and intentionally excluded from save data."""

    BOSS_DURATION = {
        EnemyClassification.ELITE: 0.75,
        EnemyClassification.BOSS: 0.55,
        EnemyClassification.WORLD_BOSS: 0.4,
    }

    def __init__(self) -> None:
        self._effects: dict[tuple[str, str], ActiveStatus] = {}

    @property
    def active_effects(self) -> tuple[ActiveStatus, ...]:
        return tuple(self._effects.values())

    def apply(
        self, *, target: str, status: str, source_id: str, magnitude: float, duration: float,
        now: float, tick_interval: float = 1.0, modifiers: Mapping[str, float] | None = None,
        classification: EnemyClassification | None = None,
    ) -> None:
        if target not in {"player", "enemy"} or not status or not source_id:
            raise ValueError("Status effects require a valid target, status, and source.")
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) for value in (magnitude, duration, now, tick_interval)):
            raise ValueError("Status effect numbers must be finite.")
        if duration < 0 or tick_interval <= 0 or magnitude < 0:
            raise ValueError("Status effect magnitude/duration must be non-negative and tick interval positive.")
        duration *= self.BOSS_DURATION.get(classification, 1.0) if target == "enemy" else 1.0
        key_status = f"buff:{source_id}" if status.casefold() == "buff" else status.casefold()
        key = (target, key_status)
        old = self._effects.get(key)
        stacks = min(3, old.stacks + 1) if old and status in {"poison", "burn"} else 1
        self._effects[key] = ActiveStatus(
            target, status.casefold(), source_id, float(magnitude), max(now + duration, old.expires_at if old else 0.0),
            min(old.next_tick_at, now + tick_interval) if old else now + tick_interval,
            float(tick_interval), dict(modifiers or {}), stacks,
        )

    def has(self, status: str, target: str = "enemy") -> bool:
        return any(effect.target == target and effect.status == status.casefold() for effect in self._effects.values())

    def player_attributes(self, attributes: AttributeSheet) -> AttributeSheet:
        values = attributes.to_dict()
        for effect in self._effects.values():
            if effect.target != "player" or effect.status != "buff":
                continue
            for name, value in effect.modifiers.items():
                if name.endswith("_multiplier"):
                    attr = {
                        "hp_regen_multiplier": "hp_regeneration",
                        "mp_regen_multiplier": "mp_regeneration",
                    }.get(name, name.removesuffix("_multiplier"))
                    if attr in values:
                        values[attr] *= value
                elif name == "critical_chance_bonus":
                    values["critical_chance"] += value
        return AttributeSheet(**values)

    def update(self, now: float, player: object, enemy: Enemy | None) -> tuple[StatusTick, ...]:
        if isinstance(now, bool) or not isinstance(now, (int, float)) or not isfinite(now):
            raise ValueError("Status update time must be finite.")
        events: list[StatusTick] = []
        for key, effect in tuple(self._effects.items()):
            target_enemy = enemy if effect.target == "enemy" else None
            if effect.target == "enemy" and target_enemy is None:
                self._effects.pop(key, None)
                continue
            if effect.status in {"burn", "poison", "regeneration"}:
                loops = 0
                while now >= effect.next_tick_at and effect.next_tick_at < effect.expires_at and loops < 10:
                    amount = effect.magnitude * effect.stacks
                    if effect.target == "enemy" and target_enemy is not None:
                        applied = target_enemy.receive_damage(max(1.0, target_enemy.max_hp * amount))
                    else:
                        if effect.status == "regeneration":
                            applied = player.heal(max(1.0, player.maximum_hp * amount))
                        else:
                            applied = player.take_damage(max(1.0, player.maximum_hp * amount))
                    events.append(StatusTick(effect.target, effect.status, applied, effect.source_id))
                    effect.next_tick_at += effect.tick_interval
                    loops += 1
            if now >= effect.expires_at:
                self._effects.pop(key, None)
        return tuple(events)

    def enemy_stunned(self) -> bool:
        return self.has("stun", "enemy")

    def clear(self) -> None:
        self._effects.clear()


__all__ = ["ActiveStatus", "StatusEffectManager", "StatusTick"]
