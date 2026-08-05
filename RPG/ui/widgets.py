import customtkinter as ctk
from ..config import ACCENT_COLOR, FONT_BUTTON, FONT_LABEL, SURFACE_COLOR, TEXT_COLOR


def section_label(parent: ctk.CTkBaseClass, text: str) -> ctk.CTkLabel:
    return ctk.CTkLabel(parent, text=text, font=FONT_BUTTON, text_color=TEXT_COLOR)


def create_primary_button(parent: ctk.CTkBaseClass, text: str, command, width: int = 140) -> ctk.CTkButton:
    return ctk.CTkButton(
        master=parent,
        text=text,
        command=command,
        fg_color=ACCENT_COLOR,
        hover_color="#7b98ff",
        text_color=TEXT_COLOR,
        corner_radius=16,
        width=width,
        height=40,
        font=FONT_BUTTON,
    )


def create_secondary_button(parent: ctk.CTkBaseClass, text: str, command, width: int = 100) -> ctk.CTkButton:
    return ctk.CTkButton(
        master=parent,
        text=text,
        command=command,
        fg_color=SURFACE_COLOR,
        hover_color="#2d3440",
        text_color=TEXT_COLOR,
        corner_radius=16,
        width=width,
        height=36,
        font=FONT_LABEL,
    )
