from dataclasses import replace

import pytest

from RPG.core.game_state import GameState
from RPG.systems.combat.loot_table import LootDrop
from RPG.systems.economy.currency import MAX_CURRENCY_VALUE
from RPG.systems.economy.economy_manager import EconomyManager
from RPG.systems.economy.transaction import TransactionDirection, TransactionType
from RPG.systems.equipment.equipment_manager import EquipmentManager, EquipmentOperationError
from RPG.systems.inventory.inventory_manager import InventoryManager, InventoryOperationError
from RPG.systems.inventory.item import ItemDefinition
from RPG.systems.inventory.item_database import ItemDatabase


def test_default_item_database_has_all_rarities_and_equipment_definitions():
    database = ItemDatabase.load_default()

    assert {item.rarity for item in database.list_items()} == {
        "common", "uncommon", "rare", "epic", "legendary", "mythic",
    }
    assert database.get_by_id("rusty_sword").equipment_slot == "main_hand"
    assert database.get_by_id("monster_essence").max_stack == 99
    assert len(database.config.equipment_slots) == 9


def test_item_definitions_reject_unknown_equipment_attributes():
    with pytest.raises(ValueError, match="unsupported attribute"):
        ItemDefinition.from_dict({
            "id": "bad_helm", "name": "Bad Helm", "description": "Bad data.",
            "type": "equipment", "subtype": "armor", "rarity": "common",
            "sell_value": 1,
            "can_equip": True, "equipment_slot": "head", "bonuses": {"luck": 1},
        })


def test_inventory_stacks_splits_filters_and_sorts_items():
    state = GameState()
    state.inventory = replace(state.inventory, capacity=3)
    inventory = InventoryManager(state)

    added = inventory.add_item("monster_essence", 150)
    assert added.added_quantity == 150
    assert sorted(item.quantity for item in inventory.get_items()) == [51, 99]
    assert inventory.has_quantity("monster_essence", 150)
    assert len(inventory.filter_items(category="materials", rarity="common")) == 2

    stack = max(inventory.get_items(), key=lambda item: item.quantity)
    split = inventory.split_stack(stack.instance_id, 25)
    assert split.quantity == 25
    assert inventory.used_slots == 3
    assert sorted(item.quantity for item in inventory.get_items()) == [25, 51, 74]
    assert inventory.sort_items(sort_by="quantity", reverse=True)[0].quantity == 74


def test_full_inventory_preserves_loot_and_duplicate_collection_is_blocked():
    state = GameState()
    state.inventory = replace(state.inventory, capacity=1)
    inventory = InventoryManager(state)
    inventory.add_item("rusty_sword")
    drop = LootDrop("dragon_scale", 2)

    first = inventory.collect_drops((drop,), encounter_id="encounter-1", source="Dragon")
    second = inventory.collect_drops((drop,), encounter_id="encounter-1", source="Dragon")

    assert first[0].collected_quantity == 0
    assert first[0].unclaimed_quantity == 2
    assert len(state.inventory.unclaimed_loot) == 1
    assert second[0].duplicate
    assert len(state.inventory.unclaimed_loot) == 1


def test_equipment_bonuses_use_shared_attributes_and_replacement_returns_old_item():
    state = GameState()
    state.character.level = 30
    inventory = InventoryManager(state)
    equipment = EquipmentManager(state, inventory.item_database, inventory)
    inventory.add_item("rusty_sword")
    inventory.add_item("dragon_slayer")
    player = state.character
    base_attack = player.calculated_attributes.attack

    first = inventory.get_by_item_id("rusty_sword")[0]
    equipment.equip("main_hand", first.instance_id)
    assert player.calculated_attributes.attack == base_attack + 5
    assert player.stats["Attack"].current == 0

    second = inventory.get_by_item_id("dragon_slayer")[0]
    equipment.equip("main_hand", second.instance_id)
    assert equipment.get_equipped("main_hand").instance_id == second.instance_id
    assert inventory.get_item(first.instance_id) is not None
    assert player.calculated_attributes.attack > base_attack + 5

    equipment.unequip("main_hand")
    assert player.calculated_attributes.attack == base_attack
    assert inventory.get_item(second.instance_id) is not None


