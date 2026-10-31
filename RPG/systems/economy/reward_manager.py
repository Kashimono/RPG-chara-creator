"""Single-path enemy defeat rewards using existing EXP and loot systems."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

from .economy_config import EconomyConfig
from .economy_manager import EconomyManager, EconomyTransactionError
from .reward_calculator import GoldRewardCalculation, RewardCalculator
from .transaction import TransactionType

if TYPE_CHECKING:
    from ...core.game_state import GameState
    from ...systems.combat.enemy import Enemy
    from ...systems.combat.loot_table import LootDrop, LootRandomSource, LootTableDatabase


@dataclass(frozen=True)
class RewardSummary:
    exp_awarded: int
    levels_gained: int
    gold_calculation: GoldRewardCalculation
    guaranteed_gold: int
    bonus_gold: int
    total_gold_credited: int
    item_drops: tuple[LootDrop, ...]
    currency_drops: tuple[LootDrop, ...]
    currency_error: str | None = None
    configuration_warning: str | None = None


class RewardManager:
    """Orchestrate a claimed defeat once, without generating parallel loot/EXP."""

    def __init__(
        self,
        config: EconomyConfig | None = None,
        *,
        economy_manager: EconomyManager | None = None,
    ) -> None:
        self.config = config or EconomyConfig.load_default()
        self.calculator = RewardCalculator(self.config)
        self.economy_manager = economy_manager
        self._processed_encounters: set[str] = set()

    def process_defeat(
        self,
        game_state: "GameState",
        enemy: Enemy,
        *,
        loot_database: LootTableDatabase,
        loot_rng: LootRandomSource,
        claim_reward: Callable[[], bool],
        temporary_multiplier: float = 1.0,
    ) -> RewardSummary | None:
        encounter_id = enemy.enemy_id
        if encounter_id in self._processed_encounters:
            return None
        temporary_multiplier = EconomyConfig.validate_multiplier(temporary_multiplier, "temporary reward")
        configuration_warning = None
        if enemy.definition_id.casefold() not in self.config.enemy_gold_rewards:
            calculation = GoldRewardCalculation(
                enemy.definition_id, 0, self.config.global_gold_multiplier,
                self.config.multiplier_for_classification(enemy.classification.value),
                self.config.multiplier_for_enemy(enemy.definition_id), temporary_multiplier, 0,
            )
            configuration_warning = f"No base Gold reward is configured for enemy '{enemy.definition_id}'."
        else:
            calculation = self.calculator.calculate(
                enemy.definition_id,
                enemy.classification.value,
                temporary_multiplier=temporary_multiplier,
            )
        if not claim_reward():
            return None
        self._processed_encounters.add(encounter_id)

        exp = enemy.exp_reward
        levels = game_state.award_combat_exp(exp) if exp > 0 else 0
        game_state.record_enemy_defeated(exp, enemy.classification.value)
        drops = loot_database.roll(enemy.loot_table_id, loot_rng)
        currency_drops = tuple(drop for drop in drops if drop.currency_type is not None)
        item_drops = tuple(drop for drop in drops if drop.currency_type is None)
        bonus_gold = sum(drop.quantity for drop in currency_drops)
        requests = []
        category_type = {
            "boss": TransactionType.BOSS_REWARD,
            "world_boss": TransactionType.WORLD_BOSS_REWARD,
        }.get(enemy.classification.value, TransactionType.ENEMY_REWARD)
        if calculation.final_gold:
            requests.append((
                calculation.final_gold,
                category_type,
                enemy.name,
                f"Guaranteed Gold reward for defeating {enemy.name}.",
                encounter_id,
            ))
        for drop in currency_drops:
            requests.append((
                drop.quantity,
                TransactionType.LOOT_CURRENCY_DROP,
                enemy.name,
                f"Additional Gold loot ({drop.reward_id}) from {enemy.name}.",
                encounter_id,
            ))

        credited = 0
        currency_error = None
        if requests:
            manager = self.economy_manager or EconomyManager(game_state, config=self.config)
            if manager.game_state is not game_state:
                manager = EconomyManager(game_state, config=self.config)
            try:
                manager.credit_currency_batch(requests, currency_type="gold")
                credited = calculation.final_gold + bonus_gold
            except EconomyTransactionError as exc:
                currency_error = str(exc)

        return RewardSummary(
            exp_awarded=exp,
            levels_gained=levels,
            gold_calculation=calculation,
            guaranteed_gold=calculation.final_gold,
            bonus_gold=bonus_gold,
            total_gold_credited=credited,
            item_drops=item_drops,
            currency_drops=currency_drops,
            currency_error=currency_error,
            configuration_warning=configuration_warning,
        )


__all__ = ["RewardManager", "RewardSummary"]
