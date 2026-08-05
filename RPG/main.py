from .core.game_state import GameState
from .ui.main_window import MainWindow


def main() -> None:
    game_state = GameState()
    window = MainWindow(game_state)
    window.mainloop()


if __name__ == "__main__":
    main()
