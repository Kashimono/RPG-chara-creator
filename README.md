# RPG: World of Ascension

A dark fantasy clicker RPG made with Python and CustomTkinter. The application has a persistent sidebar, a shared `GameState`, versioned JSON saves, and game rules that do not depend on the UI.

## Implemented features

- Roll a race from seven rarity tiers, review drop rates and pity counters, and accept the race.
- Roll and accept stat potentials for HP, MP, Attack, Agility, and Stamina; allocate earned stat points within each accepted potential.
- Gain EXP and automatically level up, including multiple levels and EXP overflow. Each level awards 10 stat points.
- View an EXP progress bar and use clearly marked direct level/EXP controls for progression testing.
- Apply race passive profiles and choose a class with passive bonuses. Race and class effects are calculated from base attributes and are not written back into them.
- Unlock and equip cosmetic titles at level milestones.
- View Physical Defense, Magical Defense, Critical Chance, Critical Damage, Attack Speed, HP Regeneration, and MP Regeneration.
- Fight a data-driven roster of 17 Common, Uncommon, Rare, Elite, Boss, and World Boss enemies with click attacks, enemy abilities, boss phases, structured loot rolls, HP regeneration, retreat, recovery, and EXP rewards.
- Earn configurable guaranteed Gold rewards and optional Gold loot drops through the existing defeat and loot-table flow. Spend Gold on five potential-aware training options, with transaction history saved in GameState.
- Collect enemy materials, trophies, miscellaneous items, and equipment in a 50-slot inventory. Stack or split materials, inspect and filter items, and claim drops that could not fit in the bag.
- Equip weapons, armor, and accessories across nine configured slots. Rarity scales configured bonuses and sale value; gear bonuses flow through the shared character calculator and combat.
- Unlock and upgrade 17 data-defined physical, magical, defensive, and support skills; equip up to six skills, spend MP, and use cooldowns, buffs, healing, damage-over-time, stun, slow, weakening, and defense-break effects.
- Sell eligible inventory items through recorded EconomyManager transactions. Equipped gear cannot be sold; equipment swaps and item sales validate before committing.
- Browse enemies by classification, start optional Elite encounters, and explicitly confirm Boss and World Boss challenges. The Common rotation retains the original five enemies and timed respawns.
- Save and load characters with version 8 JSON. Version 7 and older saves preserve existing character, combat, economy, inventory, and equipment data, initialize MP safely, and receive configured starter skills.
- Use Dashboard, Character, Combat, Skills, Economy, Inventory, and Settings navigation. Character and Inventory show equipped items and effective gear bonuses.
- Copy the existing character profile to the clipboard and choose an appearance preference.

Progression rules are documented in [`RPG/docs/PROGRESSION.md`](RPG/docs/PROGRESSION.md). Combat formulas and encounter behavior are documented in [`RPG/docs/COMBAT.md`](RPG/docs/COMBAT.md), skill definitions and effects in [`RPG/docs/SKILLS.md`](RPG/docs/SKILLS.md), economy design and tuning in [`RPG/docs/ECONOMY.md`](RPG/docs/ECONOMY.md), with enemy data, scaling, abilities, phases, and loot in [`RPG/docs/ENEMIES.md`](RPG/docs/ENEMIES.md).

Equipment enhancement, crafting, idle or offline combat, world maps, dungeons, summoning, and ascension remain future features. Full skill trees, specialization, and skill evolution are not implemented.

## Project structure

```text
RPG/
  core/                 Character, race, stats, EXP, passives, and calculations
  data/                 Enemy roster, enemy abilities, loot tables, and economy tuning
  managers/             Save and settings services
  systems/combat/       Enemy database, abilities, boss phases, loot, damage, effects, and encounters
  systems/skills/       Skill database, calculations, progression, and loadouts
  systems/economy/      Currency state, transactions, reward calculation, and training shop
  systems/inventory/    Item data, bag capacity and stacking, loot collection, and sales
  systems/equipment/    Equipment slots, validation, persistence, and bonus calculation
  data/items/           Item definitions, rarity tuning, capacity, and slot configuration
  ui/
    main_window.py      Application shell and shared actions
    navigation.py       Persistent sidebar
    components/         Reusable progression panels
    pages/              Dashboard, Character, Combat, Skills, Economy, Inventory, Settings
    *_panel.py          Race, potential, level, allocation, and advanced stats
  saves/                JSON character saves
  docs/                 Architecture, progression, combat, economy, and inventory documentation
tests/                  Logic and persistence tests
requirements-dev.txt    Test tooling plus app requirements
run_rpg.bat             Windows launcher for an existing .venv
```

Race definitions and potential ranges remain in `RPG/core/race.py`; the established stat allocation and multiplier rules remain in `RPG/core/stat.py` and `RPG/core/multiplier.py`.

## Requirements

- Python 3.10 or newer
- Tkinter (usually included with Python; some Linux distributions package it separately)
- CustomTkinter from [`RPG/requirements.txt`](RPG/requirements.txt)
- Pytest for the test suite (included in `requirements-dev.txt`)

## Install and launch

From the project root, create a virtual environment and install the application requirements:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r RPG\requirements.txt
.\.venv\Scripts\python.exe -m RPG
```

The Windows launch command after setup is:

```powershell
.\.venv\Scripts\python.exe -m RPG
```

On macOS or Linux, use `.venv/bin/python -m pip install -r RPG/requirements.txt` and `.venv/bin/python -m RPG`.

## Run tests

Install the development requirements and run the suite from the project root:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```

The game rules, progression, combat, titles, attribute calculations, and save migration tests do not open the GUI.
