# Architecture notes

The application is organized around the existing character rules and a shared `GameState`.

- `core/player.py` owns character progression, base stat allocation, class selection, and title state.
- `core/leveling.py` calculates level EXP requirements and stat point rewards.
- `core/progression_config.py` contains race bonus profiles, class definitions, and title milestones.
- `core/stat_calculator.py` derives primary and advanced attributes from base stats and passive bonuses. It does not import UI code.
- `core/race.py` retains the race database, rarity rates, race rolling, and pity behavior; `Race.bonus_profile` selects a passive profile.
- `data/` stores the enemy roster, abilities, and loot table definitions. `systems/combat/` loads that content and owns scaling, abilities, boss phases, physical damage, encounter state, and persistent combat-stat updates independently of CustomTkinter.
- `managers/` owns save serialization and settings validation. Save schema version 5 reads version 4, version 3, version 2, version 1, and raw Player data.
- `ui/components/progression_panels.py` provides race passive, class selection, and title panels. The existing stat allocation and race/potential panels remain in use.
- `ui/pages/combat.py` offers classification filtering and explicit Elite/Boss controls, then adapts CombatManager to CustomTkinter's non-blocking `after` event loop. A single cancellable timer services enemy attacks, HP regeneration, and Common respawns.
- `tests/` covers the game rules, combat, and persistence without opening a window.

See [PROGRESSION.md](PROGRESSION.md) for character formulas and migrations, [COMBAT.md](COMBAT.md) for encounter flow, and [ENEMIES.md](ENEMIES.md) for data configuration and enemy mechanics.

Equipment, functional inventory, skills, idle progression, offline rewards, world exploration, dungeons, summoning, and ascension are future features. Loot drop IDs are structured combat results and are not stored in an inventory.
