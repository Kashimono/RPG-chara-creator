from .stat import Stat


class PotentialRoller:
    """Handles potential rolling and acceptance logic."""

    @staticmethod
    def roll(stat: Stat, min_potential: int, max_potential: int) -> int:
        return stat.roll_potential(min_potential, max_potential)

    @staticmethod
    def can_accept(stat: Stat) -> bool:
        return stat.roll_value is not None and not stat.accepted
