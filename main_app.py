# File: main_app.py
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk  # For Combobox
from tkinter import (
    scrolledtext,
    messagebox,
    simpledialog,
    Listbox,
    Toplevel,
    Frame,
    Scrollbar,
    END,
    SINGLE,
    Button,
    Label,
    Entry,
    Scale,
    IntVar,
    StringVar,
    Radiobutton,
    Frame,
    LabelFrame,
    EXTENDED,
)  # Added EXTENDED
import database as db  # Assumes database.py is in the same directory
from thefuzz import process  # For fuzzy matching
import os  # For environment variables and path handling
import sys  # To detect if running as frozen executable

# Attempt to import Gemini library, handle if not installed
try:
    import google.generativeai as genai

    GEMINI_AVAILABLE = True
except ImportError:
    print(
        "WARNING: google-generativeai library not found. Gemini AI functionality will be disabled."
    )
    print("Install it using: pip install google-generativeai")
    GEMINI_AVAILABLE = False
    genai = None  # Define genai as None if import fails

# --- Constants ---
NO_MATCH_TEXT = "--- NO MATCH FOUND ---"
DEFAULT_THRESHOLD = 70
ENGINE_FUZZY = "fuzzy"
ENGINE_GEMINI = "gemini"
GEMINI_API_ENV_VAR = "GEMINI_API_KEY"
API_KEY_FILENAME = "api_key.txt"  # Name of the key file

# Define available models for the dropdown
AVAILABLE_GEMINI_MODELS = [
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-2.0-flash",
    # Add newer/experimental ones carefully if desired, e.g.:
    # 'gemini-2.5-pro' # Check availability/stability first
]
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"  # User's last choice

DEFAULT_GEMINI_INSTRUCTIONS = """Your Task: Respond with ONLY the single best matching SKU name exactly as it appears in the 'Available SKUs' list.
If none of the SKUs in the list are a suitable match for the product name, respond with the exact text: NO MATCH
Do not include any explanations, introductions, or formatting other than the single matching SKU or "NO MATCH"."""

# --- Matching Logic ---


# Fuzzy Match Function
def find_best_sku_match_fuzzy(product_name, sku_list, threshold):
    """Finds the best matching SKU using fuzzy matching."""
    if not product_name or not sku_list:
        return NO_MATCH_TEXT
    try:
        result = process.extractOne(str(product_name), sku_list)
        if result:
            best_match, score = result
            if score >= threshold:
                return best_match
            else:
                return NO_MATCH_TEXT
        else:
            return NO_MATCH_TEXT
    except Exception as e:
        print(f"Error during fuzzy matching for '{product_name}': {e}")
        return "--- ERROR DURING FUZZY MATCH ---"


# Gemini Match Function
def find_best_sku_match_gemini(
    product_name, sku_list, api_key, model_name, instructions
):
    """Matches product name to SKU list using Gemini AI."""
    if not GEMINI_AVAILABLE:
        return "--- GEMINI LIBRARY NOT INSTALLED ---"  # Check if library loaded
    if not product_name or not sku_list:
        return NO_MATCH_TEXT
    if not api_key:
        print("Error: Gemini API key not provided.")
        return "--- ERROR: MISSING API KEY ---"
    if not model_name:
        print("Error: Gemini model name not provided.")
        return "--- ERROR: MISSING MODEL NAME ---"
    if not instructions:
        print("Error: Gemini prompt instructions not provided.")
        return "--- ERROR: MISSING INSTRUCTIONS ---"

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)

        # Construct the prompt carefully using the provided instructions
        prompt = f"""Analyze the following product name and list of SKUs. Identify the single best matching SKU from the list provided.

Product Name: "{product_name}"

Available SKUs:
{chr(10).join(f"- {sku}" for sku in sku_list)}

{instructions}
"""

        response = model.generate_content(prompt)

        # Validate and parse the response
        try:
            gemini_result = response.text.strip()
            if gemini_result == "NO MATCH":
                return NO_MATCH_TEXT
            elif gemini_result in sku_list:
                return gemini_result
            else:
                print(
                    f"Warning: Gemini returned text ('{gemini_result}') not exactly in SKU list or 'NO MATCH' for product '{product_name}'. Treating as no match."
                )
                return NO_MATCH_TEXT
        except ValueError:
            print(
                f"Warning: Gemini response blocked or empty for product '{product_name}'. Response parts: {response.parts}"
            )
            return "--- GEMINI RESPONSE BLOCKED/EMPTY ---"
        except Exception as e_parse:
            print(f"Error parsing Gemini response for '{product_name}': {e_parse}")
            return "--- ERROR PARSING GEMINI RESPONSE ---"

    except Exception as e_api:
        print(
            f"Error during Gemini API call for '{product_name}' (Model: {model_name}): {e_api}"
        )
        if "API key not valid" in str(e_api):
            return "--- ERROR: INVALID API KEY ---"
        if (
            "not found" in str(e_api).lower()
            or "permission denied" in str(e_api).lower()
        ):
            return f"--- ERROR: MODEL '{model_name}' NOT FOUND/ACCESSIBLE ---"
        return "--- ERROR DURING GEMINI API CALL ---"


