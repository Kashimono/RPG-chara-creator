from typing import Any, Dict
from .player import Player


class GameState:
    """Holds the current runtime state and offers future persistence hooks."""

    SAVE_VERSION = 1

    def __init__(self) -> None:
        self.player = Player()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "save_version": self.SAVE_VERSION,
            "player": self.player.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GameState":
        state = cls()
        save_version = data.get("save_version", 1)
        if save_version != cls.SAVE_VERSION:
            # Future compatibility can be implemented here.
            pass
        state.player.from_dict(data.get("player", {}))
        return state

    def load_from_dict(self, data: Dict[str, Any]) -> None:
        loaded = self.from_dict(data)
        self.player = loaded.player
