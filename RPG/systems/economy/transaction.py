"""Validated, serializable records of successful economy operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


MAX_CURRENCY_VALUE = 9_223_372_036_854_775_807


class TransactionType(str, Enum):
    ENEMY_REWARD = "enemy_reward"
    BOSS_REWARD = "boss_reward"
    WORLD_BOSS_REWARD = "world_boss_reward"
    LOOT_CURRENCY_DROP = "loot_currency_drop"
    TRAINING_PURCHASE = "training_purchase"
    ADMIN_ADJUSTMENT = "admin_adjustment"


class TransactionDirection(str, Enum):
    EARNED = "earned"
    SPENT = "spent"


@dataclass(frozen=True)
class CurrencyTransaction:
    transaction_id: str
    transaction_type: TransactionType | str
    currency_type: str
    amount: int
    direction: TransactionDirection | str
    source: str
    description: str
    timestamp: str
    reference_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.transaction_id, str) or not self.transaction_id.strip():
            raise ValueError("Transactions require a unique identifier.")
        if not isinstance(self.currency_type, str) or not self.currency_type.strip():
            raise ValueError("Transactions require a currency type.")
        if isinstance(self.amount, bool) or not isinstance(self.amount, int) or not 0 < self.amount <= MAX_CURRENCY_VALUE:
            raise ValueError("Transaction amounts must be positive safe whole numbers.")
        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("Transactions require a source or destination.")
        if not isinstance(self.description, str) or not self.description.strip():
            raise ValueError("Transactions require a description.")
        if not isinstance(self.timestamp, str) or not self.timestamp.strip():
            raise ValueError("Transactions require a timestamp.")
        try:
            tx_type = TransactionType(self.transaction_type)
            direction = TransactionDirection(self.direction)
            datetime.fromisoformat(self.timestamp.replace("Z", "+00:00"))
        except (TypeError, ValueError) as exc:
            raise ValueError("Transaction type, direction, or timestamp is invalid.") from exc
        object.__setattr__(self, "transaction_type", tx_type)
        object.__setattr__(self, "direction", direction)

    def to_dict(self) -> dict[str, str | int | None]:
        return {
            "transaction_id": self.transaction_id,
            "transaction_type": self.transaction_type.value,
            "currency_type": self.currency_type,
            "amount": self.amount,
            "direction": self.direction.value,
            "source": self.source,
            "description": self.description,
            "timestamp": self.timestamp,
            "reference_id": self.reference_id,
        }

    @classmethod
    def from_dict(cls, data: object) -> "CurrencyTransaction":
        if not isinstance(data, dict):
            raise ValueError("A saved transaction must be an object.")
        return cls(
            transaction_id=data.get("transaction_id"),
            transaction_type=data.get("transaction_type"),
            currency_type=data.get("currency_type", "gold"),
            amount=data.get("amount"),
            direction=data.get("direction"),
            source=data.get("source"),
            description=data.get("description"),
            timestamp=data.get("timestamp"),
            reference_id=data.get("reference_id"),
        )
