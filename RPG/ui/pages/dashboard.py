"""Landing page summarizing the active character and linking to game areas."""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from ...config import ACCENT_COLOR, SECONDARY_TEXT, SURFACE_COLOR, TEXT_COLOR
from ...core.game_state import GameState


class DashboardPage(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkBaseClass, get_state: Callable[[], GameState], navigate: Callable[[str], None]) -> None:
        super().__init__(parent, fg_color="transparent")
        self._get_state = get_state
        self._navigate = navigate
        self.grid_columnconfigure(0, weight=1)

        self.heading = ctk.CTkLabel(self, text="Dashboard", anchor="w", font=ctk.CTkFont(size=28, weight="bold"), text_color=TEXT_COLOR)
        self.heading.grid(row=0, column=0, sticky="ew", padx=28, pady=(28, 2))
        ctk.CTkLabel(self, text="Your journey through the World of Ascension begins here.", anchor="w", font=ctk.CTkFont(size=13), text_color=SECONDARY_TEXT).grid(row=1, column=0, sticky="ew", padx=28, pady=(0, 20))

        hero = ctk.CTkFrame(self, fg_color=SURFACE_COLOR, corner_radius=20)
        hero.grid(row=2, column=0, sticky="ew", padx=28, pady=(0, 16))
        hero.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(hero, text="ACTIVE CHARACTER", anchor="w", font=ctk.CTkFont(size=11, weight="bold"), text_color=SECONDARY_TEXT).grid(row=0, column=0, sticky="ew", padx=22, pady=(20, 2))
        self.name_label = ctk.CTkLabel(hero, text="Adventurer", anchor="w", font=ctk.CTkFont(size=26, weight="bold"), text_color=TEXT_COLOR)
        self.name_label.grid(row=1, column=0, sticky="ew", padx=22)
        self.race_label = ctk.CTkLabel(hero, text="No race rolled", anchor="w", font=ctk.CTkFont(size=14), text_color=SECONDARY_TEXT)
        self.race_label.grid(row=2, column=0, sticky="ew", padx=22, pady=(2, 20))

        cards = ctk.CTkFrame(self, fg_color="transparent")
        cards.grid(row=3, column=0, sticky="ew", padx=22, pady=(0, 16))
        for index in range(3):
            cards.grid_columnconfigure(index, weight=1)
        self.level_value = self._summary_card(cards, 0, "LEVEL", "0")
        self.points_value = self._summary_card(cards, 1, "STAT POINTS", "0")
        self.rarity_value = self._summary_card(cards, 2, "RACE RARITY", "—")

        summary = ctk.CTkFrame(self, fg_color=SURFACE_COLOR, corner_radius=20)
        summary.grid(row=4, column=0, sticky="ew", padx=28, pady=(0, 16))
        ctk.CTkLabel(summary, text="CHARACTER SUMMARY", anchor="w", font=ctk.CTkFont(size=12, weight="bold"), text_color=SECONDARY_TEXT).pack(fill="x", padx=20, pady=(18, 6))
        self.summary_label = ctk.CTkLabel(summary, text="Roll and accept a race, then choose stat potentials to create your character.", anchor="w", justify="left", font=ctk.CTkFont(size=14), text_color=TEXT_COLOR)
        self.summary_label.pack(fill="x", padx=20, pady=(0, 18))

        quick = ctk.CTkFrame(self, fg_color="transparent")
        quick.grid(row=5, column=0, sticky="ew", padx=28, pady=(2, 24))
        ctk.CTkLabel(quick, text="QUICK ACCESS", anchor="w", font=ctk.CTkFont(size=12, weight="bold"), text_color=SECONDARY_TEXT).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))
        for index, (label, page) in enumerate((("Open Character", "character"), ("Combat", "combat"), ("Inventory", "inventory"))):
            ctk.CTkButton(quick, text=label, height=42, corner_radius=12, fg_color=ACCENT_COLOR if index == 0 else SURFACE_COLOR, hover_color="#7b98ff" if index == 0 else "#2d3440", command=lambda target=page: self._navigate(target)).grid(row=1, column=index, sticky="ew", padx=(0 if index == 0 else 8, 8), pady=2)
            quick.grid_columnconfigure(index, weight=1)
        self.refresh()

    @staticmethod
    def _summary_card(parent: ctk.CTkBaseClass, column: int, title: str, value: str) -> ctk.CTkLabel:
        card = ctk.CTkFrame(parent, fg_color=SURFACE_COLOR, corner_radius=16)
        card.grid(row=0, column=column, sticky="ew", padx=6, pady=2)
        ctk.CTkLabel(card, text=title, anchor="w", font=ctk.CTkFont(size=10, weight="bold"), text_color=SECONDARY_TEXT).pack(fill="x", padx=16, pady=(15, 2))
        value_label = ctk.CTkLabel(card, text=value, anchor="w", font=ctk.CTkFont(size=21, weight="bold"), text_color=TEXT_COLOR)
        value_label.pack(fill="x", padx=16, pady=(0, 15))
        return value_label

    def refresh(self) -> None:
        player = self._get_state().character
        race = player.race
        race_name = race.name if race else "No race rolled"
        rarity = race.rarity_name if race else "—"
        self.name_label.configure(text=player.character_name or "Adventurer")
        self.race_label.configure(text=f"{race_name}  ·  {rarity}" if race else race_name, text_color=race.text_color if race else SECONDARY_TEXT)
        self.level_value.configure(text=str(player.level))
        self.points_value.configure(text=f"{player.stat_points:,}")
        self.rarity_value.configure(text=rarity)
        if player.character_created:
            stats = "   ·   ".join(f"{name} {stat.current:,}" for name, stat in player.stats.items())
            self.summary_label.configure(text=f"Level {player.level:,} character with {player.stat_points:,} unspent stat points.\n{stats}")
        elif player.race_accepted:
            self.summary_label.configure(text="Race accepted. Roll and accept a potential for each stat to finish character creation.")
        elif race:
            self.summary_label.configure(text="Review the rolled race and accept it to unlock stat potential rolls.")
        else:
            self.summary_label.configure(text="Roll and accept a race, then choose stat potentials to create your character.")
