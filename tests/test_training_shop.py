from RPG.core.game_state import GameState
from RPG.core.player import Player
from RPG.systems.economy.economy_config import EconomyConfig, TrainingDefinition
from RPG.systems.economy.economy_manager import EconomyManager
from RPG.systems.economy.training_shop import TrainingShop


def make_shop_state(*, current=1, potential=5, balance=100):
    player = Player()
    player.character_created = True
    player.stat_points = 7
    attack = player.stats["Attack"]
    attack.accepted = True
    attack.potential = potential
    attack.current = current
    state = GameState(player=player)
    config = EconomyConfig(
        enemy_gold_rewards={},
        trainings=(TrainingDefinition("strength", "Strength Training", "Improve Attack.", "Attack", 100, 1),),
    )
    manager = EconomyManager(state, config=config)
    if balance:
        manager.credit_currency(balance)
    return state, config, manager, TrainingShop(state, manager, config)


def test_successful_training_deducts_gold_and_uses_player_allocation_validation():
    state, _config, _manager, shop = make_shop_state()
    before_attributes = state.character.calculated_attributes
    result = shop.purchase("strength")

    assert result.success
    assert state.character.stats["Attack"].current == 2
    assert state.character.stat_points == 7
    assert state.character.calculated_attributes.attack > before_attributes.attack
    assert state.economy.gold.balance == 0
    assert state.economy.gold.total_spent == 100
    assert state.economy.total_successful_purchases == 1
    assert state.economy.transactions[-1].transaction_type.value == "training_purchase"


def test_full_potential_rejects_purchase_without_deducting_gold():
    state, _config, _manager, shop = make_shop_state(current=5, potential=5)
    before = state.economy.to_dict()
    result = shop.purchase("strength")
    assert not result.success
    assert "potential" in result.message
    assert state.character.stats["Attack"].current == 5
    assert state.economy.to_dict() == before


def test_insufficient_gold_and_unknown_training_are_rejected_cleanly():
    state, config, manager, shop = make_shop_state(balance=20)
    before = state.economy.to_dict()
    result = shop.purchase("strength")
    assert not result.success and "Insufficient Gold" in result.message
    assert state.economy.to_dict() == before
    assert not shop.purchase("not-a-training").success


def test_training_requires_character_creation_and_accepted_potential():
    state, config, manager, shop = make_shop_state()
    state.character.character_created = False
    assert not shop.can_purchase("strength").success
    state.character.character_created = True
    state.character.stats["Attack"].accepted = False
    assert "potential" in shop.can_purchase("strength").message
