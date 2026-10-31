import json

import pytest

from RPG.core.game_state import GameState
from RPG.core.player import Player
from RPG.core.race import Race
from RPG.managers import save_manager
from RPG.managers.save_manager import SaveManager
from RPG.managers.settings_manager import SettingsManager


@pytest.fixture
def saves_dir(tmp_path, monkeypatch):
    directory = tmp_path / "saves"
    monkeypatch.setattr(save_manager, "SAVE_FOLDER", directory)
    return directory


def test_new_saves_use_versioned_envelope_and_round_trip(saves_dir) -> None:
    state = GameState(game_settings={"theme": "Light", "sound_enabled": True})
    state.player.set_preview_race(Race("Test Race", "Rare", 10, 20, 50))
    state.player.accept_race()
    path = SaveManager.save(state, "test.json")

    payload = json.loads(path.read_text(encoding="utf-8"))
    loaded = SaveManager.load("test.json")

    assert payload["save_version"] == GameState.SAVE_VERSION
    assert "character" in payload and "player" not in payload
    assert payload["game_settings"] == {"theme": "Light", "sound_enabled": True}
    assert payload["metadata"]["save_id"] == state.current_save_id
    assert state.created_at and state.last_saved
    assert loaded.character.race_name == "Test Race"
    assert loaded.game_settings["theme"] == "Light"
    assert loaded.current_save_id == state.current_save_id


def test_existing_version_one_player_save_loads_without_migration_write(saves_dir) -> None:
    player = Player()
    player.set_preview_race(Race("Old Race", "Epic", 5_000, 100_000, 100))
    player.accept_race()
    old_player_data = player.to_dict()
    old_player_data.pop("character_name")
    path = saves_dir / "old.json"
    path.parent.mkdir(parents=True)
    original = {"save_version": 1, "player": old_player_data}
    path.write_text(json.dumps(original), encoding="utf-8")

    loaded = SaveManager.load("old.json")

    assert loaded.loaded_from_legacy
    assert loaded.character.character_name == "Adventurer"
    assert loaded.character.race_name == "Old Race"
    assert json.loads(path.read_text(encoding="utf-8")) == original

    SaveManager.save(loaded, "old.json", overwrite=True)
    migrated = json.loads(path.read_text(encoding="utf-8"))
    assert migrated["save_version"] == GameState.SAVE_VERSION
    assert migrated["character"]["race_name"] == "Old Race"


def test_raw_legacy_player_shape_is_accepted() -> None:
    restored = GameState.from_dict({"level": 4, "stats": {}, "character_created": True})

    assert restored.loaded_from_legacy
    assert restored.character.level == 4
    assert restored.character.character_created


def test_overwrite_requires_explicit_confirmation(saves_dir) -> None:
    state = GameState()
    SaveManager.save(state, "slot.json")

    with pytest.raises(FileExistsError):
        SaveManager.save(GameState(), "slot.json")

    SaveManager.save(state, "slot.json", overwrite=True)
    assert SaveManager.list_save_files() == ["slot.json"]


def test_corrupt_saves_fail_with_readable_error(saves_dir) -> None:
    saves_dir.mkdir(parents=True)
    (saves_dir / "broken.json").write_text("{not json", encoding="utf-8")

    with pytest.raises(ValueError, match="corrupted"):
        SaveManager.load("broken.json")


def test_save_manager_rejects_paths_outside_saves_folder() -> None:
    with pytest.raises(ValueError):
        SaveManager.get_save_path("..\\outside.json")


def test_settings_manager_validates_and_resets_preferences() -> None:
    changed = SettingsManager.set_setting(SettingsManager.defaults(), "theme", "System")

    assert changed["theme"] == "System"
    assert SettingsManager.reset() == {"theme": "Dark", "sound_enabled": False}
    with pytest.raises(ValueError):
        SettingsManager.set_setting(changed, "theme", "sepia")
