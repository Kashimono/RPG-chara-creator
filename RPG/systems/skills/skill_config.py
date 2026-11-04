"""Skill loadout and configured starter skill defaults."""

from __future__ import annotations

import json
from pathlib import Path


def load_skill_config(path: str | Path | None = None) -> dict[str, object]:
    source = Path(path) if path is not None else Path(__file__).resolve().parents[2] / "data" / "skills" / "skill_config.json"
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not load skill configuration '{source}': {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("Skill configuration must be a JSON object.")
    capacity = data.get("max_equipped_skills", 6)
    starters = data.get("starting_skills", [])
    if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity < 1:
        raise ValueError("max_equipped_skills must be a positive integer.")
    if not isinstance(starters, list) or any(not isinstance(item, str) for item in starters):
        raise ValueError("starting_skills must be a list of skill IDs.")
    normalized = [item.strip().casefold() for item in starters]
    if any(not item for item in normalized) or len(set(normalized)) != len(normalized):
        raise ValueError("starting_skills must contain unique, non-empty skill IDs.")
    if len(normalized) > capacity:
        raise ValueError("starting_skills cannot exceed max_equipped_skills.")
    return {"max_equipped_skills": capacity, "starting_skills": normalized}
