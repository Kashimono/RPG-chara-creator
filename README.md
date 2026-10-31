# RPG Character Builder

A desktop RPG character builder made with Python and CustomTkinter. Roll a race, set potentials for five stats, then level up and spend stat points. Characters can be saved and loaded as JSON files.

## Features

- Roll from seven race rarities, each with its own potential range and maximum stat multiplier.
- Review race drop rates and pity counters in the race panel. Accept a race to lock it in and unlock stat rolls.
- Roll up to 10 potential values for each stat: HP, MP, Attack, Agility, and Stamina. Accept one value per stat to finish character creation.
- Level up by 1, 10, or 1,000 levels. Each level grants 10 stat points.
- Allocate points to accepted stats with one shared amount input (default `1`) or the per-stat +1 shortcut. Amounts must be positive whole numbers; allocations are capped by the available stat points and each stat's remaining potential. View multipliers and effective values in Advanced Stats.
- Copy the active character's race, rarity, level, and current stat values to the system clipboard.
- Save, load, and manage character files from the app. Save files are stored in `RPG/saves/`.

## Requirements

- Python 3.10 or newer
- Tkinter (usually included with Python; on some Linux distributions it is a separate package)
- Dependencies listed in [`RPG/requirements.txt`](RPG/requirements.txt)

## Run

From the project root, create a virtual environment and install the dependency:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python -m pip install -r RPG\requirements.txt
.\.venv\Scripts\python -m RPG
```

macOS or Linux:

```bash
.venv/bin/python -m pip install -r RPG/requirements.txt
.venv/bin/python -m RPG
```

On Windows, after setting up `.venv`, you can also launch the app with `run_rpg.bat`.

## Getting started in the app

1. Choose **Roll Race** and review the race, potential range, and multiplier.
2. Choose **Accept Race** to lock the race in.
3. Roll and accept a potential for each of the five stats. You can reroll a stat before accepting it, up to its 10-roll limit.
4. Once all five potentials are accepted, use the level-up buttons to gain stat points. Set the shared **Amount** field, then press a stat's **Allocate** button; the amount is capped to your available points and that stat's remaining potential. Use **+** to allocate one point.
5. Use **Copy Character Stats** to copy the current profile and allocated stat values to the clipboard.
6. Use **Save Game** to create a named JSON save, or **Load Game** to open an existing save.

## Project layout

```text
RPG/
  core/       Character, race, stat, leveling, and save logic
  ui/         CustomTkinter panels and dialogs
  docs/       Additional project notes
  saves/      JSON character saves
  main.py     Application entry point
  __main__.py Enables `python -m RPG`
  requirements.txt
tests/        Automated tests
run_rpg.bat   Windows launcher for an existing .venv
```

To run the test suite, install `pytest` and run `python -m pytest` from the project root.
