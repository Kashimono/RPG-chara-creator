import customtkinter as ctk
from ..core.player import Player
from ..ui.widgets import create_primary_button, section_label


class LevelPanel(ctk.CTkFrame):
    def __init__(self, parent, player: Player, callback_refresh, callback_progress=None) -> None:
        super().__init__(parent, fg_color="#171b21", corner_radius=20)
        self.player = player
        self.callback_refresh = callback_refresh
        self.callback_progress = callback_progress

        self.title = section_label(self, "Level & Progress")
        self.title.grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(12, 6))

        self.level_label = section_label(self, "Level: 0")
        self.level_label.grid(row=1, column=0, sticky="w", padx=12)

        self.exp_label = section_label(self, "EXP: 0 / 0")
        self.exp_label.grid(row=2, column=0, sticky="w", padx=12, pady=(0, 12))

        self.level_up_button = create_primary_button(self, "Level Up", self._on_level_up)
        self.level_up_button.grid(row=3, column=0, padx=12, pady=(0, 12), sticky="w")

        self.level_up_10_button = create_primary_button(self, "Level Up +10", self._on_level_up_10)
        self.level_up_10_button.grid(row=3, column=1, padx=12, pady=(0, 12), sticky="w")

    def _on_level_up(self) -> None:
        self.player.level_up(1)
        self.callback_refresh()
        if self.callback_progress:
            self.callback_progress()

    def _on_level_up_10(self) -> None:
        self.player.level_up(10)
        self.callback_refresh()
        if self.callback_progress:
            self.callback_progress()

    def refresh(self) -> None:
        summary = self.player.get_summary()
        self.level_label.configure(text=f"Level: {summary['level']}")
        self.exp_label.configure(text=f"EXP: {summary['exp']} / {summary['exp_to_next']}")
        state = "normal" if summary["character_created"] else "disabled"
        self.level_up_button.configure(state=state)
        self.level_up_10_button.configure(state=state)
