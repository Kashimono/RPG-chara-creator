import customtkinter as ctk
from .core.game_config import APP_TITLE

WINDOW_TITLE = APP_TITLE
WINDOW_WIDTH = 1040
WINDOW_HEIGHT = 720
PADDING = 16

FONT_BODY = ("Inter", 13)
FONT_HEADING = ("Inter", 18, "bold")
FONT_LABEL = ("Inter", 12)
FONT_BUTTON = ("Inter", 12, "bold")

BACKGROUND_COLOR = "#101215"
SURFACE_COLOR = "#171b21"
ACCENT_COLOR = "#5c80ff"
TEXT_COLOR = "#e6e9f0"
SECONDARY_TEXT = "#9aa3b8"


def configure_app_theme(mode: str = "Dark") -> None:
    ctk.set_appearance_mode(mode)
    ctk.set_default_color_theme("dark-blue")
