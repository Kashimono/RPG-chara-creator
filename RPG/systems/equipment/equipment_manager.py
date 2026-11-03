"""Controlled equipment changes and effective character bonus updates."""

from __future__ import annotations

from dataclasses import dataclass, replace

from .equipment import EquippedItem, EquipmentState
from .equipment_calculator import EquipmentCalculator
from ..inventory.inventory import UnclaimedLoot
from ..inventory.inventory_manager import InventoryManager, InventoryOperationError
from ..inventory.item import ItemInstance
from ..inventory.item_database import ItemDatabase


class EquipmentOperationError(ValueError):
    """Raised when equipment cannot be changed safely."""


@dataclass(frozen=True)
class EquipmentChangeResult:
    slot_id: str
    equipped_item: ItemInstance | None
    returned_item: ItemInstance | None = None


class EquipmentManager:
    def __init__(self, game_state, item_database: ItemDatabase | None = None, inventory_manager: InventoryManager | None = None) -> None:
        self.game_state = game_state
        self.item_database = item_database or ItemDatabase.load_default()
        self.inventory = inventory_manager or InventoryManager(game_state, self.item_database)
        self._repair_equipment()
        self._apply_bonuses(self.state)

    @property
    def state(self) -> EquipmentState:
        return self.game_state.equipment

    @property
    def slots(self):
        return self.item_database.config.equipment_slots

    def get_equipped(self, slot_id: str) -> ItemInstance | None:
        return self.state.get(slot_id)

    def equip(self, slot_id: str, instance_id: str) -> EquipmentChangeResult:
        slot = self._slot(slot_id)
        instance = self.inventory.get_item(instance_id)
        if instance is None:
            if self.state.find_instance(instance_id):
                raise EquipmentOperationError("That item is already equipped.")
            raise EquipmentOperationError("Item instance was not found in the inventory.")
        definition = self.item_database.get_by_id(instance.item_id)
        if not definition.can_equip:
            raise EquipmentOperationError(f"{definition.name} cannot be equipped.")
        if definition.equipment_slot != slot.equipment_slot or definition.subtype not in slot.accepted_subtypes:
            raise EquipmentOperationError(f"{definition.name} is incompatible with {slot.display_name}.")
        if self.game_state.character.level < definition.required_level:
            raise EquipmentOperationError(f"{definition.name} requires level {definition.required_level}.")
        if instance.quantity != 1:
            raise EquipmentOperationError("Equipment instances must have quantity one.")
        if self.state.find_instance(instance.instance_id):
            raise EquipmentOperationError("That item is already assigned to an equipment slot.")

        previous = self.state.get(slot.slot_id)
        bag_items = tuple(item for item in self.inventory.state.items if item.instance_id != instance.instance_id)
        if previous is not None:
            if any(item.instance_id == previous.instance_id for item in bag_items):
                raise EquipmentOperationError("Equipment instance is already present in the inventory.")
            bag_items += (previous,)
        equipment = tuple(entry for entry in self.state.equipped_items if entry.slot_id != slot.slot_id)
        equipment += (EquippedItem(slot.slot_id, instance),)
        new_state = EquipmentState(equipment)
        self._validate_state(new_state)
        # The removed bag item makes room for a replaced item, so this swap is capacity-neutral.
        self.game_state.inventory = replace(self.inventory.state, items=bag_items)
        self.game_state.equipment = new_state
        self._apply_bonuses(new_state)
        return EquipmentChangeResult(slot.slot_id, instance, previous)

    def unequip(self, slot_id: str) -> EquipmentChangeResult:
        slot = self._slot(slot_id)
        instance = self.state.get(slot.slot_id)
        if instance is None:
            raise EquipmentOperationError(f"{slot.display_name} is empty.")
        if self.inventory.free_slots < 1:
            raise EquipmentOperationError("Free an inventory slot before unequipping this item.")
        equipment = EquipmentState(tuple(entry for entry in self.state.equipped_items if entry.slot_id != slot.slot_id))
        self._validate_state(equipment)
        bag = self.inventory.state.items + (instance,)
        self.game_state.inventory = replace(self.inventory.state, items=bag)
        self.game_state.equipment = equipment
        self._apply_bonuses(equipment)
        return EquipmentChangeResult(slot.slot_id, None, instance)

    def _slot(self, slot_id: str):
        if not isinstance(slot_id, str):
            raise EquipmentOperationError("An equipment slot is required.")
        slot = self.item_database.config.slot_by_id.get(slot_id.casefold())
        if slot is None:
            raise EquipmentOperationError(f"Unknown equipment slot: {slot_id}.")
        return slot

    def _validate_state(self, state: EquipmentState) -> None:
        seen_ids: set[str] = set()
        for entry in state.equipped_items:
            slot = self._slot(entry.slot_id)
            definition = self.item_database.get_by_id(entry.item.item_id)
            if not definition.can_equip or definition.equipment_slot != slot.equipment_slot or definition.subtype not in slot.accepted_subtypes:
                raise EquipmentOperationError(f"{definition.name} is incompatible with {slot.display_name}.")
            if entry.item.quantity != 1 or entry.item.instance_id in seen_ids:
                raise EquipmentOperationError("An equipment instance cannot be assigned more than once.")
            seen_ids.add(entry.item.instance_id)

    def _apply_bonuses(self, state: EquipmentState) -> None:
        values = EquipmentCalculator.total_bonuses(
            tuple((entry.slot_id, entry.item) for entry in state.equipped_items), self.item_database,
        )
        self.game_state.character.set_equipment_bonuses(values)

    def _repair_equipment(self) -> None:
        valid: list[EquippedItem] = []
        occupied_ids = {item.instance_id for item in self.inventory.state.items}
        used_ids: set[str] = set()
        used_slots: set[str] = set()
        unclaimed = list(self.inventory.state.unclaimed_loot)
        for entry in self.state.equipped_items:
            try:
                slot = self._slot(entry.slot_id)
                definition = self.item_database.get_by_id(entry.item.item_id)
                if (entry.slot_id in used_slots or entry.item.instance_id in occupied_ids or entry.item.instance_id in used_ids
                        or not definition.can_equip or definition.equipment_slot != slot.equipment_slot
                        or definition.subtype not in slot.accepted_subtypes or entry.item.quantity != 1):
                    raise EquipmentOperationError("Saved equipment assignment is invalid.")
            except (EquipmentOperationError, ValueError) as exc:
                if entry.item.instance_id in occupied_ids or entry.item.instance_id in used_ids:
                    # The same instance is already represented by the bag or an accepted slot.
                    continue
                reason = f"Saved equipment assignment preserved: {exc}"
                try:
                    stored = self.inventory.add_instance(entry.item)
                except (InventoryOperationError, ValueError):
                    stored = False
                if not stored:
                    unclaimed.append(UnclaimedLoot.create(
                        entry.item.item_id, entry.item.quantity, source="Saved equipment", encounter_id=None,
                        reason=reason, unclaimed_id=None,
                    ))
                continue
            valid.append(entry)
            used_ids.add(entry.item.instance_id)
            used_slots.add(entry.slot_id)
        new_state = EquipmentState(tuple(valid))
        self.game_state.equipment = new_state
        if tuple(unclaimed) != self.inventory.state.unclaimed_loot:
            self.game_state.inventory = replace(self.inventory.state, unclaimed_loot=tuple(unclaimed))


__all__ = ["EquipmentChangeResult", "EquipmentManager", "EquipmentOperationError"]
