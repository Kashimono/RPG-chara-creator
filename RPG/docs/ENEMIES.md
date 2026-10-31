# Enemy Database and Encounters

Enemy definitions are static content, separate from combat calculations and the CustomTkinter page. The built-in database contains 17 enemies in six classifications: 5 Common, 4 Uncommon, 3 Rare, 2 Elite, 2 Boss, and 1 World Boss.

## Files and architecture

```text
RPG/data/
  enemies/
    common.json
    uncommon.json
    rare.json
    elite.json
    bosses.json
    world_bosses.json
  enemy_abilities.json
  loot_tables.json
RPG/systems/combat/
  enemy.py
  enemy_database.py
  enemy_ability.py
  boss_manager.py
  loot_table.py
  combat_manager.py
```

`EnemyDatabase` loads and validates every definition before encounters become available. IDs are unique without regard to case. Files named for a classification may only contain that classification. Ability IDs and boss phase ability references must resolve. Enemy loot table references must resolve. Errors include the file and invalid field/reference; combat does not silently substitute base values.

`EnemyDefinition` is immutable source data. `Enemy.spawn()` creates a uniquely identified mutable encounter containing current HP, active effects, phase, and reward-claim state. The definitions never receive encounter damage or scaled values.

## Classifications

| Classification | Visual | Encounter behavior |
|---|---|---|
| Common | Neutral gray | Default sequential rotation and timed respawn |
| Uncommon | Green | Selectable one-off encounter |
| Rare | Blue | Selectable one-off encounter |
| Elite | Purple | Selectable, dedicated Start Elite action, enhanced attributes and rewards |
| Boss | Red | Dedicated challenge control with confirmation and configured phases |
| World Boss | Gold | Dedicated challenge control with confirmation and multiple phases |

The initial roster is Slime, Goblin, Wolf, Skeleton, Orc; Goblin Warrior, Dire Wolf, Skeleton Knight, Orc Berserker; Ogre, Dark Knight, Wraith; Ancient Guardian, Blood Knight; Dragon Lord, Demon Sovereign; and Primordial Entity. No enemy from Elite through World Boss can enter ordinary spawning. Random elite scheduling is intentionally not implemented.

## Definition format

An enemy row in its classification JSON file can look like this:

```json
{
  "enemy_id": "marsh_stalker",
  "name": "Marsh Stalker",
  "description": "A patient hunter of the lowland reeds.",
  "classification": "uncommon",
  "max_hp": 900,
  "attack": 52,
  "physical_defense": 30,
  "magical_defense": 12,
  "exp_reward": 280,
  "attack_interval": 1.9,
  "abilities": ["heavy_strike"],
  "loot_table_id": "uncommon_drop",
  "difficulty_multiplier": 1.0,
  "scaling": {
    "enabled": true,
    "base_level": 1,
    "max_hp_per_level": 0.04,
    "attack_per_level": 0.03,
    "physical_defense_per_level": 0.02,
    "magical_defense_per_level": 0.01,
    "exp_per_level": 0.02
  }
}
```

`image_asset` is an optional asset reference field. The current project has no enemy image rendering path, so definitions do not download or require images. Add the row to the matching classification JSON file; no combat formula or CombatManager edit is needed.

## Scaling

Scaling is centralized in `EnemyDefinition.scaled_attributes(level)` and always uses immutable base values:

```text
level_delta = max(0, requested_level - base_level)
scaled_attribute = base_attribute × classification_multiplier × enemy_multiplier × (1 + per_level_rate × level_delta)
scaled_EXP = round(base_EXP × classification_multiplier × enemy_multiplier × (1 + exp_per_level × level_delta))
```

Maximum HP, Attack, both defenses, and EXP have independent non-negative rates. Each classification has a configurable multiplier (currently 1.0); an enemy can also define its own multiplier. With scaling disabled, the level component is 1.0 while configured difficulty multipliers still apply. The five original Common enemies keep scaling disabled to preserve their Update 2 behavior; the new classifications have level scaling enabled by configuration. The player’s current level is the requested enemy level. Every calculation starts from definition data, never from an earlier `Enemy` instance, and rejects non-finite results rather than persisting an invalid enemy.

## Enemy abilities

Abilities live once in `enemy_abilities.json`; enemy rows refer to ability IDs. Each definition includes an ID, name, description, type, trigger, cooldown, optional duration/HP threshold, and parameters. Runtime cooldowns are local to a single encounter and reset on retreat, defeat, replacement, or player death.

- **Heavy Strike** multiplies an enemy’s normal physical attack and then uses the normal player defense calculation.
- **Enrage** activates once at or below its HP threshold and multiplies Attack. A zero duration means it lasts until the encounter ends.
- **Defensive Stance** multiplies enemy Physical Defense for its configured duration. Player damage continues through the normal damage calculator.
- **Regeneration** restores a configured fraction and/or fixed amount of maximum HP, subject to its threshold and cooldown.
- **Piercing Strike** multiplies physical attack and applies a configured portion of player Physical Defense. It retains at least 5% of defense.

No player skills, enemy MP spells, or poison/burning/paralysis/freezing effects are part of this update.

## Boss phases

Boss rows have an ordered `boss_phases` array. The opening phase must start at `hp_threshold: 1.0`; subsequent thresholds must descend. As HP reaches each threshold, `BossManager` advances each phase once in order. A single hit may cross multiple thresholds; the manager emits each transition once.

Each phase can configure an attack multiplier, attack-interval multiplier, physical and magical defense multipliers, descriptive text, and the subset of ability IDs available in that phase. Effective Attack and defense start from the enemy’s level-scaled attributes; phase and temporary ability multipliers are applied to those values. Attack interval is the base interval multiplied by the active phase interval multiplier. Boss rewards use the same enemy defeat path but `BossManager.claim_defeat` prevents a second reward claim.

## Loot table format and probability

Enemies may name a table in `loot_tables.json`. Entries define a string reward ID, independent drop chance from 0 to 1, minimum/maximum quantity, optional guaranteed status, and roll count. Optional `max_drops` limits successful entries but cannot suppress configured guaranteed rolls.

Each non-guaranteed entry is rolled independently for each configured roll. A roll succeeds when the injected random value is less than `drop_chance`; quantity is then selected inclusively between minimum and maximum. Repeated IDs with the same currency type are combined. `currency_type: "gold"` marks a Gold reward entry, while an omitted currency type preserves the existing item-like drop shape. A currency and item entry may share a reward ID without being combined. Tables use injectable random sources for repeatable tests.

Non-currency drop IDs are data results written to the combat event and feedback log. They are not added to an inventory. The existing defeat roll is passed to Update 4's RewardManager, which credits currency entries once through EconomyManager; it does not perform a second roll. Equipment and inventory behavior remain future work.

## Persistence

Enemy definitions remain in `RPG/data/`; active enemies, HP, scaling snapshots, effects, cooldowns, phase timers, and loot rolls are transient. Save schema 6 persists aggregate combat statistics and the GameState-owned economy. Older version 5 and earlier saves retain existing character and combat data and receive an empty economy.
