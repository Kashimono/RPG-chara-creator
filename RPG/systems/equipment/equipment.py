"""Persist equipped item instances separately from bag capacity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ..inventory.item import ItemInstance


@dataclass(frozen=True)
class EquippedItem:
    slot_id: str
    item: ItemInstance

    def __post_init__(self) -> None:
        if not isinstance(self.slot_id, str) or not self.slot_id.strip():
            raise ValueError("Equipped items require a slot ID.")
        if not isinstance(self.item, ItemInstance):
            raise ValueError("Equipment slots require an item instance.")
        if self.item.quantity != 1:
            raise ValueError("Equipped item instances must have quantity one.")
        object.__setattr__(self, "slot_id", self.slot_id.strip().casefold())


@dataclass(frozen=True)
class EquipmentState:
    equipped_items: tuple[EquippedItem, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "equipped_items", tuple(
            equipped for equipped in self.equipped_items if isinstance(equipped, EquippedItem)
        ))

    def get(self, slot_id: str) -> ItemInstance | None:
        normalized = slot_id.casefold()
        return next((entry.item for entry in self.equipped_items if entry.slot_id == normalized), None)

    def find_instance(self, instance_id: str) -> tuple[str, ItemInstance] | None:
        return next(
            ((entry.slot_id, entry.item) for entry in self.equipped_items if entry.item.instance_id == instance_id),
            None,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "equipped_items": [
                {"slot_id": entry.slot_id, "item_instance": entry.item.to_dict()}
                for entry in self.equipped_items
            ],
        }

    @classmethod
    def from_dict(cls, data: object) -> "EquipmentState":
        if not isinstance(data, Mapping):
            return cls()
        raw = data.get("equipped_items", [])
        entries: list[EquippedItem] = []
        if isinstance(raw, list):
            for value in raw:
                try:
                    if not isinstance(value, Mapping):
                        continue
                    item = ItemInstance.from_dict(value.get("item_instance"))
                    entries.append(EquippedItem(value.get("slot_id"), item))
                except (TypeError, ValueError):
                    continue
        return cls(tuple(entries))


__all__ = ["EquipmentState", "EquippedItem"]
