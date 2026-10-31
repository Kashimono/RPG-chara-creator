# RPG: World of Ascension

A dark fantasy desktop RPG character builder made with Python and CustomTkinter. This foundation update adds a persistent navigation shell, shared game state, versioned saves, and settings while preserving the existing character creation and stat progression rules.

## Current features

- Roll from seven race rarities, review drop rates and pity counters, and accept a race.
- Roll up to ten potential values for each stat: HP, MP, Attack, Agility, and Stamina. Accept one value per stat to finish character creation.
- Level up by 1, 10, or 1,000 levels. Each level grants 10 stat points.
- Allocate stat points with a shared amount input or per-stat +1 shortcut, capped by remaining points and accepted potential.
- View stat multipliers and effective values in Advanced Stats.
- Copy character race, rarity, level, and current stat values to the clipboard.
- Save, load, overwrite with confirmation, and delete JSON saves. Existing version 1 and raw character saves can be loaded and migrate only when explicitly saved.
- Navigate between Dashboard, Character, Combat, Inventory, and Settings. Combat and Inventory are planned feature placeholders.
- Choose Dark, Light, or System appearance and store a sound preference placeholder.

No combat, enemies, inventory items, equipment, idle systems, or sound playback is implemented in this foundation update.

## Project structure

```text
RPG/
  core/                 Character, race, stats, progression, and game state
    character.py        Pure character profile formatting
    game_config.py      Save schema and default preferences
    game_state.py       Active character, settings, and save metadata
    player.py           Existing character creation and stat rules
  managers/             Save and settings services
  ui/
    main_window.py      Application shell and shared actions
    navigation.py       Persistent sidebar navigation
    pages/              Dashboard, Character, Combat, Inventory, Settings
    *_panel.py          Existing character builder panels
  saves/                JSON character saves
  docs/                 Additional project notes
tests/                  Logic and persistence tests
requirements-dev.txt    Test tooling plus application requirements
run_rpg.bat             Windows launcher for an existing .venv
```

Race definitions and balance constants remain in `RPG/core/race.py` and `RPG/constants.py`; there is no separate data directory because the current race database is code-defined.

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

The exact Windows launch command after setup is:

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

The game rules, clipboard profile formatting, save migration, and settings tests do not open a GUI.

## Architecture overview

`GameState` owns one active `Player` character, game settings, a save identifier, and timestamps. Every page reads that shared state; the Character page reuses the existing race, potential, level, allocation, and advanced stat panels. The core modules do not depend on CustomTkinter.

`SaveManager` writes version 2 JSON files with `character`, `game_settings`, and `metadata` fields. It reads the existing version 1 `{ "save_version": 1, "player": ... }` format and raw Player JSON. Loading a legacy file converts it in memory; the original file is only replaced after the user confirms a save overwrite.
