from tkinter import messagebox
import customtkinter as ctk
from ..core.player import Player
from ..core.race import RaceDatabase, RaceManager, Rarity
from ..core.race_pity import RacePityManager
from ..ui.widgets import create_primary_button, create_secondary_button, section_label


class RacePanel(ctk.CTkFrame):
    def __init__(self, parent, player: Player, callback_refresh) -> None:
        super().__init__(parent, fg_color="#171b21", corner_radius=20)
        self.player = player
        self.callback_refresh = callback_refresh

        self.title = section_label(self, "Race Selection")
        self.title.grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(12, 10))

        self.name_label = section_label(self, "Current Race: None")
        self.name_label.grid(row=1, column=0, sticky="w", padx=12, pady=6)

        self.rarity_label = section_label(self, "Current Rarity: -")
        self.rarity_label.grid(row=2, column=0, sticky="w", padx=12, pady=6)

        self.range_label = section_label(self, "Potential Range: -")
        self.range_label.grid(row=3, column=0, sticky="w", padx=12, pady=6)

        self.multiplier_label = section_label(self, "Maximum Multiplier: -")
        self.multiplier_label.grid(row=4, column=0, sticky="w", padx=12, pady=6)

        self.status_label = section_label(self, "Roll a race to begin.")
        self.pity_label = section_label(self, "Race Rolls: 0")
        self.pity_label.grid(row=8, column=0, columnspan=3, sticky="w", padx=12, pady=(0, 4))

        self.mythical_pity_label = section_label(self, "Mythical Pity: 0 / 100")
        self.mythical_pity_label.grid(row=9, column=0, columnspan=3, sticky="w", padx=12, pady=0)

        self.primordial_pity_label = section_label(self, "Primordial Pity: 0 / 1000")
        self.primordial_pity_label.grid(row=10, column=0, columnspan=3, sticky="w", padx=12, pady=(0, 10))
        self.status_label.grid(row=5, column=0, columnspan=2, sticky="w", padx=12, pady=(6, 10))

        self.roll_button = create_secondary_button(self, "Roll Race", self._on_roll, width=120)
        self.roll_button.grid(row=6, column=0, padx=(12, 8), pady=(0, 12), sticky="w")

        self.info_button = create_secondary_button(self, "Race Info ▼", self._show_info, width=120)
        self.info_button.grid(row=6, column=1, padx=(8, 12), pady=(0, 12), sticky="w")

        self.accept_button = create_primary_button(self, "Accept Race", self._on_accept, width=120)
        self.accept_button.grid(row=6, column=2, padx=(8, 12), pady=(0, 12), sticky="e")

        self.debug_button = create_secondary_button(self, "Debug", self._show_debug, width=120)
        self.debug_button.grid(row=7, column=0, columnspan=3, padx=12, pady=(0, 8), sticky="w")

    def _on_roll(self) -> None:
        if self._requires_confirmation():
            confirm = messagebox.askyesno("Confirm Reroll", f"You currently possess a {self.player.race.rarity_name} race.\n\nRolling again will permanently discard your current race.\n\nAre you sure you want to reroll?")
            if not confirm:
                return

        self.player.roll_race()
        self.callback_refresh()

    def _on_accept(self) -> None:
        self.player.accept_race()
        self.callback_refresh()

    def _show_info(self) -> None:
        dialog = ctk.CTkToplevel(self)
        dialog.title("Race Information")
        dialog.geometry("700x500")
        dialog.transient(self.winfo_toplevel())

        scroll = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=12, pady=12)

        header = section_label(scroll, "Official Drop Rates")
        header.grid(row=0, column=0, sticky="w", padx=8, pady=(4, 8))

        row_index = 1
        for rarity in [Rarity.COMMON, Rarity.UNCOMMON, Rarity.RARE, Rarity.EPIC, Rarity.LEGENDARY, Rarity.MYTHICAL, Rarity.PRIMORDIAL]:
            rate = Rarity.probability_table()[rarity]
            label = section_label(scroll, f"{rarity.value:<12} {rate:>6.2f}%")
            label.grid(row=row_index, column=0, sticky="w", padx=12, pady=2)
            row_index += 1

        total = section_label(scroll, f"Total: {sum(Rarity.probability_table().values()):.2f}%")
        total.grid(row=row_index, column=0, sticky="w", padx=12, pady=(8, 6))
        row_index += 1

        database = RaceDatabase()
        for rarity in [Rarity.COMMON, Rarity.UNCOMMON, Rarity.RARE, Rarity.EPIC, Rarity.LEGENDARY, Rarity.MYTHICAL, Rarity.PRIMORDIAL]:
            races = database.get_races_by_rarity(rarity)
            header = section_label(scroll, f"{rarity.value} ({len(races)})")
            header.grid(row=row_index, column=0, sticky="w", padx=8, pady=(10, 4))
            header.configure(text_color=rarity.color_hex)
            row_index += 1
            for race in races:
                detail = section_label(scroll, f"• {race.name} — Potential: {race.potential_range} | Max Multiplier: {race.max_multiplier}x")
                detail.grid(row=row_index, column=0, sticky="w", padx=(16, 8), pady=2)
                row_index += 1

    def _show_debug(self) -> None:
        debug_manager = RacePityManager()
        counts = {rarity: 0 for rarity in Rarity}
        for _ in range(100_000):
            base_rarity = RaceManager.roll_rarity()
            final_rarity = debug_manager.resolve_rarity(base_rarity)
            counts[final_rarity] += 1

        dialog = ctk.CTkToplevel(self)
        dialog.title("Race Roll Debug")
        dialog.geometry("400x420")
        dialog.transient(self.winfo_toplevel())

        scroll = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=12, pady=12)

        title = section_label(scroll, "100,000 simulated rolls")
        title.grid(row=0, column=0, sticky="w", padx=8, pady=(4, 8))

        row_index = 1
        for rarity in [Rarity.COMMON, Rarity.UNCOMMON, Rarity.RARE, Rarity.EPIC, Rarity.LEGENDARY, Rarity.MYTHICAL, Rarity.PRIMORDIAL]:
            percentage = counts[rarity] / 100_000 * 100
            label = section_label(scroll, f"{rarity.value}: {counts[rarity]:,} ({percentage:.2f}%)")
            label.grid(row=row_index, column=0, sticky="w", padx=12, pady=2)
            row_index += 1

    def _requires_confirmation(self) -> bool:
        return self.player.race is not None and self.player.race.rarity in {Rarity.LEGENDARY, Rarity.MYTHICAL, Rarity.PRIMORDIAL}

    def refresh(self) -> None:
        race = self.player.race
        if race is None:
            self.name_label.configure(text="Current Race: None")
            self.rarity_label.configure(text="Current Rarity: -")
            self.range_label.configure(text="Potential Range: -")
            self.multiplier_label.configure(text="Maximum Multiplier: -")
            self.status_label.configure(text="Roll a race to begin.")
            self.roll_button.configure(state="normal")
            self.accept_button.configure(state="disabled")
            return

        color = self.player.race_text_color or race.text_color
        self.name_label.configure(text=f"Current Race: {race.name}", text_color=color)
        self.rarity_label.configure(text=f"Current Rarity: {race.rarity_name}", text_color=color)
        self.range_label.configure(text=f"Potential Range: {race.potential_range}", text_color=color)
        self.multiplier_label.configure(text=f"Maximum Multiplier: {race.max_multiplier}x", text_color=color)
        self.pity_label.configure(text=f"Race Rolls: {self.player.race_pity.total_race_rolls}")
        self.mythical_pity_label.configure(text=f"Mythical Pity: {self.player.race_pity.mythical_pity_counter} / 100")
        self.primordial_pity_label.configure(text=f"Primordial Pity: {self.player.race_pity.primordial_pity_counter} / 1000")

        if self.player.race_accepted:
            self.status_label.configure(text="Race accepted. Stat potentials are now unlocked.")
            self.roll_button.configure(state="disabled")
            self.accept_button.configure(state="disabled")
        else:
            self.status_label.configure(text="Review the race and accept it to unlock stat potentials.")
            self.roll_button.configure(state="normal")
            self.accept_button.configure(state="normal")
