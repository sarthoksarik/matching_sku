# File: sku_manager_gui.py
import tkinter as tk
from tkinter import (
    messagebox,
    simpledialog,
    Listbox,
    Toplevel,
    Frame,
    Scrollbar,
    END,
    EXTENDED,
    Button,
    Label,
    Entry,
)
import database as db  # Use database functions directly


class SkuManagerWindow(Toplevel):
    """Window for managing the SKUs in the database."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Manage SKUs")
        self.geometry("450x480")
        self.transient(parent)
        self.grab_set()

        # --- Widgets ---
        self.add_frame = Frame(self)
        self.add_label = Label(self.add_frame, text="New SKU:")
        self.sku_entry = Entry(self.add_frame, width=30)
        self.add_button = Button(self.add_frame, text="Add SKU", command=self.add_sku)

        self.list_frame = Frame(self)
        self.list_label = Label(
            self.list_frame, text="Current SKUs (Ctrl/Shift+Click for multi-select):"
        )
        self.scrollbar = Scrollbar(self.list_frame, orient=tk.VERTICAL)
        self.sku_listbox = Listbox(
            self.list_frame,
            yscrollcommand=self.scrollbar.set,
            selectmode=EXTENDED,  # Allow multi-selection
            width=50,
            height=12,
        )
        self.scrollbar.config(command=self.sku_listbox.yview)

        self.action_button_frame = Frame(self)
        self.edit_button = Button(
            self.action_button_frame,
            text="Edit Selected",
            command=self.edit_selected_sku,
        )
        self.delete_button = Button(
            self.action_button_frame,
            text="Delete Selected",
            command=self.delete_selected_skus,
        )
        self.paste_button = Button(
            self.action_button_frame,
            text="Paste SKUs from Clipboard",
            command=self.paste_skus_from_clipboard,
        )

        self.close_button = Button(self, text="Close", command=self.destroy)

        # --- Layout ---
        self.add_frame.pack(pady=10, padx=10, fill=tk.X)
        self.add_label.pack(side=tk.LEFT, padx=5)
        self.sku_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        self.add_button.pack(side=tk.LEFT, padx=5)

        self.list_frame.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)
        self.list_label.pack(anchor=tk.W)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.sku_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.action_button_frame.pack(pady=5, padx=10, fill=tk.X)
        self.edit_button.pack(side=tk.LEFT, padx=5, pady=5)
        self.delete_button.pack(side=tk.LEFT, padx=5, pady=5)
        self.paste_button.pack(side=tk.RIGHT, padx=5, pady=5)

        self.close_button.pack(pady=10)

        # --- Initial Population & Bindings ---
        self.refresh_sku_list()
        self.sku_entry.bind("<Return>", lambda event: self.add_sku())
        self.sku_entry.focus_set()

    def refresh_sku_list(self):
        """Clears and reloads the listbox with SKUs from the database."""
        self.sku_listbox.delete(0, END)
        skus = db.get_all_skus()
        for sku in skus:
            self.sku_listbox.insert(END, sku)

    def add_sku(self):
        """Adds the SKU from the entry field to the database and refreshes the list."""
        new_sku = self.sku_entry.get().strip()
        if not new_sku:
            messagebox.showwarning(
                "Input Error", "Please enter an SKU name.", parent=self
            )
            return
        if db.add_sku(new_sku):
            self.refresh_sku_list()
            self.sku_entry.delete(0, END)
        else:
            messagebox.showerror(
                "Database Error",
                f"Failed to add SKU '{new_sku}'.\nIt might already exist or DB issue.",
                parent=self,
            )

    def edit_selected_sku(self):
        """Opens a dialog to edit the currently selected SKU. Best for single selection."""
        selected_indices = self.sku_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning(
                "Selection Error", "Please select an SKU to edit.", parent=self
            )
            return None
        if len(selected_indices) > 1:
            messagebox.showwarning(
                "Multiple Selection",
                "Only the first selected SKU will be edited.",
                parent=self,
            )
        selected_sku = self.sku_listbox.get(selected_indices[0])
        new_name = simpledialog.askstring(
            "Edit SKU",
            f"Enter the new name for SKU:",
            initialvalue=selected_sku,
            parent=self,
        )
        if new_name is not None:
            new_name = new_name.strip()
            if not new_name:
                messagebox.showerror(
                    "Input Error", "New SKU name cannot be empty.", parent=self
                )
                return
            if new_name == selected_sku:
                return
            if db.update_sku(selected_sku, new_name):
                self.refresh_sku_list()
                messagebox.showinfo(
                    "Success", f"SKU updated to '{new_name}'.", parent=self
                )
            else:
                messagebox.showerror(
                    "Update Error",
                    f"Could not update SKU.\n'{new_name}' might already exist.",
                    parent=self,
                )

    def delete_selected_skus(self):
        """Deletes all currently selected SKUs from the database."""
        selected_indices = self.sku_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning(
                "Selection Error",
                "Please select one or more SKUs to delete.",
                parent=self,
            )
            return
        selected_skus = [self.sku_listbox.get(i) for i in selected_indices]
        num_selected = len(selected_skus)
        confirm_message = (
            f"Are you sure you want to delete {num_selected} selected SKU(s)?"
        )
        if 0 < num_selected <= 5:
            confirm_message += "\n\n" + "\n".join(selected_skus)
        elif num_selected > 5:
            confirm_message += f"\n\n(e.g., {selected_skus[0]}, ...)"

        if messagebox.askyesno("Confirm Delete", confirm_message, parent=self):
            deleted_count = 0
            failed_count = 0
            for sku in selected_skus:
                if db.delete_sku(sku):
                    deleted_count += 1
                else:
                    failed_count += 1
            self.refresh_sku_list()
            summary = f"Deleted: {deleted_count} SKU(s)."
            if failed_count > 0:
                summary += f"\nFailed: {failed_count} SKU(s)."
                messagebox.showwarning("Deletion Report", summary, parent=self)

    def paste_skus_from_clipboard(self):
        """Pastes SKUs from clipboard (one per line) into the database."""
        try:
            clipboard_content = self.clipboard_get()
        except tk.TclError:
            messagebox.showerror(
                "Clipboard Error",
                "Could not read text data from clipboard.",
                parent=self,
            )
            return
        if not clipboard_content:
            messagebox.showwarning(
                "Clipboard Empty", "Clipboard is empty.", parent=self
            )
            return
        potential_skus = [
            line.strip() for line in clipboard_content.splitlines() if line.strip()
        ]
        if not potential_skus:
            messagebox.showwarning(
                "No SKUs Found",
                "No valid SKU text found in clipboard data.",
                parent=self,
            )
            return
        added_count = 0
        failed_count = 0
        if not messagebox.askyesno(
            "Confirm Paste",
            f"Found {len(potential_skus)} potential SKUs.\nProceed adding? (Duplicates skipped)",
            parent=self,
        ):
            return
        for sku in potential_skus:
            if db.add_sku(sku):
                added_count += 1
            else:
                failed_count += 1
        self.refresh_sku_list()
        summary_message = (
            f"Paste Report:\nAdded: {added_count}\nSkipped/Failed: {failed_count}"
        )
        messagebox.showinfo("Paste Complete", summary_message, parent=self)
