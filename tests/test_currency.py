import pytest
from dataclasses import FrozenInstanceError

from RPG.systems.economy.currency import (
    MAX_CURRENCY_VALUE,
    CurrencyAccount,
    EconomyState,
    format_currency,
    normalize_currency,
    validate_currency_amount,
)


def test_gold_defaults_and_formatting():
    account = EconomyState().gold
    assert account == CurrencyAccount(0, 0, 0)
    assert format_currency(123456) == "123,456 G"
    assert normalize_currency(" Gold ") == "gold"


@pytest.mark.parametrize("amount", [-1, 0, 1.5, True, "2", MAX_CURRENCY_VALUE + 1])
def test_invalid_currency_amounts_are_rejected(amount):
    with pytest.raises(ValueError):
        validate_currency_amount(amount)


def test_safe_integer_boundary_and_unknown_currency():
    assert validate_currency_amount(MAX_CURRENCY_VALUE) == MAX_CURRENCY_VALUE
    assert validate_currency_amount(0, allow_zero=True) == 0
    with pytest.raises(ValueError, match="Unsupported currency"):
        normalize_currency("gems")
    with pytest.raises(ValueError, match="safe integer"):
        CurrencyAccount(balance=MAX_CURRENCY_VALUE + 1)


def test_currency_account_values_are_immutable_outside_economy_manager():
    account = EconomyState().gold
    with pytest.raises(FrozenInstanceError):
        account.balance = 10


def test_economy_state_round_trips_with_zero_defaults():
    payload = {"accounts": {"gold": {"balance": 42, "total_earned": 50, "total_spent": 8}}}
    restored = EconomyState.from_dict(payload)
    assert restored.gold.to_dict() == payload["accounts"]["gold"]
    assert restored.transactions == []
    assert restored.total_successful_purchases == 0
