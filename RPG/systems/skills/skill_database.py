"""Validated loader for data-driven skill definitions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .skill import SkillDefinition


class SkillDatabaseError(ValueError):
    """Invalid or unavailable skill content."""


class SkillDatabase:
    FILES = ("physical_skills.json", "magical_skills.json", "defensive_skills.json", "support_skills.json")

    def __init__(self, definitions: Iterable[SkillDefinition]) -> None:
        self._skills: dict[str, SkillDefinition] = {}
        for definition in definitions:
            if not isinstance(definition, SkillDefinition):
                raise SkillDatabaseError("Skill database entries must be SkillDefinition values.")
            key = definition.skill_id.casefold()
            if key in self._skills:
                raise SkillDatabaseError(f"Duplicate skill ID: {definition.skill_id}")
            self._skills[key] = definition
        for skill in self._skills.values():
            if len(set(skill.prerequisites)) != len(skill.prerequisites):
                raise SkillDatabaseError(f"Skill '{skill.skill_id}' repeats a prerequisite ID.")
            if skill.skill_id in skill.prerequisites:
                raise SkillDatabaseError(f"Skill '{skill.skill_id}' cannot require itself.")
            missing = [item for item in skill.prerequisites if item not in self._skills]
            if missing:
                raise SkillDatabaseError(f"Skill '{skill.skill_id}' references missing prerequisite(s): {', '.join(missing)}")
        visiting: set[str] = set()
        visited: set[str] = set()
        def visit(skill_id: str) -> None:
            if skill_id in visiting:
                raise SkillDatabaseError(f"Skill prerequisites contain a cycle involving '{skill_id}'.")
            if skill_id in visited:
                return
            visiting.add(skill_id)
            for prerequisite in self._skills[skill_id].prerequisites:
                visit(prerequisite)
            visiting.remove(skill_id)
            visited.add(skill_id)
        for skill_id in self._skills:
            visit(skill_id)

    @classmethod
    def from_files(cls, paths: Iterable[str | Path]) -> "SkillDatabase":
        definitions: list[SkillDefinition] = []
        for path in paths:
            source = Path(path)
            try:
                raw = json.loads(source.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise SkillDatabaseError(f"Could not load skill file '{source}': {exc}") from exc
            rows = raw.get("skills") if isinstance(raw, dict) else raw
            if not isinstance(rows, list):
                raise SkillDatabaseError(f"Skill file '{source}' must contain a list of definitions.")
            for index, row in enumerate(rows):
                try:
                    definitions.append(SkillDefinition.from_dict(row))
                except (TypeError, ValueError) as exc:
                    raise SkillDatabaseError(f"Invalid skill at {source}, entry {index + 1}: {exc}") from exc
        return cls(definitions)

    @classmethod
    def load_default(cls) -> "SkillDatabase":
        root = Path(__file__).resolve().parents[2] / "data" / "skills"
        return cls.from_files(root / filename for filename in cls.FILES)

    def get(self, skill_id: str) -> SkillDefinition:
        if not isinstance(skill_id, str):
            raise SkillDatabaseError("Skill ID must be a string.")
        try:
            return self._skills[skill_id.strip().casefold()]
        except KeyError as exc:
            raise SkillDatabaseError(f"Unknown skill ID: {skill_id}") from exc

    def get_optional(self, skill_id: str) -> SkillDefinition | None:
        return self._skills.get(skill_id.strip().casefold()) if isinstance(skill_id, str) else None

    def list_skills(self) -> tuple[SkillDefinition, ...]:
        return tuple(self._skills.values())

    def by_classification(self, classification: str) -> tuple[SkillDefinition, ...]:
        key = classification.strip().casefold()
        return tuple(skill for skill in self._skills.values() if skill.classification == key)
