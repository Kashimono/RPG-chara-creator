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
- Fight five ordinary enemies with click attacks, critical hits, enemy attacks, HP regeneration, retreat, recovery, timed respawns, and EXP rewards.
- Save and load characters with version 4 JSON. Version 3, version 2, version 1, and raw legacy saves receive defaults and are only migrated on an explicit save.
- Use Dashboard, Character, Combat, Inventory, and Settings navigation. Inventory remains a planned placeholder.
- Copy the existing character profile to the clipboard and choose an appearance preference.

Progression rules are documented in [`RPG/docs/PROGRESSION.md`](RPG/docs/PROGRESSION.md), and combat formulas and encounter behavior are documented in [`RPG/docs/COMBAT.md`](RPG/docs/COMBAT.md).

This update does not add enemy databases beyond the five ordinary enemies, bosses, skills, equipment, functional inventory, idle combat, offline rewards, summoning, or ascension.

## Project structure

```text
RPG/
  core/                 Character, race, stats, EXP, passives, and calculations
  managers/             Save and settings services
  systems/combat/       Enemy definitions, damage rules, and encounter manager
  ui/
    main_window.py      Application shell and shared actions
    navigation.py       Persistent sidebar
    components/         Reusable progression panels
    pages/              Dashboard, Character, Combat, Inventory, Settings
    *_panel.py          Race, potential, level, allocation, and advanced stats
  saves/                JSON character saves
  docs/                 Architecture and progression documentation
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
