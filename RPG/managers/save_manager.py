"""Versioned JSON persistence for the active game state."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from ..core.game_state import GameState

SAVE_FOLDER = Path(__file__).resolve().parents[1] / "saves"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class SaveManager:
    """Creates, loads, overwrites, lists, and deletes local JSON saves."""

    @staticmethod
    def get_save_path(filename: str = "autosave.json") -> Path:
        if not isinstance(filename, str) or not filename.strip():
            raise ValueError("A save filename is required.")
        filename = filename.strip()
        if Path(filename).name != filename or "/" in filename or "\\" in filename:
            raise ValueError("Save files must be stored directly in the saves folder.")
        if not filename.lower().endswith(".json"):
            filename += ".json"
        return SAVE_FOLDER / filename

    @staticmethod
    def normalize_filename(name: str | None) -> str:
        if not name or not name.strip():
            name = datetime.now().strftime("save_%Y%m%d_%H%M%S")
        sanitized = name.strip().replace(" ", "_")
        sanitized = "".join(ch for ch in sanitized if ch.isalnum() or ch in "-_.")
        sanitized = sanitized.strip(".") or datetime.now().strftime("save_%Y%m%d_%H%M%S")
        if not sanitized.lower().endswith(".json"):
            sanitized += ".json"
        return sanitized

    @staticmethod
    def list_save_files() -> list[str]:
        if not SAVE_FOLDER.exists():
            return []
        return sorted(path.name for path in SAVE_FOLDER.glob("*.json") if path.is_file())

    @staticmethod
    def get_save_timestamp(filename: str) -> str:
        path = SaveManager.get_save_path(filename)
        if not path.exists():
            return "Unknown"
        modified = datetime.fromtimestamp(path.stat().st_mtime)
        return modified.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def save(state: GameState, filename: str = "autosave.json", *, overwrite: bool = False) -> Path:
        path = SaveManager.get_save_path(filename)
        if path.exists() and not overwrite:
            raise FileExistsError(f"Save '{path.name}' already exists. Confirm before overwriting it.")

        SAVE_FOLDER.mkdir(parents=True, exist_ok=True)
        now = _utc_now()
        save_id = state.save_id or uuid4().hex
        created_at = state.created_at or now
        payload_data = state.to_dict()
        payload_data["metadata"]["save_id"] = save_id
        payload_data["metadata"]["created_at"] = created_at
        payload_data["metadata"]["last_saved"] = now
        payload = json.dumps(payload_data, indent=2, ensure_ascii=False)
        temporary_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
        try:
            temporary_path.write_text(payload, encoding="utf-8")
            os.replace(temporary_path, path)
            state.save_id = save_id
            state.created_at = created_at
            state.last_saved = now
        finally:
            if temporary_path.exists():
                temporary_path.unlink()
        return path

    @staticmethod
    def delete(filename: str) -> None:
        path = SaveManager.get_save_path(filename)
        if path.exists():
            path.unlink()

    @staticmethod
    def load(filename: str = "autosave.json") -> GameState:
        path = SaveManager.get_save_path(filename)
        if not path.exists():
            raise FileNotFoundError(f"Save file '{path.name}' not found.")
        try:
            with path.open("r", encoding="utf-8") as handle:
                data: Any = json.load(handle)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"Unable to read save file '{path.name}'. It may be corrupted.") from exc
        try:
            return GameState.from_dict(data)
        except (AttributeError, TypeError, ValueError, KeyError, OverflowError) as exc:
            raise ValueError(f"Save file '{path.name}' contains invalid game data: {exc}") from exc
