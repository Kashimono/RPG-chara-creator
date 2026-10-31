"""Backward compatible import for the manager moved to ``RPG.managers``."""

from ..managers.save_manager import SAVE_FOLDER, SaveManager

__all__ = ["SAVE_FOLDER", "SaveManager"]
