"""Controlled bag operations, loot collection, stacking, filtering, and sales."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from decimal import Decimal, DecimalException, ROUND_HALF_UP
from typing import TYPE_CHECKING, Callable, Iterable, Sequence
from uuid import uuid4

from .inventory import InventoryState, UnclaimedLoot
from .item import ItemDefinition, ItemInstance
from .item_database import ItemDatabase, ItemDatabaseError
from ..economy.economy_manager import EconomyManager, EconomyTransactionError
from ..economy.transaction import TransactionType

if TYPE_CHECKING:
    from ...core.game_state import GameState
    from ...systems.combat.loot_table import LootDrop


class InventoryOperationError(ValueError):
    """Raised when an inventory operation cannot be completed safely."""


@dataclass(frozen=True)
class InventoryAddResult:
    requested_quantity: int
    added_quantity: int
    remaining_quantity: int
    instance_ids: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return self.remaining_quantity == 0


@dataclass(frozen=True)
class ItemCollectionResult:
    item_id: str
    item_name: str
    rarity: str | None
    rarity_color: str
    requested_quantity: int
    collected_quantity: int
    unclaimed_quantity: int
    unclaimed_id: str | None = None
    reason: str | None = None
    duplicate: bool = False


@dataclass(frozen=True)
class ItemSaleResult:
    success: bool
    message: str
    item_id: str | None = None
    quantity: int = 0
    gold_earned: int = 0


class InventoryManager:
    def __init__(
        self,
        game_state: "GameState",
        item_database: ItemDatabase | None = None,
        *,
        economy_manager: EconomyManager | None = None,
        id_factory: Callable[[], str] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.game_state = game_state
        self.item_database = item_database or ItemDatabase.load_default()
        self.economy_manager = economy_manager or EconomyManager(game_state)
        self._id_factory = id_factory or (lambda: uuid4().hex)
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        if self.game_state.inventory.capacity is None:
            self.game_state.inventory = replace(
                self.game_state.inventory,
                capacity=self.item_database.config.inventory_capacity,
            )
        self._repair_inventory_state()

    @property
    def state(self) -> InventoryState:
        return self.game_state.inventory

    @property
    def capacity(self) -> int:
        return self.state.capacity or self.item_database.config.inventory_capacity

    @property
    def used_slots(self) -> int:
        return len(self.state.items)

    @property
    def free_slots(self) -> int:
        return max(0, self.capacity - self.used_slots)

    def get_items(self) -> tuple[ItemInstance, ...]:
        return self.state.items

    def get_item(self, instance_id: str) -> ItemInstance | None:
        return next((item for item in self.state.items if item.instance_id == instance_id), None)

    def get_by_item_id(self, item_id: str) -> tuple[ItemInstance, ...]:
        normalized = item_id.casefold()
        return tuple(item for item in self.state.items if item.item_id == normalized)

    def has_quantity(self, item_id: str, quantity: int = 1) -> bool:
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            return False
        return sum(item.quantity for item in self.get_by_item_id(item_id)) >= quantity

    def can_add(self, item_id: str, quantity: int = 1, *, instance_data: dict | None = None) -> bool:
        try:
            _items, _ids, remaining = self._plan_add(item_id, quantity, instance_data=instance_data)
            return remaining == 0
        except InventoryOperationError:
            return False

    def add_item(
        self,
        item_id: str,
        quantity: int = 1,
        *,
        instance_data: dict | None = None,
    ) -> InventoryAddResult:
        items, instance_ids, remaining = self._plan_add(item_id, quantity, instance_data=instance_data)
        added = quantity - remaining
        if added:
            self.game_state.inventory = replace(self.state, items=items)
        return InventoryAddResult(quantity, added, remaining, instance_ids)

    def add_instance(self, instance: ItemInstance) -> bool:
        """Return an existing equipped instance to the bag without changing its ID."""
        if not isinstance(instance, ItemInstance):
            raise InventoryOperationError("An item instance is required.")
        definition = self._definition(instance.item_id)
        if instance.quantity != 1 or definition.max_stack != 1:
            raise InventoryOperationError("This operation accepts one non-stackable item instance.")
        if self.get_item(instance.instance_id) is not None:
            raise InventoryOperationError("That item instance is already in the inventory.")
        if self.used_slots >= self.capacity:
            return False
        self.game_state.inventory = replace(self.state, items=self.state.items + (instance,))
        return True

    def remove_item(self, instance_id: str, quantity: int = 1) -> ItemInstance:
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise InventoryOperationError("Removal quantity must be a positive whole number.")
        item = self.get_item(instance_id)
        if item is None:
            if self.game_state.equipment.find_instance(instance_id):
                raise InventoryOperationError("Unequip an item before removing it from the inventory.")
            raise InventoryOperationError(f"Item instance '{instance_id}' was not found in the inventory.")
        if quantity > item.quantity:
            raise InventoryOperationError("Removal quantity exceeds the stack quantity.")
        definition = self._definition(item.item_id)
        if definition.can_equip and quantity != 1:
            raise InventoryOperationError("Equipment instances can only be removed one at a time.")
        items = list(self.state.items)
        index = items.index(item)
        if quantity == item.quantity:
            items.pop(index)
        else:
            items[index] = replace(item, quantity=item.quantity - quantity)
        self.game_state.inventory = replace(self.state, items=tuple(items))
        return item if quantity == item.quantity else replace(item, quantity=quantity)

    def split_stack(self, instance_id: str, quantity: int) -> ItemInstance:
        item = self.get_item(instance_id)
        if item is None:
            raise InventoryOperationError("Item instance was not found.")
        definition = self._definition(item.item_id)
        if definition.can_equip or definition.max_stack <= 1:
            raise InventoryOperationError("Equipment and non-stackable items cannot be split.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or not 1 <= quantity < item.quantity:
            raise InventoryOperationError("Split quantity must be positive and smaller than the stack.")
        if self.used_slots >= self.capacity:
            raise InventoryOperationError("There is no free inventory slot for another stack.")
        now = self._timestamp()
        new_item = ItemInstance(
            instance_id=self._id_factory(),
            item_id=item.item_id,
            quantity=quantity,
            acquired_at=now,
            instance_data=item.instance_data,
        )
        items = list(self.state.items)
        items[items.index(item)] = replace(item, quantity=item.quantity - quantity)
        items.append(new_item)
        self.game_state.inventory = replace(self.state, items=tuple(items))
        return new_item

    def filter_items(self, *, category: str | None = None, rarity: str | None = None) -> tuple[ItemInstance, ...]:
        result: list[ItemInstance] = []
        category = category.casefold() if category else None
        rarity = rarity.casefold() if rarity else None
        for instance in self.state.items:
            definition = self._definition(instance.item_id)
            if rarity and definition.rarity != rarity:
                continue
            if category and not self._matches_category(definition, category):
                continue
            result.append(instance)
        return tuple(result)

    def sort_items(self, items: Iterable[ItemInstance] | None = None, *, sort_by: str = "name", reverse: bool = False) -> tuple[ItemInstance, ...]:
        source = tuple(self.state.items if items is None else items)
        rarity_order = {item.rarity_id: index for index, item in enumerate(self.item_database.config.rarities)}
        sorters = {
            "name": lambda item: self._definition(item.item_id).name.casefold(),
            "type": lambda item: (self._definition(item.item_id).item_type, self._definition(item.item_id).subtype),
            "rarity": lambda item: rarity_order[self._definition(item.item_id).rarity],
            "selling_value": lambda item: self._sorting_sale_value(item),
            "quantity": lambda item: item.quantity,
            "acquisition_date": lambda item: item.acquired_at,
        }
        try:
            sorter = sorters[sort_by.casefold()]
        except (AttributeError, KeyError) as exc:
            raise InventoryOperationError(f"Unknown inventory sort order: {sort_by}") from exc
        return tuple(sorted(source, key=sorter, reverse=reverse))

    def collect_drops(self, drops: Sequence["LootDrop"], *, encounter_id: str, source: str) -> tuple[ItemCollectionResult, ...]:
        results: list[ItemCollectionResult] = []
        for index, drop in enumerate(drops):
            if drop.currency_type is not None:
                continue
            claim_key = f"{encounter_id}:{index}:{drop.reward_id.casefold()}"
            if claim_key in self.state.processed_loot_keys:
                definition = self.item_database.try_get(drop.reward_id)
                rarity = self.item_database.config.rarity_by_id.get(definition.rarity) if definition else None
                results.append(ItemCollectionResult(
                    drop.reward_id,
                    definition.name if definition else drop.reward_id,
                    definition.rarity if definition else None,
                    rarity.color_hex if rarity else "#e7bd65",
                    drop.quantity,
                    0,
                    0,
                    duplicate=True,
                    reason="This encounter drop was already processed.",
                ))
                continue

            definition = self.item_database.try_get(drop.reward_id)
            reason: str | None = None
            unclaimed_id = None
            if definition is None:
                add_result = InventoryAddResult(drop.quantity, 0, drop.quantity, ())
                reason = "Item definition is unavailable."
            else:
                try:
                    add_result = self.add_item(definition.item_id, drop.quantity)
                    if add_result.remaining_quantity:
                        reason = "Inventory capacity reached."
                except InventoryOperationError as exc:
                    add_result = InventoryAddResult(drop.quantity, 0, drop.quantity, ())
                    reason = str(exc)
            if add_result.remaining_quantity:
                unclaimed = UnclaimedLoot.create(
                    drop.reward_id,
                    add_result.remaining_quantity,
                    source=source,
                    encounter_id=encounter_id,
                    reason=reason or "The drop could not be collected.",
                    unclaimed_id=self._id_factory(),
                )
                unclaimed_id = unclaimed.unclaimed_id
                self.game_state.inventory = replace(
                    self.state,
                    unclaimed_loot=self.state.unclaimed_loot + (unclaimed,),
                )
            self.game_state.inventory = replace(
                self.state,
                processed_loot_keys=self.state.processed_loot_keys + (claim_key,),
            )
            rarity = self.item_database.config.rarity_by_id.get(definition.rarity) if definition else None
            results.append(ItemCollectionResult(
                drop.reward_id,
                definition.name if definition else drop.reward_id,
                definition.rarity if definition else None,
                rarity.color_hex if rarity else "#e7bd65",
                drop.quantity,
                add_result.added_quantity,
                add_result.remaining_quantity,
                unclaimed_id,
                reason,
            ))
        return tuple(results)

    def claim_unclaimed(self, unclaimed_id: str) -> ItemCollectionResult:
        entry = next((loot for loot in self.state.unclaimed_loot if loot.unclaimed_id == unclaimed_id), None)
        if entry is None:
            raise InventoryOperationError("Unclaimed loot entry was not found.")
        definition = self.item_database.try_get(entry.item_id)
        if definition is None:
            return ItemCollectionResult(entry.item_id, entry.item_id, None, "#e7bd65", entry.quantity, 0, entry.quantity, entry.unclaimed_id, "Item definition is unavailable.")
        add_result = self._plan_add(definition.item_id, entry.quantity)
        items, instance_ids, remaining = add_result
        collected = entry.quantity - remaining
        if collected == 0:
            return ItemCollectionResult(entry.item_id, definition.name, definition.rarity, self.item_database.config.rarity_by_id[definition.rarity].color_hex, entry.quantity, 0, entry.quantity, entry.unclaimed_id, "Inventory capacity reached.")
        remaining_unclaimed = tuple(
            replace(loot, quantity=remaining) if loot.unclaimed_id == entry.unclaimed_id and remaining else loot
            for loot in self.state.unclaimed_loot
            if loot.unclaimed_id != entry.unclaimed_id or remaining
        )
        self.game_state.inventory = replace(self.state, items=items, unclaimed_loot=remaining_unclaimed)
        return ItemCollectionResult(
            definition.item_id, definition.name, definition.rarity,
            self.item_database.config.rarity_by_id[definition.rarity].color_hex,
            entry.quantity, collected, remaining, entry.unclaimed_id if remaining else None,
            "Inventory capacity reached." if remaining else None,
        )

    def calculate_sell_value(self, item_id: str, quantity: int = 1) -> int:
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise InventoryOperationError("Sale quantity must be a positive whole number.")
        definition = self._definition(item_id)
        if not definition.can_sell:
            raise InventoryOperationError(f"{definition.name} cannot be sold.")
        rarity = self.item_database.config.rarity_by_id[definition.rarity]
        try:
            value = int((Decimal(definition.sell_value) * Decimal(str(rarity.sell_multiplier)) * quantity).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        except (DecimalException, OverflowError) as exc:
            raise InventoryOperationError("Sale value exceeds the supported currency range.") from exc
        from ..economy.currency import MAX_CURRENCY_VALUE
        if not 0 < value <= MAX_CURRENCY_VALUE:
            raise InventoryOperationError("Sale value exceeds the supported currency range.")
        return value

    def sell_item(self, instance_id: str, quantity: int = 1) -> ItemSaleResult:
        item = self.get_item(instance_id)
        if item is None:
            if self.game_state.equipment.find_instance(instance_id):
                return ItemSaleResult(False, "Unequip an item before selling it.")
            return ItemSaleResult(False, "Item instance was not found in the inventory.")
        try:
            definition = self._definition(item.item_id)
            if not definition.can_sell:
                raise InventoryOperationError(f"{definition.name} cannot be sold.")
            if isinstance(quantity, bool) or not isinstance(quantity, int) or not 1 <= quantity <= item.quantity:
                raise InventoryOperationError("Sale quantity must be within the stack quantity.")
            gold = self.calculate_sell_value(item.item_id, quantity)
            new_items = list(self.state.items)
            index = new_items.index(item)
            if quantity == item.quantity:
                new_items.pop(index)
            else:
                new_items[index] = replace(item, quantity=item.quantity - quantity)
        except InventoryOperationError as exc:
            return ItemSaleResult(False, str(exc), item.item_id, quantity)

        try:
            transaction = self.economy_manager.credit_currency_with_operation(
                gold,
                transaction_type=TransactionType.ITEM_SALE,
                source=definition.name,
                description=f"Sold {quantity} × {definition.name}.",
                reference_id=item.instance_id,
                apply_operation=lambda: self._commit_inventory(new_items),
            )
        except EconomyTransactionError as exc:
            return ItemSaleResult(False, str(exc), item.item_id, quantity)
        if transaction is None:
            return ItemSaleResult(False, "Item sale could not be completed.", item.item_id, quantity)
        return ItemSaleResult(True, f"Sold {quantity} × {definition.name} for {gold:,} G.", item.item_id, quantity, gold)

    def discard_item(self, instance_id: str, quantity: int = 1) -> ItemSaleResult:
        item = self.get_item(instance_id)
        if item is None:
            return ItemSaleResult(False, "Item instance was not found in the inventory.")
        definition = self._definition(item.item_id)
        if not definition.can_discard:
            return ItemSaleResult(False, f"{definition.name} cannot be discarded.", item.item_id)
        try:
            self.remove_item(instance_id, quantity)
        except InventoryOperationError as exc:
            return ItemSaleResult(False, str(exc), item.item_id, quantity)
        return ItemSaleResult(True, f"Discarded {quantity} × {definition.name}.", item.item_id, quantity)

    def _plan_add(
        self,
        item_id: str,
        quantity: int,
        *,
        instance_data: dict | None = None,
        preferred_instance_id: str | None = None,
    ) -> tuple[tuple[ItemInstance, ...], tuple[str, ...], int]:
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise InventoryOperationError("Addition quantity must be a positive whole number.")
        definition = self._definition(item_id)
        if definition.can_equip and quantity > 1:
            # Each piece of equipment receives a distinct instance and bag slot.
            pass
        items = list(self.state.items)
        remaining = quantity
        added_ids: list[str] = []
        if not definition.can_equip and definition.max_stack > 1:
            for index, existing in enumerate(items):
                if existing.item_id != definition.item_id or dict(existing.instance_data) != dict(instance_data or {}):
                    continue
                space = definition.max_stack - existing.quantity
                if space <= 0:
                    continue
                moved = min(space, remaining)
                items[index] = replace(existing, quantity=existing.quantity + moved)
                remaining -= moved
                added_ids.append(existing.instance_id)
                if remaining == 0:
                    break
        while remaining > 0 and len(items) < self.capacity:
            stack_size = 1 if definition.can_equip else min(definition.max_stack, remaining)
            if preferred_instance_id and not added_ids and len(items) == len(self.state.items):
                instance_id = preferred_instance_id
            else:
                instance_id = self._id_factory()
            instance = ItemInstance(
                instance_id=instance_id,
                item_id=definition.item_id,
                quantity=stack_size,
                acquired_at=self._timestamp(),
                instance_data=instance_data or {},
            )
            if any(existing.instance_id == instance_id for existing in items) or self.game_state.equipment.find_instance(instance_id):
                raise InventoryOperationError("Item instance ID must be unique.")
            items.append(instance)
            added_ids.append(instance.instance_id)
            remaining -= stack_size
        return tuple(items), tuple(dict.fromkeys(added_ids)), remaining

    def _repair_inventory_state(self) -> None:
        valid: list[ItemInstance] = []
        unclaimed = list(self.state.unclaimed_loot)
        seen_ids: set[str] = set()
        capacity = self.capacity
        for item in self.state.items:
            if item.instance_id in seen_ids:
                unclaimed.append(UnclaimedLoot.create(
                    item.item_id, item.quantity, source="Saved inventory", encounter_id=None,
                    reason="Duplicate saved item instance ID; item quantity preserved here.",
                    unclaimed_id=self._id_factory(),
                ))
                continue
            seen_ids.add(item.instance_id)
            definition = self.item_database.try_get(item.item_id)
            reason = None
            if definition is None:
                reason = "Item definition is unavailable; preserved from the save."
            elif item.quantity > definition.max_stack or (definition.can_equip and item.quantity != 1):
                reason = "Saved item quantity did not match its definition."
            elif len(valid) >= capacity:
                reason = "Saved inventory exceeds configured capacity."
            if reason:
                unclaimed.append(UnclaimedLoot.create(
                    item.item_id, item.quantity, source="Saved inventory", encounter_id=None,
                    reason=reason, unclaimed_id=self._id_factory(),
                ))
            else:
                valid.append(item)
        if tuple(valid) != self.state.items or tuple(unclaimed) != self.state.unclaimed_loot:
            self.game_state.inventory = replace(self.state, items=tuple(valid), unclaimed_loot=tuple(unclaimed))

    def _definition(self, item_id: str) -> ItemDefinition:
        try:
            return self.item_database.get_by_id(item_id)
        except ItemDatabaseError as exc:
            raise InventoryOperationError(str(exc)) from exc

    def _sorting_sale_value(self, item: ItemInstance) -> int:
        definition = self._definition(item.item_id)
        if not definition.can_sell:
            return 0
        return self.calculate_sell_value(item.item_id, item.quantity)

    def _commit_inventory(self, items: Sequence[ItemInstance]) -> bool:
        self.game_state.inventory = replace(self.state, items=tuple(items))
        return True

    def _timestamp(self) -> str:
        value = self._clock()
        if not isinstance(value, datetime):
            raise InventoryOperationError("Inventory clock must return a datetime.")
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()

    def _matches_category(self, definition: ItemDefinition, category: str) -> bool:
        if category in {"all", "all items"}:
            return True
        if category in {"weapons", "weapon"}:
            return definition.item_type == "equipment" and definition.subtype == "weapon"
        if category in {"armor", "armour"}:
            return definition.item_type == "equipment" and definition.subtype == "armor"
        if category in {"accessories", "accessory"}:
            return definition.item_type == "equipment" and definition.subtype == "accessory"
        if category == "equipment":
            return definition.item_type == "equipment"
        if category in {"materials", "material"}:
            return definition.item_type == "material"
        if category in {"miscellaneous", "misc"}:
            return definition.item_type == "miscellaneous"
        return False


__all__ = [
    "InventoryAddResult",
    "InventoryManager",
    "InventoryOperationError",
    "ItemCollectionResult",
    "ItemSaleResult",
]
