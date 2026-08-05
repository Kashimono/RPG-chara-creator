from typing import Tuple
from ..constants import MILESTONE_MULTIPLIERS


class StatMultiplier:
    """Computes a smooth multiplier based on the current stat value."""

    @classmethod
    def compute(cls, points: int) -> float:
        if points <= 0:
            return 1.0

        points = min(points, MILESTONE_MULTIPLIERS[-1][0])

        for index in range(len(MILESTONE_MULTIPLIERS) - 1):
            low_points, low_multiplier = MILESTONE_MULTIPLIERS[index]
            high_points, high_multiplier = MILESTONE_MULTIPLIERS[index + 1]
            if low_points <= points <= high_points:
                if high_points == low_points:
                    return low_multiplier
                interpolation = (points - low_points) / (high_points - low_points)
                return round(low_multiplier + interpolation * (high_multiplier - low_multiplier), 2)

        return MILESTONE_MULTIPLIERS[-1][1]
