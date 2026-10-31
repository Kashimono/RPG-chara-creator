# Architecture notes

The application is organized around the existing character rules and a shared `GameState`.

- `core/player.py` owns character progression, base stat allocation, class selection, and title state.
- `core/leveling.py` calculates level EXP requirements and stat point rewards.
- `core/progression_config.py` contains race bonus profiles, class definitions, and title milestones.
- `core/stat_calculator.py` derives primary and advanced attributes from base stats and passive bonuses. It does not import UI code.
- `core/race.py` retains the race database, rarity rates, race rolling, and pity behavior; `Race.bonus_profile` selects a passive profile.
- `managers/` owns save serialization and settings validation. Save schema version 3 reads version 2, version 1, and raw Player data.
- `ui/components/progression_panels.py` provides race passive, class selection, and title panels. The existing stat allocation and race/potential panels remain in use.
- `tests/` covers the game rules and persistence without opening a window.

See [PROGRESSION.md](PROGRESSION.md) for formulas, balance values, class bonuses, titles, and migrations.

Combat, enemy damage, equipment, inventory behavior, skills, idle progression, offline rewards, summoning, and ascension are future features.
