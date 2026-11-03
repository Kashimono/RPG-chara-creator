"""Data-driven item definitions validated against shared rarity and slot settings."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from .item import ItemDefinition
from .item_config import ItemConfig


class ItemDatabaseError(ValueError):
    """Raised when item data is missing, malformed, or internally inconsistent."""


class ItemDatabase:
    def __init__(self, definitions: Iterable[ItemDefinition], config: ItemConfig) -> None:
        self.config = config
        items = tuple(definitions)
        if any(not isinstance(item, ItemDefinition) for item in items):
            raise ItemDatabaseError("Item database contains an invalid definition.")
        self._items: dict[str, ItemDefinition] = {}
        rarities = config.rarity_by_id
        slot_types = {slot.equipment_slot for slot in config.equipment_slots}
        for item in items:
            key = item.item_id.casefold()
            if key in self._items:
                raise ItemDatabaseError(f"Duplicate item ID: {item.item_id}")
            if item.rarity not in rarities:
                raise ItemDatabaseError(f"Item '{item.item_id}' references unknown rarity '{item.rarity}'.")
            if item.can_equip:
                if item.equipment_slot not in slot_types:
                    raise ItemDatabaseError(f"Equipment '{item.item_id}' references unknown slot type '{item.equipment_slot}'.")
                compatible = any(
                    slot.equipment_slot == item.equipment_slot and item.subtype in slot.accepted_subtypes
                    for slot in config.equipment_slots
                )
                if not compatible:
                    raise ItemDatabaseError(f"Equipment '{item.item_id}' is incompatible with its configured slot type.")
            self._items[key] = item

    @classmethod
    def from_definitions(cls, definitions: Iterable[ItemDefinition], config: ItemConfig | None = None) -> "ItemDatabase":
        return cls(definitions, config or ItemConfig.load_default())

    @classmethod
    def load(cls, item_files: Iterable[str | Path], config_path: str | Path) -> "ItemDatabase":
        try:
            config = ItemConfig.load(config_path)
        except (OSError, ValueError) as exc:
            raise ItemDatabaseError(str(exc)) from exc
        definitions: list[ItemDefinition] = []
        for item_path in item_files:
            source = Path(item_path)
            if not source.is_file():
                raise ItemDatabaseError(f"Item definition file is missing: {source}")
            try:
                data = json.loads(source.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise ItemDatabaseError(f"Could not load item definitions from '{source}': {exc}") from exc
            rows = data.get("items") if isinstance(data, Mapping) else data
            if not isinstance(rows, list):
                raise ItemDatabaseError(f"Item file '{source}' must contain an 'items' list.")
            for index, row in enumerate(rows):
                if not isinstance(row, Mapping):
                    raise ItemDatabaseError(f"Item row {index + 1} in '{source}' must be an object.")
                try:
                    definitions.append(ItemDefinition.from_dict(row))
                except ValueError as exc:
                    raise ItemDatabaseError(f"Invalid item row {index + 1} in '{source}': {exc}") from exc
        try:
            return cls(definitions, config)
        except ItemDatabaseError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise ItemDatabaseError(f"Invalid item database: {exc}") from exc

    @classmethod
    def load_default(cls) -> "ItemDatabase":
        directory = Path(__file__).resolve().parents[2] / "data" / "items"
        return cls.load(
            (directory / "equipment.json", directory / "materials.json", directory / "miscellaneous.json"),
            directory / "item_config.json",
        )

    def get_by_id(self, item_id: str) -> ItemDefinition:
        try:
            return self._items[item_id.casefold()]
        except (AttributeError, KeyError) as exc:
            raise ItemDatabaseError(f"Unknown item ID: {item_id}") from exc

    def try_get(self, item_id: str) -> ItemDefinition | None:
        return self._items.get(item_id.casefold()) if isinstance(item_id, str) else None

    def list_items(self) -> tuple[ItemDefinition, ...]:
        return tuple(self._items.values())

    def filter_items(
        self,
        *,
        item_type: str | None = None,
        subtype: str | None = None,
        rarity: str | None = None,
    ) -> tuple[ItemDefinition, ...]:
        return tuple(
            item for item in self._items.values()
            if (item_type is None or item.item_type == item_type.casefold())
            and (subtype is None or item.subtype == subtype.casefold())
            and (rarity is None or item.rarity == rarity.casefold())
        )

    def has(self, item_id: str) -> bool:
        return isinstance(item_id, str) and item_id.casefold() in self._items

    @property
    def item_ids(self) -> frozenset[str]:
        return frozenset(self._items)


__all__ = ["ItemDatabase", "ItemDatabaseError"]
