import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from .game_state import GameState

SAVE_FOLDER = Path(__file__).resolve().parents[1] / "saves"
SAVE_FOLDER.mkdir(parents=True, exist_ok=True)


class SaveManager:
    """Handles saving and loading game state JSON files."""

    @staticmethod
    def get_save_path(filename: str = "autosave.json") -> Path:
        return SAVE_FOLDER / filename

    @staticmethod
    def normalize_filename(name: Optional[str]) -> str:
        if not name or not name.strip():
            return datetime.now().strftime("save_%Y%m%d_%H%M%S.json")

        sanitized = name.strip().replace(" ", "_")
        sanitized = "".join(ch for ch in sanitized if ch.isalnum() or ch in "-_.")
        sanitized = sanitized or datetime.now().strftime("save_%Y%m%d_%H%M%S.json")
        if not sanitized.lower().endswith(".json"):
            sanitized += ".json"
        return sanitized

    @staticmethod
    def list_save_files() -> List[str]:
        return sorted(path.name for path in SAVE_FOLDER.glob("*.json"))

    @staticmethod
    def get_save_timestamp(filename: str) -> str:
        path = SaveManager.get_save_path(filename)
        if not path.exists():
            return "Unknown"

        modified = datetime.fromtimestamp(path.stat().st_mtime)
        return modified.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def save(state: GameState, filename: str = "autosave.json") -> Path:
        path = SaveManager.get_save_path(filename)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(state.to_dict(), handle, indent=2)
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
            raise FileNotFoundError(f"Save file '{filename}' not found.")

        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Unable to load save file '{filename}'.") from exc

        return GameState.from_dict(data)
