"""Persistent, aggregate statistics for completed combat actions."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
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
    total_elites_defeated: int = 0
    total_bosses_defeated: int = 0
    total_world_bosses_defeated: int = 0
    total_skills_used: int = 0
    total_skill_damage: float = 0.0
    total_skill_healing: float = 0.0
    total_skill_mp_consumed: float = 0.0
    total_skill_mp_restored: float = 0.0
    total_skill_critical_hits: int = 0
    skill_usage: dict[str, int] = field(default_factory=dict)
    skill_damage: dict[str, float] = field(default_factory=dict)

    def record_player_attack(self, damage: float, critical: bool) -> None:
        self.total_damage_dealt += max(0.0, float(damage))
        self.total_attacks_performed += 1
        if critical:
            self.total_critical_hits += 1

    def record_damage_received(self, damage: float) -> None:
        self.total_damage_received += max(0.0, float(damage))

    def record_enemy_defeated(self, exp_reward: int, classification: str = "common") -> None:
        self.total_enemies_defeated += 1
        self.total_exp_earned += max(0, int(exp_reward))
        raw_classification = getattr(classification, "value", classification)
        normalized = str(raw_classification).strip().casefold().replace(" ", "_")
        if normalized == "elite":
            self.total_elites_defeated += 1
        elif normalized == "boss":
            self.total_bosses_defeated += 1
        elif normalized in {"world_boss", "worldboss"}:
            self.total_world_bosses_defeated += 1

    def record_skill_use(
        self, skill_id: str, *, damage: float = 0.0, healing: float = 0.0,
        mp_consumed: float = 0.0, mp_restored: float = 0.0, critical: bool = False,
        critical_hits: int | None = None,
    ) -> None:
        key = str(skill_id).casefold()
        self.total_skills_used += 1
        self.total_skill_damage += max(0.0, float(damage))
        self.total_skill_healing += max(0.0, float(healing))
        self.total_skill_mp_consumed += max(0.0, float(mp_consumed))
        self.total_skill_mp_restored += max(0.0, float(mp_restored))
        self.skill_usage[key] = self.skill_usage.get(key, 0) + 1
        self.skill_damage[key] = self.skill_damage.get(key, 0.0) + max(0.0, float(damage))
        count = (1 if critical else 0) if critical_hits is None else max(0, int(critical_hits))
        self.total_skill_critical_hits += count
        self.total_critical_hits += count

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CombatStatistics":
        if not isinstance(data, Mapping):
            return cls()
        values: dict[str, int | float] = {}
        for name in ("total_damage_dealt", "total_damage_received", "total_skill_damage", "total_skill_healing", "total_skill_mp_consumed", "total_skill_mp_restored"):
            raw = data.get(name, 0.0)
            if isinstance(raw, bool) or not isinstance(raw, (int, float)) or not isfinite(raw):
                raw = 0.0
            values[name] = max(0.0, float(raw))
        for name in (
            "total_enemies_defeated", "total_critical_hits", "total_attacks_performed", "total_exp_earned",
            "total_elites_defeated", "total_bosses_defeated", "total_world_bosses_defeated",
            "total_skills_used", "total_skill_critical_hits",
        ):
            raw = data.get(name, 0)
            if isinstance(raw, bool) or not isinstance(raw, int):
                raw = 0
            values[name] = max(0, raw)
        for name in ("skill_usage", "skill_damage"):
            raw = data.get(name, {})
            if not isinstance(raw, Mapping):
                raw = {}
            cleaned: dict[str, int | float] = {}
            for key, value in raw.items():
                if not isinstance(key, str):
                    continue
                if name == "skill_usage" and isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                    cleaned[key.casefold()] = value
                elif name == "skill_damage" and isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value) and value >= 0:
                    cleaned[key.casefold()] = float(value)
            values[name] = cleaned
        return cls(**values)
