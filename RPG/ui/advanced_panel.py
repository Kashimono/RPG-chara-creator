import customtkinter as ctk
from ..core.player import Player
from ..ui.widgets import create_secondary_button, section_label


class AdvancedPanel(ctk.CTkFrame):
    def __init__(self, parent, player: Player, callback_refresh) -> None:
        super().__init__(parent, fg_color="#171b21", corner_radius=20)
        self.player = player
        self.callback_refresh = callback_refresh

        self.title = section_label(self, "Advanced Stats")
        self.title.grid(row=0, column=0, sticky="w", padx=12, pady=(12, 6))

        self.toggle_button = create_secondary_button(self, "Show advanced stats", self._toggle)
        self.toggle_button.grid(row=0, column=1, padx=12, pady=(12, 6), sticky="e")

        self.visible = False
        self.details_label = section_label(self, "Hidden multipliers and effective values remain hidden until toggled.")
        self.details_label.grid(row=1, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 12))

    def _toggle(self) -> None:
        self.visible = not self.visible
        self.toggle_button.configure(text="Hide advanced stats" if self.visible else "Show advanced stats")
        self.callback_refresh()

    def refresh(self) -> None:
        if not self.visible:
            self.details_label.configure(text="Hidden multipliers and effective values remain hidden until toggled.")
            return

        lines = ["Stat       Multiplier   Maximum   Effective"]
        lines.append("-------------------------------------------")
        for stat_name in self.player.stats:
            stat = self.player.get_stat(stat_name)
            lines.append(f"{stat_name:<10}{stat.multiplier:>10.2f}x   {stat.max_multiplier:>7.0f}x   {stat.effective_value:>10.2f}")

        self.details_label.configure(text="\n".join(lines))
