# Architecture notes

The application is organized around a small set of existing game rules and a shared `GameState`.

- `core/` contains the `Player` character model, race database and pity counters, stat potential and multiplier calculations, leveling, clipboard profile formatting, and serializable game state. These modules have no CustomTkinter dependency.
- `managers/` contains JSON persistence and preference validation. `core/save_manager.py` remains as an import shim for existing callers.
- `ui/` contains the persistent navigation shell, pages, and the original character builder panels. Pages reference the same active state; the Character page keeps its existing panels alive while the user navigates.
- `saves/` holds versioned JSON saves. Version 1 `{ "player": ... }` and raw Player save shapes are read in memory and are not rewritten until an explicit save.
- `tests/` exercises character rules, clipboard output, game state, preferences, and persistence without opening the UI.

The current version intentionally does not include combat, inventory behavior, equipment, skills, idle progression, or sound playback.
