# Combat system

Update 2 adds active, click-driven physical combat. The rules live under `RPG/systems/combat/` and do not depend on CustomTkinter. `CombatManager` owns one transient encounter, while `GameState` remains the source of truth for character HP, EXP, and persistent combat statistics.

## Modules and state

- `enemy.py` defines immutable `EnemyDefinition` templates and mutable, uniquely identified `Enemy` encounter instances.
- `combat_config.py` contains damage variation, mitigation, minimum damage, cooldown floor, recovery, respawn timing, and the initial five enemy definitions.
- `damage_calculator.py` applies physical damage variation, critical hits, and defense mitigation using injected randomness.
- `combat_stats.py` stores aggregate combat statistics.
- `combat_manager.py` starts and ends encounters, processes attacks and rewards, and advances timed combat effects using caller-supplied time.
- `ui/pages/combat.py` polls the manager through a single Tk `after` callback. It keeps combat active while another page is shown, cancels scheduling when combat ends or the page is destroyed, and does not use threads or blocking waits.

The manager states are `IDLE`, `ACTIVE`, `ENEMY_DEFEATED`, `PLAYER_DEFEATED`, and `RECOVERING`. An encounter is not serialized. A new application session starts with no enemy or combat timer. A character saved at zero HP opens in the defeat recovery state; the player can recover before starting another encounter.

## Initial enemies

| Enemy | HP | Attack | Physical Defense | Attack interval | EXP |
| --- | ---: | ---: | ---: | ---: | ---: |
| Slime | 100 | 5 | 0 | 2.0 s | 10 |
| Goblin | 250 | 12 | 5 | 1.8 s | 25 |
| Wolf | 400 | 18 | 8 | 1.5 s | 40 |
| Skeleton | 750 | 30 | 15 | 2.0 s | 75 |
| Orc | 1,500 | 50 | 30 | 2.5 s | 150 |

Combat starts with the selected enemy. After a defeat, the next enemy in the configured sequence spawns after two seconds. The defeated enemy is processed once, so it awards EXP and increments statistics only once. The next encounter has a fresh ID and full HP.

Newly created characters currently have no allocated HP or Attack and begin with zero stat points. Use the existing Character page EXP or direct-level testing control once to earn stat points, then allocate HP and Attack before the first encounter. Combat itself awards normal progression EXP after that setup.

## Damage and cooldown formulas

All player attributes come from `Player.calculated_attributes`, preserving Update 1's race/class passives and effective-stat multipliers.

```text
Player varied base = Effective Attack × uniform(0.90, 1.10)
Player raw damage = varied base × (Critical Damage if critical, otherwise 1)
Enemy varied base = Enemy Attack × uniform(0.90, 1.10)
Damage reduction = Defense / (Defense + 1000)
Final damage = max(1, raw damage × (1 - Damage reduction)) for positive raw damage
Attack cooldown = max(0.05 seconds, 1 / Attack Speed)
```

The critical roll uses the existing calculated Critical Chance, capped at the Update 1 limit. Critical damage uses the existing calculated Critical Damage multiplier. Player attacks are mitigated by the enemy's Physical Defense; enemy physical attacks are mitigated by the player's Physical Defense. Zero attack remains zero damage, and the minimum applies only to positive attacks. Magical Defense is displayed but unused until magical attacks are in scope.

Random sources and time are injectable into combat calculations and manager methods, so tests do not sleep or depend on real random outcomes.

## HP, recovery, and timing

Maximum HP is recalculated from the existing effective HP attribute. Current HP is separate from base stats, clamps to `0..maximum HP`, and persists on the character. A `null` saved current HP is the full-health sentinel used for new characters until they take damage; old saves without the field also begin at full health. When maximum HP rises, current HP remains unchanged after damage; if maximum HP falls below current HP, current HP is clamped down.

While combat is active, HP regeneration uses the existing `HP Regeneration/sec` value times elapsed active time and never exceeds maximum HP. Regeneration catch-up is capped to 0.25 seconds per UI tick so a stalled or suspended app does not grant offline healing. Enemies attack on their configured interval. Retreat ends the encounter without a penalty. At zero HP, combat scheduling stops and actions are blocked. Recovery restores 50% of maximum HP, clears the defeated encounter, and returns the manager to `IDLE`.

The UI services both regeneration and enemy attacks through one 100 ms `after` loop. The manager itself has no scheduler, sleeps, or threads. Retreat, defeat, game replacement, and application close stop or cancel the UI timer.

## EXP and statistics

Enemy defeat calls `GameState.award_combat_exp`, which delegates to the existing `Player.gain_exp`. Existing overflow, multi-level progression, and 10 stat points per level therefore remain authoritative. Level and stat changes are visible immediately through the shared GameState.

Combat statistics persist in the version 4 save envelope: total damage dealt, total damage received, enemies defeated, critical hits, attacks performed, and EXP earned in combat. Damage totals count actual HP removed, capped at the target's remaining HP. Temporary enemy identity, combat state, and timer deadlines are not saved.

## Save migration

Version 4 adds `character.current_hp` and top-level `combat_statistics`. Version 3, version 2, version 1, and raw legacy saves default missing HP to full health and missing statistics to zero. Existing saves are only rewritten when the user explicitly saves. No active encounter is restored on load.

## Scope

This update includes ordinary physical attacks only. It does not include bosses, enemy phases, abilities, equipment, loot, Gold, automated player attacks, idle or offline combat, or magical attacks.
