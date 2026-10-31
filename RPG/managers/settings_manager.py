"""Validation and updates for preferences stored in GameState."""

from __future__ import annotations

from typing import Any

from ..core.game_config import DEFAULT_GAME_SETTINGS, SUPPORTED_THEMES, normalize_game_settings


class SettingsManager:
    @staticmethod
    def defaults() -> dict[str, Any]:
        return dict(DEFAULT_GAME_SETTINGS)

    @staticmethod
    def normalize(settings: Any = None) -> dict[str, Any]:
        return normalize_game_settings(settings)

    @staticmethod
    def set_setting(settings: dict[str, Any], key: str, value: Any) -> dict[str, Any]:
        updated = normalize_game_settings(settings)
        if key == "theme":
            if value not in SUPPORTED_THEMES:
                raise ValueError("Theme must be Dark, Light, or System.")
        elif key == "sound_enabled":
            if not isinstance(value, bool):
                raise ValueError("Sound preference must be a boolean.")
        else:
            raise KeyError(f"Unknown game setting: {key}")
        updated[key] = value
        return updated

    @classmethod
    def reset(cls) -> dict[str, Any]:
        return cls.defaults()
