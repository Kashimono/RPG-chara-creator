# Inventory and Equipment

Update 5 adds data-driven items, bag storage, equipment, enemy loot collection, and item sales. The rules live in `RPG/systems/inventory/` and `RPG/systems/equipment/`; UI pages call those managers and never edit saved item collections themselves.

## Ownership and records

- `GameState.inventory` stores capacity, item instances, unclaimed drops, and processed loot keys.
- `GameState.equipment` stores equipped instances by slot. Equipped instances do not use bag capacity.
- `ItemDatabase` loads static definitions from `RPG/data/items/` and validates IDs, rarity references, stack sizes, attribute names, slot types, and accepted subtypes.
- `ItemDefinition` describes a kind of item. `ItemInstance` identifies one owned item or stack, including its unique instance ID, quantity, acquisition time, and optional instance data.
- `InventoryManager` controls add/remove/split, filtering, sorting, drop collection, unclaimed loot claims, discard, and sale operations.
- `EquipmentManager` validates slot compatibility and level requirements and commits equip, unequip, and replacement operations.

The bag capacity defaults to 50 slots in `item_config.json`. Each distinct `ItemInstance` uses one slot; adding stackable items fills compatible existing stacks up to `max_stack` before using a new slot. Equipment does not stack and each piece uses its own instance ID. Splitting a stack requires one free slot.

## Item data

`equipment.json`, `materials.json`, and `miscellaneous.json` each contain an `items` list. An item definition has this shape:

```json
{
  "id": "sample_sword",
  "name": "Sample Sword",
  "description": "A simple data-defined weapon.",
  "type": "equipment",
  "subtype": "weapon",
  "rarity": "common",
  "max_stack": 1,
  "sell_value": 10,
  "can_sell": true,
  "can_discard": true,
  "can_equip": true,
  "equipment_slot": "main_hand",
  "required_level": 1,
  "bonuses": { "attack": 5 },
  "icon": null,
  "metadata": {}
}
```

Supported item types are `equipment`, `material`, and `miscellaneous`. Equipment subtypes are `weapon`, `armor`, and `accessory`. Non-equipment definitions must not specify equipment slots or bonuses. Stack size is one for equipment. All bonus names must match an `AttributeSheet` field: `hp`, `mp`, `attack`, `agility`, `stamina`, `physical_defense`, `magical_defense`, `critical_chance`, `critical_damage`, `attack_speed`, `hp_regeneration`, or `mp_regeneration`.

Examples of the data-only changes required to add content:

- **Weapon:** use `type: equipment`, `subtype: weapon`, and an accepted slot such as `main_hand`; set bonuses such as `attack` or `critical_damage`.
- **Armor:** use `type: equipment`, `subtype: armor`, and a configured armor slot such as `chest`; set bonuses such as `hp` and `physical_defense`.
- **Accessory:** use `type: equipment`, `subtype: accessory`, and `equipment_slot: accessory`; the configured `accessory_1` and `accessory_2` slots accept it.
- **Material:** use `type: material`, a category subtype such as `essence`, `max_stack` above one, and no equipment properties.

Add each definition to the appropriate JSON file. No inventory or equipment code changes are needed for these examples. IDs must be unique across all item files.

## Rarity, slots, and stat calculation

`item_config.json` configures inventory capacity, six rarity records, and the slot list. Rarities are Common, Uncommon, Rare, Epic, Legendary, and Mythic. Each contains a display color, `bonus_multiplier`, and `sell_multiplier`.

When calculating equipped bonuses:

```text
effective item bonus = configured item bonus × rarity bonus multiplier
total equipment bonus = sum of each equipped instance's effective bonus
```

The shared `calculate_attributes` function adds equipment bonuses to the corresponding effective primary stat after race/class multipliers. Equipment bonuses to advanced attributes are added to the existing derived value after its existing formula. Existing caps still apply to Critical Chance, Critical Damage, and Attack Speed. Removing or replacing gear recalculates the same path. Base stats, potentials, allocated points, and race/class profiles are not changed by equipment.

Changing maximum HP preserves the character's current HP and clamps it to the new maximum; it does not heal the character. MP is currently a maximum attribute only and has no separate current-value tracker.

Slots are Main Hand, Off Hand, Head, Chest, Legs, Feet, Hands, Accessory 1, and Accessory 2. Slot IDs are unique; accessory slots share the `accessory` item slot type. An item must match both its configured slot type and an accepted subtype, and the character must meet `required_level`. Equipping a new item atomically returns the previous item in that slot to the bag. Unequipping requires one free bag slot. An instance cannot be assigned twice.

## Loot and selling

Combat continues to use the existing loot-table roll. Gold drops remain currency and are credited by the existing EconomyManager reward flow. Non-currency drops go through `InventoryManager.collect_drops`. The encounter ID and drop index are persisted as a deduplication key. If a definition is missing or the bag is full, the exact item ID and quantity are saved as an unclaimed entry with source and reason; the Inventory page can claim it later when space is available.

The sale value is:

```text
Gold = round-half-up(base sell value × rarity sell multiplier × quantity)
```

Sales are checked against wallet limits and recorded as earned `item_sale` EconomyManager transactions. The inventory mutation is applied only after those validations succeed. Items marked unsellable and equipped items are rejected. Discard follows each definition's `can_discard` flag and does not credit Gold.

## Save compatibility

Schema 7 serializes inventory and equipment inside the shared `GameState` JSON envelope. Item definitions remain static files; only player-owned instances and state are saved. Version 6 and earlier saves load with empty inventory and equipment state while retaining their character, combat, and economy data. Loading performs migration in memory; saving writes schema 7.

Implemented now: item data validation, stackable bag storage, filtering/sorting, item inspection, gear comparison, nine equipment slots, rarity-scaled bonuses and value, loot collection with claimable overflow, item sales, and save/load support.

Future features: consumables, crafting, enhancements, refining, enchanting, random affixes, and equipment durability. These are not implemented by Update 5.
