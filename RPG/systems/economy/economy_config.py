"""Validated data-driven Gold rewards and training shop content."""

from __future__ import annotations

import json
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Any, Mapping

from ...constants import STAT_NAMES
from .currency import MAX_CURRENCY_VALUE


@dataclass(frozen=True)
class TrainingDefinition:
    training_id: str
    name: str
    description: str
    stat_name: str
    cost: int
    stat_points: int = 1

    def __post_init__(self) -> None:
        if any(not isinstance(value, str) or not value.strip() for value in (
            self.training_id, self.name, self.description, self.stat_name,
        )):
            raise ValueError("Training options require an ID, name, description, and stat name.")
        if self.stat_name not in STAT_NAMES:
            raise ValueError(f"Training '{self.training_id}' targets an unknown stat: {self.stat_name}.")
        for field_name in ("cost", "stat_points"):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"Training {field_name} must be a positive whole number.")
        if self.cost > MAX_CURRENCY_VALUE:
            raise ValueError("Training cost exceeds the supported Gold range.")


@dataclass(frozen=True)
class EconomyConfig:
    enemy_gold_rewards: Mapping[str, int]
    global_gold_multiplier: float = 1.0
    classification_gold_multipliers: Mapping[str, float] | None = None
    enemy_gold_multipliers: Mapping[str, float] | None = None
    transaction_history_limit: int = 100
    trainings: tuple[TrainingDefinition, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.enemy_gold_rewards, Mapping):
            raise ValueError("Enemy Gold rewards must be an object keyed by enemy ID.")
        rewards: dict[str, int] = {}
        for enemy_id, amount in self.enemy_gold_rewards.items():
            key = self._key(enemy_id, "enemy ID")
            if key in rewards:
                raise ValueError(f"Duplicate enemy reward ID after normalization: {key}.")
            if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0 or amount > MAX_CURRENCY_VALUE:
                raise ValueError(f"Base Gold reward for '{key}' must be a positive safe integer.")
            rewards[key] = amount
        object.__setattr__(self, "enemy_gold_rewards", rewards)

        global_multiplier = self.validate_multiplier(self.global_gold_multiplier, "global Gold")
        object.__setattr__(self, "global_gold_multiplier", global_multiplier)
        class_values = self._normalize_multipliers(
            {} if self.classification_gold_multipliers is None else self.classification_gold_multipliers,
            "classification",
        )
        enemy_values = self._normalize_multipliers(
            {} if self.enemy_gold_multipliers is None else self.enemy_gold_multipliers,
            "enemy",
        )
        valid_classifications = {"common", "uncommon", "rare", "elite", "boss", "world_boss"}
        if not set(class_values).issubset(valid_classifications):
            raise ValueError("Classification multipliers contain an unknown enemy classification.")
        if not set(enemy_values).issubset(rewards):
            raise ValueError("Enemy multipliers must reference an enemy with a configured base Gold reward.")
        object.__setattr__(self, "classification_gold_multipliers", class_values)
        object.__setattr__(self, "enemy_gold_multipliers", enemy_values)

        limit = self.transaction_history_limit
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("Transaction history limit must be a positive whole number.")
        trainings = tuple(self.trainings)
        if any(not isinstance(item, TrainingDefinition) for item in trainings):
            raise ValueError("Economy config contains an invalid training definition.")
        if len({item.training_id.casefold() for item in trainings}) != len(trainings):
            raise ValueError("Training IDs must be unique.")
        object.__setattr__(self, "trainings", trainings)

    @classmethod
    def load(cls, path: str | Path) -> "EconomyConfig":
        source = Path(path)
        if not source.is_file():
            raise ValueError(f"Economy configuration file is missing: {source}")
        try:
            data = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"Could not load economy configuration '{source}': {exc}") from exc
        if not isinstance(data, Mapping):
            raise ValueError("Economy configuration root must be a JSON object.")
        try:
            trainings = tuple(TrainingDefinition(**item) for item in data.get("trainings", []))
            return cls(
                enemy_gold_rewards=data["enemy_gold_rewards"],
                global_gold_multiplier=data.get("global_gold_multiplier", 1.0),
                classification_gold_multipliers=data.get("classification_gold_multipliers", {}),
                enemy_gold_multipliers=data.get("enemy_gold_multipliers", {}),
                transaction_history_limit=data.get("transaction_history_limit", 100),
                trainings=trainings,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Malformed economy configuration '{source}': {exc}") from exc

    @classmethod
    def load_default(cls) -> "EconomyConfig":
        return cls.load(Path(__file__).resolve().parents[2] / "data" / "economy.json")

    def base_reward_for(self, enemy_id: str) -> int:
        try:
            return self.enemy_gold_rewards[enemy_id.casefold()]
        except (AttributeError, KeyError) as exc:
            raise ValueError(f"No base Gold reward is configured for enemy '{enemy_id}'.") from exc

    def multiplier_for_enemy(self, enemy_id: str) -> float:
        return self.enemy_gold_multipliers.get(enemy_id.casefold(), 1.0)

    def multiplier_for_classification(self, classification: str) -> float:
        return self.classification_gold_multipliers.get(classification.casefold(), 1.0)

    @staticmethod
    def _key(value: object, label: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Economy {label} must be a non-empty string.")
        return value.strip().casefold()

    @classmethod
    def validate_multiplier(cls, value: object, label: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or value <= 0:
            raise ValueError(f"{label} multiplier must be finite and positive.")
        return float(value)

    @classmethod
    def _normalize_multipliers(cls, values: Mapping[str, Any], label: str) -> dict[str, float]:
        if not isinstance(values, Mapping):
            raise ValueError(f"{label.title()} multipliers must be an object.")
        return {
            cls._key(key, f"{label} multiplier key"): cls.validate_multiplier(value, f"{label} reward")
            for key, value in values.items()
        }


__all__ = ["EconomyConfig", "TrainingDefinition"]
