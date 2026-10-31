"""Reusable panels for race bonuses, class selection, and character titles."""

from __future__ import annotations

from tkinter import messagebox

import customtkinter as ctk

from ...config import SECONDARY_TEXT, SURFACE_COLOR, TEXT_COLOR
from ...core.player import Player
from ...core.progression_config import (
    CLASS_DEFINITIONS,
    TITLE_DEFINITIONS,
    get_class_definition,
    get_race_bonuses,
)
from ...core.race import Race
from ...core.progression_config import PassiveBonuses


class RaceBonusPanel(ctk.CTkFrame):
    def __init__(self, parent) -> None:
        super().__init__(parent, fg_color=SURFACE_COLOR, corner_radius=18)
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text="RACE PASSIVES", anchor="w", font=ctk.CTkFont(size=12, weight="bold"), text_color=SECONDARY_TEXT).grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 6))
        self.race_label = ctk.CTkLabel(self, text="No race selected", anchor="w", font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT_COLOR)
        self.race_label.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 4))
        self.bonuses_label = ctk.CTkLabel(self, text="Roll and accept a race to activate its passive bonuses.", anchor="w", justify="left", wraplength=420, font=ctk.CTkFont(size=12), text_color=SECONDARY_TEXT)
        self.bonuses_label.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 14))

    def refresh(self, player: Player) -> None:
        race = player.race
        if not race:
            self.race_label.configure(text="No race selected")
            self.bonuses_label.configure(text="Roll and accept a race to activate its passive bonuses.")
        elif not player.race_accepted:
            self.race_label.configure(text=f"{race.name} ({race.rarity_name})", text_color=race.text_color)
            self.bonuses_label.configure(text="Accept this race to activate its passive bonuses.")
        else:
            self.race_label.configure(text=f"{race.name} ({race.rarity_name})", text_color=race.text_color)
            self.bonuses_label.configure(text=format_passive_bonuses(get_race_bonuses(race)))


class ClassSelectionPanel(ctk.CTkFrame):
    def __init__(self, parent, on_change) -> None:
        super().__init__(parent, fg_color=SURFACE_COLOR, corner_radius=18)
        self.player: Player | None = None
        self.on_change = on_change
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text="CHARACTER CLASS", anchor="w", font=ctk.CTkFont(size=12, weight="bold"), text_color=SECONDARY_TEXT).grid(row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=(14, 8))
        self.current_label = ctk.CTkLabel(self, text="Current class: Unselected", anchor="w", font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT_COLOR)
        self.current_label.grid(row=1, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 8))
        self.class_menu = ctk.CTkOptionMenu(
            self,
            values=["No class", *(definition.name for definition in CLASS_DEFINITIONS.values())],
            command=self._preview_selection,
        )
        self.class_menu.grid(row=2, column=0, sticky="ew", padx=(16, 8), pady=(0, 8))
        self.select_button = ctk.CTkButton(self, text="Select class", width=120, command=self._select)
        self.select_button.grid(row=2, column=1, sticky="e", padx=(0, 16), pady=(0, 8))
        self.description_label = ctk.CTkLabel(self, text="Choose a class to review its specialization and passive bonuses.", anchor="w", justify="left", wraplength=440, font=ctk.CTkFont(size=12), text_color=SECONDARY_TEXT)
        self.description_label.grid(row=3, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 14))
        self.class_menu.set("No class")

    def _preview_selection(self, name: str) -> None:
        definition = get_class_definition(name)
        if definition is None:
            self.description_label.configure(text="No class selected. Class passives are not active.")
            return
        requirement = definition.requirements
        requirement_text = f"Requires level {requirement.minimum_level}"
        if requirement.requires_character_created:
            requirement_text += " and a completed character"
        self.description_label.configure(
            text=f"{definition.icon}  {definition.description}\nSpecialization: {definition.specialization}\n{format_passive_bonuses(definition.bonuses)}\n{requirement_text}."
        )

    def _select(self) -> None:
        if self.player is None:
            return
        selected = self.class_menu.get()
        definition = get_class_definition(selected)
        selected_id = definition.class_id if definition else None
        if selected_id == self.player.class_id:
            return
        confirmation = "Clear your current class?" if selected_id is None else f"Select {definition.name}? You can change it later after confirming again."
        if not messagebox.askyesno("Confirm Class Selection", confirmation, parent=self):
            self.refresh(self.player)
            return
        try:
            self.player.select_class(selected_id)
        except ValueError as exc:
            messagebox.showerror("Class Selection", str(exc), parent=self)
            self.refresh(self.player)
            return
        self.on_change()

    def refresh(self, player: Player) -> None:
        self.player = player
        definition = player.selected_class
        self.current_label.configure(text=f"Current class: {definition.name if definition else 'Unselected'}")
        self.class_menu.set(definition.name if definition else "No class")
        self._preview_selection(self.class_menu.get())


