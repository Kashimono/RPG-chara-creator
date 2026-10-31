# Character progression rules

Update 1 adds character progression inputs and derived values. The core rules live in `core/leveling.py`, `core/progression_config.py`, and `core/stat_calculator.py`; the UI only displays these results and calls the model methods.

## EXP and levels

For a character at level `L`, the EXP requirement to advance is:

```text
required_exp(L) = ceil(100 * max(1, L) ^ 1.5)
```

The base requirement (100) and growth rate (1.5) are centralized in `core/game_config.py`. Sample thresholds are level 1: 100 EXP, level 2: 283 EXP, level 50: 35,356 EXP, and level 1,000: 3,162,278 EXP.

EXP is the current level's progress. `Player.gain_exp(amount)` subtracts each reached threshold, increments the level, and continues until the remainder is below the next threshold. Every level grants 10 stat points. EXP beyond a threshold remains as progress toward the next level. The character builder also retains direct level controls, clearly marked as testing utilities; it does not represent gameplay EXP rewards.

## Race passives

Each `Race` has a `bonus_profile`. By default this is its rarity key, and specific races can select a named profile. The race itself and its accepted flag are saved; calculated bonuses are never added to base stat points. Bonuses apply at calculation time only after race acceptance.

| Default profile | Passive bonuses |
| --- | --- |
| Common | No bonuses |
| Uncommon | Agility x1.04, Attack x1.02 |
| Rare | Stamina x1.05, Physical Defense x1.08 |
| Epic | MP x1.07, Magical Defense x1.10, MP Regeneration x1.08 |
| Legendary | Attack x1.08, Physical Defense x1.06, Critical Damage x1.08 |
| Mythical | HP x1.08, MP x1.08, Agility x1.08, Critical Chance +2 percentage points |
| Primordial | Primary attributes and defenses x1.12, Critical Chance +3 points, Critical Damage and regeneration x1.10 |

Named profiles allow a race to specialize beyond its rarity default: Sylvara uses `verdant` (HP x1.04, Stamina x1.06, HP Regeneration x1.12); Aetherborne uses `arcane` (MP x1.08, Magical Defense x1.08, MP Regeneration x1.12); Wyrmkin uses `draconic` (Attack x1.10, Physical Defense x1.05, Critical Damage x1.05); Phoenix Herald uses `phoenix` (HP x1.10, Critical Chance +2 points, HP Regeneration x1.15); World-First Spirit uses `world_first` (primary attributes and defenses x1.15, Critical Chance +4 points, Critical Damage and regeneration x1.12).

The balance assumption is that common races remain neutral, bonuses grow gradually by rarity, and named races exchange broad bonuses for a narrower specialty. The passive values feed the calculated attributes used by the combat system; they remain separate from base stat points.

## Character classes

Classes are configured in `CLASS_DEFINITIONS`. All five are available from character creation (minimum level 0, no completed-character requirement), and leaving the class unselected is valid.

| Class | Specialization | Passive bonuses |
| --- | --- | --- |
| Warrior | Attack and Physical Defense | Attack x1.15, Physical Defense x1.15 |
| Mage | MP and Magical Defense | MP x1.15, Magical Defense x1.15, MP Regeneration x1.08 |
| Assassin | Agility and Critical Chance | Agility x1.15, Critical Chance +8 points, Attack Speed x1.08 |
| Guardian | HP and Defense | HP x1.18, Stamina x1.10, Physical Defense x1.10, Magical Defense x1.08 |
| Ranger | Agility and Attack | Agility x1.10, Attack x1.10, Attack Speed x1.05 |

Class IDs are saved on the character. Changing or clearing a class from the Character page requires confirmation. Class bonuses are recalculated from base attributes and do not stack into those base values.

## Advanced attribute formulas

The existing `Stat.effective_value` remains the primary input. It is calculated from allocated stat points and the existing milestone multiplier. Race and class primary multipliers are then applied once:

```text
effective HP/MP/Attack/Agility/Stamina = Stat.effective_value * race multiplier * class multiplier
Physical Defense = (Stamina * 0.60 + Attack * 0.05) * defense passives
Magical Defense = (MP * 0.45 + Stamina * 0.15) * defense passives
Critical Chance = clamp(0.05 + 0.45 * Agility / (Agility + 1000) + flat passives, 0, 0.75)
Critical Damage = clamp((1.5 + Attack / (Attack + 5000)) * passives, 1.5, 4.0)
Attack Speed = clamp((1 + 2 * Agility / (Agility + 1000)) * passives, 1.0, 4.0)
HP Regeneration/sec = (Stamina * 0.01 + HP * 0.002) * passives
MP Regeneration/sec = (MP * 0.01 + Stamina * 0.001) * passives
```

Defense and regeneration have a zero minimum. Critical chance, critical damage, and attack speed have the displayed caps. Critical damage starts at x1.5, and attack speed starts at 1 attack per second. The scaling constants keep chance and speed gains diminishing at high attributes. Ordinary physical combat consumes these values; see [`COMBAT.md`](COMBAT.md) for damage, cooldown, and regeneration behavior.

## Titles

Titles are cosmetic and provide no stats. `TITLE_DEFINITIONS` controls the starting title and level requirements:

| Title | Requirement |
| --- | --- |
| Novice | Starting title |
| Apprentice | Level 10 |
| Veteran | Level 50 |
| Elite | Level 100 |
| Master | Level 250 |
| Ascendant | Level 500 |

Unlocks are granted automatically whenever progression changes the level. Only an unlocked title can be equipped. The unlocked ID list and equipped title ID are saved.

## Save migration

Save schema version 5 retains the version 4 character and combat fields, including current HP and persistent combat statistics. It adds Elite, Boss, and World Boss defeat counters to those statistics. Version 4, version 3, version 2, version 1, and raw saves continue to load with sensible defaults. Derived attributes and the current level's EXP requirement are not serialized; they are recalculated from the saved level, stats, race, and class.

Version 3 and version 2 saves use the existing `character` envelope; version 1 saves use `player`; raw Player JSON is also accepted. Older saves default to full current HP, zero combat statistics, no class, the starting Novice title, and the race's default profile. Their old stored EXP threshold is ignored and recalculated. Loading performs this migration in memory; the source file changes only when the user explicitly saves and confirms overwriting it.
