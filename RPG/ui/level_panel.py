"""Character overview, EXP progress, and explicitly marked test controls."""

from __future__ import annotations

import customtkinter as ctk

from ..core.player import Player
from ..ui.widgets import create_primary_button, section_label


class LevelPanel(ctk.CTkFrame):
    def __init__(self, parent, player: Player, callback_refresh, callback_progress=None) -> None:
        super().__init__(parent, fg_color="#171b21", corner_radius=20)
        self.player = player
        self.callback_refresh = callback_refresh
        self.callback_progress = callback_progress
        self.grid_columnconfigure((0, 1, 2), weight=1)

        section_label(self, "Character Overview & EXP").grid(
            row=0, column=0, columnspan=3, sticky="w", padx=12, pady=(12, 6)
        )
        self.level_label = section_label(self, "Level: 0")
        self.level_label.grid(row=1, column=0, sticky="w", padx=12, pady=(0, 4))
        self.exp_label = section_label(self, "EXP: 0 / 100")
        self.exp_label.grid(row=1, column=1, columnspan=2, sticky="e", padx=12, pady=(0, 4))

        self.exp_bar = ctk.CTkProgressBar(self, height=14, corner_radius=8)
        self.exp_bar.grid(row=2, column=0, columnspan=3, sticky="ew", padx=12, pady=(2, 8))
        self.exp_bar.set(0)

        self.profile_label = section_label(self, "Race: -   |   Class: Unselected   |   Title: Novice")
        self.profile_label.grid(row=3, column=0, columnspan=3, sticky="w", padx=12, pady=(0, 10))

        section_label(self, "Progression testing utility: add EXP directly until gameplay rewards are introduced.").grid(
            row=4, column=0, columnspan=3, sticky="w", padx=12, pady=(0, 4)
        )
        self.exp_amount_entry = ctk.CTkEntry(
            self,
            width=120,
            placeholder_text="EXP amount",
            validate="key",
            validatecommand=(self.register(self._validate_exp_input), "%P"),
        )
        self.exp_amount_entry.grid(row=5, column=0, sticky="w", padx=12, pady=(0, 10))
        self.exp_amount_entry.insert(0, "100")
        self.gain_exp_button = create_primary_button(self, "Add EXP (test)", self._on_gain_exp, width=150)
        self.gain_exp_button.grid(row=5, column=1, sticky="w", padx=4, pady=(0, 10))

        section_label(self, "Testing utilities: direct level adjustments").grid(
            row=6, column=0, columnspan=3, sticky="w", padx=12, pady=(0, 4)
        )
        self.level_up_button = create_primary_button(self, "Level +1 (test)", self._on_level_up)
        self.level_up_button.grid(row=7, column=0, padx=12, pady=(0, 6), sticky="w")
        self.level_up_10_button = create_primary_button(self, "Level +10 (test)", self._on_level_up_10)
        self.level_up_10_button.grid(row=7, column=1, padx=12, pady=(0, 6), sticky="w")
        self.level_up_1000_button = create_primary_button(
            self, "Level +1,000 (test)", self._on_level_up_1000, width=160
        )
        self.level_up_1000_button.grid(row=7, column=2, padx=12, pady=(0, 6), sticky="w")
        self.feedback_label = section_label(self, "")
        self.feedback_label.grid(row=8, column=0, columnspan=3, sticky="w", padx=12, pady=(0, 10))

    @staticmethod
    def _validate_exp_input(proposed_value: str) -> bool:
        return proposed_value == "" or (proposed_value.isascii() and proposed_value.isdecimal())

    def _on_gain_exp(self) -> None:
        try:
            amount = int(self.exp_amount_entry.get().strip())
            levels_gained = self.player.gain_exp(amount)
        except (ValueError, TypeError):
            self.feedback_label.configure(text="Enter a positive whole-number EXP amount.")
            return
        if levels_gained:
            self.feedback_label.configure(
                text=f"Gained {amount:,} EXP and advanced {levels_gained} level(s). +{levels_gained * 10} stat points."
            )
        else:
            self.feedback_label.configure(text=f"Gained {amount:,} EXP.")
        self.callback_refresh()

    def _on_level_up(self) -> None:
        self.player.level_up(1)
        self.feedback_label.configure(text="Testing utility: +1 level and +10 stat points.")
        self.callback_refresh()
        if self.callback_progress:
            self.callback_progress()

    def _on_level_up_10(self) -> None:
        self.player.level_up(10)
        self.feedback_label.configure(text="Testing utility: +10 levels and +100 stat points.")
        self.callback_refresh()
        if self.callback_progress:
            self.callback_progress()

    def _on_level_up_1000(self) -> None:
        self.player.level_up(1000)
        self.feedback_label.configure(text="Testing utility: +1,000 levels and +10,000 stat points.")
        self.callback_refresh()
        if self.callback_progress:
            self.callback_progress()

    def refresh(self) -> None:
        summary = self.player.get_summary()
        self.level_label.configure(text=f"Level: {summary['level']:,}")
        self.exp_label.configure(text=f"EXP: {summary['exp']:,} / {summary['exp_to_next']:,}")
        ratio = summary["exp"] / max(1, summary["exp_to_next"])
        self.exp_bar.set(min(1.0, max(0.0, ratio)))

        race_name = self.player.race.name if self.player.race else self.player.race_name or "-"
        race_rarity = self.player.race.rarity_name if self.player.race else self.player.race_rarity or "-"
        selected_class = self.player.selected_class
        self.profile_label.configure(
            text=(
                f"Race: {race_name} ({race_rarity})   |   "
                f"Class: {selected_class.name if selected_class else 'Unselected'}   |   "
                f"Title: {self.player.equipped_title_name}"
            )
        )
        state = "normal" if summary["character_created"] else "disabled"
        self.level_up_button.configure(state=state)
        self.level_up_10_button.configure(state=state)
        self.level_up_1000_button.configure(state=state)
        self.gain_exp_button.configure(state=state)
        self.exp_amount_entry.configure(state=state)
