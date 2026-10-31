"""Inventory placeholder page."""

from .placeholders import PlannedFeaturePage


class InventoryPage(PlannedFeaturePage):
    def __init__(self, parent):
        super().__init__(
            parent,
            "Inventory",
            "Your pack is waiting for a future update.",
            "◇",
            "Equipment, items, and inventory management will become available in a later gameplay update.",
        )
