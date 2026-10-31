"""Persistent, aggregate statistics for completed combat actions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from typing import Any, Mapping


@dataclass
class CombatStatistics:
    total_damage_dealt: float = 0.0
    total_damage_received: float = 0.0
    total_enemies_defeated: int = 0
    total_critical_hits: int = 0
    total_attacks_performed: int = 0
    total_exp_earned: int = 0

    def record_player_attack(self, damage: float, critical: bool) -> None:
        self.total_damage_dealt += max(0.0, float(damage))
        self.total_attacks_performed += 1
        if critical:
            self.total_critical_hits += 1

    def record_damage_received(self, damage: float) -> None:
        self.total_damage_received += max(0.0, float(damage))

    def record_enemy_defeated(self, exp_reward: int) -> None:
        self.total_enemies_defeated += 1
        self.total_exp_earned += max(0, int(exp_reward))

    def to_dict(self) -> dict[str, int | float]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CombatStatistics":
        if not isinstance(data, Mapping):
            return cls()
        values: dict[str, int | float] = {}
        for name in ("total_damage_dealt", "total_damage_received"):
            raw = data.get(name, 0.0)
            if isinstance(raw, bool) or not isinstance(raw, (int, float)) or not isfinite(raw):
                raw = 0.0
            values[name] = max(0.0, float(raw))
        for name in (
            "total_enemies_defeated", "total_critical_hits", "total_attacks_performed", "total_exp_earned",
        ):
            raw = data.get(name, 0)
            if isinstance(raw, bool) or not isinstance(raw, int):
                raw = 0
            values[name] = max(0, raw)
        return cls(**values)
