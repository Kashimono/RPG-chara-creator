import pytest

from RPG.core.game_state import GameState
from RPG.core.leveling import LevelSystem
from RPG.core.player import Player
from RPG.core.progression_config import (
    DEFAULT_RACE_BONUSES,
    RACE_BONUS_PROFILES,
    TITLE_DEFINITIONS,
    PassiveBonuses,
    get_race_bonuses,
)
from RPG.core.race import Race
from RPG.core.stat_calculator import calculate_attributes


def make_created_player(monkeypatch, race: Race | None = None) -> Player:
    player = Player()
    player.set_preview_race(race or Race("Test Common", "Common", 1, 1_000, 10))
    player.accept_race()
    monkeypatch.setattr("RPG.core.stat.random.randint", lambda low, high: high)
    for stat_name in player.stats:
        player.roll_stat_potential(stat_name)
        player.accept_stat_potential(stat_name)
    return player


def set_primary_points(player: Player) -> None:
    for name, value in {
        "HP": 200,
        "MP": 300,
        "Attack": 400,
        "Agility": 500,
        "Stamina": 600,
    }.items():
        player.stats[name].current = value
    player._sync_stat_race_context()


def test_exp_requirement_formula_scales_at_low_medium_and_high_levels() -> None:
    assert LevelSystem.required_exp(1) == 100
    assert LevelSystem.required_exp(2) == 283
    assert LevelSystem.required_exp(50) == 35_356
    assert LevelSystem.required_exp(1_000) == 3_162_278
    assert LevelSystem.required_exp(50) > LevelSystem.required_exp(2)


def test_gain_exp_level_up_and_stat_point_reward(monkeypatch) -> None:
    player = make_created_player(monkeypatch)

    assert player.gain_exp(99) == 0
    assert (player.level, player.exp, player.stat_points) == (1, 99, 0)
    assert player.gain_exp(1) == 1
    assert (player.level, player.exp, player.stat_points) == (2, 0, 10)
    assert player.exp_to_next == LevelSystem.required_exp(2)


def test_gain_exp_handles_multiple_levels_and_preserves_overflow(monkeypatch) -> None:
    player = make_created_player(monkeypatch)
    award = LevelSystem.required_exp(1) + LevelSystem.required_exp(2) + 17

    levels_gained = player.gain_exp(award)

    assert levels_gained == 2
    assert player.level == 3
    assert player.exp == 17
    assert player.exp_to_next == LevelSystem.required_exp(3)
    assert player.stat_points == 20


def test_exp_leveling_preserves_allocated_attributes(monkeypatch) -> None:
    player = make_created_player(monkeypatch)
    player.level_up(2)
    assert player.allocate_points("HP", 12)

    player.gain_exp(LevelSystem.required_exp(player.level))

    assert player.level == 4
    assert player.stats["HP"].current == 12
    assert player.stat_points == 18


def test_high_level_requirement_and_direct_level_utility_remain_available(monkeypatch) -> None:
    player = make_created_player(monkeypatch)

    player.level_up(999)

    assert player.level == 1_000
    assert player.stat_points == 9_990
    assert player.exp_to_next == LevelSystem.required_exp(1_000)


def test_exp_gain_requires_a_created_character_and_positive_integer() -> None:
    with pytest.raises(ValueError, match="Create a character"):
        Player().gain_exp(1)
    player = Player()
    player.character_created = True
    with pytest.raises(ValueError, match="positive whole number"):
        player.gain_exp(0)
    with pytest.raises(ValueError, match="positive whole number"):
        player.gain_exp(1.5)


def test_race_bonuses_apply_to_calculated_attributes_once(monkeypatch) -> None:
    player = make_created_player(monkeypatch, Race("Rare Test", "Rare", 1, 1_000, 50))
    set_primary_points(player)
    base_stamina = player.stats["Stamina"].effective_value

    first = player.calculated_attributes
    second = player.calculated_attributes

    assert first.stamina == pytest.approx(base_stamina * 1.05)
    assert first.physical_defense > 0
    assert second == first
    assert player.stats["Stamina"].effective_value == base_stamina
    assert player.stats["Stamina"].current == 600


def test_different_race_profiles_provide_different_passives() -> None:
    uncommon = get_race_bonuses(Race("Quick Race", "Uncommon", 1, 10, bonus_profile="uncommon"))
    arcane = get_race_bonuses(Race("Arcane Race", "Rare", 1, 10, bonus_profile="arcane"))

    assert uncommon.agility_multiplier == 1.04
    assert arcane.mp_multiplier == 1.08
    assert uncommon != arcane


def test_unknown_race_bonus_profile_uses_neutral_defaults() -> None:
    race = Race("Unconfigured", "Primordial", 1, 10, bonus_profile="not-configured")

    assert get_race_bonuses(race) == DEFAULT_RACE_BONUSES


def test_race_passives_activate_only_after_race_acceptance(monkeypatch) -> None:
    player = Player()
    player.set_preview_race(Race("Rare Preview", "Rare", 1, 1_000, 50))
    set_primary_points(player)
    preview_attributes = player.calculated_attributes

    player.accept_race()

    accepted_attributes = player.calculated_attributes
    assert preview_attributes.stamina < accepted_attributes.stamina


