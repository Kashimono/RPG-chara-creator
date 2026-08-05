import customtkinter as ctk
from typing import Dict
from ..core.player import Player
from ..ui.widgets import create_primary_button, create_secondary_button, section_label


class PotentialPanel(ctk.CTkFrame):
    def __init__(self, parent, player: Player, callback_refresh, callback_progress=None) -> None:
        super().__init__(parent, fg_color="#171b21", corner_radius=20)
        self.player = player
        self.callback_refresh = callback_refresh
        self.callback_progress = callback_progress
        self.stat_rows: Dict[str, Dict[str, ctk.CTkLabel]] = {}

        self.title = section_label(self, "Stat Potential Rolls")
        self.title.grid(row=0, column=0, columnspan=5, sticky="w", padx=12, pady=(12, 6))

        self._build_stat_rows()

    def _build_stat_rows(self) -> None:
        for idx, stat_name in enumerate(self.player.stats):
            label = section_label(self, stat_name)
            label.grid(row=idx + 1, column=0, sticky="w", padx=(12, 8), pady=8)

            value_label = section_label(self, "-")
            value_label.grid(row=idx + 1, column=1, sticky="w", padx=(0, 12))

            attempt_label = section_label(self, "0/10")
            attempt_label.grid(row=idx + 1, column=2, sticky="w", padx=(0, 12))

            roll_button = create_secondary_button(self, "Roll", lambda name=stat_name: self._on_roll(name), width=90)
            roll_button.grid(row=idx + 1, column=3, padx=8)

            accept_button = create_primary_button(self, "Accept", lambda name=stat_name: self._on_accept(name), width=90)
            accept_button.grid(row=idx + 1, column=4, padx=8)

            self.stat_rows[stat_name] = {
                "value_label": value_label,
                "attempt_label": attempt_label,
                "roll_button": roll_button,
                "accept_button": accept_button,
            }

    def _on_roll(self, stat_name: str) -> None:
        self.player.roll_stat_potential(stat_name)
        self.callback_refresh()
        if self.callback_progress:
            self.callback_progress()

    def _on_accept(self, stat_name: str) -> None:
        self.player.accept_stat_potential(stat_name)
        self.callback_refresh()
        if self.callback_progress:
            self.callback_progress()

    def refresh(self) -> None:
        for stat_name, row in self.stat_rows.items():
            stat = self.player.get_stat(stat_name)
            row["value_label"].configure(text=f"{stat.roll_value:,}" if stat.roll_value else "-")
            row["attempt_label"].configure(text=f"{stat.roll_attempts}/{stat.max_rolls}")
            row["roll_button"].configure(text="Roll Again" if stat.roll_value else "Roll")
            row["roll_button"].configure(state="disabled" if stat.accepted or not stat.can_roll else "normal")
            row["accept_button"].configure(state="normal" if stat.roll_value and not stat.accepted else "disabled")
