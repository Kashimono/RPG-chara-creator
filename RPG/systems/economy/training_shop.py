"""Gold-based stat training routed through Player's existing allocation rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .economy_config import EconomyConfig, TrainingDefinition
from .economy_manager import EconomyManager, EconomyTransactionError

if TYPE_CHECKING:
    from ...core.game_state import GameState


@dataclass(frozen=True)
class TrainingPurchaseResult:
    success: bool
    message: str
    training_id: str | None = None
    cost: int = 0
    stat_name: str | None = None
    stat_points: int = 0


class TrainingShop:
    def __init__(
        self,
        game_state: "GameState",
        economy_manager: EconomyManager | None = None,
        config: EconomyConfig | None = None,
    ) -> None:
        self.game_state = game_state
        self.config = config or (economy_manager.config if economy_manager else EconomyConfig.load_default())
        self.economy_manager = economy_manager or EconomyManager(game_state, config=self.config)
        self._trainings = {item.training_id.casefold(): item for item in self.config.trainings}

    @property
    def trainings(self) -> tuple[TrainingDefinition, ...]:
        return self.config.trainings

    def can_purchase(self, training_id: str) -> TrainingPurchaseResult:
        training = self._get_training(training_id)
        if training is None:
            return TrainingPurchaseResult(False, f"Unknown training option: {training_id}.")
        player = self.game_state.character
        if not player.character_created:
            return self._failure(training, "Create a character before buying training.")
        if not self.economy_manager.can_afford(training.cost):
            return self._failure(training, "Insufficient Gold.")
        try:
            can_allocate = player.can_allocate(
                training.stat_name,
                training.stat_points,
                consume_stat_points=False,
            )
        except (KeyError, TypeError):
            can_allocate = False
        if not can_allocate:
            return self._failure(training, f"{training.stat_name} potential is full or has not been accepted.")
        return TrainingPurchaseResult(True, "Ready to purchase.", training.training_id, training.cost, training.stat_name, training.stat_points)

    def purchase(self, training_id: str) -> TrainingPurchaseResult:
        available = self.can_purchase(training_id)
        if not available.success:
            return available
        training = self._trainings[training_id.casefold()]
        player = self.game_state.character
        try:
            transaction = self.economy_manager.purchase_gold(
                training.cost,
                source=training.name,
                description=f"Purchased {training.name}: +{training.stat_points} {training.stat_name}.",
                reference_id=training.training_id,
                apply_purchase=lambda: player.allocate_points(
                    training.stat_name,
                    training.stat_points,
                    consume_stat_points=False,
                ),
            )
        except EconomyTransactionError as exc:
            return self._failure(training, str(exc))
        if transaction is None:
            return self._failure(training, f"{training.stat_name} potential is full or has not been accepted.")
        return TrainingPurchaseResult(
            True,
            f"{training.name} complete: +{training.stat_points} {training.stat_name}.",
            training.training_id,
            training.cost,
            training.stat_name,
            training.stat_points,
        )

    def _get_training(self, training_id: str) -> TrainingDefinition | None:
        if not isinstance(training_id, str):
            return None
        return self._trainings.get(training_id.casefold())

    @staticmethod
    def _failure(training: TrainingDefinition, message: str) -> TrainingPurchaseResult:
        return TrainingPurchaseResult(False, message, training.training_id, training.cost, training.stat_name, training.stat_points)


__all__ = ["TrainingPurchaseResult", "TrainingShop"]
