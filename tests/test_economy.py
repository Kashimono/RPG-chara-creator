from datetime import datetime, timezone

import pytest

from RPG.core.game_state import GameState
from RPG.systems.economy.currency import MAX_CURRENCY_VALUE
from RPG.systems.economy.economy_config import EconomyConfig
from RPG.systems.economy.economy_manager import EconomyManager, EconomyTransactionError
from RPG.systems.economy.transaction import TransactionDirection, TransactionType


def test_credit_spend_lifetime_counters_and_transaction_metadata():
    ids = iter(("earn-1", "spend-1"))
    timestamp = datetime(2026, 1, 2, tzinfo=timezone.utc)
    state = GameState()
    manager = EconomyManager(state, clock=lambda: timestamp, id_factory=lambda: next(ids))

    earned = manager.credit_currency(120, source="Slime", description="Defeat reward", transaction_type=TransactionType.ENEMY_REWARD)
    spent = manager.spend_currency(35, source="Testing", description="Adjustment", transaction_type=TransactionType.ADMIN_ADJUSTMENT)

    assert manager.get_balance() == 85
    assert manager.get_account().total_earned == 120
    assert manager.get_account().total_spent == 35
    assert earned.transaction_id == "earn-1"
    assert earned.timestamp == "2026-01-02T00:00:00+00:00"
    assert earned.direction is TransactionDirection.EARNED
    assert spent.direction is TransactionDirection.SPENT
    assert [tx.transaction_id for tx in state.economy.transactions] == ["earn-1", "spend-1"]


def test_failed_or_invalid_operations_do_not_partially_change_wallet():
    state = GameState()
    manager = EconomyManager(state)
    manager.credit_currency(30)
    before = state.economy.to_dict()

    with pytest.raises(EconomyTransactionError, match="Insufficient"):
        manager.spend_currency(31, source="shop", description="too expensive")
    with pytest.raises(EconomyTransactionError, match="positive"):
        manager.credit_currency(-1)
    with pytest.raises(EconomyTransactionError, match="whole numbers"):
        manager.credit_currency(2.5)

    assert state.economy.to_dict() == before


def test_wallet_cap_rejects_overflow_atomically():
    state = GameState()
    manager = EconomyManager(state)
    manager.credit_currency(MAX_CURRENCY_VALUE)
    with pytest.raises(EconomyTransactionError, match="exceed"):
        manager.credit_currency(1)
    assert manager.get_balance() == MAX_CURRENCY_VALUE
    assert manager.get_account().total_earned == MAX_CURRENCY_VALUE
    assert len(state.economy.transactions) == 1


def test_purchase_debit_is_committed_only_after_character_callback_succeeds():
    state = GameState()
    manager = EconomyManager(state)
    manager.credit_currency(100)
    before = state.economy.to_dict()
    result = manager.purchase_gold(
        50,
        source="training",
        description="training test",
        apply_purchase=lambda: False,
    )
    assert result is None
    assert state.economy.to_dict() == before


def test_transaction_history_is_chronological_and_bounded():
    config = EconomyConfig(enemy_gold_rewards={}, transaction_history_limit=2)
    state = GameState()
    counter = iter(range(3))
    manager = EconomyManager(state, config=config, id_factory=lambda: str(next(counter)))
    manager.credit_currency(1, source="one", description="one")
    manager.credit_currency(1, source="two", description="two")
    manager.credit_currency(1, source="three", description="three")
    assert [tx.transaction_id for tx in state.economy.transactions] == ["1", "2"]
    assert state.economy.gold.total_earned == 3


def test_duplicate_transaction_ids_are_rejected_before_mutation():
    state = GameState()
    manager = EconomyManager(state, id_factory=lambda: "same")
    manager.credit_currency(5)
    with pytest.raises(EconomyTransactionError, match="Duplicate transaction ID"):
        manager.credit_currency(7)
    assert manager.get_balance() == 5


def test_transactions_sort_by_actual_time_and_preserve_equal_time_order():
    timestamps = iter((
        datetime(2026, 1, 2, 1, 0, tzinfo=timezone.utc).astimezone(timezone.utc),
        datetime(2026, 1, 2, 0, 30, tzinfo=timezone.utc),
    ))
    ids = iter(("later", "earlier"))
    state = GameState()
    manager = EconomyManager(state, clock=lambda: next(timestamps), id_factory=lambda: next(ids))
    manager.credit_currency(1, description="later")
    manager.credit_currency(1, description="earlier")
    assert [tx.description for tx in state.economy.transactions] == ["earlier", "later"]
