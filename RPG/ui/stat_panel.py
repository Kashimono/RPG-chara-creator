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
        self.title.grid(row=0, column=0, columnspan=6, sticky="w", padx=12, pady=(12, 6))

        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.grid(row=1, column=0, columnspan=6, sticky="nsew", padx=(8, 8), pady=(0, 8))

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.scroll_frame.grid_columnconfigure(0, weight=1)
        self.scroll_frame.grid_columnconfigure(1, weight=0)
        self.scroll_frame.grid_columnconfigure(2, weight=0)
        self.scroll_frame.grid_columnconfigure(3, weight=0)
        self.scroll_frame.grid_columnconfigure(4, weight=0)
        self.scroll_frame.grid_columnconfigure(5, weight=0)

        self._build_stat_rows()

    def _build_stat_rows(self) -> None:
        self._clear_rows()

        header_name = section_label(self.scroll_frame, "Stat")
        header_name.grid(row=0, column=0, sticky="w", padx=(12, 8), pady=(4, 8))

        header_value = section_label(self.scroll_frame, "Current")
        header_value.grid(row=0, column=1, sticky="w", padx=8, pady=(4, 8))

        header_amount = section_label(self.scroll_frame, "Alloc")
        header_amount.grid(row=0, column=2, sticky="w", padx=8, pady=(4, 8))

        header_plus = section_label(self.scroll_frame, "+")
        header_plus.grid(row=0, column=3, sticky="w", padx=8, pady=(4, 8))

        header_alloc = section_label(self.scroll_frame, "Alloc")
        header_alloc.grid(row=0, column=4, sticky="w", padx=8, pady=(4, 8))

        header_remaining = section_label(self.scroll_frame, "Remain")
        header_remaining.grid(row=0, column=5, sticky="w", padx=(8, 12), pady=(4, 8))

        for idx, stat_name in enumerate(self.player.stats, start=1):
            stat = self.player.get_stat(stat_name)
            label = section_label(self.scroll_frame, stat_name)
            label.grid(row=idx, column=0, sticky="w", padx=(12, 8), pady=6)

            value_label = section_label(self.scroll_frame, str(stat.current))
            value_label.grid(row=idx, column=1, sticky="w", padx=8, pady=6)

            amount_entry = ctk.CTkEntry(self.scroll_frame, width=60, placeholder_text="amt")
            amount_entry.grid(row=idx, column=2, padx=8, pady=6)
            amount_entry.insert(0, "1")

            plus_button = create_secondary_button(self.scroll_frame, "+", lambda name=stat_name: self._on_allocate(name), width=56)
            plus_button.grid(row=idx, column=3, padx=8, pady=6)

            allocate_button = create_primary_button(self.scroll_frame, "Alloc", lambda name=stat_name: self._on_allocate_custom(name), width=78)
            allocate_button.grid(row=idx, column=4, padx=(8, 12), pady=6)

            remaining_label = section_label(self.scroll_frame, "—")
            remaining_label.grid(row=idx, column=5, sticky="w", padx=(8, 12), pady=6)

            self.stat_rows[stat_name] = {
                "label": label,
                "value_label": value_label,
                "amount_entry": amount_entry,
                "plus_button": plus_button,
                "allocate_button": allocate_button,
                "remaining_label": remaining_label,
            }

    def _clear_rows(self) -> None:
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self.stat_rows.clear()

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
            if stat.accepted and stat.potential is not None:
                remaining = max(0, (stat.potential or 0) - stat.current)
                row["remaining_label"].configure(text=f"Rem: {remaining}")
            else:
                row["remaining_label"].configure(text="Rem: —")
            can_allocate = self.player.can_allocate(stat_name, 1)
            row["plus_button"].configure(state="normal" if can_allocate else "disabled")
            row["allocate_button"].configure(state="normal" if can_allocate else "disabled")
