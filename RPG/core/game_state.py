"""The shared, serializable state for one active game."""

from __future__ import annotations

from typing import Any, Mapping
from uuid import uuid4

from .game_config import SAVE_SCHEMA_VERSION, normalize_game_settings
from .player import Player


class GameState:
    """Owns the active character, preferences, and save metadata.

    ``player`` remains as a compatibility name for the existing character
    model. ``character`` refers to that exact same object.
    """

    SAVE_VERSION = SAVE_SCHEMA_VERSION

    def __init__(
        self,
        player: Player | None = None,
        game_settings: Mapping[str, Any] | None = None,
        save_id: str | None = None,
        created_at: str | None = None,
        last_saved: str | None = None,
    ) -> None:
        self.player = player if player is not None else Player()
        self.game_settings = normalize_game_settings(dict(game_settings or {}))
        self.save_id = save_id or uuid4().hex
        self.created_at = created_at
        self.last_saved = last_saved
        self.loaded_from_legacy = False

    @property
    def character(self) -> Player:
        """The active character; an alias that never creates another copy."""
        return self.player

    @property
    def current_save_id(self) -> str:
        return self.save_id

    @property
    def last_saved_at(self) -> str | None:
        return self.last_saved

    def to_dict(self) -> dict[str, Any]:
        return {
            "save_version": self.SAVE_VERSION,
            "character": self.character.to_dict(),
            "game_settings": dict(self.game_settings),
            "metadata": {
                "save_id": self.save_id,
                "created_at": self.created_at,
                "last_saved": self.last_saved,
            },
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "GameState":
        if not isinstance(data, Mapping):
            raise ValueError("Save data must be a JSON object.")

        try:
            version = int(data.get("save_version", 1))
        except (TypeError, ValueError) as exc:
            raise ValueError("Save version must be an integer.") from exc
        if version > cls.SAVE_VERSION:
            raise ValueError(
                f"Save version {version} is newer than this application supports "
                f"(version {cls.SAVE_VERSION})."
            )

        if "character" in data:
            character_data = data["character"]
        elif "player" in data:
            # Compatibility with the existing version 1 RPG saves.
            character_data = data["player"]
        else:
            # Also accept the earlier raw Player JSON shape.
            character_data = data
        if not isinstance(character_data, Mapping):
            raise ValueError("Save does not contain valid character data.")

        character = Player()
        character.from_dict(dict(character_data))

        metadata = data.get("metadata", {})
        if not isinstance(metadata, Mapping):
            metadata = {}
        state = cls(
            player=character,
            game_settings=data.get("game_settings", {}),
            save_id=metadata.get("save_id"),
            created_at=metadata.get("created_at"),
            last_saved=metadata.get("last_saved"),
        )
        state.loaded_from_legacy = version < cls.SAVE_VERSION or "character" not in data
        return state

    def load_from_dict(self, data: Mapping[str, Any]) -> None:
        """Restore this state object in place for existing UI references."""
        loaded = self.from_dict(data)
        self.player = loaded.player
        self.game_settings = loaded.game_settings
        self.save_id = loaded.save_id
        self.created_at = loaded.created_at
        self.last_saved = loaded.last_saved
        self.loaded_from_legacy = loaded.loaded_from_legacy
