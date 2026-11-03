"""Validated rarity, slot, and inventory capacity configuration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class ItemRarityDefinition:
    rarity_id: str
    display_name: str
    color_hex: str
    bonus_multiplier: float = 1.0
    sell_multiplier: float = 1.0

    def __post_init__(self) -> None:
        if any(not isinstance(value, str) or not value.strip() for value in (self.rarity_id, self.display_name, self.color_hex)):
            raise ValueError("Item rarity requires an ID, display name, and color.")
        object.__setattr__(self, "rarity_id", self.rarity_id.strip().casefold())
        for name in ("bonus_multiplier", "sell_multiplier"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or value <= 0:
                raise ValueError(f"Rarity {name} must be finite and positive.")
            object.__setattr__(self, name, float(value))
        digits = self.color_hex[1:] if isinstance(self.color_hex, str) and self.color_hex.startswith("#") else ""
        if len(digits) not in {3, 6} or any(character not in "0123456789abcdefABCDEF" for character in digits):
            raise ValueError("Rarity color must be a short or full hex color.")


@dataclass(frozen=True)
class EquipmentSlotDefinition:
    slot_id: str
    display_name: str
    equipment_slot: str
    accepted_subtypes: tuple[str, ...]

    def __post_init__(self) -> None:
        if any(not isinstance(value, str) or not value.strip() for value in (self.slot_id, self.display_name, self.equipment_slot)):
            raise ValueError("Equipment slots require an ID, display name, and slot type.")
        accepted = tuple(value.strip().casefold() for value in self.accepted_subtypes)
        if not accepted or any(not value for value in accepted):
            raise ValueError(f"Slot '{self.slot_id}' requires accepted equipment subtypes.")
        object.__setattr__(self, "slot_id", self.slot_id.strip().casefold())
        object.__setattr__(self, "equipment_slot", self.equipment_slot.strip().casefold())
        object.__setattr__(self, "accepted_subtypes", accepted)


@dataclass(frozen=True)
class ItemConfig:
    inventory_capacity: int
    rarities: tuple[ItemRarityDefinition, ...]
    equipment_slots: tuple[EquipmentSlotDefinition, ...]

    def __post_init__(self) -> None:
        if isinstance(self.inventory_capacity, bool) or not isinstance(self.inventory_capacity, int) or self.inventory_capacity < 1:
            raise ValueError("Inventory capacity must be a positive whole number.")
        rarities = tuple(self.rarities)
        slots = tuple(self.equipment_slots)
        if not rarities or any(not isinstance(item, ItemRarityDefinition) for item in rarities):
            raise ValueError("Item config requires valid rarity definitions.")
        if any(not isinstance(item, EquipmentSlotDefinition) for item in slots):
            raise ValueError("Item config contains an invalid equipment slot.")
        if len({item.rarity_id for item in rarities}) != len(rarities):
            raise ValueError("Item rarity IDs must be unique.")
        if len({item.slot_id for item in slots}) != len(slots):
            raise ValueError("Equipment slot IDs must be unique.")
        object.__setattr__(self, "rarities", rarities)
        object.__setattr__(self, "equipment_slots", slots)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ItemConfig":
        try:
            rarities = tuple(ItemRarityDefinition(**item) for item in data["rarities"])
            slots = tuple(EquipmentSlotDefinition(**item) for item in data["equipment_slots"])
            return cls(data.get("inventory_capacity", 50), rarities, slots)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Malformed item settings: {exc}") from exc

    @classmethod
    def load(cls, path: str | Path) -> "ItemConfig":
        source = Path(path)
        if not source.is_file():
            raise ValueError(f"Item settings file is missing: {source}")
        try:
            data = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"Could not load item settings '{source}': {exc}") from exc
        if not isinstance(data, Mapping):
            raise ValueError("Item settings root must be a JSON object.")
        return cls.from_dict(data)

    @classmethod
    def load_default(cls) -> "ItemConfig":
        return cls.load(Path(__file__).resolve().parents[2] / "data" / "items" / "item_config.json")

    @property
    def rarity_by_id(self) -> dict[str, ItemRarityDefinition]:
        return {item.rarity_id: item for item in self.rarities}

    @property
    def slot_by_id(self) -> dict[str, EquipmentSlotDefinition]:
        return {item.slot_id: item for item in self.equipment_slots}


__all__ = ["EquipmentSlotDefinition", "ItemConfig", "ItemRarityDefinition"]
