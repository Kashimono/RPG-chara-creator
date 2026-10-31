from ..config import configure_app_theme


def apply_theme(mode: str = "Dark") -> None:
    configure_app_theme(mode)
