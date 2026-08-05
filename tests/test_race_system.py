from RPG.core.player import Player
from RPG.core.race import Race


def test_player_can_preview_and_accept_a_race() -> None:
    player = Player()
    assert player.race is None
    assert not player.race_accepted

    race = Race("Rare", "Rare", 1_000, 20_000, 15.0)
    player.set_preview_race(race)
    assert player.race is race
    assert not player.race_accepted

    player.accept_race()
    assert player.race_accepted


def test_stat_rolls_use_the_accepted_race_range() -> None:
    player = Player()
    player.set_preview_race(Race("Legendary", "Legendary", 100_000, 1_000_000, 2.0))
    player.accept_race()

    roll_value = player.roll_stat_potential("HP")

    assert 100_000 <= roll_value <= 1_000_000


def test_player_save_round_trip_preserves_race_data() -> None:
    player = Player()
    player.set_preview_race(Race("Primordial", "Primordial", 10_000_000, 1_000_000_000, 0.02))
    player.accept_race()

    restored = Player()
    restored.from_dict(player.to_dict())

    assert restored.race_name == "Primordial"
    assert restored.race_rarity == "Primordial"
    assert restored.race_min_potential == 10_000_000
    assert restored.race_max_potential == 1_000_000_000
    assert restored.race_accepted is True
