import tkinter as tk
from tkinter import messagebox, simpledialog
import customtkinter as ctk
from .themes import apply_theme
from .potential_panel import PotentialPanel
from .race_panel import RacePanel
from .stat_panel import StatPanel
from .level_panel import LevelPanel
from .advanced_panel import AdvancedPanel
from .save_dialog import LoadSaveDialog
from ..config import BACKGROUND_COLOR, FONT_BODY, FONT_HEADING, FONT_LABEL, PADDING, TEXT_COLOR
from ..core.game_state import GameState
from ..core.save_manager import SaveManager


class MainWindow(ctk.CTk):
    def __init__(self, game_state: GameState) -> None:
        super().__init__()
        apply_theme()
        self.title("RPG Stat Workshop")
        self.geometry(f"{1180}x{780}")
        self.minsize(1120, 720)
        self.configure(fg_color=BACKGROUND_COLOR)

        self.game_state = game_state
        self.player = self.game_state.player
        self.current_save_file: str | None = None
        self.is_dirty = False

        self.protocol("WM_DELETE_WINDOW", self.on_exit)

        self._build_interface()
        self.refresh()

    def _build_interface(self) -> None:
        self.grid_columnconfigure(0, weight=5)
        self.grid_columnconfigure(1, weight=4)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)

        header_frame = ctk.CTkFrame(self, fg_color="#171b21", corner_radius=20)
        header_frame.grid(row=0, column=0, columnspan=2, padx=PADDING, pady=PADDING, sticky="nsew")
        header_frame.grid_columnconfigure(0, weight=1)
        header_frame.grid_columnconfigure(1, weight=1)

        title = ctk.CTkLabel(header_frame, text="RPG Character Builder", font=FONT_HEADING, text_color=TEXT_COLOR)
        title.grid(row=0, column=0, sticky="w", padx=16, pady=(16, 4))

        subtitle = ctk.CTkLabel(header_frame,
                                text="Roll potentials, lock them in, then level up and allocate stats.",
                                font=FONT_LABEL,
                                text_color="#9aa3b8")
        subtitle.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 16))

        self.level_summary = ctk.CTkLabel(header_frame, text="Level: 0", font=FONT_BODY, text_color=TEXT_COLOR)
        self.level_summary.grid(row=0, column=1, sticky="e", padx=16)

        self.pool_summary = ctk.CTkLabel(header_frame, text="Stat Points: 0", font=FONT_BODY, text_color=TEXT_COLOR)
        self.pool_summary.grid(row=1, column=1, sticky="e", padx=16)

        self.save_status = ctk.CTkLabel(header_frame, text="", font=FONT_LABEL, text_color="#65d16d")
        self.save_status.grid(row=2, column=0, columnspan=2, sticky="w", padx=16, pady=(0, 12))

        menu_frame = ctk.CTkFrame(header_frame, fg_color="#161a20", corner_radius=14)
        menu_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 16))
        menu_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        new_game_button = ctk.CTkButton(menu_frame, text="New Game", command=self.new_game, corner_radius=12)
        new_game_button.grid(row=0, column=0, padx=6, pady=8, sticky="ew")

        save_game_button = ctk.CTkButton(menu_frame, text="Save Game", command=self.save_game, corner_radius=12)
        save_game_button.grid(row=0, column=1, padx=6, pady=8, sticky="ew")

        load_game_button = ctk.CTkButton(menu_frame, text="Load Game", command=self.load_game, corner_radius=12)
        load_game_button.grid(row=0, column=2, padx=6, pady=8, sticky="ew")

        copy_stats_button = ctk.CTkButton(
            menu_frame,
            text="Copy Character Stats",
            command=self.copy_character_stats,
            corner_radius=12,
        )
        copy_stats_button.grid(row=0, column=3, padx=6, pady=8, sticky="ew")

        exit_button = ctk.CTkButton(menu_frame, text="Exit", command=self.on_exit, corner_radius=12)
        exit_button.grid(row=0, column=4, padx=6, pady=8, sticky="ew")

        self.race_panel = RacePanel(self, self.player, self.refresh)
        self.race_panel.grid(row=1, column=0, padx=(PADDING, 8), pady=(0, PADDING), sticky="nsew")

        self.potential_panel = PotentialPanel(self, self.player, self.refresh)
        self.potential_panel.grid(row=2, column=0, padx=(PADDING, 8), pady=(0, PADDING), sticky="nsew")

        side_panel = ctk.CTkFrame(self, fg_color=BACKGROUND_COLOR, corner_radius=0)
        side_panel.grid(row=1, column=1, padx=(8, PADDING), pady=(0, PADDING), sticky="nsew")
        side_panel.grid_rowconfigure(0, weight=0)
        side_panel.grid_rowconfigure(1, weight=1)

        self.level_panel = LevelPanel(side_panel, self.player, self.refresh)
        self.level_panel.grid(row=0, column=0, sticky="ew", pady=(0, 12))

        self.stat_panel = StatPanel(side_panel, self.player, self.refresh)
        self.stat_panel.grid(row=1, column=0, sticky="nsew")

        self.advanced_panel = AdvancedPanel(side_panel, self.player, self.refresh)
        self.advanced_panel.grid(row=2, column=0, sticky="ew", pady=(12, 0))

    def refresh(self) -> None:
        self.player = self.game_state.player
        self.race_panel.player = self.player
        self.potential_panel.player = self.player
        self.level_panel.player = self.player
        self.stat_panel.player = self.player
        self.advanced_panel.player = self.player

        summary = self.player.get_summary()
        self.level_summary.configure(text=f"Level: {summary['level']}")
        self.pool_summary.configure(text=f"Stat Points: {summary['stat_points']}")
        self.race_panel.refresh()
        self.potential_panel.refresh()
        self.level_panel.refresh()
        self.stat_panel.refresh()
        self.advanced_panel.refresh()

    def new_game(self) -> None:
        if self.is_dirty:
            if not messagebox.askyesno("Confirm New Game", "Unsaved progress will be lost. Start a new game?"):
                return
        self.game_state = GameState()
        self.player = self.game_state.player
        self.current_save_file = None
        self.is_dirty = False
        self.save_status.configure(text="New game started.")
        self.refresh()

    def save_game(self) -> None:
        if self.current_save_file is None:
            raw_save_name = simpledialog.askstring(
                "Save As",
                "Enter a name for this save file:",
                parent=self,
            )
            self.current_save_file = SaveManager.normalize_filename(raw_save_name)

        SaveManager.save(self.game_state, self.current_save_file)
        self.is_dirty = False
        self.show_status(f"Saved: {self.current_save_file}")

    def load_game(self) -> None:
        save_files = SaveManager.list_save_files()
        save_timestamps = {filename: SaveManager.get_save_timestamp(filename) for filename in save_files}
        dialog = LoadSaveDialog(self, save_files, save_timestamps)
        self.wait_window(dialog)
        if not dialog.result:
            return
        try:
            self.game_state = SaveManager.load(dialog.result)
            self.player = self.game_state.player
            self.current_save_file = dialog.result
            self.is_dirty = False
            self.show_status(f"Loaded {dialog.result}")
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Load Error", str(exc))

    def copy_character_stats(self) -> None:
        player = self.game_state.player
        if not player.character_created:
            messagebox.showinfo(
                "No Character",
                "Create or load a character before copying its stats.",
                parent=self,
            )
            return

        profile = player.get_character_profile()
        stats = profile["stats"]
        profile_text = (
            "========== CHARACTER PROFILE ==========\n\n"
            f"Race: {profile['race']}\n"
            f"Rarity: {profile['rarity']}\n"
            f"Level: {profile['level']}\n\n"
            "========== CHARACTER STATS ==========\n\n"
            f"HP: {stats['HP']}\n"
            f"MP: {stats['MP']}\n"
            f"Attack: {stats['Attack']}\n"
            f"Agility: {stats['Agility']}\n"
            f"Stamina: {stats['Stamina']}\n\n"
            "======================================="
        )

        try:
            self.clipboard_clear()
            self.clipboard_append(profile_text)
            self.update()
        except tk.TclError as exc:
            messagebox.showerror("Clipboard Error", f"Could not copy character stats.\n\n{exc}", parent=self)
            return

        self.show_status("Character stats copied to clipboard.")

    def show_status(self, message: str) -> None:
        self.save_status.configure(text=message)
        self.after(2500, lambda: self.save_status.configure(text=""))

    def on_exit(self) -> None:
        if self.is_dirty:
            if not messagebox.askyesno("Confirm Exit", "You have unsaved changes. Exit anyway?"):
                return
        self.destroy()
