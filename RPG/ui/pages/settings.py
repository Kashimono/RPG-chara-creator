"""Application preferences page."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

import customtkinter as ctk

from ...config import SECONDARY_TEXT, SURFACE_COLOR, TEXT_COLOR
from ...core.game_config import APP_TITLE, APP_VERSION, SUPPORTED_THEMES
from ...core.game_state import GameState


class SettingsPage(ctk.CTkFrame):
    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        get_state: Callable[[], GameState],
        change_setting: Callable[[str, object], None],
        reset_settings: Callable[[], None],
    ) -> None:
        super().__init__(parent, fg_color="transparent")
        self._get_state = get_state
        self._change_setting = change_setting
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text="Settings", anchor="w", font=ctk.CTkFont(size=26, weight="bold"), text_color=TEXT_COLOR).grid(row=0, column=0, sticky="ew", padx=28, pady=(28, 14))

        preferences = ctk.CTkFrame(self, fg_color=SURFACE_COLOR, corner_radius=18)
        preferences.grid(row=1, column=0, sticky="ew", padx=28, pady=(0, 14))
        preferences.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(preferences, text="PREFERENCES", anchor="w", font=ctk.CTkFont(size=11, weight="bold"), text_color=SECONDARY_TEXT).grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 12))
        ctk.CTkLabel(preferences, text="Appearance", anchor="w", font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT_COLOR).grid(row=1, column=0, sticky="w", padx=20, pady=(2, 0))
        ctk.CTkLabel(preferences, text="Choose the interface theme.", anchor="w", font=ctk.CTkFont(size=12), text_color=SECONDARY_TEXT).grid(row=2, column=0, sticky="w", padx=20, pady=(2, 10))
        self.theme_menu = ctk.CTkOptionMenu(preferences, values=list(SUPPORTED_THEMES), command=self._on_theme_change, width=140)
        self.theme_menu.grid(row=1, column=1, rowspan=2, sticky="e", padx=20, pady=4)

        ctk.CTkLabel(preferences, text="Sound preference", anchor="w", font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT_COLOR).grid(row=3, column=0, sticky="w", padx=20, pady=(10, 0))
        ctk.CTkLabel(preferences, text="Saved for a future sound implementation.", anchor="w", font=ctk.CTkFont(size=12), text_color=SECONDARY_TEXT).grid(row=4, column=0, sticky="w", padx=20, pady=(2, 16))
        self.sound_var = tk.BooleanVar(value=False)
        self.sound_switch = ctk.CTkSwitch(preferences, text="Enable sound", variable=self.sound_var, command=self._on_sound_change)
        self.sound_switch.grid(row=3, column=1, rowspan=2, sticky="e", padx=20, pady=10)

        info = ctk.CTkFrame(self, fg_color=SURFACE_COLOR, corner_radius=18)
        info.grid(row=2, column=0, sticky="ew", padx=28, pady=(0, 14))
        ctk.CTkLabel(info, text="APPLICATION", anchor="w", font=ctk.CTkFont(size=11, weight="bold"), text_color=SECONDARY_TEXT).pack(fill="x", padx=20, pady=(18, 8))
        ctk.CTkLabel(info, text=f"{APP_TITLE}\nVersion {APP_VERSION}\nCharacter creation, leveling, and stat allocation.", anchor="w", justify="left", font=ctk.CTkFont(size=13), text_color=TEXT_COLOR).pack(fill="x", padx=20, pady=(0, 18))

        reset = ctk.CTkFrame(self, fg_color=SURFACE_COLOR, corner_radius=18)
        reset.grid(row=3, column=0, sticky="ew", padx=28, pady=(0, 20))
        reset.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(reset, text="Reset settings", anchor="w", font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT_COLOR).grid(row=0, column=0, sticky="w", padx=20, pady=(16, 2))
        ctk.CTkLabel(reset, text="Restore the default theme and sound preference.", anchor="w", font=ctk.CTkFont(size=12), text_color=SECONDARY_TEXT).grid(row=1, column=0, sticky="w", padx=20, pady=(0, 16))
        ctk.CTkButton(reset, text="Reset", width=110, command=reset_settings).grid(row=0, column=1, rowspan=2, padx=20, pady=12)
        self.refresh()

    def _on_theme_change(self, value: str) -> None:
        self._change_setting("theme", value)

    def _on_sound_change(self) -> None:
        self._change_setting("sound_enabled", bool(self.sound_var.get()))

    def refresh(self) -> None:
        settings = self._get_state().game_settings
        self.theme_menu.set(settings.get("theme", "Dark"))
        self.sound_var.set(bool(settings.get("sound_enabled", False)))