# --- GUI Classes ---


class SkuManagerWindow(Toplevel):
    """Window for managing the SKUs in the database."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Manage SKUs")
        self.geometry("450x480")
        self.transient(parent)
        self.grab_set()

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
                f"Failed to add SKU '{new_sku}'.\nIt might already exist or there was a database issue.",
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
                "Multiple SKUs selected. Only the first one will be edited.",
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
                    f"Could not update SKU.\nThe new name '{new_name}' might already exist.",
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
        if num_selected > 0 and num_selected <= 5:
            confirm_message += "\n\n" + "\n".join(selected_skus)
        elif num_selected > 5:
            confirm_message += (
                f"\n\n(e.g., {selected_skus[0]}, {selected_skus[1]}, ...)"
            )
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
                "Clipboard Empty",
                "Clipboard is empty or contains no text.",
                parent=self,
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
            f"Found {len(potential_skus)} potential SKUs.\nProceed adding them? (Duplicates will be skipped)",
            parent=self,
        ):
            return
        for sku in potential_skus:
            if db.add_sku(sku):
                added_count += 1
            else:
                failed_count += 1
        self.refresh_sku_list()
        summary_message = f"Paste SKUs Report:\n\nSuccessfully Added: {added_count}\nSkipped (Duplicates/Errors): {failed_count}"
        messagebox.showinfo("Paste Complete", summary_message, parent=self)


class Application(tk.Tk):
    """Main application class."""

    def __init__(self):
        super().__init__()
        self.title("Product Name to SKU Converter")
        self.geometry("700x720")  # Adjusted height

        # --- Determine Base Path ---
        if getattr(sys, "frozen", False):
            self.base_path = os.path.dirname(sys.executable)
            print(f"Running bundled executable. Base path: {self.base_path}")
        else:
            self.base_path = os.path.dirname(os.path.abspath(__file__))
            print(f"Running as script. Base path: {self.base_path}")

        # --- Variables ---
        self.all_skus = []
        self._warned_no_skus = False
        self.similarity_threshold = IntVar(value=DEFAULT_THRESHOLD)
        self.engine_choice = StringVar(value=ENGINE_FUZZY)
        self.api_key_var = StringVar()  # Holds GUI entry text for API key
        self.selected_gemini_model = StringVar(value=DEFAULT_GEMINI_MODEL)

        # --- Read potential API Key sources (ENV and File) ---
        self.env_api_key = os.environ.get(GEMINI_API_ENV_VAR)
        self.file_api_key = None
        key_file_path = os.path.join(self.base_path, API_KEY_FILENAME)
        try:
            with open(key_file_path, "r", encoding="utf-8") as f:  # Added encoding
                key_from_file = f.readline().strip()
                if key_from_file:
                    self.file_api_key = key_from_file
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"Error reading API key file '{key_file_path}': {e}")
        if self.env_api_key:
            print(f"Info: Found Gemini API key in ENV var.")
        if self.file_api_key:
            print(f"Info: Read API key from {API_KEY_FILENAME}.")

        # --- Widgets ---
        # Input Frame (Left)
        input_frame = Frame(self)
        input_label = Label(input_frame, text="Paste Product Names (one per line):")
        self.input_text = scrolledtext.ScrolledText(
            input_frame, height=15, width=40, wrap=tk.WORD
        )

        # --- Control Frame (Center) ---
        control_frame = Frame(self)
        self.convert_button = Button(
            control_frame,
            text="Convert >>",
            command=self.perform_conversion,
            width=12,
            height=2,
        )
        self.manage_button = Button(
            control_frame, text="Manage SKUs", command=self.open_sku_manager, width=12
        )

        # -- Engine Selection Frame --
        engine_frame = LabelFrame(control_frame, text="Matching Engine")
        self.fuzzy_radio = Radiobutton(
            engine_frame,
            text="Fuzzy Match",
            variable=self.engine_choice,
            value=ENGINE_FUZZY,
            command=self.toggle_controls,
        )
        # Disable Gemini radio if library not found
        gemini_radio_state = tk.NORMAL if GEMINI_AVAILABLE else tk.DISABLED
        self.gemini_radio = Radiobutton(
            engine_frame,
            text="Gemini AI",
            variable=self.engine_choice,
            value=ENGINE_GEMINI,
            command=self.toggle_controls,
            state=gemini_radio_state,
        )

        # -- Fuzzy Threshold Controls --
        self.threshold_frame = Frame(control_frame)
        threshold_label = Label(self.threshold_frame, text="Match Sensitivity:")
        self.threshold_value_label = Label(
            self.threshold_frame, textvariable=self.similarity_threshold, width=3
        )
        self.threshold_scale = Scale(
            self.threshold_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            variable=self.similarity_threshold,
            length=120,
            showvalue=0,
        )

        # -- Gemini Controls Frame --
        self.gemini_controls_frame = Frame(
            control_frame
        )  # Parent frame for Gemini controls

        # API Key Sub-Frame
        api_key_subframe = Frame(self.gemini_controls_frame)
        api_key_label = Label(api_key_subframe, text="Gemini API Key:")
        self.api_key_entry = Entry(
            api_key_subframe, textvariable=self.api_key_var, width=20, show="*"
        )
        self.api_key_info_label = Label(
            api_key_subframe,
            text=f"(Priority: Entry > {API_KEY_FILENAME} > ENV)",
            fg="blue",
            cursor="hand2",
        )
        self.api_key_info_label.bind(
            "<Button-1>",
            lambda e: messagebox.showinfo(
                "API Key Info",
                f"API Key Loading Priority:\n1. Manual entry here.\n2. File: {API_KEY_FILENAME}\n3. Env Var: {GEMINI_API_ENV_VAR}\n\nThe first non-empty key found is used.",
                parent=self,
            ),
        )

        # Model Selection Sub-Frame
        model_select_subframe = Frame(self.gemini_controls_frame)
        model_label = Label(model_select_subframe, text="Gemini Model:")
        # Check if model list is empty before creating combobox
        if not AVAILABLE_GEMINI_MODELS:
            self.model_combobox = Label(
                model_select_subframe, text="No models defined", fg="red"
            )
        else:
            self.model_combobox = ttk.Combobox(
                model_select_subframe,
                textvariable=self.selected_gemini_model,
                values=AVAILABLE_GEMINI_MODELS,
                state="readonly",
                width=18,
            )
            # Ensure default value is valid, otherwise set to first available
            if DEFAULT_GEMINI_MODEL not in AVAILABLE_GEMINI_MODELS:
                self.selected_gemini_model.set(AVAILABLE_GEMINI_MODELS[0])

        # Prompt Instruction Sub-Frame
        prompt_instr_subframe = Frame(self.gemini_controls_frame)
        instr_label = Label(prompt_instr_subframe, text="Gemini Prompt Instructions:")
        self.prompt_instr_text = scrolledtext.ScrolledText(
            prompt_instr_subframe, height=6, width=30, wrap=tk.WORD
        )
        self.prompt_instr_text.insert("1.0", DEFAULT_GEMINI_INSTRUCTIONS)

        # Output Frame (Right)
        output_frame = Frame(self)
        output_label = Label(output_frame, text="Matching SKUs:")
        self.output_text = scrolledtext.ScrolledText(
            output_frame, height=15, width=40, wrap=tk.WORD, state=tk.DISABLED
        )

        # --- Layout ---
        input_frame.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.BOTH, expand=True)
        input_label.pack(anchor=tk.W, pady=(0, 5))
        self.input_text.pack(fill=tk.BOTH, expand=True)

        # Layout for Control Frame (Center)
        control_frame.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.Y)
        self.convert_button.pack(pady=(10, 15))
        self.manage_button.pack(pady=15)
        engine_frame.pack(pady=(15, 10), padx=5, fill=tk.X)
        self.fuzzy_radio.pack(anchor=tk.W)
        self.gemini_radio.pack(anchor=tk.W)

        # Pack Fuzzy frame (managed by toggle_controls)
        self.threshold_frame.pack(pady=5, padx=5, fill=tk.X)
        threshold_label.pack(side=tk.LEFT)
        self.threshold_value_label.pack(side=tk.LEFT, padx=2)
        self.threshold_scale.pack(side=tk.LEFT, expand=True, fill=tk.X)

        # Pack Gemini frame (managed by toggle_controls)
        self.gemini_controls_frame.pack(pady=5, padx=5, fill=tk.BOTH, expand=True)
        # Layout Gemini sub-frames
        api_key_subframe.pack(pady=(5, 0), fill=tk.X)  # Reduced top padding
        api_key_label.pack(anchor=tk.W)
        self.api_key_entry.pack(fill=tk.X, pady=(0, 2))
        self.api_key_info_label.pack(anchor=tk.W)

        model_select_subframe.pack(pady=(5, 0), fill=tk.X)
        model_label.pack(anchor=tk.W)
        self.model_combobox.pack(fill=tk.X)

        prompt_instr_subframe.pack(pady=5, fill=tk.BOTH, expand=True)
        instr_label.pack(anchor=tk.W)
        self.prompt_instr_text.pack(fill=tk.BOTH, expand=True)

        output_frame.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.BOTH, expand=True)
        output_label.pack(anchor=tk.W, pady=(0, 5))
        self.output_text.pack(fill=tk.BOTH, expand=True)

        # --- Initialization ---
        self.load_skus()
        # Set initial UI state based on default engine
        self.toggle_controls()

    def toggle_controls(self):
        """Show/hide controls based on selected engine."""
        selected_engine = self.engine_choice.get()
        if selected_engine == ENGINE_FUZZY:
            self.threshold_frame.pack(pady=5, padx=5, fill=tk.X)  # Show
            self.gemini_controls_frame.pack_forget()  # Hide
        elif selected_engine == ENGINE_GEMINI and GEMINI_AVAILABLE:
            self.threshold_frame.pack_forget()  # Hide
            self.gemini_controls_frame.pack(
                pady=5, padx=5, fill=tk.BOTH, expand=True
            )  # Show
            # Always enable API key entry now due to priority change
            self.api_key_entry.config(state=tk.NORMAL)
            # Clear API key entry if it contains placeholder text from previous logic
            if self.api_key_var.get().startswith("Detected in"):
                self.api_key_var.set("")
        else:  # Gemini selected but library missing, or other state
            self.threshold_frame.pack_forget()
            self.gemini_controls_frame.pack_forget()
            if selected_engine == ENGINE_GEMINI and not GEMINI_AVAILABLE:
                messagebox.showerror(
                    "Missing Library",
                    "Gemini AI library not installed.\nPlease install 'google-generativeai'.",
                    parent=self,
                )
                # Optionally switch back to fuzzy
                # self.engine_choice.set(ENGINE_FUZZY)
                # self.toggle_controls()

    def load_skus(self):
        """Loads/reloads the list of SKUs from the database into memory."""
        self.all_skus = db.get_all_skus()
        print(f"Loaded {len(self.all_skus)} SKUs into memory.")
        if not self.all_skus and not self._warned_no_skus:
            messagebox.showwarning(
                "No SKUs Loaded",
                "The SKU database is currently empty.\n\nPlease use 'Manage SKUs' to add your official SKU list.",
                parent=self,
            )
            self._warned_no_skus = True

    def perform_conversion(self):
        """Reads input, finds matches using the selected engine, and displays results."""
        selected_engine = self.engine_choice.get()
        print(f"Starting conversion using engine: {selected_engine}")

        # Check if Gemini library is needed but missing
        if selected_engine == ENGINE_GEMINI and not GEMINI_AVAILABLE:
            messagebox.showerror(
                "Missing Library",
                "Cannot use Gemini engine because the 'google-generativeai' library is not installed.",
            )
            return

        input_content = self.input_text.get("1.0", tk.END).strip()
        if not input_content:
            messagebox.showwarning(
                "Input Error",
                "Please paste product names into the input area.",
                parent=self,
            )
            return
        product_names = [
            name.strip() for name in input_content.splitlines() if name.strip()
        ]
        if not product_names:
            messagebox.showwarning(
                "Input Error", "No valid product names found in the input.", parent=self
            )
            return
        self.load_skus()
        if not self.all_skus:
            messagebox.showerror(
                "Error", "No SKUs available in the database.", parent=self
            )
            return

        matched_skus = []
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert(
            tk.END, f"Processing {len(product_names)} items using {selected_engine}..."
        )
        if selected_engine == ENGINE_GEMINI:
            self.output_text.insert(tk.END, "\n(This may take a while...)")
        self.output_text.config(state=tk.DISABLED)
        self.update_idletasks()  # Force GUI update to show message

        # --- Engine-Specific Logic ---
        if selected_engine == ENGINE_FUZZY:
            current_threshold = self.similarity_threshold.get()
            print(f"Using fuzzy threshold: {current_threshold}")
            matched_skus = [
                find_best_sku_match_fuzzy(name, self.all_skus, current_threshold)
                for name in product_names
            ]

        elif selected_engine == ENGINE_GEMINI:
            # --- Determine API Key based on REVERSED priority ---
            api_key_to_use = None
            source = "Not Found"
            gui_key = self.api_key_var.get().strip()
            if gui_key:  # 1. Check GUI Entry
                api_key_to_use = gui_key
                source = "GUI Entry"
            elif self.file_api_key:  # 2. Check File
                api_key_to_use = self.file_api_key
                source = f"{API_KEY_FILENAME}"
            elif self.env_api_key:  # 3. Check ENV
                api_key_to_use = self.env_api_key
                source = "Environment Variable"

            # --- Get Selected Model and Instructions ---
            selected_model = self.selected_gemini_model.get()
            custom_instructions = self.prompt_instr_text.get("1.0", tk.END).strip()

            # --- Validate Inputs ---
            if not api_key_to_use:
                messagebox.showerror(
                    "API Key Error",
                    f"Gemini API Key not found.\nPlease enter key in the GUI, create {API_KEY_FILENAME}, or set the {GEMINI_API_ENV_VAR} environment variable.",
                    parent=self,
                )
                self.output_text.config(state=tk.NORMAL)
                self.output_text.delete("1.0", tk.END)
                self.output_text.insert(tk.END, "Cancelled: Missing API Key.")
                self.output_text.config(state=tk.DISABLED)
                return
            if not selected_model:
                messagebox.showerror(
                    "Model Error", "No Gemini model selected.", parent=self
                )
                self.output_text.config(state=tk.NORMAL)
                self.output_text.delete("1.0", tk.END)
                self.output_text.insert(tk.END, "Cancelled: No Model Selected.")
                self.output_text.config(state=tk.DISABLED)
                return
            if not custom_instructions:
                messagebox.showerror(
                    "Instructions Error",
                    "Gemini prompt instructions cannot be empty.",
                    parent=self,
                )
                self.output_text.config(state=tk.NORMAL)
                self.output_text.delete("1.0", tk.END)
                self.output_text.insert(
                    tk.END, "Cancelled: Missing Prompt Instructions."
                )
                self.output_text.config(state=tk.DISABLED)
                return

            # --- Process Items ---
            print(f"Using API key from: {source}. Model: {selected_model}.")
            for i, name in enumerate(product_names):
                # Optionally update status bar or title here...
                # self.title(f"Processing {i+1}/{len(product_names)}...")
                match_result = find_best_sku_match_gemini(
                    name,
                    self.all_skus,
                    api_key_to_use,
                    selected_model,
                    custom_instructions,
                )
                matched_skus.append(match_result)
                # Handle critical errors during loop
                if (
                    "ERROR:" in match_result and "ERROR DURING" not in match_result
                ):  # Check for critical errors like invalid key/model
                    if "INVALID API KEY" in match_result:
                        messagebox.showerror(
                            "API Key Error",
                            f"Gemini API Key seems invalid (from {source}). Please check the key.",
                            parent=self,
                        )
                    elif (
                        "MODEL" in match_result
                        and "NOT FOUND/ACCESSIBLE" in match_result
                    ):
                        messagebox.showerror(
                            "Model Error",
                            f"Selected Gemini model '{selected_model}' not found or access denied.",
                            parent=self,
                        )
                    elif "MISSING API KEY" in match_result:  # Should be caught earlier
                        messagebox.showerror(
                            "API Key Error", "Gemini API Key missing.", parent=self
                        )
                    else:  # Generic API error
                        messagebox.showerror(
                            "Gemini API Error",
                            f"An error occurred during the API call:\n{match_result}",
                            parent=self,
                        )
                    break  # Stop processing other items on critical error
            # self.title("Product Name to SKU Converter") # Reset title
            print("Gemini processing finished.")

        # --- Display final results ---
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete("1.0", tk.END)
        if matched_skus:
            self.output_text.insert(tk.END, "\n".join(matched_skus))
        else:
            self.output_text.insert(
                tk.END, "Processing incomplete or no results generated."
            )
        self.output_text.config(state=tk.DISABLED)

    def open_sku_manager(self):
        """Opens the SKU Management window."""
        manager_window = SkuManagerWindow(self)
        self.wait_window(manager_window)
        self.load_skus()  # Reload SKUs after manager closes


# --- Run the Application ---
if __name__ == "__main__":
    # Ensure database exists (handled by database.py import)
    # db.init_db() # Called automatically on import now

    # Create and run the main application window
    app = Application()
    app.mainloop()
