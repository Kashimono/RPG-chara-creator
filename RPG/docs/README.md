# Architecture notes

The application is organized around the existing character rules and a shared `GameState`.

- `core/player.py` owns character progression, base stat allocation, class selection, and title state.
- `core/leveling.py` calculates level EXP requirements and stat point rewards.
- `core/progression_config.py` contains race bonus profiles, class definitions, and title milestones.
- `core/stat_calculator.py` derives primary and advanced attributes from base stats, passive bonuses, and transient equipment bonuses. It does not import UI code.
- `core/race.py` retains the race database, rarity rates, race rolling, and pity behavior; `Race.bonus_profile` selects a passive profile.
- `data/` stores the enemy roster, skills, abilities, and loot table definitions. `systems/combat/` loads that content and owns scaling, abilities, boss phases, damage, temporary status updates, encounter state, and persistent combat-stat updates independently of CustomTkinter.
- `systems/skills/` validates skill definitions and owns player unlocks, upgrades, loadouts, calculations, and transient cooldowns. CombatManager remains responsible for skill activation.
- `systems/economy/` keeps currency and reward rules independent of the UI. `EconomyManager` owns validated wallet changes, `RewardCalculator` applies configured multipliers, `RewardManager` joins defeat rewards to the existing EXP and loot lifecycle, and `TrainingShop` calls the existing Player stat allocation method.
- `systems/inventory/` owns data-driven item definitions, bag capacity and stacking, drop collection, unclaimed loot, and sales.
- `systems/equipment/` owns equipment slots, compatibility and level checks, atomic replacement, and rarity-scaled bonus aggregation.
- `managers/` owns save serialization and settings validation. Save schema version 8 reads version 7 and all earlier formats, defaulting inventory, equipment, current MP, and configured starter skills for older saves.
- `ui/components/progression_panels.py` provides race passive, class selection, and title panels. The existing stat allocation and race/potential panels remain in use.
- `ui/pages/combat.py` offers classification filtering and explicit Elite/Boss controls, then adapts CombatManager to CustomTkinter's non-blocking `after` event loop. A single cancellable timer services enemy attacks, HP regeneration, and Common respawns. Defeat item drops enter GameState inventory; overflow remains claimable.
- `ui/pages/skills.py` displays skill requirements, levels, Gold costs, and the six-slot loadout. The Combat page hotbar updates on the existing combat timer.
- The Character and Inventory pages read equipment from GameState. UI actions call the managers and do not edit item or equipment collections directly.
- `tests/` covers the game rules, combat, and persistence without opening a window.

See [PROGRESSION.md](PROGRESSION.md) for character formulas and migrations, [COMBAT.md](COMBAT.md) for encounter flow, [ECONOMY.md](ECONOMY.md) for currency and reward behavior, and [ENEMIES.md](ENEMIES.md) for data configuration and enemy mechanics.

See [INVENTORY.md](INVENTORY.md) for item data, slot configuration, stat integration, loot collection, and sales, and [SKILLS.md](SKILLS.md) for skills. Equipment enhancement, crafting, idle progression, offline rewards, world exploration, dungeons, summoning, ascension, full skill trees, specialization, and skill evolution remain future features.
