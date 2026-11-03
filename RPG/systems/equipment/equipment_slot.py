"""A configured equipment slot paired with its current optional instance."""

from __future__ import annotations

from dataclasses import dataclass

from ..inventory.item import ItemInstance
from ..inventory.item_config import EquipmentSlotDefinition


@dataclass(frozen=True)
class EquipmentSlot:
    definition: EquipmentSlotDefinition
    item: ItemInstance | None = None

    @property
    def slot_id(self) -> str:
        return self.definition.slot_id

    @property
    def display_name(self) -> str:
        return self.definition.display_name

    @property
    def is_empty(self) -> bool:
        return self.item is None


__all__ = ["EquipmentSlot"]
