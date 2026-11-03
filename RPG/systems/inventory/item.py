"""Static item definitions and serializable per-player item instances."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from math import isfinite
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4


ITEM_TYPES = frozenset({"equipment", "material", "miscellaneous"})
EQUIPMENT_SUBTYPES = frozenset({"weapon", "armor", "accessory"})
EQUIPMENT_ATTRIBUTES = frozenset({
    "hp", "mp", "attack", "agility", "stamina", "physical_defense", "magical_defense",
    "critical_chance", "critical_damage", "attack_speed", "hp_regeneration", "mp_regeneration",
})


@dataclass(frozen=True)
class ItemDefinition:
    item_id: str
    name: str
    description: str
    item_type: str
    subtype: str
    rarity: str
    max_stack: int = 1
    sell_value: int = 0
    can_sell: bool = True
    can_discard: bool = True
    can_equip: bool = False
    equipment_slot: str | None = None
    required_level: int = 1
    bonuses: Mapping[str, float] = field(default_factory=dict)
    icon: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        text_values = (self.item_id, self.name, self.description, self.item_type, self.subtype, self.rarity)
        if any(not isinstance(value, str) or not value.strip() for value in text_values):
            raise ValueError("Items require an ID, name, description, type, subtype, and rarity.")
        item_id = self.item_id.strip().casefold()
        item_type = self.item_type.strip().casefold()
        subtype = self.subtype.strip().casefold()
        rarity = self.rarity.strip().casefold()
        if item_type not in ITEM_TYPES:
            raise ValueError(f"Item '{item_id}' has unsupported type '{item_type}'.")
        if item_type == "equipment":
            if subtype not in EQUIPMENT_SUBTYPES or not self.can_equip or not self.equipment_slot:
                raise ValueError(f"Equipment '{item_id}' requires a supported subtype, slot, and can_equip=true.")
            if self.max_stack != 1:
                raise ValueError(f"Equipment '{item_id}' cannot have a stack size other than one.")
        elif self.can_equip or self.equipment_slot or self.bonuses:
            raise ValueError(f"Non-equipment item '{item_id}' cannot define equipment properties.")
        if isinstance(self.max_stack, bool) or not isinstance(self.max_stack, int) or self.max_stack < 1:
            raise ValueError(f"Item '{item_id}' max_stack must be a positive whole number.")
        if isinstance(self.sell_value, bool) or not isinstance(self.sell_value, int) or self.sell_value < 0:
            raise ValueError(f"Item '{item_id}' sell_value must be a non-negative whole number.")
        if not isinstance(self.can_sell, bool) or not isinstance(self.can_discard, bool) or not isinstance(self.can_equip, bool):
            raise ValueError(f"Item '{item_id}' operation flags must be booleans.")
        if self.can_sell and self.sell_value < 1:
            raise ValueError(f"Sellable item '{item_id}' requires a positive base sell value.")
        if isinstance(self.required_level, bool) or not isinstance(self.required_level, int) or self.required_level < 1:
            raise ValueError(f"Item '{item_id}' required_level must be a positive whole number.")
        if self.icon is not None and (not isinstance(self.icon, str) or not self.icon.strip()):
            raise ValueError(f"Item '{item_id}' has an invalid icon reference.")
        if not isinstance(self.bonuses, Mapping):
            raise ValueError(f"Item '{item_id}' bonuses must be an object.")
        normalized_bonuses: dict[str, float] = {}
        for attribute, value in self.bonuses.items():
            key = str(attribute).strip().casefold()
            if key not in EQUIPMENT_ATTRIBUTES:
                raise ValueError(f"Item '{item_id}' uses unsupported attribute bonus '{attribute}'.")
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
                raise ValueError(f"Item '{item_id}' bonus '{key}' must be a finite number.")
            normalized_bonuses[key] = float(value)
        if not isinstance(self.metadata, Mapping):
            raise ValueError(f"Item '{item_id}' metadata must be an object.")
        object.__setattr__(self, "item_id", item_id)
        object.__setattr__(self, "item_type", item_type)
        object.__setattr__(self, "subtype", subtype)
        object.__setattr__(self, "rarity", rarity)
        object.__setattr__(self, "equipment_slot", self.equipment_slot.casefold() if self.equipment_slot else None)
        object.__setattr__(self, "bonuses", MappingProxyType(normalized_bonuses))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    @property
    def id(self) -> str:
        return self.item_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.item_id,
            "name": self.name,
            "description": self.description,
            "type": self.item_type,
            "subtype": self.subtype,
            "rarity": self.rarity,
            "max_stack": self.max_stack,
            "sell_value": self.sell_value,
            "can_sell": self.can_sell,
            "can_discard": self.can_discard,
            "can_equip": self.can_equip,
            "equipment_slot": self.equipment_slot,
            "required_level": self.required_level,
            "bonuses": dict(self.bonuses),
            "icon": self.icon,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ItemDefinition":
        try:
            return cls(
                item_id=data["id"],
                name=data["name"],
                description=data.get("description", ""),
                item_type=data["type"],
                subtype=data["subtype"],
                rarity=data["rarity"],
                max_stack=data.get("max_stack", 1),
                sell_value=data.get("sell_value", 0),
                can_sell=data.get("can_sell", True),
                can_discard=data.get("can_discard", True),
                can_equip=data.get("can_equip", False),
                equipment_slot=data.get("equipment_slot"),
                required_level=data.get("required_level", 1),
                bonuses=data.get("bonuses", {}),
                icon=data.get("icon"),
                metadata=data.get("metadata", {}),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Malformed item definition: {exc}") from exc


@dataclass(frozen=True)
class ItemInstance:
    instance_id: str
    item_id: str
    quantity: int = 1
    acquired_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    instance_data: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.instance_id, str) or not self.instance_id.strip():
            raise ValueError("Item instances require a unique instance ID.")
        if not isinstance(self.item_id, str) or not self.item_id.strip():
            raise ValueError("Item instances require a definition ID.")
        if isinstance(self.quantity, bool) or not isinstance(self.quantity, int) or self.quantity < 1:
            raise ValueError("Item instance quantity must be a positive whole number.")
        if not isinstance(self.acquired_at, str) or not self.acquired_at.strip():
            raise ValueError("Item instances require an acquisition timestamp.")
        try:
            datetime.fromisoformat(self.acquired_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("Item instance acquisition timestamp is invalid.") from exc
        if not isinstance(self.instance_data, Mapping):
            raise ValueError("Item instance data must be an object.")
        object.__setattr__(self, "item_id", self.item_id.strip().casefold())
        object.__setattr__(self, "instance_data", MappingProxyType(dict(self.instance_data)))

    @classmethod
    def create(
        cls,
        item_id: str,
        quantity: int = 1,
        *,
        instance_id: str | None = None,
        acquired_at: str | None = None,
        instance_data: Mapping[str, Any] | None = None,
    ) -> "ItemInstance":
        return cls(
            instance_id=instance_id or uuid4().hex,
            item_id=item_id,
            quantity=quantity,
            acquired_at=acquired_at or datetime.now(timezone.utc).isoformat(),
            instance_data=instance_data or {},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "item_id": self.item_id,
            "quantity": self.quantity,
            "acquired_at": self.acquired_at,
            "instance_data": dict(self.instance_data),
        }

    @classmethod
    def from_dict(cls, data: object) -> "ItemInstance":
        if not isinstance(data, Mapping):
            raise ValueError("Saved item instance must be an object.")
        return cls(
            instance_id=data.get("instance_id"),
            item_id=data.get("item_id"),
            quantity=data.get("quantity", 1),
            acquired_at=data.get("acquired_at", datetime.now(timezone.utc).isoformat()),
            instance_data=data.get("instance_data", {}),
        )


__all__ = ["EQUIPMENT_ATTRIBUTES", "EQUIPMENT_SUBTYPES", "ITEM_TYPES", "ItemDefinition", "ItemInstance"]
