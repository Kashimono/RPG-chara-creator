"""GameState-owned currency balances and economy persistence models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping

from .transaction import CurrencyTransaction, MAX_CURRENCY_VALUE

SUPPORTED_CURRENCIES = frozenset({"gold"})


def validate_currency_amount(amount: object, *, allow_zero: bool = False) -> int:
    if isinstance(amount, bool) or not isinstance(amount, int):
        raise ValueError("Currency amounts must be whole numbers.")
    if amount < 0 or (amount == 0 and not allow_zero):
        raise ValueError("Currency amounts must be positive." if not allow_zero else "Currency amounts cannot be negative.")
    if amount > MAX_CURRENCY_VALUE:
        raise ValueError("Currency amount exceeds the supported safe integer range.")
    return amount


def normalize_currency(currency_type: str) -> str:
    if not isinstance(currency_type, str):
        raise ValueError("Currency type must be a string.")
    normalized = currency_type.strip().casefold()
    if normalized not in SUPPORTED_CURRENCIES:
        raise ValueError(f"Unsupported currency: {currency_type}")
    return normalized


def format_currency(amount: int, currency_type: str = "gold") -> str:
    value = validate_currency_amount(amount, allow_zero=True)
    currency = normalize_currency(currency_type)
    symbol = "G" if currency == "gold" else currency.upper()
    return f"{value:,} {symbol}"


@dataclass(frozen=True)
class CurrencyAccount:
    balance: int = 0
    total_earned: int = 0
    total_spent: int = 0

    def __post_init__(self) -> None:
        validate_currency_amount(self.balance, allow_zero=True)
        validate_currency_amount(self.total_earned, allow_zero=True)
        validate_currency_amount(self.total_spent, allow_zero=True)

    def to_dict(self) -> dict[str, int]:
        return {
            "balance": self.balance,
            "total_earned": self.total_earned,
            "total_spent": self.total_spent,
        }

    @classmethod
    def from_dict(cls, data: object) -> "CurrencyAccount":
        if not isinstance(data, Mapping):
            return cls()
        values: list[int] = []
        for key in ("balance", "total_earned", "total_spent"):
            raw = data.get(key, 0)
            if isinstance(raw, bool) or not isinstance(raw, int) or not 0 <= raw <= MAX_CURRENCY_VALUE:
                raw = 0
            values.append(raw)
        return cls(*values)


@dataclass
class EconomyState:
    """Persistent economy data owned by GameState, never by a UI page."""

    accounts: dict[str, CurrencyAccount] = field(default_factory=lambda: {"gold": CurrencyAccount()})
    transactions: list[CurrencyTransaction] = field(default_factory=list)
    total_successful_purchases: int = 0

    def __post_init__(self) -> None:
        normalized: dict[str, CurrencyAccount] = {}
        for currency, account in self.accounts.items():
            normalized[normalize_currency(currency)] = account if isinstance(account, CurrencyAccount) else CurrencyAccount.from_dict(account)
        normalized.setdefault("gold", CurrencyAccount())
        self.accounts = normalized
        unique_transactions: list[CurrencyTransaction] = []
        seen_ids: set[str] = set()
        for transaction in self.transactions:
            if isinstance(transaction, CurrencyTransaction) and transaction.transaction_id not in seen_ids:
                unique_transactions.append(transaction)
                seen_ids.add(transaction.transaction_id)
        unique_transactions.sort(key=lambda transaction: _transaction_time(transaction.timestamp))
        self.transactions = unique_transactions
        if (
            isinstance(self.total_successful_purchases, bool)
            or not isinstance(self.total_successful_purchases, int)
            or not 0 <= self.total_successful_purchases <= MAX_CURRENCY_VALUE
        ):
            self.total_successful_purchases = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "accounts": {currency: account.to_dict() for currency, account in self.accounts.items()},
            "transactions": [transaction.to_dict() for transaction in self.transactions],
            "total_successful_purchases": self.total_successful_purchases,
        }

    @classmethod
    def from_dict(cls, data: object) -> "EconomyState":
        if not isinstance(data, Mapping):
            return cls()
        raw_accounts = data.get("accounts", {})
        accounts: dict[str, CurrencyAccount] = {}
        if isinstance(raw_accounts, Mapping):
            for currency, raw_account in raw_accounts.items():
                try:
                    accounts[normalize_currency(currency)] = CurrencyAccount.from_dict(raw_account)
                except ValueError:
                    continue
        raw_transactions = data.get("transactions", [])
        transactions: list[CurrencyTransaction] = []
        if isinstance(raw_transactions, list):
            for item in raw_transactions:
                try:
                    raw_currency = item.get("currency_type", "gold") if isinstance(item, Mapping) else "gold"
                    normalize_currency(raw_currency)
                    transactions.append(CurrencyTransaction.from_dict(item))
                except (KeyError, TypeError, ValueError):
                    continue
        transactions.sort(key=lambda transaction: _transaction_time(transaction.timestamp))
        purchases = data.get("total_successful_purchases", 0)
        if isinstance(purchases, bool) or not isinstance(purchases, int) or not 0 <= purchases <= MAX_CURRENCY_VALUE:
            purchases = 0
        return cls(accounts=accounts, transactions=transactions, total_successful_purchases=purchases)

    @property
    def gold(self) -> CurrencyAccount:
        return self.accounts["gold"]

    def append_transactions(self, transactions: list[CurrencyTransaction], *, history_limit: int) -> None:
        self.transactions.extend(transactions)
        self.transactions.sort(key=lambda transaction: _transaction_time(transaction.timestamp))
        if history_limit >= 0 and len(self.transactions) > history_limit:
            if history_limit == 0:
                self.transactions.clear()
            else:
                del self.transactions[:-history_limit]

    def count_successful_purchases(self) -> int:
        return self.total_successful_purchases


def _transaction_time(value: str) -> datetime:
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


__all__ = [
    "CurrencyAccount",
    "EconomyState",
    "MAX_CURRENCY_VALUE",
    "SUPPORTED_CURRENCIES",
    "format_currency",
    "normalize_currency",
    "validate_currency_amount",
]
