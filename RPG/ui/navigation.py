"""Persistent sidebar navigation shared by every application page."""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from ..config import ACCENT_COLOR, SECONDARY_TEXT, SURFACE_COLOR, TEXT_COLOR


class NavigationSidebar(ctk.CTkFrame):
    PAGES = (
        ("dashboard", "Dashboard"),
        ("character", "Character"),
        ("combat", "Combat"),
        ("economy", "Economy"),
        ("inventory", "Inventory"),
        ("settings", "Settings"),
    )

    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        navigate: Callable[[str], None],
        new_game: Callable[[], None],
        save_game: Callable[[], None],
        load_game: Callable[[], None],
    ) -> None:
        super().__init__(parent, width=214, corner_radius=0, fg_color="#14171c")
        self.grid_propagate(False)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(8, weight=1)
        self._navigate = navigate
        self._page_buttons: dict[str, ctk.CTkButton] = {}

        brand = ctk.CTkLabel(
            self,
            text="WORLD OF\nASCENSION",
            justify="left",
            anchor="w",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=TEXT_COLOR,
        )
        brand.grid(row=0, column=0, sticky="ew", padx=20, pady=(24, 5))
        edition = ctk.CTkLabel(self, text="RPG CHARACTER BUILDER", anchor="w", font=ctk.CTkFont(size=10), text_color=SECONDARY_TEXT)
        edition.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 24))

        for index, (page_id, label) in enumerate(self.PAGES, start=2):
            button = ctk.CTkButton(
                self,
                text=label,
                anchor="w",
                height=42,
                corner_radius=12,
                fg_color="transparent",
                hover_color="#242a34",
                text_color=TEXT_COLOR,
                command=lambda target=page_id: self._navigate(target),
            )
            button.grid(row=index, column=0, sticky="ew", padx=12, pady=3)
            self._page_buttons[page_id] = button

        actions_title = ctk.CTkLabel(self, text="GAME", anchor="w", font=ctk.CTkFont(size=11, weight="bold"), text_color=SECONDARY_TEXT)
        actions_title.grid(row=9, column=0, sticky="ew", padx=20, pady=(14, 8))
        for row, (label, command) in enumerate(
            (("New Game", new_game), ("Save Game", save_game), ("Load Game", load_game)),
            start=10,
        ):
            ctk.CTkButton(
                self,
                text=label,
                anchor="w",
                height=38,
                corner_radius=11,
                fg_color=SURFACE_COLOR,
                hover_color="#2d3440",
                text_color=TEXT_COLOR,
                command=command,
            ).grid(row=row, column=0, sticky="ew", padx=12, pady=3)

        self.select_page("dashboard")

    def select_page(self, page_id: str) -> None:
        for key, button in self._page_buttons.items():
            button.configure(fg_color=ACCENT_COLOR if key == page_id else "transparent")
