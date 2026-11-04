"""Static skill definitions and serializable per-character progression."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from typing import Any, Mapping

from .skill_config import load_skill_config


def _skill_defaults() -> tuple[list[str], int]:
    config = load_skill_config()
    starters = list(config["starting_skills"])
    return starters, int(config["max_equipped_skills"])


@dataclass(frozen=True)
class SkillEffect:
    kind: str
    magnitude: float = 0.0
    damage_type: str = "physical"
    scaling: Mapping[str, float] = field(default_factory=dict)
    status: str | None = None
    duration: float = 0.0
    tick_interval: float = 1.0
    modifiers: Mapping[str, float] = field(default_factory=dict)
    target: str = "enemy"
    hits: int = 1

    @classmethod
    def from_dict(cls, raw: object) -> "SkillEffect":
        if not isinstance(raw, Mapping):
            raise ValueError("Skill effects must be JSON objects.")
        kind = str(raw.get("kind", "")).strip().casefold()
        if kind not in {"damage", "healing", "resource_restore", "buff", "debuff", "status"}:
            raise ValueError(f"Unsupported skill effect kind: {kind or '(empty)'}")
        damage_type = str(raw.get("damage_type", "physical")).casefold()
        if damage_type not in {"physical", "magical"}:
            raise ValueError(f"Unsupported skill damage type: {damage_type}")
        scaling_names = {"hp", "mp", "attack", "agility", "stamina", "physical_defense", "magical_defense", "critical_chance", "critical_damage", "attack_speed", "hp_regeneration", "mp_regeneration"}
        def number(key: str, default: float) -> float:
            value = raw.get(key, default)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
                raise ValueError(f"Skill effect {key} must be finite numeric data.")
            return float(value)
        def numeric_map(key: str) -> dict[str, float]:
            value = raw.get(key, {})
            if not isinstance(value, Mapping):
                raise ValueError(f"Skill effect {key} must be an object.")
            result: dict[str, float] = {}
            for attr, amount in value.items():
                if not isinstance(attr, str) or isinstance(amount, bool) or not isinstance(amount, (int, float)) or not isfinite(amount):
                    raise ValueError(f"Skill effect {key} entries must have string keys and finite numbers.")
                if key == "scaling" and attr not in scaling_names:
                    raise ValueError(f"Unsupported skill scaling attribute: {attr}")
                result[attr] = float(amount)
            return result
        duration = number("duration", 0.0)
        interval = number("tick_interval", 1.0)
        magnitude = number("magnitude", 0.0)
        if magnitude < 0 or duration < 0 or interval <= 0:
            raise ValueError("Skill effect duration must be non-negative and tick interval positive.")
        target = str(raw.get("target", "enemy")).casefold()
        if target not in {"enemy", "self"}:
            raise ValueError(f"Unsupported skill effect target: {target}")
        status = str(raw["status"]).casefold() if raw.get("status") else None
        if kind in {"status", "debuff"} and status not in {"burn", "poison", "stun", "slow", "weaken", "defense_break", "regeneration"}:
            raise ValueError(f"Unsupported skill status: {status or '(empty)'}")
        if kind == "damage" and target != "enemy":
            raise ValueError("Damage effects must target the enemy.")
        if kind in {"healing", "resource_restore", "buff"} and target != "self":
            raise ValueError(f"{kind.replace('_', ' ').title()} effects must target self.")
        allowed_modifiers = {
            "attack_multiplier", "physical_defense_multiplier", "magical_defense_multiplier",
            "critical_damage_multiplier", "attack_speed_multiplier", "hp_regen_multiplier",
            "mp_regen_multiplier", "critical_chance_bonus",
        }
        modifiers = numeric_map("modifiers")
        for key, value in modifiers.items():
            if key not in allowed_modifiers:
                raise ValueError(f"Unsupported skill modifier: {key}")
            if key.endswith("_multiplier") and value <= 0:
                raise ValueError(f"Skill modifier {key} must be positive.")
        hits = raw.get("hits", 1)
        if isinstance(hits, bool) or not isinstance(hits, int) or not 1 <= hits <= 10:
            raise ValueError("Skill effect hits must be an integer from 1 to 10.")
        return cls(
            kind=kind, magnitude=magnitude, damage_type=damage_type,
            scaling=numeric_map("scaling"), status=status,
            duration=duration, tick_interval=interval, modifiers=modifiers, target=target, hits=hits,
        )


@dataclass(frozen=True)
class SkillDefinition:
    skill_id: str
    name: str
    description: str
    classification: str
    skill_type: str
    mp_cost: float
    cooldown: float
    required_level: int
    unlock_gold: int
    upgrade_gold: int
    max_level: int
    effects: tuple[SkillEffect, ...]
    prerequisites: tuple[str, ...] = ()
    critical_eligible: bool = False
    icon: str | None = None
    casting_duration: float = 0.0
    rarity: str = "common"
    max_targets: int = 1
    parameters: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: object) -> "SkillDefinition":
        if not isinstance(raw, Mapping):
            raise ValueError("Skill definitions must be JSON objects.")
        skill_id = str(raw.get("id", "")).strip().casefold()
        name = str(raw.get("name", "")).strip()
        if not skill_id or not name or not str(raw.get("description", "")).strip():
            raise ValueError("Skill definitions require a non-empty id, name, and description.")
        classification = str(raw.get("classification", "")).strip().casefold()
        if classification not in {"physical", "magical", "defensive", "support"}:
            raise ValueError(f"Skill '{skill_id}' has an unsupported classification: {classification}")
        skill_type = str(raw.get("type", "")).strip().casefold()
        if skill_type not in {"damage", "healing", "resource", "buff", "debuff", "hybrid"}:
            raise ValueError(f"Skill '{skill_id}' has an unsupported type: {skill_type}")
        def nonnegative_number(key: str, default: float) -> float:
            value = raw.get(key, default)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or value < 0:
                raise ValueError(f"Skill '{skill_id}' {key} must be finite and non-negative.")
            return float(value)
        def integer(key: str, default: int, minimum: int = 0) -> int:
            value = raw.get(key, default)
            if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
                raise ValueError(f"Skill '{skill_id}' {key} must be an integer of at least {minimum}.")
            return value
        effects_raw = raw.get("effects")
        if not isinstance(effects_raw, list) or not effects_raw:
            raise ValueError(f"Skill '{skill_id}' must define at least one effect.")
        prerequisites = raw.get("prerequisites", [])
        if not isinstance(prerequisites, list) or any(not isinstance(value, str) for value in prerequisites):
            raise ValueError(f"Skill '{skill_id}' prerequisites must be a list of IDs.")
        parameters = raw.get("parameters", {})
        if not isinstance(parameters, Mapping):
            raise ValueError(f"Skill '{skill_id}' parameters must be an object.")
        critical_eligible = raw.get("critical_eligible", False)
        if not isinstance(critical_eligible, bool):
            raise ValueError(f"Skill '{skill_id}' critical_eligible must be a boolean.")
        max_targets = integer("max_targets", 1, 1)
        if max_targets > 20:
            raise ValueError(f"Skill '{skill_id}' max_targets cannot exceed 20.")
        return cls(
            skill_id=skill_id, name=name, description=str(raw.get("description", "")).strip(),
            classification=classification, skill_type=skill_type, mp_cost=nonnegative_number("mp_cost", 0),
            cooldown=nonnegative_number("cooldown", 0), required_level=integer("required_level", 1, 1),
            unlock_gold=integer("unlock_gold", 0), upgrade_gold=integer("upgrade_gold", 0),
            max_level=integer("max_level", 1, 1), effects=tuple(SkillEffect.from_dict(item) for item in effects_raw),
            prerequisites=tuple(value.casefold() for value in prerequisites),
            critical_eligible=critical_eligible,
            icon=str(raw["icon"]) if raw.get("icon") is not None else None,
            casting_duration=nonnegative_number("casting_duration", 0),
            rarity=str(raw.get("rarity", "common")).casefold(),
            max_targets=max_targets,
            parameters=dict(parameters),
        )


@dataclass
class SkillProgressState:
    unlocked_skill_ids: list[str] = field(default_factory=lambda: _skill_defaults()[0])
    skill_levels: dict[str, int] = field(default_factory=lambda: {skill_id: 1 for skill_id in _skill_defaults()[0]})
    equipped_skill_ids: list[str] = field(default_factory=lambda: _skill_defaults()[0])
    max_equipped_skills: int = field(default_factory=lambda: _skill_defaults()[1])

    def __post_init__(self) -> None:
        self.unlocked_skill_ids = list(dict.fromkeys(str(value).casefold() for value in self.unlocked_skill_ids if isinstance(value, str)))
        self.skill_levels = {str(key).casefold(): value for key, value in self.skill_levels.items() if isinstance(key, str) and isinstance(value, int) and not isinstance(value, bool) and value > 0}
        self.equipped_skill_ids = list(dict.fromkeys(str(value).casefold() for value in self.equipped_skill_ids if isinstance(value, str)))
        if isinstance(self.max_equipped_skills, bool) or not isinstance(self.max_equipped_skills, int) or self.max_equipped_skills < 1:
            self.max_equipped_skills = 6
        configured_capacity = _skill_defaults()[1]
        self.max_equipped_skills = min(self.max_equipped_skills, configured_capacity)

    def to_dict(self) -> dict[str, Any]:
        return {"unlocked_skill_ids": list(self.unlocked_skill_ids), "skill_levels": dict(self.skill_levels),
                "equipped_skill_ids": list(self.equipped_skill_ids), "max_equipped_skills": self.max_equipped_skills}

    @classmethod
    def from_dict(cls, raw: object) -> "SkillProgressState":
        if not isinstance(raw, Mapping):
            return cls()
        starters, capacity = _skill_defaults()
        unlocked = raw.get("unlocked_skill_ids", starters)
        levels = raw.get("skill_levels", {skill_id: 1 for skill_id in starters})
        equipped = raw.get("equipped_skill_ids", starters)
        return cls(unlocked if isinstance(unlocked, list) else [], levels if isinstance(levels, Mapping) else {},
                   equipped if isinstance(equipped, list) else [], raw.get("max_equipped_skills", capacity))
