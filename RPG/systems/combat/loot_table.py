"""Validated loot table definitions and deterministic, structured drop rolls."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Any, Mapping, Protocol


class LootRandomSource(Protocol):
    def random(self) -> float: ...
    def randint(self, a: int, b: int) -> int: ...


class LootTableError(ValueError):
    """Raised for missing or malformed loot table data."""


@dataclass(frozen=True)
class LootEntry:
    reward_id: str
    drop_chance: float
    min_quantity: int = 1
    max_quantity: int = 1
    guaranteed: bool = False
    rolls: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.reward_id, str) or not self.reward_id.strip():
            raise ValueError("Loot entries require a reward ID.")
        if (
            isinstance(self.drop_chance, bool)
            or not isinstance(self.drop_chance, (int, float))
            or not isfinite(self.drop_chance)
            or not 0 <= self.drop_chance <= 1
        ):
            raise ValueError(f"Loot chance for '{self.reward_id}' must be between zero and one.")
        if isinstance(self.min_quantity, bool) or not isinstance(self.min_quantity, int) or self.min_quantity < 1:
            raise ValueError(f"Minimum quantity for '{self.reward_id}' must be a positive whole number.")
        if isinstance(self.max_quantity, bool) or not isinstance(self.max_quantity, int) or self.max_quantity < self.min_quantity:
            raise ValueError(f"Maximum quantity for '{self.reward_id}' must be at least its minimum quantity.")
        if isinstance(self.rolls, bool) or not isinstance(self.rolls, int) or self.rolls < 1:
            raise ValueError(f"Roll count for '{self.reward_id}' must be a positive whole number.")
        if not isinstance(self.guaranteed, bool):
            raise ValueError(f"Guaranteed flag for '{self.reward_id}' must be a boolean.")


@dataclass(frozen=True)
class LootDrop:
    reward_id: str
    quantity: int
    guaranteed: bool = False


@dataclass(frozen=True)
class LootTable:
    table_id: str
    entries: tuple[LootEntry, ...]
    max_drops: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.table_id, str) or not self.table_id.strip():
            raise ValueError("Loot tables require an ID.")
        object.__setattr__(self, "entries", tuple(self.entries))
        if any(not isinstance(entry, LootEntry) for entry in self.entries):
            raise ValueError(f"Loot table '{self.table_id}' contains an invalid entry.")
        if self.max_drops is not None:
            if isinstance(self.max_drops, bool) or not isinstance(self.max_drops, int) or self.max_drops < 0:
                raise ValueError("Loot max_drops must be a non-negative whole number or null.")
            guaranteed_rolls = sum(entry.rolls for entry in self.entries if entry.guaranteed)
            if self.max_drops < guaranteed_rolls:
                raise ValueError("Loot max_drops cannot suppress configured guaranteed drops.")

    def roll(self, rng: LootRandomSource | None = None) -> tuple[LootDrop, ...]:
        source = rng or random.Random()
        result: list[LootDrop] = []
        successes = 0
        entries = sorted(self.entries, key=lambda entry: not entry.guaranteed)
        for entry in entries:
            for _ in range(entry.rolls):
                if self.max_drops is not None and successes >= self.max_drops:
                    break
                if entry.guaranteed or source.random() < float(entry.drop_chance):
                    quantity = source.randint(entry.min_quantity, entry.max_quantity)
                    result.append(LootDrop(entry.reward_id, quantity, entry.guaranteed))
                    successes += 1

        combined: dict[str, LootDrop] = {}
        for drop in result:
            current = combined.get(drop.reward_id)
            if current is None:
                combined[drop.reward_id] = drop
            else:
                combined[drop.reward_id] = LootDrop(
                    reward_id=drop.reward_id,
                    quantity=current.quantity + drop.quantity,
                    guaranteed=current.guaranteed or drop.guaranteed,
                )
        return tuple(combined.values())


class LootTableDatabase:
    def __init__(self, tables: tuple[LootTable, ...] | list[LootTable]) -> None:
        if any(not isinstance(table, LootTable) for table in tables):
            raise LootTableError("Loot table database contains an invalid table definition.")
        self._tables = {table.table_id.casefold(): table for table in tables}
        if len(self._tables) != len(tables):
            raise LootTableError("Duplicate loot table IDs were found.")

    @classmethod
    def load(cls, path: str | Path) -> "LootTableDatabase":
        source = Path(path)
        if not source.is_file():
            raise LootTableError(f"Loot table file is missing: {source}")
        try:
            data = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise LootTableError(f"Could not load loot tables from '{source}': {exc}") from exc
        try:
            tables_data = data["loot_tables"] if isinstance(data, dict) else data
            if not isinstance(tables_data, list):
                raise ValueError("root must be a list or contain a 'loot_tables' list")
            tables = [cls._parse_table(item) for item in tables_data]
            return cls(tables)
        except (KeyError, TypeError, ValueError) as exc:
            raise LootTableError(f"Malformed loot table file '{source}': {exc}") from exc

    @classmethod
    def load_default(cls) -> "LootTableDatabase":
        data_directory = Path(__file__).resolve().parents[2] / "data"
        return cls.load(data_directory / "loot_tables.json")

    @classmethod
    def from_tables(cls, tables: list[LootTable] | tuple[LootTable, ...]) -> "LootTableDatabase":
        return cls(tables)

    def get_by_id(self, table_id: str) -> LootTable:
        try:
            return self._tables[table_id.casefold()]
        except (AttributeError, KeyError) as exc:
            raise LootTableError(f"Unknown loot table: {table_id}") from exc

    def roll(self, table_id: str | None, rng: LootRandomSource | None = None) -> tuple[LootDrop, ...]:
        if table_id is None:
            return ()
        return self.get_by_id(table_id).roll(rng)

    def has(self, table_id: str) -> bool:
        return isinstance(table_id, str) and table_id.casefold() in self._tables

    @property
    def table_ids(self) -> frozenset[str]:
        return frozenset(self._tables)

    @staticmethod
    def _parse_table(data: Any) -> LootTable:
        if not isinstance(data, Mapping):
            raise ValueError("each loot table must be an object")
        entries_data = data.get("entries", [])
        if not isinstance(entries_data, list):
            raise ValueError("loot table entries must be a list")
        entries = tuple(
            LootEntry(
                reward_id=entry["reward_id"],
                drop_chance=entry.get("drop_chance", 0.0),
                min_quantity=entry.get("min_quantity", 1),
                max_quantity=entry.get("max_quantity", 1),
                guaranteed=entry.get("guaranteed", False),
                rolls=entry.get("rolls", 1),
            )
            for entry in entries_data
        )
        return LootTable(
            table_id=data["table_id"],
            entries=entries,
            max_drops=data.get("max_drops"),
        )