def test_stat_allocation_recalculates_derived_attributes(monkeypatch) -> None:
    player = make_created_player(monkeypatch)
    player.level_up(2)
    before = player.calculated_attributes

    assert player.allocate_points("Stamina", 10)
    after = player.calculated_attributes

    assert after.stamina > before.stamina
    assert after.physical_defense > before.physical_defense
    assert after.hp_regeneration > before.hp_regeneration


def test_class_selection_and_class_bonus_recalculation(monkeypatch) -> None:
    player = make_created_player(monkeypatch)
    set_primary_points(player)
    baseline = player.calculated_attributes

    player.select_class("Mage")
    mage = player.calculated_attributes

    assert player.class_id == "mage"
    assert mage.mp == pytest.approx(baseline.mp * 1.15)
    assert mage.magical_defense > baseline.magical_defense
    player.select_class(None)
    assert player.calculated_attributes == baseline


def test_race_and_class_multipliers_combine_without_mutating_base_stats(monkeypatch) -> None:
    player = make_created_player(monkeypatch, Race("Arcane Test", "Epic", 1, 1_000, 100))
    set_primary_points(player)
    base_mp = player.stats["MP"].effective_value
    player.select_class("mage")

    attributes = player.calculated_attributes

    assert attributes.mp == pytest.approx(base_mp * 1.07 * 1.15)
    assert player.stats["MP"].current == 300


def test_each_advanced_formula_uses_its_documented_primary_attributes() -> None:
    player = Player()
    set_primary_points(player)
    attributes = player.calculated_attributes

    expected_critical_chance = min(
        0.75,
        0.05 + 0.45 * attributes.agility / (attributes.agility + 1_000),
    )
    expected_critical_damage = min(
        4.0,
        max(1.5, 1.5 + attributes.attack / (attributes.attack + 5_000)),
    )
    expected_attack_speed = min(
        4.0,
        max(1.0, 1 + 2 * attributes.agility / (attributes.agility + 1_000)),
    )

    assert attributes.physical_defense == pytest.approx(attributes.stamina * 0.60 + attributes.attack * 0.05)
    assert attributes.magical_defense == pytest.approx(attributes.mp * 0.45 + attributes.stamina * 0.15)
    assert attributes.critical_chance == pytest.approx(expected_critical_chance, abs=0.0001)
    assert attributes.critical_damage == pytest.approx(expected_critical_damage, abs=0.0001)
    assert attributes.attack_speed == pytest.approx(expected_attack_speed, abs=0.0001)
    assert attributes.hp_regeneration == pytest.approx(attributes.stamina * 0.01 + attributes.hp * 0.002)
    assert attributes.mp_regeneration == pytest.approx(attributes.mp * 0.01 + attributes.stamina * 0.001)


def test_invalid_class_and_class_persistence(monkeypatch) -> None:
    player = make_created_player(monkeypatch)
    player.select_class("Assassin")
    state = GameState(player=player)

    with pytest.raises(ValueError, match="Unknown character class"):
        player.select_class("Paladin")
    restored = GameState.from_dict(state.to_dict())

    assert restored.character.class_id == "assassin"
    assert restored.character.calculated_attributes == player.calculated_attributes


def test_derived_attribute_defaults_and_caps(monkeypatch) -> None:
    player = Player()
    defaults = player.calculated_attributes
    assert defaults.physical_defense == 0
    assert defaults.magical_defense == 0
    assert defaults.critical_chance == 0.05
    assert defaults.critical_damage == 1.5
    assert defaults.attack_speed == 1.0
    assert defaults.hp_regeneration == 0
    assert defaults.mp_regeneration == 0

    extreme = PassiveBonuses(
        critical_chance_bonus=2.0,
        critical_damage_multiplier=10.0,
        attack_speed_multiplier=10.0,
    )
    monkeypatch.setitem(RACE_BONUS_PROFILES, "common", extreme)
    capped = calculate_attributes(player.stats, Race("Extreme", "Common", 1, 10))
    assert capped.critical_chance == 0.75
    assert capped.critical_damage == 4.0
    assert capped.attack_speed == 4.0


def test_titles_unlock_by_level_and_only_unlocked_titles_can_be_equipped(monkeypatch) -> None:
    player = make_created_player(monkeypatch)
    assert player.unlocked_titles == ["novice"]
    with pytest.raises(ValueError, match="only equip a title"):
        player.equip_title("apprentice")

    player.level_up(9)
    assert "apprentice" in player.unlocked_titles
    player.equip_title("Apprentice")
    assert player.equipped_title_name == "Apprentice"
    with pytest.raises(ValueError, match="only equip a title"):
        player.equip_title("made-up")


def test_all_title_milestones_unlock_and_persist(monkeypatch) -> None:
    player = make_created_player(monkeypatch)
    player.level_up(499)
    assert set(player.unlocked_titles) == set(TITLE_DEFINITIONS)
    player.equip_title("ascendant")

    restored = GameState.from_dict(GameState(player=player).to_dict()).character
    assert restored.equipped_title == "ascendant"
    assert set(restored.unlocked_titles) == set(TITLE_DEFINITIONS)
