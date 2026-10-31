"""Controlled, atomic currency operations over the active GameState."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Callable, Iterable
from uuid import uuid4

from .currency import MAX_CURRENCY_VALUE, CurrencyAccount, normalize_currency, validate_currency_amount
from .economy_config import EconomyConfig
from .transaction import CurrencyTransaction, TransactionDirection, TransactionType

if TYPE_CHECKING:
    from ...core.game_state import GameState


class EconomyTransactionError(ValueError):
    """Raised when a currency operation cannot be completed safely."""


CreditRequest = tuple[int, TransactionType | str, str, str, str | None]


class EconomyManager:
    """Mutate wallet state only through validated, recorded operations."""

    def __init__(
        self,
        game_state: GameState,
        *,
        config: EconomyConfig | None = None,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self.game_state = game_state
        self.config = config or EconomyConfig.load_default()
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._id_factory = id_factory or (lambda: uuid4().hex)

    def get_balance(self, currency_type: str = "gold") -> int:
        return self.game_state.economy.accounts[normalize_currency(currency_type)].balance

    def get_account(self, currency_type: str = "gold") -> CurrencyAccount:
        account = self.game_state.economy.accounts[normalize_currency(currency_type)]
        return CurrencyAccount(account.balance, account.total_earned, account.total_spent)

    def can_afford(self, amount: int, currency_type: str = "gold") -> bool:
        validate_currency_amount(amount)
        return self.get_balance(currency_type) >= amount

    def credit_currency(
        self,
        amount: int,
        *,
        currency_type: str = "gold",
        transaction_type: TransactionType | str = TransactionType.ADMIN_ADJUSTMENT,
        source: str = "Administrative adjustment",
        description: str = "Gold added by an administrative adjustment.",
        reference_id: str | None = None,
    ) -> CurrencyTransaction:
        return self.credit_currency_batch((
            (amount, transaction_type, source, description, reference_id),
        ), currency_type=currency_type)[0]

    def credit_currency_batch(
        self,
        requests: Iterable[CreditRequest],
        *,
        currency_type: str = "gold",
    ) -> tuple[CurrencyTransaction, ...]:
        currency = normalize_currency(currency_type)
        rows = tuple(requests)
        if not rows:
            return ()
        account = self.game_state.economy.accounts[currency]
        prepared: list[CurrencyTransaction] = []
        total = 0
        new_ids = {transaction.transaction_id for transaction in self.game_state.economy.transactions}
        for amount, kind, source, description, reference_id in rows:
            try:
                amount = validate_currency_amount(amount)
                tx = self._make_transaction(kind, currency, amount, TransactionDirection.EARNED, source, description, reference_id)
            except (TypeError, ValueError) as exc:
                raise EconomyTransactionError(str(exc)) from exc
            if tx.transaction_id in new_ids:
                raise EconomyTransactionError(f"Duplicate transaction ID: {tx.transaction_id}")
            new_ids.add(tx.transaction_id)
            total += amount
            if total > MAX_CURRENCY_VALUE:
                raise EconomyTransactionError("Gold reward total exceeds the supported safe integer range.")
            prepared.append(tx)
        if account.balance + total > MAX_CURRENCY_VALUE or account.total_earned + total > MAX_CURRENCY_VALUE:
            raise EconomyTransactionError("Gold balance or lifetime earnings would exceed the supported safe integer range.")

        self.game_state.economy.accounts[currency] = CurrencyAccount(
            account.balance + total,
            account.total_earned + total,
            account.total_spent,
        )
        self.game_state.economy.append_transactions(prepared, history_limit=self.config.transaction_history_limit)
        return tuple(prepared)

    def spend_currency(
        self,
        amount: int,
        *,
        currency_type: str = "gold",
        transaction_type: TransactionType | str = TransactionType.ADMIN_ADJUSTMENT,
        source: str = "Administrative adjustment",
        description: str = "Gold spent by an administrative adjustment.",
        reference_id: str | None = None,
    ) -> CurrencyTransaction:
        return self._spend(amount, currency_type, transaction_type, source, description, reference_id)

    def purchase_gold(
        self,
        amount: int,
        *,
        source: str,
        description: str,
        apply_purchase: Callable[[], bool],
        reference_id: str | None = None,
    ) -> CurrencyTransaction | None:
        """Apply the validated character change before committing its Gold debit."""
        value = validate_currency_amount(amount)
        account = self.game_state.economy.gold
        if account.balance < value:
            raise EconomyTransactionError("Insufficient Gold.")
        if account.total_spent + value > MAX_CURRENCY_VALUE:
            raise EconomyTransactionError("Lifetime Gold spending would exceed the supported safe integer range.")
        if self.game_state.economy.total_successful_purchases >= MAX_CURRENCY_VALUE:
            raise EconomyTransactionError("Successful purchase count exceeds the supported safe integer range.")
        tx = self._make_transaction(
            TransactionType.TRAINING_PURCHASE, "gold", value, TransactionDirection.SPENT,
            source, description, reference_id,
        )
        self._ensure_unique((tx,))
        if not apply_purchase():
            return None
        self.game_state.economy.accounts["gold"] = CurrencyAccount(
            account.balance - value,
            account.total_earned,
            account.total_spent + value,
        )
        self.game_state.economy.total_successful_purchases += 1
        self.game_state.economy.append_transactions([tx], history_limit=self.config.transaction_history_limit)
        return tx

    def _spend(
        self,
        amount: int,
        currency_type: str,
        transaction_type: TransactionType | str,
        source: str,
        description: str,
        reference_id: str | None,
    ) -> CurrencyTransaction:
        currency = normalize_currency(currency_type)
        value = validate_currency_amount(amount)
        account = self.game_state.economy.accounts[currency]
        if account.balance < value:
            raise EconomyTransactionError("Insufficient currency balance.")
        if account.total_spent + value > MAX_CURRENCY_VALUE:
            raise EconomyTransactionError("Lifetime spending would exceed the supported safe integer range.")
        tx = self._make_transaction(transaction_type, currency, value, TransactionDirection.SPENT, source, description, reference_id)
        self._ensure_unique((tx,))
        self.game_state.economy.accounts[currency] = CurrencyAccount(
            account.balance - value,
            account.total_earned,
            account.total_spent + value,
        )
        self.game_state.economy.append_transactions([tx], history_limit=self.config.transaction_history_limit)
        return tx

    def _make_transaction(
        self,
        transaction_type: TransactionType | str,
        currency_type: str,
        amount: int,
        direction: TransactionDirection,
        source: str,
        description: str,
        reference_id: str | None,
    ) -> CurrencyTransaction:
        timestamp = self._clock()
        if not isinstance(timestamp, datetime):
            raise EconomyTransactionError("Transaction clock must return a datetime.")
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        return CurrencyTransaction(
            transaction_id=self._id_factory(),
            transaction_type=transaction_type,
            currency_type=currency_type,
            amount=amount,
            direction=direction,
            source=source,
            description=description,
            timestamp=timestamp.astimezone(timezone.utc).isoformat(),
            reference_id=reference_id,
        )

    def _ensure_unique(self, transactions: Iterable[CurrencyTransaction]) -> None:
        existing = {transaction.transaction_id for transaction in self.game_state.economy.transactions}
        for transaction in transactions:
            if transaction.transaction_id in existing:
                raise EconomyTransactionError(f"Duplicate transaction ID: {transaction.transaction_id}")
            existing.add(transaction.transaction_id)


__all__ = ["EconomyManager", "EconomyTransactionError"]
