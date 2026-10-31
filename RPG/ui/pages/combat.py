"""Responsive combat screen backed by the UI-independent CombatManager."""

from __future__ import annotations

import time
from collections.abc import Callable

import customtkinter as ctk

from ...config import ACCENT_COLOR, SECONDARY_TEXT, SURFACE_COLOR, TEXT_COLOR
from ...core.game_state import GameState
from ...systems.combat import combat_config
from ...systems.combat.combat_manager import CombatActionError, CombatEvent, CombatManager, CombatState


class CombatPage(ctk.CTkFrame):
    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        get_game_state: Callable[[], GameState],
        on_change: Callable[[], None],
        on_dirty: Callable[[], None],
    ) -> None:
        super().__init__(parent, fg_color="transparent")
        self.get_game_state = get_game_state
        self.on_change = on_change
        self.on_dirty = on_dirty
        self._bound_game_state = get_game_state()
        self.manager = CombatManager(self._bound_game_state)
        self._timer_after_id: str | None = None
        self._closed = False
        self._feedback: list[str] = []

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 8))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header, text="Combat", anchor="w", font=ctk.CTkFont(size=27, weight="bold"), text_color=TEXT_COLOR,
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header,
            text="Face ordinary enemies, strike at your own pace, and earn character EXP.",
            anchor="w", font=ctk.CTkFont(size=12), text_color=SECONDARY_TEXT,
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        self.body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.body.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 16))
        self.body.grid_columnconfigure(0, weight=3, uniform="combat")
        self.body.grid_columnconfigure(1, weight=2, uniform="combat")
        self._build_enemy_panel()
        self._build_player_panel()
        self._build_feedback_panel()
        self._build_statistics_panel()
        self.refresh()

    def _build_enemy_panel(self) -> None:
        self.enemy_panel = ctk.CTkFrame(self.body, fg_color=SURFACE_COLOR, corner_radius=20)
        self.enemy_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 10))
        self.enemy_panel.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            self.enemy_panel, text="CURRENT ENCOUNTER", anchor="w",
            font=ctk.CTkFont(size=11, weight="bold"), text_color=SECONDARY_TEXT,
        ).grid(row=0, column=0, sticky="ew", padx=20, pady=(17, 5))
        self.enemy_name_label = ctk.CTkLabel(
            self.enemy_panel, text="No enemy active", anchor="w",
            font=ctk.CTkFont(size=25, weight="bold"), text_color=TEXT_COLOR,
        )
        self.enemy_name_label.grid(row=1, column=0, sticky="ew", padx=20)
        self.enemy_description_label = ctk.CTkLabel(
            self.enemy_panel, text="Start combat to face an ordinary enemy.", anchor="w", justify="left",
            wraplength=650, font=ctk.CTkFont(size=12), text_color=SECONDARY_TEXT,
        )
        self.enemy_description_label.grid(row=2, column=0, sticky="ew", padx=20, pady=(4, 12))
        self.enemy_hp_label = ctk.CTkLabel(
            self.enemy_panel, text="HP: - / -", anchor="w", font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT_COLOR,
        )
        self.enemy_hp_label.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 5))
        self.enemy_hp_bar = ctk.CTkProgressBar(self.enemy_panel, height=18, corner_radius=9, progress_color="#b74745")
        self.enemy_hp_bar.grid(row=4, column=0, sticky="ew", padx=20, pady=(0, 12))
        self.enemy_hp_bar.set(0)
        self.enemy_details_label = ctk.CTkLabel(
            self.enemy_panel,
            text="Classification: -   |   Attack: -   |   Physical Defense: -   |   Magical Defense: -   |   Interval: -   |   EXP: -",
            anchor="w", justify="left", wraplength=650, font=ctk.CTkFont(size=12), text_color=TEXT_COLOR,
        )
        self.enemy_details_label.grid(row=5, column=0, sticky="ew", padx=20, pady=(0, 14))

        selector = ctk.CTkFrame(self.enemy_panel, fg_color="transparent")
        selector.grid(row=6, column=0, sticky="ew", padx=16, pady=(0, 16))
        selector.grid_columnconfigure(0, weight=1)
        self.enemy_menu = ctk.CTkOptionMenu(
            selector,
            values=[definition.name for definition in self.manager.available_enemies],
            command=self._on_enemy_selected,
            width=150,
        )
        self.enemy_menu.grid(row=0, column=0, sticky="w", padx=4)
        self.enemy_menu.set(self.manager.available_enemies[0].name)
        self.start_button = ctk.CTkButton(
            selector, text="Start Combat", height=38, corner_radius=11,
            fg_color=ACCENT_COLOR, hover_color="#7b98ff", command=self._start_combat,
        )
        self.start_button.grid(row=0, column=1, sticky="e", padx=4)
        self.attack_button = ctk.CTkButton(
            selector, text="Attack", height=38, corner_radius=11, command=self._attack,
        )
        self.attack_button.grid(row=0, column=2, sticky="e", padx=4)
        self.retreat_button = ctk.CTkButton(
            selector, text="Retreat", height=38, corner_radius=11,
            fg_color="#555d69", hover_color="#6a7380", command=self._retreat,
        )
        self.retreat_button.grid(row=0, column=3, sticky="e", padx=4)
        self.recover_button = ctk.CTkButton(
            selector, text="Recover", height=38, corner_radius=11,
            fg_color="#45845a", hover_color="#55a36e", command=self._recover,
        )
        self.recover_button.grid(row=1, column=1, sticky="e", padx=4, pady=(8, 0))
        self.recover_button.grid_remove()

    def _build_player_panel(self) -> None:
        self.player_panel = ctk.CTkFrame(self.body, fg_color=SURFACE_COLOR, corner_radius=20)
        self.player_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=(0, 10))
        self.player_panel.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            self.player_panel, text="YOUR COMBAT STATUS", anchor="w",
            font=ctk.CTkFont(size=11, weight="bold"), text_color=SECONDARY_TEXT,
        ).grid(row=0, column=0, sticky="ew", padx=18, pady=(17, 5))
        self.player_name_label = ctk.CTkLabel(
            self.player_panel, text="Adventurer · Level 0", anchor="w",
            font=ctk.CTkFont(size=20, weight="bold"), text_color=TEXT_COLOR,
        )
        self.player_name_label.grid(row=1, column=0, sticky="ew", padx=18)
        self.player_hp_label = ctk.CTkLabel(
            self.player_panel, text="HP: - / -", anchor="w", font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT_COLOR,
        )
        self.player_hp_label.grid(row=2, column=0, sticky="ew", padx=18, pady=(10, 5))
        self.player_hp_bar = ctk.CTkProgressBar(self.player_panel, height=18, corner_radius=9, progress_color="#51a86b")
        self.player_hp_bar.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 12))
        self.player_hp_bar.set(0)
        self.player_attributes_label = ctk.CTkLabel(
            self.player_panel, text="Attack: -\nPhysical Defense: -\nCritical Chance: -\nCritical Damage: -\nAttack Speed: -\nHP Regeneration: -",
            anchor="w", justify="left", font=ctk.CTkFont(size=12), text_color=TEXT_COLOR,
        )
        self.player_attributes_label.grid(row=4, column=0, sticky="ew", padx=18, pady=(0, 17))

    def _build_feedback_panel(self) -> None:
        self.feedback_panel = ctk.CTkFrame(self.body, fg_color=SURFACE_COLOR, corner_radius=18)
        self.feedback_panel.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        self.feedback_panel.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            self.feedback_panel, text="COMBAT FEEDBACK", anchor="w",
            font=ctk.CTkFont(size=11, weight="bold"), text_color=SECONDARY_TEXT,
        ).grid(row=0, column=0, sticky="ew", padx=16, pady=(13, 4))
        self.feedback_label = ctk.CTkLabel(
            self.feedback_panel, text="Prepare your character, then start an encounter.", anchor="w", justify="left",
            font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT_COLOR,
        )
        self.feedback_label.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 7))
        self.feedback_log = ctk.CTkTextbox(self.feedback_panel, height=100, wrap="word", activate_scrollbars=False)
        self.feedback_log.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))
        self.feedback_log.configure(state="disabled")

    def _build_statistics_panel(self) -> None:
        self.statistics_panel = ctk.CTkFrame(self.body, fg_color=SURFACE_COLOR, corner_radius=18)
        self.statistics_panel.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        for column in range(3):
            self.statistics_panel.grid_columnconfigure(column, weight=1)
        ctk.CTkLabel(
            self.statistics_panel, text="COMBAT STATISTICS", anchor="w",
            font=ctk.CTkFont(size=11, weight="bold"), text_color=SECONDARY_TEXT,
        ).grid(row=0, column=0, columnspan=3, sticky="ew", padx=16, pady=(13, 6))
        self.stat_labels: dict[str, ctk.CTkLabel] = {}
        entries = (
            ("total_damage_dealt", "Damage dealt"),
            ("total_damage_received", "Damage received"),
            ("total_enemies_defeated", "Enemies defeated"),
            ("total_critical_hits", "Critical hits"),
            ("total_attacks_performed", "Attacks performed"),
            ("total_exp_earned", "Combat EXP earned"),
        )
        for index, (key, label) in enumerate(entries):
            row, column = divmod(index, 3)
            value = ctk.CTkLabel(
                self.statistics_panel, text=f"{label}: 0", anchor="w",
                font=ctk.CTkFont(size=12), text_color=TEXT_COLOR,
            )
            value.grid(row=row + 1, column=column, sticky="ew", padx=16, pady=(4, 13 if row == 1 else 4))
            self.stat_labels[key] = value

    def _on_enemy_selected(self, _name: str) -> None:
        self.refresh()

    def _selected_enemy_id(self) -> str:
        selected_name = self.enemy_menu.get()
        return next(
            definition.definition_id
            for definition in self.manager.available_enemies
            if definition.name == selected_name
        )

    def _start_combat(self) -> None:
        try:
            self._handle_event(self.manager.start_combat(self._selected_enemy_id()))
        except CombatActionError as exc:
            self._show_message(str(exc), "#e7bd65")
            self.refresh()
            return
        self.refresh()

    def _attack(self) -> None:
        try:
            event = self.manager.attack()
        except CombatActionError as exc:
            self._show_message(str(exc), "#e7bd65")
            self.refresh()
            return
        self._handle_event(event)
        if event.kind != "cooldown":
            self.on_dirty()
            if event.kind == "enemy_defeated":
                self.on_change()
            else:
                self.refresh()
        else:
            self.refresh()

    def _retreat(self) -> None:
        try:
            self._handle_event(self.manager.retreat())
        except CombatActionError as exc:
            self._show_message(str(exc), "#e7bd65")
            return
        self.refresh()

    def _recover(self) -> None:
        try:
            self._handle_event(self.manager.recover())
        except CombatActionError as exc:
            self._show_message(str(exc), "#e7bd65")
            self.refresh()
            return
        self.on_dirty()
        self.refresh()

    def _handle_event(self, event: CombatEvent) -> None:
        color = {
            "critical_hit": "#f0bf58",
            "enemy_hit": "#e27b59",
            "player_defeated": "#e45c5c",
            "enemy_defeated": "#76d28d",
            "recovered": "#76d28d",
        }.get(event.kind, TEXT_COLOR)
        self._show_message(event.message, color)

    def _show_message(self, message: str, color: str) -> None:
        self.feedback_label.configure(text=message, text_color=color)
        self._feedback.append(message)
        self._feedback = self._feedback[-8:]
        self.feedback_log.configure(state="normal")
        self.feedback_log.delete("1.0", "end")
        self.feedback_log.insert("end", "\n".join(self._feedback))
        self.feedback_log.see("end")
        self.feedback_log.configure(state="disabled")

    def refresh(self) -> None:
        if self._closed:
            return
        self._bind_game_state()
        transition = self.manager.synchronize_player()
        if transition is not None:
            self._handle_event(transition)

        player = self._bound_game_state.character
        attributes = player.calculated_attributes
        enemy = self.manager.current_enemy
        if enemy is None:
            self.enemy_name_label.configure(text="No enemy active")
            self.enemy_description_label.configure(text="Start combat to face an ordinary enemy.")
            self.enemy_hp_label.configure(text="HP: - / -")
            self.enemy_hp_bar.set(0)
            self.enemy_details_label.configure(
                text="Classification: -   |   Attack: -   |   Physical Defense: -   |   Magical Defense: -   |   Interval: -   |   EXP: -"
            )
        else:
            self.enemy_name_label.configure(text=enemy.name)
            self.enemy_description_label.configure(text=enemy.description)
            self.enemy_hp_label.configure(
                text=f"HP: {enemy.current_hp:,.1f} / {enemy.max_hp:,.1f} ({enemy.hp_ratio:.0%})"
            )
            self.enemy_hp_bar.set(enemy.hp_ratio)
            self.enemy_details_label.configure(
                text=(
                    f"Classification: {enemy.classification}   |   Attack: {enemy.attack:,.1f}   |   "
                    f"Physical Defense: {enemy.physical_defense:,.1f}   |   Magical Defense: {enemy.magical_defense:,.1f}   |   "
                    f"Interval: {enemy.attack_interval:.2f}s   |   EXP: {enemy.exp_reward:,}"
                )
            )

        maximum_hp = player.maximum_hp
        current_hp = player.current_hp
        self.player_name_label.configure(text=f"{player.character_name} · Level {player.level:,}")
        player_hp_ratio = min(1.0, max(0.0, current_hp / maximum_hp)) if maximum_hp else 0.0
        self.player_hp_label.configure(
            text=f"HP: {current_hp:,.1f} / {maximum_hp:,.1f} ({player_hp_ratio:.0%})"
        )
        self.player_hp_bar.set(player_hp_ratio)
        self.player_attributes_label.configure(
            text=(
                f"Attack: {attributes.attack:,.2f}\n"
                f"Physical Defense: {attributes.physical_defense:,.2f}\n"
                f"Critical Chance: {attributes.critical_chance:.2%}\n"
                f"Critical Damage: {attributes.critical_damage:.2f}x\n"
                f"Attack Speed: {attributes.attack_speed:.2f} attacks/sec\n"
                f"HP Regeneration: {attributes.hp_regeneration:,.2f}/sec"
            )
        )

        stats = self._bound_game_state.combat_statistics
        stat_values = {
            "total_damage_dealt": f"{stats.total_damage_dealt:,.1f}",
            "total_damage_received": f"{stats.total_damage_received:,.1f}",
            "total_enemies_defeated": f"{stats.total_enemies_defeated:,}",
            "total_critical_hits": f"{stats.total_critical_hits:,}",
            "total_attacks_performed": f"{stats.total_attacks_performed:,}",
            "total_exp_earned": f"{stats.total_exp_earned:,}",
        }
        labels = {
            "total_damage_dealt": "Damage dealt",
            "total_damage_received": "Damage received",
            "total_enemies_defeated": "Enemies defeated",
            "total_critical_hits": "Critical hits",
            "total_attacks_performed": "Attacks performed",
            "total_exp_earned": "Combat EXP earned",
        }
        for key, value in stat_values.items():
            self.stat_labels[key].configure(text=f"{labels[key]}: {value}")

        state = self.manager.state
        ready_character = player.character_created and maximum_hp > 0 and attributes.attack > 0
        self.start_button.configure(state="normal" if state is CombatState.IDLE and ready_character else "disabled")
        self.enemy_menu.configure(state="normal" if state is CombatState.IDLE else "disabled")
        can_attack = state is CombatState.ACTIVE and self.manager.attack_cooldown_remaining() <= 0
        self.attack_button.configure(state="normal" if can_attack else "disabled")
        self.retreat_button.configure(
            state="normal" if state in {CombatState.ACTIVE, CombatState.ENEMY_DEFEATED} else "disabled"
        )
        if state is CombatState.PLAYER_DEFEATED:
            self.recover_button.grid()
        else:
            self.recover_button.grid_remove()
        if not ready_character and state is CombatState.IDLE:
            self.enemy_description_label.configure(
                text=(
                    "Create a character, use its EXP or level testing controls to earn stat points, "
                    "then allocate at least one point to HP and Attack on the Character page."
                )
            )
        self._ensure_scheduler()

    def _on_timer(self) -> None:
        self._timer_after_id = None
        if self._closed:
            return
        result = self.manager.tick(now=time.monotonic())
        for event in result.events:
            self._handle_event(event)
        if result.changed:
            self.on_dirty()
        self.refresh()
        self._ensure_scheduler()

    def _ensure_scheduler(self) -> None:
        should_run = not self._closed and self.manager.is_running and self.winfo_exists()
        if should_run and self._timer_after_id is None:
            self._timer_after_id = self.after(combat_config.UI_COMBAT_TICK_MS, self._on_timer)
        elif not should_run and self._timer_after_id is not None:
            try:
                self.after_cancel(self._timer_after_id)
            except Exception:
                pass
            self._timer_after_id = None

    def _bind_game_state(self) -> None:
        current = self.get_game_state()
        if current is self._bound_game_state:
            return
        self._cancel_scheduler()
        self._bound_game_state = current
        self.manager = CombatManager(current)
        self._feedback.clear()
        self.feedback_log.configure(state="normal")
        self.feedback_log.delete("1.0", "end")
        self.feedback_log.configure(state="disabled")
        self.feedback_label.configure(text="Combat session reset for the loaded character.", text_color=TEXT_COLOR)

    def _cancel_scheduler(self) -> None:
        if self._timer_after_id is not None:
            try:
                self.after_cancel(self._timer_after_id)
            except Exception:
                pass
            self._timer_after_id = None

    def shutdown(self) -> None:
        self._closed = True
        self._cancel_scheduler()

    def destroy(self) -> None:
        self.shutdown()
        super().destroy()
