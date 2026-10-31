import json

from RPG.core.game_state import GameState
from RPG.managers import save_manager
from RPG.managers.save_manager import SaveManager
from RPG.systems.economy.economy_manager import EconomyManager


def test_economy_balance_and_history_round_trip_through_save_manager(tmp_path, monkeypatch):
    monkeypatch.setattr(save_manager, "SAVE_FOLDER", tmp_path / "saves")
    state = GameState()
    manager = EconomyManager(state)
    manager.credit_currency(250, source="Goblin", description="Defeat reward")
    manager.spend_currency(100, source="training", description="Training test")
    SaveManager.save(state, "economy.json")

    restored = SaveManager.load("economy.json")
    assert restored.economy.gold.balance == 150
    assert restored.economy.gold.total_earned == 250
    assert restored.economy.gold.total_spent == 100
    assert restored.economy.total_successful_purchases == 0
    assert [tx.description for tx in restored.economy.transactions] == ["Defeat reward", "Training test"]


def test_version_five_and_older_saves_default_economy_without_resetting_character():
    original = GameState().to_dict()
    original["character"]["character_name"] = "Legacy Hero"
    original.pop("economy")
    for version in (1, 2, 3, 4, 5):
        payload = dict(original)
        payload["save_version"] = version
        loaded = GameState.from_dict(payload)
        assert loaded.character.character_name == "Legacy Hero"
        assert loaded.economy.gold.balance == 0
        assert loaded.economy.gold.total_earned == 0
        assert loaded.economy.gold.total_spent == 0
        assert loaded.economy.transactions == []
        assert loaded.loaded_from_legacy


def test_game_state_load_from_dict_replaces_economy_in_place():
    source = GameState()
    EconomyManager(source).credit_currency(77)
    target = GameState()
    target.load_from_dict(source.to_dict())
    assert target.economy.gold.balance == 77
    assert target.economy.transactions[0].amount == 77
    assert json.loads(json.dumps(target.to_dict()))["economy"]["accounts"]["gold"]["balance"] == 77
