"""Character builder page composed from the existing feature panels."""

from __future__ import annotations

import customtkinter as ctk

from ...config import SECONDARY_TEXT, TEXT_COLOR
from ...core.player import Player
from ..advanced_panel import AdvancedPanel
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

        left = ctk.CTkFrame(self.body, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        left.grid_columnconfigure(0, weight=1)
        self.race_panel = RacePanel(left, player, window.handle_game_change)
        self.race_panel.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.potential_panel = PotentialPanel(left, player, window.handle_game_change)
        self.potential_panel.grid(row=1, column=0, sticky="ew")

        right = ctk.CTkFrame(self.body, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)
        self.level_panel = LevelPanel(right, player, window.handle_game_change)
        self.level_panel.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.stat_panel = StatPanel(right, player, window.handle_game_change)
        self.stat_panel.grid(row=1, column=0, sticky="nsew")
        self.advanced_panel = AdvancedPanel(right, player, window.refresh_views)
        self.advanced_panel.grid(row=2, column=0, sticky="ew", pady=(10, 0))

    def refresh(self) -> None:
        player: Player = self.window.game_state.character
        for panel in (self.race_panel, self.potential_panel, self.level_panel, self.stat_panel, self.advanced_panel):
            panel.player = player
            panel.refresh()
