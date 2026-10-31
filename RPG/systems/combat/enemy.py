"""Validated enemy definitions and mutable, uniquely identified encounters."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from uuid import uuid4

from .enemy_ability import EnemyAbilityDefinition


class EnemyClassification(str, Enum):
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    ELITE = "elite"
    BOSS = "boss"
    WORLD_BOSS = "world_boss"

    @classmethod
    def from_value(cls, value: str | "EnemyClassification") -> "EnemyClassification":
        if isinstance(value, cls):
            return value
        normalized = str(value).strip().casefold().replace(" ", "_")
        if normalized == "ordinary":
            normalized = "common"
        try:
            return cls(normalized)
        except ValueError as exc:
            raise ValueError(f"Unknown enemy classification: {value}") from exc

    @property
    def display_name(self) -> str:
        return {
            self.COMMON: "Common",
            self.UNCOMMON: "Uncommon",
            self.RARE: "Rare",
            self.ELITE: "Elite",
            self.BOSS: "Boss",
            self.WORLD_BOSS: "World Boss",
        }[self]

    @property
    def description(self) -> str:
        return {
            self.COMMON: "Basic enemies with standard attributes.",
            self.UNCOMMON: "Stronger enemies with improved attributes.",
            self.RARE: "Uncommon encounters with distinctive strengths.",
            self.ELITE: "Powerful optional encounters with increased rewards.",
            self.BOSS: "Dedicated multi-phase encounters with major rewards.",
            self.WORLD_BOSS: "Exceptional encounters with the greatest challenge and rewards.",
        }[self]

    @property
    def color_hex(self) -> str:
        return {
            self.COMMON: "#aeb8c4",
            self.UNCOMMON: "#60c878",
            self.RARE: "#6ba6ff",
            self.ELITE: "#b783ff",
            self.BOSS: "#ef6868",
            self.WORLD_BOSS: "#e9bd55",
        }[self]

    @property
    def difficulty_multiplier(self) -> float:
        """Optional category-wide multiplier; individual definitions can tune further."""
        return CLASSIFICATION_DIFFICULTY_MULTIPLIERS[self]


CLASSIFICATION_DIFFICULTY_MULTIPLIERS: dict[EnemyClassification, float] = {
    EnemyClassification.COMMON: 1.0,
    EnemyClassification.UNCOMMON: 1.0,
    EnemyClassification.RARE: 1.0,
    EnemyClassification.ELITE: 1.0,
    EnemyClassification.BOSS: 1.0,
    EnemyClassification.WORLD_BOSS: 1.0,
}


@dataclass(frozen=True)
class EnemyScaling:
    enabled: bool = True
    base_level: int = 1
    max_hp_per_level: float = 0.0
    attack_per_level: float = 0.0
    physical_defense_per_level: float = 0.0
    magical_defense_per_level: float = 0.0
    exp_per_level: float = 0.0

    def __post_init__(self) -> None:
        if not isinstance(self.enabled, bool):
            raise ValueError("Enemy scaling enabled must be a boolean.")
        if isinstance(self.base_level, bool) or not isinstance(self.base_level, int) or self.base_level < 1:
            raise ValueError("Enemy scaling base_level must be a positive whole number.")
        for field_name in (
            "max_hp_per_level", "attack_per_level", "physical_defense_per_level",
            "magical_defense_per_level", "exp_per_level",
        ):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or value < 0:
                raise ValueError(f"Enemy scaling {field_name} must be finite and non-negative.")


@dataclass(frozen=True)
class BossPhaseDefinition:
    phase_id: str
    name: str
    hp_threshold: float
    description: str = ""
    attack_multiplier: float = 1.0
    attack_interval_multiplier: float = 1.0
    physical_defense_multiplier: float = 1.0
    magical_defense_multiplier: float = 1.0
    ability_ids: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.phase_id, str) or not self.phase_id.strip() or not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Boss phases require an ID and a name.")
        if isinstance(self.hp_threshold, bool) or not isinstance(self.hp_threshold, (int, float)) or not isfinite(self.hp_threshold) or not 0 < self.hp_threshold <= 1:
            raise ValueError("Boss phase threshold must be greater than zero and at most one.")
        for field_name in (
            "attack_multiplier", "attack_interval_multiplier", "physical_defense_multiplier",
            "magical_defense_multiplier",
        ):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or value <= 0:
                raise ValueError(f"Boss phase {field_name} must be finite and positive.")
        if self.ability_ids is not None:
            if isinstance(self.ability_ids, str):
                raise ValueError("Boss phase ability IDs must be a list of IDs.")
            raw_ability_ids = tuple(self.ability_ids)
            if any(not isinstance(ability_id, str) or not ability_id.strip() for ability_id in raw_ability_ids):
                raise ValueError("Boss phase ability IDs must be non-empty strings.")
            object.__setattr__(self, "ability_ids", raw_ability_ids)


@dataclass(frozen=True)
class ScaledEnemyAttributes:
    level: int
    max_hp: float
    attack: float
    physical_defense: float
    magical_defense: float
    exp_reward: int


@dataclass(frozen=True)
class EnemyDefinition:
    """Immutable base content; scaling never writes back into these values."""

    definition_id: str
    name: str
    max_hp: float
    attack: float
    exp_reward: int
    attack_interval: float
    physical_defense: float = 0.0
    magical_defense: float = 0.0
    description: str = "An ordinary enemy."
    classification: EnemyClassification | str = EnemyClassification.COMMON
    image_asset: str | None = None
    abilities: tuple[EnemyAbilityDefinition, ...] = ()
    boss_phases: tuple[BossPhaseDefinition, ...] = ()
    loot_table_id: str | None = None
    difficulty_multiplier: float = 1.0
    scaling: EnemyScaling | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.definition_id, str) or not self.definition_id.strip():
            raise ValueError("Enemy definitions require a non-empty ID.")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Enemy definitions require a non-empty name.")
        if not isinstance(self.description, str) or not self.description.strip():
            raise ValueError(f"Enemy '{self.definition_id}' requires a description.")
        object.__setattr__(self, "classification", EnemyClassification.from_value(self.classification))
        object.__setattr__(self, "abilities", tuple(self.abilities))
        object.__setattr__(self, "boss_phases", tuple(self.boss_phases))
        numeric_values = (
            self.max_hp, self.attack, self.physical_defense, self.magical_defense,
            self.attack_interval, self.difficulty_multiplier,
        )
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) for value in numeric_values):
            raise ValueError(f"Enemy '{self.definition_id}' attributes must be finite numbers.")
        if self.max_hp <= 0 or self.attack < 0 or self.physical_defense < 0 or self.magical_defense < 0 or self.attack_interval <= 0:
            raise ValueError(f"Enemy '{self.definition_id}' has invalid HP, attack, defense, or attack interval.")
        if self.difficulty_multiplier <= 0:
            raise ValueError(f"Enemy '{self.definition_id}' difficulty multiplier must be positive.")
        if isinstance(self.exp_reward, bool) or not isinstance(self.exp_reward, int) or self.exp_reward < 0:
            raise ValueError(f"Enemy '{self.definition_id}' EXP reward must be a non-negative whole number.")
        if any(not isinstance(ability, EnemyAbilityDefinition) for ability in self.abilities):
            raise ValueError(f"Enemy '{self.definition_id}' contains an invalid ability definition.")
        if len({ability.ability_id.casefold() for ability in self.abilities}) != len(self.abilities):
            raise ValueError(f"Enemy '{self.definition_id}' contains duplicate ability IDs.")
        ability_ids = {ability.ability_id for ability in self.abilities}
        if self.boss_phases:
            if any(not isinstance(phase, BossPhaseDefinition) for phase in self.boss_phases):
                raise ValueError(f"Boss '{self.definition_id}' contains an invalid phase definition.")
            if len({phase.phase_id.casefold() for phase in self.boss_phases}) != len(self.boss_phases):
                raise ValueError(f"Boss '{self.definition_id}' contains duplicate phase IDs.")
            if self.classification not in {EnemyClassification.BOSS, EnemyClassification.WORLD_BOSS}:
                raise ValueError(f"Non-boss enemy '{self.definition_id}' cannot define boss phases.")
            if self.boss_phases[0].hp_threshold != 1.0:
                raise ValueError(f"Boss '{self.definition_id}' must define its opening phase at 100% HP.")
            thresholds = [phase.hp_threshold for phase in self.boss_phases]
            if any(current <= following for current, following in zip(thresholds, thresholds[1:])):
                raise ValueError(f"Boss '{self.definition_id}' phase thresholds must descend strictly.")
            for phase in self.boss_phases:
                if phase.ability_ids is not None and not set(phase.ability_ids).issubset(ability_ids):
                    raise ValueError(f"Boss '{self.definition_id}' phase '{phase.phase_id}' references an unknown ability.")
        elif self.classification in {EnemyClassification.BOSS, EnemyClassification.WORLD_BOSS}:
            raise ValueError(f"Boss '{self.definition_id}' must define at least one phase.")
        if self.image_asset is not None and (not isinstance(self.image_asset, str) or not self.image_asset.strip()):
            raise ValueError(f"Enemy '{self.definition_id}' has an invalid image asset reference.")
        if self.loot_table_id is not None and (not isinstance(self.loot_table_id, str) or not self.loot_table_id.strip()):
            raise ValueError(f"Enemy '{self.definition_id}' has an empty loot table reference.")
        if self.scaling is not None and not isinstance(self.scaling, EnemyScaling):
            raise ValueError(f"Enemy '{self.definition_id}' has invalid scaling settings.")

    def scaled_attributes(self, level: int) -> ScaledEnemyAttributes:
        if isinstance(level, bool) or not isinstance(level, int) or level < 1:
            raise ValueError("Enemy level must be a positive whole number.")
        scaling = self.scaling
        delta = max(0, level - scaling.base_level) if scaling and scaling.enabled else 0
        difficulty = float(self.difficulty_multiplier * self.classification.difficulty_multiplier)

        def scale(base: float, rate: float) -> float:
            try:
                value = float(base) * difficulty * (1.0 + rate * delta)
            except OverflowError as exc:
                raise ValueError(f"Scaling enemy '{self.definition_id}' to level {level} exceeds numeric limits.") from exc
            if not isfinite(value):
                raise ValueError(f"Scaling enemy '{self.definition_id}' to level {level} exceeds numeric limits.")
            return value

        max_hp_rate = scaling.max_hp_per_level if scaling else 0.0
        attack_rate = scaling.attack_per_level if scaling else 0.0
        physical_rate = scaling.physical_defense_per_level if scaling else 0.0
        magical_rate = scaling.magical_defense_per_level if scaling else 0.0
        exp_rate = scaling.exp_per_level if scaling else 0.0
        try:
            base_exp = float(self.exp_reward)
        except OverflowError as exc:
            raise ValueError(f"Scaling enemy '{self.definition_id}' to level {level} exceeds numeric limits.") from exc
        exp_value = scale(base_exp, exp_rate)
        return ScaledEnemyAttributes(
            level=level,
            max_hp=scale(self.max_hp, max_hp_rate),
            attack=scale(self.attack, attack_rate),
            physical_defense=scale(self.physical_defense, physical_rate),
            magical_defense=scale(self.magical_defense, magical_rate),
            exp_reward=max(0, int(round(exp_value))),
        )


@dataclass
class EnemyTemporaryEffect:
    ability_id: str
    name: str
    attribute: str
    multiplier: float
    expires_at: float | None


@dataclass
class Enemy:
    """One scaled enemy instance; mutable state is isolated from its definition."""

    definition: EnemyDefinition
    enemy_id: str = field(default_factory=lambda: uuid4().hex)
    current_hp: float | None = None
    level: int = 1
    reward_claimed: bool = False
    _phase_index: int = field(default=-1, init=False, repr=False)
    _effects: dict[str, EnemyTemporaryEffect] = field(default_factory=dict, init=False, repr=False)
    _scaled: ScaledEnemyAttributes = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._scaled = self.definition.scaled_attributes(self.level)
        if self.current_hp is None:
            self.current_hp = self.max_hp
        else:
            if isinstance(self.current_hp, bool) or not isinstance(self.current_hp, (int, float)) or not isfinite(self.current_hp):
                raise ValueError("Enemy current HP must be a finite number.")
            self.current_hp = min(self.max_hp, max(0.0, float(self.current_hp)))
        if self.definition.boss_phases:
            self._phase_index = 0

    @classmethod
    def spawn(cls, definition: EnemyDefinition, level: int = 1) -> "Enemy":
        return cls(definition=definition, level=level)

    @property
    def definition_id(self) -> str:
        return self.definition.definition_id

    @property
    def name(self) -> str:
        return self.definition.name

    @property
    def classification(self) -> EnemyClassification:
        return self.definition.classification

    @property
    def classification_name(self) -> str:
        return self.classification.display_name

    @property
    def max_hp(self) -> float:
        return self._scaled.max_hp

    @property
    def attack(self) -> float:
        multiplier = self.boss_phase.attack_multiplier if self.boss_phase else 1.0
        return self._finite_attribute(self._scaled.attack * multiplier * self._effect_multiplier("attack"), "Attack")

    @property
    def physical_defense(self) -> float:
        multiplier = self.boss_phase.physical_defense_multiplier if self.boss_phase else 1.0
        return self._finite_attribute(
            self._scaled.physical_defense * multiplier * self._effect_multiplier("physical_defense"),
            "Physical Defense",
        )

    @property
    def magical_defense(self) -> float:
        multiplier = self.boss_phase.magical_defense_multiplier if self.boss_phase else 1.0
        return self._finite_attribute(
            self._scaled.magical_defense * multiplier * self._effect_multiplier("magical_defense"),
            "Magical Defense",
        )

    @property
    def exp_reward(self) -> int:
        return self._scaled.exp_reward

    @property
    def attack_interval(self) -> float:
        multiplier = self.boss_phase.attack_interval_multiplier if self.boss_phase else 1.0
        return self._finite_attribute(float(self.definition.attack_interval) * multiplier, "Attack Interval")

    @property
    def description(self) -> str:
        return self.definition.description

    @property
    def image_asset(self) -> str | None:
        return self.definition.image_asset

    @property
    def loot_table_id(self) -> str | None:
        return self.definition.loot_table_id

    @property
    def is_defeated(self) -> bool:
        return self.current_hp <= 0

    @property
    def hp_ratio(self) -> float:
        return min(1.0, max(0.0, self.current_hp / self.max_hp))

    @property
    def boss_phase(self) -> BossPhaseDefinition | None:
        if self._phase_index < 0:
            return None
        return self.definition.boss_phases[self._phase_index]

    @property
    def phase_index(self) -> int:
        return self._phase_index

    @property
    def available_abilities(self) -> tuple[EnemyAbilityDefinition, ...]:
        phase = self.boss_phase
        if phase is None or phase.ability_ids is None:
            return self.definition.abilities
        allowed = set(phase.ability_ids)
        return tuple(ability for ability in self.definition.abilities if ability.ability_id in allowed)

    @property
    def active_effect_ids(self) -> tuple[str, ...]:
        return tuple(self._effects)

    @property
    def active_effect_names(self) -> tuple[str, ...]:
        return tuple(effect.name for effect in self._effects.values())

    def get_ability(self, ability_id: str) -> EnemyAbilityDefinition | None:
        return next((ability for ability in self.definition.abilities if ability.ability_id == ability_id), None)

    def receive_damage(self, amount: float) -> float:
        if isinstance(amount, bool) or not isinstance(amount, (int, float)) or not isfinite(amount) or amount < 0:
            raise ValueError("Damage must be a finite non-negative number.")
        before = self.current_hp
        self.current_hp = min(self.max_hp, max(0.0, before - float(amount)))
        return before - self.current_hp

    def heal(self, amount: float) -> float:
        if isinstance(amount, bool) or not isinstance(amount, (int, float)) or not isfinite(amount) or amount < 0:
            raise ValueError("Healing must be a finite non-negative number.")
        before = self.current_hp
        self.current_hp = min(self.max_hp, before + float(amount))
        return self.current_hp - before

    def reset(self) -> None:
        self.current_hp = self.max_hp
        self.reward_claimed = False
        self.clear_effects()
        self._phase_index = 0 if self.definition.boss_phases else -1

    def claim_reward(self) -> bool:
        if not self.is_defeated or self.reward_claimed:
            return False
        self.reward_claimed = True
        return True

    def set_phase(self, index: int) -> None:
        if not 0 <= index < len(self.definition.boss_phases):
            raise ValueError(f"Invalid phase index {index} for enemy '{self.definition_id}'.")
        if index < self._phase_index:
            raise ValueError("Boss phases cannot move backwards.")
        self._phase_index = index

    def add_effect(self, ability_id: str, name: str, attribute: str, multiplier: float, expires_at: float | None) -> None:
        if not isinstance(ability_id, str) or not ability_id.strip() or not isinstance(name, str) or not name.strip():
            raise ValueError("Enemy effects require an ability ID and display name.")
        if attribute not in {"attack", "physical_defense", "magical_defense"}:
            raise ValueError(f"Unsupported enemy effect attribute: {attribute}")
        if isinstance(multiplier, bool) or not isinstance(multiplier, (int, float)) or not isfinite(multiplier) or multiplier <= 0:
            raise ValueError("Enemy effect multipliers must be finite and positive.")
        if expires_at is not None and (
            isinstance(expires_at, bool) or not isinstance(expires_at, (int, float)) or not isfinite(expires_at)
        ):
            raise ValueError("Enemy effect expiration must be finite or None.")
        self._effects[ability_id] = EnemyTemporaryEffect(ability_id, name, attribute, multiplier, expires_at)

    def expire_effects(self, now: float) -> tuple[str, ...]:
        expired = tuple(
            ability_id for ability_id, effect in self._effects.items()
            if effect.expires_at is not None and now >= effect.expires_at
        )
        for ability_id in expired:
            del self._effects[ability_id]
        return expired

    def clear_effects(self) -> None:
        self._effects.clear()

    def to_dict(self) -> dict[str, object]:
        """Return encounter information for the UI; saves never include this object."""
        return {
            "enemy_id": self.enemy_id,
            "definition_id": self.definition_id,
            "name": self.name,
            "classification": self.classification.value,
            "level": self.level,
            "phase": self.boss_phase.name if self.boss_phase else None,
            "current_hp": self.current_hp,
            "max_hp": self.max_hp,
            "attack": self.attack,
            "physical_defense": self.physical_defense,
            "magical_defense": self.magical_defense,
            "exp_reward": self.exp_reward,
            "attack_interval": self.attack_interval,
            "description": self.description,
            "active_effects": list(self.active_effect_names),
        }

    def _effect_multiplier(self, attribute: str) -> float:
        multiplier = 1.0
        for effect in self._effects.values():
            if effect.attribute == attribute:
                multiplier *= effect.multiplier
        return multiplier

    def _finite_attribute(self, value: float, name: str) -> float:
        if not isfinite(value):
            raise ValueError(f"Enemy '{self.definition_id}' effective {name} exceeds numeric limits.")
        return value
