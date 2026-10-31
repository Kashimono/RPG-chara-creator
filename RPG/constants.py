from .core.game_config import BASE_EXP_REQUIREMENT

STAT_NAMES = ["HP", "MP", "Attack", "Agility", "Stamina"]
POTENTIAL_MIN = 1
POTENTIAL_MAX = 1_000_000
MAX_POTENTIAL_ROLLS = 10
BASE_LEVEL = 1
BASE_EXP = 0
# Compatibility alias; progression calculates each threshold by level.
EXP_TO_NEXT = BASE_EXP_REQUIREMENT
STAT_POINTS_PER_LEVEL = 10

MILESTONE_MULTIPLIERS = [
    (0, 1.0),
    (25, 1.2),
    (50, 1.5),
    (75, 1.8),
    (100, 2.2),
    (150, 3.0),
    (200, 4.0),
    (300, 6.0),
    (500, 10.0),
    (750, 15.0),
    (1000, 20.0),
    (2000, 30.0),
    (3500, 40.0),
    (5000, 50.0),
]
