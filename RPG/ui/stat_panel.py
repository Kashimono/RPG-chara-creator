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

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        header_frame.grid_columnconfigure(0, weight=1)

        self.title = section_label(header_frame, "Stat Allocation")
        self.title.grid(row=0, column=0, sticky="w")

        allocation_label = section_label(header_frame, "Amount")
        allocation_label.grid(row=0, column=1, sticky="e", padx=(8, 6))

        self.allocation_amount_entry = ctk.CTkEntry(
            header_frame,
            width=76,
            justify="center",
            validate="key",
            validatecommand=(self.register(self._validate_allocation_input), "%P"),
        )
        self.allocation_amount_entry.grid(row=0, column=2, sticky="e")
        self.allocation_amount_entry.insert(0, "1")

        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 8))
        self.scroll_frame.grid_columnconfigure(0, weight=1, minsize=90)
        self.scroll_frame.grid_columnconfigure(1, weight=0, minsize=100)
        self.scroll_frame.grid_columnconfigure(2, weight=0, minsize=42)
        self.scroll_frame.grid_columnconfigure(3, weight=0, minsize=92)
        self.scroll_frame.grid_columnconfigure(4, weight=0, minsize=100)

        self._build_stat_rows()

    @staticmethod
    def _validate_allocation_input(proposed_value: str) -> bool:
        if proposed_value == "":
            return True
        return (
            proposed_value.isascii()
            and proposed_value.isdecimal()
            and any(character != "0" for character in proposed_value)
        )

    def _build_stat_rows(self) -> None:
        headers = (
            ("Stat", 0, "w"),
            ("Current", 1, "e"),
            ("+1", 2, "center"),
            ("Allocate", 3, "center"),
            ("Remain", 4, "e"),
        )
        for text, column, anchor in headers:
            label = section_label(self.scroll_frame, text)
            label.configure(anchor=anchor)
            label.grid(row=0, column=column, sticky="ew", padx=2, pady=(4, 8))

        for row_index, stat_name in enumerate(self.player.stats, start=1):
            name_label = section_label(self.scroll_frame, stat_name)
            name_label.configure(anchor="w")
            name_label.grid(row=row_index, column=0, sticky="ew", padx=2, pady=6)

            value_label = section_label(self.scroll_frame, "0")
            value_label.configure(anchor="e")
            value_label.grid(row=row_index, column=1, sticky="ew", padx=2, pady=6)

            plus_button = create_secondary_button(
                self.scroll_frame,
                "+",
                lambda name=stat_name: self._on_allocate(name),
                width=38,
            )
            plus_button.grid(row=row_index, column=2, padx=2, pady=6)

            allocate_button = create_primary_button(
                self.scroll_frame,
                "Allocate",
                lambda name=stat_name: self._on_allocate_custom(name),
                width=90,
            )
            allocate_button.grid(row=row_index, column=3, padx=2, pady=6)

            remaining_label = section_label(self.scroll_frame, "—")
            remaining_label.configure(anchor="e")
            remaining_label.grid(row=row_index, column=4, sticky="ew", padx=2, pady=6)

            self.stat_rows[stat_name] = {
                "value_label": value_label,
                "plus_button": plus_button,
                "allocate_button": allocate_button,
                "remaining_label": remaining_label,
            }

    def _on_allocate(self, stat_name: str) -> None:
        self.player.allocate_point(stat_name)
        self.callback_refresh()
        if self.callback_progress:
            self.callback_progress()

    def _on_allocate_custom(self, stat_name: str) -> None:
        entry_text = self.allocation_amount_entry.get().strip()
        try:
            requested_amount = int(entry_text)
        except ValueError:
            self._reset_allocation_amount()
            return

        if requested_amount <= 0:
            self._reset_allocation_amount()
            return

        stat = self.player.get_stat(stat_name)
        remaining_capacity = max(0, (stat.potential or 0) - stat.current)
        amount = min(requested_amount, self.player.stat_points, remaining_capacity)
        if amount > 0:
            self.player.allocate_points(stat_name, amount)

        self.callback_refresh()
        if self.callback_progress:
            self.callback_progress()

    def _reset_allocation_amount(self) -> None:
        self.allocation_amount_entry.delete(0, ctk.END)
        self.allocation_amount_entry.insert(0, "1")

    def refresh(self) -> None:
        for stat_name, row in self.stat_rows.items():
            stat = self.player.get_stat(stat_name)
            row["value_label"].configure(text=f"{stat.current:,}")
            if stat.accepted and stat.potential is not None:
                remaining = max(0, stat.potential - stat.current)
                row["remaining_label"].configure(text=f"{remaining:,}")
            else:
                row["remaining_label"].configure(text="—")

            can_allocate = self.player.can_allocate(stat_name, 1)
            row["plus_button"].configure(state="normal" if can_allocate else "disabled")
            row["allocate_button"].configure(state="normal" if can_allocate else "disabled")
