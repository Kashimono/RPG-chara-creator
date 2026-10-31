from RPG.core.character import format_character_profile
from RPG.core.game_state import GameState
from RPG.core.player import Player
from RPG.core.race import Race
from RPG.core.stat import Stat


def make_created_player(monkeypatch) -> Player:
    player = Player()
    player.set_preview_race(Race("Test Race", "Rare", 10, 100, 50))
    player.accept_race()
    monkeypatch.setattr("RPG.core.stat.random.randint", lambda low, high: high)
    for name in player.stats:
        player.roll_stat_potential(name)
        player.accept_stat_potential(name)
    return player


def test_leveling_awards_ten_points_per_level(monkeypatch) -> None:
    player = make_created_player(monkeypatch)

    player.level_up(10)

    assert player.level == 11
    assert player.stat_points == 100


def test_stat_allocation_spends_points_and_respects_potential(monkeypatch) -> None:
    player = make_created_player(monkeypatch)
    player.level_up(2)

    assert player.allocate_points("HP", 15)
    assert player.stats["HP"].current == 15
    assert player.stat_points == 5
    assert not player.allocate_points("HP", 6)
    assert not player.allocate_points("MP", 0)


def test_advanced_stat_multiplier_and_effective_value() -> None:
    stat = Stat("Attack")
    stat.set_race_multiplier_cap(3)
    stat.current = 50

    assert stat.multiplier == 1.5
    assert stat.effective_value == 75.0


def test_clipboard_profile_contains_active_character_data(monkeypatch) -> None:
    player = make_created_player(monkeypatch)
    player.character_name = "Arin"
    player.level_up(2)
    player.allocate_points("HP", 7)

    text = format_character_profile(player)

    assert "Race: Test Race" in text
    assert "Rarity: Rare" in text
    assert "Level: 3" in text
    assert "HP: 7" in text
    assert "MP: 0" in text
    assert "Stamina: 0" in text


def test_game_state_exposes_one_shared_active_character(monkeypatch) -> None:
    player = make_created_player(monkeypatch)
    state = GameState(player=player)
    snapshot = state.to_dict()
    restored = GameState.from_dict(snapshot)

    assert state.character is state.player
    assert restored.character is restored.player
    assert restored.character.get_character_profile() == player.get_character_profile()
    assert restored.game_settings == state.game_settings
