"""Immutable serializable bag contents and claimable combat drops."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import uuid4

from .item import ItemInstance


@dataclass(frozen=True)
class UnclaimedLoot:
    unclaimed_id: str
    item_id: str
    quantity: int
    source: str
    encounter_id: str | None
    reason: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        if any(not isinstance(value, str) or not value.strip() for value in (self.unclaimed_id, self.item_id, self.source, self.reason)):
            raise ValueError("Unclaimed loot requires IDs, source, and a reason.")
        if isinstance(self.quantity, bool) or not isinstance(self.quantity, int) or self.quantity < 1:
            raise ValueError("Unclaimed loot quantity must be a positive whole number.")
        if not isinstance(self.created_at, str) or not self.created_at.strip():
            raise ValueError("Unclaimed loot requires a creation timestamp.")
        datetime.fromisoformat(self.created_at.replace("Z", "+00:00"))

    @classmethod
    def create(
        cls,
        item_id: str,
        quantity: int,
        *,
        source: str,
        encounter_id: str | None,
        reason: str,
        unclaimed_id: str | None = None,
    ) -> "UnclaimedLoot":
        return cls(unclaimed_id or uuid4().hex, item_id.casefold(), quantity, source, encounter_id, reason)

    def to_dict(self) -> dict[str, Any]:
        return {
            "unclaimed_id": self.unclaimed_id,
            "item_id": self.item_id,
            "quantity": self.quantity,
            "source": self.source,
            "encounter_id": self.encounter_id,
            "reason": self.reason,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: object) -> "UnclaimedLoot":
        if not isinstance(data, Mapping):
            raise ValueError("Saved unclaimed loot must be an object.")
        return cls(
            unclaimed_id=data.get("unclaimed_id"),
            item_id=data.get("item_id"),
            quantity=data.get("quantity"),
            source=data.get("source", "Unknown source"),
            encounter_id=data.get("encounter_id"),
            reason=data.get("reason", "Previously unclaimed loot."),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
        )


@dataclass(frozen=True)
class InventoryState:
    capacity: int | None = None
    items: tuple[ItemInstance, ...] = ()
    unclaimed_loot: tuple[UnclaimedLoot, ...] = ()
    processed_loot_keys: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.capacity is not None and (
            isinstance(self.capacity, bool) or not isinstance(self.capacity, int) or self.capacity < 1
        ):
            raise ValueError("Inventory capacity must be a positive whole number.")
        items = tuple(item for item in self.items if isinstance(item, ItemInstance))
        unclaimed = tuple(item for item in self.unclaimed_loot if isinstance(item, UnclaimedLoot))
        keys = tuple(dict.fromkeys(key for key in self.processed_loot_keys if isinstance(key, str) and key))
        object.__setattr__(self, "items", items)
        object.__setattr__(self, "unclaimed_loot", unclaimed)
        object.__setattr__(self, "processed_loot_keys", keys)

    @property
    def used_slots(self) -> int:
        return len(self.items)

    @property
    def remaining_slots(self) -> int | None:
        return None if self.capacity is None else max(0, self.capacity - self.used_slots)

    def to_dict(self) -> dict[str, Any]:
        return {
            "capacity": self.capacity,
            "items": [item.to_dict() for item in self.items],
            "unclaimed_loot": [item.to_dict() for item in self.unclaimed_loot],
            "processed_loot_keys": list(self.processed_loot_keys),
        }

    @classmethod
    def from_dict(cls, data: object) -> "InventoryState":
        if not isinstance(data, Mapping):
            return cls()
        capacity = data.get("capacity")
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity < 1:
            capacity = None
        raw_items = data.get("items", [])
        items: list[ItemInstance] = []
        if isinstance(raw_items, list):
            for raw in raw_items:
                try:
                    items.append(ItemInstance.from_dict(raw))
                except (TypeError, ValueError):
                    continue
        raw_unclaimed = data.get("unclaimed_loot", [])
        unclaimed: list[UnclaimedLoot] = []
        if isinstance(raw_unclaimed, list):
            for raw in raw_unclaimed:
                try:
                    unclaimed.append(UnclaimedLoot.from_dict(raw))
                except (TypeError, ValueError):
                    continue
        raw_keys = data.get("processed_loot_keys", [])
        keys = tuple(value for value in raw_keys if isinstance(value, str)) if isinstance(raw_keys, list) else ()
        return cls(capacity, tuple(items), tuple(unclaimed), keys)


__all__ = ["InventoryState", "UnclaimedLoot"]
