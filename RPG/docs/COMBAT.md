# Combat System

Combat uses the existing `CombatManager`, `Enemy` encounter model, and one physical `DamageCalculator`. Gameplay rules stay independent of CustomTkinter. The Combat page sends player actions to the manager and services its clock through one cancellable 100 ms Tk callback.

## Encounter flow

- The default encounter button starts the next Common enemy in this order: Slime, Goblin, Wolf, Skeleton, Orc.
- Common enemies respawn after two seconds and receive a new encounter UUID.
- Uncommon and Rare enemies are explicitly selected and fought as one-off encounters.
- Elites use the dedicated Start Elite action. The current update does not schedule random elite spawns.
- Bosses and World Bosses use the dedicated Challenge Boss action. The page asks for confirmation; they never enter the Common rotation.
- Only one encounter may run at a time. Retreat, player defeat, encounter defeat, save load, and application close stop temporary encounter effects and timers.

## Damage and timing

All player attributes come from `Player.calculated_attributes`, preserving race and class passives. The shared physical calculation remains in `damage_calculator.py`:

```text
Player varied base = Effective Attack × uniform(0.90, 1.10)
Player raw damage = varied base × (Critical Damage if critical, otherwise 1)
Enemy varied base = Effective Enemy Attack × uniform(0.90, 1.10)
Damage reduction = Defense / (Defense + 1000)
Final damage = max(1, raw damage × (1 - Damage reduction)) for positive raw damage
Attack cooldown = max(0.05 seconds, 1 / Attack Speed)
```

Player attacks use enemy Physical Defense. Enemy attacks use player Physical Defense. Piercing Strike supplies a configured effectiveness fraction to this same mitigation formula; the configuration rejects fractions below 5%. Magical Defense remains available to definitions and the UI, but no magical attack is implemented.

Enemy attacks use the configured interval. Player HP regeneration remains capped to 0.25 seconds per UI tick so a stalled app does not award offline healing. At zero HP, combat actions and scheduling stop. Recovery restores 50% of maximum HP. Existing click attacks, critical hits, player HP, retreat, recovery, and common respawning remain in place.

## Enemy content and mechanics

See [Enemy Database and Encounters](ENEMIES.md) for data files, classifications, scaling formulas, abilities, phases, and loot configuration. The short version:

- Static enemy and ability content lives in `RPG/data/` and is validated before the Combat page can use it.
- `EnemyDatabase` handles definition loading and lookup. `Enemy` holds one uniquely identified encounter. `CombatManager` controls encounter timing, rewards, and state.
- `EnemyAbilityRuntime` owns temporary cooldowns/effects. `BossManager` advances definition-driven phases and claims boss rewards once.
- `LootTableDatabase` returns structured `LootDrop` values attached to the defeat `CombatEvent`. Drop IDs are feedback data only; no inventory, equipment, Gold, or economy is implemented in this update.

## EXP and statistics

Defeat rewards use `GameState.award_combat_exp`, which delegates to `Player.gain_exp`. The existing progression system remains the authority for overflow and multi-level rewards.

Persistent combat statistics include damage dealt/received, enemies defeated, critical hits, attacks, EXP, Elite defeats, Boss defeats, and World Boss defeats. Defeat rewards are guarded per enemy instance so repeated callbacks cannot award EXP, statistics, or loot twice.

## Save compatibility

Save schema 5 keeps enemy definitions and all encounter state out of character files. It adds three long-term counters to the existing combat statistics object: Elite, Boss, and World Boss defeats. A version 4 save keeps its current HP and previous combat totals, while the new counters default to zero. Version 3, version 2, version 1, and raw legacy saves retain the earlier defaults. Loading never resumes an enemy, ability cooldown, boss phase timer, or callback; the next session begins safely at `IDLE` unless saved player HP is zero.

The generic `SaveManager` continues serializing `GameState.to_dict()` and requires no enemy-specific serialization path.
