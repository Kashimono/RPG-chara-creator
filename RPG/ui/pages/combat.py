"""Combat placeholder page."""

from .placeholders import PlannedFeaturePage


class CombatPage(PlannedFeaturePage):
    def __init__(self, parent):
        super().__init__(
            parent,
            "Combat",
            "Battle systems arrive in a future update.",
            "⚔",
            "Combat encounters, enemies, and battle controls will be introduced after the character foundation is complete.",
        )
