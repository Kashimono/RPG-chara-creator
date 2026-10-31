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

        self.toggle_button = create_secondary_button(self, "Hide advanced stats", self._toggle)
        self.toggle_button.grid(row=0, column=1, padx=12, pady=(12, 6), sticky="e")

        self.visible = True
        self.details_label = section_label(self, "")
        self.details_label.grid(row=1, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 12))
        self.details_label.configure(justify="left", anchor="w")
        self.refresh()

    def _toggle(self) -> None:
        self.visible = not self.visible
        self.toggle_button.configure(text="Hide advanced stats" if self.visible else "Show advanced stats")
        self.callback_refresh()

    def refresh(self) -> None:
        if not self.visible:
            self.details_label.configure(text="Hidden multipliers and effective values remain hidden until toggled.")
            return

        attributes = self.player.calculated_attributes
        lines = ["PRIMARY ATTRIBUTES (calculated with accepted passives)"]
        for stat_name in self.player.stats:
            stat = self.player.get_stat(stat_name)
            calculated_value = getattr(attributes, stat_name.lower())
            lines.append(
                f"{stat_name:<10}Base {stat.current:>10,}  Stat x{stat.multiplier:.2f} "
                f"(cap {stat.max_multiplier:.0f}x)  Final {calculated_value:,.2f}"
            )
        lines.extend(("", "ADVANCED ATTRIBUTES"))
        lines.extend(
            (
                f"Physical Defense: {attributes.physical_defense:,.2f}",
                f"Magical Defense: {attributes.magical_defense:,.2f}",
                f"Critical Chance: {attributes.critical_chance:.2%}",
                f"Critical Damage: {attributes.critical_damage:.2f}x",
                f"Attack Speed: {attributes.attack_speed:.2f} attacks/sec",
                f"HP Regeneration: {attributes.hp_regeneration:,.2f}/sec",
                f"MP Regeneration: {attributes.mp_regeneration:,.2f}/sec",
            )
        )

        self.details_label.configure(text="\n".join(lines))
