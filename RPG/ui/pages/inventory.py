"""Inventory, equipment, item inspection, and unclaimed drop controls."""

from __future__ import annotations

from tkinter import messagebox, simpledialog

import customtkinter as ctk

from ...config import ACCENT_COLOR, SECONDARY_TEXT, SURFACE_COLOR, TEXT_COLOR
from ...core.game_state import GameState
from ...systems.equipment.equipment_manager import EquipmentManager, EquipmentOperationError
from ...systems.inventory.inventory_manager import InventoryManager, InventoryOperationError
from ...systems.inventory.item import ItemInstance


class InventoryPage(ctk.CTkFrame):
    def __init__(self, parent, get_game_state, on_change) -> None:
        super().__init__(parent, fg_color="transparent")
        self.get_game_state = get_game_state
        self.on_change = on_change
        self._bound_state: GameState | None = None
        self.inventory: InventoryManager | None = None
        self.equipment: EquipmentManager | None = None
        self.selected_instance_id: str | None = None
        self.category = "all"
        self.rarity = "all"
        self.sort_by = "name"

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=22, pady=(18, 8))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="Inventory & Equipment", anchor="w", text_color=TEXT_COLOR,
                     font=ctk.CTkFont(size=26, weight="bold")).grid(row=0, column=0, sticky="w")
        self.usage_label = ctk.CTkLabel(header, text="0 / 50 slots", anchor="e", text_color=SECONDARY_TEXT)
        self.usage_label.grid(row=0, column=1, sticky="e")

        self.body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.body.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 12))
        self.body.grid_columnconfigure(0, weight=3, uniform="inventory")
        self.body.grid_columnconfigure(1, weight=2, uniform="inventory")

        controls = ctk.CTkFrame(self.body, fg_color=SURFACE_COLOR, corner_radius=14)
        controls.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        for column in range(3):
            controls.grid_columnconfigure(column, weight=1)
        self.category_menu = ctk.CTkOptionMenu(
            controls, values=["all", "equipment", "weapons", "armor", "accessories", "materials", "miscellaneous"],
            command=self._set_category,
        )
        self.category_menu.set("all")
        self.category_menu.grid(row=0, column=0, sticky="ew", padx=(12, 5), pady=12)
        self.rarity_menu = ctk.CTkOptionMenu(
            controls, values=["all", "common", "uncommon", "rare", "epic", "legendary", "mythic"],
            command=self._set_rarity,
        )
        self.rarity_menu.set("all")
        self.rarity_menu.grid(row=0, column=1, sticky="ew", padx=5, pady=12)
        self.sort_menu = ctk.CTkOptionMenu(
            controls,
            values=["name", "type", "rarity", "selling_value", "quantity", "acquisition_date"],
            command=self._set_sort,
        )
        self.sort_menu.set("name")
        self.sort_menu.grid(row=0, column=2, sticky="ew", padx=(5, 12), pady=12)

        self.bag_panel = ctk.CTkFrame(self.body, fg_color=SURFACE_COLOR, corner_radius=16)
        self.bag_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 7), pady=(0, 10))
        self.bag_panel.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.bag_panel, text="BAG", anchor="w", text_color=SECONDARY_TEXT,
                     font=ctk.CTkFont(size=11, weight="bold")).grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 4))
        self.item_list = ctk.CTkScrollableFrame(self.bag_panel, fg_color="transparent", height=290)
        self.item_list.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.item_list.grid_columnconfigure(0, weight=1)

        self.detail_panel = ctk.CTkFrame(self.body, fg_color=SURFACE_COLOR, corner_radius=16)
        self.detail_panel.grid(row=1, column=1, sticky="nsew", padx=(7, 0), pady=(0, 10))
        self.detail_panel.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.detail_panel, text="ITEM DETAILS", anchor="w", text_color=SECONDARY_TEXT,
                     font=ctk.CTkFont(size=11, weight="bold")).grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 5))
        self.detail_text = ctk.CTkLabel(self.detail_panel, text="Select an item to inspect it.", anchor="nw", justify="left",
                                        wraplength=390, text_color=TEXT_COLOR)
        self.detail_text.grid(row=1, column=0, sticky="new", padx=16, pady=(0, 10))
        self.action_frame = ctk.CTkFrame(self.detail_panel, fg_color="transparent")
        self.action_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 10))
        self.action_frame.grid_columnconfigure(0, weight=1)
        self.action_frame.grid_columnconfigure(1, weight=1)

        self.equipment_panel = ctk.CTkFrame(self.body, fg_color=SURFACE_COLOR, corner_radius=16)
        self.equipment_panel.grid(row=2, column=0, sticky="nsew", padx=(0, 7), pady=(0, 10))
        self.equipment_panel.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.equipment_panel, text="EQUIPMENT", anchor="w", text_color=SECONDARY_TEXT,
                     font=ctk.CTkFont(size=11, weight="bold")).grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 4))
        self.equipment_list = ctk.CTkFrame(self.equipment_panel, fg_color="transparent")
        self.equipment_list.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))
        self.equipment_list.grid_columnconfigure(0, weight=1)

        self.unclaimed_panel = ctk.CTkFrame(self.body, fg_color=SURFACE_COLOR, corner_radius=16)
        self.unclaimed_panel.grid(row=2, column=1, sticky="nsew", padx=(7, 0), pady=(0, 10))
        self.unclaimed_panel.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.unclaimed_panel, text="UNCLAIMED DROPS", anchor="w", text_color=SECONDARY_TEXT,
                     font=ctk.CTkFont(size=11, weight="bold")).grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 4))
        self.unclaimed_list = ctk.CTkFrame(self.unclaimed_panel, fg_color="transparent")
        self.unclaimed_list.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))
        self.unclaimed_list.grid_columnconfigure(0, weight=1)
        self.refresh()

    def bind_game_state(self) -> None:
        current = self.get_game_state()
        if current is self._bound_state:
            return
        self._bound_state = current
        self.inventory = InventoryManager(current)
        self.equipment = EquipmentManager(current, self.inventory.item_database, self.inventory)

    def refresh(self) -> None:
        self.bind_game_state()
        assert self.inventory is not None and self.equipment is not None
        self.usage_label.configure(text=f"{self.inventory.used_slots} / {self.inventory.capacity} slots · {self.inventory.free_slots} free")
        self._refresh_bag()
        self._refresh_details()
        self._refresh_equipment()
        self._refresh_unclaimed()

    def _refresh_bag(self) -> None:
        assert self.inventory is not None
        self._clear(self.item_list)
        items = self.inventory.filter_items(category=self.category, rarity=self.rarity)
        items = self.inventory.sort_items(items, sort_by=self.sort_by)
        visible_ids = {item.instance_id for item in items}
        if self.selected_instance_id not in visible_ids:
            self.selected_instance_id = None
        if not items:
            ctk.CTkLabel(self.item_list, text="No items match these filters.", text_color=SECONDARY_TEXT).grid(row=0, column=0, sticky="w", padx=8, pady=12)
            return
        for row, item in enumerate(items):
            definition = self.inventory.item_database.get_by_id(item.item_id)
            rarity = self.inventory.item_database.config.rarity_by_id[definition.rarity]
            label = f"{definition.name}  ·  {definition.rarity.title()}  ·  x{item.quantity}"
            button = ctk.CTkButton(
                self.item_list, text=label, anchor="w", height=36,
                fg_color=ACCENT_COLOR if item.instance_id == self.selected_instance_id else "transparent",
                hover_color="#34323d", text_color=rarity.color_hex,
                command=lambda selected=item: self._select(selected),
            )
            button.grid(row=row, column=0, sticky="ew", padx=4, pady=2)

    def _refresh_details(self) -> None:
        assert self.inventory is not None and self.equipment is not None
        self._clear(self.action_frame)
        item = self.inventory.get_item(self.selected_instance_id) if self.selected_instance_id else None
        if item is None:
            self.detail_text.configure(text="Select an item to inspect it.")
            return
        definition = self.inventory.item_database.get_by_id(item.item_id)
        rarity = self.inventory.item_database.config.rarity_by_id[definition.rarity]
        value = self.inventory.calculate_sell_value(definition.item_id, item.quantity) if definition.can_sell else 0
        lines = [definition.name, f"{rarity.display_name} {definition.item_type.title()}", definition.description,
                 f"Quantity: {item.quantity}", f"Sell value: {value:,} G" if definition.can_sell else "Cannot be sold",
                 f"Required level: {definition.required_level}" if definition.can_equip else "",
                 f"Acquired: {item.acquired_at}"]
        if definition.can_equip:
            scaled = self._equipment_bonus_text(definition)
            lines.extend([f"Slot: {definition.equipment_slot.replace('_', ' ').title()}", f"Bonuses: {scaled or 'None'}"])
            slots = [slot for slot in self.equipment.slots if slot.equipment_slot == definition.equipment_slot]
            slot = next((slot for slot in slots if self.equipment.get_equipped(slot.slot_id)), slots[0] if slots else None)
            equipped = self.equipment.get_equipped(slot.slot_id) if slot else None
            if equipped and equipped.instance_id != item.instance_id:
                current = self.inventory.item_database.get_by_id(equipped.item_id)
                lines.append(f"Compare: {current.name} currently equipped")
                lines.append("Replacement bonuses: " + (self._equipment_bonus_text(current) or "None"))
        self.detail_text.configure(text="\n".join(line for line in lines if line))

        column = 0
        if definition.can_equip:
            ctk.CTkButton(self.action_frame, text="Equip", command=lambda: self._equip(item)).grid(row=0, column=column, sticky="ew", padx=3, pady=3)
            column += 1
        if definition.can_sell:
            ctk.CTkButton(self.action_frame, text="Sell", command=lambda: self._sell(item)).grid(row=0, column=column, sticky="ew", padx=3, pady=3)
            column += 1
        if definition.can_discard:
            ctk.CTkButton(self.action_frame, text="Discard", fg_color="#714545", command=lambda: self._discard(item)).grid(row=1, column=0, sticky="ew", padx=3, pady=3)
        if definition.max_stack > 1 and item.quantity > 1 and self.inventory.free_slots:
            ctk.CTkButton(self.action_frame, text="Split Stack", command=lambda: self._split(item)).grid(row=1, column=1, sticky="ew", padx=3, pady=3)

    def _refresh_equipment(self) -> None:
        assert self.equipment is not None and self.inventory is not None
        self._clear(self.equipment_list)
        for row, slot in enumerate(self.equipment.slots):
            item = self.equipment.get_equipped(slot.slot_id)
            if item:
                definition = self.inventory.item_database.get_by_id(item.item_id)
                label = f"{slot.display_name}: {definition.name}"
                ctk.CTkButton(self.equipment_list, text=f"Unequip {slot.display_name}", width=100,
                              command=lambda selected=slot.slot_id: self._unequip(selected)).grid(row=row, column=1, padx=4, pady=2)
            else:
                label = f"{slot.display_name}: Empty"
            ctk.CTkLabel(self.equipment_list, text=label, anchor="w", text_color=TEXT_COLOR).grid(row=row, column=0, sticky="ew", padx=5, pady=3)

    def _refresh_unclaimed(self) -> None:
        assert self.inventory is not None
        self._clear(self.unclaimed_list)
        entries = self.inventory.state.unclaimed_loot
        if not entries:
            ctk.CTkLabel(self.unclaimed_list, text="No unclaimed drops.", text_color=SECONDARY_TEXT).grid(row=0, column=0, sticky="w", padx=6, pady=8)
            return
        for row, loot in enumerate(entries):
            definition = self.inventory.item_database.try_get(loot.item_id)
            title = definition.name if definition else loot.item_id
            ctk.CTkLabel(self.unclaimed_list, text=f"{title} ×{loot.quantity}\n{loot.reason}", anchor="w", justify="left",
                         text_color=TEXT_COLOR).grid(row=row, column=0, sticky="ew", padx=5, pady=3)
            ctk.CTkButton(self.unclaimed_list, text="Claim", width=72,
                          command=lambda key=loot.unclaimed_id: self._claim(key)).grid(row=row, column=1, padx=4, pady=3)

    def _select(self, item: ItemInstance) -> None:
        self.selected_instance_id = item.instance_id
        self.refresh()

    def _equip(self, item: ItemInstance) -> None:
        assert self.inventory is not None and self.equipment is not None
        definition = self.inventory.item_database.get_by_id(item.item_id)
        options = [slot for slot in self.equipment.slots if slot.equipment_slot == definition.equipment_slot]
        if len(options) == 1:
            slot = options[0]
        else:
            labels = [entry.display_name for entry in options]
            answer = simpledialog.askstring("Choose Equipment Slot", "Choose one: " + ", ".join(labels), parent=self.winfo_toplevel())
            if answer is None:
                return
            slot = next((entry for entry in options if entry.display_name.casefold() == answer.casefold() or entry.slot_id == answer.casefold()), None)
            if slot is None:
                messagebox.showerror("Equipment", "That slot was not found.", parent=self.winfo_toplevel())
                return
        try:
            result = self.equipment.equip(slot.slot_id, item.instance_id)
        except (EquipmentOperationError, ValueError) as exc:
            messagebox.showerror("Cannot Equip Item", str(exc), parent=self.winfo_toplevel())
            return
        self.selected_instance_id = None
        self.on_change()
        self._show_result(f"Equipped in {result.slot_id.replace('_', ' ').title()}.")

    def _unequip(self, slot_id: str) -> None:
        assert self.equipment is not None
        try:
            self.equipment.unequip(slot_id)
        except (EquipmentOperationError, ValueError) as exc:
            messagebox.showerror("Cannot Unequip Item", str(exc), parent=self.winfo_toplevel())
            return
        self.on_change()

    def _sell(self, item: ItemInstance) -> None:
        assert self.inventory is not None
        definition = self.inventory.item_database.get_by_id(item.item_id)
        quantity = 1
        if item.quantity > 1:
            quantity = simpledialog.askinteger("Sell Items", f"How many {definition.name} to sell? (1–{item.quantity})", parent=self.winfo_toplevel(), minvalue=1, maxvalue=item.quantity)
            if quantity is None:
                return
        value = self.inventory.calculate_sell_value(item.item_id, quantity)
        if not messagebox.askyesno("Confirm Sale", f"Sell {quantity} × {definition.name} for {value:,} G?", parent=self.winfo_toplevel()):
            return
        result = self.inventory.sell_item(item.instance_id, quantity)
        if not result.success:
            messagebox.showerror("Sale Failed", result.message, parent=self.winfo_toplevel())
            return
        self.selected_instance_id = None if quantity == item.quantity else item.instance_id
        self.on_change()
        self._show_result(result.message)

    def _discard(self, item: ItemInstance) -> None:
        assert self.inventory is not None
        definition = self.inventory.item_database.get_by_id(item.item_id)
        quantity = 1
        if item.quantity > 1:
            quantity = simpledialog.askinteger("Discard Items", f"How many {definition.name} to discard? (1–{item.quantity})", parent=self.winfo_toplevel(), minvalue=1, maxvalue=item.quantity)
            if quantity is None:
                return
        if not messagebox.askyesno("Discard Item", f"Discard {quantity} × {definition.name}? This cannot be undone.", parent=self.winfo_toplevel()):
            return
        result = self.inventory.discard_item(item.instance_id, quantity)
        if not result.success:
            messagebox.showerror("Discard Failed", result.message, parent=self.winfo_toplevel())
            return
        self.selected_instance_id = None if quantity == item.quantity else item.instance_id
        self.on_change()

    def _split(self, item: ItemInstance) -> None:
        assert self.inventory is not None
        quantity = simpledialog.askinteger("Split Stack", f"Move how many items to a new stack? (1–{item.quantity - 1})", parent=self.winfo_toplevel(), minvalue=1, maxvalue=item.quantity - 1)
        if quantity is None:
            return
        try:
            self.inventory.split_stack(item.instance_id, quantity)
        except InventoryOperationError as exc:
            messagebox.showerror("Cannot Split Stack", str(exc), parent=self.winfo_toplevel())
            return
        self.on_change()

    def _claim(self, unclaimed_id: str) -> None:
        assert self.inventory is not None
        try:
            result = self.inventory.claim_unclaimed(unclaimed_id)
        except InventoryOperationError as exc:
            messagebox.showerror("Cannot Claim Drop", str(exc), parent=self.winfo_toplevel())
            return
        if result.collected_quantity:
            self.on_change()
            self._show_result(f"Claimed {result.collected_quantity} × {result.item_name}.")
        else:
            messagebox.showinfo("Inventory Full", result.reason or "The drop could not be claimed.", parent=self.winfo_toplevel())

    def _equipment_bonus_text(self, definition) -> str:
        assert self.inventory is not None
        from ...systems.equipment.equipment_calculator import EquipmentCalculator
        bonuses = EquipmentCalculator.item_bonuses(definition, self.inventory.item_database)
        return ", ".join(f"{name.replace('_', ' ').title()} +{value:g}" for name, value in bonuses.items())

    def _set_category(self, value: str) -> None:
        self.category = value
        self.refresh()

    def _set_rarity(self, value: str) -> None:
        self.rarity = value
        self.refresh()

    def _set_sort(self, value: str) -> None:
        self.sort_by = value
        self.refresh()

    @staticmethod
    def _clear(widget) -> None:
        for child in widget.winfo_children():
            child.destroy()

    def _show_result(self, text: str) -> None:
        messagebox.showinfo("Inventory", text, parent=self.winfo_toplevel())


__all__ = ["InventoryPage"]
