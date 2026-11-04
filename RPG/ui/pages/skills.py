"""Skill catalog, progression, and six-slot loadout interface."""

from __future__ import annotations

from collections.abc import Callable
from tkinter import messagebox

import customtkinter as ctk

from ...config import ACCENT_COLOR, SECONDARY_TEXT, SURFACE_COLOR, TEXT_COLOR
from ...core.game_state import GameState
from ...systems.economy.economy_manager import EconomyManager
from ...systems.skills.skill_manager import SkillActionError, SkillManager


class SkillsPage(ctk.CTkFrame):
    CATEGORIES = ("physical", "magical", "defensive", "support")

    def __init__(self, parent: ctk.CTkBaseClass, get_game_state: Callable[[], GameState], on_change: Callable[[], None]) -> None:
        super().__init__(parent, fg_color="transparent")
        self._get_game_state = get_game_state
        self._on_change = on_change
        self._bound_state: GameState | None = None
        self.manager: SkillManager | None = None
        self._category = "physical"
        self._selected_skill_id: str | None = None
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 8))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="Skills", anchor="w", font=ctk.CTkFont(size=27, weight="bold"), text_color=TEXT_COLOR).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(header, text="Unlock, improve, and equip combat skills. Cooldowns reset when you restart the game.", anchor="w", font=ctk.CTkFont(size=12), text_color=SECONDARY_TEXT).grid(row=1, column=0, sticky="w", pady=(2, 0))
        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 14))
        body.grid_columnconfigure(0, weight=1)
        self.loadout_label = ctk.CTkLabel(body, text="Loadout", anchor="w", font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT_COLOR)
        self.loadout_label.grid(row=0, column=0, sticky="ew", pady=(2, 10))
        self.category_menu = ctk.CTkOptionMenu(body, values=[value.title() for value in self.CATEGORIES], command=self._select_category)
        self.category_menu.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.skill_menu = ctk.CTkOptionMenu(body, values=[], command=self._select_skill)
        self.skill_menu.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        self.details = ctk.CTkFrame(body, fg_color=SURFACE_COLOR, corner_radius=18)
        self.details.grid(row=3, column=0, sticky="nsew")
        self.details.grid_columnconfigure(0, weight=1)
        self.name_label = ctk.CTkLabel(self.details, text="Select a skill", anchor="w", font=ctk.CTkFont(size=22, weight="bold"), text_color=TEXT_COLOR)
        self.name_label.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 4))
        self.info_label = ctk.CTkLabel(self.details, text="", anchor="w", justify="left", wraplength=850, font=ctk.CTkFont(size=13), text_color=SECONDARY_TEXT)
        self.info_label.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 12))
        self.status_label = ctk.CTkLabel(self.details, text="", anchor="w", justify="left", wraplength=850, font=ctk.CTkFont(size=12), text_color=TEXT_COLOR)
        self.status_label.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 12))
        actions = ctk.CTkFrame(self.details, fg_color="transparent")
        actions.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 16))
        self.unlock_button = ctk.CTkButton(actions, text="Unlock", command=self._unlock)
        self.unlock_button.pack(side="left", padx=4)
        self.upgrade_button = ctk.CTkButton(actions, text="Upgrade", command=self._upgrade)
        self.upgrade_button.pack(side="left", padx=4)
        self.equip_button = ctk.CTkButton(actions, text="Equip", command=self._toggle_equip, fg_color="#526f9b")
        self.equip_button.pack(side="left", padx=4)
        self.refresh()

    def _bind_state(self) -> None:
        state = self._get_game_state()
        if state is self._bound_state:
            return
        self._bound_state = state
        self.manager = SkillManager(state)
        self._selected_skill_id = None

    def _select_category(self, value: str) -> None:
        self._category = value.casefold()
        self._selected_skill_id = None
        self.refresh()

    def _select_skill(self, value: str) -> None:
        if self.manager is None:
            return
        selected = next((skill for skill in self.manager.list_skills() if skill.name == value), None)
        self._selected_skill_id = selected.skill_id if selected else None
        self.refresh()

    def refresh(self) -> None:
        self._bind_state()
        assert self.manager is not None and self._bound_state is not None
        manager = self.manager
        skills = manager.list_skills(self._category)
        names = [skill.name for skill in skills]
        selected = manager.database.get_optional(self._selected_skill_id or "")
        if selected not in skills:
            selected = skills[0] if skills else None
            self._selected_skill_id = selected.skill_id if selected else None
        self.skill_menu.configure(values=names)
        self.skill_menu.set(selected.name if selected else "No skills configured")
        equipped_names = [manager.database.get_optional(skill_id).name for skill_id in manager.progress.equipped_skill_ids if manager.database.get_optional(skill_id)]
        slots = "  ·  ".join(f"{index + 1}. {name}" for index, name in enumerate(equipped_names)) or "No skills equipped"
        self.loadout_label.configure(text=f"Equipped ({len(equipped_names)}/{manager.progress.max_equipped_skills}): {slots}")
        if selected is None:
            return
        unlocked = manager.is_unlocked(selected.skill_id)
        level = manager.level(selected.skill_id)
        requirements, requirement_text = manager.unlock_requirements(selected.skill_id)
        cost = selected.unlock_gold
        enough_gold = EconomyManager(self._bound_state).get_balance() >= cost
        self.name_label.configure(text=f"{selected.name}  ·  {selected.classification.title()}")
        self.info_label.configure(text=selected.description)
        effects = ", ".join(effect.kind.replace("_", " ").title() + (f" ({effect.status.replace('_', ' ')})" if effect.status else "") for effect in selected.effects)
        upgrade_cost = selected.upgrade_gold * max(1, level)
        self.status_label.configure(text=(
            f"MP Cost: {selected.mp_cost:g}   ·   Cooldown: {selected.cooldown:g}s   ·   Required level: {selected.required_level}\n"
            f"Effects: {effects}\n"
            + (f"Unlocked · Level {level}/{selected.max_level}" if unlocked else f"Locked · {requirement_text} · Unlock cost: {cost:,} G")
        ))
        self.unlock_button.configure(text=f"Unlock · {cost:,} G", state="normal" if requirements and enough_gold else "disabled")
        can_upgrade = unlocked and level < selected.max_level and (upgrade_cost == 0 or EconomyManager(self._bound_state).get_balance() >= upgrade_cost)
        self.upgrade_button.configure(text=f"Upgrade · {upgrade_cost:,} G", state="normal" if can_upgrade else "disabled")
        equipped = manager.is_equipped(selected.skill_id)
        self.equip_button.configure(text="Unequip" if equipped else "Equip", state="normal" if unlocked and (equipped or len(manager.progress.equipped_skill_ids) < manager.progress.max_equipped_skills) else "disabled")

    def _unlock(self) -> None:
        self._run_action(lambda: self.manager.unlock(self._selected_skill_id or ""), "Skill unlocked.")

    def _upgrade(self) -> None:
        self._run_action(lambda: self.manager.upgrade(self._selected_skill_id or ""), "Skill upgraded.")

    def _toggle_equip(self) -> None:
        if self.manager is None or not self._selected_skill_id:
            return
        try:
            if self.manager.is_equipped(self._selected_skill_id):
                self.manager.unequip(self._selected_skill_id)
                message = "Skill unequipped."
            else:
                self.manager.equip(self._selected_skill_id)
                message = "Skill equipped."
        except SkillActionError as exc:
            messagebox.showinfo("Skills", str(exc), parent=self.winfo_toplevel())
            return
        self._on_change()
        self.refresh()
        messagebox.showinfo("Skills", message, parent=self.winfo_toplevel())

    def _run_action(self, action: Callable[[], object], success: str) -> None:
        try:
            action()
        except (SkillActionError, ValueError) as exc:
            messagebox.showinfo("Skills", str(exc), parent=self.winfo_toplevel())
            return
        self._on_change()
        self.refresh()
        messagebox.showinfo("Skills", success, parent=self.winfo_toplevel())
