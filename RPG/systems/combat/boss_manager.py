"""Boss phase transitions and single-claim victory rewards."""

from __future__ import annotations

from dataclasses import dataclass

from .enemy import Enemy, EnemyClassification


@dataclass(frozen=True)
class BossPhaseTransition:
    previous_phase: str
    current_phase: str
    description: str


class BossManager:
    """Apply monotonic, definition-driven boss phases to an enemy instance."""

    def advance_phases(self, enemy: Enemy) -> tuple[BossPhaseTransition, ...]:
        if enemy.classification not in {EnemyClassification.BOSS, EnemyClassification.WORLD_BOSS}:
            return ()
        if enemy.is_defeated or not enemy.definition.boss_phases:
            return ()

        transitions: list[BossPhaseTransition] = []
        phases = enemy.definition.boss_phases
        while enemy.phase_index + 1 < len(phases):
            next_index = enemy.phase_index + 1
            next_phase = phases[next_index]
            if enemy.hp_ratio > next_phase.hp_threshold:
                break
            previous = enemy.boss_phase.name if enemy.boss_phase else "None"
            enemy.set_phase(next_index)
            current = enemy.boss_phase
            transitions.append(BossPhaseTransition(previous, current.name, current.description))
        return tuple(transitions)

    def claim_defeat(self, enemy: Enemy) -> bool:
        """Return false after the same enemy instance has already paid out."""
        if enemy.classification not in {EnemyClassification.BOSS, EnemyClassification.WORLD_BOSS}:
            raise ValueError("BossManager can only claim boss or world-boss defeats.")
        if not enemy.is_defeated:
            return False
        return enemy.claim_reward()
