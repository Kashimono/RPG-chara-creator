from ..constants import BASE_LEVEL, EXP_TO_NEXT, STAT_POINTS_PER_LEVEL


class LevelSystem:
    """Encapsulates basic level progression rules."""

    @staticmethod
    def starting_level() -> int:
        return BASE_LEVEL

    @staticmethod
    def starting_exp() -> int:
        return 0

    @staticmethod
    def next_level_exp() -> int:
        return EXP_TO_NEXT

    @staticmethod
    def stat_points_for_levels(level_count: int) -> int:
        return level_count * STAT_POINTS_PER_LEVEL
