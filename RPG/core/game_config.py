"""Configuration shared by the non-UI game modules."""

from __future__ import annotations

from typing import Any

SAVE_SCHEMA_VERSION = 2
APP_TITLE = "RPG: World of Ascension"
APP_VERSION = "0.2.0"

SUPPORTED_THEMES = ("Dark", "Light", "System")
DEFAULT_GAME_SETTINGS: dict[str, Any] = {
    "theme": "Dark",
    "sound_enabled": False,
}


def normalize_game_settings(settings: Any = None) -> dict[str, Any]:
    """Return valid current preferences while retaining unknown future keys."""
    normalized = dict(DEFAULT_GAME_SETTINGS)
    if not isinstance(settings, dict):
        return normalized

    normalized.update(settings)
    if normalized.get("theme") not in SUPPORTED_THEMES:
        normalized["theme"] = DEFAULT_GAME_SETTINGS["theme"]
    if not isinstance(normalized.get("sound_enabled"), bool):
        normalized["sound_enabled"] = DEFAULT_GAME_SETTINGS["sound_enabled"]
    return normalized
