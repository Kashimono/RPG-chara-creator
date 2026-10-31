"""Enemy definitions and mutable encounter instances."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from uuid import uuid4


@dataclass(frozen=True)
class EnemyDefinition:
    definition_id: str
    name: str
    max_hp: float
    attack: float
    exp_reward: int
    attack_interval: float
    physical_defense: float = 0.0
    magical_defense: float = 0.0
    description: str = "An ordinary enemy."
    classification: str = "Ordinary"

    def __post_init__(self) -> None:
        if not self.definition_id.strip() or not self.name.strip():
            raise ValueError("Enemy definitions require an ID and a name.")
        numeric_values = (self.max_hp, self.attack, self.physical_defense, self.magical_defense, self.attack_interval)
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) for value in numeric_values):
            raise ValueError("Enemy combat attributes must be finite numbers.")
        if self.max_hp <= 0 or self.attack < 0 or self.physical_defense < 0 or self.magical_defense < 0 or self.attack_interval <= 0:
            raise ValueError("Enemy HP and attack interval must be positive; other attributes cannot be negative.")
        if isinstance(self.exp_reward, bool) or not isinstance(self.exp_reward, int) or self.exp_reward < 0:
            raise ValueError("Enemy EXP reward must be a non-negative whole number.")


@dataclass
class Enemy:
    """A single enemy spawned for one encounter."""

    definition: EnemyDefinition
    enemy_id: str = field(default_factory=lambda: uuid4().hex)
    current_hp: float | None = None

    def __post_init__(self) -> None:
        if self.current_hp is None:
            self.current_hp = float(self.definition.max_hp)
        else:
            self.current_hp = min(float(self.definition.max_hp), max(0.0, float(self.current_hp)))

    @classmethod
    def spawn(cls, definition: EnemyDefinition) -> "Enemy":
        return cls(definition=definition)

    @property
    def definition_id(self) -> str:
        return self.definition.definition_id

    @property
    def name(self) -> str:
        return self.definition.name

    @property
    def max_hp(self) -> float:
        return float(self.definition.max_hp)

    @property
    def attack(self) -> float:
        return float(self.definition.attack)

    @property
    def physical_defense(self) -> float:
        return float(self.definition.physical_defense)

    @property
    def magical_defense(self) -> float:
        return float(self.definition.magical_defense)

    @property
    def exp_reward(self) -> int:
        return self.definition.exp_reward

    @property
    def attack_interval(self) -> float:
        return float(self.definition.attack_interval)

    @property
    def description(self) -> str:
        return self.definition.description

    @property
    def classification(self) -> str:
        return self.definition.classification

    @property
    def is_defeated(self) -> bool:
        return self.current_hp <= 0

    @property
    def hp_ratio(self) -> float:
        return min(1.0, max(0.0, self.current_hp / self.max_hp))

    def receive_damage(self, amount: float) -> float:
        if isinstance(amount, bool) or not isinstance(amount, (int, float)) or not isfinite(amount) or amount < 0:
            raise ValueError("Damage must be a finite non-negative number.")
        before = self.current_hp
        self.current_hp = min(self.max_hp, max(0.0, before - float(amount)))
        return before - self.current_hp

    def reset(self) -> None:
        self.current_hp = self.max_hp

    def to_dict(self) -> dict[str, object]:
        """Return display information without persisting encounter state."""
        return {
            "enemy_id": self.enemy_id,
            "definition_id": self.definition_id,
            "name": self.name,
            "classification": self.classification,
            "current_hp": self.current_hp,
            "max_hp": self.max_hp,
            "attack": self.attack,
            "physical_defense": self.physical_defense,
            "magical_defense": self.magical_defense,
            "exp_reward": self.exp_reward,
            "attack_interval": self.attack_interval,
            "description": self.description,
        }
