import tkinter as tk
import customtkinter as ctk
from tkinter import ttk, messagebox
from typing import List

from ..managers.save_manager import SaveManager


class LoadSaveDialog(ctk.CTkToplevel):
    def __init__(self, parent: tk.Tk, save_files: List[str], timestamps: dict[str, str]) -> None:
        super().__init__(parent)
        self.title("Load Game")
        self.geometry("360x300")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.result: str | None = None

        label = ctk.CTkLabel(self, text="Select a save file to load:", anchor="w")
        label.pack(fill="x", padx=16, pady=(16, 8))

        list_frame = ttk.Frame(self)
        list_frame.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        self.listbox = tk.Listbox(
            list_frame,
            activestyle="dotbox",
            bg="#171b21",
            fg="#e6e9f0",
            selectbackground="#5c80ff",
            highlightthickness=0,
        )
        self.listbox.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=scrollbar.set)

        self.timestamps = timestamps
        self.tooltip = tk.StringVar(value="Hover a save to see its last modified time.")

        if save_files:
            self.save_files = save_files
            for save_file in self.save_files:
                self.listbox.insert(tk.END, save_file)
            self.listbox.selection_set(0)
            self.listbox.bind("<Motion>", self._on_hover)
            self.listbox.bind("<Leave>", self._on_leave)
        else:
            self.save_files = []
            self.listbox.insert(tk.END, "No save files found")
            self.listbox.config(state="disabled")

        self.status_label = ctk.CTkLabel(self, textvariable=self.tooltip, anchor="w", font=ctk.CTkFont(size=12))
        self.status_label.pack(fill="x", padx=16, pady=(0, 8))

        button_frame = ctk.CTkFrame(self, fg_color="#151619")
        button_frame.pack(fill="x", padx=16, pady=(0, 16))

        load_button = ctk.CTkButton(button_frame, text="Load", command=self._on_load, corner_radius=14)
        load_button.pack(side="left", expand=True, fill="x", padx=(0, 8))

        delete_button = ctk.CTkButton(button_frame, text="Delete", command=self._on_delete, corner_radius=14)
        delete_button.pack(side="left", expand=True, fill="x", padx=(0, 8))

        cancel_button = ctk.CTkButton(button_frame, text="Cancel", command=self._on_cancel, corner_radius=14)
        cancel_button.pack(side="right", expand=True, fill="x", padx=(8, 0))

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _on_hover(self, event: tk.Event) -> None:
        index = self.listbox.nearest(event.y)
        if index >= 0 and index < self.listbox.size():
            save_file = self.listbox.get(index)
            timestamp = self.timestamps.get(save_file, "Unknown")
            self.tooltip.set(f"Last saved: {timestamp}")

    def _on_leave(self, event: tk.Event) -> None:
        self.tooltip.set("Hover a save to see its last modified time.")

    def _on_load(self) -> None:
        if self.listbox.curselection():
            self.result = self.listbox.get(self.listbox.curselection()[0])
        self.destroy()

    def _refresh_list(self) -> None:
        self.listbox.delete(0, tk.END)
        self.timestamps = {filename: SaveManager.get_save_timestamp(filename) for filename in self.save_files}
        if self.save_files:
            for save_file in self.save_files:
                self.listbox.insert(tk.END, save_file)
            self.listbox.selection_set(0)
        else:
            self.listbox.insert(tk.END, "No save files found")
            self.listbox.config(state="disabled")
        self.tooltip.set("Hover a save to see its last modified time.")

    def _on_delete(self) -> None:
        if not self.listbox.curselection():
            return

        selected = self.listbox.get(self.listbox.curselection()[0])
        if selected not in self.save_files:
            return

        if not messagebox.askyesno(
            "Delete Save",
            f"Delete '{selected}'? This cannot be undone.",
            parent=self,
        ):
            return

        SaveManager.delete(selected)
        self.save_files.remove(selected)
        self._refresh_list()
        self.tooltip.set(f"Deleted: {selected}")

    def _on_cancel(self) -> None:
        self.result = None
        self.destroy()
