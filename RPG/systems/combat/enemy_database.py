"""JSON-backed, validated registry of every supported enemy definition."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from .enemy import (
    BossPhaseDefinition,
    EnemyClassification,
    EnemyDefinition,
    EnemyScaling,
)
from .enemy_ability import AbilityTrigger, EnemyAbilityDefinition, EnemyAbilityType


class EnemyDatabaseError(ValueError):
    """Raised when the static enemy content cannot be loaded or validated."""


CLASSIFICATION_DEFINITIONS: dict[EnemyClassification, dict[str, str | float]] = {
    classification: {
        "id": classification.value,
        "name": classification.display_name,
        "description": classification.description,
        "color": classification.color_hex,
        "difficulty_multiplier": classification.difficulty_multiplier,
    }
    for classification in EnemyClassification
}


class EnemyDatabase:
    def __init__(self, definitions: Iterable[EnemyDefinition]) -> None:
        self._definitions: dict[str, EnemyDefinition] = {}
        self._ordered: list[EnemyDefinition] = []
        for definition in definitions:
            key = definition.definition_id.casefold()
            if key in self._definitions:
                raise EnemyDatabaseError(f"Duplicate enemy ID: {definition.definition_id}")
            self._definitions[key] = definition
            self._ordered.append(definition)
        if not self._ordered:
            raise EnemyDatabaseError("Enemy database contains no enemy definitions.")

    @classmethod
    def load(
        cls,
        directory: str | Path,
        *,
        ability_file: str | Path | None = None,
    ) -> "EnemyDatabase":
        source_directory = Path(directory)
        if not source_directory.is_dir():
            raise EnemyDatabaseError(f"Enemy data directory is missing: {source_directory}")
        files = sorted(source_directory.glob("*.json"))
        if not files:
            raise EnemyDatabaseError(f"No enemy JSON files were found in '{source_directory}'.")

        ability_path = Path(ability_file) if ability_file else source_directory.parent / "enemy_abilities.json"
        abilities = cls._load_abilities(ability_path) if ability_path.exists() else {}
        definitions: list[EnemyDefinition] = []
        for file_path in files:
            try:
                raw_data = json.loads(file_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise EnemyDatabaseError(f"Could not load enemy definitions from '{file_path}': {exc}") from exc
            try:
                rows = raw_data["enemies"] if isinstance(raw_data, dict) else raw_data
                if not isinstance(rows, list):
                    raise ValueError("root must be an array or contain an 'enemies' array")
                expected_classification = cls._file_classification(file_path.stem)
                for row in rows:
                    definition = cls._parse_definition(row, abilities)
                    if expected_classification is not None and definition.classification is not expected_classification:
                        raise ValueError(
                            f"enemy '{definition.definition_id}' classification does not match {file_path.name}"
                        )
                    definitions.append(definition)
            except (KeyError, TypeError, ValueError) as exc:
                raise EnemyDatabaseError(f"Malformed enemy definition in '{file_path}': {exc}") from exc
        try:
            return cls(definitions)
        except EnemyDatabaseError as exc:
            raise EnemyDatabaseError(f"Invalid enemy database in '{source_directory}': {exc}") from exc

    @classmethod
    def load_default(cls) -> "EnemyDatabase":
        data_directory = Path(__file__).resolve().parents[2] / "data"
        return cls.load(data_directory / "enemies", ability_file=data_directory / "enemy_abilities.json")

    @classmethod
    def from_definitions(cls, definitions: Iterable[EnemyDefinition]) -> "EnemyDatabase":
        try:
            return cls(definitions)
        except EnemyDatabaseError:
            raise
        except (AttributeError, TypeError, ValueError) as exc:
            raise EnemyDatabaseError(f"Invalid enemy definitions: {exc}") from exc

    def get_by_id(self, enemy_id: str) -> EnemyDefinition:
        try:
            return self._definitions[enemy_id.casefold()]
        except (AttributeError, KeyError) as exc:
            raise EnemyDatabaseError(f"Unknown enemy ID: {enemy_id}") from exc

    def get_by_classification(self, classification: str | EnemyClassification) -> tuple[EnemyDefinition, ...]:
        selected = EnemyClassification.from_value(classification)
        return tuple(item for item in self._ordered if item.classification is selected)

    def list_enemies(
        self,
        classification: str | EnemyClassification | None = None,
    ) -> tuple[EnemyDefinition, ...]:
        if classification is None:
            return tuple(self._ordered)
        return self.get_by_classification(classification)

    def validate_loot_references(self, loot_table_ids: set[str]) -> None:
        available = {table_id.casefold() for table_id in loot_table_ids}
        for definition in self._ordered:
            table_id = definition.loot_table_id
            if table_id is not None and table_id.casefold() not in available:
                raise EnemyDatabaseError(
                    f"Enemy '{definition.definition_id}' references missing loot table '{table_id}'."
                )

    @property
    def classifications(self) -> tuple[EnemyClassification, ...]:
        return tuple(EnemyClassification)

    @staticmethod
    def _file_classification(filename: str) -> EnemyClassification | None:
        aliases = {
            "common": EnemyClassification.COMMON,
            "uncommon": EnemyClassification.UNCOMMON,
            "rare": EnemyClassification.RARE,
            "elite": EnemyClassification.ELITE,
            "bosses": EnemyClassification.BOSS,
            "boss": EnemyClassification.BOSS,
            "world_bosses": EnemyClassification.WORLD_BOSS,
            "world_boss": EnemyClassification.WORLD_BOSS,
        }
        return aliases.get(filename.casefold())

    @classmethod
    def _load_abilities(cls, path: Path) -> dict[str, EnemyAbilityDefinition]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise EnemyDatabaseError(f"Could not load enemy abilities from '{path}': {exc}") from exc
        try:
            rows = data["abilities"] if isinstance(data, dict) else data
            if not isinstance(rows, list):
                raise ValueError("root must be an array or contain an 'abilities' array")
            result: dict[str, EnemyAbilityDefinition] = {}
            for row in rows:
                ability = cls._parse_ability(row)
                key = ability.ability_id.casefold()
                if key in result:
                    raise ValueError(f"duplicate ability ID '{ability.ability_id}'")
                result[key] = ability
            return result
        except (KeyError, TypeError, ValueError) as exc:
            raise EnemyDatabaseError(f"Malformed enemy ability file '{path}': {exc}") from exc

    @staticmethod
    def _parse_ability(data: Any) -> EnemyAbilityDefinition:
        if not isinstance(data, Mapping):
            raise ValueError("each ability must be an object")
        return EnemyAbilityDefinition(
            ability_id=data["ability_id"],
            name=data["name"],
            description=data["description"],
            ability_type=data["ability_type"],
            trigger=data.get("trigger", AbilityTrigger.ENEMY_ATTACK.value),
            cooldown_seconds=data.get("cooldown_seconds", 0.0),
            duration_seconds=data.get("duration_seconds", 0.0),
            activation_threshold=data.get("activation_threshold"),
            parameters=data.get("parameters", {}),
        )

    @classmethod
    def _parse_definition(
        cls,
        data: Any,
        abilities: Mapping[str, EnemyAbilityDefinition],
    ) -> EnemyDefinition:
        if not isinstance(data, Mapping):
            raise ValueError("each enemy must be an object")
        ability_ids = data.get("abilities", [])
        if not isinstance(ability_ids, list):
            raise ValueError("enemy abilities must be a list of ability IDs")
        resolved_abilities: list[EnemyAbilityDefinition] = []
        for ability_id in ability_ids:
            try:
                resolved_abilities.append(abilities[str(ability_id).casefold()])
            except KeyError as exc:
                raise ValueError(f"enemy references unknown ability '{ability_id}'") from exc

        scaling_data = data.get("scaling")
        scaling = EnemyScaling(**scaling_data) if isinstance(scaling_data, Mapping) else None
        if scaling_data is not None and scaling is None:
            raise ValueError("enemy scaling must be an object or null")
        phases_data = data.get("boss_phases", [])
        if not isinstance(phases_data, list):
            raise ValueError("boss_phases must be a list")
        phases = tuple(
            BossPhaseDefinition(
                phase_id=phase["phase_id"],
                name=phase["name"],
                hp_threshold=phase["hp_threshold"],
                description=phase.get("description", ""),
                attack_multiplier=phase.get("attack_multiplier", 1.0),
                attack_interval_multiplier=phase.get("attack_interval_multiplier", 1.0),
                physical_defense_multiplier=phase.get("physical_defense_multiplier", 1.0),
                magical_defense_multiplier=phase.get("magical_defense_multiplier", 1.0),
                ability_ids=tuple(phase["ability_ids"]) if "ability_ids" in phase else None,
            )
            for phase in phases_data
        )
        return EnemyDefinition(
            definition_id=data["enemy_id"],
            name=data["name"],
            description=data.get("description", "An enemy of the realm."),
            classification=data["classification"],
            max_hp=data["max_hp"],
            attack=data["attack"],
            physical_defense=data.get("physical_defense", 0.0),
            magical_defense=data.get("magical_defense", 0.0),
            exp_reward=data["exp_reward"],
            attack_interval=data["attack_interval"],
            image_asset=data.get("image_asset"),
            abilities=tuple(resolved_abilities),
            boss_phases=phases,
            loot_table_id=data.get("loot_table_id"),
            difficulty_multiplier=data.get("difficulty_multiplier", 1.0),
            scaling=scaling,
        )
