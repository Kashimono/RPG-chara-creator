from __future__ import annotations

from math import ceil

from ..constants import BASE_LEVEL, BASE_EXP, STAT_POINTS_PER_LEVEL
from .game_config import BASE_EXP_REQUIREMENT, EXP_GROWTH_RATE


class LevelSystem:
    """Encapsulates basic level progression rules."""

    @staticmethod
    def starting_level() -> int:
        return BASE_LEVEL

    @staticmethod
    def starting_exp() -> int:
        return BASE_EXP

    @staticmethod
    def required_exp(level: int) -> int:
        """EXP needed to advance from ``level`` to the next level."""
        progression_level = max(1, int(level))
        return max(1, ceil(BASE_EXP_REQUIREMENT * progression_level**EXP_GROWTH_RATE))

    @classmethod
    def next_level_exp(cls, level: int = BASE_LEVEL) -> int:
        return cls.required_exp(level)

    @staticmethod
    def stat_points_for_levels(level_count: int) -> int:
        return level_count * STAT_POINTS_PER_LEVEL
