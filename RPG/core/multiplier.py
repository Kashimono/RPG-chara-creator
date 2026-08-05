from typing import Tuple
from ..constants import MILESTONE_MULTIPLIERS


class StatMultiplier:
    """Computes a smooth multiplier based on the current stat value."""

    @classmethod
    def compute(cls, points: int, max_multiplier: float | None = None) -> float:
        if points <= 0:
            return 1.0

        if max_multiplier is None:
            max_multiplier = MILESTONE_MULTIPLIERS[-1][1]

        points = min(points, MILESTONE_MULTIPLIERS[-1][0])

        for index in range(len(MILESTONE_MULTIPLIERS) - 1):
            low_points, low_multiplier = MILESTONE_MULTIPLIERS[index]
            high_points, high_multiplier = MILESTONE_MULTIPLIERS[index + 1]
            if low_points <= points <= high_points:
                if high_points == low_points:
                    return round(min(low_multiplier, max_multiplier), 2)
                interpolation = (points - low_points) / (high_points - low_points)
                scaled_multiplier = low_multiplier + interpolation * (high_multiplier - low_multiplier)
                return round(min(scaled_multiplier, max_multiplier), 2)

        return round(min(MILESTONE_MULTIPLIERS[-1][1], max_multiplier), 2)