class TitlePanel(ctk.CTkFrame):
    def __init__(self, parent, on_change) -> None:
        super().__init__(parent, fg_color=SURFACE_COLOR, corner_radius=18)
        self.player: Player | None = None
        self.on_change = on_change
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text="CHARACTER TITLES", anchor="w", font=ctk.CTkFont(size=12, weight="bold"), text_color=SECONDARY_TEXT).grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 4))
        self.equipped_label = ctk.CTkLabel(self, text="Equipped: Novice", anchor="w", font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT_COLOR)
        self.equipped_label.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 8))

        rows = ctk.CTkScrollableFrame(self, height=190, fg_color="transparent")
        rows.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 10))
        rows.grid_columnconfigure(0, weight=1)
        self.title_rows: dict[str, tuple[ctk.CTkLabel, ctk.CTkButton]] = {}
        for index, definition in enumerate(TITLE_DEFINITIONS.values()):
            label = ctk.CTkLabel(rows, text="", anchor="w", justify="left", wraplength=440, font=ctk.CTkFont(size=12), text_color=TEXT_COLOR)
            label.grid(row=index, column=0, sticky="ew", padx=8, pady=4)
            button = ctk.CTkButton(rows, text="Equip", width=74, height=30, command=lambda title_id=definition.title_id: self._equip(title_id))
            button.grid(row=index, column=1, sticky="e", padx=8, pady=4)
            self.title_rows[definition.title_id] = (label, button)

    def _equip(self, title_id: str) -> None:
        if self.player is None:
            return
        try:
            self.player.equip_title(title_id)
        except ValueError as exc:
            messagebox.showerror("Title Selection", str(exc), parent=self)
            return
        self.on_change()

    def refresh(self, player: Player) -> None:
        self.player = player
        self.equipped_label.configure(text=f"Equipped: {player.equipped_title_name}")
        unlocked = set(player.unlocked_titles)
        for title_id, definition in TITLE_DEFINITIONS.items():
            label, button = self.title_rows[title_id]
            is_unlocked = title_id in unlocked
            if is_unlocked:
                state_text = "Unlocked"
            else:
                state_text = f"Unlock at level {definition.minimum_level}"
            label.configure(text=f"{definition.name} - {definition.description} ({state_text})")
            if title_id == player.equipped_title:
                button.configure(text="Equipped", state="disabled")
            else:
                button.configure(text="Equip", state="normal" if is_unlocked else "disabled")


def format_passive_bonuses(bonuses: PassiveBonuses) -> str:
    labels = (
        ("HP", "hp_multiplier"),
        ("MP", "mp_multiplier"),
        ("Attack", "attack_multiplier"),
        ("Agility", "agility_multiplier"),
        ("Stamina", "stamina_multiplier"),
        ("Physical Defense", "physical_defense_multiplier"),
        ("Magical Defense", "magical_defense_multiplier"),
        ("Critical Damage", "critical_damage_multiplier"),
        ("Attack Speed", "attack_speed_multiplier"),
        ("HP Regeneration", "hp_regen_multiplier"),
        ("MP Regeneration", "mp_regen_multiplier"),
    )
    entries = [f"{label} x{getattr(bonuses, field):.2f}" for label, field in labels if getattr(bonuses, field) != 1.0]
    if bonuses.critical_chance_bonus:
        entries.append(f"Critical Chance +{bonuses.critical_chance_bonus:.0%}")
    return "Passive bonuses: " + (", ".join(entries) if entries else "none")
