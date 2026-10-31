"""Deterministic, centralized Gold reward formula and source breakdown."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, DecimalException, ROUND_HALF_UP

from .currency import MAX_CURRENCY_VALUE
from .economy_config import EconomyConfig


@dataclass(frozen=True)
class GoldRewardCalculation:
    enemy_id: str
    base_gold: int
    global_multiplier: float
    classification_multiplier: float
    enemy_multiplier: float
    temporary_multiplier: float
    final_gold: int

    @property
    def multiplier_sources(self) -> tuple[tuple[str, float], ...]:
        return (
            ("global", self.global_multiplier),
            ("classification", self.classification_multiplier),
            ("enemy", self.enemy_multiplier),
            ("temporary", self.temporary_multiplier),
        )


class RewardCalculator:
    """Calculate base rewards from the immutable enemy definition identity."""

    def __init__(self, config: EconomyConfig) -> None:
        self.config = config

    def calculate(
        self,
        enemy_id: str,
        classification: str,
        *,
        temporary_multiplier: float = 1.0,
    ) -> GoldRewardCalculation:
        base = self.config.base_reward_for(enemy_id)
        temporary = EconomyConfig.validate_multiplier(temporary_multiplier, "temporary reward")
        class_factor = self.config.multiplier_for_classification(classification)
        enemy_factor = self.config.multiplier_for_enemy(enemy_id)
        factors = (
            self.config.global_gold_multiplier,
            class_factor,
            enemy_factor,
            temporary,
        )
        try:
            result = Decimal(base)
            for factor in factors:
                result *= Decimal(str(factor))
            if result > Decimal(MAX_CURRENCY_VALUE):
                raise ValueError(f"Gold reward for '{enemy_id}' exceeds the supported safe integer range.")
            rounded = int(result.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        except ValueError:
            raise
        except (DecimalException, OverflowError) as exc:
            raise ValueError(f"Gold reward calculation for '{enemy_id}' exceeds numeric limits.") from exc
        if rounded < 0:
            raise ValueError("Gold rewards cannot be negative.")
        if rounded > MAX_CURRENCY_VALUE:
            raise ValueError(f"Gold reward for '{enemy_id}' exceeds the supported safe integer range.")
        return GoldRewardCalculation(
            enemy_id=enemy_id,
            base_gold=base,
            global_multiplier=self.config.global_gold_multiplier,
            classification_multiplier=class_factor,
            enemy_multiplier=enemy_factor,
            temporary_multiplier=temporary,
            final_gold=rounded,
        )


__all__ = ["GoldRewardCalculation", "RewardCalculator"]
