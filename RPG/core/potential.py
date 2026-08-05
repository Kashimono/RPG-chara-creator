from .stat import Stat


class PotentialRoller:
    """Handles potential rolling and acceptance logic."""

    @staticmethod
    def roll(stat: Stat) -> int:
        return stat.roll_potential()

    @staticmethod
    def can_accept(stat: Stat) -> bool:
        return stat.roll_value is not None and not stat.accepted
