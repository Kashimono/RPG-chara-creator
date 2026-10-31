"""Navigation shell and application-level actions."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog

import customtkinter as ctk

from ..config import BACKGROUND_COLOR, PADDING, SECONDARY_TEXT, SURFACE_COLOR, TEXT_COLOR
from ..core.character import format_character_profile
from ..core.game_config import APP_TITLE
from ..core.game_state import GameState
from ..managers.save_manager import SaveManager
from ..managers.settings_manager import SettingsManager
from .navigation import NavigationSidebar
from .pages.character import CharacterPage
from .pages.combat import CombatPage
from .pages.dashboard import DashboardPage
from .pages.inventory import InventoryPage
from .pages.settings import SettingsPage
from .save_dialog import LoadSaveDialog
from .themes import apply_theme


class MainWindow(ctk.CTk):
    def __init__(self, game_state: GameState) -> None:
        apply_theme(game_state.game_settings.get("theme", "Dark"))
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1360x900")
        self.minsize(1100, 700)
        self.configure(fg_color=BACKGROUND_COLOR)

        self.game_state = game_state
        self.current_save_file: str | None = None
        self.is_dirty = False
        self._status_after_id: str | None = None
        self.protocol("WM_DELETE_WINDOW", self.on_exit)
        self._build_interface()
        self.refresh_views()
        self.show_page("dashboard")

    def _build_interface(self) -> None:
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)

        self.navigation = NavigationSidebar(self, self.show_page, self.new_game, self.save_game, self.load_game)
        self.navigation.grid(row=0, column=0, rowspan=2, sticky="nsew")

        header = ctk.CTkFrame(self, fg_color=SURFACE_COLOR, corner_radius=16)
        header.grid(row=0, column=1, sticky="ew", padx=PADDING, pady=(PADDING, 10))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text=APP_TITLE, anchor="w", font=ctk.CTkFont(size=18, weight="bold"), text_color=TEXT_COLOR).grid(row=0, column=0, sticky="w", padx=18, pady=(12, 0))
        self.status_label = ctk.CTkLabel(header, text="Ready", anchor="e", font=ctk.CTkFont(size=12), text_color=SECONDARY_TEXT)
        self.status_label.grid(row=0, column=1, sticky="e", padx=18, pady=(12, 0))
        self.game_status_label = ctk.CTkLabel(header, text="New game", anchor="e", font=ctk.CTkFont(size=11), text_color=SECONDARY_TEXT)
        self.game_status_label.grid(row=1, column=0, columnspan=2, sticky="e", padx=18, pady=(2, 12))

        self.page_container = ctk.CTkFrame(self, fg_color=BACKGROUND_COLOR, corner_radius=0)
        self.page_container.grid(row=1, column=1, sticky="nsew", padx=(PADDING, PADDING), pady=(0, PADDING))
        self.page_container.grid_columnconfigure(0, weight=1)
        self.page_container.grid_rowconfigure(0, weight=1)

        self.pages = {
            "dashboard": DashboardPage(self.page_container, lambda: self.game_state, self.show_page),
            "character": CharacterPage(self.page_container, self),
            "combat": CombatPage(
                self.page_container,
                lambda: self.game_state,
                self.handle_game_change,
                self.mark_game_dirty,
            ),
            "inventory": InventoryPage(self.page_container),
            "settings": SettingsPage(
                self.page_container,
                lambda: self.game_state,
                self.update_setting,
                self.reset_settings,
            ),
        }
        for page in self.pages.values():
            page.grid(row=0, column=0, sticky="nsew")

    def show_page(self, page_id: str) -> None:
        page = self.pages.get(page_id)
        if page is None:
            return
        page.tkraise()
        self.navigation.select_page(page_id)
        self.refresh_views()

    def refresh_views(self) -> None:
        for page in self.pages.values():
            refresh = getattr(page, "refresh", None)
            if callable(refresh):
                refresh()
        if self.is_dirty:
            self.game_status_label.configure(text="Unsaved changes", text_color="#e7bd65")
        elif self.current_save_file:
            self.game_status_label.configure(text=f"Saved: {self.current_save_file}", text_color="#65d16d")
        else:
            self.game_status_label.configure(text="New game", text_color=SECONDARY_TEXT)

    def handle_game_change(self) -> None:
        self.mark_game_dirty()
        self.refresh_views()

    def mark_game_dirty(self) -> None:
        self.is_dirty = True
        if hasattr(self, "game_status_label"):
            self.game_status_label.configure(text="Unsaved changes", text_color="#e7bd65")

    def new_game(self) -> None:
        if self.is_dirty and not messagebox.askyesno(
            "Confirm New Game",
            "Unsaved progress will be lost. Start a new game?",
            parent=self,
        ):
            return
        settings = dict(self.game_state.game_settings)
        self.game_state = GameState(game_settings=settings)
        self.current_save_file = None
        self.is_dirty = False
        self.refresh_views()
        self.show_status("New game started.")

    def save_game(self) -> bool:
        filename = self.current_save_file
        if filename is None:
            raw_name = simpledialog.askstring("Save As", "Enter a name for this save file:", parent=self)
            if raw_name is None:
                return False
            filename = SaveManager.normalize_filename(raw_name)

        try:
            exists = SaveManager.get_save_path(filename).exists()
        except ValueError as exc:
            messagebox.showerror("Save Error", str(exc), parent=self)
            return False
        if exists and not messagebox.askyesno(
            "Overwrite Save",
            f"A save named '{filename}' already exists. Overwrite it?",
            parent=self,
        ):
            return False

        try:
            SaveManager.save(self.game_state, filename, overwrite=exists)
        except (OSError, ValueError, FileExistsError) as exc:
            messagebox.showerror("Save Error", str(exc), parent=self)
            return False

        self.current_save_file = filename
        self.is_dirty = False
        self.refresh_views()
        self.show_status(f"Saved: {filename}")
        return True

    def load_game(self) -> None:
        if self.is_dirty and not messagebox.askyesno(
            "Discard Unsaved Changes",
            "Loading a save will discard your unsaved progress. Continue?",
            parent=self,
        ):
            return
        save_files = SaveManager.list_save_files()
        timestamps = {filename: SaveManager.get_save_timestamp(filename) for filename in save_files}
        dialog = LoadSaveDialog(self, save_files, timestamps)
        self.wait_window(dialog)
        if not dialog.result:
            return
        try:
            loaded_state = SaveManager.load(dialog.result)
        except (OSError, ValueError, FileNotFoundError) as exc:
            messagebox.showerror("Load Error", str(exc), parent=self)
            return

        was_legacy = loaded_state.loaded_from_legacy
        self.game_state = loaded_state
        self.current_save_file = dialog.result
        self.is_dirty = False
        apply_theme(self.game_state.game_settings.get("theme", "Dark"))
        self.refresh_views()
        if was_legacy:
            self.show_status(f"Loaded legacy save: {dialog.result}. It will migrate when you save.")
        else:
            self.show_status(f"Loaded: {dialog.result}")

    def copy_character_stats(self) -> None:
        player = self.game_state.character
        if not player.character_created:
            messagebox.showinfo(
                "No Character",
                "Create or load a character before copying its stats.",
                parent=self,
            )
            return
        try:
            self.clipboard_clear()
            self.clipboard_append(format_character_profile(player))
            self.update()
        except tk.TclError as exc:
            messagebox.showerror("Clipboard Error", f"Could not copy character stats.\n\n{exc}", parent=self)
            return
        self.show_status("Character stats copied to clipboard.")

    def update_setting(self, key: str, value: object) -> None:
        try:
            self.game_state.game_settings = SettingsManager.set_setting(self.game_state.game_settings, key, value)
        except (KeyError, ValueError) as exc:
            messagebox.showerror("Settings Error", str(exc), parent=self)
            return
        if key == "theme":
            apply_theme(str(value))
        self.handle_game_change()

    def reset_settings(self) -> None:
        if not messagebox.askyesno("Reset Settings", "Restore the default application preferences?", parent=self):
            return
        self.game_state.game_settings = SettingsManager.reset()
        apply_theme(self.game_state.game_settings["theme"])
        self.handle_game_change()
        self.show_status("Settings restored to defaults.")

    def show_status(self, message: str) -> None:
        if self._status_after_id:
            self.after_cancel(self._status_after_id)
        self.status_label.configure(text=message, text_color=TEXT_COLOR)
        self._status_after_id = self.after(
            3500,
            lambda: self.status_label.configure(text="Ready", text_color=SECONDARY_TEXT),
        )

    def on_exit(self) -> None:
        if self.is_dirty and not messagebox.askyesno(
            "Confirm Exit",
            "You have unsaved changes. Exit anyway?",
            parent=self,
        ):
            return
        combat_page = self.pages.get("combat")
        if combat_page is not None:
            combat_page.shutdown()
        self.destroy()
