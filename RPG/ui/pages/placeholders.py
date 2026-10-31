"""Shared visual treatment for gameplay sections planned for later updates."""

from __future__ import annotations

import customtkinter as ctk

from ...config import ACCENT_COLOR, SECONDARY_TEXT, SURFACE_COLOR, TEXT_COLOR


class PlannedFeaturePage(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkBaseClass, title: str, subtitle: str, icon: str, description: str) -> None:
        super().__init__(parent, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(self, text=title, anchor="w", font=ctk.CTkFont(size=26, weight="bold"), text_color=TEXT_COLOR).grid(row=0, column=0, sticky="ew", padx=28, pady=(28, 12))

        card = ctk.CTkFrame(self, fg_color=SURFACE_COLOR, corner_radius=22)
        card.grid(row=1, column=0, sticky="nsew", padx=28, pady=(0, 28))
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(0, weight=1)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.grid(row=0, column=0, sticky="", padx=36, pady=36)
        ctk.CTkLabel(inner, text=icon, font=ctk.CTkFont(size=58), text_color=ACCENT_COLOR).pack(pady=(0, 12))
        ctk.CTkLabel(inner, text="PLANNED FEATURE", font=ctk.CTkFont(size=11, weight="bold"), text_color=ACCENT_COLOR).pack(pady=(0, 10))
        ctk.CTkLabel(inner, text=title, font=ctk.CTkFont(size=24, weight="bold"), text_color=TEXT_COLOR).pack(pady=(0, 8))
        ctk.CTkLabel(inner, text=subtitle, font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT_COLOR).pack(pady=(0, 8))
        ctk.CTkLabel(inner, text=description, justify="center", wraplength=480, font=ctk.CTkFont(size=13), text_color=SECONDARY_TEXT).pack()

