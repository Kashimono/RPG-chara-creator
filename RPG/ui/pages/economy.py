"""Economy overview, potential-aware training shop, and recent transactions."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

import customtkinter as ctk
from tkinter import messagebox

from ...config import ACCENT_COLOR, SECONDARY_TEXT, SURFACE_COLOR, TEXT_COLOR
from ...core.game_state import GameState
from ...systems.economy.currency import format_currency
from ...systems.economy.economy_config import EconomyConfig, TrainingDefinition
from ...systems.economy.economy_manager import EconomyManager
from ...systems.economy.training_shop import TrainingShop


class EconomyPage(ctk.CTkFrame):
    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        get_game_state: Callable[[], GameState],
        on_change: Callable[[], None],
    ) -> None:
        super().__init__(parent, fg_color="transparent")
        self._get_game_state = get_game_state
        self._on_change = on_change
        self._config = EconomyConfig.load_default()
        self._bound_state: GameState | None = None
        self._manager: EconomyManager | None = None
        self._shop: TrainingShop | None = None
        self._training_rows: dict[str, tuple[ctk.CTkLabel, ctk.CTkButton]] = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 8))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="Economy", anchor="w", font=ctk.CTkFont(size=27, weight="bold"), text_color=TEXT_COLOR).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(header, text="Earn Gold in combat and invest it in character training.", anchor="w", font=ctk.CTkFont(size=12), text_color=SECONDARY_TEXT).grid(row=1, column=0, sticky="w", pady=(2, 0))

        self.body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.body.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 14))
        self.body.grid_columnconfigure(0, weight=1)
        self._build_overview()
        self._build_shop()
        self._build_history()
        self.refresh()

    def _build_overview(self) -> None:
        section = ctk.CTkFrame(self.body, fg_color=SURFACE_COLOR, corner_radius=18)
        section.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        for index in range(4):
            section.grid_columnconfigure(index, weight=1)
        ctk.CTkLabel(section, text="CURRENCY OVERVIEW", anchor="w", font=ctk.CTkFont(size=11, weight="bold"), text_color=SECONDARY_TEXT).grid(row=0, column=0, columnspan=4, sticky="ew", padx=18, pady=(14, 7))
        self.balance_label = self._overview_value(section, 0, "CURRENT GOLD")
        self.earned_label = self._overview_value(section, 1, "TOTAL EARNED")
        self.spent_label = self._overview_value(section, 2, "TOTAL SPENT")
        self.purchases_label = self._overview_value(section, 3, "PURCHASES")

    @staticmethod
    def _overview_value(parent: ctk.CTkFrame, column: int, title: str) -> ctk.CTkLabel:
        card = ctk.CTkFrame(parent, fg_color="#20252d", corner_radius=13)
        card.grid(row=1, column=column, sticky="ew", padx=7, pady=(0, 14))
        ctk.CTkLabel(card, text=title, anchor="w", font=ctk.CTkFont(size=9, weight="bold"), text_color=SECONDARY_TEXT).pack(fill="x", padx=11, pady=(10, 1))
        value = ctk.CTkLabel(card, text="0", anchor="w", font=ctk.CTkFont(size=17, weight="bold"), text_color=TEXT_COLOR)
        value.pack(fill="x", padx=11, pady=(0, 10))
        return value

    def _build_shop(self) -> None:
        section = ctk.CTkFrame(self.body, fg_color=SURFACE_COLOR, corner_radius=18)
        section.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        section.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(section, text="CHARACTER TRAINING", anchor="w", font=ctk.CTkFont(size=12, weight="bold"), text_color=SECONDARY_TEXT).grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 2))
        ctk.CTkLabel(section, text="Training uses accepted stat potential and does not spend level-earned stat points.", anchor="w", font=ctk.CTkFont(size=11), text_color=SECONDARY_TEXT).grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 8))
        for index, training in enumerate(self._config.trainings, start=2):
            self._build_training_row(section, training, index)

    def _build_training_row(self, parent: ctk.CTkFrame, training: TrainingDefinition, row: int) -> None:
        container = ctk.CTkFrame(parent, fg_color="#20252d", corner_radius=13)
        container.grid(row=row, column=0, sticky="ew", padx=12, pady=4)
        container.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(container, text=training.name, anchor="w", font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT_COLOR).grid(row=0, column=0, sticky="ew", padx=13, pady=(9, 0))
        ctk.CTkLabel(container, text=f"{training.description}   +{training.stat_points} {training.stat_name}", anchor="w", justify="left", wraplength=560, font=ctk.CTkFont(size=11), text_color=SECONDARY_TEXT).grid(row=1, column=0, sticky="ew", padx=13, pady=(1, 8))
        status = ctk.CTkLabel(container, text="", anchor="w", font=ctk.CTkFont(size=10), text_color="#e7bd65")
        status.grid(row=2, column=0, sticky="ew", padx=13, pady=(0, 8))
        button = ctk.CTkButton(
            container,
            text=f"Train · {format_currency(training.cost)}",
            width=150,
            height=36,
            corner_radius=10,
            fg_color=ACCENT_COLOR,
            hover_color="#7b98ff",
            command=lambda training_id=training.training_id: self._purchase(training_id),
        )
        button.grid(row=0, column=1, rowspan=3, sticky="e", padx=12, pady=10)
        self._training_rows[training.training_id] = (status, button)

    def _build_history(self) -> None:
        section = ctk.CTkFrame(self.body, fg_color=SURFACE_COLOR, corner_radius=18)
        section.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        section.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(section, text="RECENT TRANSACTIONS", anchor="w", font=ctk.CTkFont(size=12, weight="bold"), text_color=SECONDARY_TEXT).grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 7))
        self.history = ctk.CTkTextbox(section, height=190, wrap="word", activate_scrollbars=False)
        self.history.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 12))
        self.history.configure(state="disabled")

    def refresh(self) -> None:
        state = self._get_game_state()
        self._bind_state(state)
        account = self._manager.get_account()
        economy = state.economy
        self.balance_label.configure(text=format_currency(account.balance))
        self.earned_label.configure(text=format_currency(account.total_earned))
        self.spent_label.configure(text=format_currency(account.total_spent))
        self.purchases_label.configure(text=f"{economy.total_successful_purchases:,}")
        for training in self._config.trainings:
            result = self._shop.can_purchase(training.training_id)
            status, button = self._training_rows[training.training_id]
            status.configure(text="Ready" if result.success else result.message, text_color="#76d28d" if result.success else "#e7bd65")
            button.configure(state="normal" if result.success else "disabled")
        self._refresh_history()

    def _bind_state(self, state: GameState) -> None:
        if self._bound_state is state:
            return
        self._bound_state = state
        self._manager = EconomyManager(state, config=self._config)
        self._shop = TrainingShop(state, self._manager, self._config)

    def _purchase(self, training_id: str) -> None:
        result = self._shop.can_purchase(training_id)
        if not result.success:
            messagebox.showwarning("Training unavailable", result.message, parent=self)
            self.refresh()
            return
        if not messagebox.askyesno(
            "Confirm training",
            f"Spend {format_currency(result.cost)} on {training_id.replace('_', ' ').title()}?",
            parent=self,
        ):
            return
        result = self._shop.purchase(training_id)
        if result.success:
            self._on_change()
            messagebox.showinfo("Training complete", result.message, parent=self)
        else:
            messagebox.showwarning("Training failed", result.message, parent=self)
            self.refresh()

    def _refresh_history(self) -> None:
        rows = self._bound_state.economy.transactions[-20:]
        self.history.configure(state="normal")
        self.history.delete("1.0", "end")
        if not rows:
            self.history.insert("end", "No Gold transactions yet.")
        else:
            for transaction in reversed(rows):
                try:
                    timestamp = datetime.fromisoformat(transaction.timestamp.replace("Z", "+00:00")).astimezone().strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    timestamp = transaction.timestamp
                direction = "+" if transaction.direction.value == "earned" else "−"
                self.history.insert(
                    "end",
                    f"{timestamp}  {direction}{format_currency(transaction.amount)}  ·  {transaction.description}\n",
                )
        self.history.configure(state="disabled")


__all__ = ["EconomyPage"]
