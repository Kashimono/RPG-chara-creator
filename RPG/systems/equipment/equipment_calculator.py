"""Central aggregation of configured equipment bonuses with rarity scaling."""

from __future__ import annotations

from math import isfinite
from typing import Mapping

from ..inventory.item import EQUIPMENT_ATTRIBUTES, ItemDefinition, ItemInstance
from ..inventory.item_database import ItemDatabase, ItemDatabaseError


class EquipmentCalculator:
    @staticmethod
    def item_bonuses(definition: ItemDefinition, database: ItemDatabase) -> dict[str, float]:
        if not definition.can_equip:
            raise ValueError(f"Item '{definition.item_id}' cannot be equipped.")
        rarity = database.config.rarity_by_id.get(definition.rarity)
        if rarity is None:
            raise ItemDatabaseError(f"Item '{definition.item_id}' references an unavailable rarity.")
        result: dict[str, float] = {}
        for attribute, base_value in definition.bonuses.items():
            if attribute not in EQUIPMENT_ATTRIBUTES:
                raise ItemDatabaseError(f"Item '{definition.item_id}' has unsupported bonus '{attribute}'.")
            value = float(base_value) * rarity.bonus_multiplier
            if not isfinite(value):
                raise ItemDatabaseError(f"Item '{definition.item_id}' bonus '{attribute}' exceeds numeric limits.")
            result[attribute] = value
        return result

    @classmethod
    def total_bonuses(
        cls,
        equipped: Mapping[str, ItemInstance] | tuple[tuple[str, ItemInstance], ...],
        database: ItemDatabase,
    ) -> dict[str, float]:
        totals = {attribute: 0.0 for attribute in EQUIPMENT_ATTRIBUTES}
        entries = equipped.items() if isinstance(equipped, Mapping) else equipped
        seen_instances: set[str] = set()
        for _slot_id, instance in entries:
            if instance.instance_id in seen_instances:
                raise ValueError(f"Equipment instance '{instance.instance_id}' is assigned more than once.")
            seen_instances.add(instance.instance_id)
            definition = database.get_by_id(instance.item_id)
            for attribute, value in cls.item_bonuses(definition, database).items():
                totals[attribute] += value
                if not isfinite(totals[attribute]):
                    raise ItemDatabaseError(f"Equipment bonus total for '{attribute}' exceeds numeric limits.")
        return {attribute: value for attribute, value in totals.items() if value != 0.0}


__all__ = ["EquipmentCalculator"]
