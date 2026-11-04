"""Progression, loadout, and transient cooldown rules for player skills."""

from __future__ import annotations

from math import isfinite
import time
from typing import TYPE_CHECKING, Callable

from .skill import SkillDefinition, SkillProgressState
from .skill_config import load_skill_config
from .skill_database import SkillDatabase

if TYPE_CHECKING:
    from ...core.game_state import GameState


class SkillActionError(ValueError):
    """Raised when a skill progression or activation action is invalid."""


class SkillManager:
    def __init__(self, game_state: "GameState", database: SkillDatabase | None = None, *, now: Callable[[], float] = time.monotonic) -> None:
        self.game_state = game_state
        self.database = database or SkillDatabase.load_default()
        config = load_skill_config()
        unknown_starters = [skill_id for skill_id in config["starting_skills"] if self.database.get_optional(skill_id) is None]
        if unknown_starters:
            raise ValueError("Skill configuration references missing starting skills: " + ", ".join(unknown_starters))
        if len(set(config["starting_skills"])) > int(config["max_equipped_skills"]):
            raise ValueError("Starting skills exceed the configured loadout capacity.")
        self._now = now
        self._ready_at: dict[str, float] = {}
        self._normalize_state()

    @property
    def progress(self) -> SkillProgressState:
        return self.game_state.skill_state

    def _normalize_state(self) -> None:
        state = self.progress
        valid_unlocked = [key for key in state.unlocked_skill_ids if self.database.get_optional(key)]
        state.unlocked_skill_ids = list(dict.fromkeys(valid_unlocked))
        state.skill_levels = {key: min(self.database.get(key).max_level, max(1, value)) for key, value in state.skill_levels.items() if key in state.unlocked_skill_ids}
        for key in state.unlocked_skill_ids:
            state.skill_levels.setdefault(key, 1)
        state.equipped_skill_ids = [key for key in dict.fromkeys(state.equipped_skill_ids) if key in state.unlocked_skill_ids][:state.max_equipped_skills]

    def list_skills(self, classification: str | None = None) -> tuple[SkillDefinition, ...]:
        skills = self.database.list_skills() if classification is None else self.database.by_classification(classification)
        return skills

    def level(self, skill_id: str) -> int:
        return self.progress.skill_levels.get(skill_id.casefold(), 0)

    def is_unlocked(self, skill_id: str) -> bool:
        return skill_id.casefold() in self.progress.unlocked_skill_ids

    def is_equipped(self, skill_id: str) -> bool:
        return skill_id.casefold() in self.progress.equipped_skill_ids

    def unlock_requirements(self, skill_id: str) -> tuple[bool, str]:
        skill = self.database.get(skill_id)
        if self.is_unlocked(skill.skill_id):
            return False, "Skill is already unlocked."
        if self.game_state.character.level < skill.required_level:
            return False, f"Requires character level {skill.required_level}."
        missing = [self.database.get(item).name for item in skill.prerequisites if not self.is_unlocked(item)]
        if missing:
            return False, "Requires: " + ", ".join(missing) + "."
        return True, "Requirements met."

    def unlock(self, skill_id: str) -> bool:
        skill = self.database.get(skill_id)
        allowed, reason = self.unlock_requirements(skill_id)
        if not allowed:
            raise SkillActionError(reason)
        from ..economy.economy_manager import EconomyManager, EconomyTransactionError
        from ..economy.transaction import TransactionType
        def apply() -> bool:
            self.progress.unlocked_skill_ids.append(skill.skill_id)
            self.progress.skill_levels[skill.skill_id] = 1
            return True
        if skill.unlock_gold == 0:
            return apply()
        try:
            result = EconomyManager(self.game_state).spend_currency_with_operation(
                skill.unlock_gold, transaction_type=TransactionType.SKILL_UNLOCK, source=skill.name,
                description=f"Unlocked skill: {skill.name}.", apply_operation=apply, reference_id=skill.skill_id,
            )
        except EconomyTransactionError as exc:
            raise SkillActionError(str(exc)) from exc
        return result is not None

    def upgrade(self, skill_id: str) -> int:
        skill = self.database.get(skill_id)
        if not self.is_unlocked(skill.skill_id):
            raise SkillActionError("Unlock this skill before upgrading it.")
        current = self.level(skill.skill_id)
        if current >= skill.max_level:
            raise SkillActionError("This skill is already at maximum level.")
        cost = skill.upgrade_gold * current
        from ..economy.economy_manager import EconomyManager, EconomyTransactionError
        from ..economy.transaction import TransactionType
        new_level = current + 1
        def apply() -> bool:
            self.progress.skill_levels[skill.skill_id] = new_level
            return True
        if cost == 0:
            apply()
            return new_level
        try:
            result = EconomyManager(self.game_state).spend_currency_with_operation(
                cost, transaction_type=TransactionType.SKILL_UPGRADE, source=skill.name,
                description=f"Upgraded {skill.name} to level {new_level}.", apply_operation=apply, reference_id=skill.skill_id,
            )
        except EconomyTransactionError as exc:
            raise SkillActionError(str(exc)) from exc
        if result is None:
            raise SkillActionError("Skill upgrade was not applied.")
        return new_level

    def equip(self, skill_id: str, slot: int | None = None) -> None:
        skill = self.database.get(skill_id)
        if not self.is_unlocked(skill.skill_id):
            raise SkillActionError("Locked skills cannot be equipped.")
        equipped = self.progress.equipped_skill_ids
        if skill.skill_id in equipped:
            return
        if slot is not None and (isinstance(slot, bool) or not isinstance(slot, int) or not 0 <= slot < self.progress.max_equipped_skills):
            raise SkillActionError("Invalid skill slot.")
        if slot is None and len(equipped) >= self.progress.max_equipped_skills:
            raise SkillActionError("The skill loadout is full.")
        if slot is not None and slot < len(equipped):
            equipped[slot] = skill.skill_id
        else:
            equipped.append(skill.skill_id)

    def unequip(self, skill_id: str) -> bool:
        key = skill_id.casefold()
        if key not in self.progress.equipped_skill_ids:
            return False
        self.progress.equipped_skill_ids.remove(key)
        return True

    def cooldown_remaining(self, skill_id: str, *, now: float | None = None) -> float:
        current = self._now() if now is None else float(now)
        if not isfinite(current):
            raise ValueError("Skill time must be finite.")
        return max(0.0, self._ready_at.get(skill_id.casefold(), 0.0) - current)

    def validate_activation(self, skill_id: str, *, now: float, require_equipped: bool = True) -> SkillDefinition:
        skill = self.database.get(skill_id)
        if not self.is_unlocked(skill.skill_id):
            raise SkillActionError(f"{skill.name} is locked.")
        if require_equipped and not self.is_equipped(skill.skill_id):
            raise SkillActionError(f"{skill.name} is not equipped.")
        if self.cooldown_remaining(skill.skill_id, now=now) > 0:
            raise SkillActionError(f"{skill.name} is recharging ({self.cooldown_remaining(skill.skill_id, now=now):.1f}s).")
        if not self.game_state.character.can_consume_mp(skill.mp_cost):
            raise SkillActionError(f"Not enough MP for {skill.name}.")
        return skill

    def start_cooldown(self, skill: SkillDefinition, now: float) -> None:
        self._ready_at[skill.skill_id] = now + skill.cooldown

    def clear_cooldowns(self) -> None:
        self._ready_at.clear()
