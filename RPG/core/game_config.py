"""Configuration shared by the non-UI game modules."""

from __future__ import annotations

from typing import Any

SAVE_SCHEMA_VERSION = 3
APP_TITLE = "RPG: World of Ascension"
APP_VERSION = "0.3.0"

BASE_EXP_REQUIREMENT = 100
EXP_GROWTH_RATE = 1.5

BASE_CRITICAL_CHANCE = 0.05
MAX_CRITICAL_CHANCE = 0.75
CRITICAL_CHANCE_AGILITY_FACTOR = 0.45
CRITICAL_AGILITY_SCALE = 1_000.0
BASE_CRITICAL_DAMAGE = 1.5
MAX_CRITICAL_DAMAGE = 4.0
CRITICAL_ATTACK_SCALE = 5_000.0
BASE_ATTACK_SPEED = 1.0
MAX_ATTACK_SPEED = 4.0
ATTACK_SPEED_AGILITY_FACTOR = 2.0
ATTACK_SPEED_AGILITY_SCALE = 1_000.0

PHYSICAL_DEFENSE_STAMINA_FACTOR = 0.60
PHYSICAL_DEFENSE_ATTACK_FACTOR = 0.05
MAGICAL_DEFENSE_MP_FACTOR = 0.45
MAGICAL_DEFENSE_STAMINA_FACTOR = 0.15
HP_REGEN_STAMINA_FACTOR = 0.01
HP_REGEN_HP_FACTOR = 0.002
MP_REGEN_MP_FACTOR = 0.01
MP_REGEN_STAMINA_FACTOR = 0.001

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