def test_hp_equipment_preserves_current_health_and_clamps_when_removed():
    state = GameState()
    state.character.level = 5
    state.character.stats["HP"].current = 100
    player = state.character
    previous_max = player.maximum_hp
    player.set_current_hp(previous_max)
    inventory = InventoryManager(state)
    equipment = EquipmentManager(state, inventory.item_database, inventory)
    inventory.add_item("traveler_vest")
    vest = inventory.get_by_item_id("traveler_vest")[0]

    equipment.equip("chest", vest.instance_id)

    assert player.maximum_hp > previous_max
    assert player.current_hp == previous_max
    player.set_current_hp(player.maximum_hp)
    equipment.unequip("chest")
    assert player.current_hp == previous_max


def test_two_accessories_stack_bonuses_without_duplicate_instance_assignment():
    state = GameState()
    state.character.level = 10
    inventory = InventoryManager(state)
    equipment = EquipmentManager(state, inventory.item_database, inventory)
    inventory.add_item("silver_ring", 2)
    rings = inventory.get_by_item_id("silver_ring")
    base_chance = state.character.calculated_attributes.critical_chance

    equipment.equip("accessory_1", rings[0].instance_id)
    equipment.equip("accessory_2", rings[1].instance_id)
    assert state.character.calculated_attributes.critical_chance == pytest.approx(base_chance + 0.05)
    with pytest.raises(EquipmentOperationError, match="already equipped"):
        equipment.equip("accessory_1", rings[0].instance_id)

    equipment.unequip("accessory_1")
    assert state.character.calculated_attributes.critical_chance == pytest.approx(base_chance + 0.025)


def test_equipment_enforces_level_slot_and_bag_capacity_rules():
    state = GameState()
    state.character.level = 1
    state.inventory = replace(state.inventory, capacity=1)
    inventory = InventoryManager(state)
    equipment = EquipmentManager(state, inventory.item_database, inventory)
    inventory.add_item("iron_helm")
    helm = inventory.get_by_item_id("iron_helm")[0]
    with pytest.raises(EquipmentOperationError, match="requires level"):
        equipment.equip("head", helm.instance_id)
    with pytest.raises(EquipmentOperationError, match="incompatible"):
        equipment.equip("main_hand", helm.instance_id)

    inventory.remove_item(helm.instance_id)
    inventory.add_item("rusty_sword")
    sword = inventory.get_by_item_id("rusty_sword")[0]
    equipment.equip("main_hand", sword.instance_id)
    inventory.add_item("monster_essence")
    with pytest.raises(EquipmentOperationError, match="Free an inventory slot"):
        equipment.unequip("main_hand")


def test_item_sale_uses_rarity_multiplier_and_records_economy_transaction():
    state = GameState()
    inventory = InventoryManager(state)
    item = inventory.add_item("boss_trophy").instance_ids[0]

    result = inventory.sell_item(item)

    assert result.success
    assert result.gold_earned == 750
    assert inventory.get_item(item) is None
    assert state.economy.gold.balance == 750
    transaction = state.economy.transactions[-1]
    assert transaction.transaction_type is TransactionType.ITEM_SALE
    assert transaction.direction is TransactionDirection.EARNED
    assert transaction.amount == 750


def test_failed_item_sale_leaves_inventory_and_wallet_unchanged():
    state = GameState()
    economy = EconomyManager(state)
    economy.credit_currency(MAX_CURRENCY_VALUE, source="test", description="fill wallet")
    inventory = InventoryManager(state)
    instance_id = inventory.add_item("monster_essence").instance_ids[0]
    before = state.economy.to_dict()

    result = inventory.sell_item(instance_id)

    assert not result.success
    assert inventory.get_item(instance_id) is not None
    assert state.economy.to_dict() == before


def test_equipment_and_inventory_round_trip_and_v6_migration():
    state = GameState()
    state.character.level = 5
    inventory = InventoryManager(state)
    equipment = EquipmentManager(state, inventory.item_database, inventory)
    inventory.add_item("rusty_sword")
    inventory.add_item("monster_essence", 7)
    sword = inventory.get_by_item_id("rusty_sword")[0]
    equipment.equip("main_hand", sword.instance_id)
    economy = EconomyManager(state)
    economy.credit_currency(73, source="test", description="preserved")

    restored = GameState.from_dict(state.to_dict())
    assert restored.inventory.to_dict() == state.inventory.to_dict()
    assert restored.equipment.to_dict() == state.equipment.to_dict()
    assert restored.economy.gold.balance == 73

    old_save = state.to_dict()
    old_save["save_version"] = 6
    old_save.pop("inventory")
    old_save.pop("equipment")
    migrated = GameState.from_dict(old_save)
    assert migrated.inventory.items == ()
    assert migrated.equipment.equipped_items == ()
    assert migrated.economy.gold.balance == 73

