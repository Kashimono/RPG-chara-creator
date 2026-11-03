"""Character builder page composed from the existing feature panels."""

from __future__ import annotations

import customtkinter as ctk

from ...config import SECONDARY_TEXT, TEXT_COLOR
from ...core.player import Player
from ...core.stat_calculator import calculate_attributes
from ...systems.inventory.item_database import ItemDatabase
from ..advanced_panel import AdvancedPanel
from ..components.progression_panels import ClassSelectionPanel, RaceBonusPanel, TitlePanel
from ..level_panel import LevelPanel
from ..potential_panel import PotentialPanel
from ..race_panel import RacePanel
from ..stat_panel import StatPanel


class CharacterPage(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkBaseClass, window) -> None:
        super().__init__(parent, fg_color="transparent")
        self.window = window
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=22, pady=(20, 8))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="Character", anchor="w", font=ctk.CTkFont(size=26, weight="bold"), text_color=TEXT_COLOR).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(header, text="Roll a race, choose potentials, then grow your stats.", anchor="w", font=ctk.CTkFont(size=12), text_color=SECONDARY_TEXT).grid(row=1, column=0, sticky="w", pady=(2, 0))
        ctk.CTkButton(header, text="Copy Character Stats", width=180, height=38, corner_radius=12, command=window.copy_character_stats).grid(row=0, column=1, rowspan=2, padx=(12, 0))

        self.body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.body.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 12))
        self.body.grid_columnconfigure(0, weight=1, uniform="character")
        self.body.grid_columnconfigure(1, weight=1, uniform="character")
        player = window.game_state.character

        self.level_panel = LevelPanel(self.body, player, window.handle_game_change)
        self.level_panel.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        self.race_panel = RacePanel(self.body, player, window.handle_game_change)
        self.race_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 6), pady=(0, 10))
        self.class_panel = ClassSelectionPanel(self.body, window.handle_game_change)
        self.class_panel.grid(row=1, column=1, sticky="nsew", padx=(6, 0), pady=(0, 10))

        self.potential_panel = PotentialPanel(self.body, player, window.handle_game_change)
        self.potential_panel.grid(row=2, column=0, sticky="nsew", padx=(0, 6), pady=(0, 10))
        self.race_bonus_panel = RaceBonusPanel(self.body)
        self.race_bonus_panel.grid(row=2, column=1, sticky="new", padx=(6, 0), pady=(0, 10))

        self.stat_panel = StatPanel(self.body, player, window.handle_game_change)
        self.stat_panel.grid(row=3, column=0, sticky="nsew", padx=(0, 6), pady=(0, 10))
        self.advanced_panel = AdvancedPanel(self.body, player, window.refresh_views)
        self.advanced_panel.grid(row=3, column=1, sticky="new", padx=(6, 0), pady=(0, 10))

        self.title_panel = TitlePanel(self.body, window.handle_game_change)
        self.title_panel.grid(row=4, column=0, columnspan=2, sticky="ew")

        self.equipment_panel = ctk.CTkFrame(self.body, fg_color="#20212a", corner_radius=16)
        self.equipment_panel.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        self.equipment_panel.grid_columnconfigure(0, weight=1)
        self.equipment_label = ctk.CTkLabel(self.equipment_panel, text="EQUIPPED ITEMS", anchor="w",
                                            text_color=TEXT_COLOR, font=ctk.CTkFont(size=12, weight="bold"))
        self.equipment_label.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 2))
        self.equipment_summary = ctk.CTkLabel(self.equipment_panel, text="", anchor="w", justify="left",
                                              text_color=SECONDARY_TEXT)
        self.equipment_summary.grid(row=1, column=0, sticky="ew", padx=16, pady=(2, 12))
        ctk.CTkButton(self.equipment_panel, text="Manage Equipment", width=150,
                      command=lambda: window.show_page("inventory")).grid(row=0, column=1, rowspan=2, padx=16, pady=12)
        self.item_database = ItemDatabase.load_default()

    def refresh(self) -> None:
        player: Player = self.window.game_state.character
        for panel in (self.race_panel, self.potential_panel, self.level_panel, self.stat_panel, self.advanced_panel):
            panel.player = player
            panel.refresh()
        self.class_panel.refresh(player)
        self.race_bonus_panel.refresh(player)
        self.title_panel.refresh(player)
        entries = self.window.game_state.equipment.equipped_items
        names = []
        for entry in entries:
            definition = self.item_database.try_get(entry.item.item_id)
            names.append(f"{entry.slot_id.replace('_', ' ').title()}: {definition.name if definition else entry.item.item_id}")
        active_race = player.race if player.race_accepted else None
        base = calculate_attributes(player.stats, active_race, player.class_id)
        effective = player.calculated_attributes
        deltas = []
        for attribute in ("hp", "mp", "attack", "agility", "stamina", "physical_defense", "magical_defense",
                          "critical_chance", "critical_damage", "attack_speed", "hp_regeneration", "mp_regeneration"):
            difference = getattr(effective, attribute) - getattr(base, attribute)
            if abs(difference) > 0.00001:
                suffix = "%" if attribute == "critical_chance" else ""
                shown = difference * 100 if suffix else difference
                deltas.append(f"{attribute.replace('_', ' ').title()} +{shown:.2f}{suffix}")
        inventory_text = "  ·  ".join(names) if names else "No equipment equipped."
        bonus_text = "  ·  ".join(deltas) if deltas else "No equipment bonuses."
        self.equipment_summary.configure(text=f"{inventory_text}\nEffective equipment bonuses: {bonus_text}")
