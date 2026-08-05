import customtkinter as ctk
from typing import Dict
from ..core.player import Player
from ..ui.widgets import create_primary_button, create_secondary_button, section_label


class StatPanel(ctk.CTkFrame):
    def __init__(self, parent, player: Player, callback_refresh, callback_progress=None) -> None:
        super().__init__(parent, fg_color="#171b21", corner_radius=20)
        self.player = player
        self.callback_refresh = callback_refresh
        self.callback_progress = callback_progress
        self.stat_rows: Dict[str, Dict[str, ctk.CTkBaseClass]] = {}

        self.title = section_label(self, "Stat Allocation")
        self.title.grid(row=0, column=0, columnspan=4, sticky="w", padx=12, pady=(12, 6))

        self._build_stat_rows()

    def _build_stat_rows(self) -> None:
        for idx, stat_name in enumerate(self.player.stats):
            label = section_label(self, stat_name)
            label.grid(row=idx + 1, column=0, sticky="w", padx=(12, 8), pady=8)

            value_label = section_label(self, "0")
            value_label.grid(row=idx + 1, column=1, padx=8)

            amount_entry = ctk.CTkEntry(self, width=60, placeholder_text="amt")
            amount_entry.grid(row=idx + 1, column=2, padx=8)
            amount_entry.insert(0, "1")

            plus_button = create_secondary_button(self, "+", lambda name=stat_name: self._on_allocate(name), width=62)
            plus_button.grid(row=idx + 1, column=3, padx=8)

            allocate_button = create_primary_button(self, "Alloc", lambda name=stat_name: self._on_allocate_custom(name), width=80)
            allocate_button.grid(row=idx + 1, column=4, padx=(8, 12))

            self.stat_rows[stat_name] = {
                "value_label": value_label,
                "amount_entry": amount_entry,
                "plus_button": plus_button,
                "allocate_button": allocate_button,
            }

    def _on_allocate(self, stat_name: str) -> None:
        self.player.allocate_point(stat_name)
        self.callback_refresh()
        if self.callback_progress:
            self.callback_progress()

    def _on_allocate_custom(self, stat_name: str) -> None:
        row = self.stat_rows[stat_name]
        entry_text = row["amount_entry"].get().strip()
        try:
            amount = max(1, int(entry_text))
        except ValueError:
            amount = 1
            row["amount_entry"].delete(0, ctk.END)
            row["amount_entry"].insert(0, "1")

        self.player.allocate_points(stat_name, amount)
        self.callback_refresh()
        if self.callback_progress:
            self.callback_progress()

    def refresh(self) -> None:
        for stat_name, row in self.stat_rows.items():
            stat = self.player.get_stat(stat_name)
            row["value_label"].configure(text=str(stat.current))
            row["plus_button"].configure(state="normal" if self.player.can_allocate(stat_name, 1) else "disabled")
            row["allocate_button"].configure(state="normal" if self.player.can_allocate(stat_name, 1) else "disabled")
